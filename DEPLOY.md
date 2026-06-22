# Deploying AEGIS — a real shareable link

One Docker image hosts everything: the AEGIS UI **and** the Firm OS API on a
single URL. Provider API keys stay server-side; a shared password + per-IP rate
limit protect the public link.

```
https://aegis-demo.onrender.com
   ├─ /          → AEGIS React build      (the face)
   └─ /api/*     → api_bridge.py / agents (the brain)  ← ANTHROPIC_API_KEY here
```

## Phase 1 — Render (for UAT)

1. Push this repo to GitHub (the `Dockerfile` + `render.yaml` are at the root).
2. On [render.com](https://render.com): **New → Blueprint**, pick the repo.
   Render reads `render.yaml` and creates one Docker web service.
3. After the first build, open the service → **Environment** and set the two
   secrets (marked `sync: false`):
   - `ANTHROPIC_API_KEY` — your Claude key.
   - `DEMO_PASSWORD` — the shared password you'll send with the link.
   (`DEMO_USER=demo`, `RATE_LIMIT_PER_HOUR=60`, `CLAUDE_MODEL` come from the blueprint.)
4. Redeploy. Share the URL **and** the `demo` / password. Visitors get a browser
   login prompt, then the live app.

**Cost guard:** every visitor IP is capped at `RATE_LIMIT_PER_HOUR` AI calls.
Also set a spend limit on the Anthropic console as a backstop. To run a
zero-cost demo, leave `ANTHROPIC_API_KEY` unset → the app runs in simulation
mode (stub responses, `meta.simulation = true`).

## Phase 2 — Vercel + Railway (post-UAT, production split)

When you outgrow the single host:
- **Frontend → Vercel:** root `frontend/aegis`, build `npm run build`, output
  `dist`. Set `VITE_API_BASE=https://<railway-backend-url>`.
- **Backend → Railway:** deploy `src/api_bridge.py` (same Dockerfile or a Python
  service). Set `ANTHROPIC_API_KEY`, `DEMO_PASSWORD`, etc.
- **CORS:** add the Vercel origin to `allow_origins` in `api_bridge.py`.
- Two URLs, independent scaling, CDN on the frontend.

## Local check before deploying

```bash
# Backend (simulation mode is fine without a key)
pip install -r requirements.txt
uvicorn src.api_bridge:app --port 8000
# → http://localhost:8000/api/health

# Frontend (split dev)
cd frontend/aegis && npm install
VITE_API_BASE=http://localhost:8000 npm run dev   # → http://localhost:5173

# Or full single-host like production:
cd frontend/aegis && npm run build && cd ../..
uvicorn src.api_bridge:app --port 8000            # serves UI + API at :8000
```

## Protection summary

| Env var | Effect |
|---|---|
| `DEMO_PASSWORD` | Empty → no gate. Set → HTTP Basic over whole site + API. |
| `DEMO_USER` | Basic-auth username (default `demo`). |
| `RATE_LIMIT_PER_HOUR` | Max AI calls per visitor IP per hour (default 60). |
| `ANTHROPIC_API_KEY` | Unset → simulation mode (no spend). Set → live Claude. |

`/api/health` is always open (no auth, no rate limit) for uptime checks.
