from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from agal.config import get_subagents_dir

VALID_MODELS = {"inherit", "sonnet", "opus", "haiku"}
AGY_READ_TOOLS = ["view_file", "grep_search"]


def load_subagent(name: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
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


def render_adapters(agent: dict[str, Any]) -> dict[str, str]:
    name = agent["name"]
    desc = agent["description"]
    model = agent.get("model", "inherit")
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

    # Cursor
    cursor_fm: dict[str, Any] = {
        "name": name,
        "description": desc,
        "model": "inherit",
    }
    if not edit_files or not run_commands:
        cursor_fm["readonly"] = True

    # OpenCode
    opencode_fm: dict[str, Any] = {
        "description": desc,
        "mode": "subagent",
        "permission": {
            "edit": "allow" if edit_files else "deny",
            "bash": "allow" if run_commands else "deny",
        },
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
            tools.append("replace_file_content")
        if run_commands:
            tools.append("run_command")
        agy_fm["tools"] = tools

    return {
        f".claude/agents/{name}.md": _render_adapter_file(claude_fm, body),
        f".cursor/agents/{name}.md": _render_adapter_file(cursor_fm, body),
        f".opencode/agents/{name}.md": _render_adapter_file(opencode_fm, body),
        f".agents/agents/{name}/agent.md": _render_adapter_file(agy_fm, body),
    }


def materialize_adapters(agent: dict[str, Any], target_dir: Path | str) -> list[str]:
    target = Path(target_dir)
    rendered = render_adapters(agent)
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

