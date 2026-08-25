"""
Layer 5 — usefulness reporting.

Phases 1–5 proved the co-pilot is *correct*: contracts hold, governance is
enforced, evidence is traceable. None of that shows it is **useful**. Layer 5 is
the only layer a human answers, and this module turns the verdicts captured in
``src/rm/feedback.py`` into something a firm can act on.

The question it answers is deliberately narrow:

    Which recommendations do RMs actually find useful, and which are wrong?

That is answered **per signal code**, because a signal code maps one-to-one onto
a rule in ``rm/heuristics.py``. A signal with a poor useful-rate names the exact
rule to retune — and a signal marked *wrong* is more serious than one marked
*not useful*: not-useful means the advice was unhelpful, wrong means the
co-pilot told an RM something untrue, which is a correctness defect rather than
a tuning problem.

Reports over small samples are reported *as* small samples. A single thumbs-down
is not evidence a rule is broken, and this module refuses to imply otherwise.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from rm.feedback import (
    VERDICT_NOT_USEFUL,
    VERDICT_USEFUL,
    VERDICT_WRONG,
    read_feedback,
)

# Below this many verdicts, a rate is not reported as meaningful.
MIN_SAMPLE_FOR_SIGNAL = 5

# A signal at or below this useful-rate (with enough samples) needs attention.
LOW_USEFUL_RATE = 0.5


def _rate(counts: Dict[str, int]) -> Optional[float]:
    total = sum(counts.values())
    return (counts[VERDICT_USEFUL] / total) if total else None


def build_report(entries: List[Dict]) -> Dict:
    """Aggregate raw feedback entries into a Layer 5 report."""
    overall = {VERDICT_USEFUL: 0, VERDICT_NOT_USEFUL: 0, VERDICT_WRONG: 0}
    by_signal: Dict[str, Dict[str, int]] = {}
    by_capability: Dict[str, Dict[str, int]] = {}
    respondents = set()

    for e in entries:
        verdict = e.get("verdict")
        if verdict not in overall:
            continue
        overall[verdict] += 1
        if e.get("rm_id"):
            respondents.add(e["rm_id"])

        signal = e.get("signal_code") or "UNATTRIBUTED"
        by_signal.setdefault(signal, dict.fromkeys(overall, 0))[verdict] += 1

        capability = e.get("capability") or "unknown"
        by_capability.setdefault(capability, dict.fromkeys(overall, 0))[verdict] += 1

    total = sum(overall.values())

    signals = []
    for code, counts in by_signal.items():
        n = sum(counts.values())
        signals.append({
            "signal_code": code,
            "responses": n,
            "counts": counts,
            "useful_rate": _rate(counts),
            "enough_data": n >= MIN_SAMPLE_FOR_SIGNAL,
            "wrong_count": counts[VERDICT_WRONG],
        })
    # `useful_rate` is None only when a signal has no scored verdicts at all.
    # It must be compared explicitly against None: a rate of 0.0 is falsy, and
    # treating it as "no data" would hide the single worst-performing rule from
    # the tuning list — exactly the signal a reviewer most needs to see.
    def _rate_or_perfect(signal: Dict) -> float:
        rate = signal["useful_rate"]
        return 1.0 if rate is None else rate

    # Worst first, but only among signals with enough data to judge.
    signals.sort(key=lambda s: (s["enough_data"], -_rate_or_perfect(s)), reverse=True)

    # Correctness defects first: "wrong" means the co-pilot said something untrue.
    correctness_concerns = [s for s in signals if s["wrong_count"] > 0]
    tuning_candidates = [
        s for s in signals
        if s["enough_data"] and _rate_or_perfect(s) <= LOW_USEFUL_RATE
    ]

    return {
        "total_responses": total,
        "respondents": len(respondents),
        "overall": overall,
        "useful_rate": _rate(overall),
        "signals": signals,
        "by_capability": [
            {"capability": c, "responses": sum(v.values()), "counts": v,
             "useful_rate": _rate(v)}
            for c, v in sorted(by_capability.items())
        ],
        "correctness_concerns": correctness_concerns,
        "tuning_candidates": tuning_candidates,
        "sufficient_data": total >= MIN_SAMPLE_FOR_SIGNAL,
    }


def _pct(rate: Optional[float]) -> str:
    return "—" if rate is None else f"{rate * 100:.0f}%"


def render_text(report: Dict) -> str:
    """Render the report for a terminal."""
    lines: List[str] = []
    add = lines.append

    add("")
    add("  RM CO-PILOT — LAYER 5 USEFULNESS REPORT")
    add("  " + "-" * 58)

    if report["total_responses"] == 0:
        add("  No feedback recorded yet.")
        add("")
        add("  Layer 5 measures whether RMs find the recommendations useful.")
        add("  It stays empty until someone uses the RM Co-pilot tab and")
        add("  answers 'Was this useful?' on an output.")
        add("")
        return "\n".join(lines)

    add(f"  Responses      {report['total_responses']} "
        f"from {report['respondents']} RM(s)")
    add(f"  Useful rate    {_pct(report['useful_rate'])}  "
        f"(useful {report['overall'][VERDICT_USEFUL]} · "
        f"not useful {report['overall'][VERDICT_NOT_USEFUL]} · "
        f"wrong {report['overall'][VERDICT_WRONG]})")

    if not report["sufficient_data"]:
        add("")
        add(f"  ⚠️  Fewer than {MIN_SAMPLE_FOR_SIGNAL} responses — treat every")
        add("      figure below as anecdote, not evidence.")

    add("")
    add("  BY SIGNAL  (each maps to one rule in rm/heuristics.py)")
    add(f"  {'SIGNAL':<28}{'N':>4}{'USEFUL':>9}{'WRONG':>7}   NOTE")
    add("  " + "-" * 58)
    for s in report["signals"]:
        note = "" if s["enough_data"] else "low sample"
        if s["wrong_count"]:
            note = ("marked WRONG" if not note else note + " · WRONG")
        add(f"  {s['signal_code']:<28}{s['responses']:>4}"
            f"{_pct(s['useful_rate']):>9}{s['wrong_count']:>7}   {note}")

    if report["correctness_concerns"]:
        add("")
        add("  ⚠️  CORRECTNESS — an RM marked these WRONG, meaning the co-pilot")
        add("      stated something untrue. Investigate the rule, not the wording:")
        for s in report["correctness_concerns"]:
            add(f"       · {s['signal_code']}  ({s['wrong_count']} of {s['responses']})")

    if report["tuning_candidates"]:
        add("")
        add(f"  TUNING — useful-rate at or below {int(LOW_USEFUL_RATE * 100)}% "
            f"with ≥{MIN_SAMPLE_FOR_SIGNAL} responses:")
        for s in report["tuning_candidates"]:
            add(f"       · {s['signal_code']}  {_pct(s['useful_rate'])} "
                f"over {s['responses']} responses")

    if not report["correctness_concerns"] and not report["tuning_candidates"]:
        add("")
        add("  No signal is flagged for correctness or tuning.")

    add("")
    return "\n".join(lines)


def load_and_render(path: Optional[str] = None) -> str:
    return render_text(build_report(read_feedback(path)))
