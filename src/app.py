"""
Command Center — AI-Native Professional Services OS

UX fixes in this version:
- "Try this" in the gallery runs the request immediately and switches to
  the Workspace tab so the output is visible right away.
- Every stage (not just EA) calls Claude when ANTHROPIC_API_KEY is set.
- The EA stage uses the preceding specialist output as context.
- Simulation mode shows a clear "⚠️ Simulation" banner so users know.
"""

import os, time
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="Command Center · OneIBC",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import engine
from engine import (AGENTS, USE_CASES,
                    STATUS_IDLE, STATUS_QUEUED, STATUS_THINKING,
                    STATUS_WORKING, STATUS_DONE, STATUS_BLOCKED,
                    _user_prompt_classification, _user_prompt_research,
                    _user_prompt_compliance, _user_prompt_ubo,
                    _user_prompt_drafting, _user_prompt_operations,
                    _user_prompt_ea)

# ===========================================================================
# CSS
# ===========================================================================
st.markdown("""
<style>
:root{--bg:#0b1020;--panel:#131a2e;--panel2:#1a2236;--border:#243049;
  --text:#e7ecf6;--muted:#93a0bd;--accent:#6ea8fe;--acc2:#b794f6;
  --idle:#64748b;--queued:#d97706;--thinking:#3b82f6;
  --working:#8b5cf6;--done:#22c55e;--blocked:#ef4444;}
.stApp{background:radial-gradient(1200px 600px at 15% -10%,#1b2542 0%,var(--bg) 55%);}
section.main>div{padding-top:.4rem;}

/* hero */
.hero{border:1px solid var(--border);border-radius:18px;padding:20px 24px;
  margin-bottom:14px;
  background:linear-gradient(135deg,rgba(110,168,254,.13),rgba(183,148,246,.09));}
.hero h1{font-size:1.55rem;margin:0 0 4px;
  background:linear-gradient(90deg,#cfe0ff,#e7d8ff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.hero p{color:var(--muted);margin:0;font-size:.93rem;}
.chips{margin-top:10px;display:flex;gap:7px;flex-wrap:wrap;}
.chip{font-size:.72rem;color:#cdd8f3;border:1px solid var(--border);
  background:var(--panel2);padding:3px 9px;border-radius:999px;}

/* section labels */
.sl{color:var(--muted);font-size:.74rem;text-transform:uppercase;
  letter-spacing:.14em;margin:16px 0 7px 1px;font-weight:600;}

/* agent roster */
.ac{display:flex;align-items:flex-start;gap:9px;padding:9px 11px;
  border:1px solid var(--border);border-radius:11px;background:var(--panel);
  margin-bottom:7px;transition:border-color .2s,box-shadow .2s;}
.ac.active{border-color:var(--accent);box-shadow:0 0 0 1px rgba(110,168,254,.3);}
.ac .ico{font-size:1.25rem;line-height:1.35rem;}
.ac .meta{flex:1;min-width:0;}
.ac .nm{font-weight:600;font-size:.88rem;color:var(--text);display:flex;align-items:center;gap:7px;}
.ac .rl{font-size:.7rem;color:var(--muted);margin-top:2px;line-height:1.2;}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:0 0 auto;}
.badge{font-size:.63rem;padding:2px 7px;border-radius:999px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}
.s-idle{background:rgba(100,116,139,.18);color:#9aa7bd;}
.s-queued{background:rgba(217,119,6,.18);color:#f0b252;}
.s-thinking{background:rgba(59,130,246,.2);color:#7eb0ff;}
.s-working{background:rgba(139,92,246,.22);color:#c0a6ff;}
.s-done{background:rgba(34,197,94,.18);color:#67e08c;}
.s-blocked{background:rgba(239,68,68,.2);color:#ff8d8d;}
.d-idle{background:var(--idle);}
.d-queued{background:var(--queued);}
.d-thinking{background:var(--thinking);animation:pulse 1.3s infinite;}
.d-working{background:var(--working);animation:pulse 1.1s infinite;}
.d-done{background:var(--done);}
.d-blocked{background:var(--blocked);}
.ac.active .d-thinking,.ac.active .d-working{box-shadow:0 0 0 0 rgba(139,92,246,.6);}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(139,92,246,.55);}
  70%{box-shadow:0 0 0 7px rgba(139,92,246,0);}
  100%{box-shadow:0 0 0 0 rgba(139,92,246,0);}}

/* pipeline stage head */
.sh{display:flex;align-items:center;gap:9px;margin-bottom:3px;}
.sh .t{font-weight:600;color:var(--text);font-size:.93rem;}
.sh .a{color:var(--muted);font-size:.76rem;}
.tl{color:var(--accent);font-size:.8rem;font-style:italic;margin-bottom:4px;}

/* activity log */
.logwrap{border:1px solid var(--border);background:#0c1322;border-radius:11px;
  padding:9px 11px;max-height:300px;overflow-y:auto;
  font-family:ui-monospace,Menlo,monospace;}
.logrow{font-size:.73rem;padding:2px 0;border-bottom:1px dashed rgba(36,48,73,.5);
  display:flex;gap:9px;}
.logrow:last-child{border-bottom:none;}
.ts{color:#5f6e8c;flex:0 0 auto;}
.ag{color:#7eb0ff;flex:0 0 140px;}
.ev{color:#c6d0e6;}

/* use-case card */
.uc-card{border:1px solid var(--border);border-radius:13px;padding:14px 15px;
  background:var(--panel);margin-bottom:10px;transition:border-color .2s;}
.uc-card:hover{border-color:var(--accent);}
.uc-card h4{margin:0 0 5px;font-size:.95rem;color:var(--text);}
.uc-card p{margin:0 0 8px;font-size:.8rem;color:var(--muted);}
.uc-flow{font-size:.75rem;color:#93a0bd;margin-bottom:9px;}
.sim-banner{background:rgba(217,119,6,.13);border:1px solid rgba(217,119,6,.35);
  border-radius:8px;padding:7px 11px;font-size:.8rem;color:#f0b252;margin-bottom:8px;}
.live-banner{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);
  border-radius:8px;padding:7px 11px;font-size:.8rem;color:#67e08c;margin-bottom:8px;}
.stButton>button{border-radius:9px;border:1px solid var(--border);
  background:var(--panel2);color:var(--text);font-size:.8rem;}
.stButton>button:hover{border-color:var(--accent);color:#fff;}
</style>""", unsafe_allow_html=True)

# ===========================================================================
# Session state
# ===========================================================================
for k, v in [("runs",[]),("activity",[]),("pending",None),
              ("statuses",{a:STATUS_IDLE for a in AGENTS}),
              ("active_tab", 0)]:
    if k not in st.session_state:
        st.session_state[k] = v

def log(agent_id: str, event: str):
    name = AGENTS[agent_id]["name"] if agent_id in AGENTS else agent_id
    st.session_state.activity.append((engine.now_ts(), name, event))

# ===========================================================================
# Renderers
# ===========================================================================
_ST = {STATUS_IDLE:"Idle", STATUS_QUEUED:"Queued", STATUS_THINKING:"Thinking",
       STATUS_WORKING:"Working", STATUS_DONE:"Done", STATUS_BLOCKED:"Needs review"}

def roster_html(statuses, active=None):
    rows = []
    for aid, meta in AGENTS.items():
        s = statuses.get(aid, STATUS_IDLE)
        cls = " active" if aid == active else ""
        rows.append(
            f'<div class="ac{cls}"><div class="ico">{meta["icon"]}</div>'
            f'<div class="meta"><div class="nm">{meta["name"]}'
            f'<span class="badge s-{s}">{_ST[s]}</span></div>'
            f'<div class="rl">{meta["role"]}</div></div>'
            f'<span class="dot d-{s}"></span></div>')
    return "".join(rows)

def activity_html(items, limit=60):
    if not items:
        return ('<div class="logwrap"><div class="logrow">'
                '<span class="ev" style="color:#5f6e8c">No activity yet.</span>'
                '</div></div>')
    rows = [f'<div class="logrow"><span class="ts">{ts}</span>'
            f'<span class="ag">{ag}</span><span class="ev">{ev}</span></div>'
            for ts, ag, ev in items[-limit:][::-1]]
    return f'<div class="logwrap">{"".join(rows)}</div>'

# ===========================================================================
# Live AI streaming helpers
# ===========================================================================
def api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY","")

def live_ai_available() -> bool:
    return bool(api_key())

def _stream_claude(system: str, user: str):
    """Yield cumulative text chunks from Claude (streaming)."""
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key())
    acc = ""
    with client.messages.stream(
        model=os.getenv("CLAUDE_MODEL","claude-sonnet-4-6"),
        max_tokens=1200,
        system=system,
        messages=[{"role":"user","content":user}],
    ) as stream:
        for text in stream.text_stream:
            acc += text
            yield acc

def stream_stage(stg: engine.Stage, prompt: str, prior_output: str, use_live: bool):
    """Yield cumulative markdown. Falls back to simulation on any error."""
    if not (use_live and live_ai_available()):
        yield from _sim_stream(stg.body)
        return
    # Build the right user message per agent role
    if stg.agent == "orchestrator":
        user = _user_prompt_classification(prompt)
    elif stg.agent == "research":
        user = _user_prompt_research(prompt)
    elif stg.agent == "compliance":
        if "ubo" in prompt.lower() or "ownership" in prompt.lower():
            user = _user_prompt_ubo(prompt)
        else:
            user = _user_prompt_compliance(prompt)
    elif stg.agent == "drafting":
        user = _user_prompt_drafting(prompt)
    elif stg.agent == "operations":
        user = _user_prompt_operations(prompt)
    elif stg.agent == "ea":
        user = _user_prompt_ea(prompt, prior_output)
    else:
        user = prompt
    try:
        yield from _stream_claude(stg.system_prompt, user)
    except Exception as e:
        yield f"⚠️ Live AI error: `{e}` — falling back to simulation.\n\n" + stg.body

def _sim_stream(body: str):
    """Stream simulation body line-by-line."""
    lines = body.split("\n")
    acc = ""
    for i, line in enumerate(lines):
        acc += ("" if i == 0 else "\n") + line
        yield acc + (" ▌" if i < len(lines)-1 else "")
        time.sleep(0.03)

# ===========================================================================
# Header
# ===========================================================================
st.markdown("""
<div class="hero">
  <h1>🛰️ Command Center — AI-Native Professional Services</h1>
  <p>An orchestrated team of AI agents for corporate formation, compliance and
  client operations. Each request is classified, routed to the right specialist,
  and synthesised into an approval-gated executive brief.</p>
  <div class="chips">
    <span class="chip">🧭 Intent routing</span>
    <span class="chip">🔍 GraphRAG research</span>
    <span class="chip">🛡️ Sanctions / UBO</span>
    <span class="chip">✍️ Draft & review</span>
    <span class="chip">📅 Renewals</span>
    <span class="chip">🔒 Human-in-the-loop</span>
  </div>
</div>""", unsafe_allow_html=True)

# ===========================================================================
# Sidebar
# ===========================================================================
with st.sidebar:
    st.markdown('<div class="sl">Live Agent Roster</div>', unsafe_allow_html=True)
    roster_ph = st.empty()
    roster_ph.markdown(roster_html(st.session_state.statuses), unsafe_allow_html=True)

    st.markdown('<div class="sl">Controls</div>', unsafe_allow_html=True)
    can_live = live_ai_available()
    if can_live:
        st.markdown('<div class="live-banner">⚡ Live AI ready — Claude will process each stage</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="sim-banner">⚠️ Simulation mode — set ANTHROPIC_API_KEY for live AI</div>',
                    unsafe_allow_html=True)
    use_live = st.toggle("⚡ Live AI (all stages)", value=can_live, disabled=not can_live,
                         help="When on, every agent stage calls Claude. When off, shows simulation.")

    if st.button("🧹 Clear session", use_container_width=True):
        st.session_state.runs = []
        st.session_state.activity = []
        st.session_state.statuses = {a: STATUS_IDLE for a in AGENTS}
        st.rerun()

    st.markdown('<div class="sl">Firm Context</div>', unsafe_allow_html=True)
    st.caption("**User:** Mark Ng  ·  **Org:** OneIBC")
    st.caption("**Mode:** Command Center  ·  **Policy:** approval-gated")

    # Capability gallery in sidebar
    st.markdown('<div class="sl">What it can do</div>', unsafe_allow_html=True)
    for i, uc in enumerate(USE_CASES):
        flow = " → ".join(AGENTS[a]["icon"] for a in uc["agents"])
        st.markdown(
            f'<div class="uc-card"><h4>{uc["icon"]} {uc["title"]}</h4>'
            f'<p>{uc["desc"]}</p>'
            f'<div class="uc-flow">Flow: {flow}</div></div>',
            unsafe_allow_html=True)
        if st.button(f"▶ Try: {uc['title']}", key=f"uc_{i}", use_container_width=True):
            st.session_state.pending = uc["example"]
            st.rerun()

# ===========================================================================
# Tabs  (Workspace + Activity log only — gallery moved to sidebar)
# ===========================================================================
tab_work, tab_log = st.tabs(["🛰️  Workspace", "🧾  Activity log"])

with tab_log:
    st.markdown('<div class="sl">Full activity history (newest first)</div>', unsafe_allow_html=True)
    st.markdown(activity_html(st.session_state.activity, 500), unsafe_allow_html=True)

with tab_work:
    if not st.session_state.runs:
        st.info("👋 Type a request below, or click **▶ Try** in the sidebar to run an example. "
                "The agent roster (top-left) updates live as each stage runs.")

    # Render completed runs
    for run in st.session_state.runs:
        with st.chat_message("user"):
            st.markdown(run["prompt"])
        with st.chat_message("assistant"):
            mode_label = "🟢 Live AI" if run.get("live") else "⚪ Simulation"
            with st.expander(f"🧭 Pipeline · {len(run['stages'])} stages · {mode_label}", expanded=False):
                for stg in run["stages"]:
                    meta = AGENTS[stg["agent"]]
                    st.markdown(
                        f'<div class="sh"><span>{meta["icon"]}</span>'
                        f'<span class="t">{stg["title"]}</span>'
                        f'<span class="a">· {meta["name"]}</span></div>',
                        unsafe_allow_html=True)
                    st.markdown(stg["body"])
                    st.divider()
            st.markdown(run["final"])

    mini_log_ph = st.empty()
    mini_log_ph.markdown(activity_html(st.session_state.activity, 10), unsafe_allow_html=True)

# ===========================================================================
# Input + execution
# ===========================================================================
typed   = st.chat_input('Ask anything — e.g. "Compare BVI and Cayman for a holding company"…')
prompt  = typed or st.session_state.pending
st.session_state.pending = None

if prompt:
    with tab_work:
        with st.chat_message("user"):
            st.markdown(prompt)

        log("orchestrator", f'Received: "{prompt[:65]}"')
        pipeline = engine.build_pipeline(prompt)

        statuses = {a: STATUS_IDLE for a in AGENTS}
        for stg in pipeline:
            statuses[stg.agent] = STATUS_QUEUED
        roster_ph.markdown(roster_html(statuses), unsafe_allow_html=True)

        with st.chat_message("assistant"):
            if not (use_live and live_ai_available()):
                st.markdown(
                    '<div class="sim-banner">⚠️ <b>Simulation mode</b> — outputs below are illustrative. '
                    'Set <code>ANTHROPIC_API_KEY</code> and enable Live AI for real Claude analysis.</div>',
                    unsafe_allow_html=True)

            timeline = st.container()
            completed, final_text, prior_output = [], "", ""

            for stg in pipeline:
                meta = AGENTS[stg.agent]

                statuses[stg.agent] = STATUS_THINKING
                roster_ph.markdown(roster_html(statuses, active=stg.agent), unsafe_allow_html=True)
                log(stg.agent, f"{stg.title} — started")

                with timeline:
                    st.markdown(
                        f'<div class="sh"><span>{meta["icon"]}</span>'
                        f'<span class="t">{stg.title}</span>'
                        f'<span class="a">· {meta["name"]}</span></div>',
                        unsafe_allow_html=True)
                    think_ph = st.empty()
                    think_ph.markdown(f'<div class="tl">{stg.thought}</div>',
                                      unsafe_allow_html=True)
                    body_ph = st.empty()

                time.sleep(0.3)
                statuses[stg.agent] = STATUS_WORKING
                roster_ph.markdown(roster_html(statuses, active=stg.agent), unsafe_allow_html=True)

                rendered = ""
                for chunk in stream_stage(stg, prompt, prior_output, use_live):
                    rendered = chunk
                    body_ph.markdown(rendered)

                body_ph.markdown(rendered)
                think_ph.empty()

                statuses[stg.agent] = STATUS_BLOCKED if stg.status == STATUS_BLOCKED else STATUS_DONE
                roster_ph.markdown(roster_html(statuses), unsafe_allow_html=True)
                log(stg.agent, f"{stg.title} — done")

                completed.append({"agent": stg.agent, "title": stg.title, "body": rendered})
                prior_output = rendered          # pass output forward to next stage
                if stg.agent == "ea":
                    final_text = rendered

                with timeline:
                    st.divider()

                mini_log_ph.markdown(activity_html(st.session_state.activity, 10),
                                     unsafe_allow_html=True)

            if not final_text and completed:
                final_text = completed[-1]["body"]
            log("ea", "Brief delivered")

        for aid in statuses:
            if statuses[aid] != STATUS_BLOCKED:
                statuses[aid] = STATUS_IDLE
        st.session_state.statuses = statuses
        st.session_state.runs.append({
            "prompt": prompt,
            "stages": completed,
            "final":  final_text,
            "live":   use_live and live_ai_available(),
        })

    st.rerun()
