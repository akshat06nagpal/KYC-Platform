export default function ResultScreen({ results, onRestart }) {
  const allPassed = Object.values(results).every((r) => r.status === "pass");

  return (
    <div className="result-screen">
      <div className={`result-badge ${allPassed ? "pass" : "fail"}`}>
        {allPassed ? "✅ KYC Verified" : "⚠️ Review Required"}
      </div>
      <h2>{allPassed ? "Verification Complete!" : "Some checks need review"}</h2>

      <div className="result-list">
        {Object.entries(results).map(([key, val]) => (
          <div key={key} className={`result-item ${val.status}`}>
            <span className="result-icon">{val.status === "pass" ? "✅" : "❌"}</span>
            <div>
              <strong>{key.replace("_", " ").toUpperCase()}</strong>
              <p>{val.message}</p>
              {val.confidence && <p>Confidence: {val.confidence}%</p>}
            </div>
          </div>
        ))}
      </div>

      <button className="btn primary" onClick={onRestart}>Start Again</button>
    </div>
  );
}