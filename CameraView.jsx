import { useRef, useState, useCallback } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const INSTRUCTIONS = {
  liveness: "Look straight at the camera. Keep your face centered in the circle.",
  left_hand: "Hold up your LEFT hand, palm facing the camera.",
  right_hand: "Hold up your RIGHT hand, palm facing the camera.",
  document: "Hold your ID card or passport flat and steady in good lighting.",
  face_match: "We'll take your selfie and compare it to your ID photo.",
};

export default function CameraView({ currentStep, onComplete }) {
  const videoRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [idFile, setIdFile] = useState(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      setStreaming(true);
      setMessage("");
    } catch {
      setMessage("Camera access denied. Please allow camera permission.");
    }
  };

  const captureFrame = useCallback(() => {
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d").drawImage(videoRef.current, 0, 0);
    return new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.95));
  }, []);

  const handleCapture = async () => {
    setLoading(true);
    setMessage("Analyzing...");
    try {
      const blob = await captureFrame();
      const form = new FormData();

      let response;

      if (currentStep === "liveness") {
        form.append("frame", blob, "frame.jpg");
        response = await axios.post(`${API}/liveness-check`, form);
      } else if (currentStep === "left_hand") {
        form.append("frame", blob, "frame.jpg");
        form.append("hand", "left");
        response = await axios.post(`${API}/hand-check`, form);
      } else if (currentStep === "right_hand") {
        form.append("frame", blob, "frame.jpg");
        form.append("hand", "right");
        response = await axios.post(`${API}/hand-check`, form);
      } else if (currentStep === "document") {
        form.append("doc_image", blob, "document.jpg");
        response = await axios.post(`${API}/scan-document`, form);
      } else if (currentStep === "face_match") {
        if (!idFile) {
          setMessage("Please select your ID photo first.");
          setLoading(false);
          return;
        }
        form.append("selfie", blob, "selfie.jpg");
        form.append("id_photo", idFile, "id_photo.jpg");
        response = await axios.post(`${API}/verify-face`, form);
      }

      const data = response.data;
      setMessage(data.message || "Done");

      if (data.status === "pass") {
        setTimeout(() => onComplete(data), 1000);
      }
    } catch (err) {
      setMessage("Error connecting to server. Make sure the backend is running.");
    }
    setLoading(false);
  };

  return (
    <div className="camera-view">
      <p className="instruction">{INSTRUCTIONS[currentStep]}</p>

      <div className="video-wrapper">
        <video ref={videoRef} autoPlay playsInline className="video-feed" />
        {!streaming && <div className="video-placeholder">📷 Camera not started</div>}
      </div>

      {currentStep === "face_match" && (
        <div className="id-upload">
          <label>Upload your ID photo:</label>
          <input type="file" accept="image/*" onChange={(e) => setIdFile(e.target.files[0])} />
        </div>
      )}

      {message && (
        <div className={`message ${message.includes("success") || message.includes("detected") ? "success" : "info"}`}>
          {message}
        </div>
      )}

      <div className="buttons">
        {!streaming ? (
          <button onClick={startCamera} className="btn primary">Start Camera</button>
        ) : (
          <button onClick={handleCapture} disabled={loading} className="btn primary">
            {loading ? "Checking..." : "Capture & Verify"}
          </button>
        )}
      </div>
    </div>
  );
}