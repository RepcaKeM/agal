from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Collection

from agal.config import (
    load_config,
    mcp_files_for_runtimes,
)
from agal.skills import (
    _prune_empty_parents,
    load_global_state,
    load_local_state,
    save_global_state,
    save_local_state,
)
from agal.sources import get_all_mcp_servers

LOCAL_MCP_FILE = ".mcp.json"
CURSOR_MCP_FILE = ".cursor/mcp.json"
PROJECT_MCP_FILES = (LOCAL_MCP_FILE, CURSOR_MCP_FILE)
CLAUDE_GLOBAL_CONFIG = Path.home() / ".claude.json"


def _mcp_key(server_name: str, servers: Collection[str]) -> str | None:
    if server_name in servers:
        return server_name
    suffixed = f"{server_name}-mcp"
    if suffixed in servers:
        return suffixed
    stripped = server_name.removesuffix("-mcp")
    if stripped in servers:
        return stripped
    return None


def mcp_matches(server_name: str, pool: Collection[str]) -> bool:
    """True when pool holds server_name, with or without the -mcp suffix."""
    return _mcp_key(server_name, pool) is not None


def _drop_server(path: Path, server_name: str, project_root: Path) -> bool:
    """Remove one server from a project MCP file. Deletes the file when it becomes empty."""
    if not path.is_file():
        return False
    mcp_data = _read_json_file(path)
    servers = mcp_data.get("mcpServers", {})
    key = _mcp_key(server_name, servers)
    if key is None:
        return False
    del servers[key]
    if not servers and not any(name != "mcpServers" for name in mcp_data):
        path.unlink(missing_ok=True)
        _prune_empty_parents(path.parent, project_root)
    else:
        _write_json_file(path, mcp_data)
    return True


def _read_json_file(path: Path) -> dict[str, Any]:
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def _write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def install_mcp(
    server_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
    cfg: dict[str, Any] | None = None,
    all_servers: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Installs an MCP server by name from available sources into local .mcp.json
    or global configuration files. Merges safely without overwriting other servers.
    """
    if cfg is None:
        cfg = load_config()

    if all_servers is None:
        all_servers = get_all_mcp_servers(cfg)
    if server_name not in all_servers:
        matched = None
        for sname, sinfo in all_servers.items():
            if (
                sinfo.get("raw_name") == server_name
                or sinfo.get("package") == server_name
                or sname.removesuffix("-mcp") == server_name
                or f"{sname}-mcp" == server_name
            ):
                matched = sname
                break
        if matched:
            server_name = matched
        else:
            raise ValueError(f"MCP server '{server_name}' not found in any registered source.")

    server_info = all_servers[server_name]
    config = dict(server_info.get("config", {}))

    # Strip description and internal metadata from the live MCP config if present
    config.pop("description", None)
    config.pop("raw_name", None)
    config.pop("package", None)

    target = (target_dir or Path.cwd()).resolve()
    installed_targets: list[str] = []

    if scope == "local":
        runtimes = load_local_state(target).get("runtimes") or None
        rel_files = mcp_files_for_runtimes(runtimes)
        for rel in rel_files:
            mcp_path = target / rel
            mcp_data = _read_json_file(mcp_path)
            servers = mcp_data.setdefault("mcpServers", {})
            servers[server_name] = config
            _write_json_file(mcp_path, mcp_data)
            installed_targets.append(rel)
        if not rel_files:
            print(
                f"⚠️  MCP server '{server_name}' recorded, but the selected "
                "runtimes do not read a project MCP file."
            )

        # Update local state
        state = load_local_state(target)
        state.setdefault("mcp", {})[server_name] = {
            "source": server_info.get("source", "unknown"),
            "manifest_path": server_info.get("manifest_path", ""),
            "config": config,
        }
        save_local_state(target, state)

    elif scope == "global":
        # Global Claude config (~/.claude.json)
        claude_cfg = _read_json_file(CLAUDE_GLOBAL_CONFIG)
        servers = claude_cfg.setdefault("mcpServers", {})
        servers[server_name] = config
        _write_json_file(CLAUDE_GLOBAL_CONFIG, claude_cfg)
        installed_targets.append(str(CLAUDE_GLOBAL_CONFIG))

        # Update global state
        state = load_global_state()
        state.setdefault("mcp", {})[server_name] = {
            "source": server_info.get("source", "unknown"),
            "manifest_path": server_info.get("manifest_path", ""),
            "config": config,
        }
        save_global_state(state)
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")

    return {
        "mcp": server_name,
        "source": server_info.get("source", "unknown"),
        "scope": scope,
        "targets": installed_targets,
    }


def uninstall_mcp(
    server_name: str,
    target_dir: Path | None = None,
    scope: str = "local",
) -> bool:
    """Removes an MCP server from local or global configurations."""
    target = (target_dir or Path.cwd()).resolve()

    if scope == "local":
        state = load_local_state(target)

        removed = False
        for rel in PROJECT_MCP_FILES:
            if _drop_server(target / rel, server_name, target):
                removed = True

        st_mcp = state.get("mcp", {})
        target_key = _mcp_key(server_name, st_mcp)

        if target_key is not None and target_key in st_mcp:
            del st_mcp[target_key]
            save_local_state(target, state)
            removed = True

        return removed

    elif scope == "global":
        removed = False
        if CLAUDE_GLOBAL_CONFIG.is_file():
            claude_cfg = _read_json_file(CLAUDE_GLOBAL_CONFIG)
            servers = claude_cfg.get("mcpServers", {})
            target_key = server_name
            if target_key not in servers and f"{target_key}-mcp" in servers:
                target_key = f"{target_key}-mcp"
            elif target_key not in servers and target_key.removesuffix("-mcp") in servers:
                target_key = target_key.removesuffix("-mcp")

            if target_key in servers:
                del servers[target_key]
                _write_json_file(CLAUDE_GLOBAL_CONFIG, claude_cfg)
                removed = True

        state = load_global_state()
        st_mcp = state.get("mcp", {})
        target_key = server_name
        if target_key not in st_mcp and f"{target_key}-mcp" in st_mcp:
            target_key = f"{target_key}-mcp"
        elif target_key not in st_mcp and target_key.removesuffix("-mcp") in st_mcp:
            target_key = target_key.removesuffix("-mcp")

        if target_key in st_mcp:
            del st_mcp[target_key]
            save_global_state(state)
            removed = True

        return removed
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'local' or 'global'.")


def sync_installed_mcp(target_dir: Path) -> None:
    """Rewrite project MCP files for the runtimes selected in this project."""
    target = target_dir.resolve()
    state = load_local_state(target)
    wanted = set(mcp_files_for_runtimes(state.get("runtimes") or None))
    managed = list(state.get("mcp", {}))

    for rel in PROJECT_MCP_FILES:
        if rel in wanted:
            continue
        path = target / rel
        for name in managed:
            _drop_server(path, name, target)

    for name, info in state.get("mcp", {}).items():
        config = dict(info.get("config", {}))
        for rel in wanted:
            path = target / rel
            data = _read_json_file(path)
            data.setdefault("mcpServers", {})[name] = config
            _write_json_file(path, data)


def list_installed_mcp(
    target_dir: Path | None = None,
    scope: str = "local",
) -> dict[str, Any]:
    target = (target_dir or Path.cwd()).resolve()
    if scope == "local":
        return load_local_state(target).get("mcp", {})
    elif scope == "global":
        return load_global_state().get("mcp", {})
    return {}
