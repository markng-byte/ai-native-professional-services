# AEGIS — Product Requirements Document

> **Strategic Intelligence Operating System** — nền tảng tình báo chiến lược AI-native cho Việt Nam & Đông Nam Á.

| | |
|---|---|
| **Version** | v2.1 |
| **Cập nhật** | 2026-08-14 |
| **Trạng thái** | Live / UAT |
| **Nhánh** | `claude/focused-fermi-ksutxb` |
| **Kiến trúc** | Firm OS L1–L6 |

Tài liệu liên quan: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/STACK.md`](docs/STACK.md) · [`DEPLOY.md`](DEPLOY.md)

---

## 1. Tầm nhìn sản phẩm

AEGIS biến tín hiệu **pháp lý — thị trường — địa chính trị** thô thành sản phẩm tình báo có thể hành động: thẻ tín hiệu, báo cáo, kịch bản mô phỏng. Mọi lệnh gọi AI đi qua **một API Bridge duy nhất** (L6 → L5) để khóa nhà cung cấp nằm ở server và mỗi request đều chạm một agent Firm OS.

- **Đối tượng** — Founder / Entrepreneur, General Counsel, PE / Managing Partner, và Super Admin nội bộ.
- **Trọng tâm** — Việt Nam & SEA: hyper-local regulatory intelligence, CBDC, fintech, crypto, M&A.
- **Nguyên tắc** — Con người xét duyệt các quyết định trọng yếu; agent **không tự phê duyệt** compliance.
- **Chế độ chạy** — Live AI (server key hoặc BYO key) & Simulation (stub đúng schema theo từng endpoint).

> **Định vị:** AEGIS là lớp giao tiếp (L6) ngồi trên toàn bộ ngăn xếp Firm OS. Người dùng không bao giờ chạm trực tiếp Claude API hay GraphRAG — họ chạm 4 module, mỗi module là một mặt của cùng một bộ agent.

---

## 2. Kiến trúc hệ thống (tóm tắt)

Chi tiết đầy đủ tại [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```
React Shell (L6)
   │  fetch / SSE  + headers X-User-Api-Key / X-User-Model
   ▼
api_bridge.py  (FastAPI)          # không lộ key, không nhận raw prompt từ browser
   │  UserKeyMiddleware → contextvars
   │  RateLimit / BasicAuth (tùy env)
   ▼
engine.py / agents (L5)
   ▼
Claude API (server-side key)  +  GraphRAG (L1–L3)
```

| Lớp | Tên | Vai trò |
|---|---|---|
| **L6** | Interaction — React Shell (AEGIS) | 4 module + Signal Feed. Gọi API qua `aegisApi.ts`. |
| **L5** | Agents — Firm OS | Research, Compliance, Operations/Intelligence, Executive Assistant, Drafting. |
| **L4** | Skills | Kỹ năng đóng gói tái sử dụng, eval-gated test suite. |
| **L3** | Tools | RSS aggregator, sanctions/UBO, scraping, file ingest. |
| **L2** | Memory | Ngữ cảnh org/phiên, hàng đợi cross-module. |
| **L1** | Knowledge Foundation — GraphRAG | Neo4j / NetworkX, kho tri thức nền. |

> **Simulation Mode:** khi không có key nào (server lẫn user), mỗi endpoint trả về một **stub đúng schema** mà UI mong đợi (không còn `{"_simulation": true}` chung chung). Nhờ vậy toàn bộ 4 module vẫn "chạy" đầy đủ để demo.

---

## 3. Bốn module + Signal Feed

Cùng một bộ agent, bốn mặt tác nghiệp.

### REGO · Macro Radar — *Global regulatory intelligence*
Radar pháp lý toàn cầu. Tín hiệu `CRITICAL` của REGO đẩy sang Signal Feed + hàng đợi Newsfeed + ticker + notification.
- Signal Impact — đánh giá tác động một tín hiệu
- What-If — mô phỏng biến thể kịch bản pháp lý
- Risk Projection — điểm rủi ro hiện tại vs dự phóng 12 tháng
- Stakeholder Map + Advocacy Brief

### VRIT · Local Intel — *Vietnam / SEA local signals*
Terminal tình báo pháp lý Việt Nam với màn boot "clearance ALPHA". Ô lệnh chat gọi `localIntel`, kết quả format qua `fmt.localIntel`.
- Local Intel — key instruments, compliance flags
- Sanctions / PEP / adverse media screen
- UBO traverse — chuỗi sở hữu & xung đột lợi ích
- 3 view: Live Feed · Intel Map · Forecast

### EIT1 · Intelligence Newsfeed — *Signal synthesis & pipeline*
Pipeline 8 stage (`INGEST → CATEGORIZE → VERIFY → FILTER → CLUSTER → SYNTHESIZE → SCORE → REVIEW`) chạy qua SSE, đổ vào Pipeline Monitor.
- Ingestion: keywords / web scrape / CSV-Excel
- Decision gate: `publish` · `escalate` · `investigate` · `waitlist` · `draft` (AUTO PUBLISH hoặc MANUAL REVIEW)
- Newsfeed: lọc theo category/action/freshness/priority; fallback RSS trực tiếp
- Reports: Trend Outlook · Industry Analysis · Specific Subject Analysis

### EIT2 · War Room — *Scenario planning & simulation*
Nhập business plan → sinh 3 kịch bản Bull/Base/Bear có xác suất → mô phỏng hành động → đề xuất cải thiện. Mỗi bước có fallback nội bộ nếu API lỗi.
- Scenarios + Next Steps (thư viện hành động)
- Simulation: waterfall variance vs plan
- Improvements: đạt target variance theo ràng buộc
- Tab khóa tuần tự cho tới khi bước trước hoàn tất

### Signal Feed (view mặc định)
Feed tổng hợp là màn hình đầu tiên sau đăng nhập. Gọi `aegisApi.ingest()` (trả `{cards:[…]}`, 8 thẻ) và ánh xạ về schema `Signal`:

| Nguồn (API) | → | Đích (Signal) |
|---|---|---|
| `headline` | → | `title` |
| `rawCredibility` / `impactScore` | → | `confidence` |
| `suggestedAction` / `priority` | → | `level` |

Ánh xạ level: `Escalate → CRITICAL`, `Act → HIGH`, `Investigate → MEDIUM`, `Monitor → LOW`. Mảng `signals` **chỉ nằm trong bộ nhớ**, reset khi `clearUserProfile()`.

---

## 4. Luồng UX (mobile-first)

```
Login → Onboarding → Profile Mapping → Signal Feed → Module (REGO/VRIT/EIT1/EIT2)
```

| Bước | Màn hình | Nội dung |
|---|---|---|
| 01 | Login | Chọn vai trò hoặc Super Admin |
| 02 | Onboarding | Org profile · jurisdictions · sectors |
| 03 | Profile Mapping | Loader ánh xạ hồ sơ → agent |
| 04 | Signal Feed | 8 thẻ tín hiệu SEA |
| 05 | Module | REGO · VRIT · EIT1 · EIT2 |

Điều hướng qua `activeView` (`FEED` | module) & `activeModule`. Super Admin (`loginAdmin()`) bỏ qua onboarding: gọi `clearUserProfile()` + `setFeedInitialized(false)` rồi `setUserProfile(admin)` để feed luôn nạp lại sạch.

**Event bus (cross-module):**
- REGO CRITICAL → Signal Feed + Newsfeed queue + ticker + notification
- VRIT push → Newsfeed pipeline
- EIT1 escalation → War Room queue
- EIT2 simulation done → notification SUCCESS

---

## 5. Backend & API — `src/api_bridge.py` (FastAPI v2)

Pydantic v2 · CORS · SSE (`StreamingResponse`) · `StaticFiles`. Middleware xếp chồng: `RateLimit` → `BasicAuth` → `UserKey`.

```bash
uvicorn src.api_bridge:app --host 0.0.0.0 --port 8000
```

| Method | Endpoint | Module | Chức năng |
|---|---|---|---|
| GET  | `/api/health` | Shared | Trạng thái + `key_source` (user/server/none) + model |
| GET  | `/api/news/feed` | EIT1 | RSS aggregator (Reuters, BBC, CNBC) interleaved |
| POST | `/api/research/signal-impact` | REGO | Đánh giá tác động tín hiệu |
| POST | `/api/research/what-if` | REGO | Mô phỏng kịch bản pháp lý |
| POST | `/api/research/risk-projection` | REGO | Điểm rủi ro hiện tại vs dự phóng |
| POST | `/api/research/stakeholder-map` | REGO | Bản đồ 5 stakeholder ưu tiên |
| POST | `/api/research/regulatory-lookup` | REGO | Tổng quan pháp lý theo jurisdiction |
| POST | `/api/research/jurisdiction-compare` | REGO | So sánh nhiều jurisdiction |
| POST | `/api/research/verify-org` | EIT1 | Xác minh / enrich tên tổ chức |
| POST | `/api/drafting/advocacy-brief` | REGO | Brief vận động cho stakeholder |
| POST | `/api/drafting/engagement-letter` | Drafting | Thư mời hợp tác |
| POST | `/api/compliance/local-intel` | VRIT | Tình báo pháp lý hyper-local |
| POST | `/api/compliance/sanctions-screen` | VRIT | Sanctions / PEP / adverse media |
| POST | `/api/compliance/ubo-traverse` | VRIT | Chuỗi UBO + xung đột lợi ích |
| POST | `/api/operations/ingest` | EIT1 | Pipeline đầy đủ → 8 thẻ (non-stream) |
| SSE  | `/api/operations/ingest/stream` | EIT1 | Pipeline stage-by-stage cho Monitor |
| POST | `/api/operations/report-generate` | EIT1 | Sinh báo cáo từ thẻ tín hiệu |
| POST | `/api/operations/report-assemble` | EIT1 | Lắp ráp báo cáo hoàn chỉnh |
| POST | `/api/executive/scenarios` | EIT2 | Sinh 3 kịch bản Bull/Base/Bear |
| POST | `/api/executive/next-steps` | EIT2 | Thư viện hành động chiến lược |
| POST | `/api/executive/simulate` | EIT2 | Mô phỏng variance vs plan |
| POST | `/api/executive/improvements` | EIT2 | Đề xuất đạt target variance |
| POST | `/api/executive/brief` | Shared | Board brief / synthesis đa module |
| POST | `/api/executive/scenario` | EIT2 | Kịch bản đơn lẻ |

### Envelope chuẩn

Mọi endpoint trả về `{ data, meta }`. `aegisApi.ts` mở gói `data` cho caller và giữ `meta` cho badge simulation/review.

```json
{
  "data": { "…": "theo từng endpoint" },
  "meta": {
    "agent": "operations",
    "simulation": false,
    "requires_human_review": true,
    "sources": [],
    "model": "…_active_model()",
    "run_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

---

## 6. BYO API Key — wire end-to-end

Người dùng dán Anthropic key + chọn model trong `SettingsModal`. Key lưu ở `localStorage` (store `aegis-store-v2`), gửi theo **mỗi request** qua header, được bắt vào `contextvars` chỉ trong vòng đời request — **không log, không lưu server-side**.

```
SettingsModal → aegisStore (persist) → aegisApi.authHeaders()
  → UserKeyMiddleware (header → contextvar) → _active_key() (ưu tiên user key hơn env)
```

```python
# api_bridge.py
_user_key_ctx = contextvars.ContextVar("user_api_key", default="")

class UserKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tok = _user_key_ctx.set(request.headers.get("X-User-Api-Key", "").strip())
        try:    return await call_next(request)
        finally: _user_key_ctx.reset(tok)

def _active_key():   return _user_key_ctx.get() or _ANTHROPIC_KEY
def _active_model(): return _user_model_ctx.get() or _MODEL
```

- **Rate-limit bypass:** request có BYO key bỏ qua bộ giới hạn per-IP (người dùng tự trả tiền usage). Chỉ request dùng server key mới bị đếm.
- **Model dropdown:** Server default · Opus 4.8 · Sonnet 4.6 · Haiku 4.5.
- Status dot trong Settings ping `/api/health` với key hiện tại để hiện `key_source`.

---

## 7. Quản lý state — Zustand + persist

| Được persist (`partialize`) | Chỉ trong bộ nhớ |
|---|---|
| `userProfile`, `orgProfile`, `profileComplete` | `signals[]` (reset khi clear profile) |
| `sidebarCollapsed`, `activeModule` | `notifications`, `tickerAlerts` |
| `feedInitialized` | `newsfeedQueue`, `warRoomQueue` |
| `userApiKey`, `userModel` | `apiBridgeConnected`, `globalRiskScore` |

Store version `aegis-store-v2` (bump để xóa state cũ). `clearUserProfile()` đặt lại `userProfile=null, signals=[], feedInitialized=false` — điểm mấu chốt để feed Super Admin nạp lại đúng.

---

## 8. Bảo mật & giới hạn

| Cơ chế | Mô tả |
|---|---|
| **BasicAuth Gate** | `DEMO_USER`/`DEMO_PASSWORD` → HTTP Basic phủ toàn site + API. Không set → không gate (dev cục bộ). |
| **Rate Limit** | `RATE_LIMIT_PER_HOUR` (mặc định 60) — sliding window per-IP trên endpoint AI. BYO key được miễn. |
| **Key isolation** | Key nhà cung cấp chỉ tồn tại server-side; BYO key chỉ sống trong contextvar mỗi request, không bao giờ ghi log. |
| **Human-in-the-loop** | Endpoint compliance đặt `requires_human_review`; agent không tự phê duyệt cảnh báo compliance. |

Open paths (không auth/limit): `/api/health`, `/favicon.ico`. CORS cho phép origin localhost dev.

---

## 9. Triển khai

**Hiện tại:** FastAPI phục vụ cả bản build React và `/api` trên **một host** (Docker · Render/Railway). Xem [`DEPLOY.md`](DEPLOY.md).

Biến môi trường: `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `DEMO_USER/PASSWORD`, `RATE_LIMIT_PER_HOUR`, `VITE_ADMIN_USER/PASSCODE`, `AIRTABLE_API_KEY` (tùy chọn), `NEO4J_URI/USER/PASSWORD` (tùy chọn).

**Phase 2 (hoãn tới sau UAT):** tách deploy Vercel (frontend tĩnh) + Railway (API bridge), dùng `VITE_API_BASE` trỏ cross-origin.

---

## 10. Changelog mới nhất

| Loại | Thay đổi |
|---|---|
| FIX | **EIT1 · thẻ pipeline tương tác lại được** — chuẩn hóa `headline→title`, `rawCredibility→credibilityScore`, `summary→synthesis` sau SSE result. |
| FIX | **EIT1 · Reports không còn treo im lặng** — `runAnalysis()` bọc try/catch/finally; lỗi API hiện banner đỏ. |
| FIX | **EIT2 · nút Generate Scenario bật sẵn** — `SAMPLE_PLAN` nạp sẵn kế hoạch CBDC thực (>50 ký tự). |
| FIX | **Super Admin · Signal Feed hiển thị lại** — `loginAdmin()` gọi `clearUserProfile()` + `setFeedInitialized(false)` trước khi set profile. |
| FEAT | **BYO API key end-to-end** — Settings → header mỗi request → contextvar → `_active_key()`; miễn rate-limit. |
| FEAT | **Simulation stub theo từng endpoint** — 4 module chạy được ở chế độ demo không cần key. |
| FEAT | **Signal Feed dùng endpoint `ingest`** — chuyển từ `signalImpact()` sang `ingest()` (mảng 8 thẻ). |

---

## 11. Roadmap & hạng mục mở

- **Split deploy Vercel + Railway** — sau khi UAT ổn định.
- **Persistence thật cho signals/reports** — hiện `SAMPLE_INTEL/HISTORY/REPORTS` vẫn là demo tĩnh trong EIT1.
- **Kết nối GraphRAG/Neo4j sản xuất** — hiện tùy chọn, mặc định tắt (NetworkX in-memory).
- **Kiểm thử E2E cho 4 luồng module** với và không có BYO key.
- **Airtable sink** cho báo cáo đã publish (tùy chọn qua `AIRTABLE_API_KEY`).

---

*Tài liệu nội bộ — tổng hợp từ trạng thái code mới nhất trên nhánh `claude/focused-fermi-ksutxb`.*
