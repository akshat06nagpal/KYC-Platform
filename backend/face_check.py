import cv2
import numpy as np
from deepface import DeepFace

from config import (
    FACE_MATCH_THRESHOLD,
    BLUR_THRESHOLD_FACE,
    BRIGHTNESS_MIN,
    BRIGHTNESS_MAX,
    LIVENESS_MIN_FACE_RATIO,
    LIVENESS_MIN_MOVEMENT,
    LIVENESS_MAX_MOVEMENT,
)

_face_cascade = None


def _get_cascade():
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _face_cascade



def _has_face(img) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return len(faces) > 0


def verify_face(selfie_path: str, id_photo_path: str):
    try:
        selfie = cv2.imread(selfie_path)
        id_photo = cv2.imread(id_photo_path)
        if selfie is None or id_photo is None:
            return {
                "match": False,
                "confidence": 0,
                "status": "error",
                "message": "Could not read one of the images",
            }
        if not _has_face(selfie):
            return {
                "match": False,
                "confidence": 0,
                "status": "fail",
                "message": "No face detected in your selfie. Retake with face centered.",
            }
        if not _has_face(id_photo):
            return {
                "match": False,
                "confidence": 0,
                "status": "fail",
                "message": "No face detected in the ID photo. Upload a clearer photo of the ID holder.",
            }

        result = DeepFace.verify(
            img1_path=selfie_path,
            img2_path=id_photo_path,
            model_name="VGG-Face",
            enforce_detection=False,
            detector_backend="opencv",
            threshold=FACE_MATCH_THRESHOLD,
        )
        distance = result.get("distance", 1.0)
        confidence = round(float(result.get("confidence", max(0.0, 1 - distance) * 100)), 2)
        verified = bool(result.get("verified", False))
        return {
            "match": verified,
            "confidence": confidence,
            "distance": round(float(distance), 3),
            "threshold": FACE_MATCH_THRESHOLD,
            "status": "pass" if verified else "fail",
            "message": (
                "Face matched with ID"
                if verified
                else f"Face does not match ID (similarity {confidence}%, needs {round((1 - FACE_MATCH_THRESHOLD) * 100)}%)"
            ),
        }
    except Exception as e:
        return {"match": False, "confidence": 0, "status": "error", "message": str(e)}


def _frame_metrics(path: str):
    img = cv2.imread(path)
    if img is None:
        return None
    small = cv2.resize(img, (160, 120))
    gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return {
        "gray_small": gray_small,
        "blur": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "brightness": float(np.mean(gray)),
        "face_count": len(faces),
    }


def check_liveness(frame_path: str):
    try:
        m = _frame_metrics(frame_path)
        if m is None:
            return {"detected": False, "status": "error", "message": "Could not read image"}
        if m["face_count"] == 0:
            return {"detected": False, "status": "fail", "message": "No face detected"}
        if m["blur"] < BLUR_THRESHOLD_FACE:
            return {"detected": True, "status": "fail", "message": "Image too blurry, please hold still"}
        if m["brightness"] < BRIGHTNESS_MIN:
            return {"detected": True, "status": "fail", "message": "Too dark, please improve lighting"}
        if m["brightness"] > BRIGHTNESS_MAX:
            return {"detected": True, "status": "fail", "message": "Too bright, avoid direct light"}
        return {
            "detected": True,
            "status": "pass",
            "face_count": int(m["face_count"]),
            "quality_score": round(min(m["blur"] / 200 * 100, 100), 1),
            "message": "Face detected and quality is good",
        }
    except Exception as e:
        return {"detected": False, "status": "error", "message": str(e)}


def check_liveness_burst(frame_paths):
    try:
        metrics = []
        for p in frame_paths:
            m = _frame_metrics(p)
            if m is not None:
                metrics.append(m)

        if len(metrics) < 3:
            return {
                "detected": False,
                "status": "error",
                "message": "Not enough valid frames captured",
            }

        frames_with_face = sum(1 for m in metrics if m["face_count"] > 0)
        face_ratio = frames_with_face / len(metrics)

        if face_ratio < LIVENESS_MIN_FACE_RATIO:
            return {
                "detected": False,
                "status": "fail",
                "message": "Face was not visible in enough frames. Keep looking at the camera.",
                "frames_ok": frames_with_face,
                "frames_total": len(metrics),
            }

        diffs = []
        for a, b in zip(metrics, metrics[1:]):
            diff = cv2.absdiff(a["gray_small"], b["gray_small"])
            diffs.append(float(np.mean(diff)))
        movement = float(np.mean(diffs)) if diffs else 0.0

        avg_blur = float(np.mean([m["blur"] for m in metrics]))
        avg_brightness = float(np.mean([m["brightness"] for m in metrics]))

        if movement < LIVENESS_MIN_MOVEMENT:
            return {
                "detected": True,
                "status": "fail",
                "message": "No natural micro-movement detected. Please blink and move slightly — photos are rejected.",
                "movement_score": round(movement, 3),
            }
        if movement > LIVENESS_MAX_MOVEMENT:
            return {
                "detected": True,
                "status": "fail",
                "message": "Too much movement. Hold steadier and try again.",
                "movement_score": round(movement, 3),
            }
        if avg_blur < BLUR_THRESHOLD_FACE:
            return {"detected": True, "status": "fail", "message": "Frames too blurry, hold still"}
        if avg_brightness < BRIGHTNESS_MIN:
            return {"detected": True, "status": "fail", "message": "Too dark, please improve lighting"}
        if avg_brightness > BRIGHTNESS_MAX:
            return {"detected": True, "status": "fail", "message": "Too bright, avoid direct light"}

        quality = round(min(avg_blur / 200 * 100, 100), 1)
        return {
            "detected": True,
            "status": "pass",
            "frames_ok": frames_with_face,
            "frames_total": len(metrics),
            "movement_score": round(movement, 3),
            "quality_score": quality,
            "message": "Liveness confirmed — natural motion detected across frames",
        }
    except Exception as e:
        return {"detected": False, "status": "error", "message": str(e)}



























while(q.size()>0){
    if(!vis[v]){
       vis[v]=true
    }
}