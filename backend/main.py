import time
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    ALLOWED_TYPES,
    MAX_UPLOAD_SIZE,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    CORS_ORIGINS,
)
from face_check import verify_face, check_liveness, check_liveness_burst
from hand_check import detect_hands
from doc_check import scan_document
from database import init_db, save_session, get_session
from scoring import compute_overall, build_report_text

import asyncio
import os
import uuid

app = FastAPI(title="KYC Platform API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()

_rate_store = {}


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if request.method == "POST":
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        hits = [t for t in _rate_store.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
        if len(hits) >= RATE_LIMIT_REQUESTS:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
            )
        hits.append(now)
        _rate_store[ip] = hits
    return await call_next(request)


async def save_upload(upload: UploadFile, filename: str) -> str:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {upload.content_type}. Allowed: JPEG, PNG, WebP, BMP",
        )
    path = os.path.join(UPLOAD_DIR, filename)
    content = await upload.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    with open(path, "wb") as f:
        f.write(content)
    return path


def cleanup(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@app.post("/verify-face")
async def verify_face_endpoint(selfie: UploadFile = File(...), id_photo: UploadFile = File(...)):
    selfie_path = id_path = None
    try:
        selfie_path = await save_upload(selfie, f"{uuid.uuid4().hex}_selfie.jpg")
        id_path = await save_upload(id_photo, f"{uuid.uuid4().hex}_id.jpg")
        return await asyncio.to_thread(verify_face, selfie_path, id_path)
    finally:
        cleanup(selfie_path, id_path)


@app.post("/liveness-check")
async def liveness_endpoint(frame: UploadFile = File(...)):
    frame_path = None
    try:
        frame_path = await save_upload(frame, f"{uuid.uuid4().hex}_frame.jpg")
        return await asyncio.to_thread(check_liveness, frame_path)
    finally:
        cleanup(frame_path)


@app.post("/verify-liveness-burst")
async def liveness_burst_endpoint(frames: List[UploadFile] = File(...)):
    paths = []
    try:
        for i, frame in enumerate(frames):
            paths.append(await save_upload(frame, f"{uuid.uuid4().hex}_burst{i}.jpg"))
        return await asyncio.to_thread(check_liveness_burst, paths)
    finally:
        cleanup(*paths)


@app.post("/hand-check")
async def hand_endpoint(frame: UploadFile = File(...), hand: str = "left"):
    frame_path = None
    try:
        frame_path = await save_upload(frame, f"{uuid.uuid4().hex}_hand.jpg")
        return await asyncio.to_thread(detect_hands, frame_path, hand)
    finally:
        cleanup(frame_path)


@app.post("/scan-document")
async def document_endpoint(doc_image: UploadFile = File(...)):
    doc_path = None
    try:
        doc_path = await save_upload(doc_image, f"{uuid.uuid4().hex}_doc.jpg")
        return await asyncio.to_thread(scan_document, doc_path)
    finally:
        cleanup(doc_path)


class SessionPayload(BaseModel):
    results: dict


@app.post("/sessions")
async def create_session(payload: SessionPayload):
    results = payload.results
    if not results or not isinstance(results, dict):
        raise HTTPException(status_code=400, detail="results object is required")
    clean = {k: v for k, v in results.items() if not k.startswith("_")}
    score, status = compute_overall(clean)
    session_id = save_session(clean, score, status)
    return {"session_id": session_id, "score": score, "status": status}


@app.get("/sessions/{session_id}")
async def get_session_endpoint(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/report/{session_id}")
async def report_endpoint(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return build_report_text(session)


@app.get("/health")
def health():
    return {"status": "ok", "message": "KYC backend is running", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
