from __future__ import annotations

import math
import random
import tkinter as tk
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable

import chess
from PIL import Image, ImageTk

from engine.assets import SpriteTheme
from engine.paths import ANIMATIONS_DIR


BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8

LIGHT_SQUARE = "#ffffff"
DARK_SQUARE = "#3f9bd3"
SELECTED_SQUARE = "#f7d750"
LEGAL_SQUARE = "#77ad78"
LAST_MOVE_SQUARE = "#b9d66b"


class BoardView:
    def __init__(self, parent: tk.Widget, on_click) -> None:
        self.canvas = tk.Canvas(parent, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        self.canvas.bind("<Button-1>", on_click)
        self.images: dict[tuple[bool, chess.PieceType], ImageTk.PhotoImage] = {}
        self.board_image: ImageTk.PhotoImage | None = None
        self.capture_animation = GifOverlay(self.canvas, find_capture_animations())
        self.endgame_animation = GifOverlay(self.canvas, find_endgame_animations(), max_size=BOARD_SIZE - 96)

    def load_board(self, board_path: Path | None) -> bool:
        self.board_image = load_board_image(board_path)
        return self.board_image is not None

    def load_theme(self, theme: SpriteTheme) -> None:
        self.images.clear()
        for key, path in theme.piece_paths.items():
            try:
                image = Image.open(path).convert("RGBA")
                image.thumbnail((SQUARE_SIZE - 12, SQUARE_SIZE - 12), Image.LANCZOS)
                self.images[key] = ImageTk.PhotoImage(image)
            except Exception:
                continue

    def draw(
        self,
        board: chess.Board,
        selected_square: chess.Square | None = None,
        legal_targets: set[chess.Square] | None = None,
        last_move: chess.Move | None = None,
    ) -> None:
        legal_targets = legal_targets or set()
        self.canvas.delete("all")
        if self.board_image:
            self.canvas.create_image(0, 0, image=self.board_image, anchor=tk.NW)

        for rank in range(8):
            for file_index in range(8):
                square = chess.square(file_index, 7 - rank)
                x = file_index * SQUARE_SIZE
                y = rank * SQUARE_SIZE
                if not self.board_image:
                    self._draw_square(x, y, file_index, rank, square, selected_square, legal_targets, last_move)
                else:
                    self._draw_overlay(x, y, square, selected_square, legal_targets, last_move)
                piece = board.piece_at(square)
                if piece:
                    self._draw_piece(piece, x, y)

        self.canvas.create_rectangle(0, 0, BOARD_SIZE, BOARD_SIZE, outline="#2d2d2d", width=2)

    def square_from_event(self, event: tk.Event) -> chess.Square | None:
        file_index = event.x // SQUARE_SIZE
        rank_index = 7 - (event.y // SQUARE_SIZE)
        if not (0 <= file_index < 8 and 0 <= rank_index < 8):
            return None
        return chess.square(file_index, rank_index)

    def play_capture_animation(self, on_complete: Callable[[], None] | None = None) -> None:
        self.capture_animation.play(on_complete=on_complete)

    def play_endgame_animation(self) -> None:
        self.endgame_animation.play(loop=True)

    def stop_endgame_animation(self) -> None:
        self.endgame_animation.stop()

    def animate_move(
        self,
        board: chess.Board,
        move: chess.Move,
        selected_square: chess.Square | None,
        legal_targets: set[chess.Square],
        last_move: chess.Move | None,
        on_complete: Callable[[], None],
    ) -> None:
        piece = board.piece_at(move.from_square)
        if not piece:
            on_complete()
            return

        animation_board = board.copy(stack=False)
        animation_board.remove_piece_at(move.from_square)
        animation_board.remove_piece_at(move.to_square)
        if board.is_en_passant(move):
            captured_square = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
            animation_board.remove_piece_at(captured_square)

        self.draw(animation_board, selected_square, legal_targets, last_move)
        item_id = self._create_piece_item(piece, *self._square_center(move.from_square))
        points = self._move_animation_points(move)
        self._animate_piece_item(item_id, points, 0, on_complete)

    def _draw_square(
        self,
        x: int,
        y: int,
        file_index: int,
        rank: int,
        square: chess.Square,
        selected_square: chess.Square | None,
        legal_targets: set[chess.Square],
        last_move: chess.Move | None,
    ) -> None:
        color = LIGHT_SQUARE if (file_index + rank) % 2 == 0 else DARK_SQUARE
        if last_move and square in {last_move.from_square, last_move.to_square}:
            color = LAST_MOVE_SQUARE
        if square == selected_square:
            color = SELECTED_SQUARE
        elif square in legal_targets:
            color = LEGAL_SQUARE
        self.canvas.create_rectangle(x, y, x + SQUARE_SIZE, y + SQUARE_SIZE, fill=color, outline=color)

    def _draw_overlay(
        self,
        x: int,
        y: int,
        square: chess.Square,
        selected_square: chess.Square | None,
        legal_targets: set[chess.Square],
        last_move: chess.Move | None,
    ) -> None:
        color = None
        if last_move and square in {last_move.from_square, last_move.to_square}:
            color = LAST_MOVE_SQUARE
        if square == selected_square:
            color = SELECTED_SQUARE
        elif square in legal_targets:
            color = LEGAL_SQUARE
        if color:
            self.canvas.create_rectangle(x, y, x + SQUARE_SIZE, y + SQUARE_SIZE, fill=color, outline=color, stipple="gray50")

    def _draw_piece(self, piece: chess.Piece, x: int, y: int) -> None:
        self._create_piece_item(piece, x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)

    def _create_piece_item(self, piece: chess.Piece, x: int, y: int) -> int:
        image = self.images.get((piece.color, piece.piece_type))
        if image:
            return self.canvas.create_image(x, y, image=image)

        fill = "#f8f8f8" if piece.color == chess.WHITE else "#111111"
        return self.canvas.create_text(x, y, text=piece.symbol(), fill=fill, font=("Helvetica", 34, "bold"))

    def _animate_piece_item(
        self,
        item_id: int,
        points: list[tuple[int, int]],
        index: int,
        on_complete: Callable[[], None],
    ) -> None:
        if index >= len(points):
            self.canvas.delete(item_id)
            on_complete()
            return

        self.canvas.coords(item_id, *points[index])
        self.canvas.tag_raise(item_id)
        self.canvas.after(22, lambda: self._animate_piece_item(item_id, points, index + 1, on_complete))

    def _move_animation_points(self, move: chess.Move) -> list[tuple[int, int]]:
        route = [move.from_square, *intermediate_squares(move), move.to_square]
        points = []
        for source, target in zip(route, route[1:]):
            points.extend(self._jump_points(source, target))
        return points or [self._square_center(move.to_square)]

    def _jump_points(self, source: chess.Square, target: chess.Square) -> list[tuple[int, int]]:
        start_x, start_y = self._square_center(source)
        end_x, end_y = self._square_center(target)
        points = []
        frames = 8
        for frame in range(1, frames + 1):
            t = frame / frames
            x = round(start_x + (end_x - start_x) * t)
            y = round(start_y + (end_y - start_y) * t - math.sin(math.pi * t) * 18)
            points.append((x, y))
        return points

    def _square_center(self, square: chess.Square) -> tuple[int, int]:
        file_index = chess.square_file(square)
        rank_from_top = 7 - chess.square_rank(square)
        return (
            file_index * SQUARE_SIZE + SQUARE_SIZE // 2,
            rank_from_top * SQUARE_SIZE + SQUARE_SIZE // 2,
        )


class GifOverlay:
    def __init__(self, canvas: tk.Canvas, gif_paths: list[Path] | Path | None, max_size: int = BOARD_SIZE // 2) -> None:
        self.canvas = canvas
        self.max_size = max_size
        self.gif_paths = normalize_gif_paths(gif_paths)
        self.frame_cache: dict[Path, list[tuple[ImageTk.PhotoImage, int]]] = {}
        self.frames: list[tuple[ImageTk.PhotoImage, int]] = []
        self.frame_index = 0
        self.image_id: int | None = None
        self.after_id: str | None = None
        self.loop = False
        self.on_complete: Callable[[], None] | None = None

    def play(self, loop: bool = False, on_complete: Callable[[], None] | None = None) -> None:
        self.frames = self._choose_frames()
        if not self.frames:
            if on_complete:
                on_complete()
            return
        self.stop()
        self.loop = loop
        self.on_complete = on_complete
        self.frame_index = 0
        self._show_next_frame()

    def stop(self) -> None:
        if self.after_id is not None:
            self.canvas.after_cancel(self.after_id)
            self.after_id = None
        if self.image_id is not None:
            self.canvas.delete(self.image_id)
            self.image_id = None
        self.frame_index = 0
        self.loop = False
        self.on_complete = None

    def _show_next_frame(self) -> None:
        self.after_id = None
        if self.frame_index >= len(self.frames):
            if self.loop:
                self.frame_index = 0
                self._show_next_frame()
                return
            on_complete = self.on_complete
            self.stop()
            if on_complete:
                on_complete()
            return

        frame, duration = self.frames[self.frame_index]
        if self.image_id is None:
            self.image_id = self.canvas.create_image(BOARD_SIZE // 2, BOARD_SIZE // 2, image=frame)
        else:
            self.canvas.itemconfigure(self.image_id, image=frame)
        self.canvas.tag_raise(self.image_id)
        self.frame_index += 1
        self.after_id = self.canvas.after(duration, self._show_next_frame)

    def _choose_frames(self) -> list[tuple[ImageTk.PhotoImage, int]]:
        if not self.gif_paths:
            return []
        gif_path = random.choice(self.gif_paths)
        if gif_path not in self.frame_cache:
            self.frame_cache[gif_path] = self._load_frames(gif_path)
        return self.frame_cache[gif_path]

    def _load_frames(self, gif_path: Path | None) -> list[tuple[ImageTk.PhotoImage, int]]:
        if not gif_path or not gif_path.exists():
            return []

        frames = []
        with Image.open(gif_path) as image:
            for index in range(getattr(image, "n_frames", 1)):
                image.seek(index)
                frame = image.convert("RGBA")
                frame.thumbnail((self.max_size, self.max_size), Image.LANCZOS)
                duration = max(35, int(image.info.get("duration", 70)))
                frames.append((ImageTk.PhotoImage(frame), duration))
        return frames


def find_capture_animations() -> list[Path]:
    numbered = [ANIMATIONS_DIR / f"kill_{index}.gif" for index in range(1, 6)]
    existing_numbered = [path for path in numbered if path.exists()]
    if existing_numbered:
        return existing_numbered

    kill_dir = ANIMATIONS_DIR / "kill"
    search_dirs = [kill_dir, ANIMATIONS_DIR]
    for directory in search_dirs:
        if not directory.exists():
            continue
        gifs = sorted(directory.glob("*.gif"))
        if gifs:
            return gifs
    return []


def find_capture_animation() -> Path | None:
    animations = find_capture_animations()
    return animations[0] if animations else None


def intermediate_squares(move: chess.Move) -> list[chess.Square]:
    from_file = chess.square_file(move.from_square)
    from_rank = chess.square_rank(move.from_square)
    to_file = chess.square_file(move.to_square)
    to_rank = chess.square_rank(move.to_square)
    file_delta = to_file - from_file
    rank_delta = to_rank - from_rank

    if file_delta == 0:
        file_step = 0
    elif abs(file_delta) == abs(rank_delta) or rank_delta == 0:
        file_step = 1 if file_delta > 0 else -1
    else:
        return []

    if rank_delta == 0:
        rank_step = 0
    elif abs(file_delta) == abs(rank_delta) or file_delta == 0:
        rank_step = 1 if rank_delta > 0 else -1
    else:
        return []

    distance = max(abs(file_delta), abs(rank_delta))
    return [
        chess.square(from_file + file_step * step, from_rank + rank_step * step)
        for step in range(1, distance)
    ]


def find_endgame_animations() -> list[Path]:
    winning_dir = ANIMATIONS_DIR / "winning"
    losing_dir = ANIMATIONS_DIR / "losing"
    search_paths = [
        winning_dir / "winning.gif",
        ANIMATIONS_DIR / "winning.gif",
        losing_dir / "losing.gif",
        ANIMATIONS_DIR / "losing.gif",
    ]
    animations = []
    for path in search_paths:
        if path.exists():
            animations.append(path)

    for directory in (winning_dir, losing_dir):
        if directory.exists():
            animations.extend(path for path in sorted(directory.glob("*.gif")) if path not in animations)
    return animations


def find_endgame_animation() -> Path | None:
    animations = find_endgame_animations()
    return animations[0] if animations else None


def normalize_gif_paths(gif_paths: list[Path] | Path | None) -> list[Path]:
    if gif_paths is None:
        return []
    if isinstance(gif_paths, Path):
        return [gif_paths]
    return gif_paths


def load_board_image(board_path: Path | None) -> ImageTk.PhotoImage | None:
    if not board_path:
        return None

    try:
        if board_path.suffix.lower() == ".svg":
            png_bytes = render_svg_to_png(board_path)
            if not png_bytes:
                return None
            with NamedTemporaryFile(suffix=".png") as temp_file:
                temp_file.write(png_bytes)
                temp_file.flush()
                image = Image.open(temp_file.name).convert("RGBA")
        else:
            image = Image.open(board_path).convert("RGBA")
        image = image.resize((BOARD_SIZE, BOARD_SIZE), Image.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def render_svg_to_png(board_path: Path) -> bytes | None:
    try:
        import cairosvg
    except Exception:
        return None

    try:
        return cairosvg.svg2png(url=str(board_path), output_width=BOARD_SIZE, output_height=BOARD_SIZE)
    except Exception:
        return None
