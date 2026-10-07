import { useState } from "react";

const RING_RADIUS = 52;
const RING_CIRC = 2 * Math.PI * RING_RADIUS;

function scoreColor(score) {
  if (score == null) return "#7c9fff";
  if (score >= 80) return "#4caf50";
  if (score >= 50) return "#ffb74d";
  return "#f44336";
}

export default function ResultScreen({ results, summary, finalizing, onRestart }) {
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  const score = summary?.score ?? null;
  const status = summary?.status ?? null;
  const color = scoreColor(score);

  const downloadReport = async () => {
    if (!summary?.session_id || !summary?.report) return;
    setDownloading(true);
    try {
      const blob = new Blob([summary.report], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kyc-report-${summary.session_id}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  const copySummary = async () => {
    const lines = Object.entries(results)
      .filter(([, v]) => !v._skipped)
      .map(([k, v]) => `${k}: ${v.status.toUpperCase()} - ${v.message}`);
    try {
      await navigator.clipboard.writeText(
        `KYC Verification ${score != null ? `- Score ${score}/100 (${status})` : ""}\n` + lines.join("\n")
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  };

  const entries = Object.entries(results);

  return (
    <div className="app">
      <div className="result-screen">
        {finalizing ? (
          <div className="finalizing">Computing your verification score...</div>
        ) : (
          <>
            <div className="score-ring-wrap">
              <svg className="score-ring" width="130" height="130" viewBox="0 0 130 130">
                <circle cx="65" cy="65" r={RING_RADIUS} className="ring-bg" />
                <circle
                  cx="65"
                  cy="65"
                  r={RING_RADIUS}
                  className="ring-fill"
                  stroke={color}
                  strokeDasharray={RING_CIRC}
                  strokeDashoffset={score == null ? RING_CIRC : RING_CIRC * (1 - score / 100)}
                />
              </svg>
              <div className="score-center">
                <span className="score-num" style={{ color }}>
                  {score == null ? "--" : score}
                </span>
                <span className="score-den">/ 100</span>
              </div>
            </div>

            <div className={`result-badge ${status === "verified" ? "pass" : status === "review" ? "warn" : "fail"}`}>
              {status === "verified"
                ? "KYC Verified"
                : status === "review"
                ? "Manual Review Required"
                : status === "rejected"
                ? "Verification Failed"
                : "Session Saved Locally Only"}
            </div>
            <h2>
              {status === "verified"
                ? "All checks passed. You are verified."
                : "See the breakdown below for details."}
            </h2>
          </>
        )}

        <div className="result-list">
          {entries.map(([key, val]) => (
            <div key={key} className={`result-item ${val.status}`}>
              {val._thumb && (
                <img src={val._thumb} alt={`${key} capture`} className="step-thumb" />
              )}
              <div className="result-body">
                <strong>{key.replaceAll("_", " ").toUpperCase()}</strong>
                <p>{val.message}</p>
                {val.confidence != null && (
                  <p>
                    Confidence: <b>{val.confidence}%</b>
                  </p>
                )}
                {val.quality_score != null && <p>Quality: {val.quality_score}</p>}
                {val.movement_score != null && <p>Movement: {val.movement_score}</p>}
                {val.face_count != null && <p>Faces: {val.face_count}</p>}
                {val.finger_gaps != null && <p>Finger gaps: {val.finger_gaps}</p>}
                {val.document_detected != null && (
                  <p>Document outline: {val.document_detected ? "detected" : "unclear"}</p>
                )}
                {val.extracted && (
                  <div className="extracted-data">
                    {val.extracted.name !== "Not found" && <p>Name: {val.extracted.name}</p>}
                    {val.extracted.dob !== "Not found" && <p>DOB: {val.extracted.dob}</p>}
                    {val.extracted.id_number !== "Not found" && <p>ID: {val.extracted.id_number}</p>}
                    {val.mrz_found && <p className="mrz-chip">Passport MRZ parsed</p>}
                  </div>
                )}
              </div>
              <span className="pill">{val.status === "pass" ? "PASS" : val.status === "fail" ? (val._skipped ? "SKIP" : "FAIL") : val.status.toUpperCase()}</span>
            </div>
          ))}
        </div>

        <div className="buttons">
          <button className="btn primary" onClick={onRestart}>
            Start Again
          </button>
          {summary?.report && (
            <button className="btn ghost" onClick={downloadReport} disabled={downloading}>
              {downloading ? "..." : "Download report"}
            </button>
          )}
          <button className="btn ghost" onClick={copySummary}>
            {copied ? "Copied" : "Copy summary"}
          </button>
        </div>

        {summary?.session_id && (
          <p className="session-note">Session ID: {summary.session_id}</p>
        )}
      </div>
    </div>
  );
}
