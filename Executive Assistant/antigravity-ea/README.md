# Senior EA — Antigravity Local Execution Engine
# Setup Guide

---

## What this is
Antigravity configured as a **local execution engine** for your Senior EA.
The EA can: use your browser for research, run terminal scripts, read/write files,
sync to Google Drive — all triggered by natural language from Agent Manager.

---

## Workspace structure
```
senior-ea-workspace/
├── GEMINI.md                    ← Antigravity identity + local machine config
├── AGENTS.md                    ← Persistent rules (read every session)
├── .agents/
│   ├── agents.md                ← 3 personas: Orchestrator, Researcher, Executor, Drafter
│   ├── workflows/               ← Slash commands
│   │   ├── brief.md             → /brief
│   │   ├── meeting.md           → /meeting
│   │   ├── research.md          → /research
│   │   ├── report.md            → /report
│   │   └── sync.md              → /sync
│   └── skills/                  ← Agent-triggered capabilities
│       ├── drive-sync/
│       ├── meeting-capture/
│       ├── research-browser/
│       ├── brief-builder/
│       ├── exec-brief/
│       └── report-draft/
└── brain/                       ← Persistent memory + all outputs
    ├── context.md               ← Running session log
    ├── meetings/
    ├── research/
    ├── reports/
    └── decisions/
```

---

## Setup checklist (do once before first use)

**Step 1 — Install Antigravity**
Download from antigravity.google and install on your machine.

**Step 2 — Create workspace**
Open Antigravity → Agent Manager → + Open Workspace
Select or create a local folder, name it `senior-ea`
Copy all files from this package into that folder.

**Step 3 — Fill in your machine details**
Open `GEMINI.md` and fill in:
- `[fill in: Mac/Windows/Linux]` → your OS
- `[fill in: e.g. ~/Google Drive/My Drive]` → your actual Drive mount path

Open `AGENTS.md` and fill in the OneIBC Context section:
- CRM name
- Any additional context about your team / reporting structure

**Step 4 — Set model**
In Antigravity → top-right `...` → Settings → Model
Select: Claude Sonnet (recommended for reasoning tasks)

**Step 5 — Verify Drive mount**
In Agent Manager, type: `/sync`
If Drive is mounted correctly, you'll see a sync confirmation.
If not, check the Drive path in GEMINI.md.

**Step 6 — First run**
Type: `/brief`
The EA will ask for your task list and produce your first weekly brief.

---

## How to use (daily)

| What you type | What happens |
|---|---|
| `/brief` | Monday priorities brief |
| `/meeting` | Paste notes → structured summary |
| `/research <topic>` | Browser research → structured brief |
| `/report` | Paste team updates → status report |
| `/sync` | Push all brain/ files to Drive |
| Natural language | EA routes to correct skill automatically |

**Examples of natural language triggers:**
- "tóm tắt meeting vừa xong: [paste notes]"
- "research về substance requirements ở BVI 2026"
- "tình trạng các tasks tuần này: [paste list]"
- "viết exec brief cho doc này: [paste content]"

---

## How skills vs workflows differ

| | Workflows | Skills |
|---|---|---|
| **Triggered by** | You (`/command`) | Agent (when it judges it's relevant) |
| **Purpose** | Macros you run on demand | Modular capabilities loaded as needed |
| **Example** | `/brief` on Monday morning | Agent loads `exec-brief` skill when you say "tóm tắt cho sếp" |

---

## Connecting to Telegram (next step)
To receive requests from Telegram and get results back:
```
Telegram → n8n webhook → Antigravity API or local script → response to Telegram
```
This requires a small n8n workflow. Ask the EA to build it: "build me a Telegram bridge using n8n"

---

## Files never to delete
- `GEMINI.md` — EA loses its identity
- `AGENTS.md` — EA loses its rules
- `brain/context.md` — EA loses its memory
