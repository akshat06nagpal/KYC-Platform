import os
import re
from shutil import which

import cv2
import numpy as np
import pytesseract

from config import TESSERACT_CMD, BLUR_THRESHOLD_DOC

if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
else:
    found = which("tesseract")
    if found:
        pytesseract.pytesseract.tesseract_cmd = found

MRZ_LINE = re.compile(r"([A-Z0-9<]{25,44})")


def scan_document(doc_path: str):
    try:
        img = cv2.imread(doc_path)
        if img is None:
            return {"status": "error", "message": "Could not read document image"}

        h, w = img.shape[:2]
        if w < 900:
            scale = 900 / w
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        glare_ratio = np.sum(gray > 240) / gray.size
        if glare_ratio > 0.15:
            return {"status": "fail", "message": "Glare detected on document. Avoid direct light on your ID"}

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < BLUR_THRESHOLD_DOC:
            return {"status": "fail", "message": "Document image is blurry. Hold your ID steady"}

        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_area = gray.shape[0] * gray.shape[1]
        doc_found = False
        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            area = cv2.contourArea(cnt)
            if len(approx) >= 4 and area > img_area * 0.1:
                doc_found = True
                break

        extracted_text = ""
        name_match = dob_match = id_match = mrz_lines = None
        if doc_found:
            processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            extracted_text = pytesseract.image_to_string(processed)
            name_match = re.search(r"(Name|NAME|Nom|Nombre)[:\s]+([A-Z][A-Z\s]{2,})", extracted_text)
            dob_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{4})", extracted_text)
            id_match = re.search(r"([A-Z]{1,3}\d{6,12})", extracted_text)
            mrz_lines = MRZ_LINE.findall(extracted_text.upper())

        parsed_mrz = None
        if mrz_lines and len(mrz_lines) >= 2 and mrz_lines[0].startswith("P<"):
            line2 = mrz_lines[1]
            raw_name = mrz_lines[0][5:]
            parts = raw_name.split("<<")
            surname = parts[0].strip("< ").title() if parts else ""
            given = parts[1].strip("< ").title() if len(parts) > 1 else ""
            number = line2[:9].replace("<", "").strip()
            dob_raw = line2[13:19]
            dob_fmt = f"{dob_raw[4:6]}/{dob_raw[2:4]}/{dob_raw[0:2]}" if dob_raw.isdigit() else None
            parsed_mrz = {
                "surname": surname,
                "given_names": given,
                "passport_number": number or None,
                "date_of_birth": dob_fmt,
            }

        if parsed_mrz and (parsed_mrz["surname"] or parsed_mrz["given_names"]):
            final_name = (parsed_mrz["surname"] + ", " + parsed_mrz["given_names"]).strip(", ")
        else:
            final_name = name_match.group(2).strip() if name_match else "Not found"

        final_dob = (
            parsed_mrz["date_of_birth"]
            if parsed_mrz and parsed_mrz["date_of_birth"]
            else (dob_match.group(1) if dob_match else "Not found")
        )
        final_id = (
            parsed_mrz["passport_number"]
            if parsed_mrz and parsed_mrz["passport_number"]
            else (id_match.group(1) if id_match else "Not found")
        )

        fields_found = sum(1 for v in (final_name, final_dob, final_id) if v != "Not found")

        if not doc_found:
            return {
                "status": "fail",
                "document_detected": False,
                "mrz_found": False,
                "quality_score": round(min(laplacian_var / 300 * 100, 100), 1),
                "extracted": {"name": "Not found", "dob": "Not found", "id_number": "Not found", "raw_text": ""},
                "message": "Document outline unclear but image is sharp. Try filling more of the frame.",
            }

        return {
            "status": "pass",
            "document_detected": True,
            "mrz_found": bool(parsed_mrz),
            "quality_score": round(min(laplacian_var / 300 * 100, 100), 1),
            "fields_found": fields_found,
            "extracted": {
                "name": final_name,
                "dob": final_dob,
                "id_number": final_id,
                "raw_text": extracted_text[:400],
            },
            "message": (
                f"Document scanned — {fields_found}/3 key fields extracted"
                + (" via passport MRZ" if parsed_mrz else "")
            ),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
