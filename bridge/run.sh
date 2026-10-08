#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn app:app --host 127.0.0.1 --port "${OMEGA_BRIDGE_PORT:-8765}"
