# RM Co-pilot — Pilot Runbook

> For the Relationship Manager taking part in the pilot, and the person running it.
> **The co-pilot drafts and advises. You decide. Nothing is ever sent to a client.**

---

# Part 1 — For the RM

## What this is

A tool that reads what the firm knows about your clients and tells you **what to do next
and why**. It does not act. It cannot email anyone. Every draft it produces waits for you.

## What to do

1. Open the app, go to the **🤝 RM Co-pilot** tab.
2. Pick your name under **Acting as**.
3. Search a client. *You will only see clients assigned to you* — that is deliberate.
4. Read the **Next best action** panel.
5. Press **👍 Useful**, **👎 Not useful**, or **⚠️ Wrong** on anything it shows you.

**Step 5 is the pilot.** Everything else already works; what nobody knows yet is whether the
advice is any good. That is the question you are answering.

## What the three buttons mean

They are not the same, and the difference matters:

| Button | Use it when |
|---|---|
| 👍 **Useful** | You'd have wanted to know this. It's what you would have done, or it caught something. |
| 👎 **Not useful** | True, but unhelpful — obvious, badly timed, or not your priority today. |
| ⚠️ **Wrong** | **It told you something untrue.** The document isn't actually expired; the deal isn't actually stalled; the client isn't yours. |

**Please use "Wrong" whenever it applies, even once.** A single "Wrong" is treated as a defect
and investigated. "Not useful" ten times is treated as a tuning problem. Conflating them costs
us the signal.

If you can, add a one-line note saying *why* — "doc was renewed last week" is worth more than
any number. **Do not paste client details into the note**; the note is stored.

## Things that are meant to happen

- **"Not authorised"** on another RM's client — correct, not a bug.
- **A draft that will not send.** There is no send button anywhere. It never had one.
- **"Delivery blocked"** until someone approves — that is the approval gate working.
- **Being refused your own approval** on a compliance-triggered draft. Those require a
  Compliance Officer. Also correct.
- **"What we do not know"** — the system is telling you where it is blind. Trust that list.

## Things that are NOT meant to happen — report these

- A client appearing that is not yours.
- A recommendation that contradicts what you can see in the CRM.
- A draft that names the wrong entity or jurisdiction.
- Anything that looks like it was sent.

## What it cannot do yet

- **It cannot write to the CRM.** It proposes; it never updates a record.
- **It does not know anything you have not logged.** If a call is not in the system, it does
  not exist to the co-pilot.
- **The risk thresholds are not yet the firm's.** See the note below — this matters.

---

# Part 2 — For whoever runs the pilot

## Before the first RM touches it

Three things, in order of how badly they bite:

**1. Set the real thresholds.** `config/thresholds.json` ships `"ratified": false` with an
unassigned owner, because the stage SLAs, the conversion-risk multiple and the high-value line
are development placeholders. The UI says so on screen, but an RM is still being told "HIGH
conversion risk" on the strength of numbers nobody at the firm chose.

Edit the file — no code change, the app reads it at runtime:

| Field | The question it answers |
|---|---|
| `stage_sla_days.PROSPECT` | After how many days is an unqualified enquiry going stale? |
| `stage_sla_days.QUALIFIED` | How long should qualification take before you chase? |
| `stage_sla_days.PROPOSAL` | How long do clients normally take to respond to a proposal? |
| `stage_sla_days.NEGOTIATION` | Past how many days is a negotiation drifting? |
| `high_risk_multiple` | How many times over SLA before it is *probably lost*, not just late? (2.0 = double) |
| `stale_activity_days` | After how long with no contact should an RM be nudged? |
| `urgent_renewal_days` | How far ahead does a renewal become urgent? |
| `urgent_renewal_high_priority_days` | Inside which window does it escalate? (must be ≤ the line above) |
| `high_value_amount` | Above what value does an opportunity get special attention? |

Then set `policy_owner` to the accountable role and `last_reviewed` to today, and flip
`ratified: true`. The loader **refuses to start** if you set `ratified: true` without both —
ratification is a governance claim, so it has to carry accountability. Once ratified, the UI
stops calling the numbers provisional and starts citing them as firm policy with an owner.

**2. Approvals are durable by default — just confirm where.**
The app writes to `approvals/approvals.db` unless told otherwise, because approvals are audit
records under `governance/GOVERNANCE.md` §5.1 (seven-year retention) and that should not depend
on remembering an environment variable. To put the file somewhere backed up:
```bash
export FIRMOS_APPROVAL_DB=/var/lib/firmos/approvals.db
```
`FIRMOS_APPROVAL_DB=memory` opts out deliberately for a throwaway demo; the app then warns on
screen that approvals will be lost. **Back this file up** — it is the audit trail, and its event
log is insert-only by design.

**3. Decide the data source.** The pilot runs on **synthetic fixtures** by default — safe, and
enough to judge whether the advice is useful. Live Salesforce (`FIRMOS_CRM_SOURCE=salesforce`)
is implemented but **has never been run against a real org**; it needs credentials and
confirmation of your custom object and stage-picklist names first.

## Running it

```bash
pip install -r requirements.txt
export FIRMOS_APPROVAL_DB=approvals/approvals.db
streamlit run src/app.py
```

## Reading the results

```bash
python rm_feedback_report.py            # text report
python rm_feedback_report.py --json     # machine-readable
```

The report breaks verdicts down **by signal code**, and each signal code is one rule in
`src/rm/heuristics.py` — so a poor result names the exact rule to revisit rather than leaving
you with "the AI isn't great".

It separates two very different findings:

- **Correctness concerns** — anything marked ⚠️ Wrong. Raised even on a single report, because
  it means the co-pilot stated something untrue. Investigate the rule.
- **Tuning candidates** — useful-rate at or below 50% **with at least 5 responses**. A rule
  that is accurate but unhelpful.

Fewer than 5 responses overall and the report labels its own figures as anecdote. That is
intentional: three thumbs-down is not evidence.

The script exits `2` when any correctness concern exists, so it can be wired into a scheduled
check.

## What success looks like

Not a percentage. The pilot has worked if you can answer:

1. Which rules do RMs consistently find useful?
2. Which rules are **wrong**, and why?
3. Are the thresholds right for this firm, or did the placeholders distort the advice?

Then retune `config/thresholds.json` and `src/rm/heuristics.py`, and run it again. The eval
suite (`python run_evals.py` and `python -m unittest discover -s tests`) protects you while you
do: 94 skill evals and 200+ tests will fail loudly if a change breaks a governance guarantee.

## Known limitations to disclose to participants

| Limitation | Consequence for the pilot |
|---|---|
| Thresholds unratified | Risk bands may not reflect firm reality |
| Fixtures, not live CRM | Clients are synthetic; judge the *reasoning*, not the data |
| Salesforce adapter unverified | Do not point at production |
| Actor picker is not authentication | Do not run outside a trusted environment |
| No CRM writes (Tier 3 deferred) | Nothing the co-pilot suggests is auto-applied |
