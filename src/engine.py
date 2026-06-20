"""
Orchestration Engine for the Command Center UI.

Each Stage carries both a simulated body (runs with no API key) and a
system_prompt that the UI uses to call Claude when ANTHROPIC_API_KEY is set.
Every specialist stage is now LLM-capable — not just the Executive Assistant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Agent roster
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

STATUS_IDLE     = "idle"
STATUS_QUEUED   = "queued"
STATUS_THINKING = "thinking"
STATUS_WORKING  = "working"
STATUS_DONE     = "done"
STATUS_BLOCKED  = "blocked"

# ---------------------------------------------------------------------------
# Capability gallery
# ---------------------------------------------------------------------------

USE_CASES: List[Dict] = [
    {
        "icon": "⚖️",
        "title": "Jurisdiction Comparison",
        "desc": "Compare BVI / Cayman / Singapore across cost, tax, timeline, "
                "substance, FATF status and banking access.",
        "agents": ["orchestrator", "research", "ea"],
        "example": "Compare BVI, Cayman and Singapore for a new holding company.",
    },
    {
        "icon": "🛡️",
        "title": "Sanctions & KYC Screening",
        "desc": "Run sanctions, PEP and adverse-media screening. Any match "
                "blocks and escalates to human review.",
        "agents": ["orchestrator", "compliance", "ea"],
        "example": "Screen Acme Holdings Ltd and its director John Doe for sanctions.",
    },
    {
        "icon": "🕸️",
        "title": "UBO / Ownership Chain",
        "desc": "Traverse the ownership graph to surface ultimate beneficial "
                "owners and flag conflicts of interest.",
        "agents": ["orchestrator", "compliance", "ea"],
        "example": "Map the UBO chain for Project Atlas Group and flag any conflicts.",
    },
    {
        "icon": "✍️",
        "title": "Engagement Letter Drafting",
        "desc": "Generate a first-draft engagement letter from approved "
                "templates — always routed for human sign-off.",
        "agents": ["orchestrator", "drafting", "ea"],
        "example": "Draft an engagement letter for a new BVI company incorporation.",
    },
    {
        "icon": "📅",
        "title": "Renewals & Deadlines",
        "desc": "Surface upcoming annual renewals, economic-substance filings "
                "and statutory deadlines across the client book.",
        "agents": ["orchestrator", "operations", "ea"],
        "example": "Show upcoming renewals and filing deadlines for this quarter.",
    },
    {
        "icon": "🧠",
        "title": "Executive Onboarding Brief",
        "desc": "Multi-agent brief: research + compliance rolled into one "
                "structured plan to onboard a new client.",
        "agents": ["orchestrator", "research", "compliance", "ea"],
        "example": "Prepare a brief to onboard a Singapore fintech client into a BVI structure.",
    },
]

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

@dataclass
class Intent:
    label: str
    confidence: float
    route: str
    target_agent: str
    missing: List[str] = field(default_factory=list)


def classify(prompt: str) -> Intent:
    p = prompt.lower()
    if any(k in p for k in ("compare", "jurisdiction", " vs ", "versus", "which is better")):
        return Intent("RESEARCH",    0.95, "Research Agent",    "research")
    if any(k in p for k in ("screen", "sanction", "kyc", "aml", "pep", "adverse media")):
        return Intent("COMPLIANCE",  0.95, "Compliance Agent",  "compliance")
    if any(k in p for k in ("ubo", "beneficial owner", "ownership", "conflict")):
        return Intent("COMPLIANCE",  0.95, "Compliance Agent",  "compliance")
    if any(k in p for k in ("draft", "letter", "engagement", "agreement", "memo")):
        return Intent("DRAFTING",    0.95, "Drafting Agent",    "drafting")
    if any(k in p for k in ("renew", "deadline", "filing", "expiry", "due", "calendar")):
        return Intent("OPERATIONS",  0.95, "Operations Agent",  "operations")
    if any(k in p for k in ("onboard", "brief", "prepare", "plan")):
        return Intent("RESEARCH",    0.92, "Research Agent",    "research")
    return Intent("AMBIGUOUS", 0.42, "Human Intake Officer", "orchestrator",
                  missing=["primary objective", "client name"])

# ---------------------------------------------------------------------------
# Entity / jurisdiction helpers
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

_JURIS_DATA = {
    "VG":    {"cost": "$2,500", "tax": "0% corporate",       "timeline": "3-5 days",  "substance": "Light (ESA)", "fatf": "Compliant", "banking": "Moderate"},
    "KY":    {"cost": "$4,500", "tax": "0% corporate",       "timeline": "5-7 days",  "substance": "Light (ESA)", "fatf": "Compliant", "banking": "Strong"},
    "SG":    {"cost": "$3,000", "tax": "17% corporate",      "timeline": "1-2 days",  "substance": "High",        "fatf": "Compliant", "banking": "Excellent"},
    "HK":    {"cost": "$2,800", "tax": "16.5% corporate",    "timeline": "2-4 days",  "substance": "Medium",      "fatf": "Compliant", "banking": "Strong"},
    "US-DE": {"cost": "$1,200", "tax": "Pass-through / 21%", "timeline": "1-3 days",  "substance": "Low",         "fatf": "Compliant", "banking": "Excellent"},
    "AE":    {"cost": "$5,500", "tax": "9% corporate",       "timeline": "5-10 days", "substance": "Medium",      "fatf": "Monitored", "banking": "Moderate"},
}


def extract_jurisdictions(prompt: str) -> List[tuple]:
    p, found, seen = prompt.lower(), [], set()
    for key, (code, name) in _JURIS.items():
        if key in p and code not in seen:
            found.append((code, name)); seen.add(code)
    return found


def extract_entity(prompt: str) -> str:
    m = re.search(r'[""\'](.*?)[""\'s]', prompt)
    if m and len(m.group(1)) > 3:
        return m.group(1).strip()
    m = re.search(
        r"([A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+){0,4}"
        r"(?:\s+(?:Ltd|Limited|LLC|Inc|Group|Holdings|Corp|PLC|Pte))?)",
        prompt,
    )
    return m.group(1).strip() if m and len(m.group(1)) > 3 else "the subject entity"

# ---------------------------------------------------------------------------
# Stage model
# ---------------------------------------------------------------------------

@dataclass
class Stage:
    agent: str
    title: str
    thought: str          # shown while "thinking"
    body: str             # simulation output (shown when no API key)
    system_prompt: str    # used for live Claude call when API key present
    status: str = STATUS_DONE
    llm: bool = True      # ALL stages are now LLM-capable

# ---------------------------------------------------------------------------
# System prompts per agent
# ---------------------------------------------------------------------------

_SYS_ORCHESTRATOR = (
    "You are the Orchestrator of an AI-native professional services firm. "
    "Given the user request, output a JSON block with: intent_label (RESEARCH / COMPLIANCE / "
    "DRAFTING / OPERATIONS / AMBIGUOUS), confidence_score (0-1), next_agent_routing (agent name), "
    "and missing_entities (list of what is still needed). "
    "Then add one sentence explaining the routing decision. Be concise."
)

_SYS_RESEARCH = (
    "You are the Research Specialist at an AI-native professional services firm. "
    "Compare the requested corporate jurisdictions across 6 dimensions: formation cost, "
    "incorporation timeline, corporate tax rate, substance requirements, FATF compliance status, "
    "and banking access quality. Present results as a markdown table with one row per dimension. "
    "End with a clear recommendation and state your confidence level."
)

_SYS_COMPLIANCE = (
    "You are the Compliance Officer at an AI-native professional services firm. "
    "Perform a structured AML/KYC screening report on the entity or person mentioned. "
    "Cover: OFAC/EU/UN sanctions check, PEP exposure, adverse media, and internal conflict check. "
    "Use a markdown table. For any POTENTIAL_MATCH or MATCH: set required_human_review=true and "
    "explain what a compliance officer must review. NEVER auto-clear a match. Be precise."
)

_SYS_UBO = (
    "You are the Compliance Officer specialising in ownership chain analysis. "
    "Trace the ultimate beneficial owner (UBO) chain for the entity mentioned. "
    "Show the ownership tree as an ASCII diagram, then a summary table of UBOs with "
    "effective ownership %, number of paths, and any flags. "
    "Flag concentration risk or circular ownership. Be precise and structured."
)

_SYS_DRAFTING = (
    "You are the Drafting Agent at an AI-native professional services firm. "
    "Generate a professional first-draft engagement letter or document for the service requested. "
    "Use proper legal letter formatting with Re: line, scope, fees placeholder, term, and signature block. "
    "End with a clear 🔒 human-in-the-loop notice — nothing is sent without human approval. "
    "Keep it concise but complete."
)

_SYS_OPERATIONS = (
    "You are the Operations Agent at an AI-native professional services firm. "
    "List upcoming compliance obligations, annual renewals, and filing deadlines "
    "relevant to the request. Present as a markdown table with: Client, Obligation, "
    "Jurisdiction, Due Date, and urgency Status (🔴 <14d / 🟠 <30d / 🟡 <60d / 🟢 60d+). "
    "Highlight the most urgent item and recommend a next action."
)

_SYS_EA = (
    "You are the Senior Executive Assistant and Command Center. "
    "Synthesise the specialist agent findings into a concise Executive Brief in markdown. "
    "Structure: Status line (✅/⏳/❓), one-paragraph summary of what happened, "
    "Key Takeaways as 2-3 bullets, and one clear Recommended Next Action. "
    "Prefer tables over prose. Everything is gated on human approval — state this."
)

# ---------------------------------------------------------------------------
# Simulation bodies (shown when no API key)
# ---------------------------------------------------------------------------

def _sim_classification(intent: Intent) -> str:
    missing = ", ".join(intent.missing) if intent.missing else "none"
    return (
        "```json\n{\n"
        f'  "intent_label": "{intent.label}",\n'
        f'  "confidence_score": {intent.confidence},\n'
        f'  "next_agent_routing": "{intent.route}",\n'
        f'  "missing_entities": [{chr(34) + (chr(34)+", "+chr(34)).join(intent.missing) + chr(34) if intent.missing else ""}]\n'
        "}\n```\n"
        f"Routing → **{intent.route}**. "
        + ("All required entities present." if not intent.missing
           else f"⚠️ Missing: _{missing}_.")
    )

def _sim_research(prompt: str) -> str:
    js = extract_jurisdictions(prompt)
    if len(js) < 2:
        js = [("VG", "British Virgin Islands"), ("KY", "Cayman Islands"), ("SG", "Singapore")]
    header = "| Dimension | " + " | ".join(n for _, n in js) + " |"
    sep    = "|---" * (len(js) + 1) + "|"
    dims   = [("💵 Formation cost","cost"),("⏱️ Timeline","timeline"),
              ("🏦 Corporate tax","tax"),("🏗️ Substance","substance"),
              ("🌐 FATF status","fatf"),("💳 Banking access","banking")]
    rows   = ["| " + lbl + " | " + " | ".join(_JURIS_DATA.get(c,{}).get(k,"n/a") for c,_ in js) + " |"
              for lbl, k in dims]
    best   = min(js, key=lambda j: int(re.sub(r"[^\d]","",_JURIS_DATA.get(j[0],{}).get("cost","999999")) or 999999))
    return (f"GraphRAG query for **{', '.join(c for c,_ in js)}** across 6 dimensions.\n\n"
            + "\n".join([header, sep]+rows)
            + f"\n\n**Recommendation:** **{best[1]}** — lowest cost for a plain holding company. "
            "Choose Singapore if substance / banking depth is the priority.\n\n"
            "_Source: Firm KnowledgeGraph · confidence HIGH · ⚠️ Simulation mode — enable Live AI for real analysis_")

def _sim_compliance(prompt: str) -> str:
    e = extract_entity(prompt)
    return (f"Screening target: **{e}**\n\n"
            "| Check | Source | Result |\n|---|---|---|\n"
            "| Sanctions (OFAC/EU/UN) | Dow Jones API | ✅ No match |\n"
            "| PEP exposure | ComplyAdvantage | ⚠️ 1 potential (score 0.71) |\n"
            "| Adverse media | ComplyAdvantage | ✅ Clear |\n"
            "| Internal conflict graph | Neo4j | ✅ No related mandate |\n\n"
            "> **Status: `POTENTIAL_MATCH`** — `required_human_review = true`\n\n"
            "PEP-adjacent record at 0.71 confidence. System does not auto-clear. "
            "Escalated for human review.\n\n"
            "_⚠️ Simulation mode — enable Live AI for real analysis_")

def _sim_ubo(prompt: str) -> str:
    e = extract_entity(prompt)
    return (f"Traversing ownership graph from **{e}**:\n\n"
            "```\n" + e + "\n"
            "  └─ 100% → Atlas Holdings (KY)\n"
            "          ├─ 60% → J. Doe  ◀ UBO\n"
            "          └─ 40% → Meridian Trust (JE)\n"
            "                   └─ Beneficiary → J. Doe  ⚠ same UBO, 2 paths\n```\n\n"
            "| UBO | Effective % | Paths | Flag |\n|---|---|---|---|\n"
            "| J. Doe | 100% | 2 | ⚠️ Concentration |\n\n"
            "> 1 UBO consolidated across 2 paths. No conflict found.\n\n"
            "_⚠️ Simulation mode — enable Live AI for real analysis_")

def _sim_drafting(prompt: str) -> str:
    js = extract_jurisdictions(prompt)
    juris = js[0][1] if js else "British Virgin Islands"
    return (f"Template `ENGAGEMENT_LETTER_v3` ({juris}):\n\n"
            "> **ENGAGEMENT LETTER — DRAFT**\n>\n"
            "> **Re: Incorporation & Corporate Services**\n>\n"
            "> Dear Client,\n>\n"
            f"> We confirm our engagement to incorporate a company in **{juris}** "
            "and provide registered-agent and corporate secretarial services.\n>\n"
            "> **Scope:** incorporation, registered office, annual compliance, KYC maintenance.\n"
            "> **Fees:** as per Schedule A. **Term:** 12 months, auto-renewing.\n>\n"
            "> _[Signature block + Schedule A auto-populated on approval]_\n\n"
            "🔒 **Human approval required before delivery.**\n\n"
            "_⚠️ Simulation mode — enable Live AI for real draft_")

def _sim_operations() -> str:
    return ("Obligations due in the next 90 days:\n\n"
            "| Client | Obligation | Jurisdiction | Due | Status |\n|---|---|---|---|---|\n"
            "| Orion Capital | Annual renewal | VG | 2026-07-15 | 🟠 25 days |\n"
            "| Vertex Pte | Economic-substance filing | SG | 2026-07-30 | 🟡 40 days |\n"
            "| Helios Group | Annual return | KY | 2026-08-12 | 🟢 53 days |\n"
            "| Nova Trust | KYC refresh | VG | 2026-06-28 | 🔴 8 days |\n\n"
            "> **1 urgent** — Nova Trust KYC refresh in 8 days.\n\n"
            "_⚠️ Simulation mode — enable Live AI for real client data_")

def _sim_ea(intent: Intent, prompt: str) -> str:
    routed = AGENTS[intent.target_agent]["name"]
    return (
        "### 🎯 Executive Brief\n\n"
        f"**Status:** ✅ Done  ·  **Request:** _{prompt.strip()}_\n\n"
        f"Orchestrator → **{intent.label}** ({int(intent.confidence*100)}% confidence) → **{routed}**.\n\n"
        "**Key takeaways**\n"
        + {"RESEARCH":    "- Jurisdiction comparison complete across 6 dimensions.\n- Cost-vs-substance trade-off highlighted.",
           "COMPLIANCE":  "- Screening complete; PEP match needs human sign-off.\n- Nothing auto-cleared.",
           "DRAFTING":    "- First draft ready in review queue.\n- Not sent to client.",
           "OPERATIONS":  "- Upcoming obligations surfaced; 1 urgent item.\n- Workflow triggers ready.",
           "AMBIGUOUS":   "- Request unclear; need more context to route."
           }.get(intent.label, "- Specialist output consolidated.")
        + "\n\n**Recommended next action:** "
        + {"RESEARCH":    "Confirm jurisdiction preference → start incorporation pack.",
           "COMPLIANCE":  "Review flagged PEP record → approve or reject escalation.",
           "DRAFTING":    "Review draft → approve for signature.",
           "OPERATIONS":  "Approve renewal workflow for urgent items.",
           "AMBIGUOUS":   "Provide client name and objective.",
           }.get(intent.label, "Awaiting your direction.")
        + "\n\n_Every output is gated on your approval._\n\n"
          "_⚠️ Simulation mode — enable Live AI for real synthesis_"
    )

# ---------------------------------------------------------------------------
# User-facing prompt builders (sent to Claude when live)
# ---------------------------------------------------------------------------

def _user_prompt_classification(prompt: str) -> str:
    return f"Classify this request and determine routing:\n\n{prompt}"

def _user_prompt_research(prompt: str) -> str:
    js = extract_jurisdictions(prompt)
    juris_str = ", ".join(n for _, n in js) if js else "the jurisdictions mentioned"
    return f"Compare {juris_str} for the following use case:\n\n{prompt}"

def _user_prompt_compliance(prompt: str) -> str:
    return f"Run a full AML/KYC screening report for:\n\n{prompt}"

def _user_prompt_ubo(prompt: str) -> str:
    return f"Trace the UBO chain and flag conflicts for:\n\n{prompt}"

def _user_prompt_drafting(prompt: str) -> str:
    return f"Draft the requested document:\n\n{prompt}"

def _user_prompt_operations(prompt: str) -> str:
    return f"Surface upcoming obligations and deadlines relevant to:\n\n{prompt}"

def _user_prompt_ea(prompt: str, specialist_output: str) -> str:
    return (f"Executive request: {prompt}\n\n"
            f"Specialist findings:\n{specialist_output or '(none yet)'}")

# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------

def build_pipeline(prompt: str) -> List[Stage]:
    intent = classify(prompt)
    stages: List[Stage] = []

    # 1. Orchestrator
    stages.append(Stage(
        agent="orchestrator",
        title="Classify intent & route",
        thought="Parsing request and matching to canonical intent…",
        body=_sim_classification(intent),
        system_prompt=_SYS_ORCHESTRATOR,
        status=STATUS_DONE if not intent.missing else STATUS_BLOCKED,
    ))

    if intent.label == "AMBIGUOUS":
        stages.append(Stage("ea", "Request clarification",
                            "Composing clarifying question…",
                            _sim_ea(intent, prompt), _SYS_EA))
        return stages

    # 2. Specialist
    p = prompt.lower()
    if intent.target_agent == "research":
        stages.append(Stage("research", "Compare jurisdictions",
                            "Querying GraphRAG knowledge graph…",
                            _sim_research(prompt), _SYS_RESEARCH))
    elif intent.target_agent == "compliance":
        if any(k in p for k in ("ubo", "beneficial owner", "ownership", "conflict")):
            stages.append(Stage("compliance", "Traverse ownership chain",
                                "Walking ownership graph for UBOs…",
                                _sim_ubo(prompt), _SYS_UBO))
        else:
            stages.append(Stage("compliance", "Run sanctions / KYC screen",
                                "Calling sanctions, PEP and adverse-media sources…",
                                _sim_compliance(prompt), _SYS_COMPLIANCE))
    elif intent.target_agent == "drafting":
        stages.append(Stage("drafting", "Draft document",
                            "Populating approved template…",
                            _sim_drafting(prompt), _SYS_DRAFTING))
    elif intent.target_agent == "operations":
        stages.append(Stage("operations", "Scan obligations",
                            "Scanning client book for deadlines…",
                            _sim_operations(), _SYS_OPERATIONS))

    # Multi-agent: onboarding adds compliance pre-check
    if any(k in p for k in ("onboard", "brief")) and intent.target_agent == "research":
        stages.append(Stage("compliance", "Pre-screen client",
                            "Running initial KYC pre-screen…",
                            _sim_compliance(prompt), _SYS_COMPLIANCE))

    # 3. Executive Assistant (always last)
    stages.append(Stage("ea", "Synthesise executive brief",
                        "Consolidating specialist outputs into brief…",
                        _sim_ea(intent, prompt), _SYS_EA))
    return stages


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")
