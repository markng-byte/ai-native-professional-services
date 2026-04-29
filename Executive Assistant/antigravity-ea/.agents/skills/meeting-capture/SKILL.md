# Skill: meeting-capture
# Converts raw meeting notes or transcript into structured summary

## Description
Takes any raw input (paste, voice-to-text, bullet notes) and produces a structured meeting summary
with decisions, action items (owner + deadline), parking lot, and open questions.
Triggers on: "tóm tắt meeting", "meeting notes", "action items", `/meeting` command.

## Executor: @drafter

## Rules
- Accept ANY input format — transcript, bullets, scribbles, voice-to-text
- MUST extract: decisions, action items with owners, parking lot
- Action items with no owner → flag as `❓ Owner unassigned`
- Action items with no deadline → flag as `❓ No deadline set`
- Sort action items by deadline (nearest first)
- Output MUST fit on 1 page
- Save output to `brain/meetings/meeting-[YYYY-MM-DD]-[topic].md`
- 🔴 Draft only — user reviews before distributing

## Steps

1. Ask for input (if not already provided):
   "Paste meeting notes, transcript, or voice-to-text. Include topic and date if you have them."

2. Parse the input — extract:
   - Meeting topic, date, attendees (if present)
   - Decisions: scan for "we decided", "agreed", "going with", "confirmed"
   - Action items: scan for "will do", "to do", "action on", "[name] will", "by [date]"
   - Parking lot: "let's discuss offline", "table this", "follow up later"
   - Open questions: questions raised but not answered

3. Build the structured output:

```markdown
## Meeting Summary: [Topic]
**Date:** [date] | **Attendees:** [list if known]

### 📌 Decisions Made
| # | Decision | By |
|---|----------|-----|

### ✅ Action Items
| # | Action | Owner | Deadline | Priority |
|---|--------|-------|----------|----------|

### 💬 Key Discussion Points
- [synthesized, not verbatim — 3-5 bullets]

### 🅿️ Parking Lot
- [items deferred]

### ❓ Open Questions
- [unanswered questions]

---
🔴 Draft only — review before distributing.
```

4. Save to `brain/meetings/meeting-[date]-[topic].md`

5. Update `brain/context.md` with:
   ```
   ## [date] — Meeting: [topic]
   - [n] action items captured
   - File: brain/meetings/meeting-[date]-[topic].md
   ```

6. Ask: "Want me to draft follow-up messages for any of the action item owners?"
