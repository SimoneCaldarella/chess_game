from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chess

from engine.paths import BOARDS_DIR, PIECES_DIR


PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


@dataclass(frozen=True)
class SpriteTheme:
    name: str
    directory: Path
    piece_paths: dict[tuple[bool, chess.PieceType], Path]
    uses_fallback_mapping: bool = False


class SpriteLibrary:
    def __init__(self, pieces_dir: Path = PIECES_DIR, boards_dir: Path = BOARDS_DIR) -> None:
        self.pieces_dir = pieces_dir
        self.boards_dir = boards_dir

    def discover_piece_themes(self) -> list[SpriteTheme]:
        themes = []
        for directory in sorted(path for path in self.pieces_dir.iterdir() if path.is_dir()):
            theme = self._load_theme(directory)
            if theme:
                themes.append(theme)
        return themes

    def discover_boards(self) -> list[Path]:
        return sorted(path for path in self.boards_dir.glob("*") if path.is_file())

    def _load_theme(self, directory: Path) -> SpriteTheme | None:
        piece_paths: dict[tuple[bool, chess.PieceType], Path] = {}
        color_paths = {chess.WHITE: [], chess.BLACK: []}
        for path in directory.glob("*.png"):
            parsed = parse_piece_sprite(path)
            if parsed:
                piece_paths[parsed] = path
            color = parse_sprite_color(path)
            if color is not None:
                color_paths[color].append(path)

        if is_complete_theme(piece_paths):
            return SpriteTheme(directory.name, directory, piece_paths)

        fallback = build_fallback_mapping(piece_paths, color_paths)
        if not fallback:
            return None
        return SpriteTheme(directory.name, directory, fallback, uses_fallback_mapping=True)


def parse_piece_sprite(path: Path) -> tuple[bool, chess.PieceType] | None:
    name = path.stem.lower()
    color = parse_sprite_color(path)
    if color is None:
        return None

    for piece_type, piece_name in PIECE_NAMES.items():
        if name.endswith(piece_name) or f"-{piece_name}" in name:
            return color, piece_type
    return None


def parse_sprite_color(path: Path) -> bool | None:
    name = path.stem.lower()
    if name.startswith("w-"):
        return chess.WHITE
    if name.startswith("b-"):
        return chess.BLACK
    return None


def is_complete_theme(piece_paths: dict[tuple[bool, chess.PieceType], Path]) -> bool:
    return all(
        (color, piece_type) in piece_paths
        for color in (chess.WHITE, chess.BLACK)
        for piece_type in PIECE_NAMES
    )


def build_fallback_mapping(
    known_paths: dict[tuple[bool, chess.PieceType], Path],
    color_paths: dict[bool, list[Path]],
) -> dict[tuple[bool, chess.PieceType], Path] | None:
    mapped = dict(known_paths)
    for color in (chess.WHITE, chess.BLACK):
        available = sorted(color_paths[color], key=lambda path: path.name.lower())
        if len(available) < len(PIECE_NAMES):
            return None

        unused = [path for path in available if path not in mapped.values()]
        for piece_type in PIECE_NAMES:
            key = (color, piece_type)
            if key not in mapped:
                mapped[key] = unused.pop(0)

    return mapped if is_complete_theme(mapped) else None
