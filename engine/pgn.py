from __future__ import annotations

import time
from pathlib import Path

import chess
import chess.pgn

from engine.paths import BUNDLED_MATCHES_DIR, MATCHES_DIR


class PgnLibrary:
    def __init__(self, matches_dir: Path = MATCHES_DIR, bundled_dir: Path = BUNDLED_MATCHES_DIR) -> None:
        self.matches_dir = matches_dir
        self.bundled_dir = bundled_dir
        self.matches_dir.mkdir(parents=True, exist_ok=True)

    def list_games(self) -> list[Path]:
        paths = []
        for directory in (self.bundled_dir, self.matches_dir):
            if directory.exists():
                paths.extend(directory.glob("*.pgn"))
        return sorted(set(paths), key=lambda path: path.name.lower())

    def load_game(self, path: Path) -> chess.pgn.Game | None:
        with path.open(encoding="utf-8") as handle:
            return chess.pgn.read_game(handle)

    def save_game(self, game: chess.pgn.Game, filename: str) -> Path:
        if not filename.endswith(".pgn"):
            filename += ".pgn"
        path = self.matches_dir / Path(filename).name
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        path.write_text(game.accept(exporter), encoding="utf-8")
        return path

    @staticmethod
    def default_save_name() -> str:
        return f"saved_{time.strftime('%Y%m%d_%H%M%S')}.pgn"


def create_local_game() -> chess.pgn.Game:
    game = chess.pgn.Game()
    game.headers["Event"] = "mylovelychessgame"
    game.headers["Site"] = "Local"
    game.headers["Date"] = time.strftime("%Y.%m.%d")
    game.headers["White"] = "White"
    game.headers["Black"] = "Black"
    game.headers["Result"] = "*"
    return game


def format_move_list(game: chess.pgn.Game, max_full_moves: int = 18) -> str:
    board = game.board()
    chunks = []
    for index, move in enumerate(game.mainline_moves(), start=1):
        san = board.san(move)
        board.push(move)
        if index % 2 == 1:
            chunks.append(f"{(index + 1) // 2}. {san}")
        else:
            chunks[-1] += f" {san}"
    return "  ".join(chunks[-max_full_moves:]) or "No moves yet."
