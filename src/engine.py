"""
Orchestration Engine for the Command Center UI.

This module turns a natural-language request into an ordered *pipeline* of
agent stages that the UI can stream step-by-step. It is designed to run with
**zero external dependencies** (just the Python stdlib) so the interface is
usable out-of-the-box for demos, while still being able to upgrade to live
Claude inference and the real CrewAI crew when an API key is present.

The UI layer (app.py) consumes:
    - AGENTS      : the agent roster + presentation metadata
    - USE_CASES   : the capability gallery ("what can this system do?")
    - classify()  : intent classification (mirrors IntentClassifierTool)
    - build_pipeline(prompt) : ordered list of Stage objects to stream
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Agent roster (mirrors L5_Agents specs + src/agents.py)
# ---------------------------------------------------------------------------

AGENTS: Dict[str, Dict] = {
    "ea": {
        "name": "Executive Assistant",
        "icon": "🎯",
        "role": "Command Center · synthesises every output into an executive brief",
        "risk": "HIGH",
    },
    "orchestrator": {
        "name": "Orchestrator",
        "icon": "🧭",
        "role": "Intake · classifies intent and routes to the right specialist",
        "risk": "LOW",
    },
    "research": {
        "name": "Research Agent",
        "icon": "🔍",
        "role": "Jurisdiction comparisons & regulatory lookups (GraphRAG)",
        "risk": "MEDIUM",
    },
    "compliance": {
        "name": "Compliance Agent",
        "icon": "🛡️",
        "role": "Sanctions / PEP screening, UBO chains, conflict checks",
        "risk": "HIGH",
    },
    "drafting": {
        "name": "Drafting Agent",
        "icon": "✍️",
        "role": "Engagement letters & banking intros from approved templates",
        "risk": "MED-HIGH",
    },
    "operations": {
        "name": "Operations Agent",
        "icon": "📅",
        "role": "Renewals, filing deadlines & status reports",
        "risk": "MEDIUM",
    },
}

# Status vocabulary shared with the UI for colour-coding the live roster.
STATUS_IDLE = "idle"
STATUS_QUEUED = "queued"
STATUS_THINKING = "thinking"
STATUS_WORKING = "working"
STATUS_DONE = "done"
STATUS_BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Capability gallery — "make it obvious what this system does"
# ---------------------------------------------------------------------------

USE_CASES: List[Dict] = [
    {
        "icon": "⚖️",
        "title": "Jurisdiction Comparison",
        "desc": "Compare BVI / Cayman / Singapore (and more) across cost, tax, "
        "timeline, substance, FATF status and banking access.",
        "agents": ["orchestrator", "research", "ea"],
        "example": "Compare BVI, Cayman and Singapore for a new holding company.",
    },
    {
        "icon": "🛡️",
        "title": "Sanctions & KYC Screening",
        "desc": "Run sanctions, PEP and adverse-media screening on a client and "
        "its principals. Any match blocks and escalates to human review.",
        "agents": ["orchestrator", "compliance", "ea"],
        "example": "Screen Acme Holdings Ltd and its director John Doe for sanctions.",
    },
    {
        "icon": "🕸️",
        "title": "UBO / Ownership Chain",
        "desc": "Traverse the ownership graph to surface ultimate beneficial "
        "owners and flag conflicts of interest along the chain.",
        "agents": ["orchestrator", "compliance", "ea"],
        "example": "Map the UBO chain for Project Atlas Group and flag any conflicts.",
    },
    {
        "icon": "✍️",
        "title": "Engagement Letter Drafting",
        "desc": "Generate a first-draft engagement letter or banking intro from "
        "approved templates — always routed for human sign-off.",
        "agents": ["orchestrator", "drafting", "ea"],
        "example": "Draft an engagement letter for a new BVI company incorporation.",
    },
    {
        "icon": "📅",
        "title": "Renewals & Deadlines",
        "desc": "Surface upcoming annual renewals, economic-substance filings and "
        "statutory deadlines across the client book.",
        "agents": ["orchestrator", "operations", "ea"],
        "example": "Show upcoming renewals and filing deadlines for this quarter.",
    },
    {
        "icon": "🧠",
        "title": "Executive Onboarding Brief",
        "desc": "A multi-agent brief: research + compliance + operations rolled "
        "into one structured plan to onboard a new client.",
        "agents": ["orchestrator", "research", "compliance", "ea"],
        "example": "Prepare a brief to onboard a Singapore fintech client into a BVI structure.",
    },
]


# ---------------------------------------------------------------------------
# Lightweight intent classification (mirrors IntentClassifierTool)
# ---------------------------------------------------------------------------

@dataclass
class Intent:
    label: str
    confidence: float
    route: str
    target_agent: str
    missing: List[str] = field(default_factory=list)


def classify(prompt: str) -> Intent:
    """Keyword intent classifier. Same contract as the L4 intent-classifier skill."""
    p = prompt.lower()

    if any(k in p for k in ("compare", "jurisdiction", " vs ", "versus", "which is better")):
        label, route, agent = "RESEARCH", "Research Agent", "research"
    elif any(k in p for k in ("screen", "sanction", "kyc", "aml", "pep", "adverse media")):
        label, route, agent = "COMPLIANCE", "Compliance Agent", "compliance"
    elif any(k in p for k in ("ubo", "beneficial owner", "ownership", "conflict")):
        label, route, agent = "COMPLIANCE", "Compliance Agent", "compliance"
    elif any(k in p for k in ("draft", "letter", "engagement", "agreement", "memo")):
        label, route, agent = "DRAFTING", "Drafting Agent", "drafting"
    elif any(k in p for k in ("renew", "deadline", "filing", "expiry", "due", "calendar")):
        label, route, agent = "OPERATIONS", "Operations Agent", "operations"
    elif any(k in p for k in ("onboard", "brief", "prepare", "plan")):
        label, route, agent = "RESEARCH", "Research Agent", "research"  # multi, EA leads
    else:
        return Intent("AMBIGUOUS", 0.42, "Human Intake Officer", "orchestrator",
                      missing=["primary objective", "client name"])

    return Intent(label, 0.95, route, agent)


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

_JURIS = {
    "bvi": ("VG", "British Virgin Islands"),
    "british virgin": ("VG", "British Virgin Islands"),
    "cayman": ("KY", "Cayman Islands"),
    "singapore": ("SG", "Singapore"),
    "hong kong": ("HK", "Hong Kong"),
    "delaware": ("US-DE", "Delaware (USA)"),
    "uae": ("AE", "United Arab Emirates"),
    "dubai": ("AE", "United Arab Emirates"),
    "uk": ("GB", "United Kingdom"),
    "luxembourg": ("LU", "Luxembourg"),
}

# Knowledge-graph mock data (consistent with JurisdictionCompareTool).
_JURIS_DATA = {
    "VG": {"cost": "$2,500", "tax": "0% corporate", "timeline": "3-5 days",
           "substance": "Light (ESA)", "fatf": "Compliant", "banking": "Moderate"},
    "KY": {"cost": "$4,500", "tax": "0% corporate", "timeline": "5-7 days",
           "substance": "Light (ESA)", "fatf": "Compliant", "banking": "Strong"},
    "SG": {"cost": "$3,000", "tax": "17% corporate", "timeline": "1-2 days",
           "substance": "High", "fatf": "Compliant", "banking": "Excellent"},
    "HK": {"cost": "$2,800", "tax": "16.5% corporate", "timeline": "2-4 days",
           "substance": "Medium", "fatf": "Compliant", "banking": "Strong"},
    "US-DE": {"cost": "$1,200", "tax": "Pass-through / 21%", "timeline": "1-3 days",
              "substance": "Low", "fatf": "Compliant", "banking": "Excellent"},
    "AE": {"cost": "$5,500", "tax": "9% corporate", "timeline": "5-10 days",
           "substance": "Medium", "fatf": "Monitored", "banking": "Moderate"},
}


def extract_jurisdictions(prompt: str) -> List[tuple]:
    p = prompt.lower()
    found, seen = [], set()
    for key, (code, name) in _JURIS.items():
        if key in p and code not in seen:
            found.append((code, name))
            seen.add(code)
    return found


def extract_entity(prompt: str) -> str:
    """Best-effort company/person name extraction."""
    # quoted name wins
    m = re.search(r'["“\']([^"”\']{3,60})["”\']', prompt)
    if m:
        return m.group(1).strip()
    # sequence of Capitalised words, optionally ending in a corporate suffix
    m = re.search(
        r"([A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+){0,4}"
        r"(?:\s+(?:Ltd|Limited|LLC|Inc|Group|Holdings|Corp|PLC|Pte))?)",
        prompt,
    )
    if m and len(m.group(1)) > 3:
        return m.group(1).strip()
    return "the subject entity"


# ---------------------------------------------------------------------------
# Stage model
# ---------------------------------------------------------------------------

@dataclass
class Stage:
    agent: str            # agent id (key of AGENTS)
    title: str            # short action label
    thought: str          # one-line "what I'm doing" shown while thinking
    body: str             # full markdown output (streamed line-by-line)
    status: str = STATUS_DONE  # terminal status after completion
    llm: bool = False     # if True, the UI may stream this from a live model


# ---------------------------------------------------------------------------
# Content generators (domain-accurate mock outputs)
# ---------------------------------------------------------------------------

def _classification_body(intent: Intent, prompt: str) -> str:
    missing = ", ".join(intent.missing) if intent.missing else "none"
    return (
        "```json\n"
        "{\n"
        f'  "intent_label": "{intent.label}",\n'
        f'  "confidence_score": {intent.confidence},\n'
        f'  "next_agent_routing": "{intent.route}",\n'
        f'  "missing_entities": [{("" if not intent.missing else chr(34) + (chr(34)+", "+chr(34)).join(intent.missing) + chr(34))}]\n'
        "}\n"
        "```\n"
        f"Routing decision → **{intent.route}**. "
        + ("All required entities present." if not intent.missing
           else f"⚠️ Missing input(s): _{missing}_. Will flag for the executive.")
    )


def _research_body(prompt: str) -> str:
    js = extract_jurisdictions(prompt)
    if len(js) < 2:
        js = [("VG", "British Virgin Islands"), ("KY", "Cayman Islands"), ("SG", "Singapore")]

    header = "| Dimension | " + " | ".join(name for _, name in js) + " |"
    sep = "|---" * (len(js) + 1) + "|"
    rows = []
    dims = [
        ("💵 Formation cost", "cost"),
        ("⏱️ Timeline", "timeline"),
        ("🏦 Corporate tax", "tax"),
        ("🏗️ Substance", "substance"),
        ("🌐 FATF status", "fatf"),
        ("💳 Banking access", "banking"),
    ]
    for label, key in dims:
        cells = [_JURIS_DATA.get(code, {}).get(key, "n/a") for code, _ in js]
        rows.append(f"| {label} | " + " | ".join(cells) + " |")

    # naive recommendation: cheapest formation among the set
    best = min(js, key=lambda j: int(re.sub(r"[^\d]", "", _JURIS_DATA.get(j[0], {}).get("cost", "999999")) or 999999))
    return (
        f"Queried GraphRAG knowledge graph for **{', '.join(c for c, _ in js)}** "
        "across 6 dimensions.\n\n"
        + "\n".join([header, sep] + rows)
        + "\n\n**Recommendation:** "
        + f"**{best[1]}** offers the lowest formation cost for a plain holding company; "
        "choose Singapore if substance / banking depth is the priority.\n\n"
        "_Source: Firm KnowledgeGraph · freshness 2026-04-29 · confidence HIGH_"
    )


def _compliance_body(prompt: str) -> str:
    entity = extract_entity(prompt)
    return (
        f"Screening target: **{entity}**\n\n"
        "| Check | Source | Result |\n|---|---|---|\n"
        "| Sanctions (OFAC/EU/UN) | Dow Jones API | ✅ No match |\n"
        "| PEP exposure | ComplyAdvantage | ⚠️ 1 potential (score 0.71) |\n"
        "| Adverse media | ComplyAdvantage | ✅ Clear |\n"
        "| Internal conflict graph | Neo4j | ✅ No related mandate |\n\n"
        f"> **Status: `POTENTIAL_MATCH`** — `required_human_review = true`\n\n"
        "A PEP-adjacent record was returned at a 0.71 confidence score. Per policy "
        "the system **does not auto-clear**; this is escalated to a compliance "
        "officer with the candidate record attached. No client-facing action taken."
    )


def _ubo_body(prompt: str) -> str:
    entity = extract_entity(prompt)
    return (
        f"Traversing ownership graph from **{entity}** (Cypher: `MATCH (e)-[:OWNS*1..5]->(o)`):\n\n"
        "```\n"
        f"{entity}\n"
        "  └─ 100% → Atlas Holdings (KY)\n"
        "          ├─ 60% → J. Doe  ◀ UBO (natural person)\n"
        "          └─ 40% → Meridian Trust (JE)\n"
        "                   └─ Beneficiary → J. Doe  ⚠ same UBO via 2 paths\n"
        "```\n\n"
        "| UBO | Effective % | Paths | Flag |\n|---|---|---|---|\n"
        "| J. Doe | 100% (60% direct + 40% via trust) | 2 | ⚠️ Concentration |\n\n"
        "> **1 ultimate beneficial owner** consolidated across 2 ownership paths. "
        "Cross-mandate check found no conflict, but the concentration is flagged for review."
    )


def _drafting_body(prompt: str) -> str:
    js = extract_jurisdictions(prompt)
    juris = js[0][1] if js else "British Virgin Islands"
    return (
        f"Generated from template `ENGAGEMENT_LETTER_v3` ({juris} incorporation):\n\n"
        "> **ENGAGEMENT LETTER — DRAFT**\n"
        "> \n"
        "> **Re: Incorporation & Corporate Services**\n"
        "> \n"
        "> Dear Client,\n"
        "> \n"
        f"> We are pleased to confirm our engagement to incorporate a company in **{juris}** "
        "and provide ongoing registered-agent and corporate secretarial services.\n"
        "> \n"
        "> **Scope:** incorporation, registered office, annual compliance, KYC maintenance.\n"
        "> **Fees:** as per Schedule A (annual government fee billed at cost).\n"
        "> **Term:** 12 months, auto-renewing subject to clear KYC.\n"
        "> \n"
        "> _[Signature block + Schedule A auto-populated on approval]_\n\n"
        "🔒 **Human-in-the-loop required** — this draft is *not* sent. It is queued for "
        "your review and signature before any client delivery."
    )


def _operations_body(prompt: str) -> str:
    return (
        "Scanned client book for obligations due in the next 90 days:\n\n"
        "| Client | Obligation | Jurisdiction | Due | Status |\n|---|---|---|---|---|\n"
        "| Orion Capital | Annual renewal | VG | 2026-07-15 | 🟠 25 days |\n"
        "| Vertex Pte | Economic-substance filing | SG | 2026-07-30 | 🟡 40 days |\n"
        "| Helios Group | Annual return | KY | 2026-08-12 | 🟢 53 days |\n"
        "| Nova Trust | KYC refresh | VG | 2026-06-28 | 🔴 8 days |\n\n"
        "> **4 obligations** in window · **1 urgent** (Nova Trust KYC refresh, 8 days). "
        "Recommend triggering the renewal workflow for Orion Capital and Nova Trust today."
    )


def _ea_body(intent: Intent, prompt: str) -> str:
    routed = AGENTS[intent.target_agent]["name"]
    return (
        "### 🎯 Executive Brief\n\n"
        "**Status:** ✅ Done  ·  **Request:** "
        f"_{prompt.strip()}_\n\n"
        f"**What happened:** Orchestrator classified this as **{intent.label}** "
        f"({int(intent.confidence*100)}% confidence) and routed it to the **{routed}**. "
        "Findings are consolidated below.\n\n"
        "**Key takeaways**\n"
        + _ea_takeaways(intent)
        + "\n\n**Recommended next action**\n"
        + _ea_next(intent)
        + "\n\n_Every client-facing output remains gated on your approval._"
    )


def _ea_takeaways(intent: Intent) -> str:
    return {
        "RESEARCH": "- Comparison table assembled across 6 dimensions.\n"
                    "- A clear cost-vs-substance trade-off is highlighted.",
        "COMPLIANCE": "- Screening complete; a potential PEP match needs human sign-off.\n"
                      "- No sanctions hits; nothing auto-cleared.",
        "DRAFTING": "- A first-draft document is ready in your review queue.\n"
                    "- Nothing has been sent to the client.",
        "OPERATIONS": "- Upcoming obligations surfaced; one is urgent.\n"
                      "- Workflow triggers are ready to fire on your word.",
        "AMBIGUOUS": "- I could not confidently classify this request.\n"
                     "- I need a little more context to route it.",
    }.get(intent.label, "- Specialist output consolidated.")


def _ea_next(intent: Intent) -> str:
    return {
        "RESEARCH": "Confirm the preferred jurisdiction and I will start the incorporation pack.",
        "COMPLIANCE": "Review the flagged PEP record and approve or reject the escalation.",
        "DRAFTING": "Open the draft, edit if needed, and approve for signature.",
        "OPERATIONS": "Approve the renewal workflow for the urgent items.",
        "AMBIGUOUS": "Tell me the client name and the objective and I'll route it immediately.",
    }.get(intent.label, "Awaiting your direction.")


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------

def build_pipeline(prompt: str) -> List[Stage]:
    """Return the ordered list of agent stages to stream for this request."""
    intent = classify(prompt)
    stages: List[Stage] = []

    # 1. Orchestrator always runs first (intake + routing)
    stages.append(Stage(
        agent="orchestrator",
        title="Classify intent & route",
        thought="Parsing the request and matching it to a canonical intent…",
        body=_classification_body(intent, prompt),
        status=STATUS_DONE if not intent.missing else STATUS_BLOCKED,
    ))

    if intent.label == "AMBIGUOUS":
        # Hand straight to the EA to ask for clarification — no specialist.
        stages.append(Stage(
            agent="ea",
            title="Request clarification",
            thought="Composing a clarifying question for the executive…",
            body=_ea_body(intent, prompt),
            llm=True,
        ))
        return stages

    # 2. Specialist stage(s)
    p = prompt.lower()
    if intent.target_agent == "research":
        stages.append(Stage("research", "Compare jurisdictions",
                            "Querying the GraphRAG knowledge graph…",
                            _research_body(prompt)))
    elif intent.target_agent == "compliance":
        if any(k in p for k in ("ubo", "beneficial owner", "ownership", "conflict")):
            stages.append(Stage("compliance", "Traverse ownership chain",
                                "Walking the ownership graph for UBOs…",
                                _ubo_body(prompt)))
        else:
            stages.append(Stage("compliance", "Run sanctions / KYC screen",
                                "Calling sanctions, PEP and adverse-media sources…",
                                _compliance_body(prompt)))
    elif intent.target_agent == "drafting":
        stages.append(Stage("drafting", "Draft document",
                            "Populating the approved template…",
                            _drafting_body(prompt)))
    elif intent.target_agent == "operations":
        stages.append(Stage("operations", "Scan obligations",
                            "Scanning the client book for deadlines…",
                            _operations_body(prompt)))

    # Multi-agent onboarding brief adds a compliance pre-check.
    if any(k in p for k in ("onboard", "brief")) and intent.target_agent == "research":
        stages.append(Stage("compliance", "Pre-screen client",
                            "Running an initial KYC pre-screen…",
                            _compliance_body(prompt)))

    # 3. Executive Assistant synthesis (always last)
    stages.append(Stage("ea", "Synthesise executive brief",
                        "Consolidating specialist outputs into a brief…",
                        _ea_body(intent, prompt), llm=True))
    return stages


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")
