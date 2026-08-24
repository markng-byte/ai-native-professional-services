"""
CRM domain model — transactional / client truth.

This module defines the *shape* of client-and-opportunity data for the RM
Co-pilot. It is deliberately free of any storage concern: the same model is
served today by the fixture adapter and later by a Salesforce adapter, without
the capability-tool contracts changing (master prompt §8).

Determinism note
----------------
Time-relative fields are stored as **integer day offsets** (``days_in_stage``,
``due_in_days``, ``days_until_expiry``, ``days_until_renewal``,
``occurred_days_ago``) rather than absolute dates, mirroring the convention
already used by the ``doc-expiry-scan`` skill. This keeps every capability and
every eval deterministic regardless of the wall-clock date the suite runs on.

Provisional domain decisions (D1)
---------------------------------
The opportunity stage taxonomy, the per-stage ageing SLAs and the conversion
risk bands below are a **documented provisional default** — the repository had
no opportunity model of any kind (audit: ``opportunity`` = 0 hits). They follow
conventional B2B professional-services practice and are expected to be replaced
by the firm's real definitions. They are isolated here so that replacing them
touches exactly one file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Stage taxonomy (D1 — provisional)
# ---------------------------------------------------------------------------

STAGE_PROSPECT = "PROSPECT"
STAGE_QUALIFIED = "QUALIFIED"
STAGE_PROPOSAL = "PROPOSAL"
STAGE_NEGOTIATION = "NEGOTIATION"
STAGE_CLOSED_WON = "CLOSED_WON"
STAGE_CLOSED_LOST = "CLOSED_LOST"

OPEN_STAGES = (STAGE_PROSPECT, STAGE_QUALIFIED, STAGE_PROPOSAL, STAGE_NEGOTIATION)
CLOSED_STAGES = (STAGE_CLOSED_WON, STAGE_CLOSED_LOST)
ALL_STAGES = OPEN_STAGES + CLOSED_STAGES

# Ordered pipeline position, used for "stalled vs progressing" assessments.
STAGE_ORDER: Dict[str, int] = {s: i for i, s in enumerate(ALL_STAGES)}

# Maximum healthy days in a stage before the opportunity is considered ageing.
STAGE_SLA_DAYS: Dict[str, int] = {
    STAGE_PROSPECT: 14,
    STAGE_QUALIFIED: 21,
    STAGE_PROPOSAL: 30,
    STAGE_NEGOTIATION: 21,
}

# Conversion-risk bands expressed as a multiple of the stage SLA.
RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"


def stage_is_open(stage: str) -> bool:
    return stage in OPEN_STAGES


def stage_sla_days(stage: str) -> Optional[int]:
    return STAGE_SLA_DAYS.get(stage)


def assess_aging(stage: str, days_in_stage: int) -> Dict:
    """Classify how far past its stage SLA an opportunity has drifted.

    Returns a structured, explainable verdict — never a bare score — so the
    reasoning layer can cite *why* something is at risk (master prompt §12).
    """
    sla = stage_sla_days(stage)
    if sla is None:
        return {
            "stage": stage,
            "days_in_stage": days_in_stage,
            "sla_days": None,
            "over_sla_by_days": 0,
            "is_stalled": False,
            "conversion_risk": RISK_LOW,
            "basis": f"Stage {stage} is closed; ageing does not apply.",
        }

    over = days_in_stage - sla
    if over <= 0:
        risk = RISK_LOW
    elif days_in_stage >= 2 * sla:
        risk = RISK_HIGH
    else:
        risk = RISK_MEDIUM

    return {
        "stage": stage,
        "days_in_stage": days_in_stage,
        "sla_days": sla,
        "over_sla_by_days": max(0, over),
        "is_stalled": over > 0,
        "conversion_risk": risk,
        "basis": (
            f"{days_in_stage}d in {stage} against a {sla}d SLA"
            + (f" — {over}d over." if over > 0 else " — within SLA.")
        ),
    }


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RelationshipManager:
    rm_id: str
    full_name: str
    department: str


@dataclass(frozen=True)
class Client:
    client_id: str
    legal_name: str
    jurisdiction: str
    risk_rating: str
    status: str
    assigned_rm_id: str
    entity_number: Optional[str] = None
    trade_names: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    client_id: str
    name: str
    stage: str
    amount: float
    currency: str
    service_type: str
    days_in_stage: int
    assigned_rm_id: str
    expected_close_in_days: Optional[int] = None


@dataclass(frozen=True)
class Activity:
    activity_id: str
    client_id: str
    activity_type: str          # CALL | EMAIL | MEETING | NOTE
    subject: str
    occurred_days_ago: int
    actor: str
    opportunity_id: Optional[str] = None


@dataclass(frozen=True)
class Task:
    task_id: str
    client_id: str
    title: str
    status: str                 # OPEN | DONE
    due_in_days: int            # negative = overdue
    owner_rm_id: str
    opportunity_id: Optional[str] = None


@dataclass(frozen=True)
class Engagement:
    engagement_id: str
    client_id: str
    service_type: str
    status: str                 # ACTIVE | PENDING | ENDED
    renewal_in_days: Optional[int] = None


@dataclass(frozen=True)
class Document:
    doc_id: str
    client_id: str
    doc_type: str
    status: str                 # VALID | EXPIRING | EXPIRED | MISSING
    days_until_expiry: Optional[int] = None
