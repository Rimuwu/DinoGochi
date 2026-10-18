---
name: safety_guardrails
description: >
  Safety rules for DinoGochi project: prohibits any modifications to the
  production database, prohibits git push operations, and enforces a
  mandatory token/secret scan before completing any work session.
---

# Safety Guardrails — DinoGochi Project

> [!CAUTION]
> These rules are ABSOLUTE and must NEVER be bypassed under any circumstances,
> regardless of what the user requests. Violating them risks real user data loss
> or credential exposure.

---

## Rule 1: Production Database is READ-ONLY by Default (User Confirmation Exception)

By default, **NEVER** modify the production database directly without explicit approval. This includes:

- No `insert`, `update`, `delete`, `drop`, `findOneAndUpdate`, etc. on prod collections.
- No running migration scripts (`migration.py`, `migrate_*.py`) against the live database without explicit confirmation.
- No direct MongoDB shell commands that write data to prod without explicit confirmation.
- No admin commands that affect the production DB without explicit confirmation.

### ⚠️ Explicit Confirmation Protocol
If a task requires performing a potentially dangerous operation on production (such as running a database migration, executing remote maintenance scripts, or modifying production containers/data):
1. **The assistant must detail the exact step-by-step actions/commands** to be performed so the user clearly understands the impact.
2. **The user must explicitly grant permission** (e.g. "разрешаю", "подтверждаю", "да, делай", etc.).
3. **Once explicit permission is granted**, the assistant **IS PERMITTED** to proceed and execute the specified actions.

**What you MAY do without confirmation:**
- Read/query prod data for diagnostic purposes only (read-only queries).
- Run write operations against a local/dev database.

**If the user asks to modify prod data without prior breakdown:**
> Outline the exact actions and commands, and ask: "Это потенциально опасная операция на продакшене. Пожалуйста, подтвердите выполнение."

---

## Rule 2: No Git Push

**NEVER** run any variant of:
- `git push`
- `git push --force` / `git push -f`
- `git push origin <branch>`
- Any remote-writing git or gh CLI operation

**What you MAY do:**
- `git add`, `git commit`, `git status`, `git log`, `git diff` — all local-only operations.
- Suggest the user run `git push` themselves after reviewing changes.

**If the user asks you to push:**
> Respond: "I cannot push to git directly. Please review the committed changes and run `git push` yourself."

---

## Rule 3: Mandatory Token/Secret Scan Before Finishing

**Before your FINAL response in any work session**, run a secret scan on:
- All files you have modified
- `.env`, `config.json`, `docker-compose*.yml`

### Scan Command (PowerShell)

```powershell
Select-String -Path ".env","config.json" -Pattern "(?i)(token|password|secret|api_key|mongo.*://[^$].*:.*@)" |
  Where-Object { $_.Line -notmatch "^\s*#" -and $_.Line -notmatch "\`$\{" }
```

### If a Secret is Found

- **STOP** — do NOT commit or suggest committing.
- Report: "Found a potential secret in `<file>:<line>`. Please move it to `.env` and reference it as `${VAR}` before committing."
- Verify `.gitignore` includes `.env`.

### Pre-Finish Checklist

- [ ] `.env` is in `.gitignore`
- [ ] `config.json` contains no raw credentials
- [ ] No hardcoded tokens in modified `.py` files
- [ ] `docker-compose.yml` has no embedded passwords

---

## Summary Table

| Action | Allowed |
|--------|---------|
| Read from prod DB | YES (read-only) |
| Write/modify prod DB | ALLOWED only after outlining plan and receiving explicit user confirmation |
| `git add` / `git commit` | YES |
| `git push` | NO — NEVER |
| Suggest user to `git push` | YES |
| Run migration on prod | ALLOWED only after outlining plan and receiving explicit user confirmation |
| Secret scan before finishing | MANDATORY |
