import { useState, useEffect, useRef } from "react";
import { aegisBus } from "./eventBus";
import { aegisApi, fmt } from "./aegisApi";
import { AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const C = { gold:"#c8a84b", teal:"#1a7a6e", red:"#e05252", green:"#4caf7d", muted:"#6b7280", bg:"#080a0d", surface:"#0f1318", surface2:"#151b22", border:"#1e2730", text:"#e8eaed", amber:"#e07b30", purple:"#7b6fd4", blue:"#5b9bd5" };

const ZONES = [
  { id:"us", label:"United States", region:"North America", score:84, trend:"up", tag:"HIGH", color:C.amber, jurisdictions:["FED","SEC","CFTC","FinCEN","OFAC"], active:["STABLE Act","FCA Stablecoin","OFAC Crypto Rule"], count:7 },
  { id:"eu", label:"European Union", region:"Europe", score:91, trend:"up", tag:"CRITICAL", color:C.red, jurisdictions:["ECB","ESMA","EBA","MiCA"], active:["MiCA Phase II","DORA","eIDAS 2.0"], count:12 },
  { id:"uk", label:"United Kingdom", region:"Europe", score:76, trend:"stable", tag:"HIGH", color:C.amber, jurisdictions:["FCA","PRA","BoE"], active:["FCA Stablecoin Regime","PSR Review"], count:4 },
  { id:"sea", label:"Southeast Asia", region:"Asia Pacific", score:78, trend:"up", tag:"HIGH", color:C.amber, jurisdictions:["SBV","MAS","BOT","OJK","BSP"], active:["SBV Circular","MAS AI v3","OJK Crypto"], count:9 },
  { id:"cn", label:"China / HK", region:"Asia Pacific", score:88, trend:"up", tag:"CRITICAL", color:C.red, jurisdictions:["PBOC","HKMA","CSRC"], active:["e-CNY mBridge","HK VASP License"], count:6 },
  { id:"jp", label:"Japan / Korea", region:"Asia Pacific", score:72, trend:"stable", tag:"MEDIUM", color:C.gold, jurisdictions:["JFSA","BOJ","FSC KR"], active:["JFSA Travel Rule","KR Crypto Tax"], count:3 },
  { id:"me", label:"Middle East", region:"MENA", score:67, trend:"up", tag:"MEDIUM", color:C.gold, jurisdictions:["ADGM","VARA","DFSA","SAMA"], active:["VARA Phase II","ADGM Tokenization"], count:5 },
  { id:"sg", label:"Singapore", region:"Asia Pacific", score:65, trend:"stable", tag:"MEDIUM", color:C.gold, jurisdictions:["MAS","ACRA","SGX"], active:["MAS AI Framework","Project Guardian"], count:4 },
  { id:"in", label:"India", region:"Asia Pacific", score:69, trend:"up", tag:"MEDIUM", color:C.gold, jurisdictions:["RBI","SEBI","MoF IN"], active:["RBI CBDC Pilot","SEBI Crypto Draft"], count:3 },
  { id:"latam", label:"Latin America", region:"Americas", score:55, trend:"stable", tag:"LOW", color:C.teal, jurisdictions:["BCB","Banxico","CMF"], active:["Brazil PIX Crypto","MX Fintech Law"], count:2 },
  { id:"af", label:"Africa", region:"Africa", score:48, trend:"up", tag:"LOW", color:C.teal, jurisdictions:["FSCA","CBN","CMA KE"], active:["SA FSCA Crypto","Nigeria Stablecoin"], count:2 },
  { id:"intl", label:"International Bodies", region:"Global", score:82, trend:"up", tag:"HIGH", color:C.amber, jurisdictions:["FATF","BIS","FSB","IMF","OECD"], active:["FATF Travel Rule","Basel IV","CARF"], count:8 },
];

const FEED_DATA = [
  { id:1, zone:"eu", jurisdiction:"EU", tag:"CRITICAL", sector:"Crypto", title:"MiCA Phase II enforcement begins", time:"2m", impact:92, desc:"Full reserve requirements for e-money tokens. Affects all EU-licensed exchanges.", citations:["EUR-Lex MiCA","ECB Digital Finance"] },
  { id:2, zone:"sea", jurisdiction:"VN", tag:"HIGH", sector:"Fintech", title:"SBV Draft Circular on Payment Intermediaries", time:"14m", impact:78, desc:"New capital adequacy for non-bank payment providers. Comment period: 30 days.", citations:["SBV Portal"] },
  { id:3, zone:"sg", jurisdiction:"SG", tag:"MEDIUM", sector:"AI", title:"MAS AI Governance Framework v3", time:"31m", impact:54, desc:"Expanded explainability requirements for AI-driven credit decisioning.", citations:["MAS.gov.sg"] },
  { id:4, zone:"us", jurisdiction:"US", tag:"HIGH", sector:"Stablecoin", title:"STABLE Act passes Senate committee", time:"1h", impact:81, desc:"Federal stablecoin oversight advances. Preempts state-level licensing.", citations:["Congress.gov","Bloomberg Law"] },
  { id:5, zone:"cn", jurisdiction:"CN", tag:"CRITICAL", sector:"CBDC", title:"e-CNY cross-border pilot expands to 15 nations", time:"3h", impact:88, desc:"PBOC extends mBridge to SEA corridor. Systemic implications.", citations:["PBOC","BIS mBridge"] },
  { id:6, zone:"me", jurisdiction:"UAE", tag:"HIGH", sector:"Crypto", title:"VARA Phase II licensing framework live", time:"4h", impact:74, desc:"Full VASP authorization required by June 2026. New custody standards.", citations:["VARA Dubai"] },
  { id:7, zone:"intl", jurisdiction:"FATF", tag:"HIGH", sector:"AML", title:"FATF Travel Rule guidance updated", time:"5h", impact:71, desc:"Revised thresholds for cross-border virtual asset transfers.", citations:["FATF.org"] },
  { id:8, zone:"jp", jurisdiction:"JP", tag:"MEDIUM", sector:"AML", title:"JFSA revises crypto exchange supervision", time:"6h", impact:58, desc:"Enhanced on-site inspections for exchanges with >50k users.", citations:["JFSA"] },
];

const RADAR_DATA = [
  { axis:"Legal", VN:52, SG:91, TH:63, MY:71 },{ axis:"Enforce", VN:44, SG:88, TH:57, MY:65 },
  { axis:"Innov.", VN:68, SG:85, TH:72, MY:69 },{ axis:"Capital", VN:58, SG:76, TH:61, MY:70 },
  { axis:"AML", VN:55, SG:94, TH:67, MY:78 },{ axis:"CBDC", VN:79, SG:82, TH:58, MY:61 },
];

const VELOCITY_DATA = [
  { j:"EU", v:91 },{ j:"CN", v:88 },{ j:"US", v:84 },{ j:"VN", v:78 },
  { j:"JP", v:72 },{ j:"SG", v:65 },{ j:"TH", v:61 },
];

const FORECAST_DATA = [
  { month:"J", forecast:42, published:38 },{ month:"F", forecast:51, published:44 },
  { month:"M", forecast:58, published:62 },{ month:"A", forecast:67, published:59 },
  { month:"M", forecast:74, published:71 },{ month:"J", forecast:82, published:78 },
  { month:"J", forecast:79, published:85 },{ month:"A", forecast:88, published:82 },
  { month:"S", forecast:93, published:null },{ month:"O", forecast:97, published:null },
  { month:"N", forecast:103, published:null },{ month:"D", forecast:109, published:null },
];

const MACRO_SIGNALS = [
  { id:1, source:"FATF", event:"Travel Rule Revision 2026", score:84, target:"VN, TH, PH, ID", months:"9–14", confidence:72, domain:"AML/CFT" },
  { id:2, source:"BIS", event:"Basel IV Crypto Exposure", score:76, target:"SG, HK, AU, JP", months:"6–10", confidence:81, domain:"Capital" },
  { id:3, source:"G20", event:"Global Stablecoin Framework", score:91, target:"All G20 + SEA", months:"12–18", confidence:68, domain:"Stablecoin" },
  { id:4, source:"FSB", event:"Crypto-Asset Reporting (CARF)", score:63, target:"VN, MY, SG", months:"8–12", confidence:77, domain:"Tax" },
  { id:5, source:"IMF", event:"Article IV SEA Digital Finance", score:58, target:"VN, ID, PH", months:"3–6", confidence:89, domain:"Systemic" },
];

const RISK_ITEMS = [
  { id:1, title:"MiCA extraterritorial reach", score:88, domain:"Crypto", action:"Assess EU nexus via customer base origin", zone:"eu", trend:"up" },
  { id:2, title:"SBV payment intermediary circular", score:76, domain:"Fintech", action:"Submit consultation response within 30 days", zone:"sea", trend:"up" },
  { id:3, title:"e-CNY corridor displacement", score:83, domain:"CBDC", action:"Model revenue impact on VN remittance flows", zone:"cn", trend:"up" },
  { id:4, title:"FATF Travel Rule tightening", score:71, domain:"AML", action:"Gap-assess transaction monitoring", zone:"intl", trend:"stable" },
  { id:5, title:"STABLE Act stablecoin preemption", score:65, domain:"Stablecoin", action:"Monitor Senate floor vote timeline", zone:"us", trend:"stable" },
];

const STAKEHOLDERS = [
  { priority:1, name:"MoF — Banking & Financial Institutions", role:"Deputy Director, Policy Division", why:"Drafts licensing threshold language; pre-consultation phase is highest leverage", when:"Immediately", approach:"Technical briefing + comparative jurisdiction data", urgency:"critical" },
  { priority:2, name:"SBV — FinTech Steering Committee", role:"Committee Secretary / Senior Advisor", why:"SBV provides formal technical opinion to MoF; shapes capital & AML requirements", when:"Within 60 days", approach:"Submit position paper + request bilateral meeting", urgency:"high" },
  { priority:3, name:"Vietnam Blockchain Association", role:"Chairman / Policy Working Group Lead", why:"Industry coalition voice; co-authoring amplifies single-firm position", when:"Immediately", approach:"Propose joint industry response to consultation", urgency:"critical" },
  { priority:4, name:"National Assembly — Economic Committee", role:"Committee Staff Economist", why:"NA review is final checkpoint; staff brief the members before vote", when:"2–3 months before gazette", approach:"One-pager with economic impact data, not legal argument", urgency:"medium" },
  { priority:5, name:"IMF Resident Representative", role:"FSAP Lead / Regional Advisor", why:"Multilateral technical assistance shapes SBV internal guidance", when:"Ongoing", approach:"Share practitioner experience as technical input", urgency:"low" },
];

const ADVOCACY_CALENDAR = [
  { meeting:"MoF Policy Division", date:"Mar 20", daysLeft:4, status:"urgent", reg:"VN Payment Circular" },
  { meeting:"VBA Coalition", date:"Mar 22", daysLeft:6, status:"urgent", reg:"VN Payment Circular" },
  { meeting:"SBV FinTech Committee", date:"Apr 5", daysLeft:20, status:"upcoming", reg:"VN Payment Circular" },
  { meeting:"MAS Bilateral", date:"Apr 15", daysLeft:30, status:"upcoming", reg:"MAS AI Framework" },
  { meeting:"NA Economic Staff", date:"May 10", daysLeft:55, status:"planned", reg:"VN Payment Circular" },
];

const PREP_TIMELINE = {
  now:["Gap-assess transaction monitoring vs. new threshold","Engage legal counsel on interpretation variance","Map jurisdictions with existing exposure"],
  soon:["Update internal compliance framework draft","Prepare board briefing on upcoming obligation","Begin vendor assessment for technical tools"],
  before:["Submit public consultation response","Complete staff training and sign-off","Run mock audit against anticipated circular"],
};

const DEADLINES = [{ label:"SBV Comment", days:28, color:C.gold },{ label:"MiCA Phase II", days:7, color:C.red },{ label:"FCA Stablecoin", days:83, color:C.teal }];
const GLOBAL_RISK = 74;
const TAG_C = { CRITICAL:C.red, HIGH:C.amber, MEDIUM:C.gold, LOW:C.teal };
const UGC = { critical:C.red, high:C.amber, medium:C.gold, low:C.teal, urgent:C.red, upcoming:C.teal, planned:C.muted };

const s = {
  wrap:{ background:C.bg, color:C.text, fontFamily:"'Inter',sans-serif", minHeight:"100%", fontSize:11 },
  topbar:{ background:C.surface, borderBottom:`1px solid ${C.border}`, padding:"5px 10px", display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" },
  ticker:{ background:"#050808", borderBottom:`1px solid ${C.border}`, overflow:"hidden", height:22, display:"flex", alignItems:"center" },
  panel:{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:4, overflow:"hidden", display:"flex", flexDirection:"column" },
  ph:{ padding:"4px 8px", borderBottom:`1px solid ${C.border}`, display:"flex", alignItems:"center", justifyContent:"space-between", background:C.surface2, flexShrink:0 },
  pt:{ fontSize:9, fontWeight:700, letterSpacing:2, color:C.gold, textTransform:"uppercase" },
  scroll:{ overflowY:"auto", flex:1 },
  btn:{ background:"transparent", border:`1px solid ${C.border}`, color:C.gold, borderRadius:3, padding:"2px 7px", cursor:"pointer", fontSize:9, fontWeight:700 },
  btnP:{ background:C.gold, color:"#000", borderRadius:3, padding:"3px 8px", cursor:"pointer", fontSize:9, fontWeight:700, border:"none" },
  btnT:{ background:"transparent", border:`1px solid ${C.teal}44`, color:C.teal, borderRadius:3, padding:"2px 7px", cursor:"pointer", fontSize:9, fontWeight:700 },
  aiBox:{ background:"#0a1a18", border:`1px solid ${C.teal}55`, borderRadius:3, padding:"6px 8px", margin:"4px 6px", fontSize:9, color:"#9ecfc9", lineHeight:1.6 },
  perpBox:{ background:"#0e1520", border:`1px solid ${C.blue}55`, borderRadius:3, padding:"6px 8px", margin:"4px 6px", fontSize:9, color:"#9bb8d4", lineHeight:1.6 },
  input:{ background:C.surface2, border:`1px solid ${C.border}`, borderRadius:3, color:C.text, padding:"4px 7px", fontSize:10, width:"100%", outline:"none", boxSizing:"border-box" },
  bar:{ height:3, borderRadius:2, background:C.border, overflow:"hidden", marginTop:3 },
};

function PH({ title, extra, model }) {
  const mc = { perplexity:C.blue, mistral:"#f97316", claude:C.teal, llama:"#a78bfa" };
  return (
    <div style={s.ph}>
      <div style={{ display:"flex", alignItems:"center", gap:5 }}>
        <span style={s.pt}>{title}</span>
        {model && <span style={{ fontSize:7, padding:"1px 4px", borderRadius:2, background:`${mc[model]}18`, color:mc[model], border:`1px solid ${mc[model]}33` }}>{model.toUpperCase()}</span>}
      </div>
      {extra}
    </div>
  );
}

function SBar({ score, color }) {
  const col = color || (score>75?C.red:score>55?C.gold:C.teal);
  return <div style={s.bar}><div style={{ height:"100%", borderRadius:2, width:`${score}%`, background:col }}/></div>;
}

function Tag({ label }) {
  const c = TAG_C[label]||C.muted;
  return <span style={{ fontSize:8, fontWeight:700, padding:"1px 5px", borderRadius:2, color:c, border:`1px solid ${c}22`, background:`${c}15`, marginRight:4 }}>{label}</span>;
}

function AIOut({ text, loading, type="claude" }) {
  if (!text && !loading) return null;
  const isP = type==="perplexity";
  return (
    <div style={isP?s.perpBox:s.aiBox}>
      {loading ? <span style={{ color:isP?C.blue:C.gold }}>▌ {isP?"Perplexity searching...":"Analyzing..."}</span> : text}
    </div>
  );
}

// AI calls now route through the AEGIS API Bridge (see ./aegisApi).
// Provider keys are server-side only — no direct browser→provider calls.

function ZoneGrid({ selectedZone, onSelect, onSelectReg }) {
  const REGION_ORDER = ["North America","Europe","Asia Pacific","MENA","Americas","Africa","Global"];
  const byRegion = {};
  ZONES.forEach(z => { if (!byRegion[z.region]) byRegion[z.region] = []; byRegion[z.region].push(z); });

  return (
    <div style={{ padding:"6px 6px 0", display:"flex", flexDirection:"column", gap:4 }}>
      {REGION_ORDER.filter(r => byRegion[r]).map(region => (
        <div key={region}>
          <div style={{ fontSize:8, color:C.muted, letterSpacing:2, textTransform:"uppercase", marginBottom:3, paddingLeft:2 }}>{region}</div>
          <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
            {byRegion[region].map(zone => {
              const isSelected = selectedZone===zone.id;
              const tc = TAG_C[zone.tag]||C.muted;
              const linkedFeed = FEED_DATA.filter(f=>f.zone===zone.id);
              return (
                <div key={zone.id} onClick={() => onSelect(isSelected?null:zone.id)}
                  style={{ background:isSelected?`${zone.color}12`:C.surface2, border:`1px solid ${isSelected?zone.color:C.border}`, borderRadius:4, padding:"5px 8px", cursor:"pointer", minWidth:100, flex:"1 1 100px", transition:"all 0.15s", position:"relative" }}>
                  {isSelected && <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:zone.color, borderRadius:"4px 4px 0 0" }}/>}
                  <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:2 }}>
                    <span style={{ fontSize:10, fontWeight:700, color:isSelected?zone.color:C.text }}>{zone.label}</span>
                    <span style={{ fontSize:8, fontWeight:700, color:tc }}>{zone.score}</span>
                  </div>
                  <div style={{ display:"flex", gap:4, alignItems:"center", marginBottom:3 }}>
                    <Tag label={zone.tag}/>
                    <span style={{ fontSize:8, color:zone.trend==="up"?C.red:C.teal }}>{zone.trend==="up"?"▲":"—"}</span>
                  </div>
                  <div style={{ display:"flex", gap:3, flexWrap:"wrap", marginBottom:3 }}>
                    {zone.jurisdictions.slice(0,3).map(j=>(
                      <span key={j} style={{ fontSize:7, background:C.border, color:C.muted, padding:"0 3px", borderRadius:2 }}>{j}</span>
                    ))}
                    {zone.jurisdictions.length>3&&<span style={{ fontSize:7, color:C.muted }}>+{zone.jurisdictions.length-3}</span>}
                  </div>
                  <SBar score={zone.score} color={tc}/>
                  {linkedFeed.length>0 && (
                    <div style={{ marginTop:4, display:"flex", gap:3, flexWrap:"wrap" }}>
                      {linkedFeed.slice(0,2).map(f=>(
                        <span key={f.id} onClick={e=>{e.stopPropagation();onSelectReg(f);}}
                          style={{ fontSize:7, color:C.teal, background:`${C.teal}10`, border:`1px solid ${C.teal}22`, padding:"1px 4px", borderRadius:2, cursor:"pointer" }}>
                          ↗ {f.jurisdiction}
                        </span>
                      ))}
                      {linkedFeed.length>2&&<span style={{ fontSize:7, color:C.muted }}>+{linkedFeed.length-2}</span>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function SettingsPanel({ keys, setKeys, onClose }) {
  const [local, setLocal] = useState({...keys});
  return (
    <div style={{ position:"fixed", top:0, left:0, right:0, bottom:0, background:"#000b", zIndex:999, display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ background:C.surface, border:`1px solid ${C.gold}`, borderRadius:6, padding:18, width:360 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
          <span style={{ color:C.gold, fontWeight:700, fontSize:11, letterSpacing:2 }}>API KEYS</span>
          <button onClick={onClose} style={s.btn}>✕</button>
        </div>
        {[["perplexity","Perplexity API Key","sonar-pro · sonar-reasoning","#5b9bd5"],["mistral","Mistral API Key","mistral-large-latest","#f97316"]].map(([k,label,model,color])=>(
          <div key={k} style={{ marginBottom:10 }}>
            <div style={{ fontSize:8, color, marginBottom:3 }}>{label} <span style={{ color:C.muted }}>— {model}</span></div>
            <input type="password" style={s.input} value={local[k]||""} onChange={e=>setLocal(p=>({...p,[k]:e.target.value}))} placeholder={`Enter ${label}...`}/>
          </div>
        ))}
        <div style={{ fontSize:8, color:C.muted, marginBottom:10, padding:"5px 7px", background:C.surface2, borderRadius:3, borderLeft:`2px solid ${C.teal}` }}>
          Claude calls route automatically — no key needed.
        </div>
        <div style={{ display:"flex", gap:6 }}>
          <button style={{ ...s.btnP, flex:1 }} onClick={()=>{setKeys(local);onClose();}}>Save Keys</button>
          <button style={s.btn} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

function MonitorTab({ onSelectReg, selectedReg, apiKeys }) {
  const [selZone, setSelZone] = useState(null);
  const [expandedRisk, setExpandedRisk] = useState(null);
  const [aiTexts, setAiTexts] = useState({});
  const [aiLoading, setAiLoading] = useState({});

  const ask = async (id, ctx, useP=false) => {
    setAiLoading(p=>({...p,[id]:true})); setAiTexts(p=>({...p,[id]:""}));
    try {
      const res = await aegisApi.signalImpact({ signal: ctx, jurisdictions: ["SG", "VN"] });
      setAiTexts(p=>({...p,[id]:fmt.signalImpact(res)}));
    } catch { setAiTexts(p=>({...p,[id]:"Error."})); }
    setAiLoading(p=>({...p,[id]:false}));
  };

  const emitCriticalSignal = (signal) => {
    if (!signal) return;
    const isCritical = signal.tag === "CRITICAL" || signal.impact > 75 || signal.score > 75 || signal.lvl === "CRITICAL";
    if (!isCritical) return;
    aegisBus.emit("CRITICAL_SIGNAL", "REGO", {
      ...signal,
      source:"REGO",
      emittedAt: Date.now(),
    });
  };

  const handleFeedSelect = (item) => {
    emitCriticalSignal(item);
    onSelectReg(item);
  };

  const handleRiskToggle = (item) => {
    emitCriticalSignal(item);
    setExpandedRisk(expandedRisk===item.id?null:item.id);
  };

  const feedShown = selZone ? FEED_DATA.filter(f=>f.zone===selZone) : FEED_DATA;
  const riskShown = selZone ? RISK_ITEMS.filter(r=>r.zone===selZone||r.zone==="intl") : RISK_ITEMS;
  const zoneInfo = selZone ? ZONES.find(z=>z.id===selZone) : null;

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1.6fr 0.9fr 0.85fr", gap:6, padding:6, height:"calc(100vh - 104px)" }}>

      {/* Zone grid + radar stacked */}
      <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
        <div style={{ ...s.panel, flex:"0 0 auto" }}>
          <PH title="Jurisdiction Zones" model="claude" extra={
            <div style={{ display:"flex", gap:4, alignItems:"center" }}>
              {selZone && <span style={{ fontSize:8, color:zoneInfo?.color, fontWeight:700 }}>{zoneInfo?.label} selected</span>}
              {selZone && <button style={s.btn} onClick={()=>setSelZone(null)}>Clear</button>}
            </div>
          }/>
          <div style={{ overflowY:"auto", maxHeight:340 }}>
            <ZoneGrid selectedZone={selZone} onSelect={setSelZone} onSelectReg={onSelectReg}/>
          </div>
        </div>

        {/* Radar */}
        <div style={{ ...s.panel, flex:1 }}>
          <PH title="Jurisdiction Radar" model="mistral" extra={
            <div style={{ display:"flex", gap:6 }}>
              {[["VN",C.red],["SG",C.gold],["TH",C.teal],["MY",C.purple]].map(([k,c])=>(
                <span key={k} style={{ display:"flex", alignItems:"center", gap:3, fontSize:8, color:C.muted }}>
                  <span style={{ width:6, height:6, borderRadius:1, background:c, display:"inline-block" }}/>{k}
                </span>
              ))}
            </div>
          }/>
          <div style={{ flex:1, minHeight:0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={RADAR_DATA} margin={{ top:8, right:20, bottom:8, left:20 }}>
                <PolarGrid stroke={C.border}/>
                <PolarAngleAxis dataKey="axis" tick={{ fill:C.muted, fontSize:8 }}/>
                <Radar name="VN" dataKey="VN" stroke={C.red} fill={C.red} fillOpacity={0.12} strokeWidth={1.5}/>
                <Radar name="SG" dataKey="SG" stroke={C.gold} fill={C.gold} fillOpacity={0.08} strokeWidth={1.5}/>
                <Radar name="TH" dataKey="TH" stroke={C.teal} fill={C.teal} fillOpacity={0.08} strokeWidth={1}/>
                <Radar name="MY" dataKey="MY" stroke={C.purple} fill={C.purple} fillOpacity={0.08} strokeWidth={1}/>
                <Tooltip contentStyle={{ background:C.surface, border:`1px solid ${C.border}`, fontSize:9 }}/>
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Live Feed */}
      <div style={{ ...s.panel }}>
        <PH title={selZone?`Feed — ${zoneInfo?.label}`:"Live Regulatory Feed"} model="perplexity"
          extra={<span style={{ fontSize:8, color:C.muted }}>{feedShown.length} signals</span>}/>
        <div style={s.scroll}>
          {feedShown.map(item=>(
            <div key={item.id} style={{ padding:"6px 8px", borderBottom:`1px solid ${C.border}`, cursor:"pointer", background:selectedReg?.id===item.id?"#1a2820":"transparent" }}
              onClick={()=>handleFeedSelect(item)}>
              <div style={{ display:"flex", alignItems:"center", marginBottom:2 }}>
                <Tag label={item.tag}/>
                <span style={{ fontSize:8, background:C.surface2, padding:"0 4px", borderRadius:2, color:C.muted, marginRight:4 }}>{item.jurisdiction}</span>
                <span style={{ fontSize:8, color:C.muted, flex:1 }}>{item.sector}</span>
                <span style={{ fontSize:8, color:C.muted }}>{item.time}</span>
              </div>
              <div style={{ fontSize:10, fontWeight:600, marginBottom:2, lineHeight:1.3 }}>{item.title}</div>
              <div style={{ fontSize:9, color:C.muted, lineHeight:1.4, marginBottom:3 }}>{item.desc}</div>
              {item.citations?.length>0&&(
                <div style={{ display:"flex", gap:3, flexWrap:"wrap", marginBottom:3 }}>
                  {item.citations.map((c,i)=><span key={i} style={{ fontSize:7, color:C.blue, background:`${C.blue}12`, padding:"0 4px", borderRadius:2, border:`1px solid ${C.blue}22` }}>{c}</span>)}
                </div>
              )}
              <SBar score={item.impact} color={item.impact>75?C.red:item.impact>55?C.gold:C.teal}/>
              <div style={{ display:"flex", gap:4, marginTop:4 }}>
                <button style={s.btn} onClick={e=>{e.stopPropagation();ask(item.id,item.title+": "+item.desc);}}>Claude</button>
                <button style={{ ...s.btn, color:C.blue, borderColor:`${C.blue}33` }} onClick={e=>{e.stopPropagation();ask("p"+item.id,item.title,true);}}>Perplexity</button>
                <button style={s.btnT} onClick={e=>{e.stopPropagation();onSelectReg(item);}}>→ Fcast</button>
              </div>
              <AIOut text={aiTexts[item.id]} loading={aiLoading[item.id]} type="claude"/>
              <AIOut text={aiTexts["p"+item.id]} loading={aiLoading["p"+item.id]} type="perplexity"/>
            </div>
          ))}
        </div>
      </div>

      {/* Risk radar + velocity */}
      <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
        <div style={{ ...s.panel, flex:1.4 }}>
          <PH title="Early Risk Radar" model="mistral" extra={<span style={{ fontSize:8, color:C.red }}>{RISK_ITEMS.filter(r=>r.score>75).length} CRITICAL</span>}/>
          <div style={s.scroll}>
            {riskShown.map(item=>(
              <div key={item.id} style={{ padding:"6px 8px", borderBottom:`1px solid ${C.border}`, cursor:"pointer" }}
                onClick={()=>handleRiskToggle(item)}>
                <div style={{ display:"flex", alignItems:"center" }}>
                  <span style={{ fontSize:10, fontWeight:600, flex:1, lineHeight:1.3 }}>{item.title}</span>
                  <span style={{ fontSize:11, fontWeight:700, color:item.score>75?C.red:C.gold, marginLeft:4 }}>{item.score}</span>
                  <span style={{ fontSize:9, color:item.trend==="up"?C.red:C.teal, marginLeft:4 }}>{item.trend==="up"?"▲":"—"}</span>
                </div>
                <div style={{ display:"flex", gap:4 }}>
                  <span style={{ fontSize:8, color:C.muted }}>{item.domain}</span>
                  <span style={{ fontSize:8, color:C.muted }}>·</span>
                  <span style={{ fontSize:8, color:C.muted }}>{ZONES.find(z=>z.id===item.zone)?.label||item.zone}</span>
                </div>
                <SBar score={item.score} color={item.score>75?C.red:C.gold}/>
                {expandedRisk===item.id&&(
                  <div style={{ marginTop:4, padding:"4px 7px", background:C.surface2, borderRadius:3, fontSize:9, color:C.muted, borderLeft:`2px solid ${C.gold}` }}>
                    <span style={{ color:C.gold, fontWeight:600 }}>→ </span>{item.action}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div style={{ ...s.panel, flex:1 }}>
          <PH title="Regulatory Velocity" model="mistral" extra={<span style={{ fontSize:8, color:C.muted }}>7 jurisdictions</span>}/>
          <div style={{ flex:1, minHeight:0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={VELOCITY_DATA} layout="vertical" margin={{ top:4, right:20, left:6, bottom:4 }}>
                <XAxis type="number" tick={{ fill:C.muted, fontSize:8 }} axisLine={false} tickLine={false} domain={[0,100]}/>
                <YAxis type="category" dataKey="j" tick={{ fill:C.muted, fontSize:9 }} axisLine={false} tickLine={false} width={20}/>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" horizontal={false}/>
                <Tooltip contentStyle={{ background:C.surface, border:`1px solid ${C.border}`, fontSize:9 }}/>
                <Bar dataKey="v" name="Velocity" radius={[0,2,2,0]} maxBarSize={12}>
                  {VELOCITY_DATA.map((d,i)=>(
                    <rect key={i} fill={d.v>80?C.red:d.v>65?C.gold:C.teal}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Board strip */}
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:4, padding:"6px 9px" }}>
          <div style={{ fontSize:8, color:C.gold, fontWeight:700, letterSpacing:1, marginBottom:4 }}>BOARD STRIP</div>
          <div style={{ display:"flex", alignItems:"baseline", gap:4, marginBottom:4 }}>
            <span style={{ fontSize:8, color:C.muted }}>Global Risk</span>
            <span style={{ fontSize:18, fontWeight:700, color:C.red, lineHeight:1 }}>{GLOBAL_RISK}</span>
            <span style={{ fontSize:8, color:C.muted }}>/100</span>
          </div>
          {DEADLINES.map((d,i)=>(
            <div key={i} style={{ display:"flex", alignItems:"center", gap:6, marginBottom:3 }}>
              <span style={{ fontSize:8, color:C.muted, flex:1 }}>{d.label}</span>
              <span style={{ fontSize:9, fontWeight:700, color:d.color }}>{d.days}d</span>
              <div style={{ width:50, height:3, borderRadius:2, background:C.border, overflow:"hidden" }}>
                <div style={{ height:"100%", width:`${Math.max(5,(90-d.days)/90*100)}%`, background:d.color, borderRadius:2 }}/>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ForecastTab({ selectedReg, apiKeys }) {
  const [selSig, setSelSig] = useState(MACRO_SIGNALS[0]);
  const [simText, setSimText] = useState(""); const [simLoading, setSimLoading] = useState(false);
  const [chartData, setChartData] = useState(null); const [chartLoading, setChartLoading] = useState(false);
  const [checked, setChecked] = useState({});

  const done = p => PREP_TIMELINE[p].filter((_,i)=>checked[`${p}-${i}`]).length;

  const runSim = async () => {
    setSimLoading(true); setSimText("");
    try {
      const res = await aegisApi.whatIf({ signal: `${selSig.event} (${selSig.source})`, levers: { domain: selSig.domain, months: selSig.months } });
      setSimText(fmt.whatIf(res));
    } catch { setSimText("Error."); }
    setSimLoading(false);
  };

  const genChart = async () => {
    setChartLoading(true);
    try {
      const arr = await aegisApi.riskProjection({ domain: selSig.domain });
      setChartData(Array.isArray(arr) ? arr : []);
    } catch { setChartData([{j:"VN",current:70,projected:85},{j:"SG",current:60,projected:65},{j:"TH",current:55,projected:70},{j:"MY",current:58,projected:68},{j:"ID",current:62,projected:78},{j:"PH",current:50,projected:65}]); }
    setChartLoading(false);
  };

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gridTemplateRows:"1fr 1fr", gap:6, padding:6, height:"calc(100vh - 104px)" }}>

      <div style={s.panel}>
        <PH title="Macro Transmission Monitor" model="perplexity" extra={<span style={{ fontSize:8, color:C.muted }}>FATF · BIS · G20 · FSB · IMF</span>}/>
        <div style={s.scroll}>
          {MACRO_SIGNALS.map(sig=>(
            <div key={sig.id} onClick={()=>setSelSig(sig)}
              style={{ padding:"7px 9px", borderBottom:`1px solid ${C.border}`, cursor:"pointer", background:selSig?.id===sig.id?"#1a2020":"transparent", borderLeft:selSig?.id===sig.id?`2px solid ${C.gold}`:"2px solid transparent" }}>
              <div style={{ display:"flex", alignItems:"center", marginBottom:2 }}>
                <span style={{ fontSize:8, fontWeight:700, color:C.gold, background:"#2a1e08", padding:"0 5px", borderRadius:2, marginRight:6 }}>{sig.source}</span>
                <span style={{ fontSize:8, color:C.muted, flex:1 }}>{sig.domain}</span>
                <span style={{ fontSize:11, fontWeight:700, color:sig.score>80?C.red:C.gold }}>{sig.score}</span>
              </div>
              <div style={{ fontSize:10, fontWeight:600, marginBottom:2 }}>{sig.event}</div>
              <div style={{ display:"flex", gap:6, fontSize:8, color:C.muted }}>
                <span>→ {sig.target}</span><span>·</span>
                <span>{sig.months}mo</span><span>·</span>
                <span style={{ color:C.teal }}>{sig.confidence}% conf.</span>
              </div>
              <SBar score={sig.score} color={sig.score>80?C.red:C.gold}/>
            </div>
          ))}
        </div>
      </div>

      <div style={s.panel}>
        <PH title="Policy Forecast vs. Published" model="claude" extra={
          <div style={{ display:"flex", gap:8 }}>
            <span style={{ fontSize:8, color:C.gold, display:"flex", alignItems:"center", gap:3 }}><span style={{ width:8, height:1, borderTop:`1px dashed ${C.gold}`, display:"inline-block" }}/>Forecast</span>
            <span style={{ fontSize:8, color:C.teal, display:"flex", alignItems:"center", gap:3 }}><span style={{ width:8, height:2, background:C.teal, display:"inline-block" }}/>Published</span>
          </div>
        }/>
        <div style={{ flex:1 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={FORECAST_DATA} margin={{ top:10, right:12, left:-14, bottom:4 }}>
              <defs>
                <linearGradient id="gf" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={C.gold} stopOpacity={0.2}/><stop offset="95%" stopColor={C.gold} stopOpacity={0}/></linearGradient>
                <linearGradient id="gp" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={C.teal} stopOpacity={0.2}/><stop offset="95%" stopColor={C.teal} stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false}/>
              <XAxis dataKey="month" tick={{ fill:C.muted, fontSize:8 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill:C.muted, fontSize:8 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{ background:C.surface, border:`1px solid ${C.border}`, fontSize:9 }}/>
              <Area type="monotone" dataKey="forecast" stroke={C.gold} fill="url(#gf)" strokeWidth={1.5} dot={false} strokeDasharray="5 3" name="Forecast"/>
              <Area type="monotone" dataKey="published" stroke={C.teal} fill="url(#gp)" strokeWidth={2} dot={{ r:2, fill:C.teal }} connectNulls={false} name="Published"/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={s.panel}>
        <PH title="What-If Simulation" model="perplexity" extra={
          <div style={{ display:"flex", gap:4 }}>
            <button style={s.btnP} onClick={runSim}>{simLoading?"...":"▶ Simulate"}</button>
            <button style={{ ...s.btn, color:"#f97316", borderColor:"#f9731633" }} onClick={genChart}>{chartLoading?"...":"Mistral Chart"}</button>
          </div>
        }/>
        <div style={s.scroll}>
          <div style={{ padding:"6px 8px", background:C.surface2, margin:"5px 6px", borderRadius:3 }}>
            <div style={{ fontSize:8, color:C.muted, marginBottom:1 }}>SELECTED SIGNAL</div>
            <div style={{ fontSize:10, fontWeight:600, color:C.gold }}>{selSig?.event}</div>
            <div style={{ fontSize:8, color:C.muted, marginTop:1 }}>{selSig?.source} · {selSig?.target} · {selSig?.months}mo · {selSig?.confidence}% conf.</div>
          </div>
          {selectedReg&&<div style={{ margin:"0 6px 4px", padding:"3px 6px", background:"#0a1a10", borderRadius:3, fontSize:9, color:C.teal, border:`1px solid ${C.teal}22` }}>↗ Linked: {selectedReg.title}</div>}
          <AIOut text={simText} loading={simLoading} type="perplexity"/>
          {chartData&&(
            <div style={{ height:160, paddingRight:8 }}>
              <div style={{ fontSize:8, color:C.muted, padding:"2px 8px 4px" }}>Mistral risk projection — {selSig?.domain}</div>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top:4, right:10, left:-14, bottom:4 }}>
                  <XAxis dataKey="j" tick={{ fill:C.muted, fontSize:8 }} axisLine={false} tickLine={false}/>
                  <YAxis tick={{ fill:C.muted, fontSize:8 }} axisLine={false} tickLine={false} domain={[0,100]}/>
                  <Tooltip contentStyle={{ background:C.surface, border:`1px solid ${C.border}`, fontSize:9 }}/>
                  <Bar dataKey="current" name="Current" fill={C.teal} radius={[2,2,0,0]} maxBarSize={14}/>
                  <Bar dataKey="projected" name="Projected" fill={C.red} radius={[2,2,0,0]} maxBarSize={14} fillOpacity={0.75}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          {!simText&&!simLoading&&!chartData&&<div style={{ color:C.muted, fontSize:9, textAlign:"center", padding:"20px 0" }}>Select a signal · click Simulate or Mistral Chart</div>}
        </div>
      </div>

      <div style={s.panel}>
        <PH title="Preparation Timeline" model="claude" extra={<span style={{ fontSize:8, color:C.muted }}>{Object.values(checked).filter(Boolean).length}/{Object.values(PREP_TIMELINE).flat().length} done</span>}/>
        <div style={s.scroll}>
          {[["now","NOW — 0–3 months",C.red],["soon","SOON — 3–6 months",C.gold],["before","BEFORE ENFORCEMENT",C.teal]].map(([phase,label,color])=>(
            <div key={phase} style={{ padding:"7px 9px", borderBottom:`1px solid ${C.border}` }}>
              <div style={{ display:"flex", alignItems:"center", marginBottom:5 }}>
                <span style={{ fontSize:8, fontWeight:700, color, letterSpacing:1 }}>{label}</span>
                <span style={{ fontSize:8, color:C.muted, marginLeft:"auto" }}>{done(phase)}/{PREP_TIMELINE[phase].length}</span>
              </div>
              {PREP_TIMELINE[phase].map((item,i)=>(
                <div key={i} onClick={()=>setChecked(p=>({...p,[`${phase}-${i}`]:!p[`${phase}-${i}`]}))}
                  style={{ display:"flex", alignItems:"flex-start", gap:6, marginBottom:5, cursor:"pointer" }}>
                  <div style={{ width:9, height:9, border:`1px solid ${color}`, borderRadius:2, flexShrink:0, marginTop:1, background:checked[`${phase}-${i}`]?color:"transparent", display:"flex", alignItems:"center", justifyContent:"center" }}>
                    {checked[`${phase}-${i}`]&&<span style={{ fontSize:6, color:"#000", fontWeight:700 }}>✓</span>}
                  </div>
                  <span style={{ fontSize:9, color:checked[`${phase}-${i}`]?C.muted:C.text, textDecoration:checked[`${phase}-${i}`]?"line-through":"none", lineHeight:1.4 }}>{item}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AdvocateTab({ selectedReg, apiKeys }) {
  const [selStk, setSelStk] = useState(STAKEHOLDERS[0]);
  const [briefing, setBriefing] = useState(""); const [bLoading, setBLoading] = useState(false);
  const [org, setOrg] = useState("Singapore/Vietnam fintech — crypto exchange and CBDC infrastructure");
  const [reg, setReg] = useState("Vietnam Crypto Exchange Licensing Framework");
  const [list, setList] = useState(null); const [lLoading, setLLoading] = useState(false);

  useEffect(()=>{ if(selectedReg) setReg(selectedReg.title); },[selectedReg]);

  const genList = async () => {
    setLLoading(true); setList(null);
    try {
      const arr = await aegisApi.stakeholderMap({ regulation: reg, org });
      setList(Array.isArray(arr) ? arr : STAKEHOLDERS);
    } catch { setList(STAKEHOLDERS); }
    setLLoading(false);
  };

  const genBrief = async () => {
    setBLoading(true); setBriefing("");
    try {
      const res = await aegisApi.advocacyBrief({ org, regulation: reg, stakeholder_name: selStk.name, stakeholder_role: selStk.role, why: selStk.why });
      setBriefing(fmt.advocacyBrief(res));
    } catch { setBriefing("Error."); }
    setBLoading(false);
  };

  const stks = list||STAKEHOLDERS;

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gridTemplateRows:"auto 1fr", gap:6, padding:6, height:"calc(100vh - 104px)" }}>
      <div style={{ ...s.panel, gridColumn:"1 / 3" }}>
        <PH title="Advocacy Intelligence Setup" model="claude"/>
        <div style={{ padding:"7px 10px", display:"grid", gridTemplateColumns:"1fr 1fr auto auto", gap:8, alignItems:"end" }}>
          <div>
            <div style={{ fontSize:8, color:C.muted, marginBottom:3 }}>TARGET REGULATION</div>
            <input style={s.input} value={reg} onChange={e=>setReg(e.target.value)}/>
          </div>
          <div>
            <div style={{ fontSize:8, color:C.muted, marginBottom:3 }}>ORG PROFILE</div>
            <input style={s.input} value={org} onChange={e=>setOrg(e.target.value)}/>
          </div>
          <button style={s.btnP} onClick={genList}>{lLoading?"Generating...":"AI Gen Stakeholders"}</button>
          {selectedReg&&<span style={{ fontSize:8, color:C.teal, background:"#0a1a14", padding:"4px 7px", borderRadius:3, whiteSpace:"nowrap" }}>↗ {selectedReg.title.slice(0,28)}...</span>}
        </div>
      </div>

      <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
        <div style={{ ...s.panel, flex:1.5 }}>
          <PH title="Stakeholder Meeting List" model="claude" extra={<span style={{ fontSize:8, color:C.muted }}>{stks.length} meetings</span>}/>
          <div style={s.scroll}>
            {stks.map((item,i)=>{
              const uc=UGC[item.urgency]||C.muted;
              return (
                <div key={i} onClick={()=>setSelStk(item)}
                  style={{ padding:"6px 8px", borderBottom:`1px solid ${C.border}`, cursor:"pointer", background:selStk?.name===item.name?"#1a2020":"transparent", borderLeft:selStk?.name===item.name?`2px solid ${C.gold}`:"2px solid transparent" }}>
                  <div style={{ display:"flex", alignItems:"center", marginBottom:2 }}>
                    <span style={{ fontSize:7, color:uc, border:`1px solid ${uc}33`, padding:"0 4px", borderRadius:2, marginRight:5 }}>{(item.urgency||"").toUpperCase()}</span>
                    <span style={{ fontSize:10, fontWeight:600, flex:1 }}>{item.name}</span>
                    {item.priority&&<span style={{ fontSize:8, color:C.muted }}>#{item.priority}</span>}
                  </div>
                  <div style={{ fontSize:8, color:C.gold, marginBottom:1 }}>{item.role}</div>
                  <div style={{ fontSize:8, color:C.muted, lineHeight:1.4 }}>{item.why}</div>
                  <div style={{ fontSize:8, color:C.teal, marginTop:2 }}>⏱ {item.when}</div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ ...s.panel, flex:1 }}>
          <PH title="Advocacy Calendar" model="claude" extra={<span style={{ fontSize:8, color:C.red }}>{ADVOCACY_CALENDAR.filter(c=>c.status==="urgent").length} URGENT</span>}/>
          <div style={s.scroll}>
            {ADVOCACY_CALENDAR.map((item,i)=>{
              const uc=UGC[item.status]||C.muted;
              const pct=Math.max(5,Math.min(100,100-(item.daysLeft/90)*100));
              return (
                <div key={i} style={{ padding:"5px 8px", borderBottom:`1px solid ${C.border}` }}>
                  <div style={{ display:"flex", alignItems:"center" }}>
                    <span style={{ fontSize:10, fontWeight:600, flex:1 }}>{item.meeting}</span>
                    <span style={{ fontSize:9, fontWeight:700, color:uc }}>{item.daysLeft}d</span>
                  </div>
                  <div style={{ display:"flex", gap:4, marginBottom:3 }}>
                    <span style={{ fontSize:8, color:C.muted }}>{item.date} · {item.reg}</span>
                  </div>
                  <div style={{ height:3, borderRadius:2, background:C.border }}>
                    <div style={{ height:"100%", borderRadius:2, width:`${pct}%`, background:item.daysLeft<10?C.red:item.daysLeft<30?C.gold:C.teal }}/>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ ...s.panel }}>
          <PH title="Coalition Map" model="claude"/>
          <div style={{ padding:"7px 9px" }}>
            {[["Nami Foundation / VNST",91,"CBDC + stablecoin positioning"],["Vietnam Fintech Association",78,"Payment licensing reform"],["ACCESS Singapore",65,"MAS/SBV cross-border alignment"]].map(([n,sc,b],i)=>(
              <div key={i} style={{ marginBottom:6 }}>
                <div style={{ display:"flex" }}>
                  <span style={{ fontSize:9, fontWeight:600, flex:1 }}>{n}</span>
                  <span style={{ fontSize:9, fontWeight:700, color:sc>85?C.teal:C.gold }}>{sc}%</span>
                </div>
                <div style={{ fontSize:8, color:C.muted, marginBottom:2 }}>{b}</div>
                <SBar score={sc} color={sc>85?C.teal:C.gold}/>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ ...s.panel }}>
        <PH title="Meeting Briefing Pack" model="claude" extra={
          <button style={s.btnP} onClick={genBrief}>{bLoading?"Generating...":"Generate Brief"}</button>
        }/>
        {selStk&&(
          <div style={{ padding:"6px 9px", borderBottom:`1px solid ${C.border}`, background:C.surface2 }}>
            <div style={{ fontSize:10, fontWeight:600 }}>{selStk.name}</div>
            <div style={{ fontSize:8, color:C.gold }}>{selStk.role}</div>
            <div style={{ fontSize:8, color:C.muted, marginTop:1 }}>Approach: {selStk.approach}</div>
          </div>
        )}
        <div style={{ ...s.scroll, padding:4 }}>
          <AIOut text={briefing} loading={bLoading} type="claude"/>
          {!briefing&&!bLoading&&<div style={{ color:C.muted, fontSize:9, textAlign:"center", padding:"20px 0" }}>Select a stakeholder · click Generate Brief</div>}
        </div>
      </div>
    </div>
  );
}

export default function REGO() {
  const [tab, setTab] = useState("monitor");
  const [selectedReg, setSelectedReg] = useState(null);
  const [boardText, setBoardText] = useState(""); const [boardLoading, setBoardLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeys, setApiKeys] = useState({ perplexity:"", mistral:"" });
  const [ts, setTs] = useState("");

  useEffect(()=>{ const t=setInterval(()=>setTs(new Date().toLocaleTimeString("en-GB",{hour12:false})),1000); return()=>clearInterval(t); },[]);

  const genBoard = async () => {
    setBoardLoading(true); setBoardText("");
    try {
      const res = await aegisApi.brief({ topic: "Board GRC brief, 2 sentences, CEO-level, no jargon. Global risk 74/100. Top risks: MiCA Phase II (EU), SBV Circular (VN), e-CNY SEA expansion. Urgent: MoF Vietnam in 4 days." });
      setBoardText(res?.summary || "No response.");
    } catch { setBoardText("Error."); }
    setBoardLoading(false);
  };

  return (
    <div style={s.wrap}>
      {showSettings&&<SettingsPanel keys={apiKeys} setKeys={setApiKeys} onClose={()=>setShowSettings(false)}/>}

      {boardText&&(
        <div style={{ background:"#0a1a14", borderBottom:`1px solid ${C.teal}44`, padding:"5px 14px", fontSize:10, color:"#9ecfc9", display:"flex", gap:8, alignItems:"flex-start" }}>
          <span style={{ color:C.gold, fontWeight:700, fontSize:8, whiteSpace:"nowrap", marginTop:1 }}>BOARD · CLAUDE</span>
          <span style={{ flex:1 }}>{boardText}</span>
          <button onClick={()=>setBoardText("")} style={{ ...s.btn, fontSize:8, padding:"1px 5px" }}>✕</button>
        </div>
      )}

      {tab==="monitor"&&<MonitorTab onSelectReg={setSelectedReg} selectedReg={selectedReg} apiKeys={apiKeys}/>}
      {tab==="forecast"&&<ForecastTab selectedReg={selectedReg} apiKeys={apiKeys}/>}
      {tab==="advocate"&&<AdvocateTab selectedReg={selectedReg} apiKeys={apiKeys}/>}
    </div>
  );
}
