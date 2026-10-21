from __future__ import annotations

from pathlib import Path
import re

from agal.config import (
    AGAL_CONTEXT_MARKER,
    CONTEXT_FILENAMES,
    context_filenames_for_runtimes,
)

_USE_WHEN_RE = re.compile(
    r"\bUse(?:\s+this)?\s+(?:when|before|during|after|for)\s+(.+?)(?:\.\s|\.\Z|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_ARTICLE_RE = re.compile(r"^(a|an|the|or|any)\s+", re.IGNORECASE)


def extract_triggers(skill_md_text: str, max_n: int = 3, max_chars: int = 50) -> str:
    """Pull 'Use when X, Y, Z' clause from a skill's frontmatter description.
    Returns pipe-separated triggers (max_n per skill, max_chars per trigger),
    or '' if not extractable."""
    if not skill_md_text.startswith("---"):
        return ""
    end = skill_md_text.find("\n---", 3)
    if end == -1:
        return ""
    fm = skill_md_text[3:end]

    desc_match = re.search(
        r'^description:\s*(?:"((?:[^"\\]|\\.)+)"|\'((?:[^\'\\]|\\.)+)\'|(.+?))(?=^\w+:|\Z)',
        fm,
        re.MULTILINE | re.DOTALL,
    )
    if not desc_match:
        return ""
    desc = (desc_match.group(1) or desc_match.group(2) or desc_match.group(3) or "").strip()
    desc = re.sub(r"\s+", " ", desc)

    uw = _USE_WHEN_RE.search(desc)
    if not uw:
        return ""
    clause = uw.group(1).strip().rstrip(".")

    parts = [p.strip() for p in clause.split(",") if p.strip()]
    parts = [_ARTICLE_RE.sub("", p) for p in parts]
    parts = [p for p in parts if p]

    def _truncate(s: str) -> str:
        if len(s) <= max_chars:
            return s
        cut = s[:max_chars].rsplit(" ", 1)[0]
        return cut or s[:max_chars]

    parts = [_truncate(p) for p in parts]
    return "|".join(parts[:max_n])


def build_routing_block(skills: list[str], skill_paths: dict[str, Path]) -> tuple[str, int]:
    """Builds the markdown block appended to AGENTS.md. Returns (block, n_rows)."""
    rows = []
    for skill in skills:
        path = skill_paths.get(skill)
        if not path:
            continue
        skill_md = path / "SKILL.md" if path.is_dir() else path
        if not skill_md.is_file():
            continue
        try:
            triggers = extract_triggers(skill_md.read_text(encoding="utf-8"))
        except OSError:
            triggers = ""
        if triggers:
            rows.append(f"{triggers},{skill}")
    if not rows:
        return "", 0
    body = "\n".join(rows)
    block = (
        "\n\n<!-- agal:routing — auto-generated per preset; removed by --unprepare -->\n"
        "## Skill routing (this project)\n\n"
        "Before answering a non-trivial task, scan the CSV below. If any "
        "trigger (left of comma, pipe-separated) matches the user's intent, "
        "invoke that skill via the Skill tool BEFORE responding.\n\n"
        "```csv\n"
        f"{body}\n"
        "```\n"
        "<!-- agal:routing-end -->\n"
    )
    return block, len(rows)


def place_context_file(
    target_dir: Path,
    context_path: Path,
    copy: bool = True,
    routing_block: str = "",
    filenames: list[str] | None = None,
) -> list[str]:
    """
    Writes guideline files into target_dir.

    Files are always copies. ``copy`` is accepted so existing callers keep working.
    ``filenames`` limits the set; None writes every context filename.
    """
    del copy
    src = context_path.expanduser()
    if not src.exists():
        return []

    names = list(filenames) if filenames is not None else list(CONTEXT_FILENAMES)
    marker = target_dir / AGAL_CONTEXT_MARKER
    prev = set(marker.read_text().split()) if marker.exists() else set()
    source_text = src.read_text(encoding="utf-8")

    created, skipped = [], []
    for fname in names:
        dest = target_dir / fname
        if dest.exists() or dest.is_symlink():
            if fname in prev:
                dest.unlink()
            else:
                skipped.append(fname)
                continue
        dest.write_text(source_text + routing_block, encoding="utf-8")
        created.append(fname)

    for fname in prev - set(names):
        path = target_dir / fname
        if path.is_symlink() or path.is_file():
            path.unlink()

    tracked = (set(created) | (prev & set(names))) - set(skipped)
    if tracked:
        marker.write_text(" ".join(sorted(tracked)) + "\n")
    elif marker.exists():
        marker.unlink()

    return created


def sync_context_files(target_dir: Path) -> None:
    """Keep guideline files aligned with the project's selected runtimes."""
    from agal.skills import load_local_state

    marker = target_dir / AGAL_CONTEXT_MARKER
    if not marker.is_file():
        return

    tracked = [name for name in marker.read_text().split() if name]
    wanted = context_filenames_for_runtimes(load_local_state(target_dir).get("runtimes") or None)
    content = None
    for name in tracked:
        path = target_dir / name
        if path.is_file() and not path.is_symlink():
            content = path.read_text(encoding="utf-8")
            break

    kept = [name for name in tracked if name in wanted]
    for name in tracked:
        if name not in wanted:
            path = target_dir / name
            if path.is_symlink() or path.is_file():
                path.unlink()

    if content is not None:
        for name in wanted:
            dest = target_dir / name
            if dest.exists() and name not in tracked:
                continue
            dest.write_text(content, encoding="utf-8")
            if name not in kept:
                kept.append(name)

    if kept:
        marker.write_text(" ".join(sorted(set(kept))) + "\n")
    else:
        marker.unlink(missing_ok=True)


def remove_context_file(target_dir: Path) -> list[str]:
    """Removes guideline files created by agal."""
    marker = target_dir / AGAL_CONTEXT_MARKER
    if not marker.exists():
        return []
    removed = []
    for fname in marker.read_text().split():
        p = target_dir / fname
        if p.is_symlink() or p.exists():
            p.unlink()
            removed.append(fname)
    marker.unlink()
    return removed
