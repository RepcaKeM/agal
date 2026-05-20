#!/usr/bin/env python3
"""
agal — Agent Agnostic Launch  (v2)
Manages skill presets for Claude Code, Gemini CLI, and Kimi CLI.
Uses symlinking to .agents/skills/ and .claude/skills/ instead of
injecting content into context files.

Each CLI loads only skill names + descriptions on startup — the full
SKILL.md content is fetched only when the agent decides the task matches.

Usage:
  agal                          # interactive launcher (fzf)
  agal <preset>                 # choose CLI interactively
  agal <preset> <cli>           # launch directly
  agal -l / --list              # list presets
  agal -n / --new  <name>       # new preset (fzf multi-select)
  agal -e / --edit <name>       # edit preset in $EDITOR
  agal -i / --info <name>       # preset details
  agal -p / --prepare <preset>  # create symlinks in cwd (multi-CLI mode)
  agal -u / --unprepare         # remove symlinks from cwd
  agal -s / --status            # show active preset in cwd
  agal -k / --check             # check skill frontmatter
  agal -V / --validate <name>   # check preset completeness
  agal -r / --remote            # modifier: copy instead of symlinking
  agal -c / --config            # open config in $EDITOR

Env vars:
  AGAL_CONFIG=path/to/config.yaml   # override config location (per-project)

Requirements:
  pip install pyyaml --break-system-packages
  sudo apt install fzf          # optional but recommended
"""

import os
import re
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌  pip install pyyaml --break-system-packages")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
# AGAL_CONFIG env var overrides the config.yaml location.
# Useful for per-project configs (e.g. .agal/config.yaml in a repo) instead of the global ~/.agal.

CONFIG_FILE = Path(os.environ.get("AGAL_CONFIG") or (Path.home() / ".agal" / "config.yaml")).expanduser()
CONFIG_DIR  = CONFIG_FILE.parent
PRESETS_DIR = CONFIG_DIR / "presets"  # overridable via `presets_dir` in config.yaml

# Skill directories created inside the project — covers all 3 CLIs
SKILL_DIRS = [
    ".agents/skills",   # Gemini CLI + Kimi CLI (open Agent Skills standard)
    ".claude/skills",   # Claude Code + Kimi CLI
]

AGAL_MARKER_FILE = ".agal_managed"   # marker file in each directory created by agal

# Context files (coding guidelines) created in the project root.
# Each CLI reads a different filename; AGENTS.md is the open standard (Gemini/Kimi).
CONTEXT_FILENAMES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "KIMI.md"]
AGAL_CONTEXT_MARKER = ".agal_context"   # list of context files created by agal

# Locate default skills directory: prefer bundled Skills/ if present, fallback to ~/.agal/src/Skills or ~/my-skills
script_dir = Path(__file__).resolve().parent
if (script_dir / "Skills").is_dir():
    DEFAULT_SKILLS_DIR = (script_dir / "Skills").resolve()
elif (Path.home() / ".agal" / "src" / "Skills").is_dir():
    DEFAULT_SKILLS_DIR = (Path.home() / ".agal" / "src" / "Skills").resolve()
else:
    DEFAULT_SKILLS_DIR = Path.home() / "my-skills"

DEFAULT_CONFIG = {
    # Directory containing your library of 200+ .md skill files
    "skills_dir": str(DEFAULT_SKILLS_DIR),
    # CLI binary names
    "clis": {
        "claude": "claude",
        "gemini": "gemini",
        "kimi":   "kimi",
    },
    # Whether to remove symlinks after the session ends in launch mode
    "cleanup_after_launch": True,
    # Meta-preset merged into every preset (None = disabled).
    # Core skills are loaded BEFORE preset skills, deduplicated.
    "core_preset": "dev-workflow-core",
    # Coding guidelines file (AGENTS.md). With --prepare it is placed in the
    # project root as AGENTS.md + CLAUDE.md/GEMINI.md/KIMI.md (symlink or copy
    # with --remote). None = disabled (back-compat).
    "context_file": None,
}

# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    global PRESETS_DIR
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            yaml.dump(DEFAULT_CONFIG, allow_unicode=True, default_flow_style=False)
        )
        print(f"✅  Created default config: {CONFIG_FILE}")
        print(f"    Set skills_dir to your skills library directory.\n")
    user = yaml.safe_load(CONFIG_FILE.read_text()) or {}
    # Merge with DEFAULT_CONFIG — missing keys get defaults (e.g. core_preset)
    merged = {**DEFAULT_CONFIG, **user}
    # If the configured skills_dir doesn't exist but the bundled one does, auto-fallback
    skills_path = Path(merged.get("skills_dir", "")).expanduser()
    if not skills_path.is_dir() and DEFAULT_SKILLS_DIR.is_dir():
        merged["skills_dir"] = str(DEFAULT_SKILLS_DIR)
    # presets_dir from config overrides the default (CONFIG_DIR/presets)
    if merged.get("presets_dir"):
        PRESETS_DIR = Path(merged["presets_dir"]).expanduser()
    return merged


def load_preset(name: str) -> dict:
    path = PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in PRESETS_DIR.glob("*.yaml"))
        print(f"❌  Preset '{name}' not found.")
        if available:
            print(f"    Available: {', '.join(available)}")
        sys.exit(1)
    return yaml.safe_load(path.read_text())


def resolve_skills(preset: dict, preset_name: str, config: dict) -> tuple[list[str], int]:
    """
    Returns (skill list, count added from core_preset).
    Core skills before preset skills, deduplicated (first wins).
    """
    core_name = config.get("core_preset")
    skills: list[str] = []
    seen: set[str] = set()
    core_added = 0

    if core_name and preset_name != core_name:
        core_path = PRESETS_DIR / f"{core_name}.yaml"
        if core_path.exists():
            core = yaml.safe_load(core_path.read_text()) or {}
            for s in core.get("skills", []):
                if s not in seen:
                    skills.append(s)
                    seen.add(s)
                    core_added += 1
        else:
            print(f"  ⚠️   core_preset '{core_name}' not found, skipping meta-skills")

    for s in preset.get("skills", []):
        if s not in seen:
            skills.append(s)
            seen.add(s)

    return skills, core_added

# ── Interaction (fzf / fallback menu) ────────────────────────────────────────

def _has_fzf() -> bool:
    return bool(shutil.which("fzf"))


def pick_one(options: list[str], prompt: str = "Select") -> str | None:
    if not options:
        return None
    if _has_fzf():
        r = subprocess.run(
            ["fzf", "--prompt", f"{prompt}: ", "--height", "40%", "--border"],
            input="\n".join(options), capture_output=True, text=True,
        )
        return r.stdout.strip() or None
    for i, o in enumerate(options, 1):
        print(f"  {i:>3}. {o}")
    try:
        return options[int(input(f"{prompt} (number): ")) - 1]
    except (ValueError, IndexError, EOFError):
        return None


def _list_skill_names(path: Path) -> list[str]:
    """Subdirs with SKILL.md (Anthropic standard) + flat .md (legacy)."""
    names = []
    for d in sorted(path.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            names.append(d.name)
    names += sorted(f.name for f in path.glob("*.md"))
    return names


def pick_skills_multi(skills_dir: str) -> list[str]:
    path = Path(skills_dir).expanduser()
    if not path.exists():
        print(f"❌  skills_dir not found: {path}")
        print(f"    Set it in {CONFIG_FILE}")
        sys.exit(1)
    names = _list_skill_names(path)
    if not names:
        print(f"❌  No skills found (no subdirs with SKILL.md or .md files) in {path}")
        sys.exit(1)

    if _has_fzf():
        # Preview: if dir → cat SKILL.md, if flat file → cat file
        preview = (
            f"if [ -d '{path}/{{}}' ]; then "
            f"  cat '{path}/{{}}/SKILL.md' 2>/dev/null; "
            f"else cat '{path}/{{}}' 2>/dev/null; fi"
        )
        r = subprocess.run(
            ["fzf", "--multi",
             "--prompt", "Skills (TAB=select, ENTER=confirm): ",
             "--height", "80%", "--border",
             "--preview", preview,
             "--preview-window", "right:50%:wrap",
             "--header", f"{len(names)} skills in {path.name}/"],
            input="\n".join(names), capture_output=True, text=True,
        )
        return [s for s in r.stdout.strip().split("\n") if s] if r.returncode == 0 else []

    print(f"\nAvailable skills ({path}):")
    for i, n in enumerate(names, 1):
        print(f"  {i:>3}. {n}")
    raw = input("\nNames or numbers (comma-separated): ")
    result = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit():
            idx = int(tok) - 1
            if 0 <= idx < len(names):
                result.append(names[idx])
        elif tok:
            result.append(tok)
    return result

# ── Preset management ─────────────────────────────────────────────────────────

def list_presets() -> None:
    presets = sorted(PRESETS_DIR.glob("*.yaml"))
    if not presets:
        print("No presets found. Create one: agal --new <name>")
        return
    print(f"\n{'Preset':<22} {'Skills':>6}  Description")
    print("─" * 58)
    for p in presets:
        try:
            d = yaml.safe_load(p.read_text())
            print(f"  {p.stem:<20} {len(d.get('skills', [])):>5}  {d.get('description', '')}")
        except Exception:
            print(f"  {p.stem:<20}   ???  (parse error)")
    print()


def show_info(name: str, config: dict) -> None:
    d = load_preset(name)
    print(f"\nPreset      : {name}")
    print(f"Description : {d.get('description', '—')}")
    if d.get("notes"):
        print(f"Notes       : {d['notes']}")
    own = d.get("skills", [])
    print(f"Own skills ({len(own)}):")
    for s in own:
        print(f"  - {s}")

    core_name = config.get("core_preset")
    if core_name and name != core_name:
        core_path = PRESETS_DIR / f"{core_name}.yaml"
        if core_path.exists():
            core = yaml.safe_load(core_path.read_text()) or {}
            extra = [s for s in core.get("skills", []) if s not in own]
            if extra:
                print(f"\n+ Auto-merged from '{core_name}' ({len(extra)} extra):")
                for s in extra:
                    print(f"  · {s}")
    print()


def new_preset(name: str, config: dict) -> None:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PRESETS_DIR / f"{name}.yaml"
    if dest.exists():
        if input(f"Preset '{name}' already exists. Overwrite? [y/N] ").strip().lower() != "y":
            return
    desc  = input("Description (optional): ").strip()
    notes = input("Notes/instructions (optional): ").strip()
    print()
    selected = pick_skills_multi(config.get("skills_dir", str(DEFAULT_SKILLS_DIR)))
    if not selected:
        print("Nothing selected.")
        return
    data: dict = {"name": name, "skills": selected}
    if desc:  data["description"] = desc
    if notes: data["notes"] = notes
    dest.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"\n✅  Preset '{name}' saved ({len(selected)} skills) → {dest}")


def validate_preset(name: str, config: dict) -> None:
    """Checks that all skills in the preset (after resolve) exist and have frontmatter."""
    preset = load_preset(name)
    skills, core_added = resolve_skills(preset, name, config)
    skills_dir = Path(config.get("skills_dir", str(DEFAULT_SKILLS_DIR))).expanduser()

    own = len(skills) - core_added
    print(f"\n🔎  Validating '{name}': {len(skills)} skills ({own} own + {core_added} core)\n")

    missing = []
    bad_frontmatter = []
    ok = 0

    for entry in skills:
        stem  = _skill_stem(entry)
        sdir  = skills_dir / stem
        sflat = skills_dir / f"{stem}.md"

        if sdir.is_dir() and (sdir / "SKILL.md").exists():
            target = sdir / "SKILL.md"
        elif sflat.is_file():
            target = sflat
        else:
            missing.append(entry)
            continue

        text = target.read_text(encoding="utf-8", errors="replace")
        has_name, has_desc = _has_frontmatter(text)
        if has_name and has_desc:
            ok += 1
        else:
            problems = []
            if not has_name: problems.append("name")
            if not has_desc: problems.append("description")
            bad_frontmatter.append((entry, problems))

    print(f"  ✅  OK: {ok}/{len(skills)}")
    if missing:
        print(f"  ❌  Missing in skills_dir ({len(missing)}):")
        for m in missing: print(f"       - {m}")
    if bad_frontmatter:
        print(f"  ⚠️   Missing frontmatter ({len(bad_frontmatter)}):")
        for e, p in bad_frontmatter: print(f"       - {e}  (missing: {', '.join(p)})")
    if not missing and not bad_frontmatter:
        print(f"\n  Preset is ready to use.\n")
    else:
        print()
        sys.exit(1)


def edit_preset(name: str) -> None:
    path = PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        print(f"❌  Preset '{name}' not found.")
        sys.exit(1)
    subprocess.run([os.environ.get("EDITOR", "nano"), str(path)])

# ── Frontmatter check ─────────────────────────────────────────────────────────

def _has_frontmatter(text: str) -> tuple[bool, bool]:
    """Returns (has_name, has_description)."""
    if not text.startswith("---"):
        return False, False
    end = text.find("\n---", 3)
    if end == -1:
        return False, False
    fm_block = text[3:end]
    return ("name:" in fm_block), ("description:" in fm_block)


def check_skills(config: dict) -> None:
    skills_dir = Path(config.get("skills_dir", str(DEFAULT_SKILLS_DIR))).expanduser()
    # Subdirs with SKILL.md + flat .md (legacy)
    files = []
    for d in sorted(skills_dir.iterdir()) if skills_dir.exists() else []:
        if d.is_dir() and (d / "SKILL.md").exists():
            files.append(d / "SKILL.md")
    files += sorted(skills_dir.glob("*.md"))
    if not files:
        print(f"No skills found in {skills_dir}")
        return

    ok = bad_name = bad_desc = bad_both = 0
    issues = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        has_name, has_desc = _has_frontmatter(text)
        # Display name: dir name for subdir, filename for flat
        display = f.parent.name if f.name == "SKILL.md" else f.name
        if has_name and has_desc:
            ok += 1
        else:
            missing = []
            if not has_name:  missing.append("name")
            if not has_desc:  missing.append("description")
            issues.append((display, missing))
            if not has_name and not has_desc: bad_both += 1
            elif not has_name: bad_name += 1
            else: bad_desc += 1

    print(f"\n📊  Results for {skills_dir} ({len(files)} files):")
    print(f"  ✅  OK (name + description): {ok}")
    print(f"  ⚠️   Missing description:    {bad_desc}")
    print(f"  ⚠️   Missing name:           {bad_name}")
    print(f"  ❌  Missing both:            {bad_both}")

    if issues:
        print(f"\n  Files requiring frontmatter (Gemini won't load them):")
        for fname, missing in issues[:20]:
            print(f"    {fname:<40} missing: {', '.join(missing)}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        print(f"""
  Required frontmatter format at the top of each SKILL.md:

    ---
    name: skill-name
    description: When and why to use this skill. The more specific, the better.
    ---
""")

# ── Symlinks — core of agal ───────────────────────────────────────────────────

def _skill_stem(filename: str) -> str:
    """typescript.md → typescript"""
    return Path(filename).stem


def _create_skill_symlinks(skills_list: list[str], skills_dir: Path,
                           target_dir: Path, copy: bool = False) -> list[str]:
    """
    For each skill creates:

    Symlink mode (default):
      target_dir/.agents/skills/<stem>  →  skills_dir/<stem>   (dir symlink)

    Copy mode (--remote):
      target_dir/.agents/skills/<stem>/  ← full contents copied, no symlinks
      Portable project — works after cloning on another machine without agal/skills_dir.

    Legacy flat .md in both modes: dest_dir/<stem>/SKILL.md.

    Returns list of missing skills.
    """
    missing = []

    for skill_entry in skills_list:
        stem = _skill_stem(skill_entry)

        src_dir  = skills_dir / stem
        src_flat = skills_dir / f"{stem}.md"

        if src_dir.is_dir() and (src_dir / "SKILL.md").exists():
            src_mode = "dir"
            src      = src_dir
        elif src_flat.is_file():
            src_mode = "flat"
            src      = src_flat
        else:
            missing.append(skill_entry)
            continue

        for skill_subdir in SKILL_DIRS:
            parent = target_dir / skill_subdir
            parent.mkdir(parents=True, exist_ok=True)
            dest = parent / stem

            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            elif dest.is_dir():
                shutil.rmtree(dest)

            if src_mode == "dir":
                if copy:
                    shutil.copytree(src, dest, symlinks=False)
                else:
                    dest.symlink_to(src.resolve(), target_is_directory=True)
            else:  # flat .md
                dest.mkdir()
                if copy:
                    shutil.copy2(src, dest / "SKILL.md")
                else:
                    (dest / "SKILL.md").symlink_to(src.resolve())

    return missing


def _mark_as_managed(target_dir: Path, preset_name: str, copy: bool = False) -> None:
    mode = "copy" if copy else "symlink"
    for skill_subdir in SKILL_DIRS:
        d = target_dir / skill_subdir
        if d.exists():
            (d / AGAL_MARKER_FILE).write_text(f"preset:{preset_name}\nmode:{mode}\n")


def _is_managed(target_dir: Path) -> tuple[str, str] | None:
    """Returns (preset_name, mode) if the directory is managed by agal."""
    for skill_subdir in SKILL_DIRS:
        marker = target_dir / skill_subdir / AGAL_MARKER_FILE
        if marker.exists():
            text = marker.read_text()
            m = re.search(r"preset:(.+)", text)
            mode_m = re.search(r"mode:(.+)", text)
            return (
                m.group(1).strip() if m else "unknown",
                mode_m.group(1).strip() if mode_m else "symlink",
            )
    return None


def _remove_skill_symlinks(target_dir: Path) -> None:
    removed = 0
    for skill_subdir in SKILL_DIRS:
        d = target_dir / skill_subdir
        if not d.exists():
            continue
        if not (d / AGAL_MARKER_FILE).exists():
            print(f"  ⏭️   {d} — not managed by agal, skipping")
            continue
        shutil.rmtree(d)
        removed += 1
        print(f"  🧹  Removed {d}")
    if removed == 0:
        print("  Nothing to remove — no directories managed by agal.")

# ── Context files (coding guidelines) ────────────────────────────────────────

def _place_context_file(target_dir: Path, context_path: Path,
                        copy: bool = False) -> list[str]:
    """
    Creates AGENTS.md + CLAUDE/GEMINI/KIMI.md in the project root (symlink or copy).

    Does not overwrite existing files that agal did not create (protects the
    user's own CLAUDE.md). The list of created names is written to .agal_context.
    Returns list of skipped names (already exist, not ours).
    """
    src = context_path.expanduser()
    if not src.is_file():
        print(f"  ⚠️   context_file not found: {src} — skipping guidelines")
        return []

    marker = target_dir / AGAL_CONTEXT_MARKER
    prev = set(marker.read_text().split()) if marker.exists() else set()

    created, skipped = [], []
    for fname in CONTEXT_FILENAMES:
        dest = target_dir / fname
        if dest.exists() or dest.is_symlink():
            if fname in prev:
                dest.unlink()              # ours from a previous prepare — refresh
            else:
                skipped.append(fname)      # user's file — leave it alone
                continue
        if copy:
            shutil.copy2(src, dest)
        else:
            dest.symlink_to(src.resolve())
        created.append(fname)

    marker.write_text("\n".join(created) + "\n" if created else "")
    return skipped


def _remove_context_file(target_dir: Path) -> None:
    marker = target_dir / AGAL_CONTEXT_MARKER
    if not marker.exists():
        return
    for fname in marker.read_text().split():
        f = target_dir / fname
        if f.exists() or f.is_symlink():
            f.unlink()
    marker.unlink()


# ── Prepare / Unprepare / Status ──────────────────────────────────────────────

def prepare(preset_name: str, config: dict, target_dir: Path | None = None,
            copy: bool = False) -> None:
    target     = (target_dir or Path.cwd()).resolve()
    preset     = load_preset(preset_name)
    skills_dir = Path(config.get("skills_dir", str(DEFAULT_SKILLS_DIR))).expanduser()
    skills, core_added = resolve_skills(preset, preset_name, config)
    own = len(skills) - core_added
    mode_label = "📋 copy (remote/portable)" if copy else "🔗 symlink"

    if core_added:
        print(f"\n📦  Preset '{preset_name}' ({own} own + {core_added} from core) — {mode_label} in {target}\n")
    else:
        print(f"\n📦  Preset '{preset_name}' ({own} skills) — {mode_label} in {target}\n")

    existing = _is_managed(target)
    if existing:
        prev_name, prev_mode = existing
        print(f"  ♻️   Replacing previous preset: {prev_name} ({prev_mode})")
        _remove_skill_symlinks(target)

    missing = _create_skill_symlinks(skills, skills_dir, target, copy=copy)
    _mark_as_managed(target, preset_name, copy=copy)

    ctx = config.get("context_file")
    if ctx:
        skipped = _place_context_file(target, Path(ctx), copy=copy)
        placed = [f for f in CONTEXT_FILENAMES if f not in skipped]
        if placed:
            print(f"  📄  Guidelines: {', '.join(placed)}")
        if skipped:
            print(f"  ⏭️   Skipped (existing, not agal's): {', '.join(skipped)}")

    if missing:
        print(f"  ⚠️   Missing files: {', '.join(missing)}")

    print(f"  ✅  Done:")
    for skill_subdir in SKILL_DIRS:
        d = target / skill_subdir
        if d.exists():
            n = sum(1 for p in d.iterdir() if p.name != AGAL_MARKER_FILE)
            print(f"       {d.relative_to(target)}  ({n} skills)")

    print(f"""
  Claude Code reads  : .claude/skills/
  Gemini CLI reads   : .agents/skills/
  Kimi CLI reads     : both of the above

  Agents load only skill names on startup.
  Full content — only when it matches the task.

  Switch preset : agal --prepare <other>
  Remove links  : agal --unprepare
""")


def unprepare(config: dict, target_dir: Path | None = None) -> None:
    target = (target_dir or Path.cwd()).resolve()
    print(f"\n🧹  Removing agal symlinks from {target}\n")
    _remove_skill_symlinks(target)
    _remove_context_file(target)
    print()


def show_status(config: dict, target_dir: Path | None = None) -> None:
    target = (target_dir or Path.cwd()).resolve()
    info = _is_managed(target)

    if not info:
        print(f"\n  No active preset in {target}")
        print(f"  Use: agal --prepare <preset>\n")
        return

    preset, mode = info
    print(f"\n  Active preset: {preset}  [{mode}]  ({target})\n")
    ctx_marker = target / AGAL_CONTEXT_MARKER
    if ctx_marker.exists():
        ctx_files = ctx_marker.read_text().split()
        if ctx_files:
            print(f"  Guidelines: {', '.join(ctx_files)}\n")
    for skill_subdir in SKILL_DIRS:
        d = target / skill_subdir
        if not d.exists():
            continue
        names = sorted(
            p.name for p in d.iterdir()
            if p.name != AGAL_MARKER_FILE and (p.is_symlink() or p.is_dir())
        )
        print(f"  {skill_subdir}/  ({len(names)} skills)")
        for name in names:
            print(f"    · {name}")
    print()

# ── Launch (pure CLI) ─────────────────────────────────────────────────────────

def launch(preset_name: str, cli_name: str, config: dict, copy: bool = False) -> None:
    clis       = config.get("clis", {})
    do_cleanup = config.get("cleanup_after_launch", True)

    if cli_name not in clis:
        print(f"❌  Unknown CLI '{cli_name}'. Available: {', '.join(clis)}")
        sys.exit(1)
    cli_cmd = clis[cli_name]
    if not shutil.which(cli_cmd):
        print(f"❌  '{cli_cmd}' not found in PATH.")
        sys.exit(1)

    preset = load_preset(preset_name)
    skills, core_added = resolve_skills(preset, preset_name, config)
    skills_dir = Path(config.get("skills_dir", str(DEFAULT_SKILLS_DIR))).expanduser()
    target = Path.cwd()
    own = len(skills) - core_added

    suffix = f"({own}+{core_added} core)" if core_added else f"({own})"
    mode_label = "📋 copy" if copy else "🔗 symlink"
    print(f"\n🚀  {cli_name}  ·  preset: {preset_name}  ·  {len(skills)} skills {suffix}  ·  {mode_label}\n")

    missing = _create_skill_symlinks(skills, skills_dir, target, copy=copy)
    _mark_as_managed(target, preset_name, copy=copy)
    ctx = config.get("context_file")
    if ctx:
        _place_context_file(target, Path(ctx), copy=copy)
    if missing:
        print(f"⚠️   Missing files: {', '.join(missing)}\n")

    try:
        subprocess.run([cli_cmd], check=False)
    finally:
        if do_cleanup:
            _remove_skill_symlinks(target)
            _remove_context_file(target)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    config = load_config()

    parser = argparse.ArgumentParser(
        description="agal — Agent Agnostic Launch with skill presets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("preset", nargs="?")
    parser.add_argument("cli",    nargs="?")
    parser.add_argument("--list",      "-l", action="store_true")
    parser.add_argument("--new",       "-n", metavar="NAME")
    parser.add_argument("--edit",      "-e", metavar="NAME")
    parser.add_argument("--info",      "-i", metavar="NAME")
    parser.add_argument("--prepare",   "-p", metavar="PRESET",
                        help="Create symlinks in cwd (multi-CLI mode)")
    parser.add_argument("--unprepare", "-u", action="store_true",
                        help="Remove symlinks managed by agal from cwd")
    parser.add_argument("--status",    "-s", action="store_true",
                        help="Show active preset in cwd")
    parser.add_argument("--check",     "-k", action="store_true",
                        help="Check skill file frontmatter")
    parser.add_argument("--validate",  "-V", metavar="PRESET",
                        help="Check whether preset (after core merge) is complete")
    parser.add_argument("--remote",    "-r", action="store_true",
                        help="Copy skill contents instead of symlinking "
                             "(for cloud agents, CI, devcontainers, portable projects)")
    parser.add_argument("--config",    "-c", action="store_true")
    args = parser.parse_args()

    if args.list:      list_presets();            return
    if args.new:       new_preset(args.new, config); return
    if args.edit:      edit_preset(args.edit);    return
    if args.info:      show_info(args.info, config);  return
    if args.prepare:   prepare(args.prepare, config, copy=args.remote); return
    if args.unprepare: unprepare(config);         return
    if args.status:    show_status(config);       return
    if args.check:     check_skills(config);      return
    if args.validate:  validate_preset(args.validate, config); return
    if args.config:
        subprocess.run([os.environ.get("EDITOR", "nano"), str(CONFIG_FILE)])
        return

    # Interactive launch
    preset_name = args.preset
    if not preset_name:
        presets = sorted(p.stem for p in PRESETS_DIR.glob("*.yaml"))
        if not presets:
            print("No presets found. Create one: agal --new <name>")
            sys.exit(1)
        preset_name = pick_one(presets, "Preset")
        if not preset_name: sys.exit(0)

    cli_name = args.cli
    if not cli_name:
        cli_name = pick_one(list(config.get("clis", {}).keys()), "CLI")
        if not cli_name: sys.exit(0)

    launch(preset_name, cli_name, config, copy=args.remote)


if __name__ == "__main__":
    main()
