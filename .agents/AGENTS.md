# Project Rules & Guidelines

## Localization Rule
- **NEVER** write language-dependent conditional structures in Python code (e.g., `if lang == 'ru': ... elif lang == 'id': ...`).
- All user-facing text, strings, notifications, formatting patterns, and templates must be retrieved from the localization JSON files (under `bot/localization/`) using the translation helper function `t()`.
- Ensure all localization keys are present across all supported language JSON files (`ru.json`, `en.json`, `es.json`, `id.json`).
