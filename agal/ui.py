from __future__ import annotations

import os
import re
import sys

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _is_color_supported() -> bool:
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if "PYTEST_CURRENT_TEST" in os.environ:
        # Keep tests deterministic unless explicitly testing UI
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def visible_len(text: str) -> int:
    """Returns string length without ANSI escape sequences."""
    return len(_ANSI_RE.sub("", text))


def color(code: str, text: str) -> str:
    if _is_color_supported():
        return f"\033[{code}m{text}\033[0m"
    return text


def bold(text: str) -> str:
    return color("1", text)


def dim(text: str) -> str:
    return color("2", text)


def cyan(text: str) -> str:
    return color("36", text)


def green(text: str) -> str:
    return color("32", text)


def yellow(text: str) -> str:
    return color("33", text)


def red(text: str) -> str:
    return color("31", text)


def blue(text: str) -> str:
    return color("34", text)


def magenta(text: str) -> str:
    return color("35", text)


def ok_mark() -> str:
    return green("✔")


def fail_mark() -> str:
    return red("✖")


def warn_mark() -> str:
    return yellow("⚠")


def badge(text: str, bg: str = "cyan") -> str:
    colors = {
        "cyan": cyan,
        "green": green,
        "yellow": yellow,
        "red": red,
        "dim": dim,
    }
    fn = colors.get(bg, cyan)
    return f"[{fn(text)}]"


def card(title: str, rows: list[tuple[str, str]], min_width: int = 62) -> str:
    """Renders a modern rounded unicode card with key-value information."""
    content_lines = []
    header_raw = f"  {title}"
    content_lines.append(header_raw)

    for label, val in rows:
        row_raw = f"  {label:<16} {val}"
        content_lines.append(row_raw)

    max_w = max([visible_len(l) for l in content_lines] + [min_width]) + 2

    border_color = cyan if _is_color_supported() else str
    top = border_color("╭" + "─" * (max_w) + "╮")
    bottom = border_color("╰" + "─" * (max_w) + "╯")

    rendered = [top]
    # Title line
    rendered.append(border_color("│") + f" {bold(title):<{max_w + (len(bold(title)) - visible_len(title)) - 1}}" + border_color("│"))
    if rows:
        rendered.append(border_color("│") + " " * max_w + border_color("│"))
        for label, val in rows:
            line_str = f"  {dim(label):<25} {val}" if _is_color_supported() else f"  {label:<16} {val}"
            pad = max_w - visible_len(line_str)
            rendered.append(border_color("│") + line_str + (" " * max(0, pad)) + border_color("│"))

    rendered.append(bottom)
    return "\n".join(rendered)


def notice_banner(text: str) -> str:
    """Renders a discrete, elegant framed notice banner."""
    v_len = visible_len(text)
    w = max(v_len + 4, 60)
    top = yellow("╭─ Notice " + "─" * (w - 10) + "╮")
    bot = yellow("╰" + "─" * w + "╯")
    pad = w - v_len - 2
    body = yellow("│") + f" {text}" + (" " * max(0, pad)) + yellow("│")
    return f"{top}\n{body}\n{bot}"
