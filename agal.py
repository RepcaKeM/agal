#!/usr/bin/env python3
"""
agal — Agent Agnostic Launch  (v2)
Zarządza presetami skilli dla Claude Code, Gemini CLI i Kimi CLI.
Używa symlinkowania do .agents/skills/ i .claude/skills/ zamiast
wstrzykiwania treści do plików kontekstowych.

Każdy CLI ładuje tylko nazwy+opisy skilli na starcie — pełna treść
SKILL.md jest pobierana dopiero gdy agent uzna że task pasuje.

Użycie:
  agal                          # interaktywny launcher (fzf)
  agal <preset>                 # wybierz CLI interaktywnie
  agal <preset> <cli>           # uruchom bezpośrednio
  agal -l / --list              # lista presetów
  agal -n / --new  <name>       # nowy preset (fzf multi-select)
  agal -e / --edit <name>       # edytuj preset w $EDITOR
  agal -i / --info <name>       # szczegóły presetu
  agal -p / --prepare <preset>  # utwórz symlinki w cwd (tryb emdash)
  agal -u / --unprepare         # usuń symlinki z cwd
  agal -s / --status            # pokaż aktywny preset w cwd
  agal -k / --check             # sprawdź frontmatter skilli
  agal -V / --validate <name>   # sprawdź czy preset jest kompletny
  agal -r / --remote            # modyfikator: kopiuj zamiast symlinkować
  agal -c / --config            # otwórz config w $EDITOR

Env vars:
  AGAL_CONFIG=path/to/config.yaml   # nadpisz lokalizację configu (per-projekt)

Wymagania:
  pip install pyyaml --break-system-packages
  sudo apt install fzf          # opcjonalnie, ale zalecane
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

# ── Ścieżki ───────────────────────────────────────────────────────────────────
# AGAL_CONFIG env var nadpisuje lokalizację config.yaml.
# Przydatne dla per-projekt configów (np. .agal/config.yaml w repo) zamiast globalnego ~/.agal.

CONFIG_FILE = Path(os.environ.get("AGAL_CONFIG") or (Path.home() / ".agal" / "config.yaml")).expanduser()
CONFIG_DIR  = CONFIG_FILE.parent
PRESETS_DIR = CONFIG_DIR / "presets"  # nadpisywalne przez `presets_dir` w config.yaml

# Katalogi skilli tworzone w projekcie — pokrywa wszystkie 3 CLIs
SKILL_DIRS = [
    ".agents/skills",   # Gemini CLI + Kimi CLI (open Agent Skills standard)
    ".claude/skills",   # Claude Code + Kimi CLI
]

AGAL_MARKER_FILE = ".agal_managed"   # marker w każdym katalogu tworzonym przez agal

# Pliki kontekstowe (coding guidelines) tworzone w root projektu.
# Każdy CLI czyta inną nazwę; AGENTS.md to open standard (Gemini/Kimi).
CONTEXT_FILENAMES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "KIMI.md"]
AGAL_CONTEXT_MARKER = ".agal_context"   # lista plików kontekstowych utworzonych przez agal

DEFAULT_CONFIG = {
    # Katalog z twoją biblioteką 200+ plików .md
    "skills_dir": str(Path.home() / "my-skills"),
    # Binarne nazwy CLI
    "clis": {
        "claude": "claude",
        "gemini": "gemini",
        "kimi":   "kimi",
    },
    # Czy usuwać symlinki po zakończeniu sesji w trybie launch
    "cleanup_after_launch": True,
    # Meta-preset doładowywany do każdego (None = wyłączone).
    # Skille z core ładowane PRZED skillami presetu, deduplikowane.
    "core_preset": "dev-workflow-core",
    # Plik z coding guidelines (AGENTS.md). Przy --prepare trafia do root
    # projektu jako AGENTS.md + CLAUDE.md/GEMINI.md/KIMI.md (symlink lub copy
    # w --remote). None = wyłączone (back-compat).
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
        print(f"✅  Stworzono domyślny config: {CONFIG_FILE}")
        print(f"    Ustaw skills_dir na katalog z twoją biblioteką skilli.\n")
    user = yaml.safe_load(CONFIG_FILE.read_text()) or {}
    # Merge z DEFAULT_CONFIG — brakujące klucze dostają defaulty (np. core_preset)
    merged = {**DEFAULT_CONFIG, **user}
    # presets_dir z configa nadpisuje default (CONFIG_DIR/presets)
    if merged.get("presets_dir"):
        PRESETS_DIR = Path(merged["presets_dir"]).expanduser()
    return merged


def load_preset(name: str) -> dict:
    path = PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in PRESETS_DIR.glob("*.yaml"))
        print(f"❌  Preset '{name}' nie istnieje.")
        if available:
            print(f"    Dostępne: {', '.join(available)}")
        sys.exit(1)
    return yaml.safe_load(path.read_text())


def resolve_skills(preset: dict, preset_name: str, config: dict) -> tuple[list[str], int]:
    """
    Zwraca (lista skilli, liczba dorzucona z core_preset).
    Core skille przed presetem, deduplikowane (pierwsza wygrywa).
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
            print(f"  ⚠️   core_preset '{core_name}' nie istnieje, pomijam meta-skille")

    for s in preset.get("skills", []):
        if s not in seen:
            skills.append(s)
            seen.add(s)

    return skills, core_added

# ── Interakcja (fzf / fallback menu) ─────────────────────────────────────────

def _has_fzf() -> bool:
    return bool(shutil.which("fzf"))


def pick_one(options: list[str], prompt: str = "Wybierz") -> str | None:
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
        return options[int(input(f"{prompt} (numer): ")) - 1]
    except (ValueError, IndexError, EOFError):
        return None


def _list_skill_names(path: Path) -> list[str]:
    """Subdiry z SKILL.md (Anthropic standard) + flat .md (legacy)."""
    names = []
    for d in sorted(path.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            names.append(d.name)
    names += sorted(f.name for f in path.glob("*.md"))
    return names


def pick_skills_multi(skills_dir: str) -> list[str]:
    path = Path(skills_dir).expanduser()
    if not path.exists():
        print(f"❌  skills_dir nie istnieje: {path}")
        print(f"    Ustaw go w {CONFIG_FILE}")
        sys.exit(1)
    names = _list_skill_names(path)
    if not names:
        print(f"❌  Brak skilli (subdirów z SKILL.md ani plików .md) w {path}")
        sys.exit(1)

    if _has_fzf():
        # Preview: jeśli to dir → cat SKILL.md, jeśli plik → cat plik
        preview = (
            f"if [ -d '{path}/{{}}' ]; then "
            f"  cat '{path}/{{}}/SKILL.md' 2>/dev/null; "
            f"else cat '{path}/{{}}' 2>/dev/null; fi"
        )
        r = subprocess.run(
            ["fzf", "--multi",
             "--prompt", "Skille (TAB=zaznacz, ENTER=potwierdź): ",
             "--height", "80%", "--border",
             "--preview", preview,
             "--preview-window", "right:50%:wrap",
             "--header", f"{len(names)} skilli w {path.name}/"],
            input="\n".join(names), capture_output=True, text=True,
        )
        return [s for s in r.stdout.strip().split("\n") if s] if r.returncode == 0 else []

    print(f"\nDostępne skille ({path}):")
    for i, n in enumerate(names, 1):
        print(f"  {i:>3}. {n}")
    raw = input("\nNazwy lub numery (przecinkami): ")
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

# ── Zarządzanie presetami ─────────────────────────────────────────────────────

def list_presets() -> None:
    presets = sorted(PRESETS_DIR.glob("*.yaml"))
    if not presets:
        print("Brak presetów. Utwórz pierwszy: agal --new <nazwa>")
        return
    print(f"\n{'Preset':<22} {'Skille':>6}  Opis")
    print("─" * 58)
    for p in presets:
        try:
            d = yaml.safe_load(p.read_text())
            print(f"  {p.stem:<20} {len(d.get('skills', [])):>5}  {d.get('description', '')}")
        except Exception:
            print(f"  {p.stem:<20}   ???  (błąd parsowania)")
    print()


def show_info(name: str, config: dict) -> None:
    d = load_preset(name)
    print(f"\nPreset : {name}")
    print(f"Opis   : {d.get('description', '—')}")
    if d.get("notes"):
        print(f"Notatki: {d['notes']}")
    own = d.get("skills", [])
    print(f"Skille własne ({len(own)}):")
    for s in own:
        print(f"  - {s}")

    core_name = config.get("core_preset")
    if core_name and name != core_name:
        core_path = PRESETS_DIR / f"{core_name}.yaml"
        if core_path.exists():
            core = yaml.safe_load(core_path.read_text()) or {}
            extra = [s for s in core.get("skills", []) if s not in own]
            if extra:
                print(f"\n+ Auto-merge z '{core_name}' ({len(extra)} extra):")
                for s in extra:
                    print(f"  · {s}")
    print()


def new_preset(name: str, config: dict) -> None:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PRESETS_DIR / f"{name}.yaml"
    if dest.exists():
        if input(f"Preset '{name}' istnieje. Nadpisać? [t/N] ").strip().lower() != "t":
            return
    desc  = input("Opis (opcjonalnie): ").strip()
    notes = input("Notatki/instrukcje (opcjonalnie): ").strip()
    print()
    selected = pick_skills_multi(config.get("skills_dir", "~/my-skills"))
    if not selected:
        print("Nic nie zaznaczono.")
        return
    data: dict = {"name": name, "skills": selected}
    if desc:  data["description"] = desc
    if notes: data["notes"] = notes
    dest.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"\n✅  Preset '{name}' zapisany ({len(selected)} skilli) → {dest}")


def validate_preset(name: str, config: dict) -> None:
    """Sprawdza czy wszystkie skille z presetu (po resolve) istnieją + mają frontmatter."""
    preset = load_preset(name)
    skills, core_added = resolve_skills(preset, name, config)
    skills_dir = Path(config.get("skills_dir", "~/my-skills")).expanduser()

    own = len(skills) - core_added
    print(f"\n🔎  Walidacja '{name}': {len(skills)} skilli ({own} własnych + {core_added} core)\n")

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
        print(f"  ❌  Brakuje w skills_dir ({len(missing)}):")
        for m in missing: print(f"       - {m}")
    if bad_frontmatter:
        print(f"  ⚠️   Brak frontmatter ({len(bad_frontmatter)}):")
        for e, p in bad_frontmatter: print(f"       - {e}  (brak: {', '.join(p)})")
    if not missing and not bad_frontmatter:
        print(f"\n  Preset gotowy do użycia.\n")
    else:
        print()
        sys.exit(1)


def edit_preset(name: str) -> None:
    path = PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        print(f"❌  Preset '{name}' nie istnieje.")
        sys.exit(1)
    subprocess.run([os.environ.get("EDITOR", "nano"), str(path)])

# ── Frontmatter check ─────────────────────────────────────────────────────────

def _has_frontmatter(text: str) -> tuple[bool, bool]:
    """Zwraca (ma_name, ma_description)."""
    if not text.startswith("---"):
        return False, False
    end = text.find("\n---", 3)
    if end == -1:
        return False, False
    fm_block = text[3:end]
    return ("name:" in fm_block), ("description:" in fm_block)


def check_skills(config: dict) -> None:
    skills_dir = Path(config.get("skills_dir", "~/my-skills")).expanduser()
    # Subdiry z SKILL.md + flat .md (legacy)
    files = []
    for d in sorted(skills_dir.iterdir()) if skills_dir.exists() else []:
        if d.is_dir() and (d / "SKILL.md").exists():
            files.append(d / "SKILL.md")
    files += sorted(skills_dir.glob("*.md"))
    if not files:
        print(f"Brak skilli w {skills_dir}")
        return

    ok = bad_name = bad_desc = bad_both = 0
    issues = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        has_name, has_desc = _has_frontmatter(text)
        # Display name: dir name dla subdir, filename dla flat
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

    print(f"\n📊  Wyniki dla {skills_dir} ({len(files)} plików):")
    print(f"  ✅  OK (name + description): {ok}")
    print(f"  ⚠️   Brak description:        {bad_desc}")
    print(f"  ⚠️   Brak name:               {bad_name}")
    print(f"  ❌  Brak obu:                 {bad_both}")

    if issues:
        print(f"\n  Pliki wymagające frontmatter (Gemini ich nie wczyta):")
        for fname, missing in issues[:20]:
            print(f"    {fname:<40} brak: {', '.join(missing)}")
        if len(issues) > 20:
            print(f"    ... i {len(issues) - 20} więcej")
        print(f"""
  Wymagany format frontmatter na początku każdego SKILL.md:

    ---
    name: nazwa-skilla
    description: Kiedy i do czego używać tego skilla. Im dokładniej, tym lepiej.
    ---
""")

# ── Symlinki — serce nowego agal ───────────────────────────────────────────────

def _skill_stem(filename: str) -> str:
    """typescript.md → typescript"""
    return Path(filename).stem


def _create_skill_symlinks(skills_list: list[str], skills_dir: Path,
                           target_dir: Path, copy: bool = False) -> list[str]:
    """
    Dla każdego skilla tworzy:

    Symlink mode (default):
      target_dir/.agents/skills/<stem>  →  skills_dir/<stem>   (dir symlink)

    Copy mode (--remote):
      target_dir/.agents/skills/<stem>/  ← cała zawartość skopiowana, brak symlinków
      Projekt portable — działa po cloneowaniu na inną maszynę bez agal/skills_dir.

    Legacy flat .md w obu trybach: dest_dir/<stem>/SKILL.md.

    Zwraca listę brakujących skilli.
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
    """Zwraca (preset_name, mode) jeśli katalog jest zarządzany przez agal."""
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
            print(f"  ⏭️   {d} — nie zarządzany przez agal, pomijam")
            continue
        shutil.rmtree(d)
        removed += 1
        print(f"  🧹  Usunięto {d}")
    if removed == 0:
        print("  Nic do usunięcia — brak katalogów zarządzanych przez agal.")

# ── Pliki kontekstowe (coding guidelines) ─────────────────────────────────────

def _place_context_file(target_dir: Path, context_path: Path,
                        copy: bool = False) -> list[str]:
    """
    Tworzy AGENTS.md + CLAUDE/GEMINI/KIMI.md w root projektu (symlink lub copy).

    Nie nadpisuje istniejących plików których agal nie utworzył (chroni
    własne CLAUDE.md usera). Lista utworzonych nazw idzie do .agal_context.
    Zwraca listę pominiętych nazw (już istnieją, nie nasze).
    """
    src = context_path.expanduser()
    if not src.is_file():
        print(f"  ⚠️   context_file nie istnieje: {src} — pomijam guidelines")
        return []

    marker = target_dir / AGAL_CONTEXT_MARKER
    prev = set(marker.read_text().split()) if marker.exists() else set()

    created, skipped = [], []
    for fname in CONTEXT_FILENAMES:
        dest = target_dir / fname
        if dest.exists() or dest.is_symlink():
            if fname in prev:
                dest.unlink()              # nasz z poprzedniego prepare — odśwież
            else:
                skipped.append(fname)      # plik usera — nie ruszaj
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
    skills_dir = Path(config.get("skills_dir", "~/my-skills")).expanduser()
    skills, core_added = resolve_skills(preset, preset_name, config)
    own = len(skills) - core_added
    mode_label = "📋 copy (remote/portable)" if copy else "🔗 symlink"

    if core_added:
        print(f"\n📦  Preset '{preset_name}' ({own} własnych + {core_added} z core) — {mode_label} w {target}\n")
    else:
        print(f"\n📦  Preset '{preset_name}' ({own} skilli) — {mode_label} w {target}\n")

    existing = _is_managed(target)
    if existing:
        prev_name, prev_mode = existing
        print(f"  ♻️   Zastępuję poprzedni preset: {prev_name} ({prev_mode})")
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
            print(f"  ⏭️   Pominięto (istniejące, nie agal): {', '.join(skipped)}")

    if missing:
        print(f"  ⚠️   Brakujące pliki: {', '.join(missing)}")

    print(f"  ✅  Gotowe:")
    for skill_subdir in SKILL_DIRS:
        d = target / skill_subdir
        if d.exists():
            n = sum(1 for p in d.iterdir() if p.name != AGAL_MARKER_FILE)
            print(f"       {d.relative_to(target)}  ({n} skilli)")

    print(f"""
  Claude Code czyta  : .claude/skills/
  Gemini CLI czyta   : .agents/skills/
  Kimi CLI czyta     : oba powyższe

  Agenci wczytują tylko nazwy skilli na start.
  Pełna treść — tylko gdy pasuje do zadania.

  Zmień preset : agal --prepare <inny>
  Usuń symlinki: agal --unprepare
""")


def unprepare(config: dict, target_dir: Path | None = None) -> None:
    target = (target_dir or Path.cwd()).resolve()
    print(f"\n🧹  Usuwam symlinki agal z {target}\n")
    _remove_skill_symlinks(target)
    _remove_context_file(target)
    print()


def show_status(config: dict, target_dir: Path | None = None) -> None:
    target = (target_dir or Path.cwd()).resolve()
    info = _is_managed(target)

    if not info:
        print(f"\n  Brak aktywnego presetu w {target}")
        print(f"  Użyj: agal --prepare <preset>\n")
        return

    preset, mode = info
    print(f"\n  Aktywny preset: {preset}  [{mode}]  ({target})\n")
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
        print(f"  {skill_subdir}/  ({len(names)} skilli)")
        for name in names:
            print(f"    · {name}")
    print()

# ── Launch (pure CLI, bez emdash) ─────────────────────────────────────────────

def launch(preset_name: str, cli_name: str, config: dict, copy: bool = False) -> None:
    clis       = config.get("clis", {})
    do_cleanup = config.get("cleanup_after_launch", True)

    if cli_name not in clis:
        print(f"❌  Nieznane CLI '{cli_name}'. Dostępne: {', '.join(clis)}")
        sys.exit(1)
    cli_cmd = clis[cli_name]
    if not shutil.which(cli_cmd):
        print(f"❌  Nie znaleziono '{cli_cmd}' w PATH.")
        sys.exit(1)

    preset = load_preset(preset_name)
    skills, core_added = resolve_skills(preset, preset_name, config)
    skills_dir = Path(config.get("skills_dir", "~/my-skills")).expanduser()
    target = Path.cwd()
    own = len(skills) - core_added

    suffix = f"({own}+{core_added} core)" if core_added else f"({own})"
    mode_label = "📋 copy" if copy else "🔗 symlink"
    print(f"\n🚀  {cli_name}  ·  preset: {preset_name}  ·  {len(skills)} skilli {suffix}  ·  {mode_label}\n")

    missing = _create_skill_symlinks(skills, skills_dir, target, copy=copy)
    _mark_as_managed(target, preset_name, copy=copy)
    ctx = config.get("context_file")
    if ctx:
        _place_context_file(target, Path(ctx), copy=copy)
    if missing:
        print(f"⚠️   Brakujące pliki: {', '.join(missing)}\n")

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
        description="agal — Agent Agnostic Launch z presetami skilli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("preset", nargs="?")
    parser.add_argument("cli",    nargs="?")
    parser.add_argument("--list",      "-l", action="store_true")
    parser.add_argument("--new",       "-n", metavar="NAZWA")
    parser.add_argument("--edit",      "-e", metavar="NAZWA")
    parser.add_argument("--info",      "-i", metavar="NAZWA")
    parser.add_argument("--prepare",   "-p", metavar="PRESET",
                        help="Utwórz symlinki w cwd (tryb emdash/multi-CLI)")
    parser.add_argument("--unprepare", "-u", action="store_true",
                        help="Usuń symlinki zarządzane przez agal z cwd")
    parser.add_argument("--status",    "-s", action="store_true",
                        help="Pokaż aktywny preset w cwd")
    parser.add_argument("--check",     "-k", action="store_true",
                        help="Sprawdź frontmatter plików skilli")
    parser.add_argument("--validate",  "-V", metavar="PRESET",
                        help="Sprawdź czy preset (po merge z core) jest kompletny")
    parser.add_argument("--remote",    "-r", action="store_true",
                        help="Kopiuj zawartość skilli zamiast symlinkować "
                             "(dla cloud agents, CI, devcontainerów, projektów portable)")
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

    # Interaktywny launch
    preset_name = args.preset
    if not preset_name:
        presets = sorted(p.stem for p in PRESETS_DIR.glob("*.yaml"))
        if not presets:
            print("Brak presetów. Utwórz pierwszy: agal --new <nazwa>")
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
