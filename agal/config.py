from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml

DEFAULT_HOME = Path.home() / ".agal"
DEFAULT_PRESETS_DIR = DEFAULT_HOME / "presets"
DEFAULT_SOURCES_DIR = DEFAULT_HOME / "sources"
DEFAULT_SUBAGENTS_DIR = DEFAULT_HOME / "subagents"
DEFAULT_CACHE_DIR = DEFAULT_HOME / "cache"
DEFAULT_SOURCES_FILE = DEFAULT_HOME / "sources.yaml"
DEFAULT_INSTALLED_FILE = DEFAULT_HOME / "installed.yaml"

LOCAL_STATE_FILE = ".agal_state.json"
AGAL_CONTEXT_MARKER = ".agal_context"
AGAL_MANAGED_MARKER = ".agal_managed"

CONTEXT_FILENAMES = ["AGENTS.md", "CLAUDE.md"]

LOCAL_SKILL_DIRS = [
    ".agents/skills",
    ".claude/skills",
]

SUPPORTED_RUNTIMES = ("claude", "cursor", "opencode", "agy")

RUNTIME_CONTEXT_FILES = {
    "claude": ("CLAUDE.md", "AGENTS.md"),
    "cursor": ("AGENTS.md",),
    "opencode": ("AGENTS.md",),
    "agy": ("AGENTS.md",),
}


def skill_rel_dirs_for_runtimes(runtimes: list[str] | None) -> list[str]:
    """Skill directories for an explicit runtime list.

    None keeps every local skill directory.
    """
    if not runtimes:
        return list(LOCAL_SKILL_DIRS)
    wanted: set[str] = set()
    if "claude" in runtimes:
        wanted.add(".claude/skills")
    if any(name in runtimes for name in ("cursor", "opencode", "agy")):
        wanted.add(".agents/skills")
    selected = [d for d in LOCAL_SKILL_DIRS if d in wanted]
    return selected or list(LOCAL_SKILL_DIRS)


def context_filenames_for_runtimes(runtimes: list[str] | None) -> list[str]:
    """Guideline filenames for an explicit runtime list.

    None keeps every context filename.
    """
    if not runtimes:
        return list(CONTEXT_FILENAMES)
    files: list[str] = []
    for runtime in runtimes:
        for name in RUNTIME_CONTEXT_FILES.get(runtime, ()):
            if name not in files:
                files.append(name)
    return files or list(CONTEXT_FILENAMES)


def mcp_files_for_runtimes(runtimes: list[str] | None) -> list[str]:
    """Project MCP config paths for an explicit runtime list.

    None keeps Claude Code's .mcp.json only, so a project that never
    picked a runtime does not grow a .cursor directory.
    """
    if not runtimes:
        return [".mcp.json"]
    files: list[str] = []
    if "claude" in runtimes:
        files.append(".mcp.json")
    if "cursor" in runtimes:
        files.append(".cursor/mcp.json")
    if "opencode" in runtimes:
        files.append("opencode.json")
    if "agy" in runtimes:
        files.append(".agents/mcp_config.json")
    return files

GLOBAL_SKILL_DIRS = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "sources_dir": str(DEFAULT_SOURCES_DIR),
    "presets_dir": str(DEFAULT_PRESETS_DIR),
    "subagents_dir": str(DEFAULT_SUBAGENTS_DIR),
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
        "subagents_dir": str(get_subagents_dir()),
        "core_preset": None,
        "context_file": None,
        "adhd_rules": False,
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


def get_subagents_dir(cfg: dict[str, Any] | None = None) -> Path:
    if cfg and cfg.get("subagents_dir"):
        return Path(cfg["subagents_dir"]).expanduser()
    return get_agal_home() / "subagents"


def get_cache_dir() -> Path:
    return get_agal_home() / "cache"


def get_sources_file() -> Path:
    return get_agal_home() / "sources.yaml"


def get_installed_file() -> Path:
    return get_agal_home() / "installed.yaml"
