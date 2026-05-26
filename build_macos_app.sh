#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pyinstaller
.venv/bin/python -m PyInstaller --clean --noconfirm ChessEngineFromScratch.spec

echo "Built dist/ChessEngineFromScratch.app"
