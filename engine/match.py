from engine.app import ChessApp


def run_chess_game() -> int:
    app = ChessApp()
    app.run()
    return 0
