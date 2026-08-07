"""
L4 Skill implementations.

Each skill is a pure-Python, deterministic callable of the form::

    run(payload: dict) -> dict

It reads a request payload (the same shape used in the ``input`` field of the
matching ``L4_Skills/evals/EVAL_<skill>.json`` suite) and returns a structured
result dict. Implementations run against small in-repo fixtures instead of live
Neo4j / CRM / sanctions APIs, so the whole system is runnable and eval-gated
with **zero external dependencies** — while keeping the exact input/output
contracts described in the ``L4_Skills/SKILL_*.md`` specifications.

The ``SKILLS`` registry maps each ``skill_id`` (as used in the eval files and
the L5 agent specs) to its implementation.
"""

from skills.intent_classifier import run as intent_classifier
from skills.client_lookup import run as client_lookup
from skills.sanctions_screen import run as sanctions_screen
from skills.conflict_check import run as conflict_check
from skills.ubo_chain_traverse import run as ubo_chain_traverse
from skills.jurisdiction_compare import run as jurisdiction_compare
from skills.doc_expiry_scan import run as doc_expiry_scan
from skills.doc_draft_banking_intro import run as doc_draft_banking_intro
from skills.doc_draft_engagement_letter import run as doc_draft_engagement_letter

SKILLS = {
    "intent-classifier": intent_classifier,
    "client-lookup": client_lookup,
    "sanctions-screen": sanctions_screen,
    "conflict-check": conflict_check,
    "ubo-chain-traverse": ubo_chain_traverse,
    "jurisdiction-compare": jurisdiction_compare,
    "doc-expiry-scan": doc_expiry_scan,
    "doc-draft-banking-intro": doc_draft_banking_intro,
    "doc-draft-engagement-letter": doc_draft_engagement_letter,
}

__all__ = ["SKILLS"]
