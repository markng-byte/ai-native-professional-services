"""
RM Sales Co-pilot — Tier 2 workflows.

Importing this package registers the Tier 2 result contracts into the shared
registry in :mod:`capabilities.contracts`, so a single ``validate_envelope``
serves Tier 1 capabilities, Tier 2 workflows, and (later) Layer 4 runtime
validation.
"""

from capabilities.contracts import register_contracts
from rm.contracts import WORKFLOW_CONTRACTS

# Idempotent: re-importing the package must not raise on duplicate registration.
try:
    register_contracts(WORKFLOW_CONTRACTS)
except ValueError:  # pragma: no cover - already registered in this process
    pass

from rm.workflows import RM_WORKFLOWS  # noqa: E402  (after registration)

__all__ = ["RM_WORKFLOWS", "WORKFLOW_CONTRACTS"]
