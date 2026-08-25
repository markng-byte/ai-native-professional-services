"""
Layer 5 feedback capture.

Phase 5 does not *measure* usefulness — it makes measurement possible. This
module records what an RM thought of a given output so that Layer 5 has data to
work with once real people use the surface.

What is stored, and what deliberately is not
--------------------------------------------
Stored: the identifiers needed to join a verdict back to the run that produced
it (``correlation_id``, ``audit_ref``, capability, signal code), the actor, the
verdict, and an optional free-text note.

**Not stored:** draft bodies, client names, summaries, or any other content.
The verdict is joinable to the original run through ``correlation_id``, so
copying the content here would duplicate client data into a second store for no
retrieval benefit — the same reasoning applied to governance records in §22.

The free-text note is the one field an RM could type client detail into. It is
length-capped and the caller is warned in the UI; it is not scrubbed, because
silently altering a human's words would be worse than storing them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

VERDICT_USEFUL = "USEFUL"
VERDICT_NOT_USEFUL = "NOT_USEFUL"
VERDICT_WRONG = "WRONG"

VERDICTS = (VERDICT_USEFUL, VERDICT_NOT_USEFUL, VERDICT_WRONG)

NOTE_MAX_CHARS = 500

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "feedback", "rm_feedback.jsonl",
)


def feedback_path(path: Optional[str] = None) -> str:
    return path or os.environ.get("FIRMOS_FEEDBACK_PATH") or _DEFAULT_PATH


def record_feedback(envelope: Dict, *, rm_id: Optional[str], verdict: str,
                    note: Optional[str] = None, path: Optional[str] = None) -> Dict:
    """Append one verdict to the feedback log and return the written entry."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}, got {verdict!r}")

    audit = envelope.get("audit") or {}
    result = envelope.get("result") or {}

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rm_id": rm_id,
        "capability": envelope.get("capability"),
        "correlation_id": envelope.get("correlation_id"),
        "audit_ref": audit.get("audit_ref"),
        "data_source": audit.get("data_source"),
        "client_id": result.get("client_id"),
        "signal_code": result.get("signal_code") or result.get("based_on_signal"),
        "priority": result.get("priority"),
        "verdict": verdict,
        "note": (note or "")[:NOTE_MAX_CHARS] or None,
    }

    target = feedback_path(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def read_feedback(path: Optional[str] = None) -> List[Dict]:
    """Read the feedback log. Returns an empty list if nothing was recorded."""
    target = feedback_path(path)
    if not os.path.exists(target):
        return []
    out: List[Dict] = []
    with open(target, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def summarise(entries: List[Dict]) -> Dict:
    """Aggregate verdicts — the raw material for a Layer 5 report."""
    counts = {v: 0 for v in VERDICTS}
    by_signal: Dict[str, Dict[str, int]] = {}
    for e in entries:
        verdict = e.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
        signal = e.get("signal_code") or "UNKNOWN"
        bucket = by_signal.setdefault(signal, {v: 0 for v in VERDICTS})
        if verdict in bucket:
            bucket[verdict] += 1
    total = sum(counts.values())
    return {
        "total": total,
        "counts": counts,
        "useful_rate": (counts[VERDICT_USEFUL] / total) if total else None,
        "by_signal": by_signal,
    }
