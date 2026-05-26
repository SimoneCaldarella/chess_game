#!/usr/bin/env bash
set -euo pipefail

python3 -m PyInstaller --clean --noconfirm ChessEngineFromScratch.spec

echo "Built dist/ChessEngineFromScratch.app"
