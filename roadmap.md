# Chess Game Roadmap

## Completed

- Inspected the current project structure and confirmed the app was still a scaffold.
- Built a Tkinter chess window in `engine/match.py`.
- Added sprite theme discovery from `assets/sprites/pieces`.
- Added a first-screen sprite selector.
- Added a graphical 8x8 board using the selected piece sprites.
- Added local friend mode with legal move validation through `python-chess`.
- Added optional Stockfish mode using `python-chess` UCI integration.
- Added a Stockfish manager that searches for an existing engine, then can download a compatible release for the current OS.
- Added PGN loading from `assets/matches`.
- Added step-by-step PGN replay with a `Next Step` button in the lower-right control area.
- Added PGN saving at any time during or after a played game.
- Added return-to-sprite-selection flow after a game or replay.
- Updated `main.py` to launch the app directly.
- Added a minimal player README.
- Refactored the first implementation into focused OOP modules:
  - `engine/app.py` for the application controller and UI flow.
  - `engine/assets.py` for sprite discovery.
  - `engine/pgn.py` for PGN loading, saving, and formatting.
  - `engine/stockfish.py` for Stockfish lookup and download.
  - `graphics/board_view.py` for board rendering and click-to-square conversion.
  - `engine/match.py` as the small launch wrapper.
- Added capture animation support. The app looks first in `assets/sprites/animations/kill` and falls back to GIFs in `assets/sprites/animations`.
- Documented why only complete standard piece sets are shown in the selector.
- Documented the engineering work avoided by using `python-chess`.
- Expanded piece theme discovery to include nonstandard folders with at least six white and six black sprites by auto-mapping missing chess roles.
- Removed board selection and standardized the app on the built-in board.
- Added a separate endgame animation that plays `assets/sprites/animations/winning.gif` when a game ends.
- Sequenced final captures so the capture animation completes before the endgame animation starts.
- Made the endgame animation loop until the user saves the PGN or starts a new session.
- Added a rounded-square app icon from `assets/icon/game.ico`.
- Added chess-piece movement animation so moves hop through intermediate squares instead of teleporting to the destination.
- Randomized capture animations across `kill_1.gif` through `kill_5.gif`.
- Randomized endgame animations across the available winning and losing GIFs.
- Added PyInstaller packaging via `ChessEngineFromScratch.spec` and `build_macos_app.sh` for a macOS `.app` bundle.
- Adjusted frozen-app paths so bundled assets are read from the app resources while saved PGNs and Stockfish downloads go to user Application Support.

## Current Behavior

- Run the game with `python3 main.py`.
- Select a piece sprite set first.
- Choose friend play, Stockfish play, or PGN replay.
- Saved games are written to `assets/matches`.

## Next Improvements

- Add curated board themes if a future UI needs board selection again.
- Add promotion piece selection instead of auto-promoting pawns to queens.
- Add move undo for friend and Stockfish games.
- Add captured-piece panels and clocks.
- Add configurable Stockfish strength and thinking time.
- Add automated GUI smoke tests where a display server is available.
- Add manual piece-role mappings so nonstandard asset packs can be curated instead of relying on filename-order fallback.
