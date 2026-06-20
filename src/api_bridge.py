"""
AEGIS API Bridge — FastAPI thin wrapper over the Firm OS engine.

Connects the AEGIS React frontend (L6) to the Firm OS AI backend (L1–L5)
without modifying any existing engine logic. Each endpoint maps to one or
more Firm OS agents as specified in AEGIS_PRD_v2 §3.3.

Run:
    uvicorn src.api_bridge:app --host 0.0.0.0 --port 8000 --reload

CORS is open to localhost:5173 (Vite dev) and localhost:4173 (Vite preview).
"""

from __future__ import annotations

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path setup so we can import the existing engine from within src/
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as _engine

logger = logging.getLogger("aegis.bridge")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AEGIS API Bridge",
    description="Firm OS agent endpoints for the AEGIS React shell",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared Claude caller (mirrors app.py's _stream_claude, non-streaming)
# ---------------------------------------------------------------------------

def _call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return f"[SIMULATION] {user[:120]}…"
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _run_agent_stage(agent_id: str, user_prompt: str, prior: str = "") -> str:
    """Build pipeline for a single-agent request and call Claude."""
    pipeline = _engine.build_pipeline(user_prompt)
    target = next((s for s in pipeline if s.agent == agent_id), None)
    if target is None:
        # Fallback: build a minimal direct stage
        stage_map = {
            "research":   (_engine._user_prompt_research,    "You are the Research Specialist for AEGIS. Provide accurate, well-sourced regulatory and jurisdiction intelligence."),
            "compliance": (_engine._user_prompt_compliance,  "You are the Compliance Officer for AEGIS. Run rigorous AML/KYC checks and return structured results."),
            "drafting":   (_engine._user_prompt_drafting,    "You are the Drafting Agent for AEGIS. Draft professional documents from approved templates."),
            "operations": (_engine._user_prompt_operations,  "You are the Operations Agent for AEGIS. Surface renewals, deadlines and status reports."),
            "ea":         (lambda p: _engine._user_prompt_ea(p, prior), "You are the Executive Assistant for AEGIS. Synthesise specialist outputs into structured executive briefs."),
        }
        if agent_id not in stage_map:
            raise ValueError(f"Unknown agent: {agent_id}")
        prompt_fn, system = stage_map[agent_id]
        return _call_claude(system, prompt_fn(user_prompt))

    return _call_claude(target.system_prompt, _build_user_msg(target.agent, user_prompt, prior))


def _build_user_msg(agent: str, prompt: str, prior: str) -> str:
    if agent == "research":
        return _engine._user_prompt_research(prompt)
    if agent == "compliance":
        if any(k in prompt.lower() for k in ("ubo", "ownership", "beneficial")):
            return _engine._user_prompt_ubo(prompt)
        return _engine._user_prompt_compliance(prompt)
    if agent == "drafting":
        return _engine._user_prompt_drafting(prompt)
    if agent == "operations":
        return _engine._user_prompt_operations(prompt)
    if agent == "ea":
        return _engine._user_prompt_ea(prompt, prior)
    return _engine._user_prompt_classification(prompt)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegLookupRequest(BaseModel):
    jurisdiction: str
    topic: Optional[str] = None
    context: Optional[str] = None

class JurisdictionCompareRequest(BaseModel):
    jurisdictions: List[str]
    dimensions: Optional[List[str]] = None
    context: Optional[str] = None

class SanctionsScreenRequest(BaseModel):
    entity_name: str
    entity_type: Optional[str] = "company"
    directors: Optional[List[str]] = None

class UBORequest(BaseModel):
    entity_name: str
    depth: Optional[int] = 3

class NewsfeedRequest(BaseModel):
    org_profile: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 20

class ReportAssembleRequest(BaseModel):
    signal_ids: Optional[List[str]] = None
    report_type: Optional[str] = "Trend Outlook"
    context: Optional[str] = None

class ScenarioRequest(BaseModel):
    business_plan: str
    scenario_type: Optional[str] = "full"  # bull | base | bear | full
    constraints: Optional[str] = None

class BriefRequest(BaseModel):
    topic: str
    prior_outputs: Optional[str] = None

class EngagementLetterRequest(BaseModel):
    client_name: str
    jurisdiction: str
    service_type: str
    context: Optional[str] = None

class AgentResponse(BaseModel):
    agent: str
    output: str
    timestamp: str
    simulation: bool

def _resp(agent: str, output: str) -> AgentResponse:
    return AgentResponse(
        agent=agent,
        output=output,
        timestamp=datetime.utcnow().isoformat() + "Z",
        simulation=not bool(os.getenv("ANTHROPIC_API_KEY")),
    )

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    live = bool(os.getenv("ANTHROPIC_API_KEY"))
    graph_ok = _engine._GRAPH is not None
    return {
        "status": "ok",
        "live_ai": live,
        "graph_rag": graph_ok,
        "agents": list(_engine.AGENTS.keys()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

# ---------------------------------------------------------------------------
# Research endpoints → Research Agent
# ---------------------------------------------------------------------------

@app.post("/api/research/regulatory-lookup", response_model=AgentResponse)
def regulatory_lookup(req: RegLookupRequest):
    prompt = f"Provide a regulatory overview for {req.jurisdiction}"
    if req.topic:
        prompt += f" on the topic: {req.topic}"
    if req.context:
        prompt += f". Additional context: {req.context}"
    try:
        output = _run_agent_stage("research", prompt)
        return _resp("research", output)
    except Exception as e:
        logger.exception("regulatory-lookup error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research/jurisdiction-compare", response_model=AgentResponse)
def jurisdiction_compare(req: JurisdictionCompareRequest):
    juris_str = ", ".join(req.jurisdictions)
    dims = ", ".join(req.dimensions) if req.dimensions else "cost, tax, substance, banking access, FATF status"
    prompt = f"Compare {juris_str} across: {dims}."
    if req.context:
        prompt += f" Context: {req.context}"
    try:
        output = _run_agent_stage("research", prompt)
        return _resp("research", output)
    except Exception as e:
        logger.exception("jurisdiction-compare error")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Compliance endpoints → Compliance Agent
# ---------------------------------------------------------------------------

@app.post("/api/compliance/sanctions-screen", response_model=AgentResponse)
def sanctions_screen(req: SanctionsScreenRequest):
    prompt = f"Screen {req.entity_name} ({req.entity_type}) for sanctions, PEP and adverse media."
    if req.directors:
        prompt += f" Also screen directors: {', '.join(req.directors)}."
    try:
        output = _run_agent_stage("compliance", prompt)
        return _resp("compliance", output)
    except Exception as e:
        logger.exception("sanctions-screen error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance/ubo-traverse", response_model=AgentResponse)
def ubo_traverse(req: UBORequest):
    prompt = f"Map the UBO chain for {req.entity_name} to depth {req.depth} and flag any conflicts of interest."
    try:
        output = _run_agent_stage("compliance", prompt)
        return _resp("compliance", output)
    except Exception as e:
        logger.exception("ubo-traverse error")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Operations endpoints → Operations Agent
# ---------------------------------------------------------------------------

@app.get("/api/operations/newsfeed")
def get_newsfeed(limit: int = 20, sector: Optional[str] = None):
    topic = "regulatory intelligence newsfeed"
    if sector:
        topic += f" for sector: {sector}"
    prompt = f"Generate the latest {topic}. Return up to {limit} signal cards with title, summary, risk level, and source."
    try:
        output = _run_agent_stage("operations", prompt)
        return _resp("operations", output)
    except Exception as e:
        logger.exception("newsfeed error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/operations/report-assemble", response_model=AgentResponse)
def report_assemble(req: ReportAssembleRequest):
    prompt = f"Assemble a {req.report_type} report."
    if req.signal_ids:
        prompt += f" Based on signals: {', '.join(req.signal_ids)}."
    if req.context:
        prompt += f" Context: {req.context}"
    try:
        output = _run_agent_stage("operations", prompt)
        return _resp("operations", output)
    except Exception as e:
        logger.exception("report-assemble error")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Executive endpoints → Executive Assistant
# ---------------------------------------------------------------------------

@app.post("/api/executive/scenario", response_model=AgentResponse)
def executive_scenario(req: ScenarioRequest):
    prompt = (
        f"Run a {req.scenario_type} financial scenario analysis for the following business plan:\n\n"
        f"{req.business_plan}"
    )
    if req.constraints:
        prompt += f"\n\nConstraints: {req.constraints}"
    try:
        output = _run_agent_stage("ea", prompt)
        return _resp("ea", output)
    except Exception as e:
        logger.exception("executive/scenario error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/executive/brief", response_model=AgentResponse)
def executive_brief(req: BriefRequest):
    prompt = f"Prepare an executive brief on: {req.topic}"
    prior = req.prior_outputs or ""
    try:
        output = _run_agent_stage("ea", prompt, prior)
        return _resp("ea", output)
    except Exception as e:
        logger.exception("executive/brief error")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Drafting endpoints → Drafting Agent
# ---------------------------------------------------------------------------

@app.post("/api/drafting/engagement-letter", response_model=AgentResponse)
def engagement_letter(req: EngagementLetterRequest):
    prompt = (
        f"Draft an engagement letter for {req.client_name} for {req.service_type} "
        f"in {req.jurisdiction}."
    )
    if req.context:
        prompt += f" Additional context: {req.context}"
    try:
        output = _run_agent_stage("drafting", prompt)
        return _resp("drafting", output)
    except Exception as e:
        logger.exception("drafting/engagement-letter error")
        raise HTTPException(status_code=500, detail=str(e))
