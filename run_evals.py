#!/usr/bin/env python3
"""
Repo-root entry point for the L4 skill eval gate.

    python run_evals.py            # run every suite, enforce the gate
    python run_evals.py --write    # also persist scores back into eval files

Exits non-zero if any skill falls below its minimum pass rate or has fewer than
the required number of test cases. Wired into CI at .github/workflows/eval-gate.yml.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from evals.runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
