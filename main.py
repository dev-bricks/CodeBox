#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeBox - Multi-Language Code Editor
Based on PythonBox v8

Author: Lukas
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from features.theme_manager import DEFAULT_THEME, apply_theme


def load_app_icon() -> QIcon:
    icon_path = Path(__file__).with_name("CodeBox.ico")
    return QIcon(str(icon_path)) if icon_path.exists() else QIcon()


def main():
    """Entry point for CodeBox."""
    app = QApplication(sys.argv)
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    apply_theme(app, DEFAULT_THEME)

    from ui.main_window import MainWindow
    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
