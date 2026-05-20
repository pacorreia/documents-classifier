#!/usr/bin/env bash
# Build cv-classifier as a standalone binary using PyInstaller.
# Run from inside the cv-classifier directory with the venv active.
#
#   source .venv/bin/activate
#   bash build.sh
#
# Output: ./dist/cv-classifier  (single self-contained executable)

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
pyinstaller \
  --onefile \
  --name cv-classifier \
  --hidden-import=pdfminer \
  --hidden-import=pdfminer.high_level \
  --hidden-import=pdfminer.layout \
  --hidden-import=pdfminer.pdfpage \
  --hidden-import=pdfminer.pdfinterp \
  --hidden-import=pdfminer.converter \
  --hidden-import=docx \
  --hidden-import=docx.oxml \
  --hidden-import=docx.oxml.ns \
  --hidden-import=docx.parts \
  --hidden-import=docx.parts.document \
  --hidden-import=yaml \
  --clean \
  --noconfirm \
  classifier.py

echo ""
echo "Binary built: $SCRIPT_DIR/dist/cv-classifier"
echo ""
echo "Copy it alongside config.yaml and run:"
echo "  GITHUB_TOKEN=ghp_... ./cv-classifier /path/to/cvs/"
