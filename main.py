#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeBox - Multi-Language Code Editor
Based on PythonBox v8

Author: Lukas
Version: 0.1.0
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


def set_dark_theme(app):
    """Apply a dark Fusion palette and stylesheet to the QApplication.

    Args:
        app: QApplication instance to style.
    """
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_color = QColor(40, 40, 40)

    dark_palette.setColor(QPalette.ColorRole.Window, dark_color)
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, dark_color)
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.black)

    app.setPalette(dark_palette)
    app.setStyleSheet("""
        QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace; }
        QPushButton {
            background-color: #3a3a3a; border: 1px solid #555;
            padding: 6px 12px; border-radius: 4px; color: white;
        }
        QPushButton:hover { background-color: #4a4a4a; border-color: #2a82da; }
        QPushButton:pressed { background-color: #2a82da; }
        QSplitter::handle { background-color: #444; width: 2px; }
        QMenuBar { background-color: #353535; color: white; }
        QMenuBar::item:selected { background-color: #2a82da; }
        QMenu { background-color: #353535; color: white; border: 1px solid #555; }
        QMenu::item:selected { background-color: #2a82da; }
        QTabWidget::pane { border: 1px solid #444; background: #1e1e1e; }
        QTabBar::tab {
            background: #353535; color: #aaa; padding: 8px 16px;
            border: 1px solid #444; border-bottom: none; margin-right: 2px;
        }
        QTabBar::tab:selected { background: #1e1e1e; color: white; }
        QTabBar::tab:hover { background: #4a4a4a; }
        QLineEdit {
            background: #2a2a2a; border: 1px solid #555; color: white;
            padding: 4px 8px; border-radius: 3px;
        }
        QLineEdit:focus { border-color: #2a82da; }
        QToolBar { background: #353535; border: none; spacing: 3px; padding: 3px; }
        QToolBar QToolButton { background: transparent; border: none; padding: 4px; }
        QToolBar QToolButton:hover { background: #4a4a4a; border-radius: 3px; }
        QStatusBar { background: #353535; color: #aaa; }
        QComboBox {
            background: #3a3a3a; border: 1px solid #555; color: white;
            padding: 4px; border-radius: 3px;
        }
        QComboBox:hover { border-color: #2a82da; }
        QComboBox QAbstractItemView {
            background: #2d2d2d; color: white; selection-background-color: #2a82da;
        }
    """)


def main():
    """Entry point for CodeBox."""
    app = QApplication(sys.argv)
    set_dark_theme(app)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
