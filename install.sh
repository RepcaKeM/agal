#!/usr/bin/env bash
# agal — Agent Agnostic Launch :: bootstrap installer
#
#   curl -fsSL https://raw.githubusercontent.com/baszczkacper/agal/main/install.sh | bash
#
# Installs the `agal` CLI, wires ~/.agal/presets to the bundled presets, and
# writes a starter config. Idempotent — safe to re-run.
#
# Env overrides:
#   AGAL_REPO        git URL to clone (default: github.com/baszczkacper/agal)
#   AGAL_HOME        state dir       (default: ~/.agal)
#   AGAL_SKILLS_DIR  skill library   (asked interactively if unset)

set -euo pipefail

AGAL_REPO="${AGAL_REPO:-https://github.com/baszczkacper/agal.git}"
AGAL_HOME="${AGAL_HOME:-$HOME/.agal}"
SRC_DIR="$AGAL_HOME/src"

say()  { printf '\033[1;36m›\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null    || die "git not found"
command -v python3 >/dev/null || die "python3 not found"

# 1. Get the source (use cwd if already a checkout, else clone/update).
if [ -f "./agal.py" ] && [ -d "./presets" ]; then
  SRC_DIR="$(pwd)"
  say "Using current checkout: $SRC_DIR"
elif [ -d "$SRC_DIR/.git" ]; then
  say "Updating existing checkout: $SRC_DIR"
  git -C "$SRC_DIR" pull --ff-only --quiet
else
  say "Cloning $AGAL_REPO → $SRC_DIR"
  mkdir -p "$AGAL_HOME"
  git clone --depth 1 --quiet "$AGAL_REPO" "$SRC_DIR"
fi

# 2. Install the CLI — prefer pipx, then uv, then pip --user.
if command -v pipx >/dev/null; then
  say "Installing via pipx"
  pipx install --force "$SRC_DIR" >/dev/null
elif command -v uv >/dev/null; then
  say "Installing via uv tool"
  uv tool install --force "$SRC_DIR" >/dev/null
else
  say "No pipx/uv — installing into a managed venv ($AGAL_HOME/venv)"
  python3 -m venv "$AGAL_HOME/venv"
  "$AGAL_HOME/venv/bin/pip" install --quiet --upgrade "$SRC_DIR"
  mkdir -p "$HOME/.local/bin"
  ln -sfn "$AGAL_HOME/venv/bin/agal" "$HOME/.local/bin/agal"
  say "Linked $HOME/.local/bin/agal → venv"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) warn 'Add ~/.local/bin to PATH:  export PATH="$HOME/.local/bin:$PATH"' ;;
  esac
fi

# 3. Wire presets so repo edits are picked up globally.
mkdir -p "$AGAL_HOME"
ln -sfn "$SRC_DIR/presets" "$AGAL_HOME/presets"
say "Presets linked: $AGAL_HOME/presets → $SRC_DIR/presets"

# 4. Starter config (never clobber an existing one).
CFG="$AGAL_HOME/config.yaml"
if [ ! -f "$CFG" ]; then
  SKILLS_DIR="${AGAL_SKILLS_DIR:-}"
  if [ -z "$SKILLS_DIR" ] && [ -t 0 ]; then
    printf 'Path to your skills library (dir of <skill>/SKILL.md): '
    read -r SKILLS_DIR
  fi
  SKILLS_DIR="${SKILLS_DIR:-$HOME/my-skills}"
  cat > "$CFG" <<EOF
skills_dir: $SKILLS_DIR
presets_dir: $AGAL_HOME/presets
core_preset: dev-workflow-core
context_file: $SRC_DIR/AGENTS.md
EOF
  say "Config written: $CFG"
else
  say "Config exists, left unchanged: $CFG"
fi

cat <<EOF

✅ agal installed.

   agal --list                 list presets
   agal --prepare backend-dev  set up a project
   agal --help                 all commands

Note: the skill library is NOT bundled. Point skills_dir in $CFG
at your own collection (see README → "Skills" for sources).
EOF
