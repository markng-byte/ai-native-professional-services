"""
Firm decision thresholds — loaded from configuration, not hardcoded.

Every risk band, priority and recommendation the RM Co-pilot shows is derived
from the numbers in ``config/thresholds.json``. Those numbers are **advice
policy**: change them and the advice changes. Keeping them in a single
governed file means the firm can set them without a code change, and means an
RM can be told *where* a judgement came from rather than being handed a bare
"HIGH risk".

Resolution order
----------------
1. ``FIRMOS_THRESHOLDS_PATH`` if set
2. ``config/thresholds.json`` at the repository root
3. the built-in defaults below

The built-in defaults exist only so the system still runs if the file is
missing; they are identical to the shipped file, so behaviour never changes
silently depending on whether the file was found.

Validation is strict and fails loudly. A malformed threshold would not crash —
it would quietly produce wrong advice, which is worse.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

# Identical to config/thresholds.json. Used only when no file is present.
_BUILTIN_DEFAULTS: Dict = {
    "policy_owner": "UNASSIGNED",
    "last_reviewed": None,
    "ratified": False,
    "stage_sla_days": {
        "PROSPECT": 14,
        "QUALIFIED": 21,
        "PROPOSAL": 30,
        "NEGOTIATION": 21,
    },
    "high_risk_multiple": 2.0,
    "stale_activity_days": 30,
    "urgent_renewal_days": 30,
    "urgent_renewal_high_priority_days": 14,
    "high_value_amount": 50000,
}

_REQUIRED_STAGES = ("PROSPECT", "QUALIFIED", "PROPOSAL", "NEGOTIATION")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_PATH = os.path.join(_REPO_ROOT, "config", "thresholds.json")

_cache: Optional["Thresholds"] = None


class ThresholdError(ValueError):
    """Raised when the policy file is present but not usable."""


class Thresholds:
    """Validated, read-only view of the firm's decision thresholds."""

    def __init__(self, data: Dict, source: str) -> None:
        self._data = data
        self.source = source
        self._validate()

    # -- validation --------------------------------------------------------

    def _validate(self) -> None:
        stages = self._data.get("stage_sla_days")
        if not isinstance(stages, dict):
            raise ThresholdError(f"{self.source}: stage_sla_days must be an object")
        for stage in _REQUIRED_STAGES:
            if stage not in stages:
                raise ThresholdError(f"{self.source}: stage_sla_days is missing {stage}")
            value = stages[stage]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ThresholdError(
                    f"{self.source}: stage_sla_days.{stage} must be a positive integer, "
                    f"got {value!r}"
                )

        multiple = self._data.get("high_risk_multiple")
        if not isinstance(multiple, (int, float)) or isinstance(multiple, bool) or multiple < 1:
            raise ThresholdError(
                f"{self.source}: high_risk_multiple must be a number >= 1, got {multiple!r}"
            )

        for key in ("stale_activity_days", "urgent_renewal_days",
                    "urgent_renewal_high_priority_days", "high_value_amount"):
            value = self._data.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ThresholdError(
                    f"{self.source}: {key} must be a non-negative number, got {value!r}"
                )

        if (self._data["urgent_renewal_high_priority_days"]
                > self._data["urgent_renewal_days"]):
            raise ThresholdError(
                f"{self.source}: urgent_renewal_high_priority_days may not exceed "
                "urgent_renewal_days — the escalated window must sit inside the urgent one"
            )

        # Ratification is a governance claim, not a flag. Declaring these
        # numbers to be firm policy without naming who owns them or when they
        # were agreed would make the provenance shown to an RM meaningless.
        if self._data.get("ratified"):
            owner = (self._data.get("policy_owner") or "").strip()
            if not owner or owner.upper().startswith("UNASSIGNED"):
                raise ThresholdError(
                    f"{self.source}: cannot set ratified=true while policy_owner is "
                    "unassigned — name the accountable role first"
                )
            if not self._data.get("last_reviewed"):
                raise ThresholdError(
                    f"{self.source}: cannot set ratified=true without last_reviewed — "
                    "record the date these figures were agreed"
                )

    # -- accessors ---------------------------------------------------------

    @property
    def stage_sla_days(self) -> Dict[str, int]:
        return dict(self._data["stage_sla_days"])

    @property
    def high_risk_multiple(self) -> float:
        return float(self._data["high_risk_multiple"])

    @property
    def stale_activity_days(self) -> int:
        return int(self._data["stale_activity_days"])

    @property
    def urgent_renewal_days(self) -> int:
        return int(self._data["urgent_renewal_days"])

    @property
    def urgent_renewal_high_priority_days(self) -> int:
        return int(self._data["urgent_renewal_high_priority_days"])

    @property
    def high_value_amount(self) -> float:
        return float(self._data["high_value_amount"])

    @property
    def policy_owner(self) -> str:
        return self._data.get("policy_owner") or "UNASSIGNED"

    @property
    def ratified(self) -> bool:
        return bool(self._data.get("ratified"))

    @property
    def provenance(self) -> str:
        """A short, human-readable statement of where a judgement came from.

        Shown next to risk bands so an RM sees that a band is firm policy with
        an owner — or, while unratified, that it is a development placeholder.
        """
        where = os.path.relpath(self.source, _REPO_ROOT) if os.path.isabs(self.source) else self.source
        if self.ratified:
            return f"firm policy · {where} · owner {self.policy_owner}"
        return f"⚠️ provisional, not ratified · {where} · owner {self.policy_owner}"


def _load_from(path: str) -> Thresholds:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ThresholdError(f"{path}: not valid JSON ({exc})") from exc
    return Thresholds(data, source=path)


def load(path: Optional[str] = None, *, use_cache: bool = True) -> Thresholds:
    """Load the firm thresholds.

    An explicitly supplied ``path`` that does not exist is an error — silently
    falling back would mean running on different numbers than the operator
    intended.
    """
    global _cache
    if path is None and use_cache and _cache is not None:
        return _cache

    if path is not None:
        if not os.path.exists(path):
            raise ThresholdError(f"threshold file not found: {path}")
        return _load_from(path)

    env_path = os.environ.get("FIRMOS_THRESHOLDS_PATH")
    if env_path:
        if not os.path.exists(env_path):
            raise ThresholdError(
                f"FIRMOS_THRESHOLDS_PATH points at a missing file: {env_path}"
            )
        loaded = _load_from(env_path)
    elif os.path.exists(_DEFAULT_PATH):
        loaded = _load_from(_DEFAULT_PATH)
    else:
        loaded = Thresholds(dict(_BUILTIN_DEFAULTS), source="built-in defaults")

    if use_cache:
        _cache = loaded
    return loaded


def reset_cache() -> None:
    """Clear the cached thresholds (used by tests that swap policy files)."""
    global _cache
    _cache = None
