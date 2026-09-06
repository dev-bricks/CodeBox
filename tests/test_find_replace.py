#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for integrated regex search & replace and preview dialog."""

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.editor import CodeEditor
from ui.main_window import MainWindow
from ui.search_dialog import FindReplaceDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_compile_search_pattern_and_errors(qapp):
    editor = CodeEditor()
    editor.setPlainText("Hello World 123\nhello world 456")

    # Plain text search
    pat, err = editor.compile_search_pattern("world", case_sensitive=False, is_regex=False)
    assert err is None
    assert pat is not None
    assert pat.search("WORLD") is not None

    # Case sensitive search
    pat_cs, err = editor.compile_search_pattern("World", case_sensitive=True, is_regex=False)
    assert err is None
    assert pat_cs.search("World") is not None
    assert pat_cs.search("world") is None

    # Whole word
    pat_ww, err = editor.compile_search_pattern("word", whole_word=True, is_regex=False)
    assert pat_ww.search("password") is None
    assert pat_ww.search("a word here") is not None

    # Regex valid
    pat_re, err = editor.compile_search_pattern(r"\d+", is_regex=True)
    assert err is None
    assert pat_re.findall("abc 123 def 456") == ["123", "456"]

    # Regex invalid
    pat_inv, err = editor.compile_search_pattern(r"[unclosed", is_regex=True)
    assert pat_inv is None
    assert err is not None


def test_find_all_matches_and_highlight(qapp):
    editor = CodeEditor()
    editor.setPlainText("foo bar foo baz\nFOO 999 foo")

    matches, err = editor.find_all_matches("foo", case_sensitive=False)
    assert err is None
    assert len(matches) == 4

    # Highlight returns count and sets extra selections
    count = editor.highlightSearchResults("foo", case_sensitive=True)
    assert count == 3
    assert len(editor.search_selections) == 3

    editor.clearSearchHighlight()
    assert len(editor.search_selections) == 0


def test_find_next_and_navigation(qapp):
    editor = CodeEditor()
    editor.setPlainText("apple banana apple cherry apple")

    # Cursor at 0
    c = editor.textCursor()
    c.setPosition(0)
    editor.setTextCursor(c)

    # First forward
    found = editor.find_next("apple", forward=True)
    assert found is True
    assert editor.textCursor().selectedText() == "apple"
    assert editor.textCursor().selectionStart() == 0

    # Second forward
    found = editor.find_next("apple", forward=True)
    assert found is True
    assert editor.textCursor().selectionStart() == 13

    # Third forward
    found = editor.find_next("apple", forward=True)
    assert found is True
    assert editor.textCursor().selectionStart() == 26

    # Fourth forward (wraps around to 0)
    found = editor.find_next("apple", forward=True)
    assert found is True
    assert editor.textCursor().selectionStart() == 0

    # Backward (wraps to 26)
    found = editor.find_next("apple", forward=False)
    assert found is True
    assert editor.textCursor().selectionStart() == 26


def test_replace_current_and_regex_groups(qapp):
    editor = CodeEditor()
    editor.setPlainText("item_101 item_102 item_103")

    # Position at beginning
    c = editor.textCursor()
    c.setPosition(0)
    editor.setTextCursor(c)

    # First find_next selects item_101
    editor.find_next(r"item_(\d+)", is_regex=True)
    assert editor.textCursor().selectedText() == "item_101"

    # Replace with capture group
    replaced = editor.replace_current(
        r"item_(\d+)",
        r"code_\1",
        is_regex=True,
    )
    assert replaced is True
    assert "code_101" in editor.toPlainText()
    # Cursor automatically advanced to next match
    assert editor.textCursor().selectedText() == "item_102"


def test_replace_all_with_single_undo(qapp):
    editor = CodeEditor()
    original_text = "alpha beta gamma alpha delta alpha"
    editor.setPlainText(original_text)

    count = editor.replace_all("alpha", "omega")
    assert count == 3
    assert editor.toPlainText() == "omega beta gamma omega delta omega"

    # Single undo should restore all replaced occurrences
    editor.undo()
    assert editor.toPlainText() == original_text


def test_get_replace_preview(qapp):
    editor = CodeEditor()
    editor.setPlainText("user_1 = 10\nuser_2 = 20\nuser_3 = 30")

    previews, total, err = editor.get_replace_preview(
        pattern=r"user_(\d+)",
        replacement=r"client_\1",
        is_regex=True,
    )
    assert err is None
    assert total == 3
    assert len(previews) == 3

    assert previews[0]["line"] == 1
    assert previews[0]["col"] == 1
    assert previews[0]["original"] == "user_1"
    assert previews[0]["replacement"] == "client_1"

    assert previews[1]["line"] == 2
    assert previews[1]["original"] == "user_2"
    assert previews[1]["replacement"] == "client_2"


def test_find_replace_dialog_ui_interaction(qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    window = MainWindow()
    window.new_file()
    tab = window.tab_widget.current_tab()
    tab.editor.setPlainText("alpha = 1\nbeta = 2\nalpha = 3\nalpha = 4")

    dialog = FindReplaceDialog(window, initial_mode="find")
    dialog.show()

    # Search for alpha
    dialog.search_input.setText("alpha")
    dialog.replace_input.setText("zeta")
    dialog._update_live_results()

    assert "3 Treffer gefunden" in dialog.status_label.text()
    assert dialog.preview_table.rowCount() == 3

    # Navigate next
    dialog.find_next()
    assert tab.editor.textCursor().selectedText() == "alpha"

    # Replace current
    dialog.replace_current()
    assert "zeta = 1" in tab.editor.toPlainText()

    # Table click jumps cursor
    item = dialog.preview_table.item(0, 0)
    dialog._on_table_item_activated(item)
    assert tab.editor.textCursor().hasSelection()

    # Replace all
    dialog.replace_all()
    assert tab.editor.toPlainText().count("zeta") >= 3
    assert "alpha" not in tab.editor.toPlainText()

    # Invalid regex test
    dialog.cb_regex.setChecked(True)
    dialog.search_input.setText("([a-z]+")
    dialog._update_live_results()
    assert "Regex-Fehler" in dialog.status_label.text()

    dialog.close()
    window.close()


def test_mainwindow_find_replace_actions(qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    window = MainWindow()
    window.new_file()
    tab = window.tab_widget.current_tab()
    tab.editor.setPlainText("def hello():\n    return 'world'\n")

    window.show()
    qapp.processEvents()

    # Trigger _find()
    window._find()
    qapp.processEvents()
    assert window._find_dialog is not None
    assert window._find_dialog.isVisible()

    # Trigger _replace()
    window._replace()
    qapp.processEvents()
    assert window._find_dialog.isVisible()

    window._find_dialog.search_input.setText("hello")
    window._find_next()
    assert tab.editor.textCursor().selectedText() == "hello"

    window._find_dialog.close()
    window.close()


def test_search_edge_cases(qapp):
    editor = CodeEditor()
    editor.setPlainText("quick brown fox jumps over the lazy dog")

    # Empty pattern
    matches, err = editor.find_all_matches("")
    assert matches == []
    assert err is None
    assert editor.find_next("") is False
    assert editor.replace_all("", "test") == 0

    # No matches found
    matches, err = editor.find_all_matches("elephant")
    assert matches == []
    assert err is None
    assert editor.find_next("elephant") is False
    assert editor.replace_all("elephant", "mouse") == 0

    # Whole word with regex
    pat, err = editor.compile_search_pattern(r"fox\w*", is_regex=True, whole_word=True)
    assert err is None
    assert pat.search("foxes") is not None

