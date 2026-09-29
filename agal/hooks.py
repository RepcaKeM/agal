from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from agal.config import load_config
from agal.skills import (
    load_global_state,
    load_local_state,
    save_global_state,
    save_local_state,
)
from agal.sources import get_all_hooks


def install_hook(
    hook_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Installs an agent lifecycle hook into .claude/hooks or global hooks directory.
    """
    if cfg is None:
        cfg = load_config()

    all_hooks = get_all_hooks(cfg)
    if hook_name not in all_hooks:
        raise ValueError(f"Hook '{hook_name}' not found in any registered source.")

    hook_info = all_hooks[hook_name]
    src_path = Path(hook_info["path"])

    target = (target_dir or Path.cwd()).resolve()

    if scope == "local":
        hooks_dir = target / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        dest = hooks_dir / hook_name

        shutil.copy2(src_path, dest)
        try:
            dest.chmod(dest.stat().st_mode | 0o111)
        except Exception:
            pass

        state = load_local_state(target)
        state.setdefault("hooks", {})[hook_name] = {
            "source": hook_info.get("source", "unknown"),
            "path": str(dest.relative_to(target)),
        }
        save_local_state(target, state)

        return {
            "hook": hook_name,
            "source": hook_info.get("source", "unknown"),
            "scope": scope,
            "dest": str(dest.relative_to(target)),
        }

    elif scope == "global":
        hooks_dir = Path.home() / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        dest = hooks_dir / hook_name

        shutil.copy2(src_path, dest)
        try:
            dest.chmod(dest.stat().st_mode | 0o111)
        except Exception:
            pass

        state = load_global_state()
        state.setdefault("hooks", {})[hook_name] = {
            "source": hook_info.get("source", "unknown"),
            "path": str(dest),
        }
        save_global_state(state)

        return {
            "hook": hook_name,
            "source": hook_info.get("source", "unknown"),
            "scope": scope,
            "dest": str(dest),
        }
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")


def uninstall_hook(
    hook_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
) -> bool:
    """Uninstalls a lifecycle hook."""
    target = (target_dir or Path.cwd()).resolve()

    if scope == "local":
        dest = target / ".claude" / "hooks" / hook_name
        existed = dest.is_symlink() or dest.exists()
        dest.unlink(missing_ok=True)

        state = load_local_state(target)
        removed_from_state = False
        if hook_name in state.get("hooks", {}):
            del state["hooks"][hook_name]
            save_local_state(target, state)
            removed_from_state = True
        return existed or removed_from_state

    elif scope == "global":
        dest = Path.home() / ".claude" / "hooks" / hook_name
        existed = dest.is_symlink() or dest.exists()
        dest.unlink(missing_ok=True)

        state = load_global_state()
        removed_from_state = False
        if hook_name in state.get("hooks", {}):
            del state["hooks"][hook_name]
            save_global_state(state)
            removed_from_state = True
        return existed or removed_from_state
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")
