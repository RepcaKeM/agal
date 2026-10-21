from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any
import yaml

from agal.config import (
    GLOBAL_SKILL_DIRS,
    LOCAL_STATE_FILE,
    SUPPORTED_RUNTIMES,
    get_installed_file,
    load_config,
    skill_rel_dirs_for_runtimes,
)
from agal.sources import get_all_skills


def load_local_state(target_dir: Path) -> dict[str, Any]:
    state_file = target_dir / LOCAL_STATE_FILE
    if state_file.is_file():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"skills": {}, "mcp": {}, "hooks": {}, "preset": None}


def save_local_state(target_dir: Path, state: dict[str, Any]) -> None:
    state_file = target_dir / LOCAL_STATE_FILE
    # If state is completely empty, clean up the file
    if (
        not state.get("skills")
        and not state.get("mcp")
        and not state.get("hooks")
        and not state.get("preset")
        and not state.get("subagents")
        and not state.get("runtimes")
        and not state.get("preset_owned")
        and not state.get("subagent_owned")
    ):
        if state_file.exists():
            state_file.unlink()
        return

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_global_state() -> dict[str, Any]:
    file_path = get_installed_file()
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"skills": {}, "mcp": {}, "hooks": {}}


def save_global_state(state: dict[str, Any]) -> None:
    file_path = get_installed_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(state, f, default_flow_style=False, sort_keys=False)


def _copy_package(src: Path, dest: Path) -> None:
    """Copies a file or directory package, replacing anything already at dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest, ignore_errors=True)
        else:
            dest.unlink(missing_ok=True)

    if src.is_dir():
        shutil.copytree(src, dest, symlinks=False)
    else:
        shutil.copy2(src, dest)


def _remove_installed_path(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _prune_empty_parents(start: Path, stop: Path) -> None:
    current = start
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def get_active_runtimes(target_dir: Path) -> list[str]:
    """Runtimes selected for a project, or every supported runtime when unset."""
    selected = load_local_state(target_dir).get("runtimes") or list(SUPPORTED_RUNTIMES)
    return [name for name in selected if name in SUPPORTED_RUNTIMES]


def install_skill(
    skill_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
    copy: bool = True,
    cfg: dict[str, Any] | None = None,
    all_skills: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Installs a skill by name from available sources into local project or global scope.
    Preserves all internal files (scripts, yamls, references).

    Project and user skill directories are always real copies. ``copy`` is
    accepted so existing callers keep working.
    """
    del copy
    if cfg is None:
        cfg = load_config()

    if all_skills is None:
        all_skills = get_all_skills(cfg)
    if skill_name not in all_skills:
        raise ValueError(f"Skill '{skill_name}' not found in any registered source.")

    skill_info = all_skills[skill_name]
    src_path = Path(skill_info["path"])
    if not src_path.exists():
        raise FileNotFoundError(f"Source directory for skill '{skill_name}' does not exist: {src_path}")

    target = (target_dir or Path.cwd()).resolve()
    installed_paths: list[str] = []

    if scope == "local":
        rel_dirs = skill_rel_dirs_for_runtimes(load_local_state(target).get("runtimes") or None)
        for rel_dir in rel_dirs:
            dest = target / rel_dir / skill_name
            _copy_package(src_path, dest)
            installed_paths.append(str(dest.relative_to(target)))

        # Update local state
        state = load_local_state(target)
        state.setdefault("skills", {})[skill_name] = {
            "source": skill_info.get("source", "unknown"),
            "mode": "copy",
            "paths": installed_paths,
            "description": skill_info.get("description", ""),
        }
        save_local_state(target, state)

    elif scope == "global":
        for g_dir in GLOBAL_SKILL_DIRS:
            dest = g_dir / skill_name
            _copy_package(src_path, dest)
            installed_paths.append(str(dest))

        # Update global state
        state = load_global_state()
        state.setdefault("skills", {})[skill_name] = {
            "source": skill_info.get("source", "unknown"),
            "mode": "copy",
            "paths": installed_paths,
            "description": skill_info.get("description", ""),
        }
        save_global_state(state)
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")

    return {
        "skill": skill_name,
        "source": skill_info.get("source", "unknown"),
        "scope": scope,
        "mode": "copy",
        "paths": installed_paths,
    }


def uninstall_skill(
    skill_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
) -> bool:
    """Removes a skill from local project or global scope."""
    target = (target_dir or Path.cwd()).resolve()

    if scope == "local":
        state = load_local_state(target)
        if skill_name not in state.get("skills", {}):
            found = False
            for rel_dir in skill_rel_dirs_for_runtimes(None):
                p = target / rel_dir / skill_name
                if p.is_symlink() or p.exists():
                    _remove_installed_path(p)
                    _prune_empty_parents(p.parent, target)
                    found = True
            return found

        entry = state["skills"][skill_name]
        parents: list[Path] = []
        for rel_path in entry.get("paths", []):
            p = target / rel_path
            if p.is_symlink() or p.exists():
                _remove_installed_path(p)
            parents.append(p.parent)

        del state["skills"][skill_name]
        save_local_state(target, state)
        for parent in parents:
            _prune_empty_parents(parent, target)
        return True

    elif scope == "global":
        state = load_global_state()
        if skill_name not in state.get("skills", {}):
            found = False
            for g_dir in GLOBAL_SKILL_DIRS:
                p = g_dir / skill_name
                if p.is_symlink() or p.exists():
                    _remove_installed_path(p)
                    found = True
            return found

        entry = state["skills"][skill_name]
        for full_path in entry.get("paths", []):
            p = Path(full_path)
            if p.is_symlink() or p.exists():
                _remove_installed_path(p)

        del state["skills"][skill_name]
        save_global_state(state)
        return True
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")


def sync_installed_skills(target_dir: Path, cfg: dict[str, Any] | None = None) -> None:
    """Move installed skills into the directories selected for this project."""
    target = target_dir.resolve()
    state = load_local_state(target)
    previous = {
        name: list(entry.get("paths", []))
        for name, entry in state.get("skills", {}).items()
    }
    wanted = set(skill_rel_dirs_for_runtimes(state.get("runtimes") or None))
    all_skills = get_all_skills(cfg) if previous else None
    for name, old_paths in previous.items():
        try:
            install_skill(name, target_dir=target, scope="local", cfg=cfg, all_skills=all_skills)
        except (ValueError, FileNotFoundError) as exc:
            print(f"⚠️  Skill '{name}' not relocated: {exc}")
            continue
        for rel in old_paths:
            parent = Path(rel).parent.as_posix()
            if parent not in wanted:
                path = target / rel
                _remove_installed_path(path)
                _prune_empty_parents(path.parent, target)


def list_installed_skills(
    target_dir: Path | None = None,
    scope: str = "local",
) -> dict[str, Any]:
    target = (target_dir or Path.cwd()).resolve()
    if scope == "local":
        return load_local_state(target).get("skills", {})
    elif scope == "global":
        return load_global_state().get("skills", {})
    return {}
