#!/usr/bin/env python3
"""
Layer 5 usefulness report for the RM Co-pilot.

    python rm_feedback_report.py                 # read the default feedback log
    python rm_feedback_report.py --path <file>   # read a specific log
    python rm_feedback_report.py --json          # machine-readable output

Reads the verdicts RMs recorded in the RM Co-pilot tab and reports which
recommendations they actually found useful, broken down by signal code so a
poor result names the exact rule in ``src/rm/heuristics.py`` to revisit.

Exits 0 normally, and 2 if any signal was marked WRONG — a "wrong" verdict means
the co-pilot told an RM something untrue, which is a correctness defect rather
than a tuning preference, so it is worth failing a scheduled check on.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from rm.feedback import read_feedback  # noqa: E402
from rm.report import build_report, render_text  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="RM Co-pilot Layer 5 report.")
    parser.add_argument("--path", help="Feedback log path (default: feedback/rm_feedback.jsonl)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    report = build_report(read_feedback(args.path))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))

    return 2 if report["correctness_concerns"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
