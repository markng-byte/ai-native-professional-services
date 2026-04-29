# Skill: brief-builder
# Produces the weekly Monday priorities brief

## Description
Aggregates tasks, deadlines, renewals, and meetings into a clean 1-page Monday brief.
Identifies Top 3 Priorities and surfaces decisions needed this week.
Triggers on: "brief tuần này", "weekly brief", "Monday brief", "priorities this week", `/brief` command.

## Executor: @orchestrator (coordinates @drafter for output)

## Rules
- Top 3 Priorities must be justified — not just listed
- Decisions section: anything that needs a human call this week
- Carryovers: items from last week's brief that aren't done
- Max length: 1 page / ~500 words
- Save to `brain/reports/weekly-brief-[YYYY-MM-DD].md`
- Also check `brain/context.md` for open items from prior sessions

## Steps

1. Read `brain/context.md` for open items.
   Read last week's brief from `brain/reports/` if it exists.

2. Ask for this week's inputs (accept any format — paste tasks, say "skip" to use brain only):
   "Paste your task list + any deadlines/renewals for this week. Or say 'skip' to use what I already have."

3. Process tasks — classify each:
   - 🔴 Overdue: past due, not done
   - 🟡 At Risk: due within 7 days, no recent update
   - 🟢 On Track: progressing normally
   - ✅ Done: completed this period

4. Process renewals — bucket by urgency:
   - 🚨 Urgent: ≤ 7 days
   - ⚠️ Upcoming: 8-30 days

5. Identify Top 3 Priorities:
   Criteria: urgency × impact × blocker status
   Each priority needs: what | why urgent | owner | due date

6. Build the brief:

```markdown
# Weekly Priorities Brief
**Week of:** [Mon date] – [Fri date]
**Prepared:** [today]

## 🎯 Top 3 Priorities This Week
1. **[Priority]** — [why it's #1] — Owner: [x] — Due: [x]
2. **[Priority]** — [rationale] — Owner: [x] — Due: [x]
3. **[Priority]** — [rationale] — Owner: [x] — Due: [x]

## 🔴 Overdue / Blocked
| Task | Owner | Was Due | Blocker |
|------|-------|---------|---------|

## 🟡 At Risk (due this week)
| Task | Owner | Due | Last Update |
|------|-------|-----|-------------|

## 🟢 On Track
| Task | Owner | Due |
|------|-------|-----|

## 🔔 Renewals & Deadlines
| Item | Expiry | Urgency | Action |
|------|--------|---------|--------|

## 🔴 Decisions Needed This Week
| Decision | Context | Who Decides | By When |
|----------|---------|-------------|---------|

## 📌 Carryovers from Last Week
- [items not completed]

---
_Next brief: [next Monday date]_
```

7. Save to `brain/reports/weekly-brief-[date].md`
8. Trigger `drive-sync` skill automatically after saving.
9. Return brief to user. Ask: "Anything to add or adjust?"
