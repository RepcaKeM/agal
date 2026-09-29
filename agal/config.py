from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml

DEFAULT_HOME = Path.home() / ".agal"
DEFAULT_PRESETS_DIR = DEFAULT_HOME / "presets"
DEFAULT_SOURCES_DIR = DEFAULT_HOME / "sources"
DEFAULT_CACHE_DIR = DEFAULT_HOME / "cache"
DEFAULT_SOURCES_FILE = DEFAULT_HOME / "sources.yaml"
DEFAULT_INSTALLED_FILE = DEFAULT_HOME / "installed.yaml"

LOCAL_STATE_FILE = ".agal_state.json"
AGAL_CONTEXT_MARKER = ".agal_context"
AGAL_MANAGED_MARKER = ".agal_managed"

CONTEXT_FILENAMES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "KIMI.md"]

LOCAL_SKILL_DIRS = [
    ".agents/skills",
    ".claude/skills",
]

GLOBAL_SKILL_DIRS = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "sources_dir": str(DEFAULT_SOURCES_DIR),
    "presets_dir": str(DEFAULT_PRESETS_DIR),
    "core_preset": None,
    "context_file": None,
    "clis": {
        "claude": "claude",
        "gemini": "gemini",
    },
    "update_check_interval": 86400,  # 24 hours in seconds
    "cleanup_after_launch": True,
}


def get_agal_home() -> Path:
    env = os.environ.get("AGAL_HOME")
    return Path(env).expanduser() if env else DEFAULT_HOME


def get_config_path() -> Path:
    env = os.environ.get("AGAL_CONFIG")
    if env:
        return Path(env).expanduser()
    return get_agal_home() / "config.yaml"


def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "sources_dir": str(get_sources_dir()),
        "presets_dir": str(get_presets_dir()),
        "core_preset": None,
        "context_file": None,
        "clis": {
            "claude": "claude",
            "gemini": "gemini",
        },
        "update_check_interval": 86400,
        "cleanup_after_launch": True,
    }
    path = get_config_path()
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f)
                if isinstance(user_cfg, dict):
                    cfg.update(user_cfg)
        except Exception:
            pass

    # Ensure directories exist
    home = get_agal_home()
    home.mkdir(parents=True, exist_ok=True)
    get_cache_dir().mkdir(parents=True, exist_ok=True)

    sdir = get_sources_dir(cfg)
    if sdir.is_symlink():
        sdir.resolve().mkdir(parents=True, exist_ok=True)
    else:
        sdir.mkdir(parents=True, exist_ok=True)

    pdir = get_presets_dir(cfg)
    if pdir.is_symlink():
        pdir.resolve().mkdir(parents=True, exist_ok=True)
    else:
        pdir.mkdir(parents=True, exist_ok=True)

    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)


def get_sources_dir(cfg: dict[str, Any] | None = None) -> Path:
    if cfg and cfg.get("sources_dir"):
        return Path(cfg["sources_dir"]).expanduser()
    return get_agal_home() / "sources"


def get_presets_dir(cfg: dict[str, Any] | None = None) -> Path:
    if cfg and cfg.get("presets_dir"):
        return Path(cfg["presets_dir"]).expanduser()
    return get_agal_home() / "presets"


def get_cache_dir() -> Path:
    return get_agal_home() / "cache"


def get_sources_file() -> Path:
    return get_agal_home() / "sources.yaml"


def get_installed_file() -> Path:
    return get_agal_home() / "installed.yaml"
