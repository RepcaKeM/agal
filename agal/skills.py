from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any
import yaml

from agal.config import (
    GLOBAL_SKILL_DIRS,
    LOCAL_SKILL_DIRS,
    LOCAL_STATE_FILE,
    get_installed_file,
    load_config,
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
    if not state.get("skills") and not state.get("mcp") and not state.get("hooks") and not state.get("preset"):
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


def _link_or_copy_directory(src: Path, dest: Path, copy: bool = False) -> None:
    """Safely symlinks or recursively copies an entire directory package."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest, ignore_errors=True)
        else:
            dest.unlink(missing_ok=True)

    if copy:
        if src.is_dir():
            shutil.copytree(src, dest, symlinks=True)
        else:
            shutil.copy2(src, dest)
    else:
        dest.symlink_to(src.resolve(), target_is_directory=src.is_dir())


def install_skill(
    skill_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
    copy: bool = False,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Installs a skill by name from available sources into local project or global scope.
    Preserves all internal files (scripts, yamls, references).
    """
    if cfg is None:
        cfg = load_config()

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
        for rel_dir in LOCAL_SKILL_DIRS:
            dest = target / rel_dir / skill_name
            _link_or_copy_directory(src_path, dest, copy=copy)
            installed_paths.append(str(dest.relative_to(target)))

        # Update local state
        state = load_local_state(target)
        state.setdefault("skills", {})[skill_name] = {
            "source": skill_info.get("source", "unknown"),
            "mode": "copy" if copy else "symlink",
            "paths": installed_paths,
            "description": skill_info.get("description", ""),
        }
        save_local_state(target, state)

    elif scope == "global":
        for g_dir in GLOBAL_SKILL_DIRS:
            dest = g_dir / skill_name
            _link_or_copy_directory(src_path, dest, copy=copy)
            installed_paths.append(str(dest))

        # Update global state
        state = load_global_state()
        state.setdefault("skills", {})[skill_name] = {
            "source": skill_info.get("source", "unknown"),
            "mode": "copy" if copy else "symlink",
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
        "mode": "copy" if copy else "symlink",
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
            # Check if skill directory exists anyway in standard local locations
            found = False
            for rel_dir in LOCAL_SKILL_DIRS:
                p = target / rel_dir / skill_name
                if p.is_symlink() or p.exists():
                    if p.is_dir() and not p.is_symlink():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
                    found = True
            return found

        entry = state["skills"][skill_name]
        for rel_path in entry.get("paths", []):
            p = target / rel_path
            if p.is_symlink() or p.exists():
                if p.is_dir() and not p.is_symlink():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)

        del state["skills"][skill_name]
        save_local_state(target, state)
        return True

    elif scope == "global":
        state = load_global_state()
        if skill_name not in state.get("skills", {}):
            found = False
            for g_dir in GLOBAL_SKILL_DIRS:
                p = g_dir / skill_name
                if p.is_symlink() or p.exists():
                    if p.is_dir() and not p.is_symlink():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
                    found = True
            return found

        entry = state["skills"][skill_name]
        for full_path in entry.get("paths", []):
            p = Path(full_path)
            if p.is_symlink() or p.exists():
                if p.is_dir() and not p.is_symlink():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)

        del state["skills"][skill_name]
        save_global_state(state)
        return True
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")


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
