from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from onetips.adapters.config import load_config
from onetips.adapters.fs import is_plain_dir
from onetips.adapters.tips import read_tip_documents
from onetips.core.config import ProjectConfig
from onetips.core.diagnostic import Diagnostic
from onetips.core.rules.body import validate_body
from onetips.core.rules.metadata import count_ids, validate_tip_metadata
from onetips.core.tip import Tip


@dataclass(frozen=True)
class Project:
    root: Path
    config: ProjectConfig
    skill: Path
    tips: list[Tip]
    diagnostics: list[Diagnostic]
    ready: bool  # False when the project directories themselves are unusable.


def load_project(root: Path) -> Project:
    """Load `onetips.yaml` (ConfigError on failure) and validate every Tip."""
    config = load_config(root / "onetips.yaml")
    skills = root / "skills"
    skill = skills / config.name
    for directory in (skills, skill, skill / "references"):
        if not is_plain_dir(directory):
            diagnostic = Diagnostic(directory, 1, "E-READ", "expected a plain project directory")
            return Project(root, config, skill, [], [diagnostic], False)
    documents, diagnostics = read_tip_documents(skill)
    ids = count_ids(documents)
    tips: list[Tip] = []
    for document in documents:
        metadata, errors = validate_tip_metadata(document, config, ids)
        title, body = validate_body(document, config)
        diagnostics.extend(errors)
        diagnostics.extend(body)
        if metadata is not None and not any(issue.code.startswith("E-") for issue in body):
            tips.append(Tip(document.path, metadata, title, document))
    return Project(root, config, skill, tips, diagnostics, True)
