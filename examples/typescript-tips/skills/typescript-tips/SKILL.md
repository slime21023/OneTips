---
name: typescript-tips
description: Practical TypeScript tips covering module layout, thin templates, and semantic code style. Check the target project's TypeScript version and conventions first.
metadata:
  onetips-format: '1'
---

# TypeScript Tips

Each Tip in `references/` solves one problem. See [INDEX.md](INDEX.md) for topics, applicable versions, and snippet verification status.

## Workflow

1. **Check the target project first.** Identify TypeScript and runtime versions from `package.json`, `tsconfig.json`, and lockfiles. Read existing code and linter configuration for conventions.
2. **Find relevant Tips.** Search [INDEX.md](INDEX.md) by tag, category, or keyword. Skip Tips that exclude the target versions; state when applicability cannot be confirmed.
3. **Read only what you need.** Follow the relative link and use the `Sections` mapping in the index to locate headings. Read metadata and only the required sections.
4. **Treat snippets as references.** Use the fence status (`unverified`, `compiled`, or `tested`) to guide verification. Adapt thin templates to match the target project's naming and tooling.
5. **Use the checklist for review.** Report which checklist items are met, not met, or not applicable.
6. **Do not override project decisions.** Follow the target project if it conflicts with a Tip, and note the conflict.
7. **Detect incomplete installs.** If an indexed file is missing, report the incomplete installation and recommend reinstalling.

## Optional: structured queries with OneTips

If `onetips` is available, replace `<skill-dir>` with the directory containing this `SKILL.md` and `<id>` with an indexed Tip ID.

- Find matching Tips: `onetips find --skill-dir "<skill-dir>" --category templates --json`
- Read one section: `onetips show --skill-dir "<skill-dir>" typed-result-pattern --section checklist`
- Get snippets: `onetips show --skill-dir "<skill-dir>" typed-result-pattern --section approach --code --lang ts --status tested`

Without the CLI, use the index and Markdown directly. Do not install tools just to read this skill.
