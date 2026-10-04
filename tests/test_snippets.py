#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für SnippetManager, Template-Parsing und SnippetSession in CodeBox.
"""

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from core.editor import CodeEditor
from core.snippets import (
    Snippet,
    SnippetManager,
    SnippetSession,
    parse_snippet,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_parse_snippet_basic():
    template = "def $1($2):\n    $0"
    rendered, stops = parse_snippet(template)
    assert rendered == "def ():\n    "
    assert len(stops) == 3
    assert stops[0].index == 1
    assert stops[0].start_offset == 4
    assert stops[0].length == 0
    assert stops[1].index == 2
    assert stops[1].start_offset == 5
    assert stops[1].length == 0
    assert stops[2].index == 0
    assert stops[2].start_offset == 12


def test_parse_snippet_with_placeholders():
    template = "def ${1:func_name}(${2:arg1, arg2}):\n    ${0:pass}"
    rendered, stops = parse_snippet(template)
    assert rendered == "def func_name(arg1, arg2):\n    pass"
    assert len(stops) == 3
    assert stops[0].index == 1
    assert stops[0].start_offset == 4
    assert stops[0].length == len("func_name")
    assert stops[0].default_text == "func_name"

    assert stops[1].index == 2
    assert stops[1].start_offset == 4 + len("func_name") + 1
    assert stops[1].length == len("arg1, arg2")
    assert stops[1].default_text == "arg1, arg2"

    assert stops[2].index == 0
    assert stops[2].length == len("pass")
    assert stops[2].default_text == "pass"


def test_parse_snippet_escaped_dollar():
    template = "price = \\$100\n$1 = ${2:val}"
    rendered, stops = parse_snippet(template)
    assert rendered == "price = $100\n = val"
    assert len(stops) == 3  # stop 1, stop 2, and default exit stop 0
    assert stops[0].index == 1
    assert stops[1].index == 2
    assert stops[2].index == 0
    assert stops[2].start_offset == len(rendered)


def test_snippet_render_plain():
    s = Snippet("prop", "Property", "@property\ndef ${1:foo}(self):\n    return self._${1:foo}", "python")
    plain = s.render_plain()
    assert plain == "@property\ndef foo(self):\n    return self._foo"


def test_snippet_manager_builtins(tmp_path: Path):
    custom_json = tmp_path / "custom_snippets.json"
    mgr = SnippetManager(custom_file=custom_json)

    # Python snippets
    py_def = mgr.get_snippet("def", "python")
    assert py_def is not None
    assert py_def.trigger == "def"
    assert "def " in py_def.body

    # JS snippets
    js_clg = mgr.get_snippet("clg", "javascript")
    assert js_clg is not None
    assert "console.log" in js_clg.body

    # Global snippets
    todo_snip = mgr.get_snippet("todo", "any_lang")
    assert todo_snip is not None
    assert "TODO" in todo_snip.body

    # Unknown
    assert mgr.get_snippet("nonexistent_trigger_xyz", "python") is None


def test_snippet_manager_custom_crud(tmp_path: Path):
    custom_json = tmp_path / "custom_snippets.json"
    mgr = SnippetManager(custom_file=custom_json)

    custom_snip = Snippet("myhook", "Custom React Hook", "const use${1:Hook} = () => {\n    $0\n};", "javascript")
    assert mgr.add_custom_snippet(custom_snip)
    assert custom_json.exists()

    # Re-read
    mgr2 = SnippetManager(custom_file=custom_json)
    found = mgr2.get_snippet("myhook", "javascript")
    assert found is not None
    assert found.is_custom is True
    assert found.description == "Custom React Hook"

    # Remove
    assert mgr2.remove_custom_snippet("myhook", "javascript")
    assert mgr2.get_snippet("myhook", "javascript") is None


def test_snippet_session_navigation(qapp):
    editor = CodeEditor()
    editor.setPlainText("")
    template = "def ${1:func_name}(${2:arg1}):\n    ${0:pass}"
    rendered, stops = parse_snippet(template)

    editor.textCursor().insertText(rendered)
    session = SnippetSession(editor, base_pos=0, rendered_text=rendered, tab_stops=stops)
    session.start()

    assert session.is_active is True
    assert editor.textCursor().selectedText() == "func_name"

    # Jump to stop 2
    assert session.next_stop() is True
    assert editor.textCursor().selectedText() == "arg1"

    # Jump back to stop 1
    assert session.prev_stop() is True
    assert editor.textCursor().selectedText() == "func_name"

    # Jump to stop 2 again
    assert session.next_stop() is True
    assert editor.textCursor().selectedText() == "arg1"

    # Next stop completes to $0
    assert session.next_stop() is True
    assert session.is_active is False
    assert editor.textCursor().selectedText() == "pass"


def test_editor_tab_trigger_expansion(qapp):
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import Qt
    from languages.python_lang import PythonProvider

    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    editor.setPlainText("def")
    # Move cursor to end of "def"
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)

    # Press Tab key
    event_tab = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    editor.keyPressEvent(event_tab)

    # Should have expanded "def" into snippet
    assert "def " in editor.toPlainText()
    assert editor._snippet_session is not None
    assert editor._snippet_session.is_active is True
    # First placeholder selected
    assert editor.textCursor().selectedText() == "name"

    # Press Tab again -> next placeholder
    editor.keyPressEvent(event_tab)
    assert editor.textCursor().selectedText() == "args"

    # Press Tab again -> exit point
    editor.keyPressEvent(event_tab)
    assert editor._snippet_session.is_active is False
    assert "pass" in editor.textCursor().selectedText() or editor.textCursor().position() > 0


def test_editor_tab_indentation_when_no_snippet(qapp):
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import Qt

    editor = CodeEditor()
    editor.setPlainText("some_random_word")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)

    # Press Tab -> should just insert spaces
    event_tab = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    editor.keyPressEvent(event_tab)

    assert editor.toPlainText() == "some_random_word    "
    assert editor._snippet_session is None


def test_editor_multiline_snippet_preserves_indent(qapp):
    from languages.python_lang import PythonProvider

    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    editor.setPlainText("    def")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)

    snippet = Snippet("def", "func", "def ${1:foo}():\n    ${0:pass}", "python")
    editor.expand_snippet(snippet, trigger_len=3)

    text = editor.toPlainText()
    lines = text.split("\n")
    assert lines[0] == "    def foo():"
    assert lines[1] == "        pass"


def test_snippets_dialog_filtering_and_preview(qapp, tmp_path: Path):
    from ui.snippets_dialog import SnippetsDialog

    custom_json = tmp_path / "snippets.json"
    mgr = SnippetManager(custom_file=custom_json)
    dlg = SnippetsDialog(manager=mgr, current_language="python")

    # Table has python snippets
    assert dlg.table.rowCount() > 0

    # Filter by search
    dlg.search_edit.setText("while")
    assert dlg.table.rowCount() >= 1
    selected = dlg._get_selected_snippet()
    assert selected is not None
    assert selected.trigger == "while"
    assert "while" in dlg.preview_edit.toPlainText()

    # Clear filter
    dlg.search_edit.clear()
    assert dlg.table.rowCount() > 1
    dlg.close()


def test_snippets_dialog_insert_signal(qapp, tmp_path: Path):
    from ui.snippets_dialog import SnippetsDialog

    custom_json = tmp_path / "snippets.json"
    mgr = SnippetManager(custom_file=custom_json)
    dlg = SnippetsDialog(manager=mgr, current_language="python")

    emitted = []
    dlg.snippetSelected.connect(lambda s: emitted.append(s))

    dlg.table.selectRow(0)
    dlg._on_insert_clicked()

    assert len(emitted) == 1
    assert isinstance(emitted[0], Snippet)
    dlg.close()


def test_snippet_edit_dialog(qapp):
    from ui.snippets_dialog import SnippetEditDialog

    dlg = SnippetEditDialog(current_language="python")
    dlg.trigger_input.setText("test_trig")
    dlg.desc_input.setText("Test Description")
    dlg.body_edit.setPlainText("def ${1:test}():\n    ${0:pass}")

    snippet = dlg.get_snippet()
    assert snippet.trigger == "test_trig"
    assert snippet.description == "Test Description"
    assert snippet.body == "def ${1:test}():\n    ${0:pass}"
    assert snippet.is_custom is True
    dlg.close()


def test_main_window_snippets_menu_and_shortcut(qapp):
    from ui.main_window import MainWindow
    from ui.shortcuts_dialog import SHORTCUTS_DATA

    # Shortcut table entry
    found = [s for s in SHORTCUTS_DATA if s[1] == "Snippet einfügen"]
    assert len(found) == 1
    assert found[0][2] == "Ctrl+Shift+J"

    # Menu action in MainWindow
    win = MainWindow()
    edit_menu = None
    for a in win.menuBar().actions():
        if a.menu() and "Bearbeiten" in a.menu().title():
            edit_menu = a.menu()
            break
    assert edit_menu is not None
    snippet_actions = [a for a in edit_menu.actions() if "Snippet einfügen" in a.text()]
    assert len(snippet_actions) == 1
    assert snippet_actions[0].shortcut().toString() == "Ctrl+Shift+J"
    win.close()


