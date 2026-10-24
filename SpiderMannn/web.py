"""Browser helpers for the pygbag web build. Everything here is a no-op on desktop."""

import sys


ON_WEB = sys.platform == "emscripten"


def _window():
    import platform

    return platform.window


def is_touch_device():
    """True for phones and tablets (a finger is the main pointer)."""
    if not ON_WEB:
        return False
    try:
        return bool(_window().matchMedia("(pointer: coarse)").matches)
    except Exception:
        return False


def is_landscape():
    try:
        window = _window()
        return window.innerWidth > window.innerHeight
    except Exception:
        return False


def fit_canvas(width, height):
    """Scale the page's canvas to the largest size that fits the screen at this aspect ratio."""
    if not ON_WEB:
        return
    try:
        window = _window()
        tall = "100dvh" if window.CSS.supports("height", "100dvh") else "100vh"
        style = window.canvas.style
        style.setProperty("width", f"min(100vw, calc({tall} * {width} / {height}))", "important")
        style.setProperty("height", f"min({tall}, calc(100vw * {height} / {width}))", "important")
    except Exception:
        pass
