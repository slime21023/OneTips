from __future__ import annotations

from pathlib import Path

from onetips.adapters.config import load_config, render_config
from onetips.adapters.fs import create_files, is_link, is_occupied, is_plain_dir
from onetips.adapters.yamlio import dump_yaml
from onetips.core.config import ProjectConfig, default_config, path_slug
from onetips.core.errors import UsageError
from onetips.core.index import render_index_header
from onetips.core.section import SECTION_KEYS


def _front_matter(data: dict[str, object]) -> str:
    return f"---\n{dump_yaml(data)}---\n"


def _readme(name: str) -> str:
    return f"""# {name}

An OneTips project: one Markdown file per Tip.

Browse the [Topic index](skills/{name}/INDEX.md).

## Install the skill

From another repository, replace the example source path with this project's directory:

```sh
bunx skills add "/path/to/{name}" --skill {name}
```
"""


def _skill(config: ProjectConfig) -> str:
    header = _front_matter(
        {
            "name": config.name,
            "description": f"Practical tips for {config.name}. Use when writing or reviewing code in this project's domain.",
            "metadata": {"onetips-format": "1"},
        }
    )
    return (
        header
        + f"""
# {config.domain} Tips

Each Tip in `references/` solves one problem. See [INDEX.md](INDEX.md) for topics, applicable versions, and snippet verification status.

## Workflow

1. **Check the target project first.** Identify relevant versions from its manifests, lockfiles, or toolchain files. Read its instructions, configuration, and existing code for conventions.
2. **Find relevant Tips.** Search [INDEX.md](INDEX.md) by tag, category, or keyword. Skip Tips that exclude the target versions; say when applicability cannot be confirmed.
3. **Read only what you need.** Follow the relative link and use the `Sections` mapping in the index to find the relevant headings. Read the Tip's metadata and only the sections needed.
4. **Treat snippets as references.** Use the fence status (`unverified`, `compiled`, or `tested`) to inform how you verify the example. An omitted status means `unverified`. Adapt examples to the target project.
5. **Use the checklist for review.** Determine which items are met, not met, or not applicable.
6. **Do not override project decisions.** Follow the target project if it conflicts with a Tip, and state the conflict.
7. **Detect incomplete installs.** If an indexed file is missing, report the incomplete installation and recommend reinstalling. Do not reconstruct missing content.

## Optional: structured queries with OneTips

If `onetips` is available, replace `<skill-dir>` with the directory containing this `SKILL.md` and `<id>` with an indexed Tip ID.

- Find matching Tips: `onetips find --skill-dir "<skill-dir>" --tag <tag> --json`
- Read one section: `onetips show --skill-dir "<skill-dir>" "<id>" --section checklist`
- Get snippets: `onetips show --skill-dir "<skill-dir>" "<id>" --section approach --code --lang "<lang>" --status tested`

Without the CLI, use the index and Markdown directly. Do not install tools just to read this skill.
"""
    )


def _tip_draft(tip_id: str, category: str, config: ProjectConfig) -> str:
    header = _front_matter(
        {
            "id": tip_id,
            "summary": "",
            "category": category,
            "tags": [],
            "related": [],
            "applies_to": {},
        }
    )
    headings = "\n\n".join(f"## {config.sections[key]}" for key in SECTION_KEYS)
    return f"{header}\n#\n\n{headings}\n\n- [ ]\n"


def init_project(root: Path, name: str) -> Path:
    config = default_config(name)
    root = root.resolve()
    skill = root / "skills" / config.name
    references = skill / "references"
    directories = (root, skill.parent, skill, references)
    contents = {
        root / "README.md": _readme(config.name),
        root / "onetips.yaml": render_config(config),
        skill / "SKILL.md": _skill(config),
        skill / "INDEX.md": render_index_header(config, 0),
    }
    conflicts = [path for path in directories if is_link(path) or (path.exists() and not path.is_dir())]
    if not root.exists():
        conflicts[:0] = [path for path in root.parents if path.exists() and not path.is_dir()]
    conflicts.extend(path for path in contents if not any(parent in conflicts for parent in path.parents) and is_occupied(path))
    if conflicts:
        raise UsageError("conflicting paths: " + ", ".join(str(path) for path in conflicts))

    create_files(contents, mkdir=references)
    return root


def new_tip(root: Path, tip_id: str, category: str) -> Path:
    tip_id = path_slug(tip_id, "id")
    root = root.resolve()
    config = load_config(root / "onetips.yaml")
    if category not in config.categories:
        raise UsageError(f"unknown category {category!r} in {root / 'onetips.yaml'}")
    skills = root / "skills"
    skill = skills / config.name
    references = skill / "references"
    for directory in (skills, skill, references):
        if not is_plain_dir(directory):
            raise UsageError(f"expected a project directory at {directory}")

    path = references / f"{tip_id}.md"
    if is_occupied(path):
        raise UsageError(f"conflicting path: {path}")
    create_files({path: _tip_draft(tip_id, category, config)})
    return path
