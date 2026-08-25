"""
Tier 1 business capability layer for the RM Co-pilot.

Agents bind to the verbs in :data:`CAPABILITIES` — never to a CRM client, a
query language, or a raw adapter. Every capability returns the shared envelope
defined in :mod:`capabilities.contracts`.

Tier 2 (recommend/draft) and Tier 3 (execute) are **not** present: Tier 2 is the
next phase, and Tier 3 consequential writes are deliberately unimplemented in v1.
"""

from capabilities.tools import CAPABILITIES

__all__ = ["CAPABILITIES"]
