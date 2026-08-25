# RM Co-pilot — Phase 5 Scope: the RM Surface

> **Status:** scope for approval — **no implementation performed**.
> **Base:** `main` @ `b809d52` (PR #4 merged; 94/94 evals, 108/108 tests green).
> **Prerequisite reading:** `docs/use-cases/RM_COPILOT.md`, `docs/audits/RM_COPILOT_ARCHITECTURE_AUDIT.md`.

---

## 1. Why this phase exists

Phases 1–4 built a working, governed co-pilot that **no human can reach**. The four
workflows in `RM_WORKFLOWS` are invoked only from `tests/`. `src/app.py` still renders the
original six-agent demo pipeline; `src/main.py` runs the CrewAI scaffold. Neither touches
the RM stack.

That has three consequences:

1. **No pilot is possible** (master prompt §19 Phase 6 presumes a surface).
2. **Layer 5 cannot exist.** "Measure actual usefulness" requires an RM using the thing.
3. **The thesis is unproven where it matters.** Passing tests show the system is *correct*;
   only an RM can show it is *useful*.

Phase 5 closes exactly that gap and nothing more.

---

## 2. Goal

> Give a Relationship Manager a surface where they can select a client, see grounded
> context, receive an evidence-backed recommendation, produce a draft, and route it
> through the real approval gate — with every fact traceable and nothing sent.

**Success:** an RM completes that loop unaided and can say whether the output was useful.
**Not success:** a prettier demo.

---

## 3. Architectural constraint (non-negotiable)

The surface is a **view**. It holds no business logic, no thresholds, no rules, and no
CRM access of its own.

```
Streamlit surface
      ↓ RM_WORKFLOWS[...]           (Tier 2 — never bypassed)
      ↓ CAPABILITIES[...]           (Tier 1 — never called directly by the view)
      ↓ CRMAdapter                  (fixtures | Salesforce)
      ↓ validation.check_delivery   (Layer 4 — before anything is shown as deliverable)
      ↓ hitl.ApprovalStore          (DRAFTED → PENDING_REVIEW → APPROVED/REJECTED)
```

Specific prohibitions, each of which the audit found violated somewhere before:

- The view **must not** re-derive risk, ageing, priority or recommendations. It renders
  what the workflow returned. (This is how the triplication started.)
- The view **must not** call `CAPABILITIES` directly for anything a workflow already
  returns — that would fork the composition logic.
- The view **must not** mark anything delivered. Only the gate decides, and only after
  approval.
- The view **must not** invent a fallback when a workflow returns an error envelope; it
  renders the error, including authorization denials.

---

## 4. Scope

### In scope
| # | Item | Notes |
|---|---|---|
| S1 | **RM Co-pilot mode inside the existing Streamlit app** | New tab/mode in `src/app.py`, reusing the existing theme and shell |
| S2 | **Actor selection** | RM identity picker (dev stand-in for real auth — decision D2) |
| S3 | **Client picker** | via `search_client`, already authorization-filtered |
| S4 | **Client summary view** | `rm-client-summary`: risk flags, open items, known needs, **missing information shown prominently** |
| S5 | **Next-best-action panel** | `rm-next-best-action`: action, priority, reason, **evidence list**, suggested question, and `other_signals` (never hidden) |
| S6 | **Opportunity review** | `rm-opportunity-review`: stage assessment, ageing, conversion risk, missing actions |
| S7 | **Draft + approval loop** | `rm-followup-draft` → submit → reviewer role → approve/reject → gate decision. Rejection requires a justification |
| S8 | **Delivery gate feedback** | Show *why* something is blocked, verbatim from `check_delivery` violations |
| S9 | **Audit ribbon** | correlation_id, audit_ref, data source, authorization result — visible, not hidden in logs |
| S10 | **L5 feedback capture** | One control per output: useful / not useful / wrong, plus free text. Written to a local JSONL feedback log |
| S11 | **Headless smoke test** | Render-function tests that run without Streamlit installed (see §7) |

### Explicitly out of scope
Tier 3 writes and any send action · a second app or entrypoint · authentication (D2 remains a
dev picker) · LLM narration · the FastAPI bridge · MCP · OpenClaw/Hermes · durable approval
storage · live Salesforce · redesign of the existing demo pipeline.

---

## 5. Screen flow

```
[ Select RM ]  →  [ Search / pick client ]
                          │
                          ▼
        ┌──────────── Client workspace ─────────────┐
        │  Summary        risk flags · open items   │
        │  Next action    priority · reason ·       │
        │                 evidence · other signals  │
        │  Opportunities  stage · ageing · risk     │
        │  Missing info   what we do NOT know       │
        └───────────────────┬───────────────────────┘
                            ▼
                    [ Generate draft ]
                            ▼
        DRAFTED → [ Submit for review ] → PENDING_REVIEW
                            ▼
           [ Reviewer role ] → Approve / Reject(+justification)
                            ▼
              Gate decision: APPROVED_FOR_DELIVERY | BLOCKED(+violations)
```

Two behaviours worth calling out because they are the governance story made visible:

- A draft triggered by a **compliance signal** shows that it requires a **Compliance
  Officer** — and the RM's own approve button is refused, with the governance reference.
- An **approved-then-tampered** artefact still shows BLOCKED. Approval does not excuse a
  contract violation.

---

## 6. Deliverables

| # | Deliverable | Path |
|---|---|---|
| D-1 | RM surface renderers (pure functions returning view models) | `src/rm/views.py` |
| D-2 | Streamlit RM mode | `src/app.py` (additive; demo pipeline untouched) |
| D-3 | Session state: selected RM/client/opportunity, approval ids | `src/rm/session.py` |
| D-4 | L5 feedback capture | `src/rm/feedback.py` + `feedback/rm_feedback.jsonl` (gitignored) |
| D-5 | Headless view tests | `tests/test_rm_views.py` |
| D-6 | Docs update | `docs/use-cases/RM_COPILOT.md` |

**Design note:** the view logic lives in `src/rm/views.py` as **pure functions returning
view models**, with `app.py` doing only Streamlit calls. That is what makes D-5 possible
without Streamlit installed, and it keeps the surface honest — a view model can be asserted
against the workflow envelope that produced it.

---

## 7. Verification constraint (stated up front)

**Streamlit is not installed in this environment**, so `src/app.py` cannot be imported or
run here — the same limitation recorded in Phase 3. Therefore:

- All testable logic goes in `src/rm/views.py` (pure, stdlib, no Streamlit import).
- `tests/test_rm_views.py` covers it headlessly and runs in CI.
- `src/app.py` stays a thin rendering shell.
- **I will not claim the UI runs.** It will be reported as *implemented, not executed*,
  exactly as the Salesforce adapter was.

If you want the UI actually exercised, the options are: install Streamlit here, run it
yourself, or drive it with Playwright (Chromium is already available in this environment) —
worth deciding before the phase starts.

---

## 8. Acceptance criteria

1. An RM can complete the full loop against fixtures without touching code.
2. Every displayed fact traces to a workflow envelope; the view derives no business value.
3. A cross-RM client is **not** selectable and a direct attempt renders the denial.
4. A draft cannot reach `APPROVED_FOR_DELIVERY` without a recorded approval.
5. A compliance-triggered draft is refused to the RM role and names the required approver.
6. Blocked deliveries display the gate's actual violations.
7. `missing_information` and `other_signals` are visible, never silently dropped.
8. Layer 1 stays 94/94; existing 108 tests stay green; new view tests pass headlessly.
9. No new runtime dependency is added to the eval gate.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| **View re-derives business logic** (how the triplication began) | Pure view models + a test asserting rendered values equal envelope values |
| UI implies an action was sent | No send control exists; drafts always render the NOT SENT banner |
| RM picker mistaken for real auth | Labelled a dev stand-in; D2 unresolved and documented in-app |
| Feedback log accumulates client data | Store identifiers + verdict only, no draft bodies (consistent with §22) |
| Scope drift into a general agent console | Acceptance criteria are RM-loop-only; demo pipeline untouched |

---

## 10. Open decisions

| ID | Question | Default if unanswered |
|---|---|---|
| **D9** | Extend `src/app.py` with an RM mode, or build a separate RM app? | **Extend** — one entrypoint, reuses the shell, keeps the demo intact |
| **D10** | How is the UI verified? | Ship headless view tests; report the UI as *implemented, not executed* |
| **D11** | Does the reviewer role come from a picker, or is the RM always the reviewer? | **Picker** — otherwise compliance escalation cannot be demonstrated |
| **D1** *(carried)* | Real stage SLAs / conversion-risk bands | Provisional values stand until you supply the firm's |

> **D1 matters more now than in any previous phase.** Until Phase 5 the invented thresholds
> only affected test assertions. Once an RM sees a screen saying an opportunity is at HIGH
> conversion risk, they are being given advice based on numbers I made up. This should be
> settled before an RM uses the surface, not before it is built.

---

## 11. Suggested sequence

1. `src/rm/views.py` + `tests/test_rm_views.py` — pure, headless, CI-enforced.
2. `src/rm/session.py` + approval wiring.
3. `src/app.py` RM mode (thin shell).
4. `src/rm/feedback.py` (L5 hooks).
5. Docs.

Commits stay logical per §18: views → session → surface → feedback → docs.

---

## 12. What this phase does **not** prove

- Nothing about live Salesforce (still unverified; Phase 4 limitation stands).
- Nothing about durability — approvals still die with the process.
- Nothing about usefulness until an actual RM uses it. Phase 5 *enables* Layer 5
  measurement; it does not perform it.
