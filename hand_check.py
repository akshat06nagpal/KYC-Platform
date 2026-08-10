import cv2
import numpy as np

def detect_hands(frame_path: str, expected_hand: str = "left"):
    try:
        img = cv2.imread(frame_path)
        if img is None:
            return {"detected": False, "status": "error", "message": "Could not read image"}

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Skin color range in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)

        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.erode(mask, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {"detected": False, "status": "fail", "message": f"No hand detected. Please show your {expected_hand} hand clearly"}

        # Find largest contour (the hand)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area < 8000:
            return {"detected": False, "status": "fail", "message": "Hand too far from camera, please move closer"}

        # Determine which side of frame the hand is on
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return {"detected": False, "status": "fail", "message": "Could not locate hand position"}

        cx = int(M["m10"] / M["m00"])
        frame_width = img.shape[1]
        hand_side = "left" if cx < frame_width / 2 else "right"

        if hand_side != expected_hand:
            return {
                "detected": True,
                "status": "fail",
                "message": f"Wrong hand detected. Please show your {expected_hand} hand"
            }

        return {
            "detected": True,
            "status": "pass",
            "hand": hand_side,
            "area": int(area),
            "message": f"{expected_hand.capitalize()} hand detected successfully"
        }
    except Exception as e:
        return {"detected": False, "status": "error", "message": str(e)}