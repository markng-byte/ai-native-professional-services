# RM Co-pilot — Master Prompt Audit (Phase 0)

> Per master-prompt §4: this is a **critical** audit. It does not conclude "the prompt is valid."
> Audited against: repository state @ `5624803`, the eval baseline (94/94 green),
> `docs/FIRMOS_DEPLOYMENT_PLAN.md`, and the L1–L6 + governance specifications.

Legend — **IMPLEMENTED** · **NOT IMPLEMENTED** · **CONTRADICTED** · **MISSING** · **OVER-COMPLEX** · **DEFER** · **DECISION**

---

## 1. Assumptions already implemented ✅

| § | Assumption | Evidence |
|---|---|---|
| 5 | Deterministic skills exist and are a protected baseline | 9 skills, 94/94 green, CI-enforced |
| 5 | The nine named skills exist | All 9 verified in `SKILLS` |
| 13 L1 | CI regression eval with fixed fixtures | `run_evals.py` + `eval-gate.yml` |
| 13 | Regression eval ≠ runtime validation | Already the explicit design in the deployment plan |
| 12 | Deterministic-source principle is established | Documented; skills are the factual source |
| 14 | UI duplicates skill logic | **Confirmed — and worse than stated (see §3.1)** |
| 21 | Per-actor scoping is anticipated | `TOOL_REGISTRY.md` per-agent permissions; `MEMORY_SCHEMA.md` read/write ACLs |
| 22 | Auditability conventions exist | `GOVERNANCE.md` §5.1 defines fields, retention, immutability |
| 9/10 | RM is a governed approver role | `GOVERNANCE.md` §2 rows 4, 5, 7 name "Relationship Manager" |

---

## 2. Assumptions NOT implemented (correctly identified gaps) ⬜

| § | Assumption | Repo reality |
|---|---|---|
| 7.1 | Salesforce is transactional truth | **No Salesforce code.** One docstring mention. `TOOL_REGISTRY` specifies it on paper only |
| 8 | Business capability tools | None exist |
| 9 | Tier 1/2/3 tool maturity model | No tool tiering exists |
| 10 | `rm-*` workflows | None exist |
| 11 | RM workflow | None exists |
| 13 L2–L5 | Contract / workflow / runtime / human eval layers | Only Layer 1 exists |
| 4/21 | Authorization boundaries | **Zero** authz code (`authoriz`, `oauth` → 0 hits) |
| 22 | correlation_id, actor identity, approval state | Not plumbed; only `audit_log_ref` UUIDs returned by some skills |
| 19 P1 | FastAPI bridge | Does not exist |
| 24 | `tests/` | **No `tests/` directory at all** |

---

## 3. Assumptions CONTRADICTED by the repository ⚠️

### 3.1 §14 understates the duplication — it is **triplication**
The prompt says *"inspect whether Command Center / engine.py duplicates skill logic."* It does —
but so does `src/tools/`. Intent classification and jurisdiction comparison each exist in **three**
independent implementations, each with its **own copy of the jurisdiction fixture**.
**Impact:** the remediation in §14 ("UI → verified skill") is necessary but **insufficient**; the
CrewAI tool layer needs the same treatment or the agent runtime will contradict the gate.

### 3.2 §3 references a plan that does not exist
The *"current RM Co-pilot Deployment Plan"* is not in the repository. `docs/FIRMOS_DEPLOYMENT_PLAN.md`
is an **OpenClaw/Hermes** plan with zero RM/opportunity/Salesforce-capability content.
**Impact:** the prompt's citations to "the existing deployment plan" are accurate about the four
cross-cutting decisions, but wrong about it being RM-scoped. Treat it as a *general* plan to
re-sequence, not an RM plan to continue.

### 3.3 §6 "Skill ≠ infrastructure adapter" is violated by the protected baseline
§6 mandates separating skills from data access. But every existing skill **embeds its own data
store** (e.g. `client_lookup.py` contains a hardcoded `CLIENTS` dict; `ubo_chain_traverse.py`
contains `GRAPH`). So the protected baseline (§5) **structurally violates** the target architecture (§6).
**Impact:** these two instructions collide. Resolution: extract a data-access seam *behind* the
existing `run(payload)->dict` contract so eval behavior is byte-identical while the fixture moves
out. **This must not change eval semantics** (§5). Flagged as the main refactor risk.

### 3.4 §7.3 "memory must not become a shadow CRM" vs. `MEMORY_SCHEMA.md` Episodic memory
Episodic memory is defined as *per-client session history … retained indefinitely while client
active* — which is precisely a shadow client-truth store.
**Impact:** latent conflict (nothing implemented yet). Needs a decision before any persistence.

### 3.5 §8 "no raw CRUD" vs. `TOOL_REGISTRY.md` row 2.0
The registry grants agents direct READ/WRITE on the Salesforce MCP server. §8 forbids exactly that
as the agent's public interface.
**Impact:** the registry must be re-read as an *adapter-level authorization policy*, not an
agent-level grant. Documentation update required.

---

## 4. Requirements MISSING from the prompt (must be specified before build) ❓

These are genuine specification gaps — not repository gaps.

| # | Missing | Why it blocks | Needs |
|---|---|---|---|
| M1 | **Opportunity domain model** | §10 requires `current_stage`, `aging`, `conversion_risk` — but no stage taxonomy, no aging thresholds, no risk formula is defined anywhere (repo: `opportunity` = 0 hits) | **DECISION** |
| M2 | **RM identity source** | §21 says "design authorization around the actor," but nothing defines who the RM is, where identity comes from, or how RM→client visibility is scoped | **DECISION** |
| M3 | **`client-lookup` vs `search_client` / `get_rm_client_context` overlap** | An existing gated skill and a proposed new tool cover the same ground. §26 explicitly warns against duplicated logic — the prompt does not say which wins | **DECISION** |
| M4 | **Determinism boundary for recommendations** | §12 mandates deterministic sources for facts. But `rm-next-best-action` / `conversion_risk` are *judgment*. Are they deterministic heuristics (gate-able at Layer 1) or LLM reasoning (only Layer 3/4-testable)? | **DECISION** |
| M5 | **Whether v1 requires an LLM at all** | The thesis can be proven with deterministic heuristics + templates. Prompt never states if an LLM is in v1 scope, nor which provider/model | **DECISION** |
| M6 | **Layer 5 success criteria** | §13 L5 = "measure actual usefulness" with no metric, sample size, or acceptance threshold | DEFER (pilot-time) |
| M7 | **"Conflicting CRM information" definition** | §13 L3 scenario 8 requires a conflict-detection concept that is undefined | **DECISION** (can default) |
| M8 | **RM session data retention** | §7.3 memory + §22 auditability, but no retention rule for RM conversational context (Working memory says purge at session close — may conflict with audit needs) | **DECISION** |

---

## 5. Requirements that are unnecessarily complex for v1 🔶

| § | Requirement | Assessment | Recommendation |
|---|---|---|---|
| 19 P1 | FastAPI bridge, schemas, discovery, auth, correlation IDs, structured errors, bridge tests | **The RM thesis needs no network transport.** Workflows can be proven in-process + through the existing UI. §28 says build the smallest system that proves the thesis | **DEFER** bridge until a real external runtime integrates. Keep *schemas* and *correlation IDs* (they are needed regardless) |
| 13 | Five eval layers | L2 and L4 share one engine (`matcher.py`) and differ only in *when* they run. Standing up five distinct layers at once is heavy | Build L1 (exists) + L3 (workflow) first; L2/L4 as one shared contract module; L5 at pilot |
| 15 | Claude Code / Cursor / OpenClaw / Hermes runtime strategy | No runtime is being integrated in v1 | **DEFER** entirely; it constrains nothing now |
| 9 | Tier 3 execute tools | Explicitly not enabled in v1 | **DEFER** — define the *contract* only, implement nothing |
| 10 | Four RM workflows simultaneously | `rm-client-summary` + `rm-next-best-action` prove the thesis; the other two add drafting/review surface | Sequence: summary → NBA → opportunity-review → followup-draft |

---

## 6. Requirements that should be explicitly deferred ⏭

Agreeing with §20, plus additions from this audit: FastAPI bridge (§5 above), OpenClaw/Hermes
integration, MCP transport, Tier 3 writes, Episodic-memory persistence, Neo4j, ingestion,
Salesforce sandbox (Phase 5+), Layer 5 measurement.

---

## 7. Ambiguities requiring human decision 🚦

Consolidated — these are the questions that must be answered before Phase 2+.

| ID | Question | Default I would take if unanswered |
|---|---|---|
| **D1** | Opportunity stage taxonomy, aging thresholds, conversion-risk formula (M1) | Invent a documented, conventional B2B-services default (stages: Prospect→Qualified→Proposal→Negotiation→Won/Lost; aging = days-in-stage vs per-stage SLA) and mark it provisional |
| **D2** | RM identity/authorization source (M2) | Fixture-based `rm_id` on every request; RM sees only clients where they are the assigned RM |
| **D3** | Does `get_rm_client_context` **wrap** the existing `client-lookup` skill, or replace it? (M3) | **Wrap.** Preserves the gated baseline; capability tool composes skills |
| **D4** | Are RM recommendations deterministic heuristics or LLM-generated? (M4) | **Deterministic heuristics producing structured evidence**, with LLM narration optional and non-authoritative — keeps them Layer-1 gate-able |
| **D5** | Is an LLM in v1 scope at all? (M5) | **No LLM required for v1 core**; drafts from templates + structured evidence. LLM optional behind a flag |
| **D6** | Episodic memory: defer, or re-scope as audit log? (§3.4 / H.3) | **Defer**; Working memory only in v1 |
| **D7** | Base `feature/rm-copilot` on `5624803` (main + plan doc) or clean `origin/main`? | **`5624803`** — keeps the referenced plan on-branch, discards nothing |
| **D8** | Does the §14 refactor extend to `src/tools/` (the third copy)? (§3.1) | **Yes** — otherwise the agent runtime contradicts the gate |

> Per §23 stop conditions, **D1, D2, D4 and D6** materially affect domain modelling, authorization,
> evaluation semantics and future platform design. I will **not** proceed past the plan without
> explicit answers or explicit approval of the defaults above.

---

## 8. Proposed changes to the master prompt itself

Per §4 ("if you believe the prompt should be changed, document it before implementing"):

1. **§3 — correct the reference.** There is no RM Co-pilot Deployment Plan; name
   `docs/FIRMOS_DEPLOYMENT_PLAN.md` and state it is to be *re-sequenced*, not continued.
2. **§14 — widen the scope.** Say "engine.py **and `src/tools/`** duplicate skill logic"; the
   duplication is threefold.
3. **§19 — demote Phase 1.** Make the bridge conditional/late; it is not on the RM critical path.
   Promote the domain model + capability tools to Phase 1.
4. **§6 vs §5 — acknowledge the collision.** State explicitly that extracting data access from
   skills must preserve eval behavior exactly (contract-preserving refactor).
5. **§7.3 — reconcile with `MEMORY_SCHEMA.md`.** Either defer Episodic memory or redefine it as an
   append-only audit log.
6. **§12 — add a carve-out** distinguishing *deterministic facts* (compliance, UBO, sanctions) from
   *judgment outputs* (next-best-action), and state how the latter are evaluated.
7. **§10 — resolve overlap** with the existing `client-lookup` skill (D3).
8. **§13 — permit merging L2 and L4** into one shared contract module with two invocation points.

---

## 9. Overall assessment

The prompt is **directionally sound and unusually well-governed** — its separation of concerns,
tool tiering, deterministic-source principle and eval layering are correct, and it aligns with
governance the repo already documents (the RM is already a named approver).

Its weaknesses are: **(a)** it assumes an RM-scoped plan that does not exist; **(b)** it
under-detects the duplication it asks to fix; **(c)** it front-loads transport infrastructure that
the thesis does not require; and **(d)** it leaves the entire opportunity domain model, the
determinism boundary for recommendations, and RM identity **unspecified** — which are precisely the
things needed first.

**Net:** proceed, but re-sequence around domain model + capability tools, defer the bridge, and
obtain decisions D1–D8.
