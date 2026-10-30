#!/bin/sh
# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
#
# Stops the Stepan Surfactant Cheminformatics dry lab that scripts/start.sh started.

ROOT=$(cd "$(dirname "$0")/.." && pwd) || exit 1
PID_FILE="$ROOT/.lab.pid"
stopped=0
if [ -f "$PID_FILE" ]; then
  pid=$(cat "$PID_FILE")
  if kill "$pid" 2>/dev/null; then stopped=1; fi
fi
rm -f "$PID_FILE" "$ROOT/.lab.port"
if [ "$stopped" -eq 1 ]; then
  echo "The lab has been stopped."
else
  echo "No running lab was found."
fi
