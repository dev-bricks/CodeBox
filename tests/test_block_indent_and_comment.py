"""Unit tests for CodeEditor block indentation, dedentation, comment toggling, and line movement."""

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from core.editor import CodeEditor
from languages.javascript_lang import JavaScriptProvider
from languages.python_lang import PythonProvider


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_single_line_indent_and_dedent(qapp):
    """Verifies single line indentation and dedentation."""
    editor = CodeEditor()
    editor.apply_editor_settings("Consolas", 10, 4)
    editor.setPlainText("def foo():\nreturn 42\n")

    # Move cursor to second line
    cursor = editor.textCursor()
    cursor.setPosition(len("def foo():\n"))
    editor.setTextCursor(cursor)

    editor.indent_selection(4)
    assert editor.toPlainText() == "def foo():\n    return 42\n"

    editor.unindent_selection(4)
    assert editor.toPlainText() == "def foo():\nreturn 42\n"
    editor.close()


def test_multiline_block_indent_and_dedent(qapp):
    """Verifies multi-line block indentation and dedentation."""
    editor = CodeEditor()
    editor.apply_editor_settings("Consolas", 10, 4)
    editor.setPlainText("line1\nline2\nline3")

    # Select all lines
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len(editor.toPlainText()), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)

    editor.indent_selection(4)
    assert editor.toPlainText() == "    line1\n    line2\n    line3"

    editor.unindent_selection(4)
    assert editor.toPlainText() == "line1\nline2\nline3"
    editor.close()


def test_toggle_comment_python(qapp):
    """Verifies toggle_comment with Python '#' comment style."""
    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    editor.setPlainText("a = 1\nb = 2\nc = 3")

    # Select lines 1 and 2
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("a = 1\nb = 2"), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)

    editor.toggle_comment()
    assert editor.toPlainText() == "# a = 1\n# b = 2\nc = 3"

    # Toggle again -> should uncomment
    editor.toggle_comment()
    assert editor.toPlainText() == "a = 1\nb = 2\nc = 3"
    editor.close()


def test_toggle_comment_javascript(qapp):
    """Verifies toggle_comment with JavaScript '//' comment style."""
    editor = CodeEditor()
    editor.set_provider(JavaScriptProvider())
    editor.setPlainText("let x = 10;\nlet y = 20;")

    # Select all
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len(editor.toPlainText()), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)

    editor.toggle_comment()
    assert editor.toPlainText() == "// let x = 10;\n// let y = 20;"

    editor.toggle_comment()
    assert editor.toPlainText() == "let x = 10;\nlet y = 20;"
    editor.close()


def test_duplicate_line_and_selection(qapp):
    """Verifies line and selection duplication."""
    editor = CodeEditor()
    editor.setPlainText("hello world")

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    editor.duplicate_line_or_selection()
    assert editor.toPlainText() == "hello world\nhello world"
    editor.close()


def test_move_line_up_and_down(qapp):
    """Verifies moving lines up and down."""
    editor = CodeEditor()
    editor.setPlainText("first\nsecond\nthird")

    # Move cursor to second line and move up
    cursor = editor.textCursor()
    cursor.setPosition(len("first\n") + 1)
    editor.setTextCursor(cursor)

    editor.move_line_up()
    assert editor.toPlainText() == "second\nfirst\nthird"

    # Move down
    editor.move_line_down()
    assert editor.toPlainText() == "first\nsecond\nthird"
    editor.close()


def test_key_press_indent_and_comment_shortcuts(qapp):
    """Verifies keyboard shortcuts in keyPressEvent."""
    editor = CodeEditor()
    editor.apply_editor_settings("Consolas", 10, 4)
    editor.set_provider(PythonProvider())
    editor.setPlainText("val = 10")

    # Test Tab
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    event_tab = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    editor.keyPressEvent(event_tab)
    assert editor.toPlainText() == "    val = 10"

    # Test Shift+Tab (Backtab)
    event_backtab = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    editor.keyPressEvent(event_backtab)
    assert editor.toPlainText() == "val = 10"

    # Test Ctrl+/ (Toggle comment)
    event_comment = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Slash, Qt.KeyboardModifier.ControlModifier, "/")
    editor.keyPressEvent(event_comment)
    assert editor.toPlainText() == "# val = 10"

    # Test Ctrl+D (Duplicate)
    event_dup = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
    editor.keyPressEvent(event_dup)
    assert "# val = 10\n# val = 10" in editor.toPlainText()
    editor.close()
