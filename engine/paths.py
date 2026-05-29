from pathlib import Path
import sys


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "mylovelychessgame"
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    USER_DATA_DIR = PROJECT_ROOT

ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_DIR = ASSETS_DIR / "icon"
APP_ICON_PATH = ICON_DIR / "game.ico"
PIECES_DIR = ASSETS_DIR / "sprites" / "pieces"
BOARDS_DIR = ASSETS_DIR / "sprites" / "boards"
ANIMATIONS_DIR = ASSETS_DIR / "sprites" / "animations"
BUNDLED_MATCHES_DIR = ASSETS_DIR / "matches"
MATCHES_DIR = USER_DATA_DIR / "matches" if getattr(sys, "frozen", False) else BUNDLED_MATCHES_DIR
ENGINES_DIR = USER_DATA_DIR / "engines"
