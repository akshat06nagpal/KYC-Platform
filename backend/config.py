import os

FACE_MATCH_THRESHOLD = float(os.getenv("KYC_FACE_THRESHOLD", "0.68"))
MAX_UPLOAD_SIZE = int(os.getenv("KYC_MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

RATE_LIMIT_REQUESTS = int(os.getenv("KYC_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("KYC_RATE_WINDOW", "60"))

LIVENESS_FRAMES_REQUIRED = 5
LIVENESS_MIN_FACE_RATIO = 0.8
LIVENESS_MIN_MOVEMENT = 0.8
LIVENESS_MAX_MOVEMENT = 40.0
BLUR_THRESHOLD_FACE = 50
BLUR_THRESHOLD_DOC = 80
BRIGHTNESS_MIN = 50
BRIGHTNESS_MAX = 220

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kyc.db")

WEIGHTS = {
    "liveness": 0.25,
    "left_hand": 0.15,
    "right_hand": 0.15,
    "document": 0.20,
    "face_match": 0.25,
}

SCORE_VERIFIED = 80
SCORE_REVIEW = 50

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
