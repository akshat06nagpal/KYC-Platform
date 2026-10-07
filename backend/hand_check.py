import cv2
import numpy as np


def detect_hands(frame_path: str, expected_hand: str = "left"):
    try:
        img = cv2.imread(frame_path)
        if img is None:
            return {"detected": False, "status": "error", "message": "Could not read image"}

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)

        kernel = np.ones((5, 5), np.uint8)

        def build_mask(lower_hsv, upper_hsv):
            m1 = cv2.inRange(hsv, lower_hsv, upper_hsv)
            m2 = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
            fused = cv2.bitwise_and(m1, m2)
            fallback = m1
            for mask in (fused, fallback):
                cleaned = cv2.dilate(mask, kernel, iterations=2)
                cleaned = cv2.erode(cleaned, kernel, iterations=1)
                cnts, _ = cv2.findContours(cleaned, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    largest = max(cnts, key=cv2.contourArea)
                    if cv2.contourArea(largest) >= 8000:
                        return cleaned
            return None

        primary = build_mask(
            np.array([0, 20, 40], dtype=np.uint8),
            np.array([25, 180, 255], dtype=np.uint8),
        )
        if primary is not None:
            mask = primary
        else:
            mask = build_mask(
                np.array([0, 15, 30], dtype=np.uint8),
                np.array([30, 255, 255], dtype=np.uint8),
            )

        if mask is None:
            return {
                "detected": False,
                "status": "fail",
                "message": f"No hand detected. Please show your {expected_hand} hand clearly",
            }

        cnts, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        largest = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area < 8000:
            return {"detected": False, "status": "fail", "message": "Hand too far from camera, please move closer"}

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return {"detected": False, "status": "fail", "message": "Could not locate hand position"}

        cx = int(M["m10"] / M["m00"])
        frame_width = img.shape[1]
        hand_side = "right" if cx < frame_width / 2 else "left"

        if hand_side != expected_hand:
            return {
                "detected": True,
                "status": "fail",
                "detected_hand": hand_side,
                "message": f"That looks like your {hand_side} hand. Please show your {expected_hand} hand",
            }

        hull = cv2.convexHull(largest, returnPoints=False)
        defects = 0
        if hull is not None and len(hull) > 4:
            defects_idx = cv2.convexityDefects(largest, hull)
            if defects_idx is not None:
                defects = int(sum(1 for i in range(defects_idx.shape[0]) if defects_idx[i][0][3] > 12000))

        return {
            "detected": True,
            "status": "pass",
            "hand": hand_side,
            "area": int(area),
            "finger_gaps": defects,
            "message": f"{expected_hand.capitalize()} palm detected successfully",
        }
    except Exception as e:
        return {"detected": False, "status": "error", "message": str(e)}
