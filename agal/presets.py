from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
from typing import Any
import yaml

from agal.config import (
    get_presets_dir,
    load_config,
)
from agal.context import (
    build_routing_block,
    place_context_file,
    remove_context_file,
)
from agal.hooks import install_hook, uninstall_hook
from agal.mcp import install_mcp, uninstall_mcp
from agal.skills import (
    install_skill,
    load_local_state,
    save_local_state,
    uninstall_skill,
)
from agal.sources import (
    get_all_mcp_servers,
    get_all_skills,
)


def load_preset(name: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Loads a preset YAML file by name."""
    if cfg is None:
        cfg = load_config()

    presets_dir = get_presets_dir(cfg)
    preset_file = presets_dir / f"{name}.yaml"
    if not preset_file.is_file():
        preset_file = presets_dir / f"{name}.yml"

    if not preset_file.is_file():
        raise FileNotFoundError(f"Preset '{name}' not found in {presets_dir}")

    with open(preset_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid preset format in {preset_file}")

    data["name"] = data.get("name", name)
    data["skills"] = list(data.get("skills", []))
    data["mcp"] = list(data.get("mcp", []))
    data["hooks"] = list(data.get("hooks", []))
    return data


def resolve_preset(name: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Loads a preset and automatically prepends skills/mcp from `core_preset`
    if configured and different from the current preset.
    """
    if cfg is None:
        cfg = load_config()

    preset = load_preset(name, cfg)
    core_name = cfg.get("core_preset")

    if core_name and core_name != name:
        try:
            core = load_preset(core_name, cfg)
            # Prepend core skills (deduplicated)
            combined_skills = []
            for s in core.get("skills", []) + preset.get("skills", []):
                if s not in combined_skills:
                    combined_skills.append(s)
            preset["skills"] = combined_skills

            # Prepend core MCP
            combined_mcp = []
            for m in core.get("mcp", []) + preset.get("mcp", []):
                if m not in combined_mcp:
                    combined_mcp.append(m)
            preset["mcp"] = combined_mcp

            # Prepend core hooks
            combined_hooks = []
            for h in core.get("hooks", []) + preset.get("hooks", []):
                if h not in combined_hooks:
                    combined_hooks.append(h)
            preset["hooks"] = combined_hooks
        except FileNotFoundError:
            pass

    return preset


def save_preset(
    name: str,
    description: str,
    skills: list[str],
    mcp: list[str] | None = None,
    hooks: list[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> Path:
    """Saves a preset YAML file into presets_dir."""
    if cfg is None:
        cfg = load_config()

    presets_dir = get_presets_dir(cfg)
    presets_dir.mkdir(parents=True, exist_ok=True)
    target_file = presets_dir / f"{name}.yaml"

    content = {
        "name": name,
        "description": description.strip(),
        "skills": skills or [],
        "mcp": mcp or [],
    }
    if hooks:
        content["hooks"] = hooks

    with open(target_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(content, f, default_flow_style=False, sort_keys=False)

    return target_file


def delete_preset(name: str, cfg: dict[str, Any] | None = None) -> bool:
    """Deletes a preset YAML file by name. Returns True if deleted, False if not found."""
    if cfg is None:
        cfg = load_config()

    presets_dir = get_presets_dir(cfg)
    preset_file = presets_dir / f"{name}.yaml"
    if not preset_file.is_file():
        preset_file = presets_dir / f"{name}.yml"

    if preset_file.is_file():
        try:
            preset_file.unlink()
            return True
        except Exception:
            return False
    return False


def edit_preset(name: str, cfg: dict[str, Any] | None = None) -> Path:
    """Opens preset YAML file in $EDITOR. Raises FileNotFoundError if preset does not exist."""
    if cfg is None:
        cfg = load_config()

    presets_dir = get_presets_dir(cfg)
    preset_file = presets_dir / f"{name}.yaml"
    if not preset_file.is_file():
        preset_file = presets_dir / f"{name}.yml"

    if not preset_file.is_file():
        raise FileNotFoundError(f"Preset '{name}' not found in {presets_dir}")

    editor = os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vim") or shutil.which("vi") or "nano"
    subprocess.run([editor, str(preset_file)], check=True)
    return preset_file


def list_presets(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Returns all available presets with item counts."""
    if cfg is None:
        cfg = load_config()

    presets_dir = get_presets_dir(cfg)
    presets = []

    if not presets_dir.is_dir():
        return presets

    for file_path in sorted(presets_dir.glob("*.yaml")) + sorted(presets_dir.glob("*.yml")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    presets.append({
                        "name": data.get("name", file_path.stem),
                        "description": data.get("description", ""),
                        "skills_count": len(data.get("skills", [])),
                        "mcp_count": len(data.get("mcp", [])),
                        "hooks_count": len(data.get("hooks", [])),
                        "path": str(file_path),
                    })
        except Exception:
            pass

    return presets


def _select_items_cli(
    items: list[str],
    prompt: str,
    display_labels: list[str] | None = None,
) -> list[str]:
    """Helper to select items using fzf if available, else interactive prompt."""
    if not items:
        return []

    if display_labels is None or len(display_labels) != len(items):
        display_labels = items

    # Try fzf
    if shutil.which("fzf"):
        try:
            label_to_item = {label.strip(): item for item, label in zip(items, display_labels)}
            proc = subprocess.Popen(
                ["fzf", "-m", "--prompt", f"{prompt} > "],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            out, _ = proc.communicate(input="\n".join(display_labels))
            if proc.returncode == 0:
                selected = []
                for line in out.splitlines():
                    line = line.strip()
                    if line in label_to_item:
                        selected.append(label_to_item[line])
                    elif line in items:
                        selected.append(line)
                return selected
        except Exception:
            pass

    # Fallback to console prompt
    print(f"\n{prompt} (enter comma-separated numbers, or press Enter to skip):")
    pad_idx = len(str(len(items)))
    for idx, label in enumerate(display_labels, 1):
        print(f"  [{idx:{pad_idx}d}] {label}")

    choice = input("\nSelect > ").strip()
    if not choice:
        return []

    selected = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx])
    return selected


def create_preset_interactive(name: str, cfg: dict[str, Any] | None = None) -> Path:
    """Interactively guides user through creating a new unified preset."""
    if cfg is None:
        cfg = load_config()

    print(f"\n🛠️  Creating preset: {name}")
    desc = input("Enter description: ").strip() or f"{name} preset"

    # Skills selection
    skills_dict = get_all_skills(cfg)
    all_skills = sorted(skills_dict.keys())
    skill_labels = []
    for sname in all_skills:
        sinfo = skills_dict[sname]
        src = sinfo.get("source", "unknown")
        raw_desc = sinfo.get("description", "")
        clean_desc = " ".join(raw_desc.split())
        desc_short = (clean_desc[:55] + "...") if len(clean_desc) > 55 else clean_desc
        label = f"{sname:<32} [{src}]"
        if desc_short:
            label = f"{label:<48} {desc_short}"
        skill_labels.append(label)

    selected_skills = _select_items_cli(all_skills, "Select Skills for this preset", display_labels=skill_labels)
    print(f"  Selected {len(selected_skills)} skill(s).")

    # MCP selection
    mcp_dict = get_all_mcp_servers(cfg)
    all_mcp = sorted(mcp_dict.keys())
    mcp_labels = []
    for mname in all_mcp:
        minfo = mcp_dict[mname]
        src = minfo.get("source", "unknown")
        mcfg = minfo.get("config", {})
        label = f"{mname:<24} [{src}]"
        if "url" in mcfg:
            label = f"{label:<40} url: {mcfg['url']}"
        elif mcfg.get("command"):
            label = f"{label:<40} command: {mcfg['command']}"
        mcp_labels.append(label)

    selected_mcp = _select_items_cli(all_mcp, "Select MCP Servers for this preset", display_labels=mcp_labels)
    print(f"  Selected {len(selected_mcp)} MCP server(s).")

    path = save_preset(name, desc, selected_skills, selected_mcp, cfg=cfg)
    print(f"\n✅ Preset saved to {path}")
    return path


def install_preset(
    name: str,
    target_dir: Path | None = None,
    scope: str = "local",
    copy: bool = False,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Installs an entire preset (skills + MCP + hooks + context guidelines).
    """
    if cfg is None:
        cfg = load_config()

    preset = resolve_preset(name, cfg)
    target = (target_dir or Path.cwd()).resolve()

    installed_skills = []
    installed_mcp = []
    installed_hooks = []

    # 1. Install Skills
    all_skills = get_all_skills(cfg)
    skill_paths: dict[str, Path] = {}
    for sname in preset.get("skills", []):
        if sname in all_skills:
            skill_paths[sname] = Path(all_skills[sname]["path"])
            try:
                res = install_skill(sname, target_dir=target, scope=scope, copy=copy, cfg=cfg)
                installed_skills.append(res)
            except Exception as e:
                print(f"⚠️  Failed to install skill '{sname}': {e}")
        else:
            print(f"⚠️  Skill '{sname}' not found in any registered source (skipped).")

    # 2. Install MCP
    all_mcp = get_all_mcp_servers(cfg)
    for mname in preset.get("mcp", []):
        if mname in all_mcp:
            try:
                res = install_mcp(mname, target_dir=target, scope=scope, cfg=cfg)
                installed_mcp.append(res)
            except Exception as e:
                print(f"⚠️  Failed to install MCP '{mname}': {e}")
        else:
            print(f"⚠️  MCP server '{mname}' not found in any registered source (skipped).")

    # 3. Install Hooks
    for hname in preset.get("hooks", []):
        try:
            res = install_hook(hname, target_dir=target, scope=scope, cfg=cfg)
            installed_hooks.append(res)
        except Exception as e:
            print(f"⚠️  Failed to install hook '{hname}': {e}")

    # 4. Context & Routing CSV (if local and context_file configured or default AGENTS.md exists)
    placed_guidelines: list[str] = []
    if scope == "local":
        ctx_file = cfg.get("context_file")
        if not ctx_file:
            # Fallback to repo's AGENTS.md or ~/.agal/AGENTS.md
            candidates = [
                Path(__file__).parent.parent / "AGENTS.md",
                get_presets_dir(cfg).parent / "AGENTS.md",
            ]
            for c in candidates:
                if c.is_file():
                    ctx_file = str(c.resolve())
                    break

        if ctx_file and Path(ctx_file).is_file():
            routing_block, _ = build_routing_block(preset.get("skills", []), skill_paths)
            placed_guidelines = place_context_file(
                target_dir=target,
                context_path=Path(ctx_file),
                copy=copy,
                routing_block=routing_block,
            )

        # Update preset marker in local state
        state = load_local_state(target)
        state["preset"] = name
        save_local_state(target, state)

    return {
        "preset": name,
        "scope": scope,
        "skills": installed_skills,
        "mcp": installed_mcp,
        "hooks": installed_hooks,
        "guidelines": placed_guidelines,
    }


def uninstall_preset(
    target_dir: Path | None = None,
    scope: str = "local",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Uninstalls all items managed by agal in the specified scope."""
    target = (target_dir or Path.cwd()).resolve()

    if scope == "local":
        state = load_local_state(target)
        removed_skills = []
        removed_mcp = []
        removed_hooks = []

        for sname in list(state.get("skills", {}).keys()):
            if uninstall_skill(sname, target_dir=target, scope="local"):
                removed_skills.append(sname)

        for mname in list(state.get("mcp", {}).keys()):
            if uninstall_mcp(mname, target_dir=target, scope="local"):
                removed_mcp.append(mname)

        for hname in list(state.get("hooks", {}).keys()):
            if uninstall_hook(hname, target_dir=target, scope="local"):
                removed_hooks.append(hname)

        removed_context = remove_context_file(target)

        # Clear state
        save_local_state(target, {"skills": {}, "mcp": {}, "hooks": {}, "preset": None})

        return {
            "scope": "local",
            "removed_skills": removed_skills,
            "removed_mcp": removed_mcp,
            "removed_hooks": removed_hooks,
            "removed_context": removed_context,
        }
    else:
        # Global scope
        raise NotImplementedError("Global preset uninstall should be done per-item or with a specific preset name.")
