# Skill: exec-brief
# Compresses any document into a 1-page exec brief

## Description
Takes a long document, report, proposal, or collection of notes and compresses it to a
C-level readable 1-page brief. Lead with Bottom Line Up Front. End with a specific ask.
Triggers on: "tóm tắt cho sếp", "exec summary", "brief this doc", "summarize for leadership", `/brief-doc` command.

## Executor: @drafter

## Rules
- Hard limit: 1 page / ~400 words
- Bottom Line Up Front MUST stand alone — readable without rest of brief
- Max 5 key points — no exceptions
- "Recommended Action" must be a specific ask, not "consider" or "explore"
- Strip all jargon — translate for exec audience
- Save to `brain/reports/exec-brief-[topic]-[date].md`
- 🔴 If used for external/client distribution: flag for human review

## Steps

1. Receive the document or content. Ask for:
   - Audience seniority (Partner / CEO / Board)
   - Purpose (for decision | for awareness | for approval)
   - The single most important question to answer

2. Identify the "So What" FIRST before writing anything.
   Ask internally: "If they read one sentence from this, what should it be?"

3. Build the brief:

```markdown
## Executive Brief: [Topic]
**For:** [Audience] | **Purpose:** [Decision/Awareness/Approval]
**Source:** [Document name] | **Date:** [prepared]

---

### Bottom Line Up Front
[2-3 sentences. The single most important thing they need to know.
If they read only this, they should understand the core situation.]

### Why This Is On Your Desk Now
[1 short paragraph: background, timing, urgency]

### Key Points
1. [Most important finding]
2. [Second finding]
3. [Third finding]
_(Max 5 points)_

### Implications
[What this means for the business / decision at hand — specific to OneIBC context]

### Recommended Action
**→ [Specific ask or next step]**
[1-2 sentences: what you need from them, or what should happen by when]

---
_Source document: [reference]_
_Brief by EA | Reviewed by: _________ | Date: _________
🔴 Draft only — review before distributing._
```

4. Self-check before delivering:
   - Is the whole brief ≤ 400 words? If not → cut the lowest-value point
   - Does Bottom Line Up Front stand alone? If not → rewrite it
   - Is Recommended Action specific (not vague)? If not → sharpen it

5. Save to `brain/reports/exec-brief-[topic]-[date].md`
6. Return to @orchestrator. Flag if external use needed.
