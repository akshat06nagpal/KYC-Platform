from deepface import DeepFace
import cv2
import numpy as np

def verify_face(selfie_path: str, id_photo_path: str):
    try:
        result = DeepFace.verify(
            img1_path=selfie_path,
            img2_path=id_photo_path,
            model_name="VGG-Face",
            enforce_detection=True
        )
        return {
            "match": result["verified"],
            "confidence": round((1 - result["distance"]) * 100, 2),
            "status": "pass" if result["verified"] else "fail",
            "message": "Face matched with ID" if result["verified"] else "Face does not match ID"
        }
    except Exception as e:
        return {"match": False, "confidence": 0, "status": "error", "message": str(e)}

def check_liveness(frame_path: str):
    try:
        img = cv2.imread(frame_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Load face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) == 0:
            return {"detected": False, "status": "fail", "message": "No face detected"}

        # Check image quality (blurriness check)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 50:
            return {"detected": True, "status": "fail", "message": "Image too blurry, please hold still"}

        # Check brightness
        brightness = np.mean(gray)
        if brightness < 50:
            return {"detected": True, "status": "fail", "message": "Too dark, please improve lighting"}
        if brightness > 220:
            return {"detected": True, "status": "fail", "message": "Too bright, avoid direct light"}

        return {
            "detected": True,
            "status": "pass",
            "face_count": len(faces),
            "quality_score": round(min(laplacian_var / 200 * 100, 100), 1),
            "message": "Face detected and quality is good"
        }
    except Exception as e:
        return {"detected": False, "status": "error", "message": str(e)}