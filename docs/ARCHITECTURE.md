# AEGIS — Architecture

> Ngăn xếp 6 lớp Firm OS (L1–L6). Request đi xuống qua các lớp; khóa nhà cung cấp chỉ tồn tại từ L5 trở xuống. Frontend chỉ nói chuyện với **một host** (single-origin: FastAPI phục vụ cả bản build tĩnh và `/api`).

Xem thêm: [`../PRD.md`](../PRD.md) · [`STACK.md`](STACK.md)

---

## 1. Ngăn xếp lớp

```
┌─────────────────────────────────────────────────────────┐
│  L6  Interaction — React Shell (AEGIS)                    │  frontend/aegis/
│      4 module TSX/JSX + Signal Feed · Zustand · aegisApi  │
├─────────────────────────────────────────────────────────┤
│  L5  Agents — Firm OS                                     │  src/agents.py, engine.py
│      Research · Compliance · Operations · EA · Drafting    │
├─────────────────────────────────────────────────────────┤
│  L4  Skills (eval-gated)                                  │  L4_Skills/
├─────────────────────────────────────────────────────────┤
│  L3  Tools — RSS, sanctions/UBO, scrape, file ingest      │  src/tools/, L3_Tools/
├─────────────────────────────────────────────────────────┤
│  L2  Memory — org/session context, cross-module queues    │  L2_Memory/
├─────────────────────────────────────────────────────────┤
│  L1  Knowledge Foundation — GraphRAG (Neo4j / NetworkX)   │  src/graph/, L1_Knowledge_Foundation/
└─────────────────────────────────────────────────────────┘
```

---

## 2. Đường đi của một request

```
React Shell (L6)
   │  fetch / SSE
   │  headers: X-User-Api-Key, X-User-Model   (BYO key — tùy chọn)
   ▼
api_bridge.py  (FastAPI)
   │  UserKeyMiddleware   → contextvars (key/model theo từng request)
   │  BasicAuthMiddleware → HTTP Basic gate (khi DEMO_PASSWORD set)
   │  RateLimitMiddleware → per-IP sliding window (BYO key được miễn)
   ▼
engine.py / agents (L5)
   │  _call_claude(system, user, sim=…)
   ▼
Claude API (server-side / BYO key)  +  GraphRAG (L1–L3)
   │
   ▼
Envelope { data, meta }  → mở gói tại aegisApi.ts
```

**Thứ tự middleware** (ngoài vào trong): `RateLimit` → `BasicAuth` → `UserKey`. `UserKeyMiddleware` chạy gần handler nhất để contextvar còn sống suốt lời gọi agent.

---

## 3. Bản đồ module ↔ agent ↔ endpoint

| Module (L6) | Agent (L5) | Endpoint prefix |
|---|---|---|
| REGO · Macro Radar | Research + Drafting | `/api/research/*`, `/api/drafting/*` |
| VRIT · Local Intel | Compliance | `/api/compliance/*` |
| EIT1 · Newsfeed | Operations / Intelligence | `/api/operations/*`, `/api/research/verify-org`, `/api/news/feed` |
| EIT2 · War Room | Executive Assistant | `/api/executive/*` |

Danh sách endpoint đầy đủ: xem [`../PRD.md`](../PRD.md) §5.

---

## 4. Pipeline EIT1 (SSE)

`POST /api/operations/ingest/stream` phát các event `stage` / `log` / `result` / `done` khớp `PIPELINE_STAGES` phía frontend:

```
INGEST → CATEGORIZE → VERIFY → FILTER → CLUSTER → SYNTHESIZE → SCORE → REVIEW
```

`aegisApi.postStream()` đọc body theo chunk, tách theo `\n\n`, parse dòng `data:`. Khi nhận `result`, frontend **chuẩn hóa field** (`headline→title`, `rawCredibility→credibilityScore`, `summary→synthesis`) trước khi render Pipeline Monitor và decision gate.

---

## 5. Event bus (cross-module)

`frontend/aegis/eventBus.ts` + store queues:

| Nguồn | Sự kiện | Đích |
|---|---|---|
| REGO | tín hiệu `CRITICAL` | Signal Feed + `newsfeedQueue` + ticker + notification |
| VRIT | push document | Newsfeed pipeline |
| EIT1 | escalation thẻ | `warRoomQueue` (EIT2) |
| EIT2 | simulation hoàn tất | notification `SUCCESS` |

---

## 6. Chế độ Simulation

`_call_claude(system, user, sim=<stub>)`:

```python
def _call_claude(system, user, max_tokens=2000, sim=None):
    key = _active_key()                     # user key > env key
    if not key:
        return json.dumps(sim) if sim is not None else json.dumps({...})
    client = Anthropic(api_key=key)
    return client.messages.create(model=_active_model(), ...).content[0].text
```

Mỗi endpoint truyền `sim=` **đúng schema** mà UI mong đợi. Không có key → toàn bộ 4 module vẫn chạy đầy đủ (`meta.simulation = true`).

---

## 7. GraphRAG (L1) — dual backend

| Backend | Khi nào | Setup |
|---|---|---|
| **NetworkX** (in-memory) | mặc định — dev / demo | seed từ `src/graph/seed/seed_data.json` |
| **Neo4j** | production | set `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` |

Cùng bộ query chạy trên cả hai backend (`src/graph/queries.py`): UBO chain traversal, jurisdiction comparison, mandates due. Agent fallback về simulation có nhãn rõ khi không có dữ liệu graph khớp.
