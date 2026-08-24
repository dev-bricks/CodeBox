"""Tests for Minimap line caching and paint optimization."""

import pytest
from PySide6.QtGui import QPaintEvent
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from core.editor import CodeEditor


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_minimap_caching_and_invalidation(qapp):
    """Verifies that Minimap caches lines and invalidates on document changes."""
    editor = CodeEditor()
    editor.resize(400, 300)
    editor.setPlainText("line 1\nline 2 is longer\nline 3")
    editor.show()
    qapp.processEvents()

    minimap = editor.minimap
    # Initially before _document_lines call, _cached_lines may be None
    lines = minimap._document_lines()
    assert lines == ["line 1", "line 2 is longer", "line 3"]
    assert minimap._cached_lines is not None
    assert minimap._cached_max_chars == len("line 2 is longer")

    # Modifying text should invalidate the cache
    editor.appendPlainText("line 4 extra very long line that expands max chars")
    qapp.processEvents()
    assert minimap._cached_lines is None

    # Fetching lines again recalculates and caches
    lines2 = minimap._document_lines()
    assert len(lines2) == 4
    assert minimap._cached_max_chars == len("line 4 extra very long line that expands max chars")
    editor.close()


def test_minimap_paint_event_uses_cached_values(qapp):
    """Verifies that paintEvent operates without errors on cached lines."""
    editor = CodeEditor()
    editor.resize(400, 300)
    editor.setPlainText("\n".join(f"def func_{i}(): pass" for i in range(200)))
    editor.show()
    qapp.processEvents()

    minimap = editor.minimap
    # Trigger paintEvent directly
    paint_event = QPaintEvent(QRect(0, 0, minimap.width(), minimap.height()))
    minimap.paintEvent(paint_event)

    assert minimap._cached_lines is not None
    assert len(minimap._cached_lines) == 200
    editor.close()
