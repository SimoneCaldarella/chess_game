from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from engine.paths import ENGINES_DIR


class StockfishManager:
    """Finds or downloads a Stockfish binary for python-chess."""

    def __init__(self, status: Callable[[str], None] | None = None) -> None:
        self.status = status or (lambda _message: None)

    def find_engine(self) -> Path | None:
        candidates = [
            os.environ.get("STOCKFISH_EXECUTABLE"),
            shutil.which("stockfish"),
        ]
        candidates.extend(str(path) for path in ENGINES_DIR.rglob("stockfish*") if path.is_file())
        for candidate in candidates:
            if candidate and Path(candidate).exists() and os.access(candidate, os.X_OK):
                return Path(candidate)
        return None

    def download_engine(self) -> Path:
        ENGINES_DIR.mkdir(parents=True, exist_ok=True)
        self.status("Finding latest Stockfish release...")
        req = urllib.request.Request(
            "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest",
            headers={"User-Agent": "ChessEngineFromScratch"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            release = json.loads(response.read().decode("utf-8"))

        asset = self._pick_asset(release.get("assets", []))
        if not asset:
            raise RuntimeError("No compatible Stockfish release asset was found for this OS.")

        archive_path = ENGINES_DIR / asset["name"]
        self.status(f"Downloading {asset['name']}...")
        urllib.request.urlretrieve(asset["browser_download_url"], archive_path)

        extract_dir = ENGINES_DIR / archive_path.stem.replace(".tar", "")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_dir)
        else:
            with tarfile.open(archive_path) as archive:
                archive.extractall(extract_dir)

        engine_path = self._find_extracted_binary(extract_dir)
        if not engine_path:
            raise RuntimeError("Downloaded Stockfish, but could not find the executable.")
        engine_path.chmod(engine_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.status(f"Stockfish ready: {engine_path.name}")
        return engine_path

    def _pick_asset(self, assets: list[dict]) -> dict | None:
        system = platform.system().lower()
        machine = platform.machine().lower()
        os_terms = {
            "darwin": ["mac", "apple", "osx"],
            "linux": ["linux"],
            "windows": ["windows", "win"],
        }.get(system, [system])
        arch_terms = ["x86-64", "x86_64", "amd64"] if "64" in machine else [machine]
        if system == "darwin" and machine in {"arm64", "aarch64"}:
            arch_terms = ["apple-silicon", "arm64", "aarch64"]

        matches = []
        for asset in assets:
            name = asset.get("name", "").lower()
            if not (name.endswith(".zip") or ".tar" in name):
                continue
            if any(term in name for term in os_terms):
                score = sum(term in name for term in arch_terms)
                matches.append((score, asset))
        if matches:
            return sorted(matches, key=lambda item: item[0], reverse=True)[0][1]
        return None

    def _find_extracted_binary(self, directory: Path) -> Path | None:
        for path in directory.rglob("*"):
            suffix = path.suffix.lower()
            if path.is_file() and "stockfish" in path.name.lower() and suffix not in {".txt", ".md"}:
                return path
        return None
