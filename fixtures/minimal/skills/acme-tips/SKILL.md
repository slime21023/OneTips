---
name: acme-tips
description: Acme SDK Tips for writing and reviewing code. Check the project's SDK version and follow project conventions over any Tip.
metadata:
  onetips-format: '1'
---

# Acme SDK Tips

Each Tip in `references/` solves one problem. See [INDEX.md](INDEX.md) for topics, applicable versions, and snippet verification status.

## Workflow

1. **Check the target project first.** Identify the Acme SDK version from its manifests or lockfiles. Read its instructions, configuration, and existing code for conventions.
2. **Find relevant Tips.** Search [INDEX.md](INDEX.md) by tag, category, or keyword. Skip Tips that exclude the target versions; say when applicability cannot be confirmed.
3. **Read only what you need.** Follow the relative link and use the `Sections` mapping in the index to find the relevant headings. Read the Tip's metadata and only the sections needed.
4. **Treat snippets as references.** Use the fence status (`unverified`, `compiled`, or `tested`) to inform how you verify the example. An omitted status means `unverified`. Adapt examples to the target project.
5. **Use the checklist for review.** Determine which items are met, not met, or not applicable.
6. **Do not override project decisions.** Follow the target project if it conflicts with a Tip, and state the conflict.
7. **Detect incomplete installs.** If an indexed file is missing, report the incomplete installation and recommend reinstalling. Do not reconstruct missing content.

## Optional: structured queries with OneTips

If `onetips` is available, replace `<skill-dir>` with the directory containing this `SKILL.md`.

- Find matching Tips: `onetips find --skill-dir "<skill-dir>" --tag retry --json`
- Read one section: `onetips show --skill-dir "<skill-dir>" retry-with-backoff --section checklist`
- Get snippets: `onetips show --skill-dir "<skill-dir>" retry-with-backoff --section approach --code --lang python --status tested`

Without the CLI, use the index and Markdown directly. Do not install tools just to read this skill.
