# Skill: research-browser
# Real-time research using Antigravity's browser agent

## Description
Uses the Antigravity browser to research a topic in real time, cross-checks sources,
and produces a structured brief with TL;DR, key points, "so what", and knowledge gaps.
Triggers on: "research", "tìm hiểu", "brief về", "what is", "compare", `/research` command.

## Executor: @researcher (browser-enabled)

## Rules
- ALWAYS use browser — never rely on training knowledge alone for regulatory, market, or current facts
- Minimum 2 sources for any factual claim
- Flag any source older than 6 months with ⚠️
- Every brief MUST have a "So What?" section — never leave the user to draw their own conclusion
- NEVER fabricate a citation — if unsure, say "could not verify"
- Output depth options: quick (3 min read) | standard (8 min) | deep (15 min) — default: standard
- Save output to `brain/research/[topic]-[YYYY-MM-DD].md`

## Steps

1. Restate the research question as 1 clear sentence.
   "You want me to research: [topic], focused on [angle]."

// turbo
2. Open browser. Search for: `[topic] [current year] site:reliable OR authoritative source`
   For regulatory/compliance topics: also search `[topic] [jurisdiction] regulation 2025 OR 2026`

// turbo
3. Open top 2-3 results. Skim for: key facts, dates, numbers, expert positions.
   Note source name + date for each.

4. Cross-check: do sources agree? If conflict → note it explicitly in the brief.

5. Build the structured brief:

```markdown
## Research Brief: [Topic]
**Depth:** [level] | **Prepared:** [date] | **Sources checked:** [n]

### TL;DR
- [bullet 1 — most important fact]
- [bullet 2]
- [bullet 3]
_(These 3 bullets stand alone — readable without the rest of the brief)_

### Background
[2-3 paragraphs: what it is, why it matters, current context]

### Key Points
**[Sub-topic 1]**
[paragraph with inline citations]

**[Sub-topic 2]**
[paragraph]

### So What? (Implications for OneIBC / Mark)
[What this means in practice — specific, not generic]

### Gaps & Caveats
- [What this brief does NOT cover]
- [What needs deeper research or verification]
- ⚠️ [Any source older than 6 months — flag here]

### Sources
| Source | Date | URL |
|--------|------|-----|
```

6. Save to `brain/research/[topic]-[date].md`

7. Update `brain/context.md`

8. Return brief to @orchestrator. Offer: "Want me to go deeper on any section?"
