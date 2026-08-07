"""
Eval gate runner.

Executes every ``L4_Skills/evals/EVAL_<skill>.json`` suite against its skill
implementation in ``src/skills`` and enforces two deployment gates:

  1. Coverage gate  — each suite must have at least ``MIN_CASES`` (10) cases.
  2. Pass-rate gate — each suite's pass rate must be >= its ``minimum_pass_rate``.

Exit code is non-zero if any gate fails, so the same command is usable as a CI
merge gate (see .github/workflows/eval-gate.yml) and as a local pre-commit
check.

Usage:
    python run_evals.py                 # run all suites, enforce gates
    python run_evals.py --skill ubo-chain-traverse
    python run_evals.py --write         # also write current_score/last_run_date
                                        # back into each EVAL_*.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_HERE)                    # .../src
_ROOT = os.path.dirname(_SRC)                    # repo root
_EVAL_DIR = os.path.join(_ROOT, "L4_Skills", "evals")

# Make `import skills` and `import evals.matcher` work regardless of CWD.
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from skills import SKILLS               # noqa: E402
from evals.matcher import check_case    # noqa: E402

MIN_CASES = 10


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def _c(text, color):
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{Colors.END}"


def run_suite(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        suite = json.load(fh)

    skill_id = suite["skill_id"]
    min_pass_rate = suite.get("minimum_pass_rate", 0.9)
    cases = suite.get("test_cases", [])
    skill = SKILLS.get(skill_id)

    result = {
        "skill_id": skill_id,
        "path": path,
        "min_pass_rate": min_pass_rate,
        "total": len(cases),
        "passed": 0,
        "case_failures": [],       # (case_id, [details])
        "coverage_ok": len(cases) >= MIN_CASES,
        "errored": skill is None,
    }

    if skill is None:
        return result

    for case in cases:
        payload = case.get("input", {})
        try:
            actual = skill(payload)
        except Exception as exc:
            result["case_failures"].append((case.get("id"), [f"skill raised: {exc}"]))
            continue
        passed, failures = check_case(actual, case.get("expected_output", {}))
        if passed:
            result["passed"] += 1
        else:
            result["case_failures"].append((case.get("id"), failures))

    result["pass_rate"] = result["passed"] / result["total"] if result["total"] else 0.0
    result["pass_rate_ok"] = result["pass_rate"] >= min_pass_rate
    result["gate_ok"] = result["coverage_ok"] and result["pass_rate_ok"] and not result["errored"]
    return result


def maybe_write_back(result, write: bool):
    if not write:
        return
    path = result["path"]
    with open(path, "r", encoding="utf-8") as fh:
        suite = json.load(fh)
    suite["current_score"] = round(result["pass_rate"], 4)
    suite["last_run_date"] = _dt.date.today().isoformat()
    suite["failure_log"] = [
        {"case_id": cid, "details": details} for cid, details in result["case_failures"]
    ]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(suite, fh, indent=2)
        fh.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the L4 skill eval gate.")
    parser.add_argument("--skill", help="Run only this skill_id.")
    parser.add_argument("--write", action="store_true",
                        help="Write current_score/last_run_date back into eval files.")
    args = parser.parse_args(argv)

    paths = sorted(glob.glob(os.path.join(_EVAL_DIR, "EVAL_*.json")))
    if args.skill:
        paths = [p for p in paths if os.path.basename(p) == f"EVAL_{args.skill}.json"]
        if not paths:
            print(_c(f"No eval file found for skill '{args.skill}'", Colors.RED))
            return 2

    print(_c("\n  L4 SKILL EVAL GATE", Colors.BOLD))
    print(_c(f"  {len(paths)} suite(s) · coverage gate ≥ {MIN_CASES} cases · "
             "pass-rate gate per-suite\n", Colors.DIM))

    header = f"  {'SKILL':<28}{'CASES':>6}{'PASS':>6}{'RATE':>8}{'REQ':>7}  RESULT"
    print(header)
    print(_c("  " + "-" * (len(header) - 2), Colors.DIM))

    all_ok = True
    results = []
    for path in paths:
        r = run_suite(path)
        results.append(r)
        maybe_write_back(r, args.write)
        all_ok = all_ok and r["gate_ok"]

        rate = f"{r.get('pass_rate', 0) * 100:.0f}%"
        req = f"{r['min_pass_rate'] * 100:.0f}%"
        if r["errored"]:
            verdict = _c("NO IMPL", Colors.RED)
        elif r["gate_ok"]:
            verdict = _c("PASS", Colors.GREEN)
        else:
            reasons = []
            if not r["coverage_ok"]:
                reasons.append(f"coverage {r['total']}/{MIN_CASES}")
            if not r["pass_rate_ok"]:
                reasons.append("below rate")
            verdict = _c("FAIL", Colors.RED) + _c(f" ({', '.join(reasons)})", Colors.YELLOW)

        print(f"  {r['skill_id']:<28}{r['total']:>6}{r.get('passed', 0):>6}"
              f"{rate:>8}{req:>7}  {verdict}")

    # Detail on any failing cases.
    failing = [r for r in results if not r["gate_ok"]]
    if failing:
        print(_c("\n  FAILURE DETAIL", Colors.BOLD))
        for r in failing:
            if r["errored"]:
                print(_c(f"  · {r['skill_id']}: no implementation registered", Colors.RED))
            for cid, details in r["case_failures"]:
                print(_c(f"  · {r['skill_id']} / {cid}", Colors.RED))
                for d in details:
                    print(f"      - {d}")

    total_cases = sum(r["total"] for r in results)
    total_passed = sum(r.get("passed", 0) for r in results)
    print()
    summary = (f"  {total_passed}/{total_cases} cases passed across "
               f"{len(results)} skills")
    if all_ok:
        print(_c(summary + "  ·  GATE PASSED ✅\n", Colors.GREEN + Colors.BOLD))
    else:
        print(_c(summary + "  ·  GATE FAILED ❌\n", Colors.RED + Colors.BOLD))

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
