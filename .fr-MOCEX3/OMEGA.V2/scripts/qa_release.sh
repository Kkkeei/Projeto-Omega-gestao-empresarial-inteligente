#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONPATH="$PWD/backend"
export OMEGA_ENV=test

echo '[1/3] Python compile'
python3 -m compileall -q backend bridge

echo '[2/3] Backend tests'
pytest -q backend/tests -ra

echo '[3/3] Bridge tests'
PYTHONPATH="$PWD/bridge" pytest -q bridge/test_app.py -ra

echo 'QA concluído. Frontend exige Node.js/npm: execute npm ci && npm run build em ambiente com Node.js.'
