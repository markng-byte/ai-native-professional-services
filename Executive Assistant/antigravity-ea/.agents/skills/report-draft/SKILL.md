# Skill: report-draft
# Converts raw team updates into a polished status report

## Description
Takes messy raw updates (text, bullets, Slack pastes) and formats them into a professional
status report with exec summary, wins, issues with asks, and next period plan.
Triggers on: "viết status report", "weekly update", "format updates", `/report` command.

## Executor: @drafter

## Rules
- Executive Summary must stand alone — readable without rest of report
- Wins section is MANDATORY — never skip, it's important for visibility and morale
- Every issue must have an action/ask — not just a problem statement
- "Requests from Leadership" must capture anything needing a decision or resource from above
- Status colors: 🟢 on track | 🟡 at risk | 🔴 needs attention
- Save to `brain/reports/status-[team/project]-[date].md`
- 🔴 Draft only — sender reviews before sending

## Steps

1. Ask for:
   - Raw updates (any format — text, bullets, Slack copy-paste)
   - Report period (default: this week)
   - Recipient (direct manager / partner / cross-team)

2. Parse updates — classify each chunk:
   - Win / milestone reached
   - Progress update on a project
   - Risk or blocker
   - Plan for next period
   - Request / ask for leadership

3. Write Executive Summary LAST (after processing everything).
   It must cover: overall status + key win + key risk + key ask. 4 sentences max.

4. Build the report:

```markdown
# [Team/Project] Status Report
**Period:** [date range]
**Prepared by:** [name] — EA draft
**For:** [recipient]

---

## Executive Summary
[4 sentences: overall status | key win | key risk | key ask.
Readable alone. Written last.]

## 🟢 Wins This Period
- [Achievement 1 — be specific, not generic]
- [Achievement 2]

## 📋 Project / Area Progress
**[Project A]**
- Status: 🟢 On Track / 🟡 At Risk / 🔴 Delayed
- Done: [what was completed]
- Next: [what's planned next period]

**[Project B]**
[same structure]

## 🔴 Issues & Risks
| Issue | Impact | Owner | Ask / Action |
|-------|--------|-------|--------------|

## 📅 Next Period Plan
| Deliverable | Owner | Due |
|-------------|-------|-----|

## 🙋 Requests from Leadership
- [Decision / resource / unblock needed — be specific]

---
🔴 Draft only — please review before sending.
```

5. Self-check:
   - Does Exec Summary stand alone? If not → rewrite
   - Does every issue have an ask? If not → add one
   - Is Wins section present? If empty → ask user for at least 1

6. Save to `brain/reports/status-[date].md`
7. Update `brain/context.md`
8. Return to @orchestrator.
