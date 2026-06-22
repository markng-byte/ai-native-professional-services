"""
AEGIS API Bridge v2 — FastAPI server connecting the 4 AEGIS frontend modules
to the Firm OS AI backend (L1–L5).

Architecture (per AEGIS PRD §3.1):
  React Shell (L6)
    ↓ fetch / SSE
  api_bridge.py   ← THIS FILE (no frontend key leaking, no raw prompts from browser)
    ↓
  engine.py / agents (L5)
    ↓
  Claude API (server-side key) + GraphRAG (L1–L3)

Run:
  uvicorn src.api_bridge:app --host 0.0.0.0 --port 8000 --reload

Modules served:
  REGO  (Macro Radar)      → /api/research/*
  VRIT  (Local Intel)      → /api/compliance/local-intel
  EIT1  (Newsfeed)         → /api/operations/*  (incl. SSE pipeline)
  EIT2  (War Room)         → /api/executive/*
"""

from __future__ import annotations

import asyncio
import json
import base64
import logging
import os
import secrets
import sys
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as _engine  # noqa: E402

logger = logging.getLogger("aegis.bridge")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AEGIS API Bridge",
    description="Firm OS agent endpoints for the AEGIS React shell (all 4 modules)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Public-demo protection (only active when the relevant env vars are set)
#
#   DEMO_USER / DEMO_PASSWORD  → HTTP Basic gate over the whole site + API.
#                                Unset → no gate (local dev).
#   RATE_LIMIT_PER_HOUR        → max AI requests per client IP per hour
#                                (default 60). Protects the Claude key from
#                                being burned on a public link.
# ---------------------------------------------------------------------------
_DEMO_USER = os.getenv("DEMO_USER", "")
_DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")
_RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_HOUR", "60"))
_RATE_WINDOW = 3600  # seconds
_rate_buckets: Dict[str, deque] = defaultdict(deque)

# Paths that never require auth / rate-limiting.
_OPEN_PATHS = {"/api/health", "/favicon.ico"}


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Shared-password HTTP Basic gate. No-op when DEMO_PASSWORD is unset."""

    async def dispatch(self, request: Request, call_next):
        if not _DEMO_PASSWORD or request.url.path in _OPEN_PATHS:
            return await call_next(request)
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                raw = base64.b64decode(header[6:]).decode("utf-8", "replace")
                user, _, pwd = raw.partition(":")
                if secrets.compare_digest(user, _DEMO_USER or user) and secrets.compare_digest(pwd, _DEMO_PASSWORD):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AEGIS Demo"'},
            content="Authentication required",
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window limit on AI endpoints (POST/GET under /api/, except open paths)."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in _OPEN_PATHS:
            ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                  or (request.client.host if request.client else "unknown"))
            now = time.time()
            bucket = _rate_buckets[ip]
            while bucket and now - bucket[0] > _RATE_WINDOW:
                bucket.popleft()
            if len(bucket) >= _RATE_LIMIT:
                retry = int(_RATE_WINDOW - (now - bucket[0]))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                    content={"detail": f"Rate limit reached ({_RATE_LIMIT}/hour). Try again in {retry // 60} min."},
                )
            bucket.append(now)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)
app.add_middleware(BasicAuthMiddleware)

# ---------------------------------------------------------------------------
# Core Claude caller (server-side, key never leaves backend)
# ---------------------------------------------------------------------------
_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def _is_live() -> bool:
    return bool(_ANTHROPIC_KEY)


def _call_claude(system: str, user: str, max_tokens: int = 2000, sim: Optional[Any] = None) -> str:
    """Call Claude API or return simulation stub when no API key is set."""
    if not _is_live():
        return json.dumps(sim) if sim is not None else json.dumps({"_simulation": True, "note": "Set ANTHROPIC_API_KEY for live AI"})
    from anthropic import Anthropic
    client = Anthropic(api_key=_ANTHROPIC_KEY)
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _parse_json_response(raw: str) -> Any:
    """Best-effort JSON parse from LLM output."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw": raw, "_parse_error": True}


def _meta(agent: str, requires_review: bool = False, sources: Optional[List] = None) -> Dict:
    return {
        "agent": agent,
        "simulation": not _is_live(),
        "requires_human_review": requires_review,
        "sources": sources or [],
        "model": _MODEL,
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _ok(agent: str, data: Any, *, requires_review: bool = False, sources: Optional[List] = None) -> Dict:
    return {"data": data, "meta": _meta(agent, requires_review=requires_review, sources=sources)}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "live_ai": _is_live(),
        "model": _MODEL,
        "graph_rag": _engine._GRAPH is not None,
        "agents": list(_engine.AGENTS.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "anthropic": _is_live(),
            "neo4j": _engine._GRAPH is not None,
            "airtable": bool(os.getenv("AIRTABLE_API_KEY")),
        },
    }


# ---------------------------------------------------------------------------
# News Feed — public RSS aggregator
# ---------------------------------------------------------------------------

import urllib.request
import xml.etree.ElementTree as ET
import html as _html

_RSS_SOURCES = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters World",    "https://feeds.reuters.com/reuters/worldNews"),
    ("BBC Business",     "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("CNBC",             "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
]

def _fetch_rss(url: str, source_name: str, limit: int = 8) -> list:
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AEGIS/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            root = ET.fromstring(r.read())
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for item in (root.iter("item") or root.iter("{http://www.w3.org/2005/Atom}entry")):
            title_el = item.find("title")
            link_el  = item.find("link")
            desc_el  = item.find("description") or item.find("summary")
            date_el  = item.find("pubDate") or item.find("updated")
            title = _html.unescape(title_el.text or "") if title_el is not None else ""
            link  = link_el.text or (link_el.get("href", "") if link_el is not None else "")
            desc  = _html.unescape(desc_el.text or "") if desc_el is not None else ""
            # strip any html tags from desc
            import re
            desc = re.sub(r"<[^>]+>", "", desc).strip()[:300]
            if title:
                items.append({
                    "id": f"{source_name}_{len(items)}",
                    "title": title,
                    "description": desc,
                    "link": link,
                    "source": source_name,
                    "publishedAt": date_el.text if date_el is not None else "",
                })
            if len(items) >= limit:
                break
    except Exception:
        pass
    return items

@app.get("/api/news/feed")
def news_feed():
    all_items: list = []
    for name, url in _RSS_SOURCES:
        all_items.extend(_fetch_rss(url, name, limit=6))
    # Sort by source variety (round-robin interleave)
    from itertools import zip_longest
    buckets: dict = {}
    for it in all_items:
        buckets.setdefault(it["source"], []).append(it)
    interleaved = [
        x for x in [item for group in zip_longest(*buckets.values()) for item in group if item]
    ]
    return {"items": interleaved[:30], "sources": list(buckets.keys())}


# ---------------------------------------------------------------------------
# REGO Module — Macro Radar
# /api/research/*
# ---------------------------------------------------------------------------

class SignalImpactRequest(BaseModel):
    signal: str                              # Signal headline/text
    jurisdictions: List[str] = ["SG", "VN"]
    org_context: Optional[str] = None

class WhatIfRequest(BaseModel):
    signal: str
    levers: Dict[str, Any] = {}
    org_context: Optional[str] = None

class StakeholderMapRequest(BaseModel):
    regulation: str
    org: str

class RegLookupRequest(BaseModel):
    jurisdiction: str
    topic: Optional[str] = None
    context: Optional[str] = None

class JurisdictionCompareRequest(BaseModel):
    jurisdictions: List[str]
    dimensions: Optional[List[str]] = None
    context: Optional[str] = None


SYSTEM_RESEARCH = (
    "You are the Research Specialist for AEGIS, an AI-native strategic intelligence platform. "
    "You specialise in regulatory, jurisdictional, and macro intelligence for Southeast Asia. "
    "Always respond with valid JSON matching the schema requested. No markdown fences."
)


@app.post("/api/research/signal-impact")
def signal_impact(req: SignalImpactRequest):
    """REGO: impact assessment callout on a single regulatory signal."""
    juris = ", ".join(req.jurisdictions)
    prompt = (
        f"GRC analyst. Assess the institutional impact of the following regulatory signal "
        f"for organisations operating in {juris}.\n\n"
        f"Signal: {req.signal}\n"
        f"Org context: {req.org_context or 'SG/VN fintech'}\n\n"
        f"Return JSON: {{\"impact_summary\": \"2-3 sentence sharp institutional assessment\", "
        f"\"risk_level\": \"CRITICAL|HIGH|MEDIUM|LOW\", "
        f"\"jurisdictions_affected\": [\"...\"], "
        f"\"recommended_action\": \"Escalate|Act|Monitor|Investigate\", "
        f"\"sources\": [\"...\"] }}"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt, sim={
        "impact_summary": f"[SIMULATION] Regulatory signal '{req.signal[:60]}...' presents elevated compliance risk for organisations in {', '.join(req.jurisdictions)}. Immediate review of exposure is recommended.",
        "risk_level": "HIGH",
        "jurisdictions_affected": req.jurisdictions,
        "recommended_action": "Escalate",
        "sources": ["AEGIS Simulation Mode — connect ANTHROPIC_API_KEY for live analysis"],
    })
    data = _parse_json_response(raw)
    return _ok("research", data)


@app.post("/api/research/what-if")
def what_if_simulation(req: WhatIfRequest):
    """REGO: What-If Simulation panel — simulate regulatory scenario variance."""
    levers_str = json.dumps(req.levers) if req.levers else "default levers"
    prompt = (
        f"You are a regulatory scenario simulator for a Southeast Asian professional services firm.\n"
        f"Signal: {req.signal}\n"
        f"Levers applied: {levers_str}\n"
        f"Org context: {req.org_context or 'SG/VN fintech'}\n\n"
        f"Simulate the downstream regulatory and business impact. Return JSON:\n"
        f"{{\"scenario_name\": \"evocative name\","
        f"\"headline\": \"1 sentence outcome\","
        f"\"probability\": 0-100,"
        f"\"timeline\": \"e.g. Q3 2026\","
        f"\"impact_areas\": [{{\"area\": \"...\", \"impact\": \"HIGH|MED|LOW\", \"note\": \"...\"}}],"
        f"\"recommended_posture\": \"Act|Monitor|Hedge|Avoid\","
        f"\"confidence\": \"Low|Medium|High\"}}"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt, sim={
        "scenario_name": "Regulatory Acceleration Scenario",
        "headline": f"[SIMULATION] '{req.signal[:50]}' triggers accelerated compliance requirements across SEA markets.",
        "probability": 65,
        "timeline": "Q3–Q4 2026",
        "impact_areas": [
            {"area": "Compliance", "impact": "HIGH", "note": "Mandatory framework updates within 90 days"},
            {"area": "Operations", "impact": "MED", "note": "Process redesign required for affected business lines"},
            {"area": "Capital", "impact": "MED", "note": "Estimated 3–5% increase in compliance spend"},
        ],
        "recommended_posture": "Hedge",
        "confidence": "Medium",
    })
    data = _parse_json_response(raw)
    return _ok("research", data)


@app.post("/api/research/stakeholder-map")
def stakeholder_map(req: StakeholderMapRequest):
    """REGO: generate a prioritised stakeholder engagement map for a regulation."""
    prompt = (
        f"GR strategist for Southeast Asia. For regulation: \"{req.regulation}\", "
        f"org: \"{req.org}\", list 5 key stakeholder meetings needed.\n"
        f"Return ONLY JSON: [{{"
        f"\"priority\": 1, \"name\": \"\", \"role\": \"\", "
        f"\"why\": \"1 sentence\", \"when\": \"\", "
        f"\"approach\": \"1 sentence\", "
        f"\"urgency\": \"critical|high|medium|low\"}}]"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt, sim=[
        {"priority": 1, "name": "MAS Director of Markets", "role": "Regulator", "why": "Primary approval authority for new regulatory framework", "when": "Within 2 weeks", "approach": "Position as early adopter supporting regulatory clarity", "urgency": "critical"},
        {"priority": 2, "name": "SBV Deputy Governor", "role": "Central Bank", "why": "Cross-border coordination and VN implementation timeline", "when": "Within 3 weeks", "approach": "Share implementation roadmap and compliance gap analysis", "urgency": "high"},
        {"priority": 3, "name": "FATF Secretariat Lead", "role": "International Body", "why": "Framework alignment and mutual recognition pathway", "when": "Within 4 weeks", "approach": "Technical briefing on compliance architecture", "urgency": "high"},
        {"priority": 4, "name": "Industry Association Chair", "role": "Peer Group", "why": "Coalition building for collective advocacy position", "when": "Within 2 weeks", "approach": "Joint working group proposal", "urgency": "medium"},
        {"priority": 5, "name": "Ministry of Finance Liaison", "role": "Government", "why": "Budget and policy coordination at national level", "when": "Within 5 weeks", "approach": "Submit position paper with cost-benefit analysis", "urgency": "medium"},
    ])
    data = _parse_json_response(raw)
    return _ok("research", data)


@app.post("/api/research/regulatory-lookup")
def regulatory_lookup(req: RegLookupRequest):
    """REGO / general: regulatory overview for a jurisdiction + topic."""
    prompt = (
        f"Provide a regulatory overview for {req.jurisdiction}"
        + (f" on topic: {req.topic}" if req.topic else "")
        + (f". Context: {req.context}" if req.context else "")
        + f"\n\nReturn JSON: {{\"overview\": \"...\", \"key_regulations\": [\"...\"], "
          f"\"risk_level\": \"HIGH|MEDIUM|LOW\", \"recent_developments\": [\"...\"], "
          f"\"sources\": [\"...\"]}}"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt, sim={
        "overview": f"[SIMULATION] {req.jurisdiction} regulatory environment for {req.topic or 'general financial services'}: Active framework with recent updates. Enforcement trend is upward.",
        "key_regulations": ["Primary Act 2024", "Subsidiary Circular 03/2025", "FATF Implementation Decree"],
        "risk_level": "MEDIUM",
        "recent_developments": ["Q1 2026 consultation paper released", "Enforcement action against 2 non-compliant entities"],
        "sources": ["AEGIS Simulation — connect API key for live data"],
    })
    data = _parse_json_response(raw)
    return _ok("research", data)


@app.post("/api/research/jurisdiction-compare")
def jurisdiction_compare(req: JurisdictionCompareRequest):
    """REGO: Compare multiple jurisdictions across requested dimensions."""
    juris_str = ", ".join(req.jurisdictions)
    dims = ", ".join(req.dimensions) if req.dimensions else "cost, tax, substance, banking access, FATF status, timeline"
    juris_cols = ", ".join('"{}": "..."'.format(j) for j in req.jurisdictions)
    prompt = (
        f"Compare jurisdictions: {juris_str}.\nDimensions: {dims}.\n"
        + (f"Context: {req.context}" if req.context else "")
        + f"\n\nReturn JSON: {{\"comparison_table\": [{{\"dimension\": \"...\", "
          f"{juris_cols}}}], "
          f"\"recommendation\": \"...\", \"confidence\": \"Low|Medium|High\"}}"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt)
    data = _parse_json_response(raw)
    return _ok("research", data)


class RiskProjectionRequest(BaseModel):
    domain: str                              # e.g. "CBDC", "Stablecoin"
    jurisdictions: List[str] = ["VN", "SG", "TH", "MY", "ID", "PH"]


@app.post("/api/research/risk-projection")
def risk_projection(req: RiskProjectionRequest):
    """REGO: per-jurisdiction current vs projected risk scores for a domain (chart data)."""
    juris = ", ".join(req.jurisdictions)
    prompt = (
        f"For regulatory domain \"{req.domain}\", give current vs projected (12-month) "
        f"regulatory-risk scores (0-100) for jurisdictions: {juris}.\n"
        f"Return ONLY a JSON array: "
        f"[{{\"j\": \"VN\", \"current\": 70, \"projected\": 85}}, ...]. "
        f"Adjust numbers to reflect domain reality."
    )
    sim_scores = [{"j": j, "current": 55 + i * 7, "projected": 62 + i * 7} for i, j in enumerate(req.jurisdictions)]
    raw = _call_claude(SYSTEM_RESEARCH, prompt, max_tokens=800, sim=sim_scores)
    data = _parse_json_response(raw)
    if not isinstance(data, list):
        data = sim_scores
    return _ok("research", data)


# ---------------------------------------------------------------------------
# REGO / Drafting — Advocacy Brief
# ---------------------------------------------------------------------------

class AdvocacyBriefRequest(BaseModel):
    org: str
    regulation: str
    stakeholder_name: str
    stakeholder_role: str
    why: str

SYSTEM_DRAFTING = (
    "You are the Drafting Agent for AEGIS. You produce sharp, institutional-quality "
    "advocacy and engagement documents. Be concise, specific, and action-oriented."
)

@app.post("/api/drafting/advocacy-brief")
def advocacy_brief(req: AdvocacyBriefRequest):
    """REGO: generate advocacy meeting brief for a specific stakeholder."""
    prompt = (
        f"Advocacy meeting brief.\n"
        f"Org: {req.org}\nReg: {req.regulation}\n"
        f"With: {req.stakeholder_name} ({req.stakeholder_role})\nWhy: {req.why}\n\n"
        f"Return JSON: {{\"talking_points\": [\"...\", \"...\", \"...\"], "
        f"\"framing\": \"1 sentence\", "
        f"\"red_lines\": \"what not to say\", "
        f"\"follow_up\": \"next action\", "
        f"\"tone\": \"sharp and institutional\"}}"
    )
    raw = _call_claude(SYSTEM_DRAFTING, prompt, max_tokens=1000, sim={
        "talking_points": [
            f"[SIMULATION] {req.org} is proactively aligning with {req.regulation} ahead of enforcement deadlines, demonstrating institutional commitment to regulatory leadership.",
            f"Our proposed implementation framework reduces systemic risk while maintaining operational agility — a win-win for both regulator and market participants.",
            f"We request a 90-day consultation window to submit detailed compliance roadmap and technical specification.",
        ],
        "framing": "Position as a constructive partner, not a compliance subject.",
        "red_lines": "Do not pre-commit to timelines without board approval. Avoid discussing competitor non-compliance.",
        "follow_up": "Submit written position paper within 7 days of meeting.",
        "tone": "Institutional, collaborative, action-oriented",
    })
    data = _parse_json_response(raw)
    return _ok("drafting", data, requires_review=True)


# ---------------------------------------------------------------------------
# VRIT Module — Local Intel (Vietnam / SEA)
# /api/compliance/local-intel
# ---------------------------------------------------------------------------

class LocalIntelRequest(BaseModel):
    entity: str
    jurisdiction: str = "VN"
    topics: Optional[List[str]] = None  # e.g. ["CBDC","fintech","AML"]
    org_context: Optional[str] = None

SYSTEM_COMPLIANCE = (
    "You are the Compliance + Research Agent for AEGIS, specialising in Vietnam and SEA "
    "hyper-local regulatory intelligence. You are rigorous, cite specific instruments, "
    "and never auto-approve compliance concerns. Return valid JSON only, no markdown."
)

@app.post("/api/compliance/local-intel")
def local_intel(req: LocalIntelRequest):
    """VRIT: hyper-local regulatory intelligence + compliance screening for an entity / topic."""
    topics_str = ", ".join(req.topics) if req.topics else "general regulatory landscape"
    prompt = (
        f"Provide hyper-local regulatory intelligence for {req.jurisdiction}.\n"
        f"Entity: {req.entity}\nTopics: {topics_str}\n"
        + (f"Org context: {req.org_context}" if req.org_context else "")
        + f"\n\nReturn JSON: {{"
          f"\"regulatory_summary\": \"2-3 sentence overview\","
          f"\"key_instruments\": [{{\"name\": \"...\", \"status\": \"Active|Draft|Pending\", \"impact\": \"HIGH|MED|LOW\", \"note\": \"...\"}}],"
          f"\"compliance_flags\": [{{\"flag\": \"...\", \"severity\": \"CRITICAL|HIGH|MEDIUM\", \"requires_review\": true}}],"
          f"\"risk_level\": \"CRITICAL|HIGH|MEDIUM|LOW\","
          f"\"recommended_actions\": [\"...\"],"
          f"\"requires_human_review\": true}}"
    )
    raw = _call_claude(SYSTEM_COMPLIANCE, prompt, sim={
        "regulatory_summary": f"[SIMULATION] {req.jurisdiction} regulatory landscape for {req.entity}: Active compliance obligations under primary fintech framework with recent amendments. Risk level is elevated due to pending MAS/SBV circulars.",
        "key_instruments": [
            {"name": "Primary Fintech Regulation 2025", "status": "Active", "impact": "HIGH", "note": "Mandatory licensing and capital requirements apply"},
            {"name": "AML/CFT Circular 03/2026", "status": "Active", "impact": "HIGH", "note": "Enhanced due diligence for digital asset entities"},
            {"name": "Draft Circular on Cross-Border Payments", "status": "Draft", "impact": "MED", "note": "Open consultation closes Q3 2026"},
        ],
        "compliance_flags": [
            {"flag": "AML/KYC framework requires annual audit submission", "severity": "HIGH", "requires_review": True},
            {"flag": "Cross-border transfer reporting threshold changed Q1 2026", "severity": "MEDIUM", "requires_review": True},
        ],
        "risk_level": "HIGH",
        "recommended_actions": [
            "Engage compliance counsel to review current AML/KYC documentation",
            "Submit regulatory update memo to board within 30 days",
            "Register for regulator consultation on draft circular",
        ],
        "requires_human_review": True,
    })
    data = _parse_json_response(raw)
    requires_review = data.get("requires_human_review", True) if isinstance(data, dict) else True
    return _ok("compliance", data, requires_review=requires_review)


@app.post("/api/compliance/sanctions-screen")
def sanctions_screen_endpoint(entity: str, directors: Optional[str] = None):
    """VRIT / general: sanctions + PEP + adverse media screen."""
    prompt = (
        f"Screen the following for sanctions, PEP and adverse media: {entity}"
        + (f". Also screen directors: {directors}." if directors else "")
        + f"\n\nReturn JSON: {{\"entity\": \"{entity}\","
          f"\"sanctions_hit\": false, \"pep_hit\": false, \"adverse_media_hit\": false,"
          f"\"risk_rating\": \"CLEAR|LOW|MEDIUM|HIGH|BLOCKED\","
          f"\"flags\": [\"...\"], \"requires_human_review\": true,"
          f"\"summary\": \"1 sentence conclusion\"}}"
    )
    raw = _call_claude(SYSTEM_COMPLIANCE, prompt)
    data = _parse_json_response(raw)
    requires_review = data.get("requires_human_review", True) if isinstance(data, dict) else True
    return _ok("compliance", data, requires_review=requires_review)


@app.post("/api/compliance/ubo-traverse")
def ubo_traverse_endpoint(entity: str, depth: int = 3):
    """VRIT / general: traverse UBO chain and flag conflicts."""
    prompt = (
        f"Map the Ultimate Beneficial Owner (UBO) chain for {entity} to depth {depth}. "
        f"Flag any conflicts of interest.\n\n"
        f"Return JSON: {{\"entity\": \"{entity}\","
        f"\"ubo_chain\": [{{\"level\": 1, \"name\": \"...\", \"ownership_pct\": 0, \"flags\": []}}],"
        f"\"conflicts\": [\"...\"], \"risk_rating\": \"CLEAR|LOW|MEDIUM|HIGH\","
        f"\"requires_human_review\": true}}"
    )
    raw = _call_claude(SYSTEM_COMPLIANCE, prompt)
    data = _parse_json_response(raw)
    return _ok("compliance", data, requires_review=True)


# ---------------------------------------------------------------------------
# EIT1 Module — Newsfeed / Intelligence Ingestion Pipeline
# /api/operations/*
#
# Pipeline stages (matches frontend PIPELINE_STAGES):
#   s1 ingest → s2 categorize → s3 verify → s4 score → s5 synthesize → done
#
# Two modes:
#   POST /api/operations/ingest             → JSON (non-streaming, ~20 cards)
#   POST /api/operations/ingest/stream      → SSE  (stage-by-stage events)
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    mode: str = "keywords"          # keywords | scrape | upload
    input: str                      # topics / URLs / CSV rows
    org_profile: Optional[Dict[str, Any]] = None
    decision_mode: str = "manual"   # auto | manual

class ReportGenerateRequest(BaseModel):
    report_type: str                # Trend Outlook | Risk Brief | IC Note | Sector Deep Dive
    signal: Optional[Dict[str, Any]] = None
    card_title: Optional[str] = None
    org_profile: Optional[Dict[str, Any]] = None

SYSTEM_OPERATIONS = (
    "You are the Operations + Intelligence Agent for AEGIS. You ingest, triage, and synthesise "
    "regulatory and market signals for institutional intelligence teams in Southeast Asia. "
    "Always return valid JSON matching the requested schema. No markdown fences."
)

SYSTEM_EA = (
    "You are the Executive Assistant for AEGIS. You synthesise specialist agent outputs "
    "into structured executive intelligence products — investment committee notes, "
    "trend outlooks, risk briefs. Be institutional, precise, and action-oriented. "
    "Return valid JSON only."
)


def _build_org_ctx(profile: Optional[Dict]) -> str:
    if not profile:
        return "Org: AEGIS Client. Sectors: fintech, financial services. Geo: Vietnam, SEA. Risk: Moderate."
    return (
        f"Org: {profile.get('name', '?')}. "
        f"Sectors: {', '.join((profile.get('sectors') or [])[:4])}. "
        f"Geo: {', '.join((profile.get('geos') or profile.get('geo', ['SEA']))[:3])}. "
        f"Risk: {profile.get('risk_appetite') or profile.get('risk', 'Moderate')}."
    )


class VerifyOrgRequest(BaseModel):
    name: str


@app.post("/api/research/verify-org")
def verify_org(req: VerifyOrgRequest):
    """EIT1 onboarding: verify/enrich an organisation name (autocomplete)."""
    prompt = (
        f"Verify and enrich the organisation: \"{req.name}\".\n"
        f"Return JSON: {{\"found\": true, \"name\": \"...\", \"type\": \"...\", "
        f"\"country\": \"...\", \"regulator\": \"...\", \"note\": \"1 short note\"}}"
    )
    raw = _call_claude(SYSTEM_RESEARCH, prompt, max_tokens=400, sim={
        "found": True, "name": req.name, "type": "Financial Institution",
        "country": "Vietnam", "regulator": "SBV / SSC",
        "note": "[SIMULATION] Organisation profile generated — connect API key for verified data",
    })
    data = _parse_json_response(raw)
    return _ok("research", data)


_SIM_CARDS = [
    {"id":"s1","headline":"SBV Signals Accelerated CBDC Pilot to 5 Commercial Banks","source":"Reuters Asia","sourceType":"wire","category":"REGULATORY","summary":"The State Bank of Vietnam has informally signaled intent to broaden its CBDC pilot beyond MB Bank to include BIDV, VietinBank, Techcombank and VPBank by Q3 2026. Infrastructure readiness assessments are underway.","rawCredibility":88,"impactScore":92,"suggestedAction":"Escalate","date":"Today 08:14","priority":"high","keyRisks":["Regulatory sequencing risk","Interoperability friction"],"synthesis":"Vietnam CBDC expansion is a structural shift in financial infrastructure."},
    {"id":"s2","headline":"Vietnam Q1 2026 FDI Inflows Surge 34% YoY — Tech & Manufacturing Lead","source":"MPI Report","sourceType":"gov","category":"MACRO","summary":"FDI commitments reached USD 8.4B in Q1 2026 with semiconductor supply chain relocation from China accounting for 41% of registered capital. South Korean and Taiwanese investors dominate.","rawCredibility":91,"impactScore":85,"suggestedAction":"Act","date":"Today 07:50","priority":"high","keyRisks":["Infrastructure bottlenecks","Power grid constraints"],"synthesis":"Headline FDI may overstate actual disbursed capital — tracking ratio at ~62%."},
    {"id":"s3","headline":"MiCA Phase 2 Stablecoin Provisions Effective June 30 — EU Enforcement Active","source":"ECB Bulletin","sourceType":"gov","category":"REGULATORY","summary":"European Central Bank confirms Phase 2 MiCA provisions for stablecoins become enforceable June 30. Issuers must hold 30% reserves in EU-domiciled accounts and file monthly attestations.","rawCredibility":95,"impactScore":88,"suggestedAction":"Act","date":"Today 09:00","priority":"high","keyRisks":["Reserve segregation cost","Monthly reporting burden"],"synthesis":"MiCA Phase 2 creates compliance cliff for non-EU stablecoin issuers operating in European markets."},
    {"id":"s4","headline":"Fed Signals 2 Additional Cuts H2 2026 — EM Capital Flow Reversal","source":"Bloomberg","sourceType":"wire","category":"MACRO","summary":"Federal Reserve minutes confirmed a dovish tilt with two 25bp cuts projected for Q3 and Q4 2026. VN-Index historically showing +8–12% sensitivity to Fed easing cycles.","rawCredibility":95,"impactScore":80,"suggestedAction":"Act","date":"Today 09:02","priority":"high","keyRisks":["USD weakening","Hot money volatility"],"synthesis":"Fed easing opens EM re-rating window with 60–90 day lag in Vietnam markets."},
    {"id":"s5","headline":"FATF Travel Rule Enforcement Deadline — 30 Days Remaining","source":"FATF Secretariat","sourceType":"gov","category":"REGULATORY","summary":"FATF Plenary confirmed Travel Rule enforcement against non-compliant VASPs begins in 30 days. Jurisdictions without compliant frameworks face grey-listing risk.","rawCredibility":97,"impactScore":94,"suggestedAction":"Escalate","date":"Today 10:00","priority":"high","keyRisks":["Grey-listing exposure","Correspondent banking risk"],"synthesis":"Travel Rule deadline is a compliance cliff — immediate gap assessment required for any VASP exposure."},
    {"id":"s6","headline":"SSC Crypto Licensing: 3 Advance, 12 Rejected in Round One","source":"Decision 96/QĐ-BTC","sourceType":"gov","category":"REGULATORY","summary":"Vietnam's SSC advanced 3 crypto exchange applications to final review while rejecting 12 for inadequate AML/KYC infrastructure. Licensed operators expected by Q4 2026.","rawCredibility":89,"impactScore":70,"suggestedAction":"Act","date":"Yesterday 16:00","priority":"high","keyRisks":["Licensing delay","Grey zone operators"],"synthesis":"SSC may face political pressure to license a state-affiliated entity preferentially."},
    {"id":"s7","headline":"Microsoft Azure USD 2.1B Vietnam Data Center Confirmed","source":"Microsoft PR","sourceType":"research","category":"TECHNOLOGY","summary":"Microsoft confirmed a USD 2.1B data center investment in Hà Nam province expected to accelerate cloud adoption across FSI, government and healthcare sectors.","rawCredibility":93,"impactScore":71,"suggestedAction":"Monitor","date":"Yesterday 14:00","priority":"moderate","keyRisks":["EVN grid reliability","Land clearance delays"],"synthesis":"Investment may be driven primarily by US diplomatic optics."},
    {"id":"s8","headline":"SBV Draft Circular 02/2026 — Public Consultation Closes May 25","source":"SBV Portal","sourceType":"gov","category":"REGULATORY","summary":"SBV released Draft Circular 02/2026 for open consultation covering digital payment infrastructure requirements. Deadline May 25. Institutions required to submit compliance gap assessments.","rawCredibility":92,"impactScore":76,"suggestedAction":"Act","date":"Today 06:30","priority":"high","keyRisks":["Short consultation window","Implementation timeline unclear"],"synthesis":"Draft Circular 02/2026 signals SBV's intent to accelerate digital payment standardisation in H2 2026."},
]


@app.post("/api/operations/ingest")
def ingest(req: IngestRequest):
    """EIT1: run full ingestion + synthesis pipeline, return 8 signal cards."""
    org = _build_org_ctx(req.org_profile)
    prompt = (
        f"Topics/Input: \"{req.input}\"\n{org}\n\n"
        f"Generate 8 realistic 2026 intelligence signals for an institutional newsfeed. "
        f"Return JSON: [{{\"id\": \"s1\", \"headline\": \"...\", "
        f"\"source\": \"...\", \"sourceType\": \"wire|gov|blog|social|research\", "
        f"\"category\": \"MACRO|REGULATORY|GEOPOLITICAL|SECTOR|CREDIT|COMMODITY|TECHNOLOGY|ESG\", "
        f"\"summary\": \"2-3 sentence synthesis\", \"rawCredibility\": 0-100, "
        f"\"impactScore\": 0-100, \"suggestedAction\": \"Escalate|Act|Monitor|Investigate\", "
        f"\"date\": \"e.g. Today 08:14\", \"priority\": \"high|moderate|monitoring\"}}]"
    )
    raw = _call_claude(SYSTEM_OPERATIONS, prompt, max_tokens=3000, sim=_SIM_CARDS)
    cards = _parse_json_response(raw)
    if not isinstance(cards, list):
        cards = _SIM_CARDS
    return _ok("operations", {"cards": cards, "count": len(cards), "decision_mode": req.decision_mode})


async def _ingest_sse_generator(req: IngestRequest):
    """Yield SSE events matching frontend PipelineMonitor stages."""
    org = _build_org_ctx(req.org_profile)

    def sse(event_type: str, payload: Any) -> str:
        return f"data: {json.dumps({'type': event_type, **payload})}\n\n"

    yield sse("stage", {"stage": "ingest", "log": "Initializing signal acquisition...", "progress": 0.05})
    await asyncio.sleep(0.3)

    # Stage 1: ingest
    ingest_prompt = (
        f"Topics: \"{req.input}\"\n{org}\n\n"
        f"Generate 8 intelligence signals. Return JSON array: "
        f"[{{\"id\": \"s1\", \"headline\": \"...\", \"source\": \"...\", "
        f"\"sourceType\": \"wire|gov|blog|social|research\", "
        f"\"category\": \"MACRO|REGULATORY|GEOPOLITICAL|SECTOR|CREDIT|COMMODITY|TECHNOLOGY|ESG\", "
        f"\"summary\": \"...\", \"rawCredibility\": 85, \"date\": \"Today\"}}]"
    )
    raw_items = _call_claude(SYSTEM_OPERATIONS, ingest_prompt, max_tokens=2500, sim=_SIM_CARDS)
    items = _parse_json_response(raw_items)
    if not isinstance(items, list):
        items = _SIM_CARDS
    yield sse("stage", {"stage": "ingest", "log": f"✓ {len(items)} signals ingested", "progress": 0.25})

    # Stage 2: categorize
    yield sse("stage", {"stage": "categorize", "log": "Categorising and tagging signals...", "progress": 0.40})
    for it in items:
        yield sse("log", {"log": f"  [{it.get('category', '?')}] {str(it.get('headline', ''))[:48]}..."})
    await asyncio.sleep(0.2)

    # Stage 3: verify + credibility filter
    yield sse("stage", {"stage": "verify", "log": "Verifying credibility scores...", "progress": 0.55})
    verified = [it for it in items if (it.get("rawCredibility") or 0) >= 60]
    yield sse("stage", {"stage": "verify", "log": f"✓ {len(verified)} signals pass credibility gate", "progress": 0.65})

    # Stage 4: score + synthesize
    yield sse("stage", {"stage": "score", "log": "Running impact scoring + synthesis...", "progress": 0.75})
    score_prompt = (
        f"You have {len(verified)} raw signals. For each, add: impactScore (0-100), "
        f"suggestedAction (Escalate|Act|Monitor|Investigate), priority (high|moderate|monitoring), "
        f"keyRisks ([...]), synthesis (2 sentence institutional summary).\n"
        f"Signals: {json.dumps(verified[:8])}\n\n"
        f"Return the same JSON array with these fields added. No other output."
    )
    raw_scored = _call_claude(SYSTEM_OPERATIONS, score_prompt, max_tokens=3000)
    scored = _parse_json_response(raw_scored)
    if not isinstance(scored, list):
        scored = verified  # fallback to unscored if parse fails
    yield sse("stage", {"stage": "score", "log": f"✓ Scored {len(scored)} cards", "progress": 0.90})

    # Done
    yield sse("result", {
        "data": {
            "cards": scored,
            "count": len(scored),
            "decision_mode": req.decision_mode,
        },
        "meta": _meta("operations"),
    })
    yield sse("done", {"log": f"Pipeline complete — {len(scored)} cards ready", "progress": 1.0})


@app.post("/api/operations/ingest/stream")
async def ingest_stream(req: IngestRequest):
    """EIT1: SSE streaming pipeline — feeds PipelineMonitor stage-by-stage."""
    return StreamingResponse(
        _ingest_sse_generator(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/operations/report-generate")
def report_generate(req: ReportGenerateRequest):
    """EIT1 Reports tab: generate AI analysis for a report card (IC Note, Trend Outlook, etc.)."""
    org = _build_org_ctx(req.org_profile)
    signal_ctx = req.signal.get("synthesis", "") if req.signal else ""
    signal_title = req.signal.get("title", "") if req.signal else (req.card_title or "")
    prompt = (
        f"{req.report_type} for investment committee.\n"
        f"Signal: {signal_title}\nContext: {signal_ctx}\nOrg profile: {org}\n\n"
        f"Return JSON: {{\"executive_summary\": \"...\", \"outlook\": \"...\", "
        f"\"investment_implications\": [\"...\"], \"risks\": [\"...\"], "
        f"\"recommended_posture\": \"Overweight|Neutral|Underweight|Hedge|Avoid\", "
        f"\"confidence\": \"Low|Medium|High\", \"next_steps\": [\"...\"]}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=1500, sim={
        "executive_summary": f"[SIMULATION] {req.report_type} for '{signal_title or 'Selected Signal'}': Elevated institutional risk with near-term compliance action required. Connect ANTHROPIC_API_KEY for full AI analysis.",
        "outlook": "Market conditions suggest continued regulatory tightening across SEA jurisdictions through H2 2026, with Vietnam and Singapore driving the policy agenda.",
        "investment_implications": ["Overweight compliance-ready fintech infrastructure", "Monitor regulatory timeline for portfolio companies", "Review cross-border exposure under new frameworks"],
        "risks": ["Regulatory sequencing delays", "Enforcement action against early movers", "Capital requirement increases"],
        "recommended_posture": "Hedge",
        "confidence": "Medium",
        "next_steps": ["Brief investment committee within 7 days", "Commission full legal review", "Engage regulatory counsel for position paper"],
    })
    data = _parse_json_response(raw)
    return _ok("ea", data, requires_review=True)


@app.post("/api/operations/report-assemble")
def report_assemble(report_type: str = "Trend Outlook", context: Optional[str] = None):
    """EIT1 / general: assemble a report from free-form context."""
    prompt = (
        f"Assemble a {report_type} report."
        + (f" Context: {context}" if context else "")
        + f"\n\nReturn JSON: {{\"title\": \"...\", \"summary\": \"...\", "
          f"\"sections\": [{{\"heading\": \"...\", \"body\": \"...\"}}], "
          f"\"recommendations\": [\"...\"], \"confidence\": \"Low|Medium|High\"}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2000)
    data = _parse_json_response(raw)
    return _ok("ea", data, requires_review=True)


# ---------------------------------------------------------------------------
# EIT2 Module — War Room (Financial Scenario Planning)
# /api/executive/*
#
# 4 sequential War Room calls:
#   1. POST /api/executive/scenarios       → bull/base/bear + plan_summary
#   2. POST /api/executive/next-steps      → action library (8-10 items)
#   3. POST /api/executive/simulate        → variance waterfall simulation
#   4. POST /api/executive/improvements    → gap-close improvement suggestions
# ---------------------------------------------------------------------------

class ScenariosRequest(BaseModel):
    business_plan: str
    org_profile: Optional[Dict[str, Any]] = None

class NextStepsRequest(BaseModel):
    business_plan: str
    org_profile: Optional[Dict[str, Any]] = None

class SimulateRequest(BaseModel):
    business_plan: str
    selected_scenario: str          # bull | base | bear
    scenario_data: Dict[str, Any]   # the scenario object from /scenarios
    selected_actions: List[Dict[str, Any]]
    org_profile: Optional[Dict[str, Any]] = None

class ImprovementsRequest(BaseModel):
    business_plan: str
    selected_scenario: str
    sim_result: Dict[str, Any]      # result from /simulate
    target_variance: float          # e.g. 90.0 (% plan adherence)
    conditions: Dict[str, str]      # {capital, pic, timeline}
    selected_steps: List[str]       # action IDs already selected
    org_profile: Optional[Dict[str, Any]] = None

class BriefRequest(BaseModel):
    topic: str
    prior_outputs: Optional[str] = None

class ScenarioRequest(BaseModel):
    business_plan: str
    scenario_type: str = "full"
    constraints: Optional[str] = None


@app.post("/api/executive/scenarios")
def executive_scenarios(req: ScenariosRequest):
    """EIT2: generate bull/base/bear scenarios from a business plan."""
    org = _build_org_ctx(req.org_profile)
    prompt = (
        f"Business Plan:\n{req.business_plan}\n\n{org}\n\n"
        f"Generate 3 scenario cases for next fiscal year rolling forecast. Return JSON:\n"
        f"{{\"bull\": {{\"name\": \"...\", \"probability\": 30, \"rationale\": \"...\","
        f"\"drivers\": [\"...\"], "
        f"\"metrics\": {{\"revenue\": \"...\", \"ebitda\": \"...\", \"vsplan\": \"+X%\", \"risk_adj\": \"...\"}}, "
        f"\"sparkline\": [8 quarterly revenue numbers], "
        f"\"keyAssumptions\": [\"...\"], \"macroTail\": \"...\"}}, "
        f"\"base\": {{same}}, "
        f"\"bear\": {{same}}, "
        f"\"plan_summary\": {{\"revenue_target\": \"...\", \"ebitda_target\": \"...\", \"key_kpis\": [\"...\"]}}}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2500, sim={
        "bull": {"name": "Breakout Growth", "probability": 25, "rationale": "[SIMULATION] Favourable macro tailwinds and regulatory clarity accelerate top-line growth beyond plan.", "drivers": ["Fed rate cuts boost EM inflows", "FTSE Russell upgrade confirmed", "Key licensing approvals fast-tracked"], "metrics": {"revenue": "+32% vs plan", "ebitda": "+28% vs plan", "vsplan": "+32%", "risk_adj": "VND 45B"}, "sparkline": [80, 88, 95, 105, 115, 125, 130, 140], "keyAssumptions": ["MAS sandbox approval in Q2", "VN market share gain +5pp", "No material FX headwind"], "macroTail": "Global liquidity surge drives EM re-rating"},
        "base": {"name": "Steady Execution", "probability": 55, "rationale": "[SIMULATION] Plan assumptions hold with moderate variance. Execution quality is the primary determinant.", "drivers": ["Regulatory timeline on schedule", "Organic growth in core markets", "Team capacity maintained"], "metrics": {"revenue": "+5% vs plan", "ebitda": "+3% vs plan", "vsplan": "+5%", "risk_adj": "VND 32B"}, "sparkline": [78, 82, 85, 90, 93, 97, 100, 103], "keyAssumptions": ["No adverse regulatory changes", "Team turnover below 15%", "FX stable within ±5%"], "macroTail": "Mild global slowdown absorbed by SEA domestic demand"},
        "bear": {"name": "Regulatory Headwind", "probability": 20, "rationale": "[SIMULATION] Compliance requirements tighten materially, increasing costs and delaying key milestones.", "drivers": ["SBV circular delays licensing", "AML/KYC audit triggers cost overrun", "FX headwind on USD revenue"], "metrics": {"revenue": "-18% vs plan", "ebitda": "-25% vs plan", "vsplan": "-18%", "risk_adj": "VND 18B"}, "sparkline": [75, 70, 65, 60, 62, 65, 68, 70], "keyAssumptions": ["Licensing delayed 6+ months", "Compliance cost +40%", "USD/VND at 26,500"], "macroTail": "Regional regulatory tightening wave hits SEA fintechs"},
        "plan_summary": {"revenue_target": "VND 120B", "ebitda_target": "VND 30B", "key_kpis": ["ARR growth 40%", "NPS > 60", "Compliance audit clean", "3 new jurisdictions"]},
    })
    data = _parse_json_response(raw)
    return _ok("ea", data)


@app.post("/api/executive/next-steps")
def executive_next_steps(req: NextStepsRequest):
    """EIT2: generate strategic action library (8-10 items) for variance management."""
    org = _build_org_ctx(req.org_profile)
    prompt = (
        f"Business Plan:\n{req.business_plan[:800]}\n\n{org}\n\n"
        f"Generate 8-10 strategic next-step actions for variance management. Return JSON:\n"
        f"[{{\"id\": \"a1\", \"category\": \"REVENUE|COST|RISK|OPERATIONS|PARTNERSHIPS\", "
        f"\"action\": \"short title\", \"description\": \"1-2 sentences\", "
        f"\"impact\": \"High|Medium|Low\", \"effort\": \"High|Medium|Low\", "
        f"\"timeline\": \"4-6 weeks\", \"capital\": \"VND 500M or null\"}}]"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2000, sim=[
        {"id":"a1","category":"REVENUE","action":"Accelerate Enterprise Sales Cycle","description":"Deploy dedicated enterprise account team to compress deal cycles from 90 to 45 days. Focus on top-10 pipeline opportunities.","impact":"High","effort":"Medium","timeline":"4-6 weeks","capital":"VND 800M"},
        {"id":"a2","category":"COST","action":"Renegotiate Cloud Infrastructure Contract","description":"Leverage volume growth to renegotiate AWS/GCP contracts. Target 20% cost reduction on compute spend.","impact":"Medium","effort":"Low","timeline":"2-3 weeks","capital":None},
        {"id":"a3","category":"RISK","action":"Regulatory Pre-Clearance Programme","description":"Engage MAS and SBV liaison counsel to pre-clear product roadmap against Q3 regulatory changes. Reduces surprise compliance costs.","impact":"High","effort":"Medium","timeline":"6-8 weeks","capital":"VND 500M"},
        {"id":"a4","category":"OPERATIONS","action":"Automate KYC/AML Pipeline","description":"Deploy ML-assisted KYC review to cut manual review time by 60%. Addresses compliance backlog and reduces headcount requirements.","impact":"High","effort":"High","timeline":"8-12 weeks","capital":"VND 2B"},
        {"id":"a5","category":"PARTNERSHIPS","action":"Strategic Distribution Partnership","description":"Formalise revenue-share arrangement with top-3 referring partners. Expected to add 15-20% to pipeline.","impact":"High","effort":"Low","timeline":"3-4 weeks","capital":None},
        {"id":"a6","category":"REVENUE","action":"Upsell Premium Tier to Top-20% Users","description":"Launch targeted premium upgrade campaign to highest-engagement user segment. Historical conversion rate 18-25%.","impact":"Medium","effort":"Low","timeline":"2-4 weeks","capital":"VND 200M"},
        {"id":"a7","category":"COST","action":"Consolidate Vendor Stack","description":"Eliminate 3 overlapping SaaS tools identified in IT audit. Projected saving VND 400M annually.","impact":"Medium","effort":"Low","timeline":"4-6 weeks","capital":None},
        {"id":"a8","category":"RISK","action":"FX Hedging Programme","description":"Establish 6-month rolling FX hedge on USD revenue exposure above VND 5B. Reduces earnings volatility.","impact":"Medium","effort":"Medium","timeline":"3-4 weeks","capital":"VND 300M"},
    ])
    data = _parse_json_response(raw)
    return _ok("ea", data)


@app.post("/api/executive/simulate")
def executive_simulate(req: SimulateRequest):
    """EIT2: simulate variance impact of selected actions on chosen scenario."""
    org = _build_org_ctx(req.org_profile)
    sc = req.scenario_data
    actions_str = json.dumps([{"action": a.get("action"), "impact": a.get("impact"), "capital": a.get("capital")} for a in req.selected_actions])
    prompt = (
        f"Scenario: {req.selected_scenario.upper()} CASE — {sc.get('name', '')}\n"
        f"Probability: {sc.get('probability', 50)}%\n"
        f"Scenario Metrics: {json.dumps(sc.get('metrics', {}))}\n"
        f"Plan: {req.business_plan[:500]}\n{org}\n"
        f"Selected Actions: {actions_str}\n\n"
        f"Simulate variance impact. Return JSON:\n"
        f"{{\"headline\": \"1 sentence outcome\","
        f"\"plan_quarterly\": [4 numbers summing to 100],"
        f"\"sim_quarterly\": [4 numbers summing to 100],"
        f"\"unit\": \"% of Annual Target\","
        f"\"variance_from_plan\": \"+/-X%\","
        f"\"variance_confidence\": \"Low|Medium|High\","
        f"\"adjusted_probability\": 0-100,"
        f"\"key_changes\": [\"3-4 changes\"],"
        f"\"residual_risks\": [\"2-3 risks\"],"
        f"\"feasible_plan\": \"1-2 sentence conclusion\","
        f"\"waterfall\": [{{\"label\": \"Base\", \"value\": 100, \"display\": \"100%\"}}, ..."
        f"{{\"label\": \"Result\", \"value\": 115, \"display\": \"115%\"}}]}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2000, sim={
        "headline": f"[SIMULATION] {req.selected_scenario.upper()} scenario with {len(req.selected_actions)} actions: projected +8% variance improvement vs base plan.",
        "plan_quarterly": [22, 25, 26, 27],
        "sim_quarterly": [20, 24, 28, 30],
        "unit": "% of Annual Target",
        "variance_from_plan": "+8%",
        "variance_confidence": "Medium",
        "adjusted_probability": 62,
        "key_changes": ["Enterprise sales acceleration +12% H2 uplift", "KYC automation reduces compliance cost 60%", "Partnership pipeline adds +15% addressable revenue", "FX hedge locks in USD 2.1M revenue floor"],
        "residual_risks": ["Regulatory timeline uncertainty persists", "Key hire dependency for enterprise sales", "Cloud migration risk in Q3"],
        "feasible_plan": "[SIMULATION] Selected actions are feasible within stated capital and timeline constraints. Connect ANTHROPIC_API_KEY for live simulation.",
        "waterfall": [
            {"label": "Base", "value": 100, "display": "100%"},
            {"label": "Sales+", "value": 112, "display": "+12%"},
            {"label": "Cost-", "value": 108, "display": "-4%"},
            {"label": "Partner+", "value": 115, "display": "+7%"},
            {"label": "Risk-", "value": 108, "display": "-7%"},
            {"label": "Result", "value": 108, "display": "108%"},
        ],
    })
    data = _parse_json_response(raw)
    return _ok("ea", data)


@app.post("/api/executive/improvements")
def executive_improvements(req: ImprovementsRequest):
    """EIT2: generate gap-close improvement suggestions to hit target variance."""
    org = _build_org_ctx(req.org_profile)
    steps_str = ", ".join(req.selected_steps)
    prompt = (
        f"Business Plan: {req.business_plan[:500]}\n{org}\n"
        f"Scenario: {req.selected_scenario.upper()} — {req.sim_result.get('headline', '')}\n"
        f"Current Variance from Plan: {req.sim_result.get('variance_from_plan', '0%')}\n"
        f"User Target Variance: {req.target_variance}% plan adherence\n"
        f"Constraints: Capital: {req.conditions.get('capital', 'N/A')}, "
        f"PIC Qualification: {req.conditions.get('pic', 'N/A')}, "
        f"Timeline: {req.conditions.get('timeline', 'N/A')}\n"
        f"Selected Actions: {steps_str}\n\n"
        f"Generate improvement suggestions to close the gap. Return JSON:\n"
        f"{{\"secured_variance\": 0-100,"
        f"\"feasibility_summary\": \"2 sentence statement\","
        f"\"improvements\": [{{\"title\": \"...\", "
        f"\"category\": \"REVENUE|COST|RISK|PROCESS|GOVERNANCE\","
        f"\"priority\": \"Critical|High|Medium\","
        f"\"description\": \"2 sentences\","
        f"\"variance_impact\": \"+X% improvement\","
        f"\"capital_required\": \"VND XM or Minimal\","
        f"\"timeline\": \"X weeks\","
        f"\"feasibility_score\": 0-100,"
        f"\"conditions_met\": true,"
        f"\"conditions\": [{{\"label\": \"...\", \"met\": true}}]}}]}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2500, sim={
        "secured_variance": 72,
        "feasibility_summary": "[SIMULATION] Selected improvement set closes approximately 72% of the target gap. Capital requirements are within stated constraints. Connect ANTHROPIC_API_KEY for live optimization.",
        "improvements": [
            {"title": "Revenue Acceleration Programme", "category": "REVENUE", "priority": "Critical", "description": "Deploy dedicated enterprise team with revised incentive structure. Compress deal cycles from 90 to 45 days targeting top-10 pipeline opportunities.", "variance_impact": "+8% improvement", "capital_required": "VND 800M", "timeline": "4 weeks", "feasibility_score": 85, "conditions_met": True, "conditions": [{"label": "Capital available", "met": True}, {"label": "Team headcount", "met": True}]},
            {"title": "Compliance Cost Reduction", "category": "COST", "priority": "High", "description": "Automate KYC/AML review pipeline using ML-assisted scoring. Reduces manual review by 60% and eliminates compliance backlog.", "variance_impact": "+6% improvement", "capital_required": "VND 2B", "timeline": "8 weeks", "feasibility_score": 72, "conditions_met": True, "conditions": [{"label": "Capital available", "met": True}, {"label": "Tech readiness", "met": False}]},
            {"title": "Partnership Revenue Activation", "category": "PARTNERSHIPS", "priority": "High", "description": "Formalise three strategic distribution partnerships. Historical channel partners contribute 15-20% incremental pipeline.", "variance_impact": "+5% improvement", "capital_required": "Minimal", "timeline": "3 weeks", "feasibility_score": 90, "conditions_met": True, "conditions": [{"label": "Agreements signed", "met": True}, {"label": "Onboarding ready", "met": True}]},
        ],
    })
    data = _parse_json_response(raw)
    return _ok("ea", data, requires_review=True)


@app.post("/api/executive/brief")
def executive_brief(req: BriefRequest):
    """General: synthesise prior outputs into an executive brief."""
    prior = f"\nPrior outputs:\n{req.prior_outputs}" if req.prior_outputs else ""
    prompt = (
        f"Prepare an executive brief on: {req.topic}{prior}\n\n"
        f"Return JSON: {{\"title\": \"...\", \"summary\": \"...\", "
        f"\"key_findings\": [\"...\"], \"recommendations\": [\"...\"], "
        f"\"risk_flags\": [\"...\"], \"confidence\": \"Low|Medium|High\"}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=1500, sim={
        "title": f"[SIMULATION] Executive Brief: {req.topic}",
        "summary": "AEGIS intelligence synthesis for executive review. Live AI analysis requires ANTHROPIC_API_KEY configuration on the backend.",
        "key_findings": ["Regulatory environment is tightening across SEA with 30-day FATF enforcement deadline", "Vietnam CBDC pilot expansion accelerates digital infrastructure timeline", "Fed easing cycle creates EM re-rating opportunity with 60-90 day lag"],
        "recommendations": ["Immediate: compliance gap assessment for FATF Travel Rule", "30-day: engage SBV regulatory liaison for CBDC positioning", "60-day: review EM portfolio allocation given Fed pivot"],
        "risk_flags": ["Grey-listing risk if FATF compliance not achieved by deadline", "Regulatory sequencing delays in Vietnam licensing pipeline"],
        "confidence": "Medium",
    })
    data = _parse_json_response(raw)
    return _ok("ea", data, requires_review=True)


@app.post("/api/executive/scenario")
def executive_scenario(req: ScenarioRequest):
    """General: full scenario analysis (non–War Room shorthand)."""
    prompt = (
        f"Run a {req.scenario_type} financial scenario analysis.\n\nBusiness plan:\n{req.business_plan}"
        + (f"\n\nConstraints: {req.constraints}" if req.constraints else "")
        + f"\n\nReturn JSON: {{\"scenarios\": {{\"bull\": {{...}}, \"base\": {{...}}, \"bear\": {{...}}}}}}"
    )
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2500)
    data = _parse_json_response(raw)
    return _ok("ea", data)


@app.post("/api/drafting/engagement-letter")
def engagement_letter(client_name: str, jurisdiction: str, service_type: str, context: Optional[str] = None):
    """Drafting Agent: engagement letter from approved template."""
    prompt = (
        f"Draft an engagement letter for {client_name} for {service_type} in {jurisdiction}."
        + (f" Context: {context}" if context else "")
        + f"\n\nReturn JSON: {{\"subject\": \"...\", \"salutation\": \"...\", "
          f"\"body_paragraphs\": [\"...\"], \"scope\": \"...\", "
          f"\"fee_structure\": \"...\", \"next_steps\": [\"...\"]}}"
    )
    raw = _call_claude(SYSTEM_DRAFTING, prompt, max_tokens=2000)
    data = _parse_json_response(raw)
    return _ok("drafting", data, requires_review=True)


# ---------------------------------------------------------------------------
# Static frontend (single-host deploy)
#
# When the AEGIS React app is built (frontend/aegis/dist), serve it at "/" so
# one URL hosts both the UI and the API. Mounted LAST so every /api/* route
# above takes precedence. Set AEGIS_STATIC_DIR to override the location.
# ---------------------------------------------------------------------------
_STATIC_DIR = os.getenv(
    "AEGIS_STATIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "aegis", "dist"),
)
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    logger.info("Serving AEGIS frontend from %s", _STATIC_DIR)
else:
    logger.info("No frontend build at %s — API-only mode", _STATIC_DIR)
