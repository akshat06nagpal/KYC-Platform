import { useState } from "react";
import CameraView from "./CameraView";
import ResultScreen from "./ResultScreen";
import "./App.css";

const STEPS = ["liveness", "left_hand", "right_hand", "document", "face_match"];

export default function App() {
  const [step, setStep] = useState(0);
  const [results, setResults] = useState({});
  const [done, setDone] = useState(false);

  const handleStepComplete = (stepName, data) => {
    const updated = { ...results, [stepName]: data };
    setResults(updated);
    if (step + 1 >= STEPS.length) {
      setDone(true);
    } else {
      setStep(step + 1);
    }
  };

  if (done) return <ResultScreen results={results} onRestart={() => { setStep(0); setResults({}); setDone(false); }} />;

  return (
    <div className="app">
      <div className="header">
        <h1>KYC Verification</h1>
        <div className="progress-bar">
          {STEPS.map((s, i) => (
            <div key={s} className={`step-dot ${i < step ? "done" : ""} ${i === step ? "active" : ""}`} />
          ))}
        </div>
        <p className="step-label">Step {step + 1} of {STEPS.length}: {STEPS[step].replace("_", " ").toUpperCase()}</p>
      </div>
      <CameraView
        currentStep={STEPS[step]}
        onComplete={(data) => handleStepComplete(STEPS[step], data)}
      />
    </div>
  );
}