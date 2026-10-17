#!/bin/sh
set -eu
case "${PORT:-3000}" in *[!0-9]*|'') echo 'PORT must be a number.' >&2; exit 1;; esac
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-3000}" --workers 1
