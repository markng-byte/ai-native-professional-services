---
description: Sync all local brain/ outputs to Google Drive EA workspace
---

When user types `/sync`, activate @executor and execute `drive-sync` skill.

// turbo
1. Check Drive is mounted: `ls "[DRIVE_ROOT]/AI-native professional services firm/senior-ea/"`
   If fails → stop and report: "Drive not mounted. Check GEMINI.md Drive path."
// turbo
2. List new/modified files in `brain/` since last sync
// turbo
3. Run rsync: `rsync -av --update brain/ "[DRIVE_ROOT]/AI-native professional services firm/senior-ea/brain/"`
4. Log to `brain/context.md`: files synced, timestamp
5. Report: "✅ Synced [n] files to Drive. [list filenames]"
