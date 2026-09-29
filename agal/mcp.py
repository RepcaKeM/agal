from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agal.config import (
    load_config,
)
from agal.skills import (
    load_global_state,
    load_local_state,
    save_global_state,
    save_local_state,
)
from agal.sources import get_all_mcp_servers

LOCAL_MCP_FILE = ".mcp.json"
CLAUDE_GLOBAL_CONFIG = Path.home() / ".claude.json"


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
) -> dict[str, Any]:
    """
    Installs an MCP server by name from available sources into local .mcp.json
    or global configuration files. Merges safely without overwriting other servers.
    """
    if cfg is None:
        cfg = load_config()

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
        mcp_path = target / LOCAL_MCP_FILE
        mcp_data = _read_json_file(mcp_path)
        servers = mcp_data.setdefault("mcpServers", {})
        servers[server_name] = config
        _write_json_file(mcp_path, mcp_data)
        installed_targets.append(str(mcp_path.relative_to(target)))

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
        mcp_path = target / LOCAL_MCP_FILE
        state = load_local_state(target)

        removed = False
        if mcp_path.is_file():
            mcp_data = _read_json_file(mcp_path)
            servers = mcp_data.get("mcpServers", {})
            target_key = server_name
            if target_key not in servers and f"{target_key}-mcp" in servers:
                target_key = f"{target_key}-mcp"
            elif target_key not in servers and target_key.removesuffix("-mcp") in servers:
                target_key = target_key.removesuffix("-mcp")

            if target_key in servers:
                del servers[target_key]
                removed = True
                if not servers and (not state.get("skills") and not state.get("preset")):
                    mcp_path.unlink(missing_ok=True)
                else:
                    _write_json_file(mcp_path, mcp_data)

        st_mcp = state.get("mcp", {})
        target_key = server_name
        if target_key not in st_mcp and f"{target_key}-mcp" in st_mcp:
            target_key = f"{target_key}-mcp"
        elif target_key not in st_mcp and target_key.removesuffix("-mcp") in st_mcp:
            target_key = target_key.removesuffix("-mcp")

        if target_key in st_mcp:
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
