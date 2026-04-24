#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/texttospeechhighlighted"

mkdir -p "$BIN_DIR" "$APP_DIR"

install -m 0755 "$SCRIPT_DIR/tts_highlight.py" "$APP_DIR/tts_highlight.py"
install -m 0755 "$SCRIPT_DIR/highlight_pane.py" "$APP_DIR/highlight_pane.py"
install -m 0644 "$SCRIPT_DIR/tts_settings.json" "$APP_DIR/tts_settings.json"

cat <<EOF
Installed:
  $APP_DIR/tts_highlight.py
  $APP_DIR/highlight_pane.py
  $APP_DIR/tts_settings.json

Suggested alias:
  alias s2t="python3 $APP_DIR/tts_highlight.py"
EOF
