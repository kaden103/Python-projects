"""Save the best score between games: in the browser's localStorage on the web,
or in a small JSON file in the home folder on desktop."""

import json
import sys
from pathlib import Path


STORAGE_KEY = "spiderman_best"
SAVE_FILE = Path.home() / ".spiderman_game_best.json"


def load_best():
    try:
        if sys.platform == "emscripten":
            import platform

            raw = platform.window.localStorage.getItem(STORAGE_KEY)
        else:
            raw = SAVE_FILE.read_text() if SAVE_FILE.exists() else None
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_best(data):
    try:
        raw = json.dumps(data)
        if sys.platform == "emscripten":
            import platform

            platform.window.localStorage.setItem(STORAGE_KEY, raw)
        else:
            SAVE_FILE.write_text(raw)
    except Exception:
        pass  # Saving is a bonus; never crash the game over it
