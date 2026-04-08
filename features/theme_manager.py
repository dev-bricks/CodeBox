"""Theme Manager for CodeBox.

Loads QSS stylesheets from the themes/ directory and applies them to the application.
Supports runtime theme switching.
"""

from pathlib import Path
from typing import List, Optional


THEMES_DIR = Path(__file__).parent.parent / "themes"


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
    app.setStyleSheet(qss)
    return True
