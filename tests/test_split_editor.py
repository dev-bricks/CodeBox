#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for split editor functionality (horizontal/vertical split, sync, tabs)."""

from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.shortcuts_dialog import SHORTCUTS_DATA


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_split_editor_right_creates_clone(qapp, tmp_path):
    f = tmp_path / "test_split.py"
    f.write_text("print('hello split')\n", encoding="utf-8")

    window = MainWindow()
    window.open_path(Path(f))

    assert not window.is_editor_split()
    assert window.split_tab_widget.isHidden()

    window.split_editor_right()

    assert window.is_editor_split()
    assert not window.split_tab_widget.isHidden()
    assert window.editor_splitter.orientation() == Qt.Orientation.Horizontal
    assert window.split_tab_widget.count() == 1
    assert window.get_active_tab_widget() is window.split_tab_widget

    # Check document sharing
    primary_doc = window.tab_widget.current_tab().editor.document()
    split_doc = window.split_tab_widget.current_tab().editor.document()
    assert primary_doc is split_doc

    window.close()


def test_split_editor_down(qapp):
    window = MainWindow()

    window.split_editor_down()

    assert window.is_editor_split()
    assert not window.split_tab_widget.isHidden()
    assert window.editor_splitter.orientation() == Qt.Orientation.Vertical
    assert window.split_tab_widget.count() == 1

    window.close()


def test_split_editor_synchronized_editing_and_undo(qapp):
    window = MainWindow()
    tab = window.tab_widget.current_tab()
    tab.editor.setPlainText("initial content")

    window.split_editor_right()
    primary_editor = window.tab_widget.current_tab().editor
    split_editor = window.split_tab_widget.current_tab().editor

    # Edit in primary editor
    c = primary_editor.textCursor()
    c.movePosition(c.MoveOperation.End)
    primary_editor.setTextCursor(c)
    primary_editor.insertPlainText(" [from primary]")
    assert "initial content [from primary]" in split_editor.toPlainText()

    # Edit in split editor
    c2 = split_editor.textCursor()
    c2.movePosition(c2.MoveOperation.End)
    split_editor.setTextCursor(c2)
    split_editor.insertPlainText(" [from split]")
    assert "initial content [from primary] [from split]" in primary_editor.toPlainText()

    # Undo in split editor
    split_editor.undo()
    assert " [from split]" not in primary_editor.toPlainText()

    window.close()


def test_split_editor_focus_switching(qapp):
    window = MainWindow()
    window.split_editor_right()

    assert window.get_active_tab_widget() is window.split_tab_widget

    # Switch to primary
    window.focus_other_split()
    assert window.get_active_tab_widget() is window.tab_widget

    # Switch back to split
    window.focus_other_split()
    assert window.get_active_tab_widget() is window.split_tab_widget

    window.close()


def test_split_editor_move_tab(qapp):
    window = MainWindow()
    window.new_file()
    assert window.tab_widget.count() == 2

    window._active_tab_widget = window.tab_widget
    window.move_tab_to_other_split()

    assert window.is_editor_split()
    assert window.tab_widget.count() == 1
    assert window.split_tab_widget.count() == 1

    # Move tab back to primary
    window._active_tab_widget = window.split_tab_widget
    window.move_tab_to_other_split()

    # Auto-unsplit because split tab widget is empty
    assert window.tab_widget.count() == 2
    assert window.split_tab_widget.count() == 0
    assert not window.is_editor_split()

    window.close()


def test_split_editor_close_last_split_tab_auto_unsplits(qapp):
    window = MainWindow()
    window.split_editor_right()
    assert window.is_editor_split()

    # Close the only tab in the split pane
    window._on_split_tab_close_requested(0)

    assert not window.is_editor_split()
    assert window.split_tab_widget.isHidden()
    assert window.get_active_tab_widget() is window.tab_widget

    window.close()


def test_unsplit_editor_preserves_unique_tabs(qapp, tmp_path):
    f1 = tmp_path / "file1.py"
    f1.write_text("# file 1", encoding="utf-8")
    f2 = tmp_path / "file2.py"
    f2.write_text("# file 2", encoding="utf-8")

    window = MainWindow()
    # Close initial empty tab to make count tracking deterministic
    window.tab_widget.close_tab(0, prompt=False)

    window.open_path(Path(f1))
    window.split_editor_right()

    # Open file2 into the split tab widget
    window.open_path(Path(f2), target_widget=window.split_tab_widget)
    assert window.split_tab_widget.count() == 2

    # Close the cloned file1 tab from the split pane
    window.split_tab_widget.close_tab(0, prompt=False)
    assert window.split_tab_widget.count() == 1

    # File 2 is unique to split_tab_widget. Now unsplit editor.
    window.unsplit_editor()

    assert not window.is_editor_split()
    assert window.tab_widget.count() == 2

    # Check that both file1 and file2 are in the primary tab widget
    paths = [t.file_path for t in window.tab_widget.tabs.values() if t.file_path]
    assert Path(f1) in paths
    assert Path(f2) in paths

    window.close()


def test_search_dialog_targets_active_split(qapp, tmp_path):
    f1 = tmp_path / "doc1.txt"
    f1.write_text("apple alpha", encoding="utf-8")
    f2 = tmp_path / "doc2.txt"
    f2.write_text("banana beta", encoding="utf-8")

    window = MainWindow()
    window.open_path(Path(f1))
    window.split_editor_right()
    window.open_path(Path(f2), target_widget=window.split_tab_widget)

    # Focus split tab widget
    window._active_tab_widget = window.split_tab_widget
    window._find()
    assert window._find_dialog._get_current_editor() is window.split_tab_widget.current_tab().editor

    # Focus primary tab widget
    window._active_tab_widget = window.tab_widget
    window._find()
    assert window._find_dialog._get_current_editor() is window.tab_widget.current_tab().editor

    window._find_dialog.close()
    window.close()


def test_shortcuts_registry_has_split_actions():
    action_names = {item[1] for item in SHORTCUTS_DATA}
    assert "Editor nach rechts teilen" in action_names
    assert "Editor nach unten teilen" in action_names
    assert "Editor-Teilung aufheben" in action_names
    assert "Fokus zwischen geteilten Ansichten" in action_names
    assert "Tab zur anderen Ansicht verschieben" in action_names
