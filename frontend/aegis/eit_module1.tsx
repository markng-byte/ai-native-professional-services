import { useState, useRef, useEffect, useCallback } from "react";
import { aegisApi, type SseEvent } from "./aegisApi";
import { useAegisStore } from "./aegisStore";


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
  orange:"#f08040",
  shadow:"0 4px 24px rgba(0,0,0,0.6)",
  glow:"0 0 16px rgba(61,232,160,0.18)",
};

const ROLES={
  lv1:[{id:"analyst",label:"Analyst",icon:"◈"},{id:"associate",label:"Associate",icon:"⬡"},{id:"manager",label:"Manager",icon:"▦"}],
  lv2:[{id:"vp",label:"VP / Director",icon:"◇"},{id:"c_suite",label:"C-Suite",icon:"★"},{id:"board",label:"Board Member",icon:"⊞"}],
};
const SECTORS=["Financial Services","Technology","Energy","Real Estate","Healthcare","Consumer","Industrials","Agriculture","Crypto/Web3","Shipping"];
const GEOS=["Vietnam","Southeast Asia","Greater China","South Asia","Global","US & Americas","Europe","Middle East"];
const ASSETS=["Equities","Fixed Income","Real Estate","Private Equity","Commodities","Digital Assets","FX","Infrastructure"];
const RISK_LEVELS=["Conservative","Moderate","Aggressive","Opportunistic"];
const TICKET_TYPES=["Trend Outlook","Industry Analysis","Specific Subject Analysis"];
const ACTION_COLOR={Escalate:C.red,Act:C.gold,Investigate:C.blue,Monitor:C.green};
const POSTURE_COLOR={Overweight:C.green,Neutral:C.muted,Underweight:C.orange,Hedge:C.blue,Avoid:C.red};
const PIPELINE_STAGES=[
  {id:"ingest",label:"INGEST",icon:"⬇"},
  {id:"categorize",label:"CATEG.",icon:"🏷"},
  {id:"verify",label:"VERIFY",icon:"✔"},
  {id:"filter",label:"FILTER",icon:"▽"},
  {id:"cluster",label:"CLUSTER",icon:"⬡"},
  {id:"synthesize",label:"SYNTH.",icon:"◇"},
  {id:"score",label:"SCORE",icon:"▲"},
  {id:"review",label:"REVIEW",icon:"👁"},
];

const SAMPLE_INTEL=[
  {id:"s1",title:"SBV Signals Accelerated CBDC Pilot to 5 Commercial Banks",category:"REGULATORY",impactScore:92,credibilityScore:88,suggestedAction:"Escalate",synthesis:"The State Bank of Vietnam has informally signaled intent to broaden its CBDC pilot beyond MB Bank to include BIDV, VietinBank, Techcombank and VPBank by Q3 2026. Infrastructure readiness assessments are underway, materially accelerating the digital currency timeline ahead of the 2025–2030 fintech framework.",keyRisks:["Regulatory sequencing risk if NQ57 amendments delayed","Interoperability friction between legacy systems","Potential exclusion of non-bank fintech players"],devAngle:"Expansion may be performative ahead of NQ57 review rather than operationally driven.",relevantLinks:[{label:"SBV Digital Currency Framework",age:"2h ago",live:false},{label:"NQ57-NQ/TW Full Text",age:"1d ago",live:false},{label:"MB Bank CBDC Pilot Report",age:"3d ago",live:false}],publisher:"Harvey N.",publishedAt:"Today 08:14",freshness:"24h",priority:"high",status:"published"},
  {id:"s2",title:"Vietnam Q1 2026 FDI Inflows Surge 34% YoY — Tech & Manufacturing Lead",category:"MACRO",impactScore:85,credibilityScore:91,suggestedAction:"Act",synthesis:"FDI commitments reached USD 8.4B in Q1 2026 with semiconductor supply chain relocation from China accounting for 41% of registered capital. South Korean and Taiwanese investors dominate.",keyRisks:["Infrastructure bottlenecks in northern industrial zones","Power grid capacity constraints","Skilled labor shortage"],devAngle:"Headline FDI may overstate actual disbursed capital — tracking ratio at ~62%.",relevantLinks:[{label:"MPI FDI Report Q1/2026",age:"6h ago",live:false},{label:"Samsung Vietnam Expansion",age:"1d ago",live:false}],publisher:"Minh T.",publishedAt:"Today 07:50",freshness:"24h",priority:"high",status:"published"},
  {id:"s3",title:"Grab–SeaMoney Merger Talks Resurface; SEA Super-App Consolidation Looms",category:"SECTOR",impactScore:82,credibilityScore:71,suggestedAction:"Investigate",synthesis:"Multiple sources indicate renewed M&A dialogue between Grab Financial and Sea's financial arm, potentially creating a dominant SEA digital financial infrastructure player with a USD 120B addressable market.",keyRisks:["Antitrust exposure in SG, VN, ID","Integration complexity across 8 jurisdictions","Culture clash risk"],devAngle:"Previous talks in 2024 collapsed on valuation — current climate may not differ.",relevantLinks:[{label:"Bloomberg Tech SEA",age:"3h ago",live:false},{label:"SSC Licensing Update",age:"2d ago",live:false}],publisher:"Harvey N.",publishedAt:"Yesterday 16:30",freshness:"week",priority:"high",status:"published"},
  {id:"s4",title:"Fed Signals 2 Additional Cuts H2 2026 — EM Capital Flow Reversal Anticipated",category:"MACRO",impactScore:80,credibilityScore:95,suggestedAction:"Act",synthesis:"Federal Reserve minutes confirmed a dovish tilt with two 25bp cuts projected for Q3 and Q4 2026. VN-Index historically showing +8–12% sensitivity to Fed easing cycles with 60–90 day lag.",keyRisks:["US inflation re-acceleration","USD weakening may not translate to VND strength","Hot money volatility"],devAngle:"Vietnam's current account surplus limits upside sensitivity to external capital flows.",relevantLinks:[{label:"FOMC March 2026 Minutes",age:"1h ago",live:false},{label:"EM Capital Flow Tracker",age:"4h ago",live:false}],publisher:"Lan P.",publishedAt:"Today 09:02",freshness:"24h",priority:"high",status:"published"},
  {id:"s5",title:"Thông Tư 15 Creates Compliance Gap for 200+ Vietnamese Crypto Entities",category:"REGULATORY",impactScore:78,credibilityScore:84,suggestedAction:"Act",synthesis:"Thông tư 15/2026/TT-BTC mandates IFRS-adjacent crypto accounting for exchanges, custodians and institutional investors by June 2026. An estimated 200+ entities lack compliant reporting infrastructure.",keyRisks:["Regulatory timeline may slip","Audit firm readiness gap","Scope creep to individual investors"],devAngle:"MoF circulars historically have 6–12 month enforcement grace period.",relevantLinks:[{label:"Thông tư 15/2026/TT-BTC",age:"2d ago",live:false}],publisher:"Harvey N.",publishedAt:"Yesterday 11:20",freshness:"week",priority:"high",status:"published"},
  {id:"s6",title:"Mekong Delta Flooding Triggers Agricultural Price Shock",category:"COMMODITY",impactScore:74,credibilityScore:87,suggestedAction:"Investigate",synthesis:"Severe flooding across An Giang, Đồng Tháp and Kiên Giang has damaged ~180,000 hectares of winter-spring rice crop. Global rice markets already pricing in a 4–7% supply reduction from Vietnam.",keyRisks:["Export ban strains bilateral agreements","Insurance payout capacity under pressure","Input company margin compression"],devAngle:"Government may prefer targeted subsidies over export controls given WTO obligations.",relevantLinks:[{label:"MARD Flood Assessment",age:"12h ago",live:false},{label:"Global Rice Futures — CME",age:"live",live:true}],publisher:"Minh T.",publishedAt:"Today 06:45",freshness:"24h",priority:"moderate",status:"published"},
  {id:"s7",title:"Microsoft Azure USD 2.1B Vietnam Data Center — Largest Tech FDI",category:"TECHNOLOGY",impactScore:71,credibilityScore:93,suggestedAction:"Monitor",synthesis:"Microsoft confirmed a USD 2.1B data center investment in Hà Nam province expected to accelerate cloud adoption across FSI, government and healthcare sectors.",keyRisks:["Land clearance and permitting delays","EVN grid reliability dependency","Talent localization requirements"],devAngle:"Investment may be driven primarily by US diplomatic optics.",relevantLinks:[{label:"Microsoft Vietnam Press Release",age:"2d ago",live:false}],publisher:"Lan P.",publishedAt:"Yesterday 14:00",freshness:"week",priority:"moderate",status:"published"},
  {id:"s8",title:"SSC Crypto Licensing: 3 Advance, 12 Rejected in Round One",category:"REGULATORY",impactScore:70,credibilityScore:89,suggestedAction:"Act",synthesis:"Vietnam's SSC advanced 3 crypto exchange applications to final review while rejecting 12 for inadequate AML/KYC infrastructure. Licensed operators expected by Q4 2026.",keyRisks:["Licensing delay creates uncertainty","Grey zone operators continue","Capital requirements exclude smaller players"],devAngle:"SSC may face political pressure to license a state-affiliated entity preferentially.",relevantLinks:[{label:"Decision 96/QĐ-BTC",age:"3d ago",live:false}],publisher:"Harvey N.",publishedAt:"2 days ago",freshness:"week",priority:"high",status:"published"},
  {id:"s9",title:"HOSE ESG Disclosure Mandate from FY2027 — Draft Circular Released",category:"ESG",impactScore:65,credibilityScore:82,suggestedAction:"Monitor",synthesis:"HOSE released a draft circular mandating GRI-aligned ESG disclosure for all listed companies from FY2027. ~340 firms affected.",keyRisks:["ESG reporting capacity gap","Greenwashing risk","Foreign expectations exceed local standards"],devAngle:"HOSE lacks enforcement track record on disclosure mandates.",relevantLinks:[{label:"HOSE Draft Circular",age:"4d ago",live:false}],publisher:"Minh T.",publishedAt:"3 days ago",freshness:"week",priority:"monitoring",status:"published"},
  {id:"s10",title:"Indonesia–Vietnam Partnership — Joint Industrial Zones Proposed",category:"GEOPOLITICAL",impactScore:63,credibilityScore:80,suggestedAction:"Monitor",synthesis:"State visits produced a joint declaration proposing co-developed industrial zones at the Batam–Vietnam maritime corridor targeting USD 15B bilateral trade by 2028.",keyRisks:["Bureaucratic coordination challenges","Political change risk post-election","Financing structure undefined"],devAngle:"Joint zone proposals historically take 5–7 years to operationalize in ASEAN.",relevantLinks:[{label:"MoFA Joint Statement",age:"2d ago",live:false}],publisher:"Lan P.",publishedAt:"3 days ago",freshness:"week",priority:"monitoring",status:"published"},
  {id:"s11",title:"VN-Index Breaks 1,450 — Foreign Net Buying Signals EM Re-rating",category:"MACRO",impactScore:75,credibilityScore:90,suggestedAction:"Act",synthesis:"Foreign investors net bought VND 2.3 trillion on HOSE in the past 5 sessions. FTSE Russell upgrade watch status remains a key catalyst. Financials and real estate lead the rally.",keyRisks:["Reversal risk if USD strengthens","Thin liquidity","Retail margin leverage elevated"],devAngle:"Foreign buying may reflect index rebalancing rather than fundamental conviction.",relevantLinks:[{label:"HOSE Market Data",age:"live",live:true}],publisher:"Harvey N.",publishedAt:"Today 10:30",freshness:"24h",priority:"high",status:"published"},
  {id:"s12",title:"Vietnam Shipbuilding Eyes Top-10 Global Ranking — Order Backlog +28%",category:"SECTOR",impactScore:62,credibilityScore:78,suggestedAction:"Investigate",synthesis:"SBIC reports a 28% increase in international order backlog for 2026–2028 driven by Hyundai Vietnam Shipbuilding and Damen Song Cam.",keyRisks:["Steel input cost inflation","Skilled labor shortage","Quality certification gaps"],devAngle:"Global shipping cycle is peaking — backlog could deteriorate if freight rates soften.",relevantLinks:[{label:"SBIC Annual Report 2025",age:"1w ago",live:false},{label:"Baltic Dry Index",age:"live",live:true}],publisher:"Minh T.",publishedAt:"4 days ago",freshness:"week",priority:"moderate",status:"published"},
  {id:"s13",title:"CypherCore Japan–Vietnam Quantum Security MOU",category:"TECHNOLOGY",impactScore:68,credibilityScore:75,suggestedAction:"Investigate",synthesis:"CypherCore Japan signed an MOU with Vietnam's MIC for post-quantum cryptography infrastructure across government financial systems. Estimated contract value USD 40–80M.",keyRisks:["Technology readiness gap","Budget allocation risk","Standards alignment unclear"],devAngle:"MOU is non-binding; actual contract award typically runs 18–36 months.",relevantLinks:[{label:"MIC Press Release",age:"3d ago",live:false}],publisher:"Harvey N.",publishedAt:"4 days ago",freshness:"week",priority:"moderate",status:"published"},
  {id:"s14",title:"Resolution 05/2025 Crypto Pilot Rules Finalized — DeFi Explicitly Excluded",category:"REGULATORY",impactScore:73,credibilityScore:86,suggestedAction:"Act",synthesis:"Implementing regulations clarify the pilot covers exchange operation, custody and institutional investment but explicitly excludes DeFi protocols and self-custodied assets.",keyRisks:["DeFi exclusion pushes activity offshore","Tax uncertainty blocks institutional entry","Pilot scope may be further narrowed"],devAngle:"Five-year pilot framing allows government to reverse course without formal legislative repeal.",relevantLinks:[{label:"Resolution 05 Implementing Decree",age:"5d ago",live:false}],publisher:"Lan P.",publishedAt:"5 days ago",freshness:"week",priority:"high",status:"published"},
  {id:"s15",title:"Da Nang Smart City Phase 2 — USD 380M AI & IoT Procurement Opens",category:"TECHNOLOGY",impactScore:58,credibilityScore:77,suggestedAction:"Monitor",synthesis:"Da Nang opened procurement for Phase 2 covering traffic AI, environmental IoT and integrated citizen services. Cisco, Huawei, Viettel and two Korean consortia pre-qualified.",keyRisks:["Huawei participation triggers US investor sensitivity","Procurement extends 2x historically","Data sovereignty requirements"],devAngle:"Phase 1 KPI achievement rate was only ~55%.",relevantLinks:[{label:"Da Nang Smart City Portal",age:"1w ago",live:false}],publisher:"Minh T.",publishedAt:"5 days ago",freshness:"week",priority:"monitoring",status:"published"},
  {id:"s16",title:"Vietnam Ranked #2 SEA Private Credit Target — Preqin H1 2026",category:"CREDIT",impactScore:67,credibilityScore:83,suggestedAction:"Investigate",synthesis:"Preqin ranks Vietnam #2 in SEA for direct lending in 2026. Key drivers: underpenetrated bank credit and USD 4–8% net yield advantage over comparable IG bonds.",keyRisks:["FX risk on USD-denominated facilities","Bankruptcy code limitations","Limited secondary liquidity"],devAngle:"Survey-based ranking; actual deployed capital remains well below Indonesia.",relevantLinks:[{label:"Preqin SEA Private Credit H1 2026",age:"1w ago",live:false}],publisher:"Harvey N.",publishedAt:"6 days ago",freshness:"week",priority:"moderate",status:"published"},
  {id:"s17",title:"Hanoi Urban Heat Island — Parametric Insurance Market Emerging",category:"ESG",impactScore:55,credibilityScore:72,suggestedAction:"Monitor",synthesis:"WMO data shows Hanoi's urban core recorded 42 mean tropical nights in 2025. MOF ISA held its first stakeholder workshop on parametric product approvals in February 2026.",keyRisks:["Basis risk in parametric triggers","Regulatory pathway undefined","Low insurance literacy"],devAngle:"Workshop participation ≠ regulatory approval; approval cycles run 18–24 months.",relevantLinks:[{label:"WMO Vietnam Climate Report",age:"2w ago",live:false}],publisher:"Lan P.",publishedAt:"1 week ago",freshness:"month",priority:"monitoring",status:"published"},
  {id:"s18",title:"MB Bank Core Banking Replacement — USD 120M RFP Issued",category:"SECTOR",impactScore:61,credibilityScore:81,suggestedAction:"Monitor",synthesis:"MB Bank issued an RFP for full core banking system replacement targeting 2027 go-live. Temenos, Mambu and FIS are confirmed bidders.",keyRisks:["Implementation risk — limited VN track record","Vendor lock-in","Data migration across 8M+ accounts"],devAngle:"Stated 18-month timeline is highly aggressive by global standards.",relevantLinks:[{label:"MB Bank IR Disclosure",age:"1w ago",live:false}],publisher:"Minh T.",publishedAt:"1 week ago",freshness:"month",priority:"monitoring",status:"published"},
  {id:"s19",title:"Global Rice Futures Hit 5-Year High — Vietnam Competitiveness Pressured",category:"COMMODITY",impactScore:60,credibilityScore:88,suggestedAction:"Monitor",synthesis:"Chicago rice futures crossed USD 22/cwt for the first time since 2021. Vietnam's export pricing power partially offset by domestic flood damage.",keyRisks:["Domestic price controls cap margins","Currency appreciation dampens revenue","Competition from Cambodia and Myanmar"],devAngle:"Futures pricing may not fully transmit to physical FOB Vietnam prices.",relevantLinks:[{label:"FAO Food Price Index",age:"2d ago",live:false},{label:"CME Rice Futures",age:"live",live:true}],publisher:"Harvey N.",publishedAt:"1 week ago",freshness:"month",priority:"monitoring",status:"published"},
  {id:"s20",title:"EVFTA Utilization Reaches 42% — Non-Tariff Barriers Remain Bottleneck",category:"GEOPOLITICAL",impactScore:57,credibilityScore:85,suggestedAction:"Monitor",synthesis:"Three years post-ratification, EVFTA preferential tariff utilization at 42% — below the 65% ASEAN average for mature FTAs.",keyRisks:["EU CBAM expansion impacts exporters","SPS measures used as non-tariff barriers","SME origin capacity limited"],devAngle:"Utilization improvement may plateau without structural reform of origin infrastructure.",relevantLinks:[{label:"VCCI EVFTA Tracker",age:"1w ago",live:false}],publisher:"Lan P.",publishedAt:"1 week ago",freshness:"month",priority:"monitoring",status:"published"},
];
const SAMPLE_REPORTS=[
  {id:"r1",type:"Trend Outlook",cardTitle:"SBV CBDC Pilot Expansion",status:"COMPLETE",result:{executive_summary:"Vietnam's CBDC expansion is a structural shift in financial infrastructure with significant implications for incumbent banks and fintech players. The accelerated timeline creates both compliance obligations and commercial opportunities.",outlook:"The SBV's pivot toward multi-bank CBDC deployment signals Vietnam is front-running regional peers. Over 18–24 months this will reshape interbank settlement, retail payments and the competitive positioning of digital wallet providers.",investment_implications:["Overweight fintech infrastructure and core banking modernization vendors","Watch for SBV-adjacent fintech licensing opportunities","Monitor traditional remittance corridor exposure"],risks:["Regulatory sequencing delays","Incumbent bank resistance to disintermediation","Cybersecurity vulnerabilities"],recommended_posture:"Overweight",confidence:"High",next_steps:["Map CBDC-adjacent vendor ecosystem in Vietnam","Initiate dialogue with MB Bank and BIDV digital transformation teams","Review Nami Foundation CBDC positioning vs SBV requirements"]}},
  {id:"r2",type:"Industry Analysis",cardTitle:"SEA Crypto Exchange Licensing Wave",status:"PENDING",result:null},
  {id:"r3",type:"Specific Subject Analysis",cardTitle:"Vietnam Private Credit Market Entry",status:"PENDING",result:null},
];
const SAMPLE_HISTORY=[
  {id:"h1",label:"Vietnam CBDC regulations SBV 2026",mode:"keywords",by:"Harvey N.",at:"Today 08:00",cards:5,action:"published"},
  {id:"h2",label:"SEA fintech M&A landscape Q1 2026",mode:"keywords",by:"Minh T.",at:"Yesterday 14:20",cards:4,action:"published"},
  {id:"h3",label:"sources_fintech_march2026.csv",mode:"upload",by:"Lan P.",at:"Yesterday 09:05",cards:3,action:"waitlist"},
  {id:"h4",label:"https://vnexpress.net/kinh-doanh, techcrunch.com/sea",mode:"scrape",by:"Harvey N.",at:"2 days ago",cards:6,action:"escalated"},
  {id:"h5",label:"Vietnam shipbuilding rankings 2025",mode:"keywords",by:"Minh T.",at:"3 days ago",cards:2,action:"investigate"},
  {id:"h6",label:"regulatory_watch_feb2026.xlsx",mode:"upload",by:"Lan P.",at:"4 days ago",cards:4,action:"published"},
];

// ── UTILS ─────────────────────────────────────────────────────────────────────
// AI calls now route through the AEGIS API Bridge (see ./aegisApi).
// Provider keys are server-side only.
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,5);
const nowTime=()=>new Date().toLocaleTimeString("en",{hour12:false,hour:"2-digit",minute:"2-digit",second:"2-digit"});

// ── LOGO ──────────────────────────────────────────────────────────────────────
function EITLogo({size=32}){
  const cx=size/2,cy=size/2;
  const nodes=[{a:0,d:.85},{a:30,d:.7},{a:60,d:.9},{a:90,d:.75},{a:120,d:.85},{a:150,d:.65},{a:180,d:.8},{a:210,d:.7},{a:240,d:.88},{a:270,d:.75},{a:300,d:.82},{a:330,d:.68},{a:15,d:.55},{a:75,d:.5},{a:135,d:.58},{a:195,d:.52},{a:255,d:.56},{a:315,d:.54}];
  return(
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{flexShrink:0}}>
      <defs><filter id="gf2"><feGaussianBlur stdDeviation="1.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      {nodes.map((n,i)=>{const rad=n.a*Math.PI/180;const x=cx+Math.cos(rad)*cx*n.d*.92;const y=cy+Math.sin(rad)*cy*n.d*.92;return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#3de8a0" strokeWidth={.6} strokeOpacity={.45}/>;} )}
      {nodes.map((n,i)=>{const rad=n.a*Math.PI/180;const x=cx+Math.cos(rad)*cx*n.d*.92;const y=cy+Math.sin(rad)*cy*n.d*.92;const r=n.d>.75?size*.038:size*.028;return <circle key={i} cx={x} cy={y} r={r} fill="#3de8a0" opacity={n.d>.75?.9:.6} filter="url(#gf2)"/>;} )}
      <circle cx={cx} cy={cy} r={size*.07} fill="#3de8a0" opacity={.3} filter="url(#gf2)"/>
      <circle cx={cx} cy={cy} r={size*.04} fill="#e8fff8" opacity={.95}/>
    </svg>
  );
}

// ── BASE COMPONENTS ───────────────────────────────────────────────────────────
const Btn=({onClick,variant="primary",sm,disabled,children,style={}})=>{
  const vs={primary:{bg:C.teal,c:C.bg,b:C.tealD},ghost:{bg:"transparent",c:C.offwhite,b:C.border2},danger:{bg:C.redBg,c:C.red,b:C.redBorder},success:{bg:C.greenBg,c:C.green,b:C.greenBorder},navy:{bg:C.bg3,c:C.offwhite,b:C.border2},tealOut:{bg:"transparent",c:C.teal,b:C.tealDim},gold:{bg:C.bg3,c:C.gold,b:C.goldD+"80"},blue:{bg:C.blueBg,c:C.blue,b:C.blueBorder},stop:{bg:"#2a0808",c:C.red,b:C.redBorder}};
  const v=vs[variant]||vs.primary;
  return <button onClick={onClick} disabled={disabled} style={{background:v.bg,color:v.c,border:`1px solid ${v.b}`,padding:sm?"3px 10px":"7px 18px",cursor:disabled?"not-allowed":"pointer",fontFamily:"inherit",fontSize:sm?10:11,fontWeight:700,borderRadius:4,opacity:disabled?0.5:1,letterSpacing:.5,...style}}>{children}</button>;
};
const Tag=({color=C.dim,label})=><span style={{background:color+"20",border:`1px solid ${color}40`,color,fontSize:9,padding:"2px 8px",borderRadius:3,marginRight:4,fontWeight:700,letterSpacing:.8,display:"inline-block"}}>{label}</span>;
const Chip=({on,onClick,children,small})=><button onClick={onClick} style={{background:on?C.teal:C.bg3,color:on?C.bg:C.muted,border:`1px solid ${on?C.teal:C.border2}`,padding:small?"3px 9px":"5px 12px",cursor:"pointer",fontSize:small?10:11,fontFamily:"inherit",fontWeight:700,borderRadius:4}}>{children}</button>;
const ScoreBadge=({label,val})=>{const c=val>=75?C.green:val>=50?C.gold:val>=25?C.orange:C.red;return <span style={{marginRight:8}}><span style={{color:C.dim,fontSize:9}}>{label} </span><span style={{color:c,fontWeight:800,fontSize:13}}>{val}</span></span>;};
const Sec=({title,children,style={}})=><div style={{background:C.bg3,border:`1px solid ${C.border}`,borderRadius:6,padding:12,marginBottom:10,...style}}>{title&&<div style={{color:C.teal,fontSize:9,fontWeight:800,letterSpacing:2,marginBottom:10,paddingBottom:8,borderBottom:`1px solid ${C.border}`}}>{title}</div>}{children}</div>;

// ── DROPDOWN ──────────────────────────────────────────────────────────────────
function Dropdown({label,value,options,onChange,colorMap={},width=160}){
  const [open,setOpen]=useState(false);
  const ref=useRef(null);
  useEffect(()=>{const h=e=>{if(ref.current&&!ref.current.contains(e.target))setOpen(false);};document.addEventListener("mousedown",h);return()=>document.removeEventListener("mousedown",h);},[]);
  const selected=options.find(o=>(o.value||o)===value);
  const selLabel=selected?(selected.label||selected):value;
  const selColor=colorMap[value]||C.teal;
  const isFiltered=value!==options[0]?.value&&value!==options[0];
  return(
    <div ref={ref} style={{position:"relative",display:"inline-block"}}>
      <div style={{color:C.dim,fontSize:9,fontWeight:700,letterSpacing:1,marginBottom:4}}>{label}</div>
      <button onClick={()=>setOpen(o=>!o)} style={{background:isFiltered?selColor+"18":C.bg3,color:isFiltered?selColor:C.muted,border:`1px solid ${isFiltered?selColor:C.border2}`,padding:"5px 10px",cursor:"pointer",fontSize:10,fontFamily:"inherit",fontWeight:700,borderRadius:4,display:"flex",alignItems:"center",gap:6,width,minWidth:width,boxSizing:"border-box"}}>
        <span style={{flex:1,textAlign:"left",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{selLabel}</span>
        <span style={{fontSize:8,flexShrink:0}}>{open?"▲":"▼"}</span>
      </button>
      {open&&(
        <div style={{position:"absolute",top:"calc(100% + 2px)",left:0,background:C.bg2,border:`1px solid ${C.border2}`,borderRadius:4,zIndex:200,width:Math.max(width,180),boxShadow:C.shadow}}>
          {options.map(o=>{const v=o.value||o;const l=o.label||o;const col=colorMap[v];const isSelected=v===value;return(<div key={v} onClick={()=>{onChange(v);setOpen(false);}} style={{padding:"7px 12px",cursor:"pointer",color:isSelected?(col||C.teal):C.offwhite,background:isSelected?((col||C.teal)+"18"):"transparent",fontSize:11,fontWeight:isSelected?700:400,display:"flex",alignItems:"center",gap:8}}>{col&&<span style={{width:6,height:6,borderRadius:"50%",background:col,display:"inline-block",flexShrink:0}}/>}{l}</div>);})}
        </div>
      )}
    </div>
  );
}

// ── PIPELINE MONITOR ──────────────────────────────────────────────────────────
function PipelineMonitor({runs,activeRunId,logs,done,stopped,cards,decisionMode,onDecision,onBulk}){
  const logRef=useRef(null);
  useEffect(()=>{if(logRef.current)logRef.current.scrollTop=logRef.current.scrollHeight;},[logs]);
  const activeRun=runs.find(r=>r.id===activeRunId);
  const stageIdx=activeRun?PIPELINE_STAGES.findIndex(s=>s.id===activeRun.stage):-1;
  const isRunning=!!activeRunId&&!done&&!stopped;
  const actionColors={publish:C.green,escalate:C.red,investigate:C.blue,waitlist:C.gold,draft:C.muted};
  const actionIcons={publish:"✓",escalate:"⚡",investigate:"🔍",waitlist:"⏸",draft:"✎"};

  return(
    <div style={{background:C.bg,border:`1px solid ${C.border2}`,borderRadius:8,marginTop:14,overflow:"hidden"}}>
      <div style={{background:C.bg2,padding:"8px 14px",display:"flex",alignItems:"center",justifyContent:"space-between",borderBottom:`1px solid ${C.border}`}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}><EITLogo size={16}/><span style={{color:C.teal,fontWeight:800,fontSize:11,letterSpacing:1.5}}>PIPELINE MONITOR</span></div>
        <span style={{color:C.dim,fontSize:10}}>{runs.length} job{runs.length!==1?"s":""}</span>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"240px 1fr",minHeight:220}}>
        {/* Job list */}
        <div style={{borderRight:`1px solid ${C.border}`,overflowY:"auto",maxHeight:360}}>
          <div style={{padding:"5px 10px",color:C.dim,fontSize:9,fontWeight:700,letterSpacing:1,borderBottom:`1px solid ${C.border}`,background:C.bg2}}>JOBS</div>
          {runs.length===0&&<div style={{color:C.dim,fontSize:10,padding:"14px 12px",textAlign:"center"}}>No jobs yet</div>}
          {runs.map(run=>{
            const isAct=run.id===activeRunId&&isRunning;
            const isStopped=run.status==="stopped";
            const isDone=run.status==="done";
            const stCol=isStopped?C.red:isDone?C.green:isAct?C.teal:C.dim;
            const mIcon=run.mode==="keywords"?"⌨":run.mode==="scrape"?"🌐":"📋";
            return(
              <div key={run.id} style={{padding:"9px 11px",borderBottom:`1px solid ${C.border}`,background:isAct?C.bg3:"transparent"}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
                  <span style={{color:stCol,fontSize:9,fontWeight:700}}>{isStopped?"⏹ STOPPED":isDone?"✓ DONE":isAct?"● RUNNING":"○ DONE"}</span>
                  <span style={{color:C.dim,fontSize:9}}>{run.startedAt}</span>
                </div>
                <div style={{color:C.offwhite,fontSize:10,fontWeight:600,lineHeight:1.3,marginBottom:5}}>{mIcon} {run.label?.slice(0,24)}{run.label?.length>24?"...":""}</div>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:2}}>
                  {[["MODE",run.mode?.toUpperCase()],["AGENTS",run.agents],["TIME",isStopped?"stopped":isDone?"done":run.estTime],["TOKENS",run.estTokens]].map(([k,v])=>(
                    <div key={k}><div style={{color:C.dim,fontSize:8}}>{k}</div><div style={{color:C.muted,fontSize:9,fontWeight:700}}>{v}</div></div>
                  ))}
                </div>
                {isAct&&activeRun?.stage&&<div style={{marginTop:5,color:C.teal,fontSize:9,fontWeight:700}}>▶ {PIPELINE_STAGES.find(s=>s.id===activeRun.stage)?.label}</div>}
                {(isDone||isStopped)&&<div style={{marginTop:4,color:isStopped?C.red:C.green,fontSize:9}}>{isStopped?"Pipeline stopped":` ✓ ${run.cardsOut||0} cards`}</div>}
              </div>
            );
          })}
        </div>
        {/* Stages + log */}
        <div style={{display:"flex",flexDirection:"column"}}>
          <div style={{padding:"8px 12px",borderBottom:`1px solid ${C.border}`,overflowX:"auto"}}>
            <div style={{display:"flex",alignItems:"center",gap:0,minWidth:"max-content"}}>
              {PIPELINE_STAGES.map((st,i)=>{
                const isA=activeRun?.stage===st.id&&isRunning;
                const isDn=(done||stopped)||(stageIdx>i&&stageIdx>=0);
                const col=stopped&&!isDn?C.dim:isDn?C.green:isA?C.teal:C.dim;
                const bg=isDn?C.greenBg:isA?C.tealGlow:C.bg3;
                const bdr=isDn?C.greenBorder:isA?C.tealDim:C.border;
                return(
                  <div key={st.id} style={{display:"flex",alignItems:"center"}}>
                    <div style={{textAlign:"center",width:56,padding:"4px 2px",background:bg,border:`1px solid ${bdr}`,borderRadius:4,boxShadow:isA?C.glow:"none"}}>
                      <div style={{fontSize:11,marginBottom:1}}>{isDn?"✓":stopped&&isA?"⏹":isA?"◉":st.icon}</div>
                      <div style={{color:col,fontSize:7.5,fontWeight:800}}>{st.label}</div>
                    </div>
                    {i<PIPELINE_STAGES.length-1&&<div style={{width:6,height:1,background:isDn?C.greenBorder:C.border}}/>}
                  </div>
                );
              })}
            </div>
          </div>
          <div ref={logRef} style={{flex:1,background:"#030a07",padding:"7px 10px",fontFamily:"'Courier New',monospace",fontSize:10,overflowY:"auto",maxHeight:140}}>
            {logs.length===0&&<div style={{color:C.dim}}>Awaiting pipeline run...</div>}
            {logs.map((l,i)=><div key={i} style={{color:l.t==="success"?C.green:l.t==="teal"?C.teal:l.t==="stop"?C.red:C.muted,marginBottom:1.5}}><span style={{color:C.dim}}>[{l.time}] </span>{l.msg}</div>)}
            {isRunning&&<div style={{color:C.teal}}>▌</div>}
          </div>
        </div>
      </div>

      {/* Decision gate */}
      {(done||stopped)&&cards.length>0&&(
        <div style={{borderTop:`1px solid ${C.border2}`,padding:14,background:C.bg2}}>
          {decisionMode==="auto"?(
            <div style={{display:"flex",alignItems:"center",gap:10,padding:"10px 14px",background:C.greenBg,border:`1px solid ${C.greenBorder}`,borderRadius:6}}>
              <span style={{fontSize:16}}>✓</span>
              <div>
                <div style={{color:C.green,fontWeight:800,fontSize:11}}>{stopped?"Partial pipeline results —":"Auto-published:"} {cards.length} cards sent to Newsfeed</div>
                <div style={{color:C.muted,fontSize:10,marginTop:2}}>Cards were automatically published based on your selected decision gate mode.</div>
              </div>
            </div>
          ):(
            <div>
              <div style={{color:C.teal,fontWeight:800,fontSize:11,letterSpacing:1,marginBottom:4}}>👁 MANUAL REVIEW — {cards.length} Cards{stopped?" (partial pipeline)":""}</div>
              <div style={{color:C.muted,fontSize:10,marginBottom:12}}>Route each card individually before publishing.</div>
              <div style={{display:"flex",flexDirection:"column",gap:7}}>
                {cards.map((c,i)=>(
                  <div key={c.id||i} style={{background:C.bg3,border:`1px solid ${C.border2}`,borderRadius:5,padding:"9px 12px",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{color:C.offwhite,fontSize:11,fontWeight:700,lineHeight:1.3,marginBottom:2}}>{c.title?.slice(0,55)}{c.title?.length>55?"...":""}</div>
                      <div style={{display:"flex",gap:4}}><ScoreBadge label="IMP" val={c.impactScore||70}/><ScoreBadge label="CR" val={c.credibilityScore||70}/><Tag color={C.tealDim} label={c.category||"—"}/></div>
                    </div>
                    <div style={{display:"flex",gap:5,flexShrink:0,flexWrap:"wrap"}}>
                      <Btn variant="success" sm onClick={()=>onDecision(c.id||i,"publish")}>✓ PUBLISH</Btn>
                      <Btn variant="danger" sm onClick={()=>onDecision(c.id||i,"escalate")}>⚡ ESCALATE</Btn>
                      <Btn variant="blue" sm onClick={()=>onDecision(c.id||i,"investigate")}>🔍 INVESTIGATE</Btn>
                      <Btn variant="gold" sm onClick={()=>onDecision(c.id||i,"waitlist")}>⏸ WAITLIST</Btn>
                      <Btn variant="ghost" sm onClick={()=>onDecision(c.id||i,"draft")}>✎ DRAFT</Btn>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{display:"flex",gap:8,marginTop:12}}>
                <Btn variant="primary" onClick={()=>onBulk("publish")}>✓ PUBLISH ALL</Btn>
                <Btn variant="danger" onClick={()=>onBulk("escalate")}>⚡ ESCALATE ALL</Btn>
                <Btn variant="ghost" onClick={()=>onBulk("waitlist")}>⏸ WAITLIST ALL</Btn>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── ORG PROFILE ───────────────────────────────────────────────────────────────
function OrgProfileTab({profile,setProfile,onSave}){
  const [local,setLocal]=useState(profile);
  const [orgStatus,setOrgStatus]=useState(null);
  const [step,setStep]=useState(0);
  const toRef=useRef(null);
  const toggle=(k,v)=>setLocal(p=>{const a=p[k]||[];return{...p,[k]:a.includes(v)?a.filter(x=>x!==v):[...a,v]};});
  const handleOrgName=v=>{
    setLocal(p=>({...p,name:v}));clearTimeout(toRef.current);
    if(v.trim().length<3){setOrgStatus(null);return;}
    setOrgStatus("searching");
    toRef.current=setTimeout(async()=>{try{const r=await aegisApi.verifyOrg({ name:v });setOrgStatus(r);}catch{setOrgStatus(null);}},900);
  };

  const steps=[
    {id:"role",label:"Role",icon:"👤"},
    {id:"org",label:"Organization",icon:"🏢"},
    {id:"profile",label:"Investment Profile",icon:"📊"},
    {id:"strategy",label:"Strategy",icon:"🎯"},
  ];

  const complete={
    role:!!local.role,
    org:!!local.name,
    profile:(local.sectors||[]).length>0&&(local.geos||[]).length>0,
    strategy:!!(local.priorities||local.risk),
  };

  const CG=({field,opts})=><div style={{display:"flex",flexWrap:"wrap",gap:5}}>{opts.map(o=><Chip key={o} small on={(local[field]||[]).includes(o)} onClick={()=>toggle(field,o)}>{o}</Chip>)}</div>;

  const RC=({role,level})=>{const on=local.role===role.id;return(
    <div onClick={()=>setLocal(p=>({...p,role:role.id,roleLevel:level}))} style={{background:on?C.teal:C.bg3,border:`1.5px solid ${on?C.teal:C.border2}`,borderRadius:6,padding:"10px 14px",cursor:"pointer",textAlign:"center",flex:1,minWidth:90}}>
      <div style={{fontSize:18,marginBottom:3}}>{role.icon}</div>
      <div style={{color:on?C.bg:C.offwhite,fontWeight:800,fontSize:11}}>{role.label}</div>
      <div style={{color:on?C.bg:C.dim,fontSize:9,marginTop:1}}>Lv.{level}</div>
    </div>
  );};

  const inp2={background:C.bg,border:`1px solid ${C.border2}`,color:C.white,padding:"8px 12px",width:"100%",fontFamily:"inherit",fontSize:12,borderRadius:4,boxSizing:"border-box",outline:"none"};

  return(
    <div style={{padding:20,maxWidth:720,margin:"0 auto"}}>
      {/* Step progress */}
      <div style={{display:"flex",alignItems:"center",marginBottom:24,background:C.bg2,border:`1px solid ${C.border}`,borderRadius:8,padding:"10px 16px"}}>
        {steps.map((s,i)=>{const done=complete[s.id];const active=i===step;return(
          <div key={s.id} style={{display:"flex",alignItems:"center",flex:1}}>
            <div onClick={()=>setStep(i)} style={{display:"flex",alignItems:"center",gap:6,cursor:"pointer",padding:"4px 8px",borderRadius:4,background:active?C.tealGlow:"transparent",border:`1px solid ${active?C.tealDim:"transparent"}`,flex:1}}>
              <div style={{width:22,height:22,borderRadius:"50%",background:done?C.teal:active?C.tealDark:C.bg3,border:`1.5px solid ${done||active?C.teal:C.border2}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,color:done?C.bg:active?C.teal:C.dim,fontWeight:800,flexShrink:0}}>{done?"✓":i+1}</div>
              <div><div style={{color:active?C.teal:done?C.tealD:C.dim,fontSize:9,fontWeight:700,letterSpacing:.5}}>{s.label}</div></div>
            </div>
            {i<steps.length-1&&<div style={{width:16,height:1,background:C.border,flexShrink:0}}/>}
          </div>
        );})}
      </div>

      {/* Step content */}
      <div style={{background:C.bg2,border:`1px solid ${C.border}`,borderRadius:8,padding:20,minHeight:280}}>
        {step===0&&(
          <div>
            <div style={{color:C.teal,fontWeight:800,fontSize:13,marginBottom:4}}>What's your role?</div>
            <div style={{color:C.muted,fontSize:11,marginBottom:16}}>This determines which features you can access in the platform.</div>
            <div style={{marginBottom:14}}>
              <div style={{color:C.dim,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:8}}>LEVEL 1 — ANALYSTS & MANAGERS <span style={{fontWeight:400}}>(full platform access)</span></div>
              <div style={{display:"flex",gap:8,marginBottom:14}}>{ROLES.lv1.map(r=><RC key={r.id} role={r} level={1}/>)}</div>
              <div style={{color:C.dim,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:8}}>LEVEL 2 — EXECUTIVES <span style={{fontWeight:400}}>(newsfeed + reports only)</span></div>
              <div style={{display:"flex",gap:8}}>{ROLES.lv2.map(r=><RC key={r.id} role={r} level={2}/>)}</div>
            </div>
          </div>
        )}
        {step===1&&(
          <div>
            <div style={{color:C.teal,fontWeight:800,fontSize:13,marginBottom:4}}>Organization details</div>
            <div style={{color:C.muted,fontSize:11,marginBottom:16}}>Your org name will be auto-verified and used to calibrate intelligence scoring.</div>
            <div style={{marginBottom:14}}>
              <div style={{color:C.muted,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:6}}>ORG NAME</div>
              <input value={local.name||""} onChange={e=>handleOrgName(e.target.value)} placeholder="e.g. Nami Foundation" style={inp2}/>
              {orgStatus==="searching"&&<div style={{color:C.teal,fontSize:10,marginTop:4}}>◈ Verifying...</div>}
              {orgStatus&&orgStatus!=="searching"&&(
                <div style={{marginTop:8,padding:"8px 12px",background:orgStatus.found?C.greenBg:C.redBg,border:`1px solid ${orgStatus.found?C.greenBorder:C.redBorder}`,borderRadius:4}}>
                  <div style={{color:orgStatus.found?C.green:C.red,fontSize:11,fontWeight:700}}>{orgStatus.found?"✓ VERIFIED":"⚠ NOT FOUND"} · {orgStatus.name}</div>
                  {orgStatus.found&&<div style={{color:C.muted,fontSize:10,marginTop:2}}>{orgStatus.type} · {orgStatus.country}{orgStatus.regulator?` · ${orgStatus.regulator}`:""}</div>}
                  <div style={{color:C.dim,fontSize:10,marginTop:2}}>{orgStatus.note}</div>
                </div>
              )}
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
              <div>
                <div style={{color:C.muted,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:6}}>RISK APPETITE</div>
                <select value={local.risk||""} onChange={e=>setLocal(p=>({...p,risk:e.target.value}))} style={{...inp2,padding:"8px 12px"}}>
                  <option value="">— SELECT —</option>{RISK_LEVELS.map(r=><option key={r}>{r}</option>)}
                </select>
              </div>
              <div style={{display:"flex",flexDirection:"column",justifyContent:"flex-end"}}>
                <div style={{color:C.dim,fontSize:10,lineHeight:1.5}}>Risk appetite calibrates how intelligence cards are weighted — aggressive profiles surface higher-volatility signals.</div>
              </div>
            </div>
          </div>
        )}
        {step===2&&(
          <div>
            <div style={{color:C.teal,fontWeight:800,fontSize:13,marginBottom:4}}>Investment profile</div>
            <div style={{color:C.muted,fontSize:11,marginBottom:16}}>Select your focus areas. These weight the relevance scoring of all intelligence cards.</div>
            <div style={{marginBottom:14}}>
              <div style={{color:C.muted,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:6}}>SECTOR FOCUS</div>
              <CG field="sectors" opts={SECTORS}/>
            </div>
            <div style={{marginBottom:14}}>
              <div style={{color:C.muted,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:6,marginTop:10}}>GEOGRAPHIC EXPOSURE</div>
              <CG field="geos" opts={GEOS}/>
            </div>
            <div>
              <div style={{color:C.muted,fontSize:10,fontWeight:700,letterSpacing:1,marginBottom:6,marginTop:10}}>ASSET CLASSES</div>
              <CG field="assets" opts={ASSETS}/>
            </div>
          </div>
        )}
        {step===3&&(
          <div>
            <div style={{color:C.teal,fontWeight:800,fontSize:13,marginBottom:4}}>Strategic priorities</div>
            <div style={{color:C.muted,fontSize:11,marginBottom:14}}>Describe your key investment themes and priorities in free text. This provides context for AI synthesis.</div>
            <textarea value={local.priorities||""} onChange={e=>setLocal(p=>({...p,priorities:e.target.value}))} placeholder="e.g. Pre-IPO fintech SEA, CBDC infrastructure plays, regulatory arbitrage opportunities in Vietnam crypto..." style={{...inp2,resize:"vertical",minHeight:120}}/>
            <div style={{marginTop:16,padding:12,background:C.bg3,border:`1px solid ${C.border}`,borderRadius:6}}>
              <div style={{color:C.teal,fontSize:10,fontWeight:700,marginBottom:8}}>PROFILE SUMMARY</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,fontSize:10}}>
                {[["Role",([...ROLES.lv1,...ROLES.lv2].find(r=>r.id===local.role)||{}).label||"—"],["Org",local.name||"—"],["Risk",local.risk||"—"],["Sectors",(local.sectors||[]).length+" selected"],["Geos",(local.geos||[]).length+" selected"],["Assets",(local.assets||[]).length+" selected"]].map(([k,v])=>(<div key={k}><span style={{color:C.dim}}>{k}: </span><span style={{color:C.offwhite,fontWeight:600}}>{v}</span></div>))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div style={{display:"flex",justifyContent:"space-between",marginTop:14}}>
        <Btn variant="ghost" onClick={()=>setStep(s=>Math.max(0,s-1))} disabled={step===0}>← BACK</Btn>
        <div style={{display:"flex",gap:8}}>
          {step<steps.length-1?(
            <Btn onClick={()=>setStep(s=>s+1)}>NEXT →</Btn>
          ):(
            <Btn onClick={()=>{setProfile(local);onSave&&onSave();}}>SAVE & LAUNCH EIT →</Btn>
          )}
        </div>
      </div>
    </div>
  );
}

// ── INGESTION ─────────────────────────────────────────────────────────────────
function IngestionTab({profile,onIntelligenceReady}){
  const [mode,setMode]=useState("keywords");
  const [topics,setTopics]=useState("");
  const [scrapeUrls,setScrapeUrls]=useState("");
  const [uploadedRows,setUploadedRows]=useState([]);
  const [loading,setLoading]=useState(false);
  const [logs,setLogs]=useState([]);
  const [done,setDone]=useState(false);
  const [stopped,setStopped]=useState(false);
  const [cards,setCards]=useState([]);
  const [cardDecisions,setCardDecisions]=useState({});
  const [runs,setRuns]=useState([]);
  const [activeRunId,setActiveRunId]=useState(null);
  const [history,setHistory]=useState(SAMPLE_HISTORY);
  const [decisionMode,setDecisionMode]=useState("manual"); // "auto" | "manual"
  const stopRef=useRef(false);
  const fileRef=useRef(null);

  const addLog=(msg,t="info")=>setLogs(p=>[...p,{msg,t,time:nowTime()}]);
  const handleFile=e=>{const file=e.target.files[0];if(!file)return;const reader=new FileReader();reader.onload=ev=>{const rows=ev.target.result.split("\n").filter(Boolean).slice(1,21).map((r,i)=>{const c=r.split(/,|;|\t/);return{id:i,topic:c[0]?.trim(),source:c[1]?.trim()||""};});setUploadedRows(rows);addLog(`✓ Loaded ${rows.length} rows from ${file.name}`,"success");};reader.readAsText(file);};

  const stopPipeline=()=>{
    stopRef.current=true;
    setStopped(true);setLoading(false);
    addLog("⏹ Pipeline stopped by user","stop");
    setRuns(p=>p.map(r=>r.id===activeRunId?{...r,status:"stopped"}:r));
  };

  const run=async()=>{
    const hasInput=(mode==="keywords"&&topics.trim())||(mode==="scrape"&&scrapeUrls.trim())||(mode==="upload"&&uploadedRows.length>0);
    if(!hasInput||loading)return;
    stopRef.current=false;
    const runId=uid();
    const inputDesc=mode==="keywords"?topics:mode==="scrape"?scrapeUrls:uploadedRows.map(r=>r.topic).join(", ");
    const estTokens=mode==="keywords"?"~2,400":mode==="scrape"?"~4,800":"~3,200";
    const newRun={id:runId,label:inputDesc,mode,agents:mode==="scrape"?6:4,estTime:"~20s",estTokens,startedAt:nowTime(),status:"running",stage:"ingest",cardsOut:0};
    setRuns(p=>[newRun,...p]);setActiveRunId(runId);
    setLoading(true);setDone(false);setStopped(false);setCards([]);setCardDecisions({});setLogs([]);
    const setStage=s=>{if(!stopRef.current)setRuns(p=>p.map(r=>r.id===runId?{...r,stage:s}:r));};

    addLog(`Mode:${mode.toUpperCase()} | Agents:${newRun.agents} | Tokens:${estTokens}`);

    // Backend (Operations Agent) owns ingest→filter→synthesize; we stream its
    // stage events into the Pipeline Monitor.
    let newCards=[];
    try{
      await aegisApi.ingestStream(
        {
          mode,
          input: inputDesc,
          org_profile: { name:profile.name, sectors:profile.sectors, geos:profile.geos, risk_appetite:profile.risk, priorities:profile.priorities },
          decision_mode: decisionMode,
        },
        (e: SseEvent)=>{
          if(stopRef.current) return;
          if(e.type==="stage"){ setStage(e.stage); if(e.log) addLog(e.log, e.log.startsWith("\u2713")?"success":"teal"); }
          else if(e.type==="log"){ addLog(e.log); }
          else if(e.type==="result"){ newCards=e.data?.cards||[]; setCards(newCards); }
          else if(e.type==="done"){ addLog(e.log,"success"); }
        }
      );
    }catch(err){
      addLog("\u26a0 Pipeline error — kiểm tra api_bridge đang chạy.","stop");
      setLoading(false);
      setRuns(p=>p.map(r=>r.id===runId?{...r,status:"error"}:r));
      return;
    }
    if(stopRef.current)return;

    // ── Decision gate (frontend-owned) ────────────────────────────────────────
    setStage("review");
    if(decisionMode==="auto"){
      addLog("\u25b6 Auto-publish mode — sending all cards to Newsfeed...","teal");
      newCards.forEach(c=>onIntelligenceReady({...c,publisher:profile.name||"Editor",publishedAt:"Just now",status:"published",freshness:"24h",priority:"high"}));
      addLog(`\u2713 ${newCards.length} cards published automatically`,"success");
    } else {
      addLog("\u25b6 Manual review mode — awaiting decision gate...","teal");
    }
    setRuns(p=>p.map(r=>r.id===runId?{...r,status:"done",stage:"review",cardsOut:newCards.length}:r));
    setDone(true);setLoading(false);
    const inputLabel=mode==="keywords"?topics:mode==="scrape"?scrapeUrls:uploadedRows.map(r=>r.topic).join(", ");
    setHistory(p=>[{id:uid(),label:inputLabel,mode,by:profile.name||"Editor",at:"Just now",cards:newCards.length,action:decisionMode==="auto"?"published":"pending"},...p]);
  };

  const handleDecision=(id,action)=>{
    setCardDecisions(p=>({...p,[id]:action}));
    const card=cards.find((c,i)=>(c.id||i)===id);
    if(!card)return;
    if(action==="publish"||action==="escalate"){
      onIntelligenceReady({...card,publisher:profile.name||"Editor",publishedAt:"Just now",status:action,freshness:"24h",priority:action==="escalate"?"high":"high",suggestedAction:action==="escalate"?"Escalate":card.suggestedAction});
    }
    addLog(`→ "${card.title?.slice(0,28)}..." → ${action.toUpperCase()}`,"teal");
  };
  const handleBulk=action=>cards.forEach((c,i)=>handleDecision(c.id||i,action));

  const ModeBtn=({m,label})=><button style={{background:mode===m?C.teal:C.bg3,color:mode===m?C.bg:C.muted,border:`1px solid ${mode===m?C.teal:C.border2}`,padding:"6px 14px",cursor:"pointer",fontSize:11,fontFamily:"inherit",fontWeight:700,borderRadius:4,marginRight:6}} onClick={()=>setMode(m)}>{label}</button>;
  const ta={background:C.bg,border:`1px solid ${C.border2}`,color:C.white,padding:"8px 12px",width:"100%",fontFamily:"inherit",fontSize:12,borderRadius:4,boxSizing:"border-box",resize:"vertical",minHeight:80,outline:"none"};
  const actionColors={publish:C.green,escalate:C.red,investigate:C.blue,waitlist:C.gold,draft:C.muted};
  const actionIcons={publish:"✓",escalate:"⚡",investigate:"🔍",waitlist:"⏸",draft:"✎"};

  return(
    <div style={{padding:14,display:"grid",gridTemplateColumns:"1fr 300px",gap:14,alignItems:"start"}}>
      <div>
        <Sec title="SIGNAL INGESTION">
          {/* Decision gate toggle */}
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,padding:"8px 12px",background:C.bg2,border:`1px solid ${C.border}`,borderRadius:6}}>
            <div>
              <div style={{color:C.offwhite,fontSize:11,fontWeight:700}}>Decision Gate Mode</div>
              <div style={{color:C.dim,fontSize:10,marginTop:2}}>{decisionMode==="auto"?"Cards auto-published to Newsfeed after pipeline completes":"Manually review & route each card after pipeline completes"}</div>
            </div>
            <div style={{display:"flex",gap:0,borderRadius:4,overflow:"hidden",border:`1px solid ${C.border2}`,flexShrink:0}}>
              {[["auto","AUTO PUBLISH"],["manual","MANUAL REVIEW"]].map(([m,l])=>(
                <button key={m} onClick={()=>setDecisionMode(m)} style={{background:decisionMode===m?(m==="auto"?C.green:C.teal):C.bg3,color:decisionMode===m?C.bg:C.muted,border:"none",padding:"5px 12px",cursor:"pointer",fontSize:10,fontFamily:"inherit",fontWeight:700,letterSpacing:.3}}>{l}</button>
              ))}
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <ModeBtn m="keywords" label="⌨ KEYWORDS"/>
            <ModeBtn m="scrape" label="🌐 WEB SCRAPING"/>
            <ModeBtn m="upload" label="⬆ CSV / EXCEL"/>
          </div>

          {mode==="keywords"&&<textarea value={topics} onChange={e=>setTopics(e.target.value)} placeholder="e.g. Vietnam CBDC regulations, SEA fintech M&A, SBV monetary policy 2026..." style={ta}/>}
          {mode==="scrape"&&<div><textarea value={scrapeUrls} onChange={e=>setScrapeUrls(e.target.value)} placeholder={"https://vnexpress.net/kinh-doanh\nhttps://techcrunch.com/southeast-asia"} style={ta}/><div style={{color:C.dim,fontSize:10,marginTop:4}}>AI will scrape each URL and extract signals filtered by org profile.</div></div>}
          {mode==="upload"&&<div>
            <div style={{border:`2px dashed ${C.border2}`,borderRadius:6,padding:18,textAlign:"center",marginBottom:8,cursor:"pointer",background:C.bg}} onClick={()=>fileRef.current?.click()}>
              <div style={{fontSize:22,marginBottom:3}}>⬆</div>
              <div style={{color:C.offwhite,fontWeight:700,fontSize:12,marginBottom:3}}>Drop CSV or Excel file here</div>
              <div style={{color:C.dim,fontSize:10}}>Columns: Topic | Source URL | Category (optional)</div>
            </div>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.txt" style={{display:"none"}} onChange={handleFile}/>
            {uploadedRows.length>0&&<div style={{background:C.greenBg,border:`1px solid ${C.greenBorder}`,borderRadius:4,padding:8,maxHeight:72,overflowY:"auto"}}>
              <div style={{color:C.green,fontWeight:700,fontSize:10,marginBottom:3}}>✓ {uploadedRows.length} rows loaded</div>
              {uploadedRows.slice(0,2).map((r,i)=><div key={i} style={{color:C.muted,fontSize:10}}>· {r.topic}</div>)}
              {uploadedRows.length>2&&<div style={{color:C.dim,fontSize:10}}>...+{uploadedRows.length-2} more</div>}
            </div>}
          </div>}

          <div style={{marginTop:12,display:"flex",alignItems:"center",gap:10}}>
            {!loading?(
              <Btn onClick={run}>▶ RUN PIPELINE</Btn>
            ):(
              <Btn variant="stop" onClick={stopPipeline}>⏹ STOP PIPELINE</Btn>
            )}
            {done&&!stopped&&<span style={{color:C.green,fontSize:11,fontWeight:700}}>✓ {cards.length} cards ready</span>}
            {stopped&&<span style={{color:C.red,fontSize:11,fontWeight:700}}>⏹ Stopped · {cards.length} partial cards</span>}
          </div>

          {runs.length>0&&<PipelineMonitor runs={runs} activeRunId={loading?activeRunId:null} logs={logs} done={done} stopped={stopped} cards={cards} decisionMode={decisionMode} onDecision={handleDecision} onBulk={handleBulk}/>}

          {Object.keys(cardDecisions).length>0&&(
            <div style={{display:"flex",gap:5,flexWrap:"wrap",marginTop:10}}>
              {cards.map((c,i)=>{const id=c.id||i;const dec=cardDecisions[id];if(!dec)return null;const col=actionColors[dec];return <div key={id} style={{background:col+"18",border:`1px solid ${col}40`,borderRadius:4,padding:"3px 9px",fontSize:10}}><span style={{color:col,fontWeight:700}}>{actionIcons[dec]} {dec.toUpperCase()}</span><span style={{color:C.muted,marginLeft:5}}>{c.title?.slice(0,22)}...</span></div>;})}
            </div>
          )}
        </Sec>
      </div>

      {/* History sidebar */}
      <div style={{position:"sticky",top:14}}>
        <Sec title="SEARCH HISTORY" style={{marginBottom:0}}>
          <div style={{color:C.dim,fontSize:9,marginBottom:10}}>All ingestion runs · click RE-RUN to restore</div>
          <div style={{maxHeight:560,overflowY:"auto"}}>
            {history.map(h=>{
              const mIcon=h.mode==="keywords"?"⌨":h.mode==="scrape"?"🌐":"📋";
              const aCol={published:C.green,escalated:C.red,investigate:C.blue,waitlist:C.gold,pending:C.teal,draft:C.muted}[h.action]||C.dim;
              const aIcon={published:"✓",escalated:"⚡",investigate:"🔍",waitlist:"⏸",pending:"◉",draft:"✎"}[h.action]||"○";
              return(
                <div key={h.id} style={{borderBottom:`1px solid ${C.border}`,paddingBottom:9,marginBottom:9}}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:3}}>
                    <span style={{color:C.teal,fontSize:9,fontWeight:700}}>{mIcon} {h.mode?.toUpperCase()}</span>
                    <span style={{color:aCol,fontSize:9,fontWeight:700}}>{aIcon} {h.action?.toUpperCase()}</span>
                  </div>
                  <div style={{color:C.offwhite,fontSize:10,fontWeight:600,lineHeight:1.3,marginBottom:3,wordBreak:"break-all"}}>{h.label?.slice(0,48)}{h.label?.length>48?"...":""}</div>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                    <div style={{color:C.dim,fontSize:9}}>{h.by} · {h.at} · {h.cards} cards</div>
                    <button style={{background:"transparent",border:`1px solid ${C.border2}`,color:C.muted,fontSize:9,padding:"2px 7px",cursor:"pointer",borderRadius:3,fontFamily:"inherit"}} onClick={()=>{if(h.mode==="keywords")setTopics(h.label);else if(h.mode==="scrape")setScrapeUrls(h.label);setMode(h.mode);}}>↺</button>
                  </div>
                </div>
              );
            })}
          </div>
        </Sec>
      </div>
    </div>
  );
}

// ── NEWSFEED ──────────────────────────────────────────────────────────────────
function NewsfeedTab({intelligence,onReport}){
  const [active,setActive]=useState(null);
  const [catFilter,setCatFilter]=useState("ALL");
  const [actionFilter,setActionFilter]=useState("ALL");
  const [freshnessFilter,setFreshnessFilter]=useState("ALL");
  const [priorityFilter,setPriorityFilter]=useState("ALL");
  const allCards=intelligence.length>0?intelligence:SAMPLE_INTEL;
  const isSample=intelligence.length===0;
  const cats=["ALL",...new Set(allCards.map(c=>c.category).filter(Boolean))].sort();
  const filtered=allCards.filter(c=>(catFilter==="ALL"||c.category===catFilter)&&(actionFilter==="ALL"||c.suggestedAction===actionFilter)&&(freshnessFilter==="ALL"||c.freshness===freshnessFilter)&&(priorityFilter==="ALL"||c.priority===priorityFilter)).sort((a,b)=>(b.impactScore||0)-(a.impactScore||0));
  const card=active?allCards.find(c=>c.id===active):null;

  const catOptions=cats.map(v=>({value:v,label:v}));
  const actionOptions=[{value:"ALL",label:"All Actions"},...["Escalate","Act","Investigate","Monitor"].map(v=>({value:v,label:v}))];
  const freshnessOptions=[{value:"ALL",label:"All Time"},{value:"24h",label:"Last 24 Hours"},{value:"week",label:"Last Week"},{value:"month",label:"Last Month"}];
  const priorityOptions=[{value:"ALL",label:"All Priorities"},{value:"high",label:"High"},{value:"moderate",label:"Moderate"},{value:"monitoring",label:"Monitoring"}];
  const actionColors={"ALL":C.teal,Escalate:C.red,Act:C.gold,Investigate:C.blue,Monitor:C.green};
  const freshnessColors={"ALL":C.teal,"24h":C.green,"week":C.gold,"month":C.dim};
  const priorityColors={"ALL":C.teal,"high":C.red,"moderate":C.gold,"monitoring":C.green};

  return(
    <div style={{background:C.bg,height:"calc(100vh - 90px)",display:"flex",flexDirection:"column"}}>
      {isSample&&<div style={{background:C.tealGlow,borderBottom:`1px solid ${C.tealDim}40`,padding:"5px 20px",fontSize:10,color:C.teal,fontWeight:700}}>◈ SAMPLE DATA — Run ingestion pipeline to populate with live intelligence</div>}

      {/* Filter bar — all dropdowns */}
      <div style={{background:C.bg2,borderBottom:`1px solid ${C.border}`,padding:"10px 16px"}}>
        <div style={{display:"flex",alignItems:"flex-end",gap:12,flexWrap:"wrap"}}>
          <Dropdown label="CATEGORY" value={catFilter} options={catOptions} onChange={setCatFilter} colorMap={{"ALL":C.teal}} width={170}/>
          <Dropdown label="ACTION" value={actionFilter} options={actionOptions} onChange={setActionFilter} colorMap={actionColors} width={150}/>
          <Dropdown label="FRESHNESS" value={freshnessFilter} options={freshnessOptions} onChange={setFreshnessFilter} colorMap={freshnessColors} width={155}/>
          <Dropdown label="PRIORITY" value={priorityFilter} options={priorityOptions} onChange={setPriorityFilter} colorMap={priorityColors} width={150}/>
          <div style={{marginLeft:"auto",alignSelf:"flex-end",paddingBottom:2}}>
            <span style={{color:C.dim,fontSize:10}}><span style={{color:C.offwhite,fontWeight:700}}>{filtered.length}</span> cards · sorted by impact</span>
            {(catFilter!=="ALL"||actionFilter!=="ALL"||freshnessFilter!=="ALL"||priorityFilter!=="ALL")&&(
              <button onClick={()=>{setCatFilter("ALL");setActionFilter("ALL");setFreshnessFilter("ALL");setPriorityFilter("ALL");}} style={{background:"transparent",border:`1px solid ${C.border2}`,color:C.muted,fontSize:9,padding:"2px 8px",cursor:"pointer",borderRadius:3,fontFamily:"inherit",marginLeft:8}}>✕ CLEAR</button>
            )}
          </div>
        </div>
      </div>

      <div style={{display:"flex",flex:1,overflow:"hidden"}}>
        {/* Card list */}
        <div style={{width:card?"44%":"100%",overflowY:"auto",padding:"10px 12px"}}>
          {filtered.map(c=>(
            <div key={c.id} onClick={()=>setActive(active===c.id?null:c.id)} style={{background:active===c.id?C.bg3:C.bg2,border:`1.5px solid ${active===c.id?C.teal:C.border}`,borderRadius:6,padding:"10px 12px",marginBottom:8,cursor:"pointer",boxShadow:active===c.id?C.glow:"none",transition:"all .12s"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <div><Tag color={ACTION_COLOR[c.suggestedAction]||C.dim} label={c.suggestedAction}/><Tag color={C.tealDim} label={c.category}/><Tag color={c.priority==="high"?C.red:c.priority==="moderate"?C.gold:C.green} label={(c.priority||"monitoring").toUpperCase()}/></div>
                <div><ScoreBadge label="IMP" val={c.impactScore}/><ScoreBadge label="CR" val={c.credibilityScore}/></div>
              </div>
              <div style={{color:C.offwhite,fontSize:12,fontWeight:700,marginBottom:4,lineHeight:1.4}}>{c.title}</div>
              <div style={{color:C.muted,fontSize:10,lineHeight:1.6,marginBottom:5}}>{c.synthesis?.slice(0,120)}...</div>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <div style={{display:"flex",alignItems:"center",gap:6}}>
                  <div style={{background:C.tealDark,color:C.teal,width:18,height:18,borderRadius:"50%",display:"flex",alignItems:"center",justifyContent:"center",fontSize:9,fontWeight:800}}>{(c.publisher||"?").charAt(0)}</div>
                  <span style={{color:C.dim,fontSize:10}}>{c.publisher||"Editor"} · {c.publishedAt||"Recently"}</span>
                </div>
                <span style={{color:c.freshness==="24h"?C.green:c.freshness==="week"?C.gold:C.dim,fontSize:9,fontWeight:700}}>{c.freshness==="24h"?"● FRESH":c.freshness==="week"?"● THIS WEEK":"● OLDER"}</span>
              </div>
            </div>
          ))}
          {filtered.length===0&&<div style={{color:C.dim,textAlign:"center",paddingTop:40,fontSize:12}}>No cards match current filters</div>}
        </div>

        {/* Detail panel */}
        {card&&(
          <div style={{flex:1,overflowY:"auto",padding:"14px 16px",background:C.bg3,borderLeft:`1px solid ${C.border}`}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
              <div style={{color:C.teal,fontSize:14,fontWeight:800,maxWidth:"80%",lineHeight:1.4}}>{card.title}</div>
              <Btn variant="ghost" sm onClick={()=>setActive(null)}>✕</Btn>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:10,flexWrap:"wrap"}}>
              <Tag color={ACTION_COLOR[card.suggestedAction]||C.dim} label={card.suggestedAction}/>
              <Tag color={C.tealDim} label={card.category}/>
              <ScoreBadge label="IMPACT" val={card.impactScore}/>
              <ScoreBadge label="CREDIBILITY" val={card.credibilityScore}/>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12,padding:"8px 12px",background:C.bg2,border:`1px solid ${C.border}`,borderRadius:6}}>
              <div style={{background:C.tealDark,color:C.teal,width:28,height:28,borderRadius:"50%",display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,fontWeight:800,flexShrink:0}}>{(card.publisher||"E").charAt(0)}</div>
              <div><div style={{color:C.offwhite,fontWeight:700,fontSize:11}}>{card.publisher||"Editor"}</div><div style={{color:C.dim,fontSize:10}}>Published · {card.publishedAt||"Recently"}</div></div>
              <div style={{marginLeft:"auto",color:card.freshness==="24h"?C.green:card.freshness==="week"?C.gold:C.dim,fontSize:10,fontWeight:700}}>{card.freshness==="24h"?"● FRESH (24H)":card.freshness==="week"?"● THIS WEEK":"● OLDER"}</div>
            </div>
            <Sec title="INTELLIGENCE SYNTHESIS"><div style={{fontSize:12,lineHeight:1.8,color:C.offwhite}}>{card.synthesis}</div></Sec>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div style={{background:C.redBg,border:`1px solid ${C.redBorder}`,borderRadius:6,padding:12}}><div style={{color:C.red,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:8}}>KEY RISKS</div>{(card.keyRisks||[]).map((r,i)=><div key={i} style={{fontSize:11,color:C.red,marginBottom:4,lineHeight:1.5}}>▸ {r}</div>)}</div>
              <div style={{background:C.blueBg,border:`1px solid ${C.blueBorder}`,borderRadius:6,padding:12}}><div style={{color:C.blue,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:8}}>DEVIL'S ADVOCATE</div><div style={{fontSize:11,color:C.blue,fontStyle:"italic",lineHeight:1.7}}>{card.devAngle}</div></div>
            </div>
            {(card.relevantLinks||[]).length>0&&(
              <Sec title="RELATED SOURCES & FRESHNESS">
                {card.relevantLinks.map((l,i)=>{const isLive=l.live||l.age==="live";const isR=l.age?.includes("h ago")||l.age?.includes("m ago");const fc=isLive?C.green:isR?C.gold:C.dim;return(<div key={i} style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 0",borderBottom:i<card.relevantLinks.length-1?`1px solid ${C.border}`:"none"}}><div style={{display:"flex",alignItems:"center",gap:7}}><span style={{color:C.teal}}>↗</span><span style={{color:C.offwhite,fontSize:11,fontWeight:600}}>{l.label}</span></div><div style={{display:"flex",alignItems:"center",gap:5}}><span style={{width:6,height:6,borderRadius:"50%",background:fc,boxShadow:isLive?`0 0 5px ${C.green}`:"none",display:"inline-block"}}/><span style={{color:fc,fontSize:10,fontWeight:700}}>{isLive?"LIVE":l.age||"—"}</span></div></div>);})}
              </Sec>
            )}
            <div style={{background:C.tealGlow,border:`1px solid ${C.tealDim}60`,borderRadius:6,padding:12}}>
              <div style={{color:C.teal,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:10}}>REQUEST A REPORT</div>
              <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>{TICKET_TYPES.map(t=><Btn key={t} onClick={()=>onReport({type:t,card})}>+ {t.toUpperCase()}</Btn>)}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── REPORTS ───────────────────────────────────────────────────────────────────
function ReportsTab({reports,setReports,profile}){
  const [expanded,setExpanded]=useState("r1");
  const [loading,setLoading]=useState(null);
  const runAnalysis=async id=>{
    const all=[...reports,...SAMPLE_REPORTS];const rep=all.find(r=>r.id===id);if(!rep)return;
    setLoading(id);
    const orgCtx=`Org:${profile.name||"Unknown"}.Sectors:${(profile.sectors||[]).join(",")}.Geos:${(profile.geos||[]).join(",")}.Risk:${profile.risk||"Moderate"}.`;
    const result=await aegisApi.reportGenerate({ report_type: rep.type, signal: rep.card, card_title: rep.cardTitle, org_profile: { name:profile.name, sectors:profile.sectors, geos:profile.geos, risk_appetite:profile.risk } });
    setReports(p=>{const ex=p.find(r=>r.id===id);if(ex)return p.map(r=>r.id===id?{...r,status:"COMPLETE",result}:r);return[{...rep,status:"COMPLETE",result},...p];});
    setLoading(null);
  };
  const stCol={PENDING:C.gold,COMPLETE:C.green,CANCELLED:C.red};
  const stIcon={PENDING:"○",COMPLETE:"✓",CANCELLED:"✕"};
  const displayReports=reports.length>0?reports:SAMPLE_REPORTS;
  return(
    <div style={{padding:20}}>
      {reports.length===0&&<div style={{background:C.tealGlow,border:`1px solid ${C.tealDim}40`,borderRadius:6,padding:"8px 14px",fontSize:11,color:C.teal,fontWeight:700,marginBottom:14}}>◈ SAMPLE REPORTS — request a report from any intelligence card in the Newsfeed</div>}
      <div style={{background:C.bg2,border:`1px solid ${C.border}`,borderRadius:8,padding:14,marginBottom:16,display:"flex"}}>
        {[["TOTAL",displayReports.length,C.offwhite],["PENDING",displayReports.filter(r=>r.status==="PENDING").length,C.gold],["COMPLETE",displayReports.filter(r=>r.status==="COMPLETE").length,C.green]].map(([l,v,c],i,arr)=>(
          <div key={l} style={{flex:1,textAlign:"center",borderRight:i<arr.length-1?`1px solid ${C.border}`:"none",padding:"4px 0"}}>
            <div style={{color:c,fontWeight:800,fontSize:22}}>{v}</div>
            <div style={{color:C.dim,fontSize:9,letterSpacing:1,marginTop:2}}>{l}</div>
          </div>
        ))}
        <div style={{flex:2,padding:"4px 16px",borderLeft:`1px solid ${C.border}`}}>
          <div style={{color:C.dim,fontSize:9,fontWeight:700,letterSpacing:1,marginBottom:5}}>REPORT TYPES</div>
          {TICKET_TYPES.map(t=><div key={t} style={{color:C.muted,fontSize:11,marginBottom:3}}>◈ {t}</div>)}
        </div>
      </div>
      {displayReports.map(rep=>(
        <div key={rep.id} style={{background:C.bg2,border:`1.5px solid ${expanded===rep.id?C.teal:C.border}`,borderRadius:8,marginBottom:10,overflow:"hidden",boxShadow:expanded===rep.id?C.glow:"none"}}>
          <div style={{padding:"12px 16px",display:"flex",justifyContent:"space-between",alignItems:"center",cursor:"pointer",background:expanded===rep.id?C.bg3:C.bg2}} onClick={()=>setExpanded(expanded===rep.id?null:rep.id)}>
            <div style={{display:"flex",alignItems:"center",gap:10,flex:1,minWidth:0}}>
              <span style={{color:stCol[rep.status],fontSize:18,fontWeight:700}}>{stIcon[rep.status]}</span>
              <div style={{minWidth:0}}>
                <div style={{color:C.teal,fontSize:9,fontWeight:800,letterSpacing:1.5}}>{rep.type.toUpperCase()}</div>
                <div style={{color:C.offwhite,fontSize:12,fontWeight:600,marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{rep.cardTitle||rep.card?.title}</div>
              </div>
            </div>
            <div style={{display:"flex",gap:8,alignItems:"center",flexShrink:0,marginLeft:12}}>
              <span style={{color:stCol[rep.status],fontSize:10,fontWeight:700}}>● {rep.status}</span>
              {rep.status==="PENDING"&&<Btn variant="primary" sm onClick={e=>{e.stopPropagation();runAnalysis(rep.id);}} disabled={loading===rep.id}>{loading===rep.id?"◈ ANALYZING...":"▶ GENERATE"}</Btn>}
              <span style={{color:C.dim}}>{expanded===rep.id?"▲":"▼"}</span>
            </div>
          </div>
          {expanded===rep.id&&rep.result&&(
            <div style={{padding:16,borderTop:`1px solid ${C.border}`}}>
              <Sec title="EXECUTIVE SUMMARY"><div style={{fontSize:12,lineHeight:1.8,color:C.offwhite}}>{rep.result.executive_summary}</div></Sec>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
                <Sec title="OUTLOOK"><div style={{fontSize:11,lineHeight:1.7,color:C.muted}}>{rep.result.outlook}</div></Sec>
                <Sec title="INVESTMENT IMPLICATIONS">{(rep.result.investment_implications||[]).map((imp,i)=><div key={i} style={{fontSize:11,color:C.green,marginBottom:5,fontWeight:600}}>▸ {imp}</div>)}</Sec>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
                <div style={{background:C.tealGlow,border:`1px solid ${C.tealDim}60`,borderRadius:6,padding:12,textAlign:"center"}}>
                  <div style={{color:C.teal,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:6}}>POSTURE</div>
                  <div style={{color:POSTURE_COLOR[rep.result.recommended_posture]||C.muted,fontWeight:800,fontSize:22,marginBottom:4}}>{rep.result.recommended_posture}</div>
                  <div style={{color:C.dim,fontSize:9}}>CONF: <span style={{color:C.muted,fontWeight:700}}>{rep.result.confidence}</span></div>
                </div>
                <div style={{background:C.redBg,border:`1px solid ${C.redBorder}`,borderRadius:6,padding:12}}>
                  <div style={{color:C.red,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:8}}>KEY RISKS</div>
                  {(rep.result.risks||[]).map((r,i)=><div key={i} style={{fontSize:11,color:C.red,marginBottom:4}}>▸ {r}</div>)}
                </div>
                <div style={{background:C.greenBg,border:`1px solid ${C.greenBorder}`,borderRadius:6,padding:12}}>
                  <div style={{color:C.green,fontSize:9,fontWeight:800,letterSpacing:1.5,marginBottom:8}}>NEXT STEPS</div>
                  {(rep.result.next_steps||[]).map((st,i)=><div key={i} style={{fontSize:11,color:C.green,marginBottom:4,fontWeight:600}}>→ {st}</div>)}
                </div>
              </div>
            </div>
          )}
          {expanded===rep.id&&rep.status==="PENDING"&&!loading&&<div style={{padding:12,borderTop:`1px solid ${C.border}`,color:C.dim,fontSize:11,textAlign:"center"}}>Click ▶ GENERATE to run AI analysis</div>}
          {expanded===rep.id&&loading===rep.id&&<div style={{padding:12,borderTop:`1px solid ${C.border}`,color:C.teal,fontSize:11,textAlign:"center",fontWeight:700}}>◈ Generating {rep.type}...</div>}
        </div>
      ))}
    </div>
  );
}

// ── APP ───────────────────────────────────────────────────────────────────────
export default function App(){
  const storeProfile = useAegisStore(s => s.userProfile);
  const orgData = storeProfile?.orgData;
  // Skip PROFILE tab if already set from onboarding
  const hasProfile = !!(storeProfile?.name && (storeProfile?.sectors?.length || orgData?.name));
  const [tab,setTab]=useState(hasProfile ? "INGESTION" : "PROFILE");
  const [profile,setProfile]=useState({
    name: orgData?.name ?? storeProfile?.name ?? "",
    sectors: storeProfile?.sectors ?? [],
    geos: storeProfile?.jurisdictions ?? [],
    assets:[],
    risk: storeProfile?.role === "pe_partner" ? "Aggressive" : storeProfile?.role === "counsel" ? "Conservative" : "Moderate",
    priorities: "",
    role: storeProfile?.role ?? "",
    roleLevel: null,
  });
  const [intelligence,setIntelligence]=useState([] as any[]);
  const [reports,setReports]=useState([] as any[]);
  const addIntel=card=>setIntelligence(p=>[card,...p.filter(c=>c.id!==card.id)]);
  const addReport=({type,card})=>{setReports(p=>[{id:uid(),type,card,cardTitle:card.title,status:"PENDING",result:null},...p]);setTab("REPORTS");};
  const isLv2=profile.roleLevel===2;
  const TABS=hasProfile
    ? (isLv2 ? ["NEWSFEED","REPORTS"] : ["INGESTION","NEWSFEED","REPORTS"])
    : (isLv2 ? ["PROFILE","NEWSFEED","REPORTS"] : ["PROFILE","INGESTION","NEWSFEED","REPORTS"]);
  const TAB_LABEL={PROFILE:"◈ ORG PROFILE",INGESTION:"⬡ INGESTION",NEWSFEED:"▦ NEWSFEED",REPORTS:"⊞ REPORTS"};
  const COUNTS={NEWSFEED:intelligence.length||0,REPORTS:reports.length||0};
  const roleInfo=[...ROLES.lv1,...ROLES.lv2].find(r=>r.id===profile.role);
  return(
    <div style={{background:C.bg,color:C.offwhite,fontFamily:"'Inter',system-ui,sans-serif",minHeight:"100vh",fontSize:12}}>
      <div style={{background:C.bg2,borderBottom:`1px solid ${C.border}`,padding:"0 20px",display:"flex",alignItems:"center",justifyContent:"space-between",height:48}}>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <EITLogo size={32}/>
          <div>
            <div style={{display:"flex",alignItems:"baseline",gap:8}}>
              <span style={{color:C.teal,fontWeight:900,fontSize:18,letterSpacing:4,textShadow:`0 0 18px ${C.teal}60`}}>EIT</span>
              <span style={{color:C.tealD,fontSize:11,fontWeight:700,letterSpacing:2}}>EXECUTIVE INTELLIGENCE TERMINAL</span>
            </div>
            <div style={{color:C.dim,fontSize:9,letterSpacing:1.5}}>MODULE 1 · INTELLIGENCE NEWSFEED</div>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          {profile.name&&<span style={{color:C.teal,fontSize:11,fontWeight:700}}>{profile.name.toUpperCase()}</span>}
          {roleInfo&&<span style={{background:C.bg3,color:C.muted,fontSize:10,padding:"2px 8px",borderRadius:3,border:`1px solid ${C.border}`}}>{roleInfo.icon} {roleInfo.label}</span>}
          {profile.risk&&<span style={{color:C.dim,fontSize:10}}>RISK: {profile.risk.toUpperCase()}</span>}
          <span style={{color:C.dim,fontSize:10}}>{new Date().toISOString().slice(0,10)}</span>
        </div>
      </div>
      <div style={{background:C.bg,borderBottom:`1px solid ${C.border}`,padding:"0 18px",display:"flex",alignItems:"center"}}>
        {TABS.map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{background:"transparent",color:tab===t?C.teal:C.dim,border:"none",borderBottom:`2px solid ${tab===t?C.teal:"transparent"}`,padding:"10px 16px",cursor:"pointer",fontSize:11,fontFamily:"inherit",fontWeight:tab===t?800:500,letterSpacing:.5,textShadow:tab===t?`0 0 10px ${C.teal}50`:""}}>
            {TAB_LABEL[t]}{COUNTS[t]?` (${COUNTS[t]})`:""}
          </button>
        ))}
      </div>
      <div style={{overflowY:tab==="NEWSFEED"?"hidden":"auto"}}>
        {tab==="PROFILE"&&<OrgProfileTab profile={profile} setProfile={setProfile} onSave={()=>setTab(isLv2?"NEWSFEED":"INGESTION")}/>}
        {tab==="INGESTION"&&!isLv2&&<IngestionTab profile={profile} onIntelligenceReady={addIntel}/>}
        {tab==="NEWSFEED"&&<NewsfeedTab intelligence={intelligence} onReport={addReport}/>}
        {tab==="REPORTS"&&<ReportsTab reports={reports} setReports={setReports} profile={profile}/>}
      </div>
    </div>
  );
}
