---
name: localization_sync
description: Sync and translate localizations when modifying Russian keys. Automatically runs trs_openrouter.py.
---

# DinoGochi Localization Synchronization Skill

Use this skill when you need to add, remove, or modify user-facing text, strings, notifications, patterns, or templates in the project localizations.

## Steps to Modify Localizations

1. **Modify `ru.json` Only**:
   - Add, edit, or remove translation keys directly in the Russian localization file: [ru.json](file:///c:/Папки/коды/Telegram%20DinoGochi/DinoGochi/bot/localization/ru.json).
   - Ensure all keys and placeholders (`{name}`, `{count}`, etc.) are correct.

2. **Run the Automatic Translation Script**:
   - Execute the `trs_openrouter.py` translation script to automatically translate the new/modified keys into English (`en.json`), Spanish (`es.json`), and Indonesian (`id.json`):
     ```powershell
     python tools/translate/trs_openrouter.py
     ```
   - *Note*: Ensure your environment variables are configured with a valid `OPENROUTER_API_KEY` in `tools/translate/.env`.

3. **Verify the Sync**:
   - Check the logs output by `trs_openrouter.py` to confirm that all targets (`en`, `es`, `id`) were updated and matching keys were synchronized.
