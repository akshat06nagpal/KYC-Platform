import cv2
import numpy as np
import pytesseract
import re

# If you're on Windows, tell pytesseract where Tesseract is installed
# Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def scan_document(doc_path: str):
    try:
        img = cv2.imread(doc_path)
        if img is None:
            return {"status": "error", "message": "Could not read document image"}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check for glare (very bright regions)
        bright_pixels = np.sum(gray > 240)
        total_pixels = gray.size
        glare_ratio = bright_pixels / total_pixels
        if glare_ratio > 0.15:
            return {"status": "fail", "message": "Glare detected on document. Avoid direct light on your ID"}

        # Check sharpness
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 80:
            return {"status": "fail", "message": "Document image is blurry. Hold your ID steady"}

        # Edge detection to find document borders
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        doc_found = False
        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            area = cv2.contourArea(cnt)
            if len(approx) == 4 and area > 50000:
                doc_found = True
                break

        # OCR to extract text
        processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        extracted_text = pytesseract.image_to_string(processed)

        # Try to find common ID fields
        name_match = re.search(r'(Name|NAME)[:\s]+([A-Z\s]+)', extracted_text)
        dob_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})', extracted_text)
        id_match = re.search(r'([A-Z]{1,3}\d{7,10})', extracted_text)

        return {
            "status": "pass",
            "document_detected": doc_found,
            "quality_score": round(min(laplacian_var / 300 * 100, 100), 1),
            "extracted": {
                "name": name_match.group(2).strip() if name_match else "Not found",
                "dob": dob_match.group(1) if dob_match else "Not found",
                "id_number": id_match.group(1) if id_match else "Not found",
                "raw_text": extracted_text[:300]
            },
            "message": "Document scanned successfully"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}