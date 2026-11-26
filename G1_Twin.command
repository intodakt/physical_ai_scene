#!/bin/bash
# G1 virtual table on a MacBook: double-click this file in Finder (first time: right-click -> Open).
# Uses the same .venv as G1_Demo.command; the first run sets it up (Python 3.11 via uv, packages, Ollama model).
# Options are passed on, e.g.:  ./G1_Twin.command --run data/demo_store/runs/S2_bag --parser rules
set -e
cd "$(dirname "$0")"
MODEL="${S5_MODEL:-qwen2.5:3b}"
say() { printf "\n\033[1;34m[G1]\033[0m %s\n" "$*"; }

if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  say "Installing uv (Python package manager)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ ! -x .venv/bin/python ]; then
  say "Creating the Python 3.11 environment (first run only, a few minutes)..."
  "$UV" venv -p 3.11 .venv
fi
if [ ! -f .venv/.deps_ok ] || [ requirements-demo.txt -nt .venv/.deps_ok ]; then
  say "Installing packages..."
  VIRTUAL_ENV="$PWD/.venv" "$UV" pip install -r requirements-demo.txt
  touch .venv/.deps_ok
fi
if [ "$(uname)" = "Darwin" ] && ! .venv/bin/python -c "import open3d" >/dev/null 2>&1; then
  BREW="$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1)"
  if [ -n "$BREW" ]; then
    say "Installing libusb + libomp for Open3D (Homebrew)..."
    "$BREW" install libusb libomp
  else
    say "Open3D needs Homebrew's libusb. Install Homebrew (https://brew.sh), then run: brew install libusb libomp"
    exit 1
  fi
fi

if command -v ollama >/dev/null 2>&1 || [ -d /Applications/Ollama.app ]; then
  if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
    say "Starting Ollama..."
    if [ -d /Applications/Ollama.app ]; then open -a Ollama; else (ollama serve >/tmp/g1_ollama.log 2>&1 &); fi
    for _ in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
  fi
  if ! curl -sf http://127.0.0.1:11434/api/tags | grep -q "\"$MODEL\""; then
    say "Downloading the S5 model $MODEL (about 2 GB, first run only)..."
    if command -v ollama >/dev/null 2>&1; then ollama pull "$MODEL"
    else curl -sf http://127.0.0.1:11434/api/pull -d "{\"model\": \"$MODEL\", \"stream\": false}" >/dev/null; fi
  fi
else
  say "Ollama is not installed: S5 uses the offline rule parser."
fi

say "Starting the virtual table (close this window or press Ctrl+C to stop)"
export S5_MODEL="$MODEL"
exec .venv/bin/python -m demo.twin "$@"
