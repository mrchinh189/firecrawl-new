#!/usr/bin/env bash
# Wrapper for cron: runs the tracker from this directory and appends to a log.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
"$PY" -m nvl_tracker.tracker "$@" >> "logs/tracker-$(date +%Y-%m).log" 2>&1
