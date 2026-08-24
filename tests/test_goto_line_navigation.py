"""Tests for MainWindow line navigation and Edit menu delegation."""

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog

from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_goto_line_moves_to_correct_block(qapp, monkeypatch):
    """Verifies that _goto_line accurately navigates to the requested line number."""
    window = MainWindow()
    tab = window.tab_widget.current_tab()
    assert tab is not None

    # Populate 100 lines
    tab.editor.setPlainText("\n".join(f"line_{i}" for i in range(1, 101)))

    # Monkeypatch QInputDialog.getInt to simulate selecting line 42
    monkeypatch.setattr(QInputDialog, "getInt", lambda *args, **kwargs: (42, True))

    window._goto_line()

    cursor = tab.editor.textCursor()
    assert cursor.blockNumber() == 41  # 0-indexed: line 42 is block 41
    assert cursor.block().text() == "line_42"
    window.close()


def test_mainwindow_edit_delegations(qapp):
    """Verifies that MainWindow edit actions correctly call CodeEditor methods."""
    window = MainWindow()
    tab = window.tab_widget.current_tab()
    assert tab is not None

    tab.editor.setPlainText("def hello():\n    return 1")

    # Select all and toggle comment
    tab.editor.selectAll()
    window._toggle_comment()
    assert "# def hello():\n#     return 1" in tab.editor.toPlainText()

    # Toggle back
    tab.editor.selectAll()
    window._toggle_comment()
    assert "def hello():\n    return 1" in tab.editor.toPlainText()

    # Test indent / dedent delegations
    tab.editor.selectAll()
    window._indent()
    assert "    def hello():\n        return 1" in tab.editor.toPlainText()

    tab.editor.selectAll()
    window._dedent()
    assert "def hello():\n    return 1" in tab.editor.toPlainText()

    window.close()
