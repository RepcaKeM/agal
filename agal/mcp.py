from __future__ import annotations

import json
from pathlib import Path
import re
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


def _drop_server(path: Path, server_name: str, project_root: Path, rel: str) -> bool:
    """Remove one server from a project MCP file. Deletes the file when it becomes empty."""
    target = MCP_TARGETS[rel]
    mcp_data = _read_target_file(path, target)
    if mcp_data is None:
        return False
    servers = mcp_data.get(target["container"], {})
    if not isinstance(servers, dict):
        return False
    key = _mcp_key(server_name, servers)
    if key is None:
        return False
    del servers[key]
    allowed_empty = set(target.get("empty_keys", ()))
    leftovers = {
        name for name in mcp_data
        if name != target["container"] and name not in allowed_empty
    }
    if not servers and not leftovers:
        path.unlink(missing_ok=True)
        _prune_empty_parents(path.parent, project_root)
    else:
        _write_json_file(path, mcp_data)
    return True


def _read_target_file(path: Path, target: dict[str, Any]) -> dict[str, Any] | None:
    """Read a project MCP file. None means a strict target holds invalid JSON or no object."""
    if not path.is_file():
        return {}
    if target.get("strict"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
        return data if isinstance(data, dict) else None
    return _read_json_file(path)



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


ENV_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _shell_text(text: str) -> str:
    return "".join("\\" + ch if ch in '\\"`$' else ch for ch in text)


def _shell_word(word: str) -> str:
    """Double-quote one shell word, leaving Claude ${VAR} references for the shell."""
    parts: list[str] = []
    pos = 0
    for match in ENV_REF_RE.finditer(word):
        parts.append(_shell_text(word[pos:match.start()]))
        default = match.group(2)
        if default is None:
            parts.append(match.group(0))
        else:
            parts.append(f"${{{match.group(1)}:-{_shell_text(default)}}}")
        pos = match.end()
    parts.append(_shell_text(word[pos:]))
    return '"' + "".join(parts) + '"'


def _sh_wrap(
    command: str, args: list[str], env: dict[str, str]
) -> tuple[str, list[str], dict[str, str]]:
    """Run a stdio server through sh so ${VAR} and ${VAR:-default} expand like Claude's."""
    assignments: list[str] = []
    literal_env: dict[str, str] = {}
    for key, value in env.items():
        value = str(value)
        if ENV_REF_RE.search(value):
            assignments.append(f"{key}={_shell_word(value)}")
        else:
            literal_env[key] = value
    words = ["exec", _shell_word(str(command))]
    words.extend(_shell_word(str(arg)) for arg in args)
    script = " ".join([*assignments, *words])
    return "sh", ["-c", script], literal_env


def _has_refs(*values: Any) -> bool:
    """True when any string in values (including dict and list values) has a ${VAR} reference."""
    def texts(value: Any):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from texts(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from texts(item)

    return any(ENV_REF_RE.search(text) for value in values for text in texts(value))


def _warn_unknown_keys(
    config: dict[str, Any], allowed: set[str], warnings: list[str]
) -> None:
    for key in config:
        if key not in allowed:
            warnings.append(f"dropped unsupported key '{key}'")


def _opencode_ref(text: str, warnings: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(2) is not None:
            warnings.append(
                f"dropped default value in {match.group(0)} (OpenCode has no default syntax)"
            )
        return "{env:" + match.group(1) + "}"

    return ENV_REF_RE.sub(replace, text)


def _opencode_entry(config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if "url" in config:
        entry: dict[str, Any] = {
            "type": "remote",
            "url": _opencode_ref(str(config["url"]), warnings),
        }
        if config.get("headers"):
            entry["headers"] = {
                key: _opencode_ref(str(value), warnings)
                for key, value in config["headers"].items()
            }
        _warn_unknown_keys(config, {"type", "url", "headers"}, warnings)
        return entry, warnings

    command = config.get("command", "")
    args = list(config.get("args", []))
    env = dict(config.get("env", {}))
    if _has_refs(command, args, env):
        command, args, env = _sh_wrap(command, args, env)
    entry = {"type": "local", "command": [command, *args]}
    if env:
        entry["environment"] = {key: str(value) for key, value in env.items()}
    _warn_unknown_keys(config, {"type", "command", "args", "env"}, warnings)
    return entry, warnings


def _agy_entry(config: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if "url" in config:
        if config.get("type") == "sse":
            warnings.append("Antigravity supports Streamable HTTP only")
        if _has_refs(config.get("url"), config.get("headers")):
            warnings.append(
                "Antigravity does not expand environment variables; add it by hand (agy mcp add …)"
            )
            return None, warnings
        entry: dict[str, Any] = {"serverUrl": config["url"]}
        if config.get("headers"):
            entry["headers"] = dict(config["headers"])
        _warn_unknown_keys(config, {"type", "url", "headers"}, warnings)
        return entry, warnings

    command = config.get("command", "")
    args = list(config.get("args", []))
    env = dict(config.get("env", {}))
    if _has_refs(command, args, env):
        command, args, env = _sh_wrap(command, args, env)
    entry = {"command": command, "args": args, "env": env}
    if "cwd" in config:
        entry["cwd"] = config["cwd"]
    _warn_unknown_keys(config, {"type", "command", "args", "env", "cwd"}, warnings)
    return entry, warnings


# Project file, container key, converter, and the rules only agal-written targets need.
MCP_TARGETS: dict[str, dict[str, Any]] = {
    ".mcp.json": {"container": "mcpServers"},
    ".cursor/mcp.json": {"container": "mcpServers"},
    "opencode.json": {
        "container": "mcp",
        "converter": _opencode_entry,
        "strict": True,
        "empty_keys": ("$schema",),
        "schema": "https://opencode.ai/config.json",
    },
    ".agents/mcp_config.json": {
        "container": "mcpServers",
        "converter": _agy_entry,
        "strict": True,
    },
}
PROJECT_MCP_FILES = tuple(MCP_TARGETS)



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
            mcp_target = MCP_TARGETS[rel]
            if rel == "opencode.json" and server_name == "servers":
                print(
                    f"⚠️  MCP server '{server_name}': the name collides with OpenCode's "
                    "mcp.servers container, so opencode.json was not written."
                )
                continue
            mcp_data = _read_target_file(mcp_path, mcp_target)
            if mcp_data is None:
                print(
                    f"⚠️  MCP server '{server_name}': cannot read {rel}, leaving it unchanged."
                )
                continue
            entry: dict[str, Any] | None = config
            converter = mcp_target.get("converter")
            if converter:
                entry, warnings = converter(config)
                for warning in warnings:
                    print(f"⚠️  MCP server '{server_name}': {warning}")
            if entry is None:
                continue
            if mcp_target.get("schema") and not mcp_path.exists():
                mcp_data.setdefault("$schema", mcp_target["schema"])
            servers = mcp_data.setdefault(mcp_target["container"], {})
            servers[server_name] = entry
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
            if _drop_server(target / rel, server_name, target, rel):
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
            _drop_server(path, name, target, rel)

    for name, info in state.get("mcp", {}).items():
        config = dict(info.get("config", {}))
        for rel in wanted:
            if rel == "opencode.json" and name == "servers":
                continue
            mcp_target = MCP_TARGETS[rel]
            path = target / rel
            data = _read_target_file(path, mcp_target)
            if data is None:
                continue
            entry: dict[str, Any] | None = config
            converter = mcp_target.get("converter")
            if converter:
                entry, _ = converter(config)
            if entry is None:
                continue
            if mcp_target.get("schema") and not path.exists():
                data.setdefault("$schema", mcp_target["schema"])
            data.setdefault(mcp_target["container"], {})[name] = entry
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
