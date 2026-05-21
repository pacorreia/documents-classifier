#!/usr/bin/env bash
# Build documents-classifier as a standalone binary using PyInstaller.
# Run from inside the documents-classifier directory with the venv active.
#
#   source .venv/bin/activate
#   bash build.sh
#
# Output: ./dist/documents-classifier  (single self-contained executable)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Require an active virtual environment to avoid polluting the global Python install.
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Error: no virtual environment is active."
  echo "Run:  python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "── Installing PyInstaller ────────────────────────────────────────"
pip install --quiet pyinstaller

echo "── Building binary ───────────────────────────────────────────────"
pyinstaller --clean --noconfirm documents-classifier.spec

echo ""
echo "Binary built: $SCRIPT_DIR/dist/documents-classifier"
echo ""
echo "Copy it alongside config.yaml and run:"
echo "  GITHUB_TOKEN=ghp_... ./documents-classifier /path/to/cvs/"
