---
description: Research any topic using browser — returns structured brief with TL;DR and So What
---

When user types `/research <topic>`, activate @researcher and execute `research-browser` skill.

1. Restate: "You want me to research: [topic]."
   Ask: "What depth? quick / standard / deep (default: standard)"
   Ask: "Any specific angle? (or press enter to skip)"
// turbo
2. Open browser. Search: `[topic] [current year]`
   For compliance/regulatory topics: add jurisdiction to query
// turbo
3. Open top 2-3 results, extract key facts and note source + date
4. Execute `research-browser` skill to build structured brief
// turbo
5. Save to `brain/research/[topic]-[YYYY-MM-DD].md`
// turbo
6. Update `brain/context.md`
7. Present brief to user. Offer: "Want me to go deeper on any section?"
