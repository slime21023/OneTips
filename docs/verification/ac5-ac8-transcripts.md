# AC-5 / AC-8 Real Agent Verification Transcripts

- **Date**: 2026-11-25
- **Fixture / Skill**: `fixtures/minimal/skills/acme-tips` (`computedHash: 13296f4c85669969dfc87866fe844d3663e431ca8e9a1794073077ae3b8fdfc8`)
- **Agent**: Antigravity `research` subagent (read-only sandbox; `read_file` only — no terminal, no `onetips` CLI, no Python, no `uv`, no `mq`)
- **Result**: 3 / 3 scenarios **PASS**

---

## Scenario 1 — AC-5: No-CLI Tag Lookup & Localized Checklist

### Input Context
- Target repo contains only `.claude/skills/acme-tips/` (copied from `fixtures/minimal/skills/acme-tips/`).
- Prompt: Locate the Tip with unique tag `retry` via `INDEX.md`, use the `Sections` mapping to find its `checklist` section, and report exact files read, Tip ID, and checklist items without using any CLI/Python/uv tools.

### Expected Behavior
- Agent reads `SKILL.md` → `INDEX.md` → `references/retry-with-backoff.md` using only file-reading tools.
- Resolves `checklist` → `檢查清單`, ignores the decoy `## 檢查清單` inside the fenced `text` block, and reports Tip ID `retry-with-backoff` and `- [ ] Limit both attempts and delay.`.

### Actual De-identified Transcript Summary
- **Tools used**: `read_file` only (no CLI, Python, `uv`, or `mq`).
- **Files read (in order)**:
  1. `.claude/skills/acme-tips/SKILL.md`
  2. `.claude/skills/acme-tips/INDEX.md`
  3. `.claude/skills/acme-tips/references/retry-with-backoff.md`
- **Output**:
  - Tip ID: `retry-with-backoff` (matched via unique tag `retry` in `INDEX.md`).
  - `Sections` mapping: `checklist` → `檢查清單`.
  - Heading: `## 檢查清單` (line 42; explicitly ignored the decoy `## 檢查清單` inside the `text` code fence on lines 30–32).
  - Exact checklist item: `- [ ] Limit both attempts and delay.`
- **Verdict**: **PASS**

---

## Scenario 2 — AC-8a: Target Version Mismatch (`acme-sdk 1.5.0`)

### Input Context
- Target repo contains `.claude/skills/acme-tips/` and `package.json`:
  ```json
  {
    "name": "demo-app",
    "dependencies": {
      "acme-sdk": "1.5.0"
    }
  }
  ```
- Prompt: Implement retry-with-backoff logic for `acme-sdk` requests consulting `.claude/skills/acme-tips/`.

### Expected Behavior
- Agent checks `package.json` first, sees `acme-sdk 1.5.0` is outside `acme-sdk >=2.0 <3.0` in `INDEX.md`, explains the mismatch, and does **not** apply the v2.x Tip example.

### Actual De-identified Transcript Summary
- **Files read (in order)**:
  1. `package.json`
  2. `.claude/skills/acme-tips/SKILL.md`
  3. `.claude/skills/acme-tips/INDEX.md`
  *(Intentionally did **not** open `references/retry-with-backoff.md` or `references/idempotency-keys.md`.)*
- **Output**:
  - Decision: **Does not apply — will not apply the `retry-with-backoff` v2.x example.**
  - Rationale: `package.json` specifies `acme-sdk: 1.5.0`, whereas `INDEX.md` declares `Applies to: acme-sdk >=2.0 <3.0`. Per `SKILL.md` Workflow Step 2 ("Skip Tips that exclude the target versions"), the Tip was skipped directly from `INDEX.md` and the user was informed of the version mismatch with v1.5.0-safe alternatives.
- **Verdict**: **PASS**

---

## Scenario 3 — AC-8b: `AGENTS.md` Rule Conflicts with Applicable Tip

### Input Context
- Target repo contains `.claude/skills/acme-tips/`, `package.json` (`"acme-sdk": "2.3.0"`), and `AGENTS.md`:
  ```markdown
  # Project Rules

  - Do NOT reuse idempotency keys across retries; our gateway requires a fresh UUID per HTTP attempt.
  ```
- Prompt: Add idempotency key handling when retrying `acme-sdk` requests consulting `.claude/skills/acme-tips/`.

### Expected Behavior
- Agent verifies `acme-sdk 2.3.0` is in range (`>=2.0 <3.0`), reads `AGENTS.md` and `references/idempotency-keys.md` (without reading unrelated Tips), explicitly states the conflict, and follows `AGENTS.md` over the Tip.

### Actual De-identified Transcript Summary
- **Files read (in order)**:
  1. `package.json`
  2. `AGENTS.md`
  3. `.claude/skills/acme-tips/SKILL.md`
  4. `.claude/skills/acme-tips/INDEX.md`
  5. `.claude/skills/acme-tips/references/idempotency-keys.md`
  *(Did **not** read `references/retry-with-backoff.md`.)*
- **Output**:
  - Identified direct conflict: `idempotency-keys.md` recommends reusing the same key per operation, whereas `AGENTS.md` forbids reuse and requires a fresh UUID per HTTP attempt.
  - Decision: Followed **`AGENTS.md`** per `SKILL.md` Workflow Step 6 ("Do not override project decisions. Follow the target project if it conflicts with a Tip, and state the conflict.").
  - Checklist evaluation: marked `Reuse the same key for the same operation.` as **Not applicable (overridden by project rule in `AGENTS.md`)**.
- **Verdict**: **PASS**
