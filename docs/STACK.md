# AEGIS — Tech Stack & Quickstart

Xem thêm: [`../PRD.md`](../PRD.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`../DEPLOY.md`](../DEPLOY.md)

---

## 1. Stack

### Frontend (L6) — `frontend/aegis/`
| Thành phần | Công nghệ |
|---|---|
| Framework | React 19 |
| Build tool | Vite 8 |
| Ngôn ngữ | TypeScript 5.6 |
| State | Zustand 5 (+ `persist`) |
| Charts | Recharts 3 |
| Styling | Inline CSS-in-JS (design tokens per module) |

### Backend (L5–L1) — `src/`
| Thành phần | Công nghệ |
|---|---|
| API bridge | FastAPI (Pydantic v2) |
| Server | Uvicorn (ASGI) |
| Streaming | SSE qua `StreamingResponse` |
| AI provider | Anthropic Claude (`anthropic` SDK) |
| Graph | Neo4j (prod) / NetworkX (dev) |
| Command Center | Streamlit (`src/app.py`) |
| Container | Docker (single image: UI + API) |

---

## 2. Cấu trúc monorepo

```
.
├── PRD.md                     # Product Requirements Document
├── README.md                  # Tổng quan repo
├── DEPLOY.md                  # Hướng dẫn triển khai
├── docs/
│   ├── ARCHITECTURE.md        # Kiến trúc L1–L6, request flow, event bus
│   └── STACK.md               # Tài liệu này
│
├── frontend/aegis/            # L6 — React shell
│   ├── aegis.tsx              #   App shell, routing, TopBar, SettingsModal
│   ├── aegisApi.ts            #   Client API + authHeaders (BYO key)
│   ├── aegisStore.ts          #   Zustand store (persist)
│   ├── eventBus.ts            #   Cross-module events
│   ├── LoginScreen.tsx        #   Chọn vai trò + Super Admin
│   ├── OnboardingFlow.tsx     #   Org profile
│   ├── ProfileMappingLoader.tsx
│   ├── SignalFeed.tsx         #   Feed mặc định (ingest → 8 thẻ)
│   ├── rego_dashboard_v4.tsx  #   REGO · Macro Radar
│   ├── vrit_v4.tsx            #   VRIT · Local Intel
│   ├── eit_module1.tsx        #   EIT1 · Newsfeed + pipeline
│   └── eit_module2.jsx        #   EIT2 · War Room
│
├── src/                       # L5–L1 — backend
│   ├── api_bridge.py          #   FastAPI — 24 endpoint + middleware
│   ├── agents.py, engine.py   #   Agent layer
│   ├── app.py                 #   Streamlit Command Center
│   ├── tools/                 #   L3 tools
│   └── graph/                 #   L1 GraphRAG (dual backend)
│
├── L1_Knowledge_Foundation/ … L6_Interaction/   # Spec docs từng lớp
├── governance/                # Chính sách
├── Dockerfile, render.yaml, railway.json        # Deploy config
└── requirements.txt           # Python deps
```

---

## 3. Quickstart

### Backend + UI (single host)
```bash
pip install -r requirements.txt

# Build frontend
cd frontend/aegis && npm install && npm run build && cd ../..

# Chạy API bridge (phục vụ cả dist/ và /api)
uvicorn src.api_bridge:app --host 0.0.0.0 --port 8000
# → http://localhost:8000
```

### Dev split (hot reload)
```bash
# Terminal 1 — API
uvicorn src.api_bridge:app --reload --port 8000

# Terminal 2 — Vite dev server
cd frontend/aegis
VITE_API_BASE=http://localhost:8000 npm run dev
# → http://localhost:5173
```

### Không cần API key
Bỏ trống `ANTHROPIC_API_KEY` → app chạy **Simulation Mode** (stub đúng schema, `meta.simulation = true`). Hoặc người dùng dán **BYO key** trong ⚙ Settings.

---

## 4. Biến môi trường

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Claude key server-side. Bỏ trống → simulation mode. |
| `CLAUDE_MODEL` | — | Model mặc định (vd `claude-sonnet-4-6`). |
| `DEMO_USER` / `DEMO_PASSWORD` | — | Bật HTTP Basic gate cho link công khai. |
| `RATE_LIMIT_PER_HOUR` | — | Giới hạn AI call per-IP (mặc định 60). BYO key được miễn. |
| `VITE_ADMIN_USER` / `VITE_ADMIN_PASSCODE` | — | Thông tin Super Admin (frontend). |
| `VITE_API_BASE` | — | Base URL API cho dev split / cross-origin. |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | — | Bật GraphRAG backend Neo4j. |
| `AIRTABLE_API_KEY` | — | Sink báo cáo (tùy chọn). |

---

## 5. Build & test

```bash
# Frontend build
cd frontend/aegis && npm run build

# Graph tests
python tests/test_graph.py

# Eval suite (L4 skills)
python run_evals.py
```
