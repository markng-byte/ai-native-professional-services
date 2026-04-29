---
description: Convert raw team updates into a formatted status report ready to send up
---

When user types `/report`, activate @drafter and execute `report-draft` skill.

1. Ask: "Paste raw updates (text, bullets, Slack — any format)"
   Ask: "Who is this going to? (manager / partner / cross-team)"
   Ask: "What period does this cover? (default: this week)"
2. Execute `report-draft` skill with inputs
// turbo
3. Save to `brain/reports/status-[YYYY-MM-DD].md`
// turbo
4. Update `brain/context.md`
5. Present draft. Flag: "🔴 Draft only — review before sending"
6. Ask: "Want me to also prepare an exec brief version for senior leadership?"
