---
description: Convert meeting notes or transcript into structured summary with action items
---

When user types `/meeting`, activate @drafter and execute `meeting-capture` skill.

1. Ask: "Paste meeting notes, transcript, or voice-to-text. Topic and date if you have them."
2. Execute `meeting-capture` skill on the input
// turbo
3. Save output to `brain/meetings/meeting-[YYYY-MM-DD]-[topic].md`
// turbo
4. Update `brain/context.md`
5. Present Artifact: Decisions | Action Items | Parking Lot | Open Questions
6. Ask: "Want me to draft follow-up messages for any action item owners?"
