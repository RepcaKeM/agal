from __future__ import annotations

import datetime
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from agal.config import (
    get_cache_dir,
    load_config,
)
from agal.sources import (
    index_source_dir,
    list_sources,
    load_sources_registry,
    save_sources_registry,
)


def get_update_cache_file() -> Path:
    return get_cache_dir() / "update_cache.json"


def load_update_cache() -> dict[str, Any]:
    cache_file = get_update_cache_file()
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"timestamp": 0, "updates": {}}


def save_update_cache(cache: dict[str, Any]) -> None:
    cache_file = get_update_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def check_for_updates(
    force: bool = False,
    timeout_sec: float = 2.0,
    cfg: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    """
    Checks registered sources against remote git repositories.
    Uses cached results if check occurred within `update_check_interval`.
    Returns dict: source_name -> {"local": hash, "remote": hash, "url": url}
    """
    if cfg is None:
        cfg = load_config()

    interval = cfg.get("update_check_interval", 86400)
    now = time.time()
    cache = load_update_cache()

    if not force and (now - cache.get("timestamp", 0) < interval):
        return cache.get("updates", {})

    sources = list_sources(cfg)
    updates: dict[str, dict[str, str]] = {}

    for src in sources:
        url = src.get("url")
        branch = src.get("branch") or "main"
        local_commit = src.get("head_commit", "")
        src_path = Path(src.get("path", ""))

        if not url or not src_path.is_dir():
            continue

        if not local_commit:
            try:
                local_commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=src_path, text=True
                ).strip()
            except Exception:
                continue

        try:
            # Query remote branch HEAD using git ls-remote
            output = subprocess.check_output(
                ["git", "ls-remote", "--heads", url, branch],
                text=True,
                timeout=timeout_sec,
                stderr=subprocess.DEVNULL,
            ).strip()
            if output:
                remote_commit = output.split()[0]
                if remote_commit and remote_commit != local_commit:
                    updates[src["name"]] = {
                        "local": local_commit[:7],
                        "remote": remote_commit[:7],
                        "url": url,
                    }
        except Exception:
            # On network timeout or error, silently pass
            pass

    save_update_cache({"timestamp": now, "updates": updates})
    return updates


def format_update_notice(updates: dict[str, dict[str, str]]) -> str | None:
    """Returns a user-friendly suggestion message if updates are available."""
    if not updates:
        return None

    names = list(updates.keys())
    if len(names) == 1:
        s = names[0]
        u = updates[s]
        return f"💡 Update available for '{s}' ({u['local']} → {u['remote']}). Run 'agal update {s}' to apply."
    else:
        s_list = ", ".join(f"'{name}'" for name in names)
        return f"💡 Updates available for sources: {s_list}. Run 'agal update' to apply."


def update_sources(
    source_names: list[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Pulls updates for specified sources (or all if None), re-indexes them,
    and returns a summary of changes.
    """
    if cfg is None:
        cfg = load_config()

    sources = load_sources_registry()
    targets = source_names if source_names else list(sources.keys())
    summary: dict[str, Any] = {}

    for name in targets:
        if name not in sources:
            summary[name] = {"success": False, "error": "Source not found in registry"}
            continue

        src_info = sources[name]
        src_path = Path(src_info.get("path", ""))
        if not src_path.is_dir() or not (src_path / ".git").is_dir():
            summary[name] = {"success": False, "error": f"Path is not a git repository: {src_path}"}
            continue

        old_commit = src_info.get("head_commit", "")
        old_skills = src_info.get("skills_count", 0)
        old_mcp = src_info.get("mcp_count", 0)

        # Pull
        try:
            pull_res = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=src_path,
                capture_output=True,
                text=True,
                check=True,
            )
            new_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=src_path, text=True
            ).strip()

            indexed = index_source_dir(src_path)
            sources[name]["head_commit"] = new_commit
            sources[name]["last_checked"] = datetime.datetime.now().isoformat()
            sources[name]["skills_count"] = len(indexed["skills"])
            sources[name]["mcp_count"] = len(indexed["mcp_servers"])
            sources[name]["hooks_count"] = len(indexed["hooks"])

            summary[name] = {
                "success": True,
                "old_commit": old_commit[:7] if old_commit else "none",
                "new_commit": new_commit[:7],
                "skills_count": len(indexed["skills"]),
                "skills_diff": len(indexed["skills"]) - old_skills,
                "mcp_count": len(indexed["mcp_servers"]),
                "mcp_diff": len(indexed["mcp_servers"]) - old_mcp,
            }
        except subprocess.CalledProcessError as e:
            summary[name] = {"success": False, "error": f"git pull failed: {e.stderr.strip()}"}

    save_sources_registry(sources)

    # Invalidate cache for updated sources
    cache = load_update_cache()
    if "updates" in cache and isinstance(cache["updates"], dict):
        for name in targets:
            cache["updates"].pop(name, None)
        save_update_cache(cache)

    return summary
