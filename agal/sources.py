from __future__ import annotations

import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any
import yaml

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None

from agal.config import (
    get_agal_home,
    get_sources_dir,
    get_sources_file,
    load_config,
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_sources_registry() -> dict[str, Any]:
    file_path = get_sources_file()
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "sources" in data and isinstance(data["sources"], dict):
                    return data["sources"]
        except Exception:
            pass
    return {}


def save_sources_registry(sources: dict[str, Any]) -> None:
    file_path = get_sources_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"sources": sources}, f, default_flow_style=False, sort_keys=False)


def derive_source_name(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    name = Path(cleaned).name
    if not name or name == ".":
        name = "custom-source"
    # normalize characters
    name = re.sub(r"[^a-zA-Z0-9_\-\.]", "-", name).strip("-").lower()
    return name or "source"


def parse_skill_frontmatter(skill_md: Path) -> dict[str, str]:
    meta = {"name": skill_md.parent.name, "description": ""}
    try:
        text = skill_md.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match:
            fm_text = match.group(1)
            parsed = yaml.safe_load(fm_text)
            if isinstance(parsed, dict):
                if "name" in parsed and parsed["name"]:
                    meta["name"] = str(parsed["name"]).strip()
                if "description" in parsed and parsed["description"]:
                    meta["description"] = str(parsed["description"]).strip()
    except Exception:
        pass
    return meta


def _server_config(sval: dict[str, Any]) -> dict[str, Any]:
    """Remote servers (url) keep type/url/headers; stdio servers keep command/args/env."""
    if "url" in sval:
        config: dict[str, Any] = {"type": sval.get("type", "http"), "url": sval["url"]}
        if sval.get("headers"):
            config["headers"] = sval["headers"]
    else:
        config = {
            "command": sval.get("command", ""),
            "args": sval.get("args", []),
            "env": sval.get("env", {}),
        }
    config["description"] = sval.get("description", "")
    return config


def parse_mcp_manifest(manifest_path: Path) -> dict[str, dict[str, Any]]:
    """
    Parses an MCP manifest (JSON or YAML) and returns a mapping:
    server_name -> {command, args, env, description, ...}
    """
    servers: dict[str, dict[str, Any]] = {}
    try:
        text = manifest_path.read_text(encoding="utf-8")
        if manifest_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(text)
        else:
            import json
            data = json.loads(text)

        if not isinstance(data, dict):
            return servers

        # Case 1: Standard MCP schema with mcpServers key
        if "mcpServers" in data and isinstance(data["mcpServers"], dict):
            for sname, sval in data["mcpServers"].items():
                if isinstance(sval, dict):
                    servers[sname] = _server_config(sval)
        # Case 2: Direct server definition
        elif "command" in data:
            sname = manifest_path.parent.name if manifest_path.name in ("mcp.json", "server.json") else manifest_path.stem
            servers[sname] = {
                "command": data.get("command", ""),
                "args": data.get("args", []),
                "env": data.get("env", {}),
                "description": data.get("description", ""),
            }
        # Case 3: MCP Registry schema (e.g. server.json with packages list)
        elif "packages" in data and isinstance(data["packages"], list):
            raw_name = data.get("name", "")
            sname = raw_name.split("/")[-1] if "/" in raw_name else raw_name
            if not sname or sname in ("server", "mcp"):
                sname = manifest_path.parent.name

            for pkg in data["packages"]:
                if not isinstance(pkg, dict):
                    continue
                reg_type = pkg.get("registryType", "").lower()
                identifier = pkg.get("identifier", "")
                if not identifier:
                    continue

                command = ""
                args: list[str] = []

                if reg_type == "npm":
                    command = "npx"
                    args = ["-y", identifier]
                elif reg_type in ("pypi", "python"):
                    command = "uvx"
                    args = [identifier]
                elif reg_type == "docker":
                    command = "docker"
                    args = ["run", "-i", "--rm", identifier]
                elif "command" in pkg:
                    command = pkg["command"]
                    args = pkg.get("args", [])

                if command:
                    servers[sname] = {
                        "command": command,
                        "args": args,
                        "env": pkg.get("env", data.get("env", {})),
                        "description": data.get("description", ""),
                        "raw_name": raw_name,
                        "package": identifier,
                    }
                    break
        # Case 4: Key-value map of servers directly
        else:
            for sname, sval in data.items():
                if isinstance(sval, dict) and ("command" in sval or "url" in sval):
                    servers[sname] = _server_config(sval)
    except Exception:
        pass
    return servers


def index_source_dir(source_dir: Path) -> dict[str, Any]:
    """
    Scans a cloned directory for:
    - skills (directories containing SKILL.md)
    - mcp (manifest files defining MCP servers)
    - hooks (scripts or hooks declarations)
    """
    skills: dict[str, dict[str, Any]] = {}
    mcp_servers: dict[str, dict[str, Any]] = {}
    hooks: list[dict[str, Any]] = []

    if not source_dir.is_dir():
        return {"skills": skills, "mcp_servers": mcp_servers, "hooks": hooks}

    # 1. Discover Skills (case-insensitive skill.md discovery)
    for candidate in source_dir.rglob("*"):
        if not candidate.is_file() or candidate.name.lower() != "skill.md":
            continue

        try:
            rel_parts = candidate.relative_to(source_dir).parts
        except ValueError:
            rel_parts = candidate.parts

        # Ignore skills inside hidden dirs, node_modules, tests, .git
        if any(p.startswith(".") and p != "." for p in rel_parts[:-1]):
            continue
        if any(p in ["node_modules", "vendor", "__pycache__"] for p in rel_parts):
            continue

        skill_dir = candidate.parent
        meta = parse_skill_frontmatter(candidate)
        skill_name = meta.get("name") or (skill_dir.name if skill_dir != source_dir else source_dir.name)

        # Detect auxiliary assets
        has_scripts = any(skill_dir.glob("*.sh")) or any(skill_dir.glob("scripts/*"))
        has_references = (skill_dir / "references").is_dir()

        entry = {
            "name": skill_name,
            "dir_name": skill_dir.name,
            "path": str(skill_dir.resolve()),
            "description": meta.get("description", ""),
            "has_scripts": has_scripts,
            "has_references": has_references,
        }

        if skill_name in skills:
            # Prefer path inside a 'skills' folder
            if "skills" in rel_parts:
                skills[skill_name] = entry
        else:
            skills[skill_name] = entry

    # 2. Discover MCP Servers
    mcp_patterns = [
        "mcp.json",
        "mcp-servers.json",
        "server.json",
        "servers.json",
        "servers.yaml",
        "servers.yml",
        "agal-mcp.yaml",
        "agal-mcp.json",
    ]
    for pattern in mcp_patterns:
        for manifest_file in source_dir.rglob(pattern):
            try:
                rel_parts = manifest_file.relative_to(source_dir).parts
            except ValueError:
                rel_parts = manifest_file.parts

            if any(p.startswith(".") and p != "." for p in rel_parts[:-1]):
                continue
            if any(p in ["node_modules", "vendor", "__pycache__"] for p in rel_parts):
                continue

            parsed = parse_mcp_manifest(manifest_file)
            for sname, sconfig in parsed.items():
                if sname not in mcp_servers:
                    server_entry = {
                        "name": sname,
                        "manifest_path": str(manifest_file.resolve()),
                        "config": sconfig,
                        "description": sconfig.get("description", ""),
                    }
                    if "raw_name" in sconfig:
                        server_entry["raw_name"] = sconfig["raw_name"]
                    if "package" in sconfig:
                        server_entry["package"] = sconfig["package"]
                    mcp_servers[sname] = server_entry

    # Also detect MCP server if pyproject.toml defines mcp dependencies & CLI scripts
    pyproject_file = source_dir / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            txt = pyproject_file.read_text(encoding="utf-8")
            if "mcp" in txt and ("optional-dependencies" in txt or "dependencies" in txt):
                for line in txt.splitlines():
                    if "=" in line and ("__main__" in line or "main" in line or "cli" in line):
                        cmd_name = line.split("=")[0].strip().strip("\"'")
                        if cmd_name and cmd_name not in mcp_servers:
                            mcp_servers[cmd_name] = {
                                "name": cmd_name,
                                "manifest_path": str(pyproject_file.resolve()),
                                "config": {
                                    "command": cmd_name,
                                    "args": ["--mcp"],
                                    "description": f"{cmd_name} MCP server",
                                },
                                "description": f"{cmd_name} MCP server",
                            }
                            break
        except Exception:
            pass

    # Also detect MCP server if package.json defines MCP dependencies & CLI scripts
    package_json = source_dir / "package.json"
    if package_json.is_file() and not mcp_servers:
        try:
            import json
            pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = pkg_data.get("dependencies", {})
            dev_deps = pkg_data.get("devDependencies", {})
            is_mcp = (
                "@modelcontextprotocol/sdk" in deps
                or "@modelcontextprotocol/sdk" in dev_deps
                or "mcpName" in pkg_data
                or "mcp" in pkg_data.get("keywords", [])
            )
            if is_mcp:
                pkg_name = pkg_data.get("name", "")
                sname = pkg_name.split("/")[-1] if "/" in pkg_name else pkg_name
                if not sname:
                    sname = source_dir.name
                if sname not in mcp_servers:
                    mcp_servers[sname] = {
                        "name": sname,
                        "manifest_path": str(package_json.resolve()),
                        "config": {
                            "command": "npx",
                            "args": ["-y", pkg_name] if pkg_name else ["node", "index.js"],
                            "description": pkg_data.get("description", f"{sname} MCP server"),
                        },
                        "description": pkg_data.get("description", f"{sname} MCP server"),
                        "raw_name": pkg_data.get("mcpName", pkg_name),
                        "package": pkg_name,
                    }
        except Exception:
            pass

    # 3. Discover Hooks
    hooks_dir = source_dir / "hooks"
    if hooks_dir.is_dir():
        for hook_file in hooks_dir.iterdir():
            if hook_file.is_file() and not hook_file.name.startswith("."):
                hooks.append({
                    "name": hook_file.name,
                    "path": str(hook_file.resolve()),
                    "executable": os.access(hook_file, os.X_OK),
                })

    return {
        "skills": skills,
        "mcp_servers": mcp_servers,
        "hooks": hooks,
    }


def add_source(url: str, name: str | None = None, branch: str = "main",
               cfg: dict[str, Any] | None = None,
               install_tools: bool | None = None,
               force: bool = False) -> dict[str, Any]:
    """
    Clones a git repo into ~/.agal/sources/<name> and indexes its contents.
    Prompts before installing CLI tools if present.
    """
    if cfg is None:
        cfg = load_config()

    source_name = name or derive_source_name(url)
    sources_dir = get_sources_dir(cfg)
    target_path = sources_dir / source_name

    if target_path.exists():
        if force:
            remove_source(source_name, cfg=cfg)
        else:
            raise FileExistsError(f"Source directory already exists: {target_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Git clone
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, str(target_path)])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Retry without --branch if specific branch failed
        if branch:
            cmd = ["git", "clone", "--depth", "1", url, str(target_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository {url}: {res.stderr.strip()}")

    # Determine head commit
    head_commit = ""
    try:
        head_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=target_path, text=True
        ).strip()
    except Exception:
        pass

    # Index contents
    indexed = index_source_dir(target_path)

    # Check for executable CLI tools
    available_tools = detect_source_binaries(target_path)
    installed_binaries: list[str] = []

    if available_tools:
        tools_str = ", ".join(f"'{t}'" for t in available_tools)
        should_install = False

        if install_tools is True:
            should_install = True
            print(f"\n⚡ Detected CLI tool(s): {tools_str}")
            print(f"   Installing into isolated environment (~/.agal/venv) (--yes flag)...")
        elif install_tools is False:
            should_install = False
            print(f"\n⚡ Detected CLI tool(s): {tools_str}")
            print(f"   ⏭️  Skipped tool installation (--no-tools flag).")
            print(f"       You can install them anytime with: agal source install-tools {source_name}")
        elif sys.stdin.isatty():
            print(f"\n⚡ Detected executable CLI tool(s): {tools_str}")
            print(f"   ℹ️  This repository includes CLI binaries needed to execute its skills/MCP servers.")
            print(f"   📦 Installation target: isolated environment (~/.agal/venv)")
            print(f"   🔗 Symlink destination: ~/.local/bin (no system pollution)")
            try:
                ans = input(f"   Install {tools_str} now? [Y/n]: ").strip().lower()
                should_install = ans in ("", "y", "yes", "t", "tak")
            except (EOFError, KeyboardInterrupt):
                should_install = False
                print()

            if not should_install:
                print(f"   ⏭️  Skipped tool installation.")
                print(f"       You can install them anytime with: agal source install-tools {source_name}")
        else:
            should_install = False
            print(f"\n⚡ Detected CLI tool(s): {tools_str} (skipped in non-interactive mode)")
            print(f"   Run 'agal source install-tools {source_name}' to install.")

        if should_install:
            print(f"   ⚙️  Installing {tools_str} into ~/.agal/venv...")
            installed_binaries = install_source_binaries(target_path)
            if installed_binaries:
                print(f"   ✅ Successfully linked {', '.join(installed_binaries)} to ~/.local/bin")
            else:
                print(f"   ⚠️  Installation completed but no binaries were linked.")

    # Save to registry
    sources = load_sources_registry()
    sources[source_name] = {
        "url": url,
        "branch": branch,
        "path": str(target_path.resolve()),
        "added_at": datetime.datetime.now().isoformat(),
        "last_checked": datetime.datetime.now().isoformat(),
        "head_commit": head_commit,
        "skills_count": len(indexed["skills"]),
        "mcp_count": len(indexed["mcp_servers"]),
        "hooks_count": len(indexed["hooks"]),
        "binaries": installed_binaries,
    }
    save_sources_registry(sources)

    return {
        "name": source_name,
        "path": target_path,
        "url": url,
        "head_commit": head_commit,
        "indexed": indexed,
        "binaries": installed_binaries,
        "available_tools": available_tools,
    }


def detect_source_binaries(source_path: Path) -> list[str]:
    """Inspects source_path to see what CLI tools/binaries it provides."""
    binaries: list[str] = []
    pyproject = source_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            if tomllib:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                scripts = data.get("project", {}).get("scripts", {})
                if isinstance(scripts, dict):
                    for k in scripts.keys():
                        if k and k not in binaries:
                            binaries.append(k)
                poetry_scripts = data.get("tool", {}).get("poetry", {}).get("scripts", {})
                if isinstance(poetry_scripts, dict):
                    for k in poetry_scripts.keys():
                        if k not in binaries:
                            binaries.append(k)
                if not binaries:
                    pname = data.get("project", {}).get("name")
                    if pname and (source_path / pname / "__main__.py").is_file():
                        binaries.append(pname)
            else:
                txt = pyproject.read_text(encoding="utf-8")
                in_scripts = False
                for line in txt.splitlines():
                    striped = line.strip()
                    if striped.startswith("[") and striped.endswith("]"):
                        in_scripts = "scripts" in striped.lower()
                    elif in_scripts and "=" in striped and not striped.startswith("#"):
                        candidate = striped.split("=")[0].strip().strip("\"' ")
                        if candidate and candidate not in binaries:
                            binaries.append(candidate)
        except Exception:
            pass

    setup_py = source_path / "setup.py"
    if setup_py.is_file() and not binaries:
        try:
            txt = setup_py.read_text(encoding="utf-8")
            m = re.search(r"['\"]?console_scripts['\"]?\s*[:=]\s*\[(.*?)\]", txt, re.DOTALL)
            if m:
                for entry in m.group(1).split(","):
                    if "=" in entry:
                        bname = entry.split("=")[0].strip().strip("'\" ")
                        if bname and bname not in binaries:
                            binaries.append(bname)
        except Exception:
            pass

    return binaries


def install_source_binaries(source_path: Path) -> list[str]:
    """
    If source_path is a Python package (has pyproject.toml or setup.py),
    installs it into ~/.agal/venv and creates symlinks for entrypoint binaries in ~/.local/bin.
    """
    if not (source_path / "pyproject.toml").is_file() and not (source_path / "setup.py").is_file():
        return []

    venv_dir = get_agal_home() / "venv"
    if not venv_dir.is_dir():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=False)

    pip_bin = venv_dir / "bin" / "pip"
    bin_dir = venv_dir / "bin"
    if not pip_bin.is_file():
        return []

    before_bins = set(bin_dir.iterdir()) if bin_dir.is_dir() else set()

    # Install package into managed venv
    res = subprocess.run([str(pip_bin), "install", "-e", str(source_path)], capture_output=True, text=True)
    if res.returncode != 0:
        res = subprocess.run([str(pip_bin), "install", str(source_path)], capture_output=True, text=True)
        if res.returncode != 0:
            return []

    after_bins = set(bin_dir.iterdir()) if bin_dir.is_dir() else set()
    new_bins = [b for b in (after_bins - before_bins) if b.name not in ("python", "python3", "pip", "pip3", "agal")]

    # Also check scripts defined in pyproject.toml
    for candidate_name in detect_source_binaries(source_path):
        cand_path = bin_dir / candidate_name
        if cand_path.is_file() and cand_path not in new_bins:
            new_bins.append(cand_path)

    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    installed_names = []
    for b in new_bins:
        dest = local_bin / b.name
        if dest.is_symlink() or dest.exists():
            dest.unlink(missing_ok=True)
        dest.symlink_to(b.resolve())
        installed_names.append(b.name)

    return installed_names


def uninstall_source_binaries(binaries: list[str]) -> None:
    local_bin = Path.home() / ".local" / "bin"
    for b in binaries:
        p = local_bin / b
        if p.is_symlink() or p.exists():
            p.unlink(missing_ok=True)


def remove_source(name: str, cfg: dict[str, Any] | None = None) -> bool:
    """Removes a source directory and deregisters it."""
    if cfg is None:
        cfg = load_config()

    sources = load_sources_registry()
    if name not in sources:
        sources_dir = get_sources_dir(cfg)
        path = sources_dir / name
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return True
        return False

    source_info = sources[name]
    bins = source_info.get("binaries", [])
    if bins:
        uninstall_source_binaries(bins)

    path = Path(source_info.get("path", get_sources_dir(cfg) / name))
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)

    del sources[name]
    save_sources_registry(sources)
    return True


def list_sources(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Returns a list of all registered sources with current indexed counts."""
    if cfg is None:
        cfg = load_config()

    sources = load_sources_registry()
    result = []
    for name, data in sources.items():
        entry = dict(data)
        entry["name"] = name
        path = Path(data.get("path", get_sources_dir(cfg) / name))
        if path.is_dir():
            indexed = index_source_dir(path)
            entry["skills_count"] = len(indexed["skills"])
            entry["mcp_count"] = len(indexed["mcp_servers"])
            entry["hooks_count"] = len(indexed["hooks"])
        result.append(entry)
    return result


def get_all_skills(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """
    Returns mapping of skill_name -> skill_info across all sources.
    Also falls back to bundled skills if configured.
    """
    if cfg is None:
        cfg = load_config()

    sources = list_sources(cfg)
    all_skills: dict[str, dict[str, Any]] = {}

    for src in sources:
        src_path = Path(src["path"])
        if not src_path.is_dir():
            continue
        indexed = index_source_dir(src_path)
        for sname, sinfo in indexed["skills"].items():
            sentry = dict(sinfo)
            sentry["source"] = src["name"]
            all_skills[sname] = sentry

    # Backward compatibility: if a custom skills_dir or bundled Skills/ exists
    bundled_skills_dir = None
    if cfg.get("skills_dir"):
        bundled_skills_dir = Path(cfg["skills_dir"]).expanduser()
    elif (Path(__file__).parent.parent / "Skills").is_dir():
        bundled_skills_dir = (Path(__file__).parent.parent / "Skills").resolve()

    if bundled_skills_dir and bundled_skills_dir.is_dir():
        for skill_file in bundled_skills_dir.rglob("SKILL.md"):
            skill_dir = skill_file.parent
            meta = parse_skill_frontmatter(skill_file)
            sname = meta.get("name") or skill_dir.name
            if sname not in all_skills:
                all_skills[sname] = {
                    "name": sname,
                    "dir_name": skill_dir.name,
                    "path": str(skill_dir.resolve()),
                    "description": meta.get("description", ""),
                    "has_scripts": any(skill_dir.glob("*.sh")),
                    "has_references": (skill_dir / "references").is_dir(),
                    "source": "bundled",
                }

    return all_skills


def get_all_mcp_servers(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Returns mapping of server_name -> mcp_info across all sources."""
    if cfg is None:
        cfg = load_config()

    sources = list_sources(cfg)
    all_mcp: dict[str, dict[str, Any]] = {}

    for src in sources:
        src_path = Path(src["path"])
        if not src_path.is_dir():
            continue
        indexed = index_source_dir(src_path)
        for sname, sinfo in indexed["mcp_servers"].items():
            entry = dict(sinfo)
            entry["source"] = src["name"]
            all_mcp[sname] = entry

    return all_mcp


def get_all_hooks(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Returns mapping of hook_name -> hook_info across all sources."""
    if cfg is None:
        cfg = load_config()

    sources = list_sources(cfg)
    all_hooks: dict[str, dict[str, Any]] = {}

    for src in sources:
        src_path = Path(src["path"])
        if not src_path.is_dir():
            continue
        indexed = index_source_dir(src_path)
        for hinfo in indexed["hooks"]:
            entry = dict(hinfo)
            entry["source"] = src["name"]
            all_hooks[hinfo["name"]] = entry

    return all_hooks
