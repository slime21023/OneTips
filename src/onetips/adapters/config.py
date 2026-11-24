from __future__ import annotations

from pathlib import Path

import yaml

from onetips.adapters.yamlio import dump_yaml, load_yaml
from onetips.core.config import ProjectConfig, config_data, parse_config
from onetips.core.errors import ConfigError


def load_config(path: Path) -> ProjectConfig:
    try:
        return parse_config(load_yaml(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise ConfigError(path, f"{path}: missing config; run from the project root") from exc
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ConfigError(path, f"{path}: {exc}") from exc


def render_config(config: ProjectConfig) -> str:
    return dump_yaml(config_data(config))
