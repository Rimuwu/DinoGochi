---
name: json_inspector
description: Skill for precise inspection and synchronization of JSON files (localizations, configs) without loading entire files.
---

# Localization & Config Inspector Skill

This skill provides the agent with tool-like capabilities to query and manipulate large JSON files (such as localizations `ru.json`, `en.json`, or item configs) without reading the entire raw contents, saving thousands of context tokens.

## How to Use

Instead of using `view_file` on large JSON files, run the python helper script:
`python .agents/skills/json_inspector/scripts/json_inspector.py --action <action> [arguments]`

### Supported Actions

1. **get_keys**: Get all key names at a specific JSON dot-notation path.
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action get_keys --file <relative_file_path> [--dot-path <dot_notation_path>]
   ```
   *Example*:
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action get_keys --file bot/localization/ru.json --dot-path ru.buttons_name
   ```

2. **get_value**: Retrieve the value at a specific dot-notation path.
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action get_value --file <relative_file_path> --dot-path <dot_notation_path>
   ```
   *Example*:
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action get_value --file bot/localization/en.json --dot-path en.no_text_key
   ```

3. **sync**: Sync/merge keys of a specific section from a base file to target files (preserves existing translations, only copies missing keys).
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action sync --base-file <base_file> --target-files <comma_separated_targets> --section-path <dot_notation_path>
   ```
   *Example*:
   ```bash
   python .agents/skills/json_inspector/scripts/json_inspector.py --action sync --base-file bot/localization/ru.json --target-files bot/localization/en.json,bot/localization/es.json,bot/localization/id.json --section-path items_names
   ```

## Smart Path Resolving
For localization files, the CLI script automatically detects and handles the root language key (e.g. `ru`, `en`, `es`, `id`). You can omit the root key in `--dot-path` or `--section-path`, and the script will automatically resolve it!
