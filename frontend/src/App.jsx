import { useState } from "react";
import CameraView from "./CameraView";
import ResultScreen from "./ResultScreen";
import client from "./api";
import "./App.css";

const STEPS = ["liveness", "left_hand", "right_hand", "document", "face_match"];

export default function App() {
  const [step, setStep] = useState(0);
  const [results, setResults] = useState({});
  const [done, setDone] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [summary, setSummary] = useState(null);

  const finish = async (allResults) => {
    setDone(true);
    setFinalizing(true);
    try {
      const clean = {};
      for (const [k, v] of Object.entries(allResults)) {
        if (!v?._skipped) clean[k] = v;
      }
      const res = await client.post("/sessions", { results: clean });
      let report = null;
      try {
        report = (await client.get(`/report/${res.data.session_id}`)).data;
      } catch {
        report = null;
      }
      setSummary({ ...res.data, report });
    } catch {
      setSummary(null);
    }
    setFinalizing(false);
  };

  const handleStepComplete = (stepName, data) => {
    const updated = { ...results, [stepName]: data };
    setResults(updated);
    if (step + 1 >= STEPS.length) {
      finish(updated);
    } else {
      setStep(step + 1);
    }
  };

  const handleSkip = () => {
    const updated = {
      ...results,
      [STEPS[step]]: { status: "fail", message: "Skipped by user", _skipped: true },
    };
    setResults(updated);
    if (step + 1 >= STEPS.length) {
      finish(updated);
    } else {
      setStep(step + 1);
    }
  };

  const restart = () => {
    setStep(0);
    setResults({});
    setDone(false);
    setSummary(null);
  };

  if (done) {
    return (
      <ResultScreen
        results={results}
        summary={summary}
        finalizing={finalizing}
        onRestart={restart}
      />
    );
  }

  return (
    <div className="app">
      <div className="header">
        <h1>KYC Verification</h1>
        <div className="progress-bar">
          {STEPS.map((s, i) => (
            <div
              key={s}
              title={s.replaceAll("_", " ")}
              className={`step-dot ${i < step ? "done" : ""} ${i === step ? "active" : ""}`}
            />
          ))}
        </div>
        <p className="step-label">
          Step {step + 1} of {STEPS.length} · {STEPS[step].replaceAll("_", " ").toUpperCase()}
        </p>
      </div>

      <CameraView
        currentStep={STEPS[step]}
        onComplete={(data) => handleStepComplete(STEPS[step], data)}
      />

      <div className="footer-actions">
        <button className="link-btn" onClick={handleSkip}>
          Skip this step
        </button>
      </div>
    </div>
  );
}