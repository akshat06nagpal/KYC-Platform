import { useRef, useState, useCallback, useEffect } from "react";
import client, { serverError } from "./api";

const INSTRUCTIONS = {
  liveness: "Look straight at the camera. We will capture a short burst of frames to confirm you are live. Blink naturally.",
  left_hand: "Hold up your LEFT hand, palm facing the camera.",
  right_hand: "Hold up your RIGHT hand, palm facing the camera.",
  document: "Hold your ID card or passport flat, filling the frame, in good lighting.",
  face_match: "Look at the camera for a fresh selfie, then upload your ID photo below.",
};

const GUIDE_CLASS = {
  liveness: "guide-face",
  left_hand: "guide-hand",
  right_hand: "guide-hand",
  document: "guide-doc",
  face_match: "guide-face",
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function CameraView({ currentStep, onComplete }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const prevPixelsRef = useRef(null);
  const goodFramesRef = useRef(0);
  const busyRef = useRef(false);
  const facingRef = useRef("user");

  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [msgType, setMsgType] = useState("info");
  const [idFile, setIdFile] = useState(null);
  const [facing, setFacing] = useState("user");
  const [meters, setMeters] = useState({ brightness: null, stability: null });
  const [autoReady, setAutoReady] = useState(false);

  const stopStream = () => {
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setStreaming(false);
    goodFramesRef.current = 0;
    setAutoReady(false);
    setMeters({ brightness: null, stability: null });
  };

  useEffect(() => {
    return () => {
      stopStream();
    };
  }, []);

  const startCamera = async (mode = facingRef.current) => {
    try {
      stopStream();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode },
        audio: false,
      });
      facingRef.current = mode;
      setFacing(mode);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setStreaming(true);
      setMessage("");
    } catch {
      setMessage("Camera access denied. Please allow camera permission.");
      setMsgType("error");
    }
  };

  const flipCamera = () => {
    startCamera(facingRef.current === "user" ? "environment" : "user");
  };

  const captureFrame = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const full = document.createElement("canvas");
    full.width = video.videoWidth;
    full.height = video.videoHeight;
    full.getContext("2d").drawImage(video, 0, 0);
    const thumbC = document.createElement("canvas");
    thumbC.width = 128;
    thumbC.height = 96;
    thumbC.getContext("2d").drawImage(video, 0, 0, 128, 96);
    const blob = await new Promise((res) => full.toBlob(res, "image/jpeg", 0.92));
    return { blob, thumb: thumbC.toDataURL("image/jpeg", 0.6) };
  }, []);

  const handleCapture = async (auto = false) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setLoading(true);
    setMsgType("info");
    setMessage(auto ? "Auto-capturing..." : "Analyzing...");

    try {
      const form = new FormData();
      let response;
      let thumb = null;

      if (currentStep === "liveness") {
        const shots = [];
        for (let i = 0; i < 5; i++) {
          const shot = await captureFrame();
          if (shot) shots.push(shot);
          if (i < 4) await sleep(350);
        }
        if (shots.length < 3) {
          setMessage("Camera not ready. Please wait and try again.");
          setMsgType("error");
          setLoading(false);
          busyRef.current = false;
          return;
        }
        thumb = shots[Math.floor(shots.length / 2)].thumb;
        shots.forEach((s) => form.append("frames", s.blob, "frame.jpg"));
        response = await client.post("/verify-liveness-burst", form);
      } else {
        const shot = await captureFrame();
        if (!shot) {
          setMessage("Camera not ready. Please wait and try again.");
          setMsgType("error");
          setLoading(false);
          busyRef.current = false;
          return;
        }
        thumb = shot.thumb;

        if (currentStep === "left_hand") {
          form.append("frame", shot.blob, "frame.jpg");
          form.append("hand", "left");
          response = await client.post("/hand-check", form);
        } else if (currentStep === "right_hand") {
          form.append("frame", shot.blob, "frame.jpg");
          form.append("hand", "right");
          response = await client.post("/hand-check", form);
        } else if (currentStep === "document") {
          form.append("doc_image", shot.blob, "document.jpg");
          response = await client.post("/scan-document", form);
        } else if (currentStep === "face_match") {
          if (!idFile) {
            setMessage("Please select your ID photo first.");
            setMsgType("error");
            setLoading(false);
            busyRef.current = false;
            return;
          }
          form.append("selfie", shot.blob, "selfie.jpg");
          form.append("id_photo", idFile, "id_photo.jpg");
          response = await client.post("/verify-face", form);
        }
      }

      const data = response.data;
      setMessage(data.message || "Done");
      setMsgType(
        data.status === "pass" ? "success" : data.status === "fail" ? "error" : "info"
      );

      if (data.status === "pass") {
        setTimeout(() => onComplete({ ...data, _thumb: thumb }), 900);
      }
    } catch (err) {
      setMessage(serverError(err) || "Error connecting to server. Make sure the backend is running.");
      setMsgType("error");
    }
    setLoading(false);
    busyRef.current = false;
  };

  const analyzeLive = useCallback(() => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || busyRef.current) return;

    if (!canvasRef.current) canvasRef.current = document.createElement("canvas");
    const c = canvasRef.current;
    c.width = 64;
    c.height = 48;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, 64, 48);
    const data = ctx.getImageData(0, 0, 64, 48).data;

    let sum = 0;
    const pixels = new Uint8Array(data.length / 4);
    for (let i = 0; i < pixels.length; i++) {
      const lum = (data[i * 4] * 0.299 + data[i * 4 + 1] * 0.587 + data[i * 4 + 2] * 0.114) | 0;
      pixels[i] = lum;
      sum += lum;
    }
    const brightness = sum / pixels.length;

    let stability = 1;
    if (prevPixelsRef.current && prevPixelsRef.current.length === pixels.length) {
      let diff = 0;
      for (let i = 0; i < pixels.length; i++) diff += Math.abs(pixels[i] - prevPixelsRef.current[i]);
      stability = Math.max(0, 1 - diff / pixels.length / 40);
    }
    prevPixelsRef.current = pixels;

    setMeters({
      brightness: Math.round(brightness),
      stability: Math.round(stability * 100),
    });

    const lightOk = brightness >= 60 && brightness <= 205;
    const stableOk = stability >= 0.82;
    const needsId = currentStep === "face_match" && !idFile;

    if (lightOk && stableOk) {
      goodFramesRef.current += 1;
    } else {
      goodFramesRef.current = 0;
    }

    setAutoReady(goodFramesRef.current >= 2 && !needsId);

    if (goodFramesRef.current >= 5 && !needsId) {
      handleCapture(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep, idFile]);

  useEffect(() => {
    if (!streaming) return;
    const iv = setInterval(analyzeLive, 450);
    return () => clearInterval(iv);
  }, [streaming, analyzeLive]);

  const bPct = meters.brightness == null ? 0 : Math.min(100, (meters.brightness / 255) * 100);
  const sPct = meters.stability ?? 0;
  const bGood = meters.brightness != null && meters.brightness >= 60 && meters.brightness <= 205;
  const sGood = sPct >= 82;

  return (
    <div className="camera-view">
      <p className="instruction">{INSTRUCTIONS[currentStep]}</p>

      <div className={`video-wrapper ${autoReady ? "armed" : ""}`}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`video-feed ${facing === "user" ? "mirror" : ""}`}
        />
        {!streaming && (
          <div className="video-placeholder">
            <span>Camera off</span>
            <button className="btn primary" onClick={() => startCamera()}>
              Start Camera
            </button>
          </div>
        )}
        {streaming && currentStep !== "document" && <div className={GUIDE_CLASS[currentStep]} />}
        {streaming && (
          <>
            <div className="live-badge">
              <span className="dot" /> LIVE
            </div>
            {loading && <div className="capture-flash" />}
          </>
        )}
      </div>

      {streaming && (
        <div className="meters">
          <div className="meter-row">
            <span>Light</span>
            <div className="meter">
              <i className={bGood ? "good" : ""} style={{ width: `${bPct}%` }} />
            </div>
          </div>
          <div className="meter-row">
            <span>Steady</span>
            <div className="meter">
              <i className={sGood ? "good" : ""} style={{ width: `${sPct}%` }} />
            </div>
          </div>
          <span className={`auto-chip ${autoReady ? "on" : ""}`}>
            {loading ? "Checking..." : autoReady ? "Auto-capture armed" : "Hold steady to arm auto-capture"}
          </span>
        </div>
      )}

      {currentStep === "face_match" && (
        <div className="id-upload">
          <label>ID photo</label>
          <input type="file" accept="image/*" onChange={(e) => setIdFile(e.target.files[0])} />
        </div>
      )}

      {message && <div className={`message ${msgType}`}>{message}</div>}

      <div className="buttons">
        {streaming && (
          <>
            <button onClick={() => handleCapture(false)} disabled={loading} className="btn primary">
              {loading ? "Checking..." : "Capture now"}
            </button>
            <button onClick={flipCamera} disabled={loading} className="btn ghost">
              Flip
            </button>
            <button onClick={stopStream} disabled={loading} className="btn ghost">
              Stop
            </button>
          </>
        )}
      </div>
    </div>
  );
}
