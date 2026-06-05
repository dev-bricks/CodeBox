#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeBox - Multi-Language Code Editor
Based on PythonBox v8

Author: Lukas
"""

import argparse
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


def parse_launch_args(argv=None):
    """Extract startup file arguments and leave unknown Qt args untouched."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--open", dest="open_path")
    args, qt_args = parser.parse_known_args(list(argv or []))

    startup_path = Path(args.open_path).expanduser() if args.open_path else None
    if startup_path is None and qt_args and not qt_args[0].startswith("-"):
        startup_path = Path(qt_args[0]).expanduser()
        qt_args = qt_args[1:]
    return startup_path, qt_args


def _should_replace_startup_placeholder(window) -> bool:
    """Detect the initial empty tab created during window bootstrap."""
    tab = window.tab_widget.current_tab()
    return bool(
        tab
        and window.tab_widget.count() == 1
        and tab.file_path is None
        and not tab.is_modified
        and not tab.editor.toPlainText()
    )


def main(argv=None):
    """Entry point for CodeBox."""
    startup_path, qt_args = parse_launch_args(sys.argv[1:] if argv is None else argv)

    app = QApplication.instance() or QApplication([sys.argv[0], *qt_args])
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    apply_theme(app, DEFAULT_THEME)

    from ui.main_window import MainWindow
    window = MainWindow()
    replace_placeholder = _should_replace_startup_placeholder(window)
    if not icon.isNull():
        window.setWindowIcon(icon)
    if startup_path:
        opened_tab = window.open_path(startup_path)
        if opened_tab and replace_placeholder and window.tab_widget.count() > 1:
            window.tab_widget.close_tab(0)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
