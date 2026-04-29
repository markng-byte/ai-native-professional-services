---
description: Weekly Monday priorities brief — aggregates tasks, renewals, and open decisions
---

When user types `/brief`, activate @orchestrator and execute `brief-builder` skill.

// turbo-all
1. Read `brain/context.md` for open items from last session
2. Read most recent file in `brain/reports/weekly-brief-*.md` for carryovers
3. Ask: "Paste this week's tasks + renewals, or say 'skip' to use brain only"
4. Execute `brief-builder` skill with all collected input
5. Save output to `brain/reports/weekly-brief-[YYYY-MM-DD].md`
6. Trigger `drive-sync` skill
7. Present Artifact to user
