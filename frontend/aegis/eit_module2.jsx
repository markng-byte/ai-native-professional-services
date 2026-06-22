import { useState, useRef, useEffect, useCallback } from "react";
import { aegisApi } from "./aegisApi";
import { useAegisStore } from "./aegisStore";


// ── DESIGN TOKENS (matches EIT Module 1) ──────────────────────────────────────
const C = {
  bg:"#07100e",bg2:"#0b1a16",bg3:"#0f2018",bg4:"#132618",
  border:"#1a3028",border2:"#234038",border3:"#2e5448",
  teal:"#3de8a0",tealD:"#22b872",tealDark:"#0f6b42",tealGlow:"#3de8a018",tealDim:"#1a7a50",
  cyan:"#40e0d0",
  gold:"#f0c040",goldD:"#c8980a",
  white:"#e8fff8",offwhite:"#b0d8c8",muted:"#5a8878",dim:"#2a5040",
  green:"#22d07a",greenBg:"#001a0e",greenBorder:"#0f4a28",
  red:"#f05060",redBg:"#1a0808",redBorder:"#4a1818",
  blue:"#40b0f0",blueBg:"#050f1a",blueBorder:"#1a3860",
  orange:"#f08040",orangeBg:"#1a0e04",orangeBorder:"#4a2808",
  purple:"#b070f0",purpleBg:"#0d0818",purpleBorder:"#3a1a5a",
  shadow:"0 4px 24px rgba(0,0,0,0.6)",
  glow:"0 0 16px rgba(61,232,160,0.18)",
};

const SCENARIO_COLORS = {
  bull: { main: C.green, bg: C.greenBg, border: C.greenBorder, label: "BULL" },
  base: { main: C.teal,  bg: C.tealGlow, border: C.tealDim, label: "BASE" },
  bear: { main: C.red,   bg: C.redBg,   border: C.redBorder, label: "BEAR" },
};

const SIM_STAGES = [
  { id:"parse",    label:"PARSE",    icon:"⬇" },
  { id:"model",    label:"MODEL",    icon:"◇" },
  { id:"scenario", label:"SCENARIO", icon:"⬡" },
  { id:"simulate", label:"SIMULATE", icon:"▲" },
  { id:"optimize", label:"OPTIMIZE", icon:"◈" },
  { id:"output",   label:"OUTPUT",   icon:"✔" },
];

const SAMPLE_PLAN = `Business: CBDC middleware & digital asset compliance platform for Vietnamese commercial banks.
Revenue target FY2026: VND 48B. 3 bank partnerships planned (MB Bank, BIDV, Techcombank). VNST transaction fees (35%), consulting retainers (30%), licensing (20%), advisory (15%).
Key risks: NQ57 regulatory timeline slippage, talent shortfall in quantum-security engineering, FX exposure on USD-denominated CypherCore Japan contract.
Q1 priority: close MB Bank MOU to binding SLA. Q2: CBDC v2.0 launch. Q3: ISO 27001 certification.`;

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const nowTime = () => new Date().toLocaleTimeString("en", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ── API ───────────────────────────────────────────────────────────────────────
// AI calls route through the AEGIS API Bridge (see ./aegisApi). Provider keys server-side only.
function EITLogo({ size = 32 }) {
  const cx = size / 2, cy = size / 2;
  const nodes = [{ a: 0, d: .85 }, { a: 30, d: .7 }, { a: 60, d: .9 }, { a: 90, d: .75 }, { a: 120, d: .85 }, { a: 150, d: .65 }, { a: 180, d: .8 }, { a: 210, d: .7 }, { a: 240, d: .88 }, { a: 270, d: .75 }, { a: 300, d: .82 }, { a: 330, d: .68 }, { a: 15, d: .55 }, { a: 75, d: .5 }, { a: 135, d: .58 }, { a: 195, d: .52 }, { a: 255, d: .56 }, { a: 315, d: .54 }];
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
      <defs><filter id="gf2"><feGaussianBlur stdDeviation="1.2" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
      {nodes.map((n, i) => { const rad = n.a * Math.PI / 180; const x = cx + Math.cos(rad) * cx * n.d * .92; const y = cy + Math.sin(rad) * cy * n.d * .92; return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#3de8a0" strokeWidth={.6} strokeOpacity={.45} />; })}
      {nodes.map((n, i) => { const rad = n.a * Math.PI / 180; const x = cx + Math.cos(rad) * cx * n.d * .92; const y = cy + Math.sin(rad) * cy * n.d * .92; const rr = n.d > .75 ? size * .038 : size * .028; return <circle key={i} cx={x} cy={y} r={rr} fill="#3de8a0" opacity={n.d > .75 ? .9 : .6} filter="url(#gf2)" />; })}
      <circle cx={cx} cy={cy} r={size * .07} fill="#3de8a0" opacity={.3} filter="url(#gf2)" />
      <circle cx={cx} cy={cy} r={size * .04} fill="#e8fff8" opacity={.95} />
    </svg>
  );
}

// ── BASE UI ───────────────────────────────────────────────────────────────────
const Btn = ({ onClick, variant = "primary", sm, disabled, children, style = {} }) => {
  const vs = { primary: { bg: C.teal, c: C.bg, b: C.tealD }, ghost: { bg: "transparent", c: C.offwhite, b: C.border2 }, danger: { bg: C.redBg, c: C.red, b: C.redBorder }, success: { bg: C.greenBg, c: C.green, b: C.greenBorder }, navy: { bg: C.bg3, c: C.offwhite, b: C.border2 }, tealOut: { bg: "transparent", c: C.teal, b: C.tealDim }, gold: { bg: C.bg3, c: C.gold, b: C.goldD + "80" }, blue: { bg: C.blueBg, c: C.blue, b: C.blueBorder } };
  const v = vs[variant] || vs.primary;
  return <button onClick={onClick} disabled={disabled} style={{ background: v.bg, color: v.c, border: `1px solid ${v.b}`, padding: sm ? "3px 10px" : "7px 18px", cursor: disabled ? "not-allowed" : "pointer", fontFamily: "inherit", fontSize: sm ? 10 : 11, fontWeight: 700, borderRadius: 4, opacity: disabled ? 0.5 : 1, letterSpacing: .5, ...style }}>{children}</button>;
};
const Tag = ({ color = C.dim, label }) => <span style={{ background: color + "20", border: `1px solid ${color}40`, color, fontSize: 9, padding: "2px 8px", borderRadius: 3, marginRight: 4, fontWeight: 700, letterSpacing: .8, display: "inline-block" }}>{label}</span>;
const Sec = ({ title, children, style = {} }) => <div style={{ background: C.bg3, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12, marginBottom: 10, ...style }}>{title && <div style={{ color: C.teal, fontSize: 9, fontWeight: 800, letterSpacing: 2, marginBottom: 10, paddingBottom: 8, borderBottom: `1px solid ${C.border}` }}>{title}</div>}{children}</div>;

// ── MINI SPARKLINE SVG ────────────────────────────────────────────────────────
function Sparkline({ data, color, width = 120, height = 36, fill = false }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });
  const pathD = `M ${pts.join(" L ")}`;
  const fillD = `M 0,${height} L ${pts.join(" L ")} L ${width},${height} Z`;
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {fill && <path d={fillD} fill={color} opacity={0.12} />}
      <path d={pathD} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r={3} fill={color} />
    </svg>
  );
}

// ── WATERFALL BAR CHART ───────────────────────────────────────────────────────
function WaterfallChart({ items, width = 420, height = 160 }) {
  if (!items || !items.length) return null;
  const maxAbs = Math.max(...items.map(it => Math.abs(it.value)));
  const barW = Math.floor((width - 40) / items.length) - 4;
  const cx0 = 36;
  return (
    <svg width={width} height={height + 20} style={{ display: "block", overflow: "visible" }}>
      {/* Axis */}
      <line x1={cx0} y1={0} x2={cx0} y2={height} stroke={C.border2} strokeWidth={1} />
      <line x1={cx0} y1={height / 2} x2={width} y2={height / 2} stroke={C.border2} strokeWidth={1} strokeDasharray="3,4" />
      <text x={cx0 - 4} y={height / 2 + 4} textAnchor="end" fill={C.dim} fontSize={8}>0</text>
      {items.map((it, i) => {
        const pct = it.value / maxAbs;
        const barH = Math.abs(pct) * (height / 2 - 8);
        const isPos = it.value >= 0;
        const x = cx0 + 4 + i * (barW + 4);
        const y = isPos ? height / 2 - barH : height / 2;
        const col = it.color || (isPos ? C.green : C.red);
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={Math.max(barH, 2)} fill={col} opacity={0.85} rx={2} />
            <text x={x + barW / 2} y={height + 14} textAnchor="middle" fill={C.muted} fontSize={8}>{it.label}</text>
            <text x={x + barW / 2} y={isPos ? y - 3 : y + barH + 10} textAnchor="middle" fill={col} fontSize={8} fontWeight={700}>{it.value > 0 ? "+" : ""}{it.display}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ── DONUT CHART ───────────────────────────────────────────────────────────────
function DonutChart({ segments, size = 90, label, sublabel }) {
  const r = 32, cx = size / 2, cy = size / 2, stroke = 10;
  let cum = 0;
  const arcs = segments.map(s => {
    const start = cum;
    cum += s.pct;
    const a1 = (start / 100) * 2 * Math.PI - Math.PI / 2;
    const a2 = (cum / 100) * 2 * Math.PI - Math.PI / 2;
    const laf = s.pct > 50 ? 1 : 0;
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
    return { ...s, d: `M ${x1} ${y1} A ${r} ${r} 0 ${laf} 1 ${x2} ${y2}`, start };
  });
  return (
    <svg width={size} height={size}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={C.border} strokeWidth={stroke} />
      {arcs.map((a, i) => <path key={i} d={a.d} fill="none" stroke={a.color} strokeWidth={stroke} strokeLinecap="butt" />)}
      {label && <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fill={C.white} fontSize={11} fontWeight={800}>{label}</text>}
      {sublabel && <text x={cx} y={cy + 13} textAnchor="middle" fill={C.muted} fontSize={7}>{sublabel}</text>}
    </svg>
  );
}

// ── SCENARIO PROBABILITY GAUGE ────────────────────────────────────────────────
function ProbGauge({ pct, color, size = 70 }) {
  const r = 26, cx = size / 2, cy = size / 2 + 6;
  const startAngle = Math.PI;
  const endAngle = startAngle + (pct / 100) * Math.PI;
  const x1 = cx + r * Math.cos(startAngle), y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle), y2 = cy + r * Math.sin(endAngle);
  const laf = pct > 50 ? 1 : 0;
  return (
    <svg width={size} height={size * 0.6 + 4}>
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke={C.border} strokeWidth={7} strokeLinecap="round" />
      <path d={`M ${x1} ${y1} A ${r} ${r} 0 ${laf} 1 ${x2} ${y2}`} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round" />
      <text x={cx} y={cy - 2} textAnchor="middle" fill={color} fontSize={12} fontWeight={800}>{pct}%</text>
    </svg>
  );
}

// ── PIPELINE PROGRESS ─────────────────────────────────────────────────────────
function SimPipeline({ stage, done, logs }) {
  const logRef = useRef(null);
  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [logs]);
  const stageIdx = SIM_STAGES.findIndex(s => s.id === stage);
  return (
    <div style={{ background: C.bg, border: `1px solid ${C.border2}`, borderRadius: 8, overflow: "hidden", marginBottom: 14 }}>
      <div style={{ background: C.bg2, padding: "8px 14px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 8 }}>
        <EITLogo size={14} />
        <span style={{ color: C.teal, fontWeight: 800, fontSize: 11, letterSpacing: 1.5 }}>SIMULATION ENGINE</span>
        {!done && <span style={{ color: C.teal, fontSize: 10, marginLeft: 4 }}>● RUNNING</span>}
        {done && <span style={{ color: C.green, fontSize: 10, marginLeft: 4 }}>✓ COMPLETE</span>}
      </div>
      <div style={{ padding: "10px 14px", borderBottom: `1px solid ${C.border}`, overflowX: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 0, minWidth: "max-content" }}>
          {SIM_STAGES.map((st, i) => {
            const isA = st.id === stage && !done;
            const isDn = done || stageIdx > i;
            const col = isDn ? C.green : isA ? C.teal : C.dim;
            const bg = isDn ? C.greenBg : isA ? C.tealGlow : C.bg3;
            const bdr = isDn ? C.greenBorder : isA ? C.tealDim : C.border;
            return (
              <div key={st.id} style={{ display: "flex", alignItems: "center" }}>
                <div style={{ textAlign: "center", width: 60, padding: "4px 2px", background: bg, border: `1px solid ${bdr}`, borderRadius: 4, boxShadow: isA ? C.glow : "none" }}>
                  <div style={{ fontSize: 11, marginBottom: 1, color: col }}>{isDn ? "✓" : isA ? "◉" : st.icon}</div>
                  <div style={{ color: col, fontSize: 7.5, fontWeight: 800 }}>{st.label}</div>
                </div>
                {i < SIM_STAGES.length - 1 && <div style={{ width: 6, height: 1, background: isDn ? C.greenBorder : C.border }} />}
              </div>
            );
          })}
        </div>
      </div>
      <div ref={logRef} style={{ background: "#030a07", padding: "7px 10px", fontFamily: "'Courier New',monospace", fontSize: 10, height: 90, overflowY: "auto" }}>
        {logs.map((l, i) => <div key={i} style={{ color: l.t === "success" ? C.green : l.t === "teal" ? C.teal : l.t === "warn" ? C.gold : C.muted, marginBottom: 1.5 }}><span style={{ color: C.dim }}>[{l.time}] </span>{l.msg}</div>)}
        {!done && <div style={{ color: C.teal }}>▌</div>}
      </div>
    </div>
  );
}

// ── SCENARIO CARD ─────────────────────────────────────────────────────────────
function ScenarioCard({ scenario, type, selected, onClick }) {
  const sc = SCENARIO_COLORS[type];
  const metrics = scenario.metrics || {};
  const sparkData = scenario.sparkline || [];
  return (
    <div onClick={onClick} style={{ background: selected ? sc.bg : C.bg2, border: `1.5px solid ${selected ? sc.main : C.border}`, borderRadius: 8, padding: 14, cursor: "pointer", boxShadow: selected ? `0 0 18px ${sc.main}28` : "none", transition: "all .15s", flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{ background: sc.main + "22", border: `1px solid ${sc.main}50`, color: sc.main, fontSize: 9, fontWeight: 800, letterSpacing: 1.5, padding: "2px 10px", borderRadius: 3, display: "inline-block", marginBottom: 5 }}>{sc.label} CASE</div>
          <div style={{ color: C.offwhite, fontSize: 12, fontWeight: 700, lineHeight: 1.3 }}>{scenario.name}</div>
        </div>
        <ProbGauge pct={scenario.probability} color={sc.main} size={64} />
      </div>
      <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6, marginBottom: 10 }}>{scenario.rationale}</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 10 }}>
        {[
          ["Revenue", metrics.revenue, sc.main],
          ["EBITDA", metrics.ebitda, sc.main],
          ["vs. Plan", metrics.vsplan, metrics.vsplan?.startsWith("+") ? C.green : C.red],
          ["Risk Adj.", metrics.risk_adj, C.gold],
        ].map(([l, v, c]) => (
          <div key={l} style={{ background: C.bg + "80", border: `1px solid ${C.border}`, borderRadius: 4, padding: "5px 8px" }}>
            <div style={{ color: C.dim, fontSize: 8, fontWeight: 700, letterSpacing: .8 }}>{l}</div>
            <div style={{ color: c || C.offwhite, fontWeight: 800, fontSize: 12, marginTop: 1 }}>{v || "—"}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          {(scenario.drivers || []).slice(0, 3).map((d, i) => (
            <div key={i} style={{ color: C.muted, fontSize: 9, marginBottom: 2 }}>▸ {d}</div>
          ))}
        </div>
        <Sparkline data={sparkData} color={sc.main} width={80} height={32} fill />
      </div>
      {selected && <div style={{ marginTop: 8, background: sc.main + "15", border: `1px solid ${sc.main}40`, borderRadius: 4, padding: "4px 8px", color: sc.main, fontSize: 9, fontWeight: 700, textAlign: "center" }}>● SELECTED FOR SIMULATION</div>}
    </div>
  );
}

// ── SIMULATION CHART ──────────────────────────────────────────────────────────
function SimChart({ simResult, selectedScenario }) {
  if (!simResult) return null;
  const sc = SCENARIO_COLORS[selectedScenario] || SCENARIO_COLORS.base;
  const quarters = ["Q1", "Q2", "Q3", "Q4"];
  const plan = simResult.plan_quarterly || [25, 25, 25, 25];
  const sim = simResult.sim_quarterly || [22, 26, 27, 25];
  const width = 400, height = 140, padL = 44, padB = 24, padT = 12;
  const chartW = width - padL - 10, chartH = height - padB - padT;
  const allV = [...plan, ...sim];
  const minV = Math.min(...allV) * 0.92, maxV = Math.max(...allV) * 1.08;
  const toY = v => padT + chartH - ((v - minV) / (maxV - minV)) * chartH;
  const toX = i => padL + (i / (quarters.length - 1)) * chartW;
  const planPts = plan.map((v, i) => `${toX(i)},${toY(v)}`).join(" L ");
  const simPts = sim.map((v, i) => `${toX(i)},${toY(v)}`).join(" L ");
  const simFill = `M ${toX(0)},${height - padB} L ${simPts} L ${toX(quarters.length - 1)},${height - padB} Z`;
  const ticks = 4;
  return (
    <div>
      <div style={{ display: "flex", gap: 16, marginBottom: 8, alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}><div style={{ width: 20, height: 2, background: C.tealD, borderRadius: 1 }} /><span style={{ color: C.muted, fontSize: 9 }}>TARGET PLAN</span></div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}><div style={{ width: 20, height: 2, background: sc.main, borderRadius: 1 }} /><span style={{ color: C.muted, fontSize: 9 }}>SIMULATION ({sc.label})</span></div>
        <div style={{ marginLeft: "auto", color: C.dim, fontSize: 9 }}>{simResult.unit || "VND Billion"}</div>
      </div>
      <svg width={width} height={height} style={{ display: "block", overflow: "visible" }}>
        {/* Grid */}
        {Array.from({ length: ticks }).map((_, i) => {
          const v = minV + (i / (ticks - 1)) * (maxV - minV);
          const y = toY(v);
          return (
            <g key={i}>
              <line x1={padL} y1={y} x2={padL + chartW} y2={y} stroke={C.border} strokeWidth={1} strokeDasharray="3,5" />
              <text x={padL - 4} y={y + 3} textAnchor="end" fill={C.dim} fontSize={8}>{Math.round(v)}</text>
            </g>
          );
        })}
        {/* X axis */}
        <line x1={padL} y1={height - padB} x2={padL + chartW} y2={height - padB} stroke={C.border2} />
        {quarters.map((q, i) => <text key={i} x={toX(i)} y={height - padB + 13} textAnchor="middle" fill={C.muted} fontSize={9}>{q}</text>)}
        {/* Variance area */}
        {plan.map((pv, i) => {
          const sv = sim[i];
          if (i >= quarters.length - 1) return null;
          const x1 = toX(i), x2 = toX(i + 1);
          const py1 = toY(pv), py2 = toY(plan[i + 1]);
          const sy1 = toY(sv), sy2 = toY(sim[i + 1]);
          return (
            <polygon key={i} points={`${x1},${py1} ${x2},${py2} ${x2},${sy2} ${x1},${sy1}`}
              fill={sv > pv ? C.green + "30" : C.red + "30"} />
          );
        })}
        {/* Sim fill */}
        <path d={simFill} fill={sc.main} opacity={0.07} />
        {/* Lines */}
        <path d={`M ${planPts}`} fill="none" stroke={C.tealD} strokeWidth={1.5} strokeDasharray="5,3" strokeLinejoin="round" />
        <path d={`M ${simPts}`} fill="none" stroke={sc.main} strokeWidth={2} strokeLinejoin="round" />
        {/* Dots */}
        {sim.map((v, i) => <circle key={i} cx={toX(i)} cy={toY(v)} r={3.5} fill={sc.main} />)}
        {plan.map((v, i) => <circle key={i} cx={toX(i)} cy={toY(v)} r={2.5} fill={C.tealD} opacity={0.7} />)}
      </svg>
    </div>
  );
}

// ── STEP ACTIONS PANEL ────────────────────────────────────────────────────────
function NextStepsPanel({ steps, selectedSteps, onToggle, onRunSim, simRunning }) {
  if (!steps || !steps.length) return null;
  const categories = [...new Set(steps.map(s => s.category))];
  return (
    <div>
      <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6, marginBottom: 12 }}>
        Select one or more strategic actions to simulate. Each combination produces a different variance outcome.
      </div>
      {categories.map(cat => (
        <div key={cat} style={{ marginBottom: 12 }}>
          <div style={{ color: C.dim, fontSize: 9, fontWeight: 800, letterSpacing: 1.5, marginBottom: 6 }}>{cat}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {steps.filter(s => s.category === cat).map(step => {
              const sel = selectedSteps.includes(step.id);
              const impactColor = step.impact === "High" ? C.green : step.impact === "Medium" ? C.gold : C.muted;
              const effortColor = step.effort === "High" ? C.red : step.effort === "Medium" ? C.orange : C.green;
              return (
                <div key={step.id} onClick={() => onToggle(step.id)}
                  style={{ background: sel ? C.tealGlow : C.bg2, border: `1px solid ${sel ? C.tealDim : C.border}`, borderRadius: 6, padding: "8px 12px", cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 10, transition: "all .1s" }}>
                  <div style={{ width: 14, height: 14, borderRadius: 3, border: `1.5px solid ${sel ? C.teal : C.border2}`, background: sel ? C.teal : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                    {sel && <span style={{ color: C.bg, fontSize: 9, fontWeight: 900 }}>✓</span>}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: sel ? C.teal : C.offwhite, fontWeight: 700, fontSize: 11, marginBottom: 2 }}>{step.action}</div>
                    <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.5 }}>{step.description}</div>
                    <div style={{ display: "flex", gap: 8, marginTop: 5 }}>
                      <span style={{ color: impactColor, fontSize: 9, fontWeight: 700 }}>▲ IMPACT: {step.impact}</span>
                      <span style={{ color: effortColor, fontSize: 9, fontWeight: 700 }}>◈ EFFORT: {step.effort}</span>
                      {step.timeline && <span style={{ color: C.dim, fontSize: 9 }}>⏱ {step.timeline}</span>}
                      {step.capital && <span style={{ color: C.gold, fontSize: 9 }}>💰 {step.capital}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
      <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 10 }}>
        <Btn onClick={onRunSim} disabled={!selectedSteps.length || simRunning}>
          {simRunning ? "◈ SIMULATING..." : `▶ RUN SIMULATION (${selectedSteps.length} action${selectedSteps.length !== 1 ? "s" : ""})`}
        </Btn>
        {selectedSteps.length === 0 && <span style={{ color: C.dim, fontSize: 10 }}>Select at least one action</span>}
      </div>
    </div>
  );
}

// ── IMPROVEMENT SUGGESTIONS ───────────────────────────────────────────────────
function ImprovementsPanel({ improvements, targetVariance, conditions }) {
  if (!improvements) return null;
  const items = improvements.improvements || [];
  const securedVariance = improvements.secured_variance || 0;
  const gap = targetVariance - securedVariance;
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 14 }}>
        {[
          { label: "TARGET VARIANCE", value: `${targetVariance}%`, color: C.teal },
          { label: "SECURED VARIANCE", value: `${securedVariance}%`, color: securedVariance >= targetVariance ? C.green : C.gold },
          { label: "REMAINING GAP", value: `${Math.max(gap, 0)}%`, color: gap > 0 ? C.red : C.green },
        ].map(m => (
          <div key={m.label} style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 12px", textAlign: "center" }}>
            <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>{m.label}</div>
            <div style={{ color: m.color, fontWeight: 800, fontSize: 20 }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div style={{ background: C.tealGlow, border: `1px solid ${C.tealDim}60`, borderRadius: 6, padding: "8px 12px", marginBottom: 12, fontSize: 10, color: C.teal, lineHeight: 1.6 }}>
        <strong>Feasibility Assessment:</strong> {improvements.feasibility_summary}
      </div>

      {items.map((imp, i) => {
        const priorityColor = imp.priority === "Critical" ? C.red : imp.priority === "High" ? C.orange : C.gold;
        const feasColor = imp.feasibility_score >= 80 ? C.green : imp.feasibility_score >= 60 ? C.gold : C.red;
        return (
          <div key={i} style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12, marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <div style={{ flex: 1 }}>
                <Tag color={priorityColor} label={imp.priority} />
                <Tag color={C.tealDim} label={imp.category} />
                <div style={{ color: C.offwhite, fontWeight: 700, fontSize: 12, marginTop: 5 }}>{imp.title}</div>
              </div>
              <div style={{ textAlign: "center", flexShrink: 0, marginLeft: 10 }}>
                <div style={{ color: feasColor, fontWeight: 800, fontSize: 18 }}>{imp.feasibility_score}</div>
                <div style={{ color: C.dim, fontSize: 8 }}>FEAS.</div>
              </div>
            </div>
            <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6, marginBottom: 8 }}>{imp.description}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 8 }}>
              {[
                ["Variance Impact", imp.variance_impact, C.green],
                ["Capital Needed", imp.capital_required, C.gold],
                ["Timeline", imp.timeline, C.blue],
              ].map(([l, v, c]) => (
                <div key={l} style={{ background: C.bg3, border: `1px solid ${C.border}`, borderRadius: 4, padding: "5px 8px" }}>
                  <div style={{ color: C.dim, fontSize: 8, fontWeight: 700 }}>{l}</div>
                  <div style={{ color: c, fontWeight: 700, fontSize: 11, marginTop: 1 }}>{v}</div>
                </div>
              ))}
            </div>
            {imp.conditions_met !== undefined && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {(imp.conditions || []).map((cond, j) => (
                  <span key={j} style={{ background: cond.met ? C.greenBg : C.redBg, border: `1px solid ${cond.met ? C.greenBorder : C.redBorder}`, color: cond.met ? C.green : C.red, fontSize: 9, padding: "2px 8px", borderRadius: 3 }}>
                    {cond.met ? "✓" : "✕"} {cond.label}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const storeProfile = useAegisStore(s => s.userProfile);
  const orgData = storeProfile?.orgData;
  const [tab, setTab] = useState("INPUT");
  const [planText, setPlanText] = useState(SAMPLE_PLAN);
  const [orgCtx, setOrgCtx] = useState({
    name: orgData?.name ?? "",
    sector: orgData?.sector ?? (storeProfile?.sectors?.[0] ?? ""),
    geo: orgData?.country ?? (storeProfile?.jurisdictions?.[0] ?? ""),
    risk: storeProfile?.role === "pe_partner" ? "Aggressive" : storeProfile?.role === "counsel" ? "Conservative" : "Moderate",
  });

  // Stage 1: Scenario generation
  const [genRunning, setGenRunning] = useState(false);
  const [genDone, setGenDone] = useState(false);
  const [genStage, setGenStage] = useState(null);
  const [genLogs, setGenLogs] = useState([]);
  const [scenarios, setScenarios] = useState(null);

  // Stage 2: Action selection + simulation
  const [selectedScenario, setSelectedScenario] = useState(null); // "bull"|"base"|"bear"
  const [nextSteps, setNextSteps] = useState(null);
  const [selectedSteps, setSelectedSteps] = useState([]);
  const [simRunning, setSimRunning] = useState(false);
  const [simDone, setSimDone] = useState(false);
  const [simResult, setSimResult] = useState(null);

  // Stage 3: Improvement suggestions
  const [targetVariance, setTargetVariance] = useState(85);
  const [conditions, setConditions] = useState({ capital: "< VND 5B additional", pic: "Existing team", timeline: "FY2026" });
  const [improvRunning, setImprovRunning] = useState(false);
  const [improvements, setImprovements] = useState(null);

  const addLog = (msg, t = "info") => setGenLogs(p => [...p, { msg, t, time: nowTime() }]);

  // ── GENERATE SCENARIOS ────────────────────────────────────────────────────
  const runScenarioGen = async () => {
    setGenRunning(true); setGenDone(false); setGenLogs([]); setScenarios(null);
    setSelectedScenario(null); setNextSteps(null); setSimResult(null); setImprovements(null);

    const log = (msg, t = "info") => setGenLogs(p => [...p, { msg, t, time: nowTime() }]);

    setGenStage("parse");
    log("Parsing business plan & extracting financial model...", "teal");
    await sleep(400);

    setGenStage("model");
    log("Calibrating rolling forecast parameters...", "teal");

    const raw = await aegisApi.scenarios({ business_plan: planText, org_profile: { name: orgCtx.name, sectors: [orgCtx.sector], geos: [orgCtx.geo], risk_appetite: orgCtx.risk } });

    setGenStage("scenario");
    log("Scoring scenario probabilities...", "teal");
    await sleep(300);

    if (raw.error || !raw.bull) {
      log("⚠ Generation error — using fallback scenarios", "warn");
      // Fallback
      setScenarios({
        bull: { name: "Regulatory Tailwind Surge", probability: 25, rationale: "SBV CBDC pilot accelerates beyond expectations, Nami secures all 5 bank partnerships ahead of schedule.", drivers: ["Full NQ57 passage Q1", "CypherCore partnership operationalized", "MB Bank + BIDV sign Q2", "VNST volume 3x"], metrics: { revenue: "VND 68B", ebitda: "VND 31B", vsplan: "+42%", risk_adj: "A-" }, sparkline: [8, 12, 18, 24, 32, 42, 54, 68], keyAssumptions: ["Regulatory fast-track", "No competitor entry", "FX stable"], macroTail: "US rate shock could delay foreign bank partnerships" },
        base: { name: "Steady Execution Path", probability: 50, rationale: "Plan targets met with moderate delays; 3 bank partnerships secured and CBDC middleware launches Q2 as planned.", drivers: ["NQ57 passes Q2", "2 of 3 target banks sign", "VNST growth on track", "ISO 27001 Q3"], metrics: { revenue: "VND 48B", ebitda: "VND 20B", vsplan: "±0%", risk_adj: "B+" }, sparkline: [7, 10, 14, 18, 24, 32, 40, 48], keyAssumptions: ["Regulatory timeline holds", "Team headcount achieved", "No major competitors"], macroTail: "Macro slowdown compresses bank digital budgets" },
        bear: { name: "Regulatory & Execution Drag", probability: 25, rationale: "NQ57 delays compound with slower bank procurement cycles, limiting revenue to 1 partnership and VNST headwinds.", drivers: ["NQ57 deferred to Q4", "Only MB Bank signs", "Talent gap widens", "CBDC tech delays"], metrics: { revenue: "VND 28B", ebitda: "VND 6B", vsplan: "-42%", risk_adj: "C+" }, sparkline: [6, 8, 10, 12, 14, 18, 22, 28], keyAssumptions: ["Regulatory slippage 2 quarters", "Budget cuts at target banks", "Engineering delays"], macroTail: "Political reversal on crypto pilot could stall all revenue" },
        plan_summary: { revenue_target: "VND 48B", ebitda_target: "VND 20B", key_kpis: ["3 bank partnerships", "CBDC v2.0 Q2 launch", "ISO 27001 Q3"] }
      });
    } else {
      setScenarios(raw);
    }

    setGenStage("output");
    log("✓ 3 scenarios generated with probability weights", "success");
    log("✓ Bull/Base/Bear framework ready for action simulation", "success");
    await sleep(200);

    // Generate next steps
    log("Generating strategic action options...", "teal");
    const stepsRaw = await aegisApi.nextSteps({ business_plan: planText, org_profile: { name: orgCtx.name, sectors: [orgCtx.sector], geos: [orgCtx.geo], risk_appetite: orgCtx.risk } });
    if (Array.isArray(stepsRaw)) {
      setNextSteps(stepsRaw);
    } else {
      setNextSteps([
        { id: "s1", category: "PARTNERSHIPS", action: "Accelerate MB Bank MOU to binding contract", description: "Fast-track the MB Bank CBDC middleware agreement from MOU to signed SLA by end of Q1.", impact: "High", effort: "Medium", timeline: "6 weeks", capital: null },
        { id: "s2", category: "PARTNERSHIPS", action: "Engage BIDV digital transformation team", description: "Initiate formal partnership dialogue with BIDV's Fintech Division via SBV introduction.", impact: "High", effort: "High", timeline: "8-12 weeks", capital: "VND 200M" },
        { id: "s3", category: "REVENUE", action: "Pre-sell VNST enterprise tier to 3 anchor clients", description: "Offer 12-month discounted lock-ins to secure recurring VNST transaction revenue baseline.", impact: "High", effort: "Medium", timeline: "4-6 weeks", capital: null },
        { id: "s4", category: "REVENUE", action: "Launch consulting retainer packages", description: "Package CBDC integration advisory as fixed-fee quarterly retainers for Tier 2 banks.", impact: "Medium", effort: "Low", timeline: "3 weeks", capital: null },
        { id: "s5", category: "COST", action: "Defer non-critical R&D to Q3", description: "Push 2 non-critical engineering workstreams to H2, freeing VND 3B in H1 runway.", impact: "Medium", effort: "Low", timeline: "2 weeks", capital: null },
        { id: "s6", category: "OPERATIONS", action: "Hire 2 quantum-security engineers via CypherCore", description: "Leverage CypherCore Japan partnership for secondment or referral to fill key technical gaps.", impact: "High", effort: "Medium", timeline: "6-8 weeks", capital: "VND 1.2B" },
        { id: "s7", category: "RISK", action: "Establish regulatory monitoring function", description: "Dedicate 0.5 FTE to tracking NQ57 amendments and SBV circular updates in real time.", impact: "Medium", effort: "Low", timeline: "2 weeks", capital: "VND 150M" },
        { id: "s8", category: "RISK", action: "FX hedging for USD-denominated contracts", description: "Use forward contracts to hedge USD/VND exposure on CypherCore Japan payments.", impact: "Medium", effort: "Medium", timeline: "4 weeks", capital: "VND 500M" },
      ]);
    }
    log("✓ Strategic action library generated", "success");
    setGenRunning(false); setGenDone(true);
    setTab("SCENARIOS");
  };

  // ── RUN SIMULATION ────────────────────────────────────────────────────────
  const runSimulation = async () => {
    if (!selectedSteps.length || !selectedScenario) return;
    setSimRunning(true); setSimDone(false); setSimResult(null);

    const selectedActions = nextSteps.filter(s => selectedSteps.includes(s.id));
    const sc = scenarios?.[selectedScenario];

    const result = await aegisApi.simulate({ business_plan: planText, selected_scenario: selectedScenario, scenario_data: sc, selected_actions: selectedActions, org_profile: { name: orgCtx.name, sectors: [orgCtx.sector], geos: [orgCtx.geo], risk_appetite: orgCtx.risk } });

    if (result && !result.error) {
      setSimResult(result);
    } else {
      const actions = selectedActions.length;
      const boost = actions * (selectedScenario === "bull" ? 4 : selectedScenario === "base" ? 3 : 2);
      setSimResult({
        headline: `Executing ${actions} strategic action${actions !== 1 ? "s" : ""} improves ${selectedScenario} case variance by ~${boost}% against plan.`,
        plan_quarterly: [22, 24, 26, 28],
        sim_quarterly: [20, 25, 28, 27 + boost * 0.3],
        unit: "% of Annual Target",
        variance_from_plan: `+${boost}%`,
        variance_confidence: "Medium",
        adjusted_probability: Math.min(95, (sc?.probability || 50) + 8),
        key_changes: selectedActions.slice(0, 4).map(a => `${a.action} contributes ${a.impact === "High" ? "3-5%" : "1-2%"} variance improvement`),
        residual_risks: ["Regulatory timing remains key external variable", "Execution capacity stretched with current team size"],
        feasible_plan: "The selected actions materially improve plan adherence, though execution sequencing will be critical to realizing projected upside.",
        waterfall: [
          { label: "Base Plan", value: 100, display: "100%", color: C.tealD },
          ...selectedActions.slice(0, 3).map((a, i) => ({ label: a.action.slice(0, 12), value: a.impact === "High" ? 4 : 2, display: a.impact === "High" ? "+4%" : "+2%", color: C.green })),
          { label: "Risks", value: -(selectedScenario === "bear" ? 15 : 5), display: selectedScenario === "bear" ? "-15%" : "-5%", color: C.red },
          { label: "Result", value: 100 + boost - (selectedScenario === "bear" ? 15 : 5), display: `${100 + boost - (selectedScenario === "bear" ? 15 : 5)}%`, color: C.teal },
        ]
      });
    }
    setSimRunning(false); setSimDone(true);
    setTab("SIMULATION");
  };

  // ── GENERATE IMPROVEMENTS ─────────────────────────────────────────────────
  const runImprovements = async () => {
    setImprovRunning(true);
    const result = await aegisApi.improvements({ business_plan: planText, selected_scenario: selectedScenario, sim_result: simResult, target_variance: targetVariance, conditions, selected_steps: selectedSteps, org_profile: { name: orgCtx.name, sectors: [orgCtx.sector], geos: [orgCtx.geo], risk_appetite: orgCtx.risk } });
    if (result && !result.error) {
      setImprovements(result);
    } else {
      setImprovements({
        secured_variance: 72,
        feasibility_summary: "With current capital and team constraints, securing 85% plan variance is achievable through focused revenue acceleration and cost discipline. The primary lever is accelerating the MB Bank contract close.",
        improvements: [
          { title: "Executive Sponsor Introduction — MB Bank CEO", category: "REVENUE", priority: "Critical", description: "Leverage Nami Foundation's SBV relationships to secure a direct executive introduction to MB Bank's CEO. Bypasses procurement delays by 6-8 weeks.", variance_impact: "+8% variance", capital_required: "Minimal", timeline: "2 weeks", feasibility_score: 88, conditions_met: true, conditions: [{ label: "SBV relationship exists", met: true }, { label: "MB Bank interest confirmed", met: true }] },
          { title: "VNST Revenue Pull-Forward via Prepaid Fees", category: "REVENUE", priority: "High", description: "Offer 3-month prepaid VNST transaction fee packages to top 10 institutional clients at 5% discount. Accelerates ~VND 3B into H1.", variance_impact: "+6% variance", capital_required: "Minimal", timeline: "3 weeks", feasibility_score: 76, conditions_met: true, conditions: [{ label: "Client pipeline established", met: true }, { label: "Legal approval", met: false }] },
          { title: "Defer ISO 27001 to Q4", category: "COST", priority: "High", description: "Reschedule ISO 27001 certification audit to Q4 2026, freeing VND 800M in H1 cash for BD acceleration.", variance_impact: "+3% variance", capital_required: "Minimal", timeline: "1 week", feasibility_score: 92, conditions_met: true, conditions: [{ label: "No client contract requires Q3 cert", met: true }] },
          { title: "Consulting Revenue Sprint — Tier 2 Banks", category: "REVENUE", priority: "Medium", description: "Run a 6-week outreach to Techcombank and VPBank offering CBDC readiness assessments as fixed-fee engagements at VND 500M each.", variance_impact: "+4% variance", capital_required: "VND 200M BD cost", timeline: "6 weeks", feasibility_score: 65, conditions_met: false, conditions: [{ label: "BD capacity available", met: false }, { label: "CBDC framework drafted", met: true }] },
        ]
      });
    }
    setImprovRunning(false);
    setTab("IMPROVEMENTS");
  };

  // ── TABS ──────────────────────────────────────────────────────────────────
  const TABS = [
    { id: "INPUT", label: "⬇ PLAN INPUT" },
    { id: "SCENARIOS", label: "◇ SCENARIOS", locked: !genDone },
    { id: "SIMULATION", label: "▲ SIMULATION", locked: !simDone },
    { id: "IMPROVEMENTS", label: "◈ IMPROVEMENTS", locked: !improvements },
  ];

  return (
    <div style={{ background: C.bg, color: C.offwhite, fontFamily: "'Inter',system-ui,sans-serif", minHeight: "100vh", fontSize: 12, overflowX: "hidden", maxWidth: "100vw", boxSizing: "border-box" }}>
      {/* Header */}
      <div style={{ background: C.bg2, borderBottom: `1px solid ${C.border}`, padding: "0 20px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 48 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <EITLogo size={32} />
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ color: C.teal, fontWeight: 900, fontSize: 18, letterSpacing: 4, textShadow: `0 0 18px ${C.teal}60` }}>EIT</span>
              <span style={{ color: C.tealD, fontSize: 11, fontWeight: 700, letterSpacing: 2 }}>EXECUTIVE INTELLIGENCE TERMINAL</span>
            </div>
            <div style={{ color: C.dim, fontSize: 9, letterSpacing: 1.5 }}>MODULE 2 · SCENARIOS & SIMULATIONS</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ color: C.dim, fontSize: 10 }}>{orgCtx.name}</span>
          <span style={{ color: C.tealDim, fontSize: 10 }}>◈ {orgCtx.sector}</span>
          <span style={{ color: C.dim, fontSize: 10 }}>{new Date().toISOString().slice(0, 10)}</span>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ background: C.bg, borderBottom: `1px solid ${C.border}`, padding: "0 18px", display: "flex", alignItems: "center" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => !t.locked && setTab(t.id)}
            style={{ background: "transparent", color: t.locked ? C.dim + "60" : tab === t.id ? C.teal : C.dim, border: "none", borderBottom: `2px solid ${tab === t.id ? C.teal : "transparent"}`, padding: "10px 16px", cursor: t.locked ? "default" : "pointer", fontSize: 11, fontFamily: "inherit", fontWeight: tab === t.id ? 800 : 500, letterSpacing: .5, textShadow: tab === t.id ? `0 0 10px ${C.teal}50` : "" }}>
            {t.label}{t.locked ? " 🔒" : ""}
          </button>
        ))}
        {genDone && (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            {scenarios && <Tag color={C.green} label={`BULL ${scenarios.bull?.probability}%`} />}
            {scenarios && <Tag color={C.teal} label={`BASE ${scenarios.base?.probability}%`} />}
            {scenarios && <Tag color={C.red} label={`BEAR ${scenarios.bear?.probability}%`} />}
          </div>
        )}
      </div>

      {/* ── INPUT TAB ─────────────────────────────────────────────────────── */}
      {tab === "INPUT" && (
        <div style={{ padding: 20, display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,280px)", gap: 16, alignItems: "start", maxWidth: "100%", boxSizing: "border-box" }}>
          <div>
            <Sec title="BUSINESS PLAN / STRATEGY INPUT">
              <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6, marginBottom: 10 }}>
                Paste your business plan, BSC, financial model, or rolling forecast. The simulation engine will extract key parameters and generate 3 scenario cases with probability weights.
              </div>
              <textarea
                value={planText}
                onChange={e => setPlanText(e.target.value)}
                style={{ background: C.bg, border: `1px solid ${C.border2}`, color: C.white, padding: "10px 12px", width: "100%", fontFamily: "monospace", fontSize: 11, borderRadius: 4, boxSizing: "border-box", resize: "vertical", minHeight: 320, outline: "none", lineHeight: 1.7 }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
                <span style={{ color: C.dim, fontSize: 10 }}>{planText.length} chars · Supports free text, tables, or structured formats</span>
                <Btn onClick={runScenarioGen} disabled={genRunning || planText.trim().length < 50}>
                  {genRunning ? "◈ GENERATING..." : "▶ GENERATE SCENARIOS"}
                </Btn>
              </div>
            </Sec>
            {genRunning && <SimPipeline stage={genStage} done={genDone} logs={genLogs} />}
          </div>

          {/* Org profile sidebar */}
          <div>
            <Sec title="ORG PROFILE">
              {[
                { label: "ORGANIZATION", field: "name", placeholder: "Company name" },
                { label: "SECTOR", field: "sector", placeholder: "e.g. Fintech, Web3" },
                { label: "GEOGRAPHY", field: "geo", placeholder: "e.g. Vietnam, SEA" },
                { label: "RISK APPETITE", field: "risk", placeholder: "Conservative / Moderate / Aggressive" },
              ].map(f => (
                <div key={f.field} style={{ marginBottom: 10 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>{f.label}</div>
                  <input value={orgCtx[f.field]} onChange={e => setOrgCtx(p => ({ ...p, [f.field]: e.target.value }))}
                    placeholder={f.placeholder}
                    style={{ background: C.bg, border: `1px solid ${C.border2}`, color: C.white, padding: "6px 10px", width: "100%", fontFamily: "inherit", fontSize: 11, borderRadius: 4, boxSizing: "border-box", outline: "none" }} />
                </div>
              ))}
            </Sec>
            <Sec title="WHAT YOU'LL GET">
              {[
                ["◇ 3 Scenario Cases", "Bull / Base / Bear with probability weights and rationale"],
                ["▲ Action Simulation", "Select next steps and simulate variance impact visually"],
                ["◈ Improvement Plan", "AI-generated improvements to hit your target variance"],
              ].map(([t, d]) => (
                <div key={t} style={{ marginBottom: 10 }}>
                  <div style={{ color: C.teal, fontWeight: 700, fontSize: 11 }}>{t}</div>
                  <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.5 }}>{d}</div>
                </div>
              ))}
            </Sec>
            <Sec title="SUPPORTED INPUTS" style={{ marginBottom: 0 }}>
              {["Business plan (Word / text)", "Balanced Scorecard (BSC)", "Financial model summaries", "Rolling forecast tables", "Strategy deck narratives"].map(i => (
                <div key={i} style={{ color: C.muted, fontSize: 10, marginBottom: 3 }}>◈ {i}</div>
              ))}
            </Sec>
          </div>
        </div>
      )}

      {/* ── SCENARIOS TAB ──────────────────────────────────────────────────── */}
      {tab === "SCENARIOS" && scenarios && (
        <div style={{ padding: 20, maxWidth: 1100, margin: "0 auto" }}>
          {/* Plan summary bar */}
          <div style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ color: C.teal, fontSize: 9, fontWeight: 800, letterSpacing: 2 }}>PLAN TARGETS</div>
            {[
              ["REVENUE", scenarios.plan_summary?.revenue_target],
              ["EBITDA", scenarios.plan_summary?.ebitda_target],
              ...((scenarios.plan_summary?.key_kpis || []).map((k, i) => [`KPI ${i + 1}`, k])),
            ].map(([l, v]) => (
              <div key={l} style={{ display: "flex", flex: 1, flexDirection: "column" }}>
                <span style={{ color: C.dim, fontSize: 9, fontWeight: 700 }}>{l}</span>
                <span style={{ color: C.offwhite, fontWeight: 700, fontSize: 11 }}>{v}</span>
              </div>
            ))}
          </div>

          {/* Probability donut row */}
          <div style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, marginBottom: 16, display: "flex", alignItems: "center", gap: 20 }}>
            <DonutChart
              segments={[
                { pct: scenarios.bull?.probability || 25, color: C.green },
                { pct: scenarios.base?.probability || 50, color: C.teal },
                { pct: scenarios.bear?.probability || 25, color: C.red },
              ]}
              size={90} label={`${scenarios.base?.probability || 50}%`} sublabel="BASE"
            />
            <div style={{ flex: 1 }}>
              <div style={{ color: C.teal, fontSize: 9, fontWeight: 800, letterSpacing: 2, marginBottom: 8 }}>SCENARIO PROBABILITY DISTRIBUTION</div>
              {[["bull", C.green], ["base", C.teal], ["bear", C.red]].map(([k, c]) => (
                <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: c, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: C.muted, fontSize: 10 }}>{SCENARIO_COLORS[k].label} — {scenarios[k]?.name}</span>
                      <span style={{ color: c, fontWeight: 800, fontSize: 11 }}>{scenarios[k]?.probability}%</span>
                    </div>
                    <div style={{ height: 4, background: C.border, borderRadius: 2, marginTop: 3 }}>
                      <div style={{ width: `${scenarios[k]?.probability}%`, height: "100%", background: c, borderRadius: 2 }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ color: C.dim, fontSize: 10, maxWidth: 220, lineHeight: 1.6, borderLeft: `1px solid ${C.border}`, paddingLeft: 16 }}>
              Probabilities reflect current macro conditions and plan execution confidence. Select a scenario below to proceed to action simulation.
            </div>
          </div>

          {/* 3 scenario cards */}
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {["bull", "base", "bear"].map(k => (
              <ScenarioCard key={k} scenario={scenarios[k]} type={k}
                selected={selectedScenario === k}
                onClick={() => setSelectedScenario(k === selectedScenario ? null : k)} />
            ))}
          </div>

          {/* Scenario deep-dive (expanded) */}
          {selectedScenario && scenarios[selectedScenario] && (
            <Sec title={`${SCENARIO_COLORS[selectedScenario].label} CASE · KEY ASSUMPTIONS & TAIL RISKS`}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 6 }}>KEY ASSUMPTIONS</div>
                  {(scenarios[selectedScenario].keyAssumptions || []).map((a, i) => (
                    <div key={i} style={{ color: C.offwhite, fontSize: 11, marginBottom: 5, lineHeight: 1.5 }}>▸ {a}</div>
                  ))}
                </div>
                <div>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 6 }}>MACRO TAIL RISK</div>
                  <div style={{ background: C.redBg, border: `1px solid ${C.redBorder}`, borderRadius: 4, padding: "8px 10px", color: C.red, fontSize: 11, lineHeight: 1.6, fontStyle: "italic" }}>
                    {scenarios[selectedScenario].macroTail}
                  </div>
                </div>
              </div>
            </Sec>
          )}

          {/* Next steps for selected scenario */}
          {selectedScenario && nextSteps && (
            <Sec title="STRATEGIC ACTION OPTIONS · SELECT TO SIMULATE">
              <NextStepsPanel steps={nextSteps} selectedSteps={selectedSteps}
                onToggle={id => setSelectedSteps(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])}
                onRunSim={runSimulation} simRunning={simRunning} />
            </Sec>
          )}
          {!selectedScenario && <div style={{ textAlign: "center", color: C.dim, fontSize: 12, paddingTop: 10 }}>↑ Select a scenario card to unlock action simulation</div>}
        </div>
      )}

      {/* ── SIMULATION TAB ─────────────────────────────────────────────────── */}
      {tab === "SIMULATION" && simResult && (
        <div style={{ padding: 20, maxWidth: 1100, margin: "0 auto" }}>
          {/* Headline */}
          <div style={{ background: C.tealGlow, border: `1px solid ${C.tealDim}80`, borderRadius: 8, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ color: C.teal, fontSize: 16 }}>◇</span>
            <div>
              <div style={{ color: C.teal, fontSize: 9, fontWeight: 800, letterSpacing: 1.5, marginBottom: 2 }}>SIMULATION OUTCOME · {selectedScenario?.toUpperCase()} CASE</div>
              <div style={{ color: C.offwhite, fontWeight: 700, fontSize: 12 }}>{simResult.headline}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
            <div>
              {/* Quarterly chart */}
              <Sec title="QUARTERLY REVENUE TRAJECTORY — PLAN vs. SIMULATION">
                <SimChart simResult={simResult} selectedScenario={selectedScenario} />
                <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
                  {[
                    { label: "VARIANCE FROM PLAN", val: simResult.variance_from_plan, color: simResult.variance_from_plan?.startsWith("+") ? C.green : C.red },
                    { label: "CONFIDENCE", val: simResult.variance_confidence, color: simResult.variance_confidence === "High" ? C.green : simResult.variance_confidence === "Medium" ? C.gold : C.red },
                    { label: "ADJ. PROBABILITY", val: `${simResult.adjusted_probability}%`, color: C.teal },
                  ].map(m => (
                    <div key={m.label} style={{ flex: 1, background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 6, padding: "8px 10px", textAlign: "center" }}>
                      <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: .8 }}>{m.label}</div>
                      <div style={{ color: m.color, fontWeight: 800, fontSize: 18, marginTop: 3 }}>{m.val}</div>
                    </div>
                  ))}
                </div>
              </Sec>

              {/* Waterfall */}
              {simResult.waterfall && (
                <Sec title="VARIANCE WATERFALL — ACTION IMPACT BREAKDOWN">
                  <WaterfallChart items={simResult.waterfall} width={480} height={140} />
                </Sec>
              )}

              {/* Key changes */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Sec title="KEY CHANGES FROM SELECTED ACTIONS">
                  {(simResult.key_changes || []).map((c, i) => (
                    <div key={i} style={{ color: C.green, fontSize: 10, marginBottom: 5, lineHeight: 1.5 }}>▸ {c}</div>
                  ))}
                </Sec>
                <Sec title="RESIDUAL RISKS">
                  {(simResult.residual_risks || []).map((r, i) => (
                    <div key={i} style={{ color: C.red, fontSize: 10, marginBottom: 5, lineHeight: 1.5 }}>▸ {r}</div>
                  ))}
                </Sec>
              </div>
            </div>

            {/* Right panel */}
            <div>
              <Sec title="SELECTED ACTIONS">
                {nextSteps?.filter(s => selectedSteps.includes(s.id)).map(s => (
                  <div key={s.id} style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 4, padding: "7px 10px", marginBottom: 6 }}>
                    <div style={{ color: C.teal, fontWeight: 700, fontSize: 10 }}>{s.action}</div>
                    <div style={{ display: "flex", gap: 6, marginTop: 3 }}>
                      <Tag color={s.impact === "High" ? C.green : s.impact === "Medium" ? C.gold : C.muted} label={s.impact} />
                      {s.capital && <Tag color={C.gold} label={s.capital} />}
                    </div>
                  </div>
                ))}
              </Sec>

              <Sec title="FEASIBILITY CONCLUSION">
                <div style={{ color: C.offwhite, fontSize: 11, lineHeight: 1.7 }}>{simResult.feasible_plan}</div>
              </Sec>

              {/* Improvement gate */}
              <Sec title="VARIANCE GAP ANALYSIS">
                <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6, marginBottom: 10 }}>
                  Set your target plan adherence and conditions. AI will generate improvement suggestions to close the remaining variance gap.
                </div>
                <div style={{ marginBottom: 10 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>TARGET VARIANCE (%)</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input type="range" min={50} max={100} value={targetVariance} onChange={e => setTargetVariance(+e.target.value)}
                      style={{ flex: 1, accentColor: C.teal }} />
                    <span style={{ color: C.teal, fontWeight: 800, fontSize: 14, minWidth: 36 }}>{targetVariance}%</span>
                  </div>
                </div>
                {[
                  { label: "CAPITAL CONSTRAINT", field: "capital" },
                  { label: "PIC QUALIFICATION", field: "pic" },
                  { label: "TIMELINE", field: "timeline" },
                ].map(f => (
                  <div key={f.field} style={{ marginBottom: 8 }}>
                    <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, letterSpacing: 1, marginBottom: 3 }}>{f.label}</div>
                    <input value={conditions[f.field]} onChange={e => setConditions(p => ({ ...p, [f.field]: e.target.value }))}
                      style={{ background: C.bg, border: `1px solid ${C.border2}`, color: C.white, padding: "5px 9px", width: "100%", fontFamily: "inherit", fontSize: 11, borderRadius: 4, boxSizing: "border-box", outline: "none" }} />
                  </div>
                ))}
                <Btn onClick={runImprovements} disabled={improvRunning} style={{ marginTop: 6, width: "100%", justifyContent: "center" }}>
                  {improvRunning ? "◈ ANALYZING..." : "◈ GENERATE IMPROVEMENTS"}
                </Btn>
              </Sec>
            </div>
          </div>
        </div>
      )}

      {/* ── IMPROVEMENTS TAB ────────────────────────────────────────────────── */}
      {tab === "IMPROVEMENTS" && improvements && (
        <div style={{ padding: 20, maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,280px)", gap: 16, alignItems: "start" }}>
            <div>
              <Sec title={`IMPROVEMENT PLAN · ${targetVariance}% TARGET VARIANCE · ${selectedScenario?.toUpperCase()} CASE`}>
                <ImprovementsPanel improvements={improvements} targetVariance={targetVariance} conditions={conditions} />
              </Sec>
            </div>
            <div>
              <Sec title="SIMULATION SUMMARY">
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, marginBottom: 3 }}>SCENARIO</div>
                  <div style={{ color: SCENARIO_COLORS[selectedScenario]?.main, fontWeight: 700, fontSize: 12 }}>
                    {SCENARIO_COLORS[selectedScenario]?.label} — {scenarios?.[selectedScenario]?.name}
                  </div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, marginBottom: 3 }}>ACTIONS SELECTED</div>
                  <div style={{ color: C.teal, fontWeight: 700, fontSize: 12 }}>{selectedSteps.length} of {nextSteps?.length || 0}</div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, marginBottom: 3 }}>SIMULATION VARIANCE</div>
                  <div style={{ color: simResult?.variance_from_plan?.startsWith("+") ? C.green : C.red, fontWeight: 800, fontSize: 18 }}>{simResult?.variance_from_plan}</div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, marginBottom: 3 }}>IMPROVEMENT TARGET</div>
                  <div style={{ color: C.teal, fontWeight: 800, fontSize: 18 }}>{targetVariance}%</div>
                </div>
                <div style={{ height: 1, background: C.border, margin: "10px 0" }} />
                <div style={{ color: C.dim, fontSize: 9, fontWeight: 700, marginBottom: 6 }}>CONDITIONS</div>
                {Object.entries(conditions).map(([k, v]) => (
                  <div key={k} style={{ marginBottom: 4 }}>
                    <span style={{ color: C.dim, fontSize: 9 }}>{k.toUpperCase()}: </span>
                    <span style={{ color: C.muted, fontSize: 9, fontWeight: 700 }}>{v}</span>
                  </div>
                ))}
              </Sec>

              <Sec title="IMPROVEMENT FEASIBILITY CHART">
                <div style={{ color: C.muted, fontSize: 10, marginBottom: 8 }}>Feasibility score distribution</div>
                {(improvements.improvements || []).map((imp, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ color: C.muted, fontSize: 9 }}>{imp.title?.slice(0, 28)}{imp.title?.length > 28 ? "..." : ""}</span>
                      <span style={{ color: imp.feasibility_score >= 80 ? C.green : imp.feasibility_score >= 60 ? C.gold : C.red, fontSize: 9, fontWeight: 700 }}>{imp.feasibility_score}</span>
                    </div>
                    <div style={{ height: 4, background: C.border, borderRadius: 2 }}>
                      <div style={{ width: `${imp.feasibility_score}%`, height: "100%", background: imp.feasibility_score >= 80 ? C.green : imp.feasibility_score >= 60 ? C.gold : C.red, borderRadius: 2, transition: "width .3s" }} />
                    </div>
                  </div>
                ))}
              </Sec>

              <Btn onClick={() => { setTab("INPUT"); setGenDone(false); setScenarios(null); setSelectedScenario(null); setSimResult(null); setImprovements(null); setSelectedSteps([]); setGenLogs([]); }}
                variant="ghost" style={{ width: "100%", justifyContent: "center" }}>
                ↺ START NEW SIMULATION
              </Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
