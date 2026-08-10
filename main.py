from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from face_check import verify_face, check_liveness
from hand_check import detect_hands
from doc_check import scan_document
import shutil, os

app = FastAPI()

# Allow React frontend to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/verify-face")
async def verify_face_endpoint(selfie: UploadFile = File(...), id_photo: UploadFile = File(...)):
    selfie_path = f"{UPLOAD_DIR}/selfie.jpg"
    id_path = f"{UPLOAD_DIR}/id_photo.jpg"
    with open(selfie_path, "wb") as f:
        shutil.copyfileobj(selfie.file, f)
    with open(id_path, "wb") as f:
        shutil.copyfileobj(id_photo.file, f)
    result = verify_face(selfie_path, id_path)
    return result

@app.post("/liveness-check")
async def liveness_endpoint(frame: UploadFile = File(...)):
    frame_path = f"{UPLOAD_DIR}/frame.jpg"
    with open(frame_path, "wb") as f:
        shutil.copyfileobj(frame.file, f)
    result = check_liveness(frame_path)
    return result

@app.post("/hand-check")
async def hand_endpoint(frame: UploadFile = File(...), hand: str = "left"):
    frame_path = f"{UPLOAD_DIR}/hand_frame.jpg"
    with open(frame_path, "wb") as f:
        shutil.copyfileobj(frame.file, f)
    result = detect_hands(frame_path, hand)
    return result

@app.post("/scan-document")
async def document_endpoint(doc_image: UploadFile = File(...)):
    doc_path = f"{UPLOAD_DIR}/document.jpg"
    with open(doc_path, "wb") as f:
        shutil.copyfileobj(doc_image.file, f)
    result = scan_document(doc_path)
    return result

@app.get("/health")
def health():
    return {"status": "ok", "message": "KYC backend is running"}