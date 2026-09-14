#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für Breakpoints und Zuletzt geöffnete Dateien (Recent Files)."""

import pytest
from PySide6.QtWidgets import QApplication

from core.editor import CodeEditor
from ui.main_window import MainWindow


@pytest.fixture
def qt_app():
    instance = QApplication.instance()
    if not instance:
        instance = QApplication([])
    return instance


def test_code_editor_breakpoint_toggling(qt_app):
    editor = CodeEditor()
    editor.setPlainText("line 1\nline 2\nline 3\nline 4\nline 5")

    changes = []
    editor.breakpointsChanged.connect(changes.append)

    # Initial empty
    assert editor.get_breakpoints() == []
    assert not editor.has_breakpoint(2)

    # Toggle on line 2
    res = editor.toggle_breakpoint(2)
    assert res is True
    assert editor.has_breakpoint(2)
    assert editor.get_breakpoints() == [2]
    assert changes[-1] == [2]

    # Toggle on line 4
    res2 = editor.toggle_breakpoint(4)
    assert res2 is True
    assert editor.has_breakpoint(4)
    assert editor.get_breakpoints() == [2, 4]

    # Toggle off line 2
    res3 = editor.toggle_breakpoint(2)
    assert res3 is False
    assert not editor.has_breakpoint(2)
    assert editor.get_breakpoints() == [4]

    # Set multiple breakpoints
    editor.set_breakpoints([1, 5, 3])
    assert editor.get_breakpoints() == [1, 3, 5]

    # Clear breakpoints
    editor.clear_breakpoints()
    assert editor.get_breakpoints() == []
    assert changes[-1] == []


def test_code_editor_toggle_breakpoint_current_line(qt_app):
    editor = CodeEditor()
    editor.setPlainText("alpha\nbeta\ngamma")

    # Move cursor to line 2 (blockNumber 1)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Down)
    editor.setTextCursor(cursor)
    assert editor.textCursor().blockNumber() == 1

    # Toggle current line
    active = editor.toggle_breakpoint()
    assert active is True
    assert editor.get_breakpoints() == [2]

    # Invalid line <= 0
    assert editor.toggle_breakpoint(0) is False
    assert editor.toggle_breakpoint(-5) is False


def test_line_number_area_width(qt_app):
    editor = CodeEditor()
    editor.setPlainText("one\ntwo\nthree")
    assert editor.lineNumberAreaWidth() >= editor.BREAKPOINT_AREA_WIDTH + editor.FOLD_AREA_WIDTH


def test_main_window_breakpoint_actions(qt_app, tmp_path):
    win = MainWindow()
    win.resize(600, 400)
    win.show()

    test_file = tmp_path / "code.py"
    test_file.write_text("x = 1\ny = 2\nz = 3", encoding="utf-8")
    win.open_path(test_file)

    editor = win.get_current_editor()
    assert editor is not None
    assert editor.get_breakpoints() == []

    # Toggle breakpoint via MainWindow action
    win.act_toggle_breakpoint.trigger()
    assert 1 in editor.get_breakpoints()
    assert "Breakpoint auf Zeile 1 gesetzt" in win.status_bar.currentMessage()

    # Toggle off
    win.act_toggle_breakpoint.trigger()
    assert 1 not in editor.get_breakpoints()
    assert "Breakpoint auf Zeile 1 entfernt" in win.status_bar.currentMessage()

    # Clear all
    editor.set_breakpoints([1, 2, 3])
    win.act_clear_breakpoints.trigger()
    assert editor.get_breakpoints() == []
    assert "Alle Breakpoints" in win.status_bar.currentMessage()

    win.close()


def test_main_window_recent_files(qt_app, tmp_path):
    win = MainWindow()
    win.show()

    f1 = tmp_path / "file1.py"
    f2 = tmp_path / "file2.py"
    for f in [f1, f2]:
        f.write_text("print(1)", encoding="utf-8")

    # Initial clear
    win._clear_recent_files()
    assert win._settings.get("recent_files") == []

    # Open file1, file2
    win.open_path(f1)
    win.open_path(f2)

    recent = win._settings.get("recent_files", [])
    assert str(f2.resolve()) == recent[0]
    assert str(f1.resolve()) == recent[1]

    # Re-opening f1 brings it to front
    win.open_path(f1)
    recent = win._settings.get("recent_files", [])
    assert str(f1.resolve()) == recent[0]
    assert len(recent) == 2

    # Clear recent files
    win._clear_recent_files()
    assert win._settings.get("recent_files") == []

    win.close()
