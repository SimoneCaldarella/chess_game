from __future__ import annotations

import threading
from pathlib import Path

import chess
import chess.engine
import chess.pgn
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from tkinter import filedialog, messagebox, simpledialog, ttk

from engine.assets import SpriteLibrary, SpriteTheme
from engine.paths import APP_ICON_PATH, MATCHES_DIR, PROJECT_ROOT
from engine.pgn import PgnLibrary, create_local_game, format_move_list
from engine.stockfish import StockfishManager
from graphics.board_view import BOARD_SIZE, BoardView


SIDEBAR_WIDTH = 320
WINDOW_WIDTH = BOARD_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = BOARD_SIZE


class ChessApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Chess Engine From Scratch")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.app_icon: ImageTk.PhotoImage | None = self._load_app_icon()
        if self.app_icon:
            self.root.iconphoto(True, self.app_icon)

        self.sprite_library = SpriteLibrary()
        self.pgn_library = PgnLibrary()
        self.themes = self.sprite_library.discover_piece_themes()
        if not self.themes:
            raise RuntimeError("No usable piece sprite theme found in assets/sprites/pieces.")
        self.selected_theme = self.themes[0]

        self.board_view = BoardView(self.root, self.on_board_click)
        self.sidebar = ttk.Frame(self.root, width=SIDEBAR_WIDTH, padding=16)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.sidebar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Select a sprite theme to begin.")
        self.move_list_var = tk.StringVar(value="")

        self.mode = "menu"
        self.player_color = chess.WHITE
        self.engine: chess.engine.SimpleEngine | None = None
        self.engine_thinking = False
        self.move_animating = False

        self.board = chess.Board()
        self.game = chess.pgn.Game()
        self.current_node: chess.pgn.ChildNode | chess.pgn.Game = self.game
        self.selected_square: chess.Square | None = None
        self.legal_targets: set[chess.Square] = set()
        self.last_move: chess.Move | None = None
        self.replay_moves: list[chess.Move] = []
        self.replay_index = 0

        self.show_sprite_selection()

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self._shutdown_engine()
        self.root.destroy()

    def show_sprite_selection(self) -> None:
        self.mode = "sprite_selection"
        self.board_view.stop_endgame_animation()
        self._clear_sidebar()
        self._shutdown_engine()
        self._reset_board_state()

        ttk.Label(self.sidebar, text="Sprite Library", font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(self.sidebar, text="Choose the pieces before starting.").pack(anchor="w", pady=(4, 16))

        self._add_theme_selector()
        ttk.Button(self.sidebar, text="Continue", command=self.show_mode_selection).pack(fill=tk.X, pady=(24, 8))
        ttk.Label(self.sidebar, textvariable=self.status_var, wraplength=280).pack(anchor="w", pady=(16, 0))

        self.board_view.load_theme(self.selected_theme)
        self.board_view.load_board(None)
        self.draw_board()

    def show_mode_selection(self) -> None:
        self.mode = "mode_selection"
        self._clear_sidebar()

        ttk.Label(self.sidebar, text="New Session", font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(self.sidebar, text=f"Pieces: {self.selected_theme.name}").pack(anchor="w", pady=(4, 20))
        ttk.Button(self.sidebar, text="Play with a Friend", command=self.start_friend_game).pack(fill=tk.X, pady=5)
        ttk.Button(self.sidebar, text="Play with Stockfish", command=self.start_stockfish_game).pack(fill=tk.X, pady=5)
        ttk.Button(self.sidebar, text="Load Existing Match", command=self.show_match_loader).pack(fill=tk.X, pady=5)
        ttk.Button(self.sidebar, text="Back to Sprites", command=self.show_sprite_selection).pack(fill=tk.X, pady=(28, 5))
        ttk.Label(self.sidebar, textvariable=self.status_var, wraplength=280).pack(anchor="w", pady=(16, 0))

        self.status_var.set("Choose how you want to play.")
        self.draw_board()

    def start_friend_game(self) -> None:
        self._start_playing_game("friend")

    def start_stockfish_game(self) -> None:
        self.player_color = chess.WHITE if messagebox.askyesno("Choose side", "Play as White?") else chess.BLACK
        engine_path = self._ensure_stockfish()
        if not engine_path:
            self.status_var.set("Stockfish mode cancelled.")
            return

        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(str(engine_path))
        except Exception as exc:
            messagebox.showerror("Stockfish error", f"Could not start Stockfish:\n{exc}")
            return

        self._start_playing_game("stockfish")
        if self.board.turn != self.player_color:
            self.request_engine_move()

    def show_match_loader(self) -> None:
        self.mode = "load_match"
        self._clear_sidebar()

        ttk.Label(self.sidebar, text="Load PGN", font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(self.sidebar, text="Choose a saved match to replay.").pack(anchor="w", pady=(4, 12))

        pgn_files = self.pgn_library.list_games()
        listbox = tk.Listbox(self.sidebar, height=12)
        listbox.pack(fill=tk.BOTH, expand=True)
        for path in pgn_files:
            listbox.insert(tk.END, path.name)
        if pgn_files:
            listbox.selection_set(0)

        ttk.Button(
            self.sidebar,
            text="Load Selected",
            command=lambda: self._load_listbox_selection(listbox, pgn_files),
        ).pack(fill=tk.X, pady=(12, 5))
        ttk.Button(self.sidebar, text="Browse PGN...", command=self.browse_pgn).pack(fill=tk.X, pady=5)
        ttk.Button(self.sidebar, text="Back", command=self.show_mode_selection).pack(fill=tk.X, pady=(20, 5))

        self.status_var.set("PGN files are read from assets/matches.")
        self.draw_board()

    def browse_pgn(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=str(MATCHES_DIR),
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
        )
        if path:
            self.load_pgn_file(Path(path))

    def load_pgn_file(self, path: Path) -> None:
        self.board_view.stop_endgame_animation()
        game = self.pgn_library.load_game(path)
        if not game:
            messagebox.showerror("PGN error", f"No game found in {path.name}.")
            return

        self.mode = "replay"
        self.game = game
        self.board = game.board()
        self.replay_moves = list(game.mainline_moves())
        self.replay_index = 0
        self._clear_selection()
        self.last_move = None

        self._clear_sidebar()
        white = game.headers.get("White", "White")
        black = game.headers.get("Black", "Black")
        ttk.Label(self.sidebar, text=path.name, font=("Helvetica", 18, "bold"), wraplength=280).pack(anchor="w")
        ttk.Label(self.sidebar, text=f"{white} vs {black}", wraplength=280).pack(anchor="w", pady=(4, 12))
        ttk.Label(self.sidebar, textvariable=self.status_var, wraplength=280).pack(anchor="w", pady=(0, 12))

        bottom = ttk.Frame(self.sidebar)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(bottom, text="Next Step", command=self.next_replay_step).pack(side=tk.RIGHT, pady=8)
        ttk.Button(bottom, text="New Session", command=self.show_sprite_selection).pack(side=tk.LEFT, pady=8)

        self.status_var.set(f"Move 0 of {len(self.replay_moves)}.")
        self.draw_board()

    def next_replay_step(self) -> None:
        if self.move_animating:
            return
        if self.replay_index >= len(self.replay_moves):
            self.status_var.set("Replay complete.")
            return

        move = self.replay_moves[self.replay_index]
        is_capture = self.board.is_capture(move)

        def commit_replay_move() -> None:
            self.board.push(move)
            self.last_move = move
            self.replay_index += 1
            self.status_var.set(f"Move {self.replay_index} of {len(self.replay_moves)}: {move.uci()}")
            self.draw_board()
            self.move_animating = False
            self._play_post_move_animations(is_capture)

        self._animate_then(move, commit_replay_move)

    def on_board_click(self, event: tk.Event) -> None:
        if not self._can_accept_player_move():
            return

        square = self.board_view.square_from_event(event)
        if square is None:
            return
        piece = self.board.piece_at(square)

        if self.selected_square is None:
            if piece and piece.color == self.board.turn:
                self._select_square(square)
            return

        if square == self.selected_square:
            self._clear_selection()
            self.draw_board()
            return

        move = self._candidate_move(self.selected_square, square)
        if move in self.board.legal_moves:
            def after_player_move() -> None:
                if self.mode == "stockfish" and not self.board.is_game_over():
                    self.request_engine_move()

            self.play_move(move, after_move=after_player_move)
        elif piece and piece.color == self.board.turn:
            self._select_square(square)
        else:
            self._clear_selection()
            self.draw_board()

    def play_move(self, move: chess.Move, after_move=None) -> None:
        is_capture = self.board.is_capture(move)

        def commit_move() -> None:
            self.board.push(move)
            self.current_node = self.current_node.add_variation(move)
            self.last_move = move
            self._clear_selection()
            self.update_status()
            self.draw_board()
            self.move_animating = False
            self._play_post_move_animations(is_capture)
            if after_move:
                after_move()

        self._animate_then(move, commit_move)

    def request_engine_move(self) -> None:
        if not self.engine or self.engine_thinking:
            return

        self.engine_thinking = True
        self.status_var.set("Stockfish is thinking...")
        board_copy = self.board.copy()

        def think() -> None:
            try:
                result = self.engine.play(board_copy, chess.engine.Limit(time=0.4))
                self.root.after(0, lambda: self.finish_engine_move(result.move))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Stockfish error", str(exc)))
                self.root.after(0, self._engine_done)

        threading.Thread(target=think, daemon=True).start()

    def finish_engine_move(self, move: chess.Move) -> None:
        self.engine_thinking = False
        if move in self.board.legal_moves:
            self.play_move(move)
        else:
            self.update_status()

    def save_current_pgn(self) -> None:
        self.board_view.stop_endgame_animation()
        self.game.headers["Result"] = self.board.result() if self.board.is_game_over() else "*"
        filename = simpledialog.askstring("Save PGN", "File name:", initialvalue=self.pgn_library.default_save_name())
        if not filename:
            return

        path = self.pgn_library.save_game(self.game, filename)
        self.status_var.set(f"Saved {path.relative_to(PROJECT_ROOT)}")

    def draw_board(self) -> None:
        self.board_view.draw(self.board, self.selected_square, self.legal_targets, self.last_move)

    def update_status(self) -> None:
        if self.board.is_game_over():
            self.status_var.set(f"Game over: {self.board.result()}. You can save the PGN or start a new session.")
        else:
            color = "White" if self.board.turn == chess.WHITE else "Black"
            self.status_var.set(f"{color} to move.")
        self.move_list_var.set(format_move_list(self.game))

    def _play_post_move_animations(self, is_capture: bool) -> None:
        is_game_over = self.board.is_game_over()
        if is_capture and is_game_over:
            self.board_view.play_capture_animation(on_complete=self.board_view.play_endgame_animation)
        elif is_capture:
            self.board_view.play_capture_animation()
        elif is_game_over:
            self.board_view.play_endgame_animation()

    def _animate_then(self, move: chess.Move, on_complete) -> None:
        self.move_animating = True
        self.board_view.animate_move(
            self.board,
            move,
            self.selected_square,
            self.legal_targets,
            self.last_move,
            on_complete,
        )

    def _start_playing_game(self, mode: str) -> None:
        self.board_view.stop_endgame_animation()
        self.mode = mode
        self._reset_board_state()
        self.game = create_local_game()
        self.current_node = self.game
        self._show_game_controls()
        self.draw_board()

    def _show_game_controls(self) -> None:
        self._clear_sidebar()
        title = "Friend Game" if self.mode == "friend" else "Stockfish Game"
        ttk.Label(self.sidebar, text=title, font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(self.sidebar, textvariable=self.status_var, wraplength=280).pack(anchor="w", pady=(8, 12))
        ttk.Button(self.sidebar, text="Save PGN", command=self.save_current_pgn).pack(fill=tk.X, pady=5)
        ttk.Button(self.sidebar, text="New Session", command=self.show_sprite_selection).pack(fill=tk.X, pady=5)
        ttk.Separator(self.sidebar).pack(fill=tk.X, pady=14)
        ttk.Label(self.sidebar, text="Moves", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(self.sidebar, textvariable=self.move_list_var, wraplength=280, justify=tk.LEFT).pack(anchor="w", pady=(6, 0))
        self.update_status()

    def _add_theme_selector(self) -> None:
        theme_names = [theme.name for theme in self.themes]
        theme_var = tk.StringVar(value=self.selected_theme.name)
        combo = ttk.Combobox(self.sidebar, textvariable=theme_var, values=theme_names, state="readonly")
        combo.pack(fill=tk.X)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._select_theme(theme_var.get()))

    def _select_theme(self, name: str) -> None:
        self.selected_theme = self._theme_named(name)
        self.board_view.load_theme(self.selected_theme)
        suffix = " with automatic role mapping" if self.selected_theme.uses_fallback_mapping else ""
        self.status_var.set(f"Selected pieces: {self.selected_theme.name}{suffix}")
        self.draw_board()

    def _theme_named(self, name: str) -> SpriteTheme:
        for theme in self.themes:
            if theme.name == name:
                return theme
        return self.selected_theme

    def _load_listbox_selection(self, listbox: tk.Listbox, pgn_files: list[Path]) -> None:
        selection = listbox.curselection()
        if not selection:
            messagebox.showinfo("No match selected", "Choose a PGN from the list first.")
            return
        self.load_pgn_file(pgn_files[selection[0]])

    def _ensure_stockfish(self) -> Path | None:
        manager = StockfishManager(self.status_var.set)
        engine_path = manager.find_engine()
        if engine_path:
            return engine_path

        should_download = messagebox.askyesno(
            "Stockfish not found",
            "Stockfish is not installed. Download the engine for this computer now?",
        )
        if not should_download:
            return None

        try:
            return manager.download_engine()
        except Exception as exc:
            messagebox.showerror("Stockfish download failed", str(exc))
            return None

    def _can_accept_player_move(self) -> bool:
        if self.mode not in {"friend", "stockfish"}:
            return False
        if self.move_animating or self.engine_thinking or self.board.is_game_over():
            return False
        return not (self.mode == "stockfish" and self.board.turn != self.player_color)

    def _candidate_move(self, source: chess.Square, target: chess.Square) -> chess.Move:
        piece = self.board.piece_at(source)
        promotion = None
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(target) in {0, 7}:
            promotion = chess.QUEEN
        return chess.Move(source, target, promotion=promotion)

    def _select_square(self, square: chess.Square) -> None:
        self.selected_square = square
        self.legal_targets = {move.to_square for move in self.board.legal_moves if move.from_square == square}
        self.draw_board()

    def _clear_selection(self) -> None:
        self.selected_square = None
        self.legal_targets = set()

    def _reset_board_state(self) -> None:
        self.board = chess.Board()
        self._clear_selection()
        self.last_move = None
        self.replay_moves = []
        self.replay_index = 0
        self.move_animating = False

    def _engine_done(self) -> None:
        self.engine_thinking = False
        self.update_status()

    def _shutdown_engine(self) -> None:
        if self.engine:
            self.engine.quit()
            self.engine = None
        self.engine_thinking = False
        self.move_animating = False

    def _clear_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()

    def _load_app_icon(self) -> ImageTk.PhotoImage | None:
        if not APP_ICON_PATH.exists():
            return None
        try:
            image = Image.open(APP_ICON_PATH).convert("RGBA")
            image = image.resize((128, 128), Image.LANCZOS)
            mask = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(mask)
            radius = round(image.size[0] * 0.22)
            draw.rounded_rectangle((0, 0, image.size[0] - 1, image.size[1] - 1), radius=radius, fill=255)
            image.putalpha(mask)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None
