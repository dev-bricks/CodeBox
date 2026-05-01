"""Theme Manager for CodeBox.

Loads QSS stylesheets from the themes/ directory and applies them to the application.
Supports runtime theme switching.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette


THEMES_DIR = Path(__file__).parent.parent / "themes"
DEFAULT_THEME = "dark"


def get_available_themes() -> List[str]:
    """Returns a list of available theme names (without .qss extension)."""
    if not THEMES_DIR.exists():
        return []
    return sorted(p.stem for p in THEMES_DIR.glob("*.qss"))


def load_theme(name: str) -> Optional[str]:
    """Loads the QSS content for the given theme name.

    Args:
        name: Theme name (e.g. 'dark', 'light').

    Returns:
        QSS string, or None if theme file not found.
    """
    path = THEMES_DIR / f"{name}.qss"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _build_dark_palette() -> QPalette:
    palette = QPalette()
    dark_color = QColor(40, 40, 40)

    palette.setColor(QPalette.ColorRole.Window, dark_color)
    palette.setColor(QPalette.ColorRole.WindowText, Qt.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, dark_color)
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.black)
    return palette


def _build_light_palette() -> QPalette:
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, Qt.white)
    palette.setColor(QPalette.ColorRole.WindowText, Qt.black)
    palette.setColor(QPalette.ColorRole.Base, Qt.white)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(243, 243, 243))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.black)
    palette.setColor(QPalette.ColorRole.Text, Qt.black)
    palette.setColor(QPalette.ColorRole.Button, QColor(243, 243, 243))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.black)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.white)
    return palette


def build_palette(name: str) -> QPalette:
    """Build the palette that belongs to a theme name."""
    if name == "light":
        return _build_light_palette()
    return _build_dark_palette()


def apply_theme(app, name: str) -> bool:
    """Applies a theme to the QApplication.

    Args:
        app: QApplication instance.
        name: Theme name.

    Returns:
        True if theme was applied, False if theme not found.
    """
    qss = load_theme(name)
    if qss is None:
        return False
    app.setStyle("Fusion")
    app.setPalette(build_palette(name))
    app.setStyleSheet(qss)
    return True
