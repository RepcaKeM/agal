#!/usr/bin/env python3
"""Lint sales copy: word limit, banned words, banned names, closing question.

Usage: check_copy.py FILE --max-words N [--banned-names PATH] [--require-question]
Prints OK (exit 0) or one violation per line (exit 1). Missing names file: exit 2.
"""
import argparse
import re
import sys
from pathlib import Path

BANNED_WORDS_FILE = Path(__file__).resolve().parent.parent / "references" / "banned-words.md"


def load_list(path: Path) -> list[str]:
    path = Path(path)
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    if path.suffix == ".md":
        return [line[2:].strip() for line in lines if line.startswith("- ")]
    return [line for line in lines if line and not line.startswith("#")]


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


def check(text: str, max_words: int, banned_words: list[str], banned_names: list[str], require_question: bool) -> list[str]:
    violations = []
    words = len(text.split())
    if words > max_words:
        violations.append(f"too long: {words} words (max {max_words})")
    violations += [f"banned word: {w}" for w in banned_words if _contains(text, w)]
    violations += [f"banned name: {n}" for n in banned_names if _contains(text, n)]
    if require_question and not text.rstrip().endswith("?"):
        violations.append("must end with a question")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint sales copy.")
    parser.add_argument("file")
    parser.add_argument("--max-words", type=int, required=True)
    parser.add_argument("--banned-names")
    parser.add_argument("--require-question", action="store_true")
    args = parser.parse_args(argv)

    names: list[str] = []
    if args.banned_names:
        try:
            names = load_list(Path(args.banned_names))
        except OSError as e:
            print(f"cannot read banned names file {args.banned_names}: {e.strerror}", file=sys.stderr)
            return 2

    text = Path(args.file).read_text(encoding="utf-8")
    violations = check(text, args.max_words, load_list(BANNED_WORDS_FILE), names, args.require_question)
    print("\n".join(violations) if violations else "OK")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
