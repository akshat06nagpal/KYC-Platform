import time

from config import WEIGHTS, SCORE_VERIFIED, SCORE_REVIEW


def compute_overall(results: dict):
    score = 0.0
    for step, weight in WEIGHTS.items():
        r = results.get(step)
        if not r or r.get("_skipped"):
            continue
        status = r.get("status")
        if status == "pass":
            conf = r.get("confidence", r.get("quality_score", 80))
            try:
                norm = min(max(float(conf) / 100.0, 0.5), 1.0)
            except (TypeError, ValueError):
                norm = 0.8
            score += weight * (0.75 + 0.25 * norm)
        elif status == "fail":
            score += weight * 0.25
    score = round(min(score * 100, 100), 1)
    if score >= SCORE_VERIFIED:
        status = "verified"
    elif score >= SCORE_REVIEW:
        status = "review"
    else:
        status = "rejected"
    return score, status


STEP_LABELS = {
    "liveness": "Liveness Check",
    "left_hand": "Left Hand",
    "right_hand": "Right Hand",
    "document": "Document Scan",
    "face_match": "Face Match",
}


def build_report_text(session: dict) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(session["created_at"]))
    lines = [
        "=" * 52,
        "         KYC VERIFICATION REPORT",
        "=" * 52,
        f"Session ID : {session['id']}",
        f"Date       : {ts}",
        f"Status     : {session['status'].upper()}",
        f"Score      : {session['score']} / 100",
        "-" * 52,
    ]
    for key, val in session["results"].items():
        label = STEP_LABELS.get(key, key.replace("_", " ").title())
        skipped = val.get("_skipped")
        status = "SKIPPED" if skipped else val.get("status", "?").upper()
        lines.append(f"\n[{label}]  ->  {status}")
        lines.append(f"  {val.get('message', 'No message')}")
        if val.get("confidence") is not None:
            lines.append(f"  Confidence: {val['confidence']}%")
        if val.get("quality_score") is not None:
            lines.append(f"  Quality: {val['quality_score']}")
        if val.get("extracted"):
            ex = val["extracted"]
            for field in ("name", "dob", "id_number"):
                v = ex.get(field)
                if v and v != "Not found":
                    lines.append(f"  {field.replace('_', ' ').title()}: {v}")
    lines.append("")
    lines.append("=" * 52)
    lines.append("This report was generated automatically by the")
    lines.append("KYC Verification Platform.")
    lines.append("=" * 52)
    return "\n".join(lines)
