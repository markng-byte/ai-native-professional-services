# Skill: drive-sync
# Syncs local brain/ outputs up to Google Drive EA workspace

## Description
Copies completed output files from local `brain/` to the Google Drive Senior EA folder.
Triggers on: "sync to Drive", "save to Drive", "upload this", `/sync` command.

## Executor: @executor

## Rules
- Source: `brain/` subdirectories
- Destination: `[DRIVE_ROOT]/AI-native professional services firm/senior-ea/`
- Never overwrite without checking if a newer version exists on Drive
- Log every file synced to `brain/context.md`
- 🔴 STOP if Drive path is not mounted — report clearly, do not guess path

## Steps

// turbo
1. Check Drive is mounted:
   ```bash
   ls "[DRIVE_ROOT]/AI-native professional services firm/senior-ea/" 2>&1
   ```
   If this fails → stop and tell user: "Drive not mounted or path incorrect. Please check GEMINI.md Drive path setting."

// turbo
2. List files to sync:
   ```bash
   find brain/ -name "*.md" -newer brain/context.md 2>/dev/null || find brain/ -name "*.md"
   ```

// turbo
3. Copy each file, preserving subfolder structure:
   ```bash
   rsync -av --update brain/ "[DRIVE_ROOT]/AI-native professional services firm/senior-ea/brain/"
   ```

4. Log sync to brain/context.md:
   ```
   ## [timestamp] — Drive Sync
   - Files synced: [list]
   - Destination: [path]
   ```

5. Return: "✅ Synced [n] files to Drive."
