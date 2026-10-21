from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import yaml

from agal.config import LOCAL_STATE_FILE, get_subagents_dir
from agal.mcp import install_mcp, uninstall_mcp
from agal.presets import resolve_preset
from agal.skills import (
    install_skill,
    load_local_state,
    save_local_state,
    uninstall_skill,
)

VALID_MODELS = {"inherit", "sonnet", "opus", "haiku"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
# OpenCode applies the last matching shell rule. "*" denies every command;
# a pattern ending in " *" also matches that command with no arguments.
# https://opencode.ai/docs/agents/
_OPENCODE_READONLY_SHELL = {
    "*": "deny",
    "git status *": "allow",
    "git diff *": "allow",
    "git log *": "allow",
    "git show *": "allow",
    "git rev-parse *": "allow",
    "ls *": "allow",
    "rg *": "allow",
    "grep *": "allow",
    "find *": "allow",
    "cat *": "allow",
    "pytest *": "allow",
    "python -m pytest *": "allow",
    "python3 -m pytest *": "allow",
    "npm test *": "allow",
    "pnpm test *": "allow",
}
_NO_SHELL_WRITES = "Do not create or edit files, including through shell commands."
AGY_READ_TOOLS = ["view_file", "grep_search", "list_dir", "find_by_name"]
AGY_WRITE_TOOLS = ["replace_file_content", "write_to_file"]

_ADAPTER_KEYS = {
    "claude": ".claude/agents/{name}.md",
    "cursor": ".cursor/agents/{name}.md",
    "opencode": ".opencode/agents/{name}.md",
    "agy": ".agents/agents/{name}/agent.md",
}


def _validate_name(name: str) -> None:
    if not VALID_NAME_RE.fullmatch(name):
        raise ValueError(
            f"Invalid subagent name '{name}'. Use only letters, digits, '_' and '-'."
        )


def _permission_note(note: str, body: str) -> str:
    body_clean = body.strip()
    if body_clean:
        return f"{note}\n\n{body_clean}"
    return note


def load_subagent(name: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    _validate_name(name)
    sub_dir = get_subagents_dir(cfg)
    agent_file = sub_dir / name / "AGENT.md"
    if not agent_file.is_file():
        raise FileNotFoundError(f"Subagent '{name}' not found: {agent_file}")

    text = agent_file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"No YAML frontmatter in {agent_file}")

    closing_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx == -1:
        raise ValueError(f"Unclosed YAML frontmatter in {agent_file}")

    fm_text = "".join(lines[1:closing_idx])
    body = "".join(lines[closing_idx + 1:])

    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter in {agent_file}: {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError(f"Frontmatter must be a mapping in {agent_file}")

    if fm.get("name") != name:
        raise ValueError(
            f"Subagent name mismatch in {agent_file}: expected '{name}', got '{fm.get('name')}'"
        )

    desc = fm.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        raise ValueError(f"Missing or empty description in {agent_file}")

    model = fm.get("model", "inherit")
    if model is None:
        model = "inherit"
    if model not in VALID_MODELS:
        raise ValueError(
            f"Invalid model '{model}' in {agent_file}. Must be one of: {', '.join(sorted(VALID_MODELS))}"
        )

    effort = fm.get("effort")
    if effort is not None and effort not in VALID_EFFORTS:
        raise ValueError(
            f"Invalid effort '{effort}' in {agent_file}. Must be one of: {', '.join(sorted(VALID_EFFORTS))}"
        )

    skills = fm.get("skills", [])
    if skills is None:
        skills = []
    if not isinstance(skills, list) or any(not isinstance(s, str) for s in skills):
        raise ValueError(f"Invalid skills in {agent_file}: must be a list of strings")

    mcp = fm.get("mcp", [])
    if mcp is None:
        mcp = []
    if not isinstance(mcp, list) or any(not isinstance(m, str) for m in mcp):
        raise ValueError(f"Invalid mcp in {agent_file}: must be a list of strings")

    perms_raw = fm.get("permissions")
    if perms_raw is None:
        permissions = {"edit_files": True, "run_commands": True}
    elif not isinstance(perms_raw, dict):
        raise ValueError(f"Invalid permissions in {agent_file}: must be a mapping")
    else:
        permissions = {
            "edit_files": bool(perms_raw.get("edit_files", True)),
            "run_commands": bool(perms_raw.get("run_commands", True)),
        }

    return {
        "name": name,
        "description": desc.strip(),
        "model": model,
        "effort": effort,
        "permissions": permissions,
        "skills": list(skills),
        "mcp": list(mcp),
        "system_prompt": body.strip(),
        "path": agent_file,
    }


def list_subagents(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    sub_dir = get_subagents_dir(cfg)
    if not sub_dir.is_dir():
        return {}

    subagents: dict[str, dict[str, Any]] = {}
    for entry in sorted(sub_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            subagents[entry.name] = load_subagent(entry.name, cfg)
        except (ValueError, FileNotFoundError) as e:
            print(f"⚠️  Skipping subagent '{entry.name}': {e}")

    return subagents


def save_subagent_template(name: str, cfg: dict[str, Any] | None = None) -> Path:
    _validate_name(name)
    sub_dir = get_subagents_dir(cfg)
    agent_dir = sub_dir / name
    agent_file = agent_dir / "AGENT.md"

    if agent_file.exists():
        raise FileExistsError(f"Subagent '{name}' already exists: {agent_file}")

    agent_dir.mkdir(parents=True, exist_ok=True)
    template_content = f"""---
name: {name}
description: >-
  Description for {name}.
  Use when ...
model: inherit
permissions:
  edit_files: true
  run_commands: true
skills: []
mcp: []
---

You are a {name} subagent.
"""
    agent_file.write_text(template_content, encoding="utf-8")
    return agent_file


def ADAPTER_PATHS(name: str) -> list[str]:
    return [
        f".claude/agents/{name}.md",
        f".cursor/agents/{name}.md",
        f".opencode/agents/{name}.md",
        f".agents/agents/{name}/agent.md",
    ]


def _render_adapter_file(fm: dict[str, Any], body: str) -> str:
    fm_yaml = yaml.safe_dump(fm, sort_keys=False)
    body_clean = body.strip()
    if body_clean:
        return f"---\n{fm_yaml}---\n\n{body_clean}\n"
    return f"---\n{fm_yaml}---\n"


def render_adapters(
    agent: dict[str, Any],
    runtimes: list[str] | None = None,
) -> dict[str, str]:
    name = agent["name"]
    desc = agent["description"]
    model = agent.get("model", "inherit")
    effort = agent.get("effort")
    body = agent.get("system_prompt", "")
    perms = agent.get("permissions") or {}
    edit_files = perms.get("edit_files", True)
    run_commands = perms.get("run_commands", True)
    skills = agent.get("skills") or []
    mcp = agent.get("mcp") or []

    # Claude Code
    claude_fm: dict[str, Any] = {
        "name": name,
        "description": desc,
        "model": model,
    }
    if effort:
        claude_fm["effort"] = effort
    if skills:
        claude_fm["skills"] = list(skills)
    if mcp:
        claude_fm["mcpServers"] = list(mcp)
    disallowed: list[str] = []
    if not edit_files:
        disallowed.extend(["Edit", "Write", "NotebookEdit"])
    if not run_commands:
        disallowed.append("Bash")
    if disallowed:
        claude_fm["disallowedTools"] = disallowed

    # Cursor, OpenCode, and Antigravity inherit the calling session's model.
    # model and effort are written only into the Claude Code adapter.
    cursor_fm: dict[str, Any] = {
        "name": name,
        "description": desc,
        "model": "inherit",
    }
    cursor_body = body
    claude_body = body
    opencode_body = body
    agy_body = body
    if not edit_files and run_commands:
        note = f"{_NO_SHELL_WRITES} You may run commands."
        claude_body = _permission_note(note, body)
        cursor_body = _permission_note(note, body)
        opencode_body = _permission_note(note, body)
        agy_body = _permission_note(note, body)
    elif not edit_files and not run_commands:
        cursor_fm["readonly"] = True
    elif edit_files and not run_commands:
        cursor_body = _permission_note(
            "Do not run shell commands. You may edit files.",
            body,
        )

    # OpenCode's current agent format keys command rules as permission.shell.
    # The older bash key stays for the coarse allow/deny cases.
    opencode_permission: dict[str, Any] = {
        "edit": "allow" if edit_files else "deny",
    }
    if not edit_files and run_commands:
        opencode_permission["shell"] = dict(_OPENCODE_READONLY_SHELL)
    else:
        opencode_permission["bash"] = "allow" if run_commands else "deny"
    opencode_fm: dict[str, Any] = {
        "description": desc,
        "mode": "subagent",
        "permission": opencode_permission,
    }

    # Antigravity
    agy_fm: dict[str, Any] = {
        "name": name,
        "description": desc,
        "subagent": True,
        "mainAgent": False,
        "model": "inherit",
    }
    if skills:
        agy_fm["skills"] = [f"skills/{s}" for s in skills]
    if not edit_files or not run_commands:
        tools = list(AGY_READ_TOOLS)
        if edit_files:
            tools.extend(AGY_WRITE_TOOLS)
        if run_commands:
            tools.append("run_command")
        agy_fm["tools"] = tools

    rendered = {
        f".claude/agents/{name}.md": _render_adapter_file(claude_fm, claude_body),
        f".cursor/agents/{name}.md": _render_adapter_file(cursor_fm, cursor_body),
        f".opencode/agents/{name}.md": _render_adapter_file(opencode_fm, opencode_body),
        f".agents/agents/{name}/agent.md": _render_adapter_file(agy_fm, agy_body),
    }
    if not runtimes:
        return rendered
    keep = {
        _ADAPTER_KEYS[runtime].format(name=name)
        for runtime in runtimes
        if runtime in _ADAPTER_KEYS
    }
    return {path: content for path, content in rendered.items() if path in keep}


def materialize_adapters(
    agent: dict[str, Any],
    target_dir: Path | str,
    runtimes: list[str] | None = None,
) -> list[str]:
    target = Path(target_dir)
    rendered = render_adapters(agent, runtimes=runtimes)
    written: list[str] = []
    for rel_path, content in rendered.items():
        full_path = target / rel_path
        if full_path.exists() or full_path.is_symlink():
            print(f"⚠️  {rel_path} exists and is not managed by agal (skipped).")
            continue
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        written.append(rel_path)
    return written


def unmaterialize_adapters(files: list[str], target_dir: Path | str) -> None:
    target = Path(target_dir)
    for rel_path in files:
        full_path = target / rel_path
        if full_path.is_file() or full_path.is_symlink():
            try:
                full_path.unlink()
            except OSError:
                pass

    parents: set[Path] = set()
    for rel_path in files:
        p = (target / rel_path).parent
        while p != target and target in p.parents:
            parents.add(p)
            p = p.parent

    for p in sorted(parents, key=lambda x: len(x.parts), reverse=True):
        try:
            p.rmdir()
        except OSError:
            pass


def _is_present_mcp(name: str, mcp_keys: set[str]) -> bool:
    return name in mcp_keys or f"{name}-mcp" in mcp_keys or name.removesuffix("-mcp") in mcp_keys


def _drop_replaced_dependencies(
    target: Path,
    name: str,
    previous_skills: list[str],
    previous_mcp: list[str],
    recorded_skills: list[str],
    recorded_mcp: list[str],
    cfg: dict[str, Any] | None,
) -> None:
    """Uninstall deps this subagent dropped, unless another owner still needs them."""
    kept_skills = set(recorded_skills)
    kept_mcp = set(recorded_mcp)
    dropped_skills = [s for s in previous_skills if s not in kept_skills]
    dropped_mcp = [m for m in previous_mcp if not _is_present_mcp(m, kept_mcp)]
    if not dropped_skills and not dropped_mcp:
        return

    state = load_local_state(target)
    other_skills: set[str] = set()
    other_mcp: set[str] = set()
    for sub_name, sub in state.get("subagents", {}).items():
        if sub_name == name:
            continue
        other_skills.update(sub.get("skills", []))
        other_mcp.update(sub.get("mcp", []))

    needed_skills = set(other_skills)
    needed_mcp = set(other_mcp)
    preset_skills: set[str] = set()
    preset_mcp: set[str] = set()
    preset_resolved = False
    if state.get("preset"):
        try:
            preset = resolve_preset(state["preset"], cfg=cfg)
            preset_skills = set(preset.get("skills", []))
            preset_mcp = set(preset.get("mcp", []))
            preset_resolved = True
            needed_skills.update(preset_skills)
            needed_mcp.update(preset_mcp)
        except Exception:
            needed_skills = set(state.get("skills", {}))
            needed_mcp = set(state.get("mcp", {}))

    owned = state.get("subagent_owned", {})
    owned_skills = set(owned.get("skills", []))
    owned_mcp = set(owned.get("mcp", []))

    transfer_skills: list[str] = []
    transfer_mcp: list[str] = []
    if preset_resolved:
        transfer_skills = [
            s for s in dropped_skills
            if s in owned_skills and s not in other_skills and s in preset_skills
        ]
        transfer_mcp = [
            m for m in dropped_mcp
            if m in owned_mcp and not _is_present_mcp(m, other_mcp) and _is_present_mcp(m, preset_mcp)
        ]

    to_uninstall_skills = [
        s for s in dropped_skills if s in owned_skills and s not in needed_skills
    ]
    to_uninstall_mcp = [
        m for m in dropped_mcp
        if m in owned_mcp and not _is_present_mcp(m, needed_mcp)
    ]

    uninstalled_skills: list[str] = []
    for s in to_uninstall_skills:
        if uninstall_skill(s, target_dir=target, scope="local"):
            uninstalled_skills.append(s)

    uninstalled_mcp: list[str] = []
    for m in to_uninstall_mcp:
        if uninstall_mcp(m, target_dir=target, scope="local"):
            uninstalled_mcp.append(m)

    state = load_local_state(target)
    if "subagent_owned" not in state:
        return
    cur_skills = [
        s for s in state["subagent_owned"].get("skills", [])
        if s not in uninstalled_skills and s not in transfer_skills
    ]
    cur_mcp = [
        m for m in state["subagent_owned"].get("mcp", [])
        if m not in uninstalled_mcp and m not in transfer_mcp
    ]
    if not cur_skills and not cur_mcp and not state.get("subagents"):
        state.pop("subagent_owned", None)
    else:
        state["subagent_owned"]["skills"] = cur_skills
        state["subagent_owned"]["mcp"] = cur_mcp
    if transfer_skills or transfer_mcp:
        preset_owned = state.setdefault("preset_owned", {"skills": [], "mcp": [], "hooks": []})
        preset_owned["skills"] = sorted(set(preset_owned.get("skills", [])) | set(transfer_skills))
        preset_owned["mcp"] = sorted(set(preset_owned.get("mcp", [])) | set(transfer_mcp))
        preset_owned.setdefault("hooks", list(preset_owned.get("hooks", [])))
    save_local_state(target, state)


def install_subagent(
    name: str,
    target_dir: Path | str | None = None,
    cfg: dict[str, Any] | None = None,
    all_skills: dict[str, dict[str, Any]] | None = None,
    all_mcp: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    agent = load_subagent(name, cfg)
    target = (Path(target_dir) if target_dir else Path.cwd()).resolve()

    if all_skills is None:
        from agal.skills import get_all_skills
        all_skills = get_all_skills(cfg)
    if all_mcp is None:
        from agal.mcp import get_all_mcp_servers
        all_mcp = get_all_mcp_servers(cfg)

    state = load_local_state(target)
    previous = state.get("subagents", {}).get(name, {})
    previous_skills = list(previous.get("skills", []))
    previous_mcp = list(previous.get("mcp", []))
    before_skills = set(state.get("skills", {}).keys())
    before_mcp = set(state.get("mcp", {}).keys())

    recorded_skills: list[str] = []
    newly_owned_skills: list[str] = []
    missing: list[str] = []

    for s in agent.get("skills", []):
        try:
            install_skill(
                s, target_dir=target, scope="local", cfg=cfg, all_skills=all_skills
            )
            recorded_skills.append(s)
            if s not in before_skills:
                newly_owned_skills.append(s)
                before_skills.add(s)
        except (ValueError, FileNotFoundError):
            print(f"⚠️  Subagent '{name}': skill '{s}' not available (skipped).")
            missing.append(s)

    recorded_mcp: list[str] = []
    newly_owned_mcp: list[str] = []

    for m in agent.get("mcp", []):
        if _is_present_mcp(m, before_mcp):
            recorded_mcp.append(m)
            continue
        try:
            install_mcp(
                m, target_dir=target, scope="local", cfg=cfg, all_servers=all_mcp
            )
            recorded_mcp.append(m)
            newly_owned_mcp.append(m)
            before_mcp.add(m)
        except (ValueError, FileNotFoundError):
            print(f"⚠️  Subagent '{name}': mcp '{m}' not available (skipped).")
            missing.append(m)

    if name in state.get("subagents", {}):
        old_files = state["subagents"][name].get("files", [])
        unmaterialize_adapters(old_files, target)

    runtimes = state.get("runtimes") or None
    files = materialize_adapters(agent, target, runtimes=runtimes)

    state = load_local_state(target)
    state.setdefault("subagents", {})[name] = {
        "skills": recorded_skills,
        "mcp": recorded_mcp,
        "files": files,
    }

    owned = state.setdefault("subagent_owned", {})
    owned_skills = set(owned.get("skills", []))
    owned_skills.update(newly_owned_skills)
    owned["skills"] = sorted(owned_skills)

    owned_mcp = set(owned.get("mcp", []))
    owned_mcp.update(newly_owned_mcp)
    owned["mcp"] = sorted(owned_mcp)

    save_local_state(target, state)
    _drop_replaced_dependencies(
        target, name, previous_skills, previous_mcp, recorded_skills, recorded_mcp, cfg
    )

    return {
        "name": name,
        "files": files,
        "skills": recorded_skills,
        "mcp": recorded_mcp,
        "missing": missing,
    }


def remove_subagent(
    name: str,
    target_dir: Path | str | None = None,
    cfg: dict[str, Any] | None = None,
    check_preset: bool = True,
) -> dict[str, Any]:
    target = (Path(target_dir) if target_dir else Path.cwd()).resolve()
    state_file = target / LOCAL_STATE_FILE
    if not state_file.is_file():
        return {"removed": False, "skills": [], "mcp": []}

    state = load_local_state(target)
    if name not in state.get("subagents", {}):
        return {"removed": False, "skills": [], "mcp": []}

    entry = state["subagents"].pop(name)
    save_local_state(target, state)
    unmaterialize_adapters(entry.get("files", []), target)

    other_subagents = state.get("subagents", {})
    other_skills = set()
    other_mcp = set()
    for sub in other_subagents.values():
        other_skills.update(sub.get("skills", []))
        other_mcp.update(sub.get("mcp", []))

    needed_skills = set(other_skills)
    needed_mcp = set(other_mcp)
    preset_skills: set[str] = set()
    preset_mcp: set[str] = set()
    preset_resolved = False

    if check_preset and state.get("preset"):
        try:
            preset = resolve_preset(state["preset"], cfg=cfg)
            preset_skills = set(preset.get("skills", []))
            preset_mcp = set(preset.get("mcp", []))
            preset_resolved = True
            needed_skills.update(preset_skills)
            needed_mcp.update(preset_mcp)
        except Exception:
            needed_skills = set(state.get("skills", {}).keys())
            needed_mcp = set(state.get("mcp", {}).keys())

    owned = state.get("subagent_owned", {})
    owned_skills = list(owned.get("skills", []))
    owned_mcp = list(owned.get("mcp", []))

    transfer_skills: list[str] = []
    transfer_mcp: list[str] = []
    if preset_resolved:
        transfer_skills = [
            s for s in owned_skills if s not in other_skills and s in preset_skills
        ]
        transfer_mcp = [
            m for m in owned_mcp
            if not _is_present_mcp(m, other_mcp) and _is_present_mcp(m, preset_mcp)
        ]

    to_uninstall_skills = [s for s in owned_skills if s not in needed_skills]
    to_uninstall_mcp = [m for m in owned_mcp if not _is_present_mcp(m, needed_mcp)]

    uninstalled_skills: list[str] = []
    for s in to_uninstall_skills:
        if uninstall_skill(s, target_dir=target, scope="local"):
            uninstalled_skills.append(s)

    uninstalled_mcp: list[str] = []
    for m in to_uninstall_mcp:
        if uninstall_mcp(m, target_dir=target, scope="local"):
            uninstalled_mcp.append(m)

    state = load_local_state(target)
    if "subagent_owned" in state:
        cur_skills = [
            s for s in state["subagent_owned"].get("skills", [])
            if s not in uninstalled_skills and s not in transfer_skills
        ]
        cur_mcp = [
            m for m in state["subagent_owned"].get("mcp", [])
            if m not in uninstalled_mcp and m not in transfer_mcp
        ]
        if not cur_skills and not cur_mcp and not state.get("subagents"):
            state.pop("subagent_owned", None)
        else:
            state["subagent_owned"]["skills"] = cur_skills
            state["subagent_owned"]["mcp"] = cur_mcp
    if transfer_skills or transfer_mcp:
        preset_owned = state.setdefault("preset_owned", {"skills": [], "mcp": [], "hooks": []})
        preset_owned["skills"] = sorted(set(preset_owned.get("skills", [])) | set(transfer_skills))
        preset_owned["mcp"] = sorted(set(preset_owned.get("mcp", [])) | set(transfer_mcp))
        preset_owned.setdefault("hooks", list(preset_owned.get("hooks", [])))
    save_local_state(target, state)

    return {
        "removed": True,
        "skills": uninstalled_skills,
        "mcp": uninstalled_mcp,
    }


def sync_installed_subagents(
    target_dir: Path | str,
    cfg: dict[str, Any] | None = None,
) -> None:
    """Rewrite installed subagent files for the project's selected runtimes."""
    target = Path(target_dir).resolve()
    state = load_local_state(target)
    runtimes = state.get("runtimes") or None
    for name in list(state.get("subagents", {})):
        entry = state["subagents"][name]
        try:
            agent = load_subagent(name, cfg)
        except (ValueError, FileNotFoundError) as exc:
            print(f"⚠️  Subagent '{name}' not rewritten: {exc}")
            continue
        unmaterialize_adapters(entry.get("files", []), target)
        files = materialize_adapters(agent, target, runtimes=runtimes)
        state = load_local_state(target)
        if name in state.get("subagents", {}):
            state["subagents"][name]["files"] = files
            save_local_state(target, state)


def unprepare_all_subagents(
    target_dir: Path | str | None = None,
    cfg: dict[str, Any] | None = None,
) -> list[str]:
    target = (Path(target_dir) if target_dir else Path.cwd()).resolve()
    state = load_local_state(target)
    installed_names = list(state.get("subagents", {}).keys())
    removed: list[str] = []
    for name in installed_names:
        res = remove_subagent(name, target_dir=target, cfg=cfg, check_preset=False)
        if res.get("removed"):
            removed.append(name)
    return removed

