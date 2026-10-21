from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from agal.config import get_subagents_dir, load_config

VALID_MODELS = {"inherit", "sonnet", "opus", "haiku"}


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
