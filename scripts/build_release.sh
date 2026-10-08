#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${1:-${PROJECT_DIR}/OMEGA_RELEASE.zip}"

rm -f "$OUTPUT"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

rsync -a "$PROJECT_DIR/" "$TMP_DIR/OMEGA/" \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.log' \
  --exclude '*.bak*' \
  --exclude '*.tsbuildinfo' \
  --exclude 'backend/omega.db' \
  --exclude 'backend/omega.db-wal' \
  --exclude 'backend/omega.db-shm' \
  --exclude 'storage/' \
  --exclude '.test_runtime/' \
  --exclude 'OMEGA_RELEASE.zip'

if find "$TMP_DIR/OMEGA" -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '.env' \) | grep -q .; then
  echo 'ERRO: artefato proibido encontrado no release.' >&2
  exit 1
fi

(
  cd "$TMP_DIR"
  zip -qr "$OUTPUT" OMEGA
)

echo "Release criado: $OUTPUT"
