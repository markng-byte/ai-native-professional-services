"""
Generic assertion matcher for the eval suites.

Each test case declares an ``expected_output`` object. Rather than hard-coding
every skill's contract, this module interprets a small vocabulary of assertion
conventions used consistently across the ``EVAL_*.json`` files, so one matcher
covers all nine skills:

Suffix / prefix conventions on the *key*:
    <field>              exact match (scalars; dict = subset; list = each
                         expected element must match some actual element)
    <field>_min          numeric/length of actual >= expected
    <field>_max          numeric/length of actual <= expected
    <field>_count        len(actual[field]) == expected
    <field>_not          actual[field] != expected
    <field>_not_null     actual[field] is not None (expected: true)
    <field>_not_empty    actual[field] is a non-empty collection
    <field>_present      actual[field] is present and non-empty/non-null
    <field>_possible     soft flag — accepted (informational)
    <field>_contains     expected (str) is a case-insensitive substring
    all_results_<field>  every item in actual["results"] has item[field] == expected
    all_have_<field>     every item in actual["results"] has a non-null [field]

Named predicates (skill-specific but declarative in the eval):
    no_null_expiry_dates      no result has a null expiry_date
    sorted_ascending_by_days  results are sorted by days_until_expiry ascending
    draft_contains_sg_entity  the draft text uses the Singapore entity

``check_case`` returns (passed: bool, failures: list[str]).
"""

from __future__ import annotations

import numbers
from typing import Dict, List, Tuple


def _magnitude(value):
    """Numeric magnitude for a value: the number itself, or a collection length."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Number):
        return value
    if isinstance(value, (list, tuple, str, dict)):
        return len(value)
    return None


def _resolve_magnitude(actual: Dict, field: str):
    if field.endswith("_count"):
        field = field[: -len("_count")]
    return _magnitude(actual.get(field))


def _match_value(actual, expected) -> bool:
    """Structural match: dict = subset, list = each expected elem found, else ==."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(_match_value(actual.get(k), v) for k, v in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        return all(any(_match_value(a, e) for a in actual) for e in expected)
    return actual == expected


def _results(actual: Dict) -> List[Dict]:
    return actual.get("results", []) or []


def _check_key(actual: Dict, key: str, expected) -> Tuple[bool, str]:
    # --- named predicates ---------------------------------------------------
    if key == "no_null_expiry_dates":
        ok = all(r.get("expiry_date") is not None for r in _results(actual))
        return ok, "a result has a null expiry_date"
    if key == "sorted_ascending_by_days":
        days = [r.get("days_until_expiry") for r in _results(actual)]
        ok = all(days[i] <= days[i + 1] for i in range(len(days) - 1))
        return ok, f"results not sorted ascending by days: {days}"
    if key == "draft_contains_sg_entity":
        draft = (actual.get("draft_text") or "").lower()
        ok = "singapore" in draft and "multico (bvi)" not in draft
        return ok, "draft does not use the Singapore entity"

    # --- prefix conventions -------------------------------------------------
    if key.startswith("all_results_"):
        field = key[len("all_results_"):]
        ok = all(r.get(field) == expected for r in _results(actual))
        return ok, f"not all results have {field} == {expected!r}"
    if key.startswith("all_have_"):
        field = key[len("all_have_"):]
        ok = all(r.get(field) is not None for r in _results(actual))
        return ok, f"not all results have a non-null {field}"

    # --- suffix conventions (order matters: longest/most specific first) ----
    if key.endswith("_not_null"):
        field = key[: -len("_not_null")]
        return actual.get(field) is not None, f"{field} is null"
    if key.endswith("_not_empty"):
        field = key[: -len("_not_empty")]
        val = actual.get(field)
        ok = val is not None and len(val) > 0
        return ok, f"{field} is empty"
    if key.endswith("_present"):
        field = key[: -len("_present")]
        val = actual.get(field)
        ok = val is not None and (not hasattr(val, "__len__") or len(val) > 0)
        return ok, f"{field} is not present"
    if key.endswith("_possible"):
        # Soft/informational flag — accepted regardless (the skill may or may
        # not hard-assert it), but recorded.
        field = key[: -len("_possible")]
        return True, f"{field} possible (soft)"
    if key.endswith("_contains"):
        field = key[: -len("_contains")]
        val = actual.get(field) or ""
        ok = str(expected).lower() in str(val).lower()
        return ok, f"{field} ({val!r}) does not contain {expected!r}"
    if key.endswith("_not"):
        field = key[: -len("_not")]
        return actual.get(field) != expected, f"{field} == {expected!r} (should differ)"
    if key.endswith("_count"):
        field = key[: -len("_count")]
        val = actual.get(field)
        ok = val is not None and len(val) == expected
        return ok, f"len({field}) != {expected}"
    if key.endswith("_min"):
        field = key[: -len("_min")]
        mag = _resolve_magnitude(actual, field)
        ok = mag is not None and mag >= expected
        return ok, f"{field} magnitude {mag} < {expected}"
    if key.endswith("_max"):
        field = key[: -len("_max")]
        mag = _resolve_magnitude(actual, field)
        ok = mag is not None and mag <= expected
        return ok, f"{field} magnitude {mag} > {expected}"

    # --- plain structural equality -----------------------------------------
    ok = _match_value(actual.get(key), expected)
    return ok, f"{key}: expected {expected!r}, got {actual.get(key)!r}"


def check_case(actual: Dict, expected_output: Dict) -> Tuple[bool, List[str]]:
    """Return (passed, failures) for one test case's expected_output block."""
    failures: List[str] = []
    for key, expected in expected_output.items():
        try:
            ok, detail = _check_key(actual, key, expected)
        except Exception as exc:  # a skill returning the wrong shape is a failure
            ok, detail = False, f"{key}: error evaluating ({exc})"
        if not ok:
            failures.append(detail)
    return (len(failures) == 0), failures
