#!/bin/sh
# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
#
# Starts the Stepan Surfactant Cheminformatics dry lab on macOS or Linux. The first start downloads a Python
# runtime and the packages pinned in uv.lock into this folder; later starts take seconds.

ROOT=$(cd "$(dirname "$0")/.." && pwd) || exit 1
cd "$ROOT" || exit 1

PID_FILE="$ROOT/.lab.pid"
PORT_FILE="$ROOT/.lab.port"
LOG_FILE="$ROOT/.lab.log"
TOOLS="$ROOT/.tools"

say() { printf '%s\n' "$*"; }
open_page() {
  [ -n "${LAB_NO_BROWSER:-}" ] && return 0
  if command -v open >/dev/null 2>&1; then open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1
  else say "Open this address in a browser: $1"; fi
}
fail() {
  say ""
  say "The lab could not be started: $*"
  say "The log is in $LOG_FILE"
  exit 1
}

say "Stepan Surfactant Cheminformatics"
say "Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University"
say ""

# A folder downloaded as a ZIP carries a quarantine flag on macOS; clear it for this folder.
if [ "$(uname)" = "Darwin" ]; then xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true; fi

# Already running: just open the page again.
if [ -f "$PID_FILE" ] && [ -f "$PORT_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  URL="http://127.0.0.1:$(cat "$PORT_FILE")/"
  say "The lab is already running at $URL"
  open_page "$URL"
  exit 0
fi
rm -f "$PID_FILE" "$PORT_FILE"
: > "$LOG_FILE"

# Step 1: uv, the tool that installs Python and the packages.
UV=""
if [ -x "$TOOLS/uv" ]; then
  UV="$TOOLS/uv"
elif command -v uv >/dev/null 2>&1; then
  UV=$(command -v uv)
else
  say "Step 1 of 3: downloading uv, the tool that installs Python and the packages (about 20 MB)"
  mkdir -p "$TOOLS"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | UV_UNMANAGED_INSTALL="$TOOLS" sh >>"$LOG_FILE" 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | UV_UNMANAGED_INSTALL="$TOOLS" sh >>"$LOG_FILE" 2>&1
  fi
  [ -x "$TOOLS/uv" ] || fail "uv could not be downloaded. Check the internet connection and start again."
  UV="$TOOLS/uv"
fi

# Step 2: Python 3.12 and the packages, kept inside this folder.
export UV_PYTHON_INSTALL_DIR="$TOOLS/python"
export UV_CACHE_DIR="$TOOLS/cache"
say "Step 2 of 3: installing Python and the packages (first start only, a few minutes)"
"$UV" sync --frozen || fail "the packages could not be installed. Check the internet connection and start again."
PY="$ROOT/.venv/bin/python"

# Step 3: start the server on a free port.
PORT=$("$PY" -c '
import socket
for p in list(range(2718, 2740)) + [0]:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p))
        print(s.getsockname()[1])
        break
    except OSError:
        pass
    finally:
        s.close()
')
say "Step 3 of 3: starting the lab"
export PYTHONDONTWRITEBYTECODE=1
nohup "$PY" -m uvicorn server:app --host 127.0.0.1 --port "$PORT" >>"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "$PORT" > "$PORT_FILE"
URL="http://127.0.0.1:$PORT/"

i=0
while [ "$i" -lt 120 ]; do
  if "$PY" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1)' "$URL" >/dev/null 2>&1; then
    say ""
    say "The lab is running at $URL and opens in your browser."
    say "To stop it, use the Stop file in this folder."
    open_page "$URL"
    exit 0
  fi
  kill -0 "$(cat "$PID_FILE")" 2>/dev/null || fail "the server stopped while starting."
  sleep 0.5
  i=$((i + 1))
done
fail "the server did not answer within a minute."
