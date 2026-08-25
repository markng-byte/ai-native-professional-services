"""
Command Center — AI-Native Professional Services OS
====================================================
A polished Streamlit interface that makes the system legible at a glance:

  • A capability gallery so anyone instantly sees *what it can do*.
  • A live agent roster showing *who is doing what*, updated in real time.
  • Step-by-step *streaming* of every request through the agent pipeline.
  • A persistent *activity log* (history) of everything that happened.

Runs out-of-the-box with no API key (deterministic simulation engine). If
ANTHROPIC_API_KEY is set and the "Live AI" toggle is on, the Executive
Assistant's synthesis step streams from a real Claude model instead.
"""

import os
import time

import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:  # optional dependency — app still runs without it
    def load_dotenv(*args, **kwargs):
        return False

st.set_page_config(
    page_title="Command Center · AI-Native Professional Services",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import engine
from engine import (
    AGENTS,
    USE_CASES,
    STATUS_IDLE,
    STATUS_QUEUED,
    STATUS_THINKING,
    STATUS_WORKING,
    STATUS_DONE,
    STATUS_BLOCKED,
)

load_dotenv()

# ===========================================================================
# Theme / CSS  (kept as a plain string — CSS braces clash with f-strings)
# ===========================================================================
st.markdown(
    """
<style>
:root {
  --bg: #0b1020; --panel: #131a2e; --panel-2: #1a2236;
  --border: #243049; --text: #e7ecf6; --muted: #93a0bd;
  --accent: #6ea8fe; --accent-2: #b794f6;
  --idle:#64748b; --queued:#d97706; --thinking:#3b82f6;
  --working:#8b5cf6; --done:#22c55e; --blocked:#ef4444;
}
.stApp { background: radial-gradient(1200px 600px at 15% -10%, #1b2542 0%, var(--bg) 55%); }
section.main > div { padding-top: .5rem; }

.hero { border:1px solid var(--border);
  background: linear-gradient(135deg, rgba(110,168,254,.14), rgba(183,148,246,.10));
  border-radius:18px; padding:22px 26px; margin-bottom:18px; }
.hero h1 { font-size:1.7rem; margin:0 0 4px 0; letter-spacing:.2px;
  background: linear-gradient(90deg,#cfe0ff,#e7d8ff); -webkit-background-clip:text;
  -webkit-text-fill-color:transparent; }
.hero p { color:var(--muted); margin:0; font-size:.96rem; }
.hero .chips { margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; }
.chip { font-size:.74rem; color:#cdd8f3; border:1px solid var(--border);
  background:var(--panel-2); padding:4px 10px; border-radius:999px; }

.section-label { color:var(--muted); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.14em; margin:18px 0 8px 2px; font-weight:600; }

/* Agent roster card */
.agent-card { display:flex; align-items:flex-start; gap:10px; padding:10px 12px;
  border:1px solid var(--border); border-radius:12px; background:var(--panel);
  margin-bottom:8px; transition:border-color .25s, box-shadow .25s; }
.agent-card .ico { font-size:1.3rem; line-height:1.4rem; }
.agent-card .meta { flex:1; min-width:0; }
.agent-card .nm { font-weight:600; font-size:.9rem; color:var(--text); display:flex;
  align-items:center; gap:8px; }
.agent-card .rl { font-size:.72rem; color:var(--muted); margin-top:2px; line-height:1.25; }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; flex:0 0 auto; }
.badge { font-size:.66rem; padding:2px 8px; border-radius:999px; font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; }
.s-idle{background:rgba(100,116,139,.18);color:#9aa7bd;}
.s-queued{background:rgba(217,119,6,.18);color:#f0b252;}
.s-thinking{background:rgba(59,130,246,.20);color:#7eb0ff;}
.s-working{background:rgba(139,92,246,.22);color:#c0a6ff;}
.s-done{background:rgba(34,197,94,.18);color:#67e08c;}
.s-blocked{background:rgba(239,68,68,.20);color:#ff8d8d;}
.d-idle{background:var(--idle);}
.d-queued{background:var(--queued);}
.d-thinking{background:var(--thinking); box-shadow:0 0 0 0 rgba(59,130,246,.6); animation:pulse 1.3s infinite;}
.d-working{background:var(--working); box-shadow:0 0 0 0 rgba(139,92,246,.6); animation:pulse 1.1s infinite;}
.d-done{background:var(--done);}
.d-blocked{background:var(--blocked);}
.agent-card.active { border-color:var(--accent); box-shadow:0 0 0 1px rgba(110,168,254,.35); }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(139,92,246,.55);} 70%{box-shadow:0 0 0 8px rgba(139,92,246,0);} 100%{box-shadow:0 0 0 0 rgba(139,92,246,0);} }

/* Stage cards in the run timeline */
.stage-head { display:flex; align-items:center; gap:10px; margin-bottom:2px; }
.stage-head .t { font-weight:600; color:var(--text); font-size:.95rem; }
.stage-head .a { color:var(--muted); font-size:.78rem; }
.thinking-line { color:var(--accent); font-size:.82rem; font-style:italic; }

/* Activity log */
.logwrap { border:1px solid var(--border); background:#0c1322; border-radius:12px;
  padding:10px 12px; max-height:340px; overflow-y:auto; font-family:ui-monospace,Menlo,monospace; }
.logrow { font-size:.76rem; padding:3px 0; border-bottom:1px dashed rgba(36,48,73,.6);
  display:flex; gap:10px; }
.logrow:last-child{border-bottom:none;}
.logrow .ts { color:#5f6e8c; flex:0 0 auto; }
.logrow .ag { color:#7eb0ff; flex:0 0 130px; }
.logrow .ev { color:#c6d0e6; }

/* Use-case container tweak */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
div[data-testid="stExpander"] details { border:1px solid var(--border)!important;
  border-radius:12px!important; background:var(--panel); }
.stButton>button { border-radius:10px; border:1px solid var(--border);
  background:var(--panel-2); color:var(--text); font-size:.82rem; }
.stButton>button:hover { border-color:var(--accent); color:#fff; }
</style>
""",
    unsafe_allow_html=True,
)

# ===========================================================================
# Session state
# ===========================================================================
if "runs" not in st.session_state:
    st.session_state.runs = []          # completed runs (for history rendering)
if "activity" not in st.session_state:
    st.session_state.activity = []      # list of (ts, agent_name, event)
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "statuses" not in st.session_state:
    st.session_state.statuses = {aid: STATUS_IDLE for aid in AGENTS}


def log(agent_id: str, event: str):
    name = AGENTS[agent_id]["name"] if agent_id in AGENTS else agent_id
    st.session_state.activity.append((engine.now_ts(), name, event))


# ===========================================================================
# Renderers
# ===========================================================================
_STATUS_TEXT = {
    STATUS_IDLE: "Idle", STATUS_QUEUED: "Queued", STATUS_THINKING: "Thinking",
    STATUS_WORKING: "Working", STATUS_DONE: "Done", STATUS_BLOCKED: "Needs review",
}


def roster_html(statuses: dict, active: str | None = None) -> str:
    rows = []
    for aid, meta in AGENTS.items():
        s = statuses.get(aid, STATUS_IDLE)
        is_active = " active" if aid == active else ""
        rows.append(
            f'<div class="agent-card{is_active}">'
            f'<div class="ico">{meta["icon"]}</div>'
            f'<div class="meta"><div class="nm">{meta["name"]}'
            f'<span class="badge s-{s}">{_STATUS_TEXT[s]}</span></div>'
            f'<div class="rl">{meta["role"]}</div></div>'
            f'<span class="dot d-{s}"></span>'
            f"</div>"
        )
    return "".join(rows)


def activity_html(items: list, limit: int = 60) -> str:
    if not items:
        return '<div class="logwrap"><div class="logrow"><span class="ev" style="color:#5f6e8c">No activity yet — run a request to populate the log.</span></div></div>'
    rows = []
    for ts, ag, ev in items[-limit:][::-1]:
        rows.append(
            f'<div class="logrow"><span class="ts">{ts}</span>'
            f'<span class="ag">{ag}</span><span class="ev">{ev}</span></div>'
        )
    return f'<div class="logwrap">{"".join(rows)}</div>'


# ===========================================================================
# Live-AI helper (optional, graceful fallback)
# ===========================================================================
def live_ai_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def stream_live_ai(prompt: str, context: str):
    """Yield cumulative markdown from a real Claude model. Best-effort; the
    caller falls back to the simulated body on any failure."""
    from langchain_anthropic import ChatAnthropic  # local import; optional dep

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    llm = ChatAnthropic(model_name=model, temperature=0.3, max_tokens=900)
    system = (
        "You are the Senior Executive Assistant and Command Center for a "
        "professional-services firm (corporate formation, compliance, banking). "
        "Synthesise the specialist findings into a crisp executive brief in "
        "Markdown: a status line, key takeaways as bullets, and one recommended "
        "next action. Prefer tables over prose. Never send client-facing comms; "
        "everything stays gated on human approval."
    )
    user = f"Executive request: {prompt}\n\nSpecialist findings so far:\n{context}"
    acc = ""
    for chunk in llm.stream([("system", system), ("human", user)]):
        acc += getattr(chunk, "content", "") or ""
        yield acc


# ===========================================================================
# Header
# ===========================================================================
st.markdown(
    """
<div class="hero">
  <h1>🛰️ Command Center — AI-Native Professional Services</h1>
  <p>An orchestrated team of AI agents for corporate formation, compliance and
  client operations. Ask in plain language; the Orchestrator routes your request
  to the right specialist, and the Executive Assistant returns a single, approval-gated brief.</p>
  <div class="chips">
    <span class="chip">🧭 Intent routing</span>
    <span class="chip">🔍 GraphRAG research</span>
    <span class="chip">🛡️ Sanctions / UBO</span>
    <span class="chip">✍️ Draft &amp; review</span>
    <span class="chip">📅 Renewals</span>
    <span class="chip">🔒 Human-in-the-loop</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ===========================================================================
# Sidebar — live roster + controls + firm context
# ===========================================================================
with st.sidebar:
    st.markdown('<div class="section-label">Live Agent Roster</div>', unsafe_allow_html=True)
    roster_ph = st.empty()
    roster_ph.markdown(roster_html(st.session_state.statuses), unsafe_allow_html=True)

    st.markdown('<div class="section-label">Controls</div>', unsafe_allow_html=True)
    can_live = live_ai_available()
    use_live = st.toggle(
        "⚡ Live AI synthesis",
        value=False,
        disabled=not can_live,
        help="Stream the Executive Assistant's brief from a real Claude model. "
        + ("Requires ANTHROPIC_API_KEY." if not can_live else "Key detected."),
    )
    st.caption("🟢 Live AI ready" if can_live else "⚪ Simulation mode (no API key)")
    if st.button("🧹 Clear session", use_container_width=True):
        st.session_state.runs = []
        st.session_state.activity = []
        st.session_state.statuses = {aid: STATUS_IDLE for aid in AGENTS}
        st.rerun()

    st.markdown('<div class="section-label">Firm Context</div>', unsafe_allow_html=True)
    st.caption("**User:** Mark Ng  ·  **Org:** OneIBC")
    st.caption("**Mode:** Command Center  ·  **Policy:** approval-gated")


# ===========================================================================
# RM Co-pilot surface
# ===========================================================================
# This is a *rendering shell*. It never computes a priority, a risk, an ageing
# figure or a recommendation — it displays what rm.session returned, shaped by
# rm.views. Adding business logic here is what created the triplication the
# Phase 0 audit found, so it is deliberately kept out.

from hitl.approvals import ROLE_COMPLIANCE_OFFICER, ROLE_DEPARTMENT_HEAD, ROLE_RM  # noqa: E402
from hitl import STATE_APPROVED, STATE_REJECTED, ApprovalError, ApprovalStore  # noqa: E402
from hitl.storage import InMemoryApprovalStorage, SqliteApprovalStorage  # noqa: E402
from crm.fixtures import RELATIONSHIP_MANAGERS  # noqa: E402  (dev actor picker — see D2)
from rm import views as rm_views  # noqa: E402
from rm.feedback import VERDICT_NOT_USEFUL, VERDICT_USEFUL, VERDICT_WRONG, record_feedback  # noqa: E402
from rm.session import RMSession  # noqa: E402

_REVIEWER_ROLES = [ROLE_RM, ROLE_COMPLIANCE_OFFICER, ROLE_DEPARTMENT_HEAD]


# Approvals are audit records (GOVERNANCE.md §5.1, seven-year retention), so the
# *application* defaults to durable storage rather than requiring an operator to
# remember an environment variable. Libraries and tests keep the in-memory
# default, which is why this default lives here and not in hitl.storage.
DEFAULT_APPROVAL_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "approvals", "approvals.db",
)


def _approval_store() -> ApprovalStore:
    """Build the approval store for the running app.

    ``FIRMOS_APPROVAL_DB`` overrides the location. Setting it to ``memory``
    opts out deliberately — for a throwaway demo where losing approvals is
    acceptable — so opting out is an explicit choice rather than an omission.
    """
    configured = (os.environ.get("FIRMOS_APPROVAL_DB") or "").strip()
    if configured.lower() in ("memory", ":memory:"):
        return ApprovalStore(InMemoryApprovalStorage())
    return ApprovalStore(SqliteApprovalStorage(configured or DEFAULT_APPROVAL_DB))


def _rm_session() -> RMSession:
    if "rm_session" not in st.session_state:
        st.session_state.rm_session = RMSession(store=_approval_store())
    return st.session_state.rm_session


def _audit_caption(audit: dict):
    st.caption(
        f"corr `{audit.get('correlation_id')}` · audit `{audit.get('audit_ref')}` · "
        f"source `{audit.get('data_source')}` · actor `{audit.get('actor_id')}`"
    )


def _render_error(view: dict):
    if view.get("is_authorization_denial"):
        st.error(f"🔒 **{view['headline']}** — {view['message']}")
    else:
        st.warning(f"**{view['headline']}** — {view['message']}")
    _audit_caption(view["audit"])


def _feedback_controls(envelope: dict, rm_id: str, key: str):
    st.caption("Was this useful?")
    c1, c2, c3 = st.columns(3)
    choices = (
        (c1, "👍 Useful", VERDICT_USEFUL),
        (c2, "👎 Not useful", VERDICT_NOT_USEFUL),
        (c3, "⚠️ Wrong", VERDICT_WRONG),
    )
    for col, label, verdict in choices:
        with col:
            if st.button(label, key=f"fb_{key}_{verdict}", use_container_width=True):
                record_feedback(envelope, rm_id=rm_id, verdict=verdict)
                st.toast("Feedback recorded — thank you.")


def _render_signal(sig: dict, *, expanded: bool):
    badge = sig["badge"]
    with st.expander(f"{badge['glyph']}  {badge['label']} — {sig['action']}",
                     expanded=expanded):
        st.write(sig["reason"])
        if sig.get("evidence"):
            st.caption("Evidence")
            for e in sig["evidence"]:
                st.markdown(f"- `{e}`")


def render_rm_copilot():
    session = _rm_session()

    st.markdown('<div class="section-label">RM Co-pilot — grounded, governed decision support</div>',
                unsafe_allow_html=True)

    # --- actor selection (dev stand-in for real auth; decision D2) ---------
    left, right = st.columns([2, 3])
    with left:
        rm_options = list(RELATIONSHIP_MANAGERS)
        chosen = st.selectbox(
            "Acting as", rm_options,
            format_func=lambda r: f"{RELATIONSHIP_MANAGERS[r].full_name} ({r})",
            key="rm_actor",
        )
        session.select_rm(chosen)
        st.caption("⚠️ Development actor picker — not authentication (decision D2 open).")
    with right:
        query = st.text_input("Find a client", key="rm_query",
                              placeholder="Name, trade name or entity number…")

    if query:
        sv = rm_views.search_results_view(session.search(query))
        if sv["kind"] == "error":
            _render_error(sv)
        elif sv["match_count"] == 0:
            st.info(sv["empty_note"])
        else:
            labels = {m["client_id"]: f"{m['legal_name']} · {m['jurisdiction']} "
                                      f"{m['risk']['glyph']} {m['risk_rating']}"
                      for m in sv["matches"]}
            picked = st.radio("Matches", list(labels), format_func=lambda c: labels[c],
                              key="rm_pick")
            if st.button("Open client workspace", type="primary"):
                session.select_client(picked)
                st.rerun()

    if not session.is_ready:
        st.info("Search for a client above to begin. Only clients assigned to you are shown.")
        return

    # --- client workspace -------------------------------------------------
    summary = rm_views.client_summary_view(session.client_summary())
    if summary["kind"] == "error":
        _render_error(summary)
        return

    st.subheader(summary["headline"])

    action_env = session.next_best_action()
    action = rm_views.next_action_view(action_env)

    col_a, col_b = st.columns([3, 2])

    with col_a:
        if action["kind"] == "error":
            _render_error(action)
        else:
            badge = action["badge"]
            with st.container(border=True):
                st.markdown(f"### {badge['glyph']}  Next best action — {badge['label']}")
                st.markdown(f"**{action['recommended_action']}**")
                st.write(action["reason"])
                if action["evidence"]:
                    st.caption("Evidence")
                    for e in action["evidence"]:
                        st.markdown(f"- `{e}`")
                if action["required_information"]:
                    st.caption("Still needed")
                    for r in action["required_information"]:
                        st.markdown(f"- {r}")
                if action["suggested_next_question"]:
                    st.info(f"💬 Suggested question: {action['suggested_next_question']}")
                _audit_caption(action["audit"])
                _feedback_controls(action_env, session.rm_id, "nba")

            if action["other_signals"]:
                st.markdown('<div class="section-label">Other signals (not hidden)</div>',
                            unsafe_allow_html=True)
                for sig in action["other_signals"]:
                    _render_signal(sig, expanded=False)

    with col_b:
        if summary["missing_information"]:
            with st.container(border=True):
                st.markdown("#### ❓ What we do not know")
                for gap in summary["missing_information"]:
                    st.markdown(f"- {gap}")

        if summary["open_items"]:
            with st.container(border=True):
                st.markdown("#### 📌 Open items")
                for item in summary["open_items"]:
                    flag = "🔴 " if item.get("is_overdue") else ""
                    st.markdown(f"- {flag}**{item['type']}** · {item['detail']}")

        if summary["known_needs"]:
            with st.container(border=True):
                st.markdown("#### 🧾 Known needs")
                st.write(", ".join(summary["known_needs"]))

    # --- opportunities ----------------------------------------------------
    if summary["opportunities"]:
        st.markdown('<div class="section-label">Opportunities</div>', unsafe_allow_html=True)
        for opp in summary["opportunities"]:
            with st.expander(
                f"{opp['risk']['glyph']}  {opp['opportunity_id']} — {opp['name']} "
                f"({opp['stage']}, {opp['currency']} {opp['amount']:,.0f})"
            ):
                review = rm_views.opportunity_review_view(
                    session.opportunity_review(opp["opportunity_id"])
                )
                if review["kind"] == "error":
                    _render_error(review)
                else:
                    st.markdown(f"**{review['stage_assessment']}**")
                    st.caption(review["aging"]["basis"])
                    if review["aging"].get("policy_source"):
                        st.caption(f"Risk band per {review['aging']['policy_source']}")
                    if review["missing_actions"]:
                        st.caption("Missing actions")
                        for m in review["missing_actions"]:
                            st.markdown(f"- {m}")
                    for a in review["recommended_actions"]:
                        _render_signal(a, expanded=False)
                    _audit_caption(review["audit"])

    # --- draft -> approval -> gate ---------------------------------------
    st.markdown('<div class="section-label">Follow-up draft (human-gated)</div>',
                unsafe_allow_html=True)

    if st.button("✍️  Generate follow-up draft"):
        session.generate_draft()
        st.rerun()

    if session.draft_envelope:
        draft = rm_views.draft_view(session.draft_envelope, session.approval_record(),
                                    session.delivery_decision())
        if draft["kind"] == "error":
            _render_error(draft)
            return

        with st.container(border=True):
            st.code(draft["draft"], language=None)
            st.caption(f"🔒 {draft['never_sent_notice']}")

            state = draft["approval_state"]
            st.markdown(f"**Approval state:** `{state}`")

            storage = session.storage_notice()
            if storage["durable"]:
                st.caption(storage["message"])
            else:
                st.warning(storage["message"])
            if draft["gate_status"] == "BLOCKED":
                for reason in draft["blocked_reasons"]:
                    st.warning(f"Delivery blocked — {reason}")
            elif draft["gate_delivered"]:
                st.success("✅ Approved for delivery. (Nothing is transmitted by this system.)")

            required = session.required_role()
            if required:
                st.caption(f"Governance requires approval by: **{required}**")

            if not session.approval_id:
                if st.button("Submit for review", type="primary"):
                    session.submit_for_review()
                    st.rerun()
            elif state not in (STATE_APPROVED, STATE_REJECTED):
                role = st.selectbox("Reviewing as role", _REVIEWER_ROLES, key="rm_role")
                justification = st.text_input(
                    "Justification (required to reject)", key="rm_just"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Approve", use_container_width=True):
                        try:
                            session.decide(STATE_APPROVED, reviewer_id=session.rm_id,
                                           reviewer_role=role)
                            st.rerun()
                        except ApprovalError as exc:
                            st.error(f"Refused — {exc}")
                with c2:
                    if st.button("❌ Reject", use_container_width=True):
                        try:
                            session.decide(STATE_REJECTED, reviewer_id=session.rm_id,
                                           reviewer_role=role, justification=justification)
                            st.rerun()
                        except ApprovalError as exc:
                            st.error(f"Refused — {exc}")

            if draft["events"]:
                st.caption("Approval trail")
                for e in draft["events"]:
                    st.markdown(
                        f"- `{e['timestamp']}` **{e['event']}** by `{e.get('actor')}`"
                        + (f" — {e['justification']}" if e.get("justification") else "")
                    )
            if draft["supporting_facts"]:
                with st.expander("Supporting facts (every claim, with its source)"):
                    for f in draft["supporting_facts"]:
                        st.markdown(f"- **{f['fact']}**: {f['value']}  \n  _source: `{f['source']}`_")
            _audit_caption(draft["audit"])
            _feedback_controls(session.draft_envelope, session.rm_id, "draft")


# ===========================================================================
# Main tabs
# ===========================================================================
tab_work, tab_rm, tab_uses, tab_log = st.tabs(
    ["🛰️  Workspace", "🤝  RM Co-pilot", "🧩  What it can do", "🧾  Activity log"]
)

# ---- Tab: RM Co-pilot ------------------------------------------------------
# Thin rendering shell only. Every decision, fact and gate verdict comes from
# rm.session / rm.views; this block adds no business logic of its own.
with tab_rm:
    render_rm_copilot()

# ---- Tab: What it can do (capability gallery) -----------------------------
with tab_uses:
    st.markdown('<div class="section-label">Capability gallery — click “Try” to load an example</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, uc in enumerate(USE_CASES):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"#### {uc['icon']}  {uc['title']}")
                st.caption(uc["desc"])
                chain = "  →  ".join(AGENTS[a]["icon"] for a in uc["agents"])
                st.markdown(f"<span style='font-size:.8rem;color:#93a0bd'>Flow: {chain}</span>", unsafe_allow_html=True)
                if st.button("Try this", key=f"uc_{i}", use_container_width=True):
                    st.session_state.pending_prompt = uc["example"]
                    st.rerun()

# ---- Tab: Activity log -----------------------------------------------------
with tab_log:
    st.markdown('<div class="section-label">Full activity history (newest first)</div>', unsafe_allow_html=True)
    st.markdown(activity_html(st.session_state.activity, limit=500), unsafe_allow_html=True)

# ---- Tab: Workspace --------------------------------------------------------
with tab_work:
    # Past runs (rendered statically so they survive Streamlit reruns)
    if not st.session_state.runs:
        st.info("👋 Welcome. Type a request below, or open **What it can do** to load an example. "
                "Watch the sidebar roster and the timeline update live as your request is processed.")
    for run in st.session_state.runs:
        with st.chat_message("user"):
            st.markdown(run["prompt"])
        with st.chat_message("assistant"):
            with st.expander(f"🧭 Pipeline — {len(run['stages'])} stage(s)", expanded=False):
                for stg in run["stages"]:
                    meta = AGENTS[stg["agent"]]
                    st.markdown(
                        f'<div class="stage-head"><span class="ico">{meta["icon"]}</span>'
                        f'<span class="t">{stg["title"]}</span>'
                        f'<span class="a">· {meta["name"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(stg["body"])
                    st.divider()
            st.markdown(run["final"])

    # Mini activity strip under the conversation
    st.markdown('<div class="section-label">Recent activity</div>', unsafe_allow_html=True)
    mini_log_ph = st.empty()
    mini_log_ph.markdown(activity_html(st.session_state.activity, limit=12), unsafe_allow_html=True)


# ===========================================================================
# Input handling
# ===========================================================================
typed = st.chat_input("Ask anything — e.g. “Compare BVI and Cayman for a holding company”…")
prompt = typed or st.session_state.pending_prompt
st.session_state.pending_prompt = None

if prompt:
    # Render the new user turn immediately inside the workspace tab context.
    with tab_work:
        with st.chat_message("user"):
            st.markdown(prompt)

        log("orchestrator", f'Request received: "{prompt[:70]}"')
        pipeline = engine.build_pipeline(prompt)

        # Reset roster, mark all pipeline agents as queued.
        statuses = {aid: STATUS_IDLE for aid in AGENTS}
        for stg in pipeline:
            statuses[stg.agent] = STATUS_QUEUED
        roster_ph.markdown(roster_html(statuses), unsafe_allow_html=True)

        with st.chat_message("assistant"):
            timeline = st.container()
            completed_stages = []
            final_text = ""

            for stg in pipeline:
                meta = AGENTS[stg.agent]

                # → thinking
                statuses[stg.agent] = STATUS_THINKING
                roster_ph.markdown(roster_html(statuses, active=stg.agent), unsafe_allow_html=True)
                log(stg.agent, f"{stg.title} — started")

                with timeline:
                    st.markdown(
                        f'<div class="stage-head"><span class="ico">{meta["icon"]}</span>'
                        f'<span class="t">{stg.title}</span>'
                        f'<span class="a">· {meta["name"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                    think_ph = st.empty()
                    think_ph.markdown(f'<div class="thinking-line">{stg.thought}</div>', unsafe_allow_html=True)
                    body_ph = st.empty()

                time.sleep(0.45)

                # → working / streaming
                statuses[stg.agent] = STATUS_WORKING
                roster_ph.markdown(roster_html(statuses, active=stg.agent), unsafe_allow_html=True)

                rendered = ""
                streamed_live = False
                if stg.llm and use_live and live_ai_available():
                    try:
                        ctx = "\n\n".join(c["body"] for c in completed_stages) or "(none)"
                        for acc in stream_live_ai(prompt, ctx):
                            rendered = acc
                            body_ph.markdown(rendered + " ▌")
                        streamed_live = True
                    except Exception:
                        streamed_live = False  # fall through to simulation

                if not streamed_live:
                    # Stream the simulated body line-by-line (cumulative markdown).
                    lines = stg.body.split("\n")
                    for j in range(len(lines)):
                        rendered = "\n".join(lines[: j + 1])
                        body_ph.markdown(rendered + (" ▌" if j < len(lines) - 1 else ""))
                        time.sleep(0.035)

                body_ph.markdown(rendered)
                think_ph.empty()

                # → done
                statuses[stg.agent] = STATUS_BLOCKED if stg.status == STATUS_BLOCKED else STATUS_DONE
                roster_ph.markdown(roster_html(statuses), unsafe_allow_html=True)
                log(stg.agent, f"{stg.title} — completed")

                completed_stages.append({"agent": stg.agent, "title": stg.title, "body": rendered})
                if stg.agent == "ea":
                    final_text = rendered

                with timeline:
                    st.divider()

                mini_log_ph.markdown(activity_html(st.session_state.activity, limit=12), unsafe_allow_html=True)

            if not final_text and completed_stages:
                final_text = completed_stages[-1]["body"]

            log("ea", "Brief delivered to executive")

        # Settle roster back to idle and persist the run.
        for aid in statuses:
            if statuses[aid] not in (STATUS_BLOCKED,):
                statuses[aid] = STATUS_IDLE
        st.session_state.statuses = statuses
        st.session_state.runs.append(
            {"prompt": prompt, "stages": completed_stages, "final": final_text}
        )

    st.rerun()
