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


def _call_claude(system: str, user: str, max_tokens: int = 2000) -> str:
    if not _is_live():
        return json.dumps({"_simulation": True, "note": "Set ANTHROPIC_API_KEY for live AI"})
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt)
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt)
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt)
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt)
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt, max_tokens=800)
    data = _parse_json_response(raw)
    if not isinstance(data, list):
        data = []
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
    raw = _call_claude(SYSTEM_DRAFTING, prompt, max_tokens=1000)
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
    raw = _call_claude(SYSTEM_COMPLIANCE, prompt)
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
    raw = _call_claude(SYSTEM_RESEARCH, prompt, max_tokens=400)
    data = _parse_json_response(raw)
    return _ok("research", data)


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
    raw = _call_claude(SYSTEM_OPERATIONS, prompt, max_tokens=3000)
    cards = _parse_json_response(raw)
    if not isinstance(cards, list):
        cards = []
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
    raw_items = _call_claude(SYSTEM_OPERATIONS, ingest_prompt, max_tokens=2500)
    items = _parse_json_response(raw_items)
    if not isinstance(items, list):
        items = []
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=1500)
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2500)
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2000)
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2000)
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=2500)
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
    raw = _call_claude(SYSTEM_EA, prompt, max_tokens=1500)
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
