# Chess Engine From Scratch

Run the graphical chess game:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Build a macOS `.app` bundle:

```bash
chmod +x build_macos_app.sh
./build_macos_app.sh
```

The standalone app is created at `dist/ChessEngineFromScratch.app`.

The build script creates a local `.venv`, installs the required Python packages there, and bundles them into the `.app`. The standalone app does not install Python libraries globally on the target Mac.

Using a local `.venv` avoids externally managed Python errors from Homebrew or system Python. Pillow is needed by the app for image rendering and lets PyInstaller convert the `.ico` icon into the macOS app icon format.

The bundle is ad-hoc signed for local use, not notarized for public distribution. On another Mac, Gatekeeper may ask for approval the first time it opens.

When running as a bundled app, saved PGNs and downloaded Stockfish binaries are stored under `~/Library/Application Support/ChessEngineFromScratch/`.

The app starts with a sprite-library selection screen. After choosing the pieces, you can:

- play locally with a friend;
- play against Stockfish;
- load a PGN from `assets/matches` and replay it step by step.

During a friend or Stockfish game, use `Save PGN` to save the current match at any point. From source, new PGNs are saved in `assets/matches`; from the bundled app, they are saved in Application Support.

Stockfish is optional. If no Stockfish binary is found in your `PATH`, in the `STOCKFISH_EXECUTABLE` environment variable, or under `engines/`, the app can download one for your operating system when you start Stockfish mode.

Captures play a random center-board GIF from `assets/sprites/animations/kill_1.gif` through `kill_5.gif`. If the final move is also a capture, the capture animation plays first and the endgame animation starts after it. Finished games loop a random animation from the winning/losing endgame pool until you save the PGN or start a new session.

The running app uses `assets/icon/game.ico` as a rounded-square window icon when Tk supports custom icons on your platform.

Pieces animate when they move: sliding pieces hop through intermediate chess squares, pawns hop through their path, and knights hop directly to the destination.

## Sprite Sets

The selector shows every folder that has at least six white and six black PNG sprites. Standard chess sets are mapped by filename. Decorative or fairy-chess folders are mapped automatically in filename order for any missing roles, so they can still be used as normal chess pieces.

## Why `python-chess` Matters

Without `python-chess`, this project would need a full chess rules engine: legal moves for every piece, checks, checkmate, stalemate, castling, en passant, promotion, pins, move history, board notation, PGN parsing/export, replay, and UCI communication with Stockfish. That is a substantial project on its own and very easy to get subtly wrong.

Using `python-chess` lets this app focus on the graphical interface, sprites, PGN browsing, saving, replay, and Stockfish integration instead of reimplementing the rules of chess from scratch.
