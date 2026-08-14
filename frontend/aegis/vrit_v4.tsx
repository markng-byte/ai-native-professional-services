import { useState, useEffect, useRef } from "react";
import { aegisBus } from "./eventBus";
import { aegisApi, fmt } from "./aegisApi";

// ── DATA ──────────────────────────────────────────────────────────────────────
const RISKS = [
  { id:1, title:"Thuế TNCN cải cách lần 3", src:"Bộ Tài chính", lvl:"CRITICAL", date:"12/03", desc:"Tăng biểu thuế lũy tiến, ảnh hưởng thu nhập >40tr/tháng. Xác suất ban hành Q2: 78%.", st:null },
  { id:2, title:"NĐ quản lý tài sản mã hóa", src:"NHNN + BTC", lvl:"HIGH", date:"10/03", desc:"Custody, AML/KYC cho sàn crypto. Tác động trực tiếp Nami Foundation.", st:"mon" },
  { id:3, title:"Luật Bảo vệ dữ liệu cá nhân", src:"Bộ Công an", lvl:"HIGH", date:"09/03", desc:"Phạt đến 5% doanh thu. Fintech cần audit ngay.", st:null },
  { id:4, title:"Room tín dụng Q2/2026", src:"NHNN", lvl:"MEDIUM", date:"08/03", desc:"Giảm room xuống 12% — ảnh hưởng chi phí vốn SME.", st:null },
  { id:5, title:"Sandbox bảo hiểm số", src:"Cục QLBH", lvl:"MEDIUM", date:"07/03", desc:"Khung thí điểm bảo hiểm tham số — cơ hội BHTT.", st:"elab" },
  { id:6, title:"VAT thương mại điện tử", src:"TCT", lvl:"LOW", date:"05/03", desc:"Hướng dẫn kê khai VAT TMĐT. Ít tác động B2B fintech.", st:null },
];

const FEED = [
  { id:1, ts:"13/03 11:42", title:"Dự thảo NĐ quản lý tài sản mã hóa — Phiên bản 3.1", src:"NHNN", type:"DRAFT", risk:92, tag:"FinTech · Crypto", analysis:"Bổ sung điều khoản bắt buộc đăng ký trong 90 ngày. Yêu cầu vốn pháp định tăng 40% so v2.", sector:"Fintech", urgent:true },
  { id:2, ts:"13/03 09:15", title:"Thông báo lấy ý kiến Luật PPP sửa đổi lần 2", src:"Bộ KH&ĐT", type:"CONSULT", risk:61, tag:"Infrastructure · PPP", analysis:"Mở rộng phạm vi dự án PPP sang lĩnh vực y tế và giáo dục. Deadline 30/03/2026.", sector:"Investment", urgent:false },
  { id:3, ts:"12/03 17:30", title:"NQ Chuyển đổi số ngành bảo hiểm — Ban hành chính thức", src:"Chính phủ", type:"ENACTED", risk:77, tag:"InsurTech · Digital", analysis:"Yêu cầu 100% hợp đồng bảo hiểm số hóa trước 2028. Cơ hội lớn cho sản phẩm tham số.", sector:"Insurance", urgent:true },
  { id:4, ts:"12/03 14:00", title:"Công văn hướng dẫn kê khai thuế sàn TMĐT", src:"Tổng cục Thuế", type:"GUIDANCE", risk:34, tag:"Tax · E-commerce", analysis:"Áp dụng từ 01/04/2026. Nền tảng TMĐT phải khấu trừ thuế tại nguồn 1% doanh thu.", sector:"Tax", urgent:false },
  { id:5, ts:"11/03 10:20", title:"Quyết định 96 — Hướng dẫn cấp phép sàn tài sản số", src:"SSC / Bộ TC", type:"ENACTED", risk:85, tag:"Crypto · Licensing", analysis:"3 sàn đầu tiên được cấp phép thí điểm. Khung pháp lý rõ hơn cho token listing.", sector:"Fintech", urgent:true },
  { id:6, ts:"11/03 08:45", title:"Dự thảo Nghị định xử phạt vi phạm PDPD", src:"Bộ Công an", type:"DRAFT", risk:79, tag:"Data · Privacy", analysis:"Mức phạt tối đa 5% doanh thu năm. Doanh nghiệp có 6 tháng để tuân thủ sau ban hành.", sector:"Compliance", urgent:true },
  { id:7, ts:"10/03 16:00", title:"Thông tư 15/2026 — Chuẩn mực kế toán tài sản số", src:"Bộ Tài chính", type:"ENACTED", risk:68, tag:"Accounting · Crypto", analysis:"Token issuance proceeds ghi nhận là nợ phải trả. Áp dụng cho tổ chức, không cá nhân.", sector:"Fintech", urgent:false },
  { id:8, ts:"09/03 11:10", title:"Đề xuất sửa đổi Luật Ngân hàng 2010", src:"NHNN", type:"PROPOSAL", risk:55, tag:"Banking · Reform", analysis:"Mở rộng điều kiện cho vay ngang hàng P2P. Phải qua Quốc hội — dự kiến 2027.", sector:"Banking", urgent:false },
];

// Org hierarchy: Chính phủ → Ban KT TW + Bộ ngành
const ORG = {
  id:"gov", name:"Chính phủ", short:"GOV", role:"Thủ tướng", color:"#4499dd",
  children:[
    { id:"ptt", name:"Trần Hồng Hà", short:"PTT", role:"Phó Thủ tướng", color:"#4499dd",
      children:[
        { id:"nhnn", name:"Nguyễn Văn Thắng", short:"NHNN", role:"Thống đốc NHNN", color:"#5dcaa5",
          children:[
            { id:"ptdg", name:"Phạm Tiến Dũng", short:"PTĐ·NHNN", role:"Phó Thống đốc", color:"#5dcaa5", children:[] },
          ]
        },
        { id:"btc", name:"Hồ Đức Phớc", short:"BTC", role:"Bộ trưởng Tài chính", color:"#c8a84b",
          children:[
            { id:"tct", name:"Mai Xuân Thành", short:"TCT", role:"Tổng cục trưởng TCT", color:"#c8a84b", children:[] },
            { id:"qlbh", name:"Ngô Việt Trung", short:"QLBH", role:"Cục trưởng QLBH", color:"#c8a84b", children:[] },
          ]
        },
        { id:"bct", name:"Nguyễn Hồng Diên", short:"BCT", role:"Bộ trưởng BCT", color:"#e05533", children:[] },
      ]
    },
    { id:"bktw", name:"Lê Minh Hưng", short:"BKTW", role:"Trưởng Ban KT TW", color:"#9977ee", children:[] },
    { id:"bca", name:"Tô Lâm", short:"BCA", role:"Bộ trưởng Công an", color:"#dd4477", children:[] },
  ]
};

const FORECAST_DATA = [
  { doc:"QĐ 96", dept:"BTC", fq:"Q4/2025", actual:"Q4/2025", acc:97, stage:"Released" },
  { doc:"TT 15/2026", dept:"BTC", fq:"Q1/2026", actual:"02/2026", acc:92, stage:"Released" },
  { doc:"NĐ Crypto", dept:"NHNN", fq:"Q2/2026", actual:"—", acc:null, stage:"Draft" },
  { doc:"NĐ PDPD", dept:"BCA", fq:"Q2/2026", actual:"—", acc:null, stage:"Consult" },
  { doc:"Luật Fintech", dept:"NHNN", fq:"2027", actual:"—", acc:null, stage:"Pre-draft" },
];

const INIT_CHAT = [
  { r:"sys", t:"VRIT v5.0 ONLINE — 847 tài liệu · 12 luồng giám sát · 3 cảnh báo nghiêm trọng" },
  { r:"usr", t:"Phân tích tác động NĐ crypto đến Nami Foundation" },
  { r:"sys", t:"Phân tích hoàn tất → Yêu cầu: (1) Đăng ký NHNN 90 ngày, (2) Vốn pháp định ≥50 tỷ, (3) Tách biệt 100% tài sản KH. Lợi thế: VNST + CypherCore. Đề xuất: chuẩn bị hồ sơ Q2/2026." },
];

const INIT_LOG = [
  { id:1, ts:"13/03 09:14", type:"RESEARCH", txt:"NĐ crypto — Nami Foundation impact", st:"DONE" },
  { id:2, ts:"12/03 16:30", type:"MONITOR", txt:"Sandbox bảo hiểm số Cục QLBH", st:"ACTIVE" },
  { id:3, ts:"11/03 11:00", type:"MEETING", txt:"Đặt lịch Cục QLBH về sandbox", st:"PENDING" },
  { id:4, ts:"10/03 08:45", type:"REPORT", txt:"Rủi ro regulatory Q1/2026", st:"DONE" },
];

const RCOL = { CRITICAL:"#ff3333", HIGH:"#ff7700", MEDIUM:"#ffcc00", LOW:"#33dd88" };
const TCOL_FEED = { DRAFT:"#ff7700", CONSULT:"#5577ee", ENACTED:"#33dd88", GUIDANCE:"#5dcaa5", PROPOSAL:"#9977ee" };

// Flat map: simplified world coastlines (SVG path-like point arrays)
// We'll draw a simplified SEA region with key country outlines
const GEO = { latMin:1, latMax:25, lngMin:98, lngMax:115 };
const VN_POLY = [[23.4,102.9],[23.3,104.9],[22.5,103.9],[22.0,104.0],[21.5,102.5],[20.5,103.0],[20.0,104.0],[18.2,105.6],[17.5,106.0],[16.0,108.0],[15.2,108.6],[13.0,109.3],[11.5,109.1],[10.5,107.4],[10.0,105.4],[10.5,104.3],[11.5,103.4],[13.0,103.0],[14.5,103.5],[17.0,104.0],[19.0,103.0],[20.5,102.8],[23.4,102.9]];
const TH_POLY = [[20.4,99.0],[21.0,101.0],[22.0,100.5],[22.5,101.0],[20.5,103.0],[20.0,104.0],[18.0,103.5],[17.0,102.5],[15.0,102.0],[13.0,100.5],[11.5,99.5],[10.5,99.8],[6.5,100.2],[5.5,101.5],[6.0,102.5],[7.5,103.5],[10.0,99.0],[12.5,99.5],[16.0,98.5],[18.0,98.0],[20.4,99.0]];
const KH_POLY = [[14.5,103.5],[13.0,103.0],[11.5,103.4],[10.5,104.3],[10.5,105.0],[11.0,105.5],[12.0,107.0],[13.5,107.5],[14.5,107.0],[14.5,103.5]];
const LA_POLY = [[22.5,101.0],[22.0,103.5],[21.5,104.0],[20.5,103.0],[22.5,101.0]];
const MY_POLY = [[6.5,100.2],[5.5,101.5],[2.5,103.5],[2.0,104.5],[2.5,103.0],[4.5,103.5],[6.0,102.5],[7.5,103.5],[6.5,100.2]];
const CN_POLY = [[23.4,102.9],[23.3,104.9],[22.5,103.9],[22.0,104.0],[22.5,101.0],[21.0,101.0],[20.4,99.0],[22.0,98.5],[24.0,98.0],[25.0,98.5],[23.4,102.9]];
const CITIES = [
  { n:"Hà Nội", lat:21.03, lng:105.85, main:true },
  { n:"TP.HCM", lat:10.78, lng:106.70, main:true },
  { n:"Đà Nẵng", lat:16.05, lng:108.22, main:false },
  { n:"Cần Thơ", lat:10.04, lng:105.78, main:false },
  { n:"Hải Phòng", lat:20.86, lng:106.68, main:false },
];

function geo2xy(lat, lng, W, H, pad=20) {
  const x = pad + (lng - GEO.lngMin) / (GEO.lngMax - GEO.lngMin) * (W - pad*2);
  const y = pad + (1-(lat - GEO.latMin)/(GEO.latMax - GEO.latMin)) * (H - pad*2);
  return { x, y };
}

const OFFICER_PINS = [
  { id:"nhnn", name:"NV Thắng", role:"Thống đốc NHNN", city:"Hà Nội", lat:21.05, lng:105.82, color:"#5dcaa5" },
  { id:"btc",  name:"HĐ Phớc",  role:"Bộ trưởng BTC",  city:"Hà Nội", lat:21.01, lng:105.88, color:"#c8a84b" },
  { id:"ptt",  name:"TH Hà",    role:"Phó Thủ tướng",  city:"Hà Nội", lat:21.03, lng:105.85, color:"#4499dd" },
  { id:"bktw", name:"LM Hưng",  role:"Trưởng Ban KTTW",city:"Hà Nội", lat:21.07, lng:105.80, color:"#9977ee" },
  { id:"bct",  name:"NH Diên",  role:"Bộ trưởng BCT",  city:"Hà Nội", lat:21.00, lng:105.84, color:"#e05533" },
  { id:"ptdg", name:"PT Dũng",  role:"Phó TĐ NHNN",    city:"TP.HCM", lat:10.80, lng:106.68, color:"#5dcaa5" },
];

// ── MAIN ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [phase, setPhase] = useState("boot");
  const [bootStep, setBootStep] = useState(0);
  const [risks, setRisks] = useState(RISKS);
  const [centerView, setCenterView] = useState("feed");
  const [selOfficer, setSelOfficer] = useState(null);
  const [selFeed, setSelFeed] = useState(null);
  const [feedFilter, setFeedFilter] = useState("ALL");
  const [chat, setChat] = useState(INIT_CHAT);
  const [cmdInput, setCmdInput] = useState("");
  const [log, setLog] = useState(INIT_LOG);
  const [cmdOpen, setCmdOpen] = useState(false);
  const chatEnd = useRef(null);

  const BOOT_LINES = [
    "INITIALIZING VRIT v5.0 — VIETNAM REGULATORY INTELLIGENCE TERMINAL",
    "SCANNING ORIGIN IP: 103.72.xx.xx → HO CHI MINH CITY NODE DETECTED",
    "CROSS-REFERENCING DEVICE FINGERPRINT MATRIX...",
    "GEOLOCATION LOCK: VIETNAM · SEA CLUSTER · UTC+7",
    "VALIDATING EXECUTIVE CLEARANCE CREDENTIALS...",
    "DECRYPTING IDENTITY TOKEN — BIOMETRIC MATCH CONFIRMED",
    "LOADING 847 REGULATORY DOCUMENTS...",
    "CONNECTING SCRAPE NETWORK: 12/12 SOURCES LIVE",
    "◈ ACCESS GRANTED — CLEARANCE LEVEL: ALPHA ◈",
  ];

  useEffect(() => {
    if (phase !== "boot") return;
    if (bootStep < BOOT_LINES.length) {
      const t = setTimeout(() => setBootStep(s => s+1), bootStep===0?200:360);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setPhase("live"), 900);
    return () => clearTimeout(t);
  }, [phase, bootStep]);

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior:"smooth" }); }, [chat]);

  const actRisk = (id, s) => setRisks(r => r.map(x => x.id===id ? {...x, st:x.st===s?null:s} : x));

  const sendCmd = async () => {
    if (!cmdInput.trim()) return;
    const q = cmdInput; setCmdInput("");
    setChat(c => [...c, { r:"usr", t:q }, { r:"sys", t:"◈ Đang phân tích qua Firm OS…" }]);
    const ts = new Date().toLocaleString("vi-VN",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
    setLog(l => [{ id:l.length+1, ts, type:"RESEARCH", txt:q, st:"ACTIVE" }, ...l]);
    try {
      const res = await aegisApi.localIntel({ entity: q, jurisdiction: "VN" });
      setChat(c => [...c.slice(0,-1), { r:"sys", t: fmt.localIntel(res) }]);
      setLog(l => l.map(x => (x.txt===q && x.st==="ACTIVE") ? { ...x, st:"DONE" } : x));
    } catch {
      setChat(c => [...c.slice(0,-1), { r:"sys", t:"⚠ Lỗi kết nối Firm OS bridge — kiểm tra api_bridge đang chạy." }]);
    }
  };

  if (phase === "boot") return <BootScreen lines={BOOT_LINES} step={bootStep} />;

  const feedItems = feedFilter==="ALL" ? FEED : FEED.filter(f=>f.type===feedFilter||f.sector===feedFilter);

  return (
    <div style={{ background:"#020c08", display:"flex", flexDirection:"column", flex:1, fontFamily:"'Courier New',monospace", color:"#7ecfaa", fontSize:11, overflow:"hidden" }}>
      <style>{`
        @keyframes tk{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
        @keyframes bl{0%,100%{opacity:1}50%{opacity:0}}
        @keyframes sd{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes ri{from{opacity:0;transform:translateX(8px)}to{opacity:1;transform:translateX(0)}}
        ::-webkit-scrollbar{width:3px;height:3px}
        ::-webkit-scrollbar-track{background:#020c08}
        ::-webkit-scrollbar-thumb{background:#0d2a1a;border-radius:2px}
        input::placeholder{color:#1a4a2a}
        input:focus{outline:none}
      `}</style>

      {/* MAIN 3-COL LAYOUT */}
      <div style={{ flex:1, display:"grid", gridTemplateColumns:"236px 1fr 230px", overflow:"hidden", minHeight:0 }}>

        {/* ── LEFT: Risk Monitor + Action Log ── */}
        <div style={{ borderRight:"1px solid #0a2014", display:"flex", flexDirection:"column", overflow:"hidden" }}>
          {/* KPIs */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:3, padding:"7px 7px 3px", flexShrink:0 }}>
            {[["C",risks.filter(r=>r.lvl==="CRITICAL").length,"#ff3333"],["H",risks.filter(r=>r.lvl==="HIGH").length,"#ff7700"],["M",risks.filter(r=>r.lvl==="MEDIUM").length,"#ffcc00"],["▶",risks.filter(r=>r.st==="mon").length,"#5577ee"]].map(([k,v,c])=>(
              <div key={k} style={{ background:"#030f0a", border:`1px solid ${c}28`, padding:"4px 6px", borderRadius:2, textAlign:"center" }}>
                <div style={{ color:c, fontSize:6.5, letterSpacing:1 }}>{k}</div>
                <div style={{ color:c, fontSize:17, fontWeight:700, lineHeight:1.1 }}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{ padding:"2px 8px 3px", color:"#0a3018", fontSize:7, letterSpacing:1.5, flexShrink:0 }}>⬡ RISK MONITOR</div>

          {/* Risk cards */}
          <div style={{ flex:1, overflowY:"auto", padding:"0 7px", minHeight:0 }}>
            {risks.map(r=>(
              <div key={r.id} style={{ marginBottom:5, background:"#030f0a", borderLeft:`2px solid ${RCOL[r.lvl]}`, border:`1px solid #0a2014`, borderLeftWidth:2, borderLeftColor:RCOL[r.lvl], padding:"6px 8px", borderRadius:"0 2px 2px 0" }}>
                <div style={{ display:"flex", gap:4, alignItems:"center", marginBottom:2 }}>
                  <span style={{ background:RCOL[r.lvl]+"1a", color:RCOL[r.lvl], fontSize:6.5, padding:"0 4px", borderRadius:2, fontWeight:700, flexShrink:0 }}>{r.lvl}</span>
                  <span style={{ color:"#0a3018", fontSize:7, marginLeft:"auto", flexShrink:0 }}>{r.date}</span>
                </div>
                <div style={{ color:"#8ad4b0", fontSize:9, fontWeight:700, marginBottom:2, lineHeight:1.3 }}>{r.title}</div>
                <div style={{ color:"#1a4a2a", fontSize:8, lineHeight:1.45, marginBottom:4 }}>{r.desc}</div>
                <div style={{ display:"flex", gap:3, alignItems:"center" }}>
                  {[["elab","E","#33dd88"],["just","J","#c8a84b"],["mon","M","#5577ee"]].map(([k,lb,c])=>(
                    <button key={k} onClick={()=>actRisk(r.id,k)} style={{ background:r.st===k?c+"22":"transparent", border:`1px solid ${r.st===k?c:"#0a2014"}`, color:r.st===k?c:"#1a4a2a", width:20,height:15,cursor:"pointer",fontSize:7,borderRadius:2,fontFamily:"inherit" }}>{lb}</button>
                  ))}
                  <span style={{ color:"#0a3018", fontSize:7, marginLeft:2 }}>{r.src}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Action Log */}
          <div style={{ borderTop:"1px solid #0a2014", padding:"5px 7px 3px", color:"#0a3018", fontSize:7, letterSpacing:1.5, flexShrink:0 }}>⊞ ACTION LOG</div>
          <div style={{ overflowY:"auto", maxHeight:148, padding:"0 7px 7px", minHeight:0 }}>
            {log.map(a=>{
              const sc={DONE:"#33dd88",ACTIVE:"#c8a84b",PENDING:"#5577ee"};
              const tc={RESEARCH:"#5dcaa5",MONITOR:"#9977ee",MEETING:"#e05533",REPORT:"#c8a84b"};
              return (
                <div key={a.id} style={{ marginBottom:4, padding:"5px 7px", background:"#030f0a", borderLeft:`2px solid ${tc[a.type]||"#444"}`, border:`1px solid #0a2014`, borderLeftWidth:2, borderLeftColor:tc[a.type]||"#444", borderRadius:"0 2px 2px 0" }}>
                  <div style={{ display:"flex", gap:4, marginBottom:2 }}>
                    <span style={{ color:tc[a.type],fontSize:6.5 }}>{a.type}</span>
                    <span style={{ color:"#0a3018",fontSize:6.5 }}>{a.ts}</span>
                    <span style={{ color:sc[a.st],fontSize:6.5,marginLeft:"auto" }}>{a.st}</span>
                  </div>
                  <div style={{ color:"#3a7a5a",fontSize:8.5,lineHeight:1.35 }}>{a.txt}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── CENTER: Feed / Map / Forecast ── */}
        <div style={{ display:"flex", flexDirection:"column", overflow:"hidden" }}>
          {/* Center toggle bar */}
          <div style={{ display:"flex", alignItems:"center", borderBottom:"1px solid #0a2014", flexShrink:0 }}>
            {[["feed","⬡ LIVE FEED"],["map","⊕ INTEL MAP"],["forecast","⟁ FORECAST"]].map(([k,v])=>(
              <button key={k} onClick={()=>setCenterView(k)} style={{ background:centerView===k?"#0a2018":"transparent", borderTop:"none",borderLeft:"none",borderRight:"1px solid #0a2014",borderBottom:centerView===k?"2px solid #00ee77":"2px solid transparent", color:centerView===k?"#00ee77":"#1a4a2a", padding:"5px 14px",cursor:"pointer",fontSize:9,letterSpacing:1.5,fontFamily:"inherit" }}>{v}</button>
            ))}
            {centerView==="feed" && (
              <div style={{ display:"flex", gap:3, padding:"0 10px", marginLeft:4 }}>
                {["ALL","DRAFT","ENACTED","CONSULT"].map(f=>(
                  <button key={f} onClick={()=>setFeedFilter(f)} style={{ background:feedFilter===f?"#0a2018":"transparent", border:`1px solid ${feedFilter===f?"#2a6a4a":"#0a2014"}`, color:feedFilter===f?"#5dcaa5":"#1a4a2a", padding:"2px 7px", cursor:"pointer", fontSize:7.5, borderRadius:2, fontFamily:"inherit" }}>{f}</button>
                ))}
              </div>
            )}
            <div style={{ flex:1 }}/>
            <span style={{ color:"#0a3018", fontSize:7.5, padding:"0 12px" }}>
              {centerView==="feed" ? `${feedItems.length} DOCUMENTS` : centerView==="map" ? "SEA INTEL MAP" : "FORECAST ACCURACY"}
            </span>
          </div>

          <div style={{ flex:1, overflow:"hidden", position:"relative", minHeight:0 }}>
            {centerView==="feed"     && <FeedView items={feedItems} sel={selFeed} setSel={setSelFeed} />}
            {centerView==="map"      && <MapView officers={OFFICER_PINS} sel={selOfficer} setSel={setSelOfficer} />}
            {centerView==="forecast" && <ForecastView data={FORECAST_DATA} />}
          </div>
        </div>

        {/* ── RIGHT: Org Hierarchy + Officer detail ── */}
        <div style={{ borderLeft:"1px solid #0a2014", display:"flex", flexDirection:"column", overflow:"hidden" }}>
          <div style={{ padding:"7px 10px 4px", color:"#0a3018", fontSize:7, letterSpacing:1.5, flexShrink:0 }}>◎ GOVERNMENT HIERARCHY</div>
          <div style={{ flex:1, overflowY:"auto", padding:"0 8px 8px", minHeight:0 }}>
            <OrgTree node={ORG} depth={0} sel={selOfficer} setSel={setSelOfficer} />
          </div>
        </div>

      </div>

      {/* ── COMMAND BAR ── */}
      <div style={{ borderTop:"1px solid #0a2014", background:"#020c08", flexShrink:0 }}>
        {cmdOpen && (
          <div style={{ height:155, display:"flex", borderBottom:"1px solid #0a2014", overflow:"hidden", animation:"sd .2s ease" }}>
            <div style={{ flex:1, overflowY:"auto", padding:"8px 12px", display:"flex", flexDirection:"column", gap:5 }}>
              {chat.map((m,i)=>(
                <div key={i} style={{ display:"flex", gap:8 }}>
                  <span style={{ color:m.r==="usr"?"#c8a84b":"#00ee77", fontSize:7.5, minWidth:42, paddingTop:1, flexShrink:0 }}>{m.r==="usr"?"▸ YOU":"◈ VRIT"}</span>
                  <span style={{ color:m.r==="usr"?"#8ad4b0":"#2a6a4a", fontSize:9.5, lineHeight:1.55 }}>{m.t}</span>
                </div>
              ))}
              <div ref={chatEnd}/>
            </div>
            <div style={{ width:170, borderLeft:"1px solid #0a2014", overflowY:"auto", padding:"8px 10px" }}>
              <div style={{ color:"#0a3018", fontSize:7, letterSpacing:1, marginBottom:5 }}>THOUGHT LOG</div>
              {chat.filter(m=>m.r==="usr").map((m,i)=>(
                <div key={i} style={{ borderBottom:"1px solid #030f0a", paddingBottom:4, marginBottom:4 }}>
                  <div style={{ color:"#0a3018", fontSize:6.5 }}>Q{i+1}</div>
                  <div style={{ color:"#2a6a4a", fontSize:8.5, lineHeight:1.4 }}>{m.t}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div style={{ display:"flex", alignItems:"center", gap:8, padding:"5px 12px" }}>
          <span style={{ color:"#00ee77", fontSize:9 }}>◈</span>
          <input value={cmdInput} onChange={e=>setCmdInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&sendCmd()} onFocus={()=>setCmdOpen(true)} placeholder="Nhập lệnh phân tích — Enter to send..." style={{ flex:1, background:"transparent", border:"none", color:"#8ad4b0", fontSize:10, fontFamily:"inherit", padding:"2px 0" }}/>
          <button onClick={sendCmd} style={{ background:"transparent", border:"1px solid #0a2014", color:"#2a6a4a", fontSize:8, padding:"3px 10px", cursor:"pointer", fontFamily:"inherit", letterSpacing:1 }}>SEND ▸</button>
          <button onClick={()=>setCmdOpen(o=>!o)} style={{ background:"transparent", border:"1px solid #0a2014", color:"#1a4a2a", fontSize:8, padding:"3px 8px", cursor:"pointer", fontFamily:"inherit" }}>{cmdOpen?"▾":"▴"} LOG</button>
        </div>
      </div>
    </div>
  );
}

// ── Boot ──────────────────────────────────────────────────────────────────────
function BootScreen({ lines, step }) {
  const [scan, setScan] = useState(0);
  useEffect(()=>{ const iv=setInterval(()=>setScan(s=>(s+1)%100),22); return ()=>clearInterval(iv); },[]);
  return (
    <div style={{ background:"#000", minHeight:"100%", fontFamily:"'Courier New',monospace", display:"flex", alignItems:"center", justifyContent:"center", position:"relative", overflow:"hidden" }}>
      <div style={{ position:"absolute", inset:0, backgroundImage:"repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,255,80,.01) 3px,rgba(0,255,80,.01) 4px)", pointerEvents:"none" }}/>
      <div style={{ position:"absolute", inset:0, background:`linear-gradient(transparent ${scan}%,rgba(0,255,80,.04) ${scan}%,rgba(0,255,80,.04) ${scan+1.5}%,transparent ${scan+1.5}%)`, pointerEvents:"none" }}/>
      <div style={{ width:540, border:"1px solid #00ff44", padding:"36px 44px" }}>
        <div style={{ color:"#00ff44", fontSize:18, fontWeight:700, letterSpacing:5, marginBottom:2 }}>◈ VRIT SECURE ACCESS</div>
        <div style={{ color:"#003a1a", fontSize:8, letterSpacing:3, marginBottom:24 }}>EXECUTIVE INTELLIGENCE TERMINAL — CLEARANCE ALPHA</div>
        <div style={{ minHeight:210 }}>
          {lines.slice(0,step).map((l,i)=>(
            <div key={i} style={{ display:"flex", gap:10, marginBottom:5, color:i===step-1?"#00ff44":"#003a1a", fontSize:9.5 }}>
              <span style={{ color:"#001a0a" }}>[{String(i+1).padStart(2,"0")}]</span>
              <span>{l}{i===step-1&&<span style={{ animation:"bl .7s infinite" }}>█</span>}</span>
            </div>
          ))}
        </div>
        {step>=lines.length&&<div style={{ borderTop:"1px solid #003a1a", paddingTop:14, textAlign:"center", color:"#00ff44", fontSize:12, letterSpacing:4 }}>◈ ACCESS GRANTED ◈</div>}
        <div style={{ marginTop:18, height:2, background:"#001a0a" }}>
          <div style={{ height:"100%", background:"#00ff44", width:`${Math.min(100,(step/lines.length)*100)}%`, transition:"width .35s" }}/>
        </div>
      </div>
      <style>{`@keyframes bl{0%,100%{opacity:1}50%{opacity:0}}`}</style>
    </div>
  );
}

// ── Live Feed ─────────────────────────────────────────────────────────────────
function FeedView({ items, sel, setSel }) {
  const [ai, setAi] = useState({});          // id → live analysis text
  const [aiLoading, setAiLoading] = useState({});
  const elaborate = async (item, mode) => {
    setAiLoading(p=>({...p,[item.id]:true}));
    try {
      const res = await aegisApi.localIntel({
        entity: item.title,
        jurisdiction: "VN",
        topics: [item.sector, item.type].filter(Boolean),
        org_context: mode === "Justify" ? "Justify the risk rating citing specific Vietnamese legal instruments." : undefined,
      });
      setAi(p=>({...p,[item.id]: fmt.localIntel(res)}));
    } catch { setAi(p=>({...p,[item.id]:"⚠ Lỗi kết nối Firm OS bridge."})); }
    setAiLoading(p=>({...p,[item.id]:false}));
  };
  const pushToNewsfeed = (item) => {
    aegisBus.emit("PUSH_TO_NEWSFEED", "VRIT", {
      id: item.id,
      title: item.title,
      src: item.src,
      risk: item.risk,
      type: item.type,
      tag: item.tag,
      urgent: item.urgent,
      analysis: item.analysis,
      emittedAt: Date.now(),
    });
  };

  return (
    <div style={{ height:"100%", overflowY:"auto", padding:"8px 10px" }}>
      {items.map(item=>{
        const tc = TCOL_FEED[item.type]||"#888";
        const isSel = sel?.id===item.id;
        const riskColor = item.risk>=80?"#ff3333":item.risk>=60?"#ff7700":item.risk>=40?"#ffcc00":"#33dd88";
        return (
          <div key={item.id} onClick={()=>setSel(isSel?null:item)} style={{ marginBottom:6, background:"#030f0a", border:`1px solid ${isSel?"#2a6a4a":"#0a2014"}`, borderLeft:`3px solid ${tc}`, padding:"8px 10px", borderRadius:"0 3px 3px 0", cursor:"pointer" }}>
            {/* Row 1: type + tag + timestamp */}
            <div style={{ display:"flex", gap:6, alignItems:"center", marginBottom:4 }}>
              <span style={{ background:tc+"22", color:tc, fontSize:7, padding:"0 5px", height:14, display:"flex", alignItems:"center", borderRadius:2, fontWeight:700, flexShrink:0 }}>{item.type}</span>
              {item.urgent && <span style={{ color:"#ff3333", fontSize:7, animation:"bl 2s infinite" }}>● URGENT</span>}
              <span style={{ color:"#1a4a2a", fontSize:7, background:"#0a2014", padding:"0 5px", borderRadius:2 }}>{item.tag}</span>
              <span style={{ color:"#0a3018", fontSize:7, marginLeft:"auto" }}>{item.ts}</span>
            </div>
            {/* Row 2: title */}
            <div style={{ color:"#8ad4b0", fontSize:10, fontWeight:700, marginBottom:3, lineHeight:1.3 }}>{item.title}</div>
            {/* Row 3: source + risk score */}
            <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom: isSel?6:0 }}>
              <span style={{ color:"#1a4a2a", fontSize:7.5 }}>📄 {item.src}</span>
              <div style={{ display:"flex", alignItems:"center", gap:5, marginLeft:"auto" }}>
                <div style={{ width:60, height:3, background:"#0a2014", borderRadius:2 }}>
                  <div style={{ width:`${item.risk}%`, height:"100%", background:riskColor, borderRadius:2 }}/>
                </div>
                <span style={{ color:riskColor, fontSize:8, fontWeight:700, minWidth:24 }}>{item.risk}</span>
                <span style={{ color:"#0a3018", fontSize:7 }}>RISK</span>
              </div>
            </div>
            {/* Expanded: AI analysis */}
            {isSel && (
              <div style={{ borderTop:"1px solid #0a2014", paddingTop:6, animation:"sd .15s ease" }}>
                <div style={{ color:"#0a3018", fontSize:7, letterSpacing:1, marginBottom:3 }}>◈ AI ANALYSIS</div>
                <div style={{ color:"#3a7a5a", fontSize:9, lineHeight:1.6, whiteSpace:"pre-wrap" }}>{aiLoading[item.id] ? "◈ Đang phân tích qua Firm OS…" : (ai[item.id] || item.analysis)}</div>
                <div style={{ display:"flex", gap:4, marginTop:6 }}>
                  {["Elaborate","Justify","Add to Monitor","Export"].map(a=>{
                    const onClick = (e) => {
                      e.stopPropagation();
                      if (a === "Add to Monitor") pushToNewsfeed(item);
                      else if (a === "Elaborate" || a === "Justify") elaborate(item, a);
                    };
                    return (
                      <button key={a} onClick={onClick} style={{ background:"transparent", border:"1px solid #0a2014", color:"#2a6a4a", fontSize:7.5, padding:"2px 7px", cursor:"pointer", borderRadius:2, fontFamily:"inherit" }}>{a}</button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Flat Map ──────────────────────────────────────────────────────────────────
function MapView({ officers, sel, setSel }) {
  const svgRef = useRef(null);
  const [dim, setDim] = useState({ w:600, h:400 });
  useEffect(()=>{
    const ro = new ResizeObserver(([e])=>setDim({ w:e.contentRect.width||600, h:e.contentRect.height||400 }));
    if (svgRef.current) ro.observe(svgRef.current);
    return ()=>ro.disconnect();
  },[]);
  const W=dim.w, H=dim.h;
  const g = (la,ln)=>geo2xy(la,ln,W,H,22);

  const polys = [
    { pts:VN_POLY,   fill:"rgba(0,255,100,.08)", stroke:"rgba(0,255,100,.45)", sw:1.2 },
    { pts:TH_POLY,   fill:"rgba(60,180,255,.04)", stroke:"rgba(60,180,255,.18)", sw:.6 },
    { pts:KH_POLY,   fill:"rgba(60,180,255,.04)", stroke:"rgba(60,180,255,.18)", sw:.6 },
    { pts:MY_POLY,   fill:"rgba(60,180,255,.04)", stroke:"rgba(60,180,255,.18)", sw:.6 },
    { pts:CN_POLY,   fill:"rgba(60,180,255,.03)", stroke:"rgba(60,180,255,.12)", sw:.5 },
    { pts:LA_POLY,   fill:"rgba(60,180,255,.04)", stroke:"rgba(60,180,255,.15)", sw:.5 },
  ];

  // lat/lng grid labels
  const latLines=[5,10,15,20,25], lngLines=[100,103,106,109,112];

  return (
    <svg ref={svgRef} width="100%" height="100%" style={{ display:"block" }}>
      <defs>
        <radialGradient id="mbg" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stopColor="#030d18"/>
          <stop offset="100%" stopColor="#010810"/>
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill="url(#mbg)"/>
      {/* Grid */}
      {latLines.map(la=>{ const p1=g(la,98),p2=g(la,115); return <line key={la} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="rgba(0,200,100,.06)" strokeWidth={.5}/>; })}
      {lngLines.map(ln=>{ const p1=g(1,ln),p2=g(25,ln); return <line key={ln} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="rgba(0,200,100,.06)" strokeWidth={.5}/>; })}
      {/* Grid labels */}
      {latLines.map(la=>{ const p=g(la,98.2); return <text key={la} x={p.x} y={p.y+3} fontSize={7} fill="rgba(0,200,100,.2)" fontFamily="monospace">{la}°N</text>; })}
      {lngLines.map(ln=>{ const p=g(24.5,ln); return <text key={ln} x={p.x-8} y={p.y+8} fontSize={7} fill="rgba(0,200,100,.2)" fontFamily="monospace">{ln}°E</text>; })}
      {/* Country fills */}
      {polys.map((po,i)=>(
        <polygon key={i} points={po.pts.map(([la,ln])=>{ const p=g(la,ln); return `${p.x},${p.y}`; }).join(" ")} fill={po.fill} stroke={po.stroke} strokeWidth={po.sw}/>
      ))}
      {/* Sea label */}
      {(()=>{ const p=g(10,111); return <text x={p.x} y={p.y} fontSize={8} fill="rgba(60,180,255,.15)" fontFamily="monospace" fontStyle="italic">Biển Đông</text>; })()}
      {/* City dots */}
      {CITIES.map(c=>{ const p=g(c.lat,c.lng); return (
        <g key={c.n}>
          <circle cx={p.x} cy={p.y} r={c.main?2.5:1.5} fill={c.main?"rgba(0,255,100,.4)":"rgba(0,255,100,.2)"} stroke="rgba(0,255,100,.3)" strokeWidth={.5}/>
          <text x={p.x+4} y={p.y+3} fontSize={c.main?7.5:6.5} fill={c.main?"rgba(0,255,100,.35)":"rgba(0,255,100,.2)"} fontFamily="monospace">{c.n}</text>
        </g>
      );})}
      {/* Officer pins */}
      {officers.map(o=>{
        const p=g(o.lat,o.lng), isSel=sel?.id===o.id;
        return (
          <g key={o.id} onClick={()=>setSel(isSel?null:o)} style={{ cursor:"pointer" }}>
            {/* Drop shadow */}
            <ellipse cx={p.x} cy={p.y+18} rx={5} ry={2} fill={o.color} opacity={.12}/>
            {/* Pin spike */}
            <line x1={p.x} y1={p.y+6} x2={p.x} y2={p.y+18} stroke={o.color} strokeWidth={1.2} opacity={.6}/>
            {/* Pulse ring when selected */}
            {isSel&&<circle cx={p.x} cy={p.y} r={16} fill={o.color+"15"} stroke={o.color} strokeWidth={.8} strokeDasharray="2 2"/>}
            {/* Pin head */}
            <circle cx={p.x} cy={p.y} r={isSel?9:7} fill={o.color+"30"} stroke={o.color} strokeWidth={isSel?1.5:1}/>
            <circle cx={p.x} cy={p.y} r={2.5} fill={o.color}/>
            {/* Name label */}
            <text x={p.x+11} y={p.y-2} fontSize={7.5} fill={o.color} fontFamily="monospace" fontWeight={700}>{o.name}</text>
            <text x={p.x+11} y={p.y+7} fontSize={6.5} fill={o.color+"99"} fontFamily="monospace">{o.role.split(" ").slice(0,2).join(" ")}</text>
          </g>
        );
      })}
      {/* Dossier popup */}
      {sel&&(()=>{
        const p=g(sel.lat,sel.lng);
        const bx=Math.min(p.x+20, W-200), by=Math.min(p.y-10, H-100);
        return (
          <g style={{ animation:"sd .15s ease" }}>
            <rect x={bx} y={by} width={190} height={88} rx={3} fill="rgba(2,12,8,.97)" stroke={sel.color} strokeWidth={.8}/>
            <text x={bx+10} y={by+16} fontSize={7.5} fill={sel.color} fontFamily="monospace" fontWeight={700}>◎ DOSSIER — {sel.name}</text>
            <line x1={bx+6} y1={by+22} x2={bx+184} y2={by+22} stroke={sel.color} strokeWidth={.4} opacity={.4}/>
            <text x={bx+10} y={by+35} fontSize={8.5} fill="#8ad4b0" fontFamily="monospace">{sel.role}</text>
            <text x={bx+10} y={by+50} fontSize={7.5} fill="#2a6a4a" fontFamily="monospace">📍 {sel.city}</text>
            <text x={bx+10} y={by+66} fontSize={7} fill={sel.color+"aa"} fontFamily="monospace">Ministry: {sel.id.toUpperCase()}</text>
            <text x={bx+10} y={by+80} fontSize={7} fill="#1a4a2a" fontFamily="monospace">Click node in hierarchy →</text>
          </g>
        );
      })()}
      {/* Compass */}
      <text x={W-16} y={22} textAnchor="middle" fontSize={9} fill="rgba(0,255,100,.25)" fontFamily="monospace">N</text>
      <line x1={W-16} y1={24} x2={W-16} y2={34} stroke="rgba(0,255,100,.15)" strokeWidth={.5}/>
      <text x={W-16} y={43} textAnchor="middle" fontSize={9} fill="rgba(0,255,100,.15)" fontFamily="monospace">S</text>
    </svg>
  );
}

// ── Org Tree ──────────────────────────────────────────────────────────────────
function OrgTree({ node, depth, sel, setSel }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isSel = sel?.id === node.id;
  const indent = depth * 12;

  return (
    <div>
      <div
        onClick={()=>{ setSel(isSel?null:node); if(hasChildren) setOpen(o=>!o); }}
        style={{ display:"flex", alignItems:"center", gap:6, padding:"5px 6px", marginBottom:2, background:isSel?"#0a2018":"transparent", border:`1px solid ${isSel?node.color||"#2a6a4a":"transparent"}`, borderRadius:2, cursor:"pointer", marginLeft:indent, animation:isSel?"ri .15s ease":"none" }}
      >
        {/* Tree connector */}
        {depth>0&&<span style={{ color:"#0a2014", fontSize:8, flexShrink:0 }}>{hasChildren?(open?"▾":"▸"):"└"}</span>}
        {/* Badge */}
        <div style={{ width:28, height:18, background:(node.color||"#444")+"22", border:`1px solid ${node.color||"#444"}`, borderRadius:2, display:"flex", alignItems:"center", justifyContent:"center", fontSize:6.5, color:node.color||"#444", fontWeight:700, flexShrink:0 }}>{node.short||node.id.toUpperCase().slice(0,4)}</div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ color:"#8ad4b0", fontSize:8.5, fontWeight:700, lineHeight:1.2, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{node.name}</div>
          <div style={{ color:"#1a4a2a", fontSize:7, lineHeight:1.2 }}>{node.role}</div>
        </div>
      </div>
      {/* Expanded detail */}
      {isSel&&node.bias&&(
        <div style={{ marginLeft:indent+12, marginBottom:4, padding:"5px 8px", background:"#030f0a", border:`1px solid ${node.color||"#444"}22`, borderRadius:2, animation:"sd .15s ease" }}>
          <div style={{ color:"#0a3018", fontSize:6.5, letterSpacing:1, marginBottom:3 }}>BIAS PROFILE</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:3, marginBottom:4 }}>
            {(node.bias||[]).map(b=><span key={b} style={{ background:"#020c08", border:`1px solid ${node.color||"#444"}44`, color:"#3a7a5a", fontSize:7, padding:"1px 5px", borderRadius:2 }}>{b}</span>)}
          </div>
          {node.inf&&<div style={{ height:2, background:"#0a2014", borderRadius:1 }}><div style={{ width:`${node.inf}%`, height:"100%", background:node.color||"#444", borderRadius:1 }}/></div>}
        </div>
      )}
      {/* Children */}
      {hasChildren&&open&&node.children.map(child=>(
        <OrgTree key={child.id} node={child} depth={depth+1} sel={sel} setSel={setSel} />
      ))}
    </div>
  );
}

// ── Forecast View ─────────────────────────────────────────────────────────────
function ForecastView({ data }) {
  const [sel, setSel] = useState(null);
  const SC={Released:"#33dd88",Draft:"#ff7700",Consult:"#5577ee","Pre-draft":"#555"};
  return (
    <div style={{ height:"100%", overflowY:"auto", padding:"10px 12px", boxSizing:"border-box" }}>
      {/* Bar chart */}
      <div style={{ background:"#030f0a", border:"1px solid #0a2014", padding:"10px 12px", borderRadius:3, marginBottom:10 }}>
        <div style={{ color:"#0a3018", fontSize:7, letterSpacing:1.5, marginBottom:8 }}>FORECAST ACCURACY — RELEASED DOCS</div>
        <div style={{ display:"flex", gap:8, alignItems:"flex-end", height:56 }}>
          {data.map(d=>(
            <div key={d.doc} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:3 }}>
              <span style={{ color:d.acc?"#33dd88":"#0a3018", fontSize:8 }}>{d.acc?d.acc+"%":"—"}</span>
              <div style={{ width:"100%", background:"#0a1a14", borderRadius:2, height:36, display:"flex", alignItems:"flex-end", border:d.acc?"none":"1px dashed #0a2014" }}>
                {d.acc&&<div style={{ width:"100%", height:`${d.acc}%`, background:d.acc>90?"#33dd88":"#c8a84b", borderRadius:2 }}/>}
              </div>
              <span style={{ color:"#0a3018", fontSize:6.5, textAlign:"center" }}>{d.doc}</span>
            </div>
          ))}
        </div>
      </div>
      {/* Table */}
      <div style={{ background:"#030f0a", border:"1px solid #0a2014", borderRadius:3, overflow:"hidden" }}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"#020a06" }}>
              {["Doc","Dept","Forecast","Actual","Acc","Stage"].map(h=>(
                <th key={h} style={{ color:"#0a3018", fontSize:7, padding:"6px 10px", textAlign:"left", borderBottom:"1px solid #0a2014", letterSpacing:1 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((d,i)=>(
              <tr key={i} onClick={()=>setSel(sel===i?null:i)} style={{ background:sel===i?"#0a2018":i%2===0?"#030f0a":"#020a06", cursor:"pointer", borderLeft:sel===i?"2px solid #00ee77":"2px solid transparent" }}>
                <td style={{ color:"#8ad4b0", fontSize:9.5, padding:"6px 10px", fontWeight:700 }}>{d.doc}</td>
                <td style={{ color:"#2a6a4a", fontSize:8.5, padding:"6px 10px" }}>{d.dept}</td>
                <td style={{ color:"#c8a84b", fontSize:8.5, padding:"6px 10px" }}>{d.fq}</td>
                <td style={{ color:d.actual==="—"?"#0a2014":"#5dcaa5", fontSize:8.5, padding:"6px 10px" }}>{d.actual}</td>
                <td style={{ padding:"6px 10px" }}>
                  {d.acc
                    ? <div style={{ display:"flex", alignItems:"center", gap:5 }}><div style={{ width:40, background:"#0a1a14", height:2.5, borderRadius:2 }}><div style={{ width:`${d.acc}%`, height:"100%", background:d.acc>90?"#33dd88":"#c8a84b", borderRadius:2 }}/></div><span style={{ color:"#8ad4b0", fontSize:8 }}>{d.acc}%</span></div>
                    : <span style={{ color:"#0a2014" }}>—</span>}
                </td>
                <td style={{ padding:"6px 10px" }}>
                  <span style={{ background:(SC[d.stage]||"#555")+"22", color:SC[d.stage]||"#555", fontSize:7.5, padding:"1px 6px", borderRadius:2 }}>{d.stage}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sel!==null&&<div style={{ marginTop:8, background:"#030f0a", border:"1px solid #00ee7733", padding:"7px 12px", borderRadius:3, fontSize:8.5, color:"#2a6a4a" }}>⟁ PIVOT → <span style={{ color:"#8ad4b0" }}>{data[sel]?.dept}</span> · {data[sel]?.stage} · Next review Q2/2026</div>}
    </div>
  );
}
