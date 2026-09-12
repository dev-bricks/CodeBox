#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die globale Textsuche über alle Projektordner (Find in Files / Grep Tool).
"""

from pathlib import Path
import re
import pytest
from PySide6.QtWidgets import QApplication

from core.file_search import (
    SearchMatch,
    SearchOptions,
    SearchWorker,
    compile_search_regex,
    is_binary_file,
    matches_glob_patterns,
    search_file,
)
from ui.find_in_files_dialog import FindInFilesDialog
from ui.main_window import MainWindow
from ui.shortcuts_dialog import SHORTCUTS_DATA


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_compile_search_regex():
    # 1. Plain text case-insensitive
    opts = SearchOptions(query="codebox", case_sensitive=False)
    pat, err = compile_search_regex(opts)
    assert err is None
    assert pat is not None
    assert pat.search("CodeBox v0.2.0") is not None
    assert pat.search("other") is None

    # 2. Case-sensitive
    opts_cs = SearchOptions(query="CodeBox", case_sensitive=True)
    pat_cs, err = compile_search_regex(opts_cs)
    assert err is None
    assert pat_cs.search("CodeBox") is not None
    assert pat_cs.search("codebox") is None

    # 3. Whole word
    opts_ww = SearchOptions(query="test", whole_word=True)
    pat_ww, err = compile_search_regex(opts_ww)
    assert err is None
    assert pat_ww.search("a test here") is not None
    assert pat_ww.search("testing") is None
    assert pat_ww.search("pytest") is None

    # 4. Valid Regex
    opts_re = SearchOptions(query=r"def\s+[a-zA-Z_]\w*\(", is_regex=True)
    pat_re, err = compile_search_regex(opts_re)
    assert err is None
    assert pat_re.search("def my_func(arg):") is not None

    # 5. Invalid Regex
    opts_bad = SearchOptions(query=r"[unclosed(", is_regex=True)
    pat_bad, err = compile_search_regex(opts_bad)
    assert pat_bad is None
    assert err is not None
    assert "Ungültiger regulärer Ausdruck" in err

    # 6. Empty query
    opts_empty = SearchOptions(query="")
    pat_empty, err = compile_search_regex(opts_empty)
    assert pat_empty is None
    assert err is not None


def test_matches_glob_patterns():
    # Include pattern
    assert matches_glob_patterns("main.py", "src/main.py", ["*.py"], []) is True
    assert matches_glob_patterns("index.js", "src/index.js", ["*.py"], []) is False

    # Multiple includes
    assert matches_glob_patterns("index.js", "src/index.js", ["*.py", "*.js"], []) is True

    # Exclude pattern
    assert matches_glob_patterns("bundle.min.js", "dist/bundle.min.js", [], ["*.min.js"]) is False
    assert matches_glob_patterns("test_foo.py", "tests/test_foo.py", [], ["tests/*"]) is False
    assert matches_glob_patterns("foo.py", "src/foo.py", [], ["tests/*"]) is True

    # Exclude overrides include
    assert matches_glob_patterns("test_foo.py", "tests/test_foo.py", ["*.py"], ["tests/*"]) is False


def test_is_binary_file_and_search_file(tmp_path: Path):
    text_file = tmp_path / "sample.py"
    text_file.write_text(
        "def hello_world():\n"
        "    # Erste Zeile mit Suchbegriff\n"
        "    print('hello world', 'another hello')\n"
        "    return 42\n",
        encoding="utf-8",
    )

    bin_file = tmp_path / "binary.dat"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x00\xff")

    assert is_binary_file(text_file) is False
    assert is_binary_file(bin_file) is True

    # Search in binary file returns empty
    pat = re.compile("hello", re.IGNORECASE)
    assert search_file(bin_file, "binary.dat", "root", pat) == []

    # Search in text file
    matches = search_file(text_file, "sample.py", "root", pat)
    assert len(matches) == 3

    # Match 1: line 1
    assert matches[0].line_number == 1
    assert matches[0].column == 5
    assert matches[0].match_length == 5
    assert "def hello_world():" in matches[0].line_text

    # Match 2: line 3 first occurrence
    assert matches[1].line_number == 3
    assert matches[1].column == 12

    # Match 3: line 3 second occurrence
    assert matches[2].line_number == 3
    assert matches[2].column == 35


def test_search_file_with_umlauts(tmp_path: Path):
    umlaut_file = tmp_path / "umlaut.txt"
    umlaut_file.write_text(
        "Größe und Übertragungsrate prüfen.\n"
        "Änderungen erfolgreich übernommen.\n",
        encoding="utf-8",
    )

    pat, err = compile_search_regex(SearchOptions(query="größe", case_sensitive=False))
    assert err is None
    matches = search_file(umlaut_file, "umlaut.txt", "root", pat)
    assert len(matches) == 1
    assert matches[0].line_number == 1
    assert "Größe" in matches[0].line_text


def test_search_worker_multi_folder(qapp, tmp_path: Path):
    folder_a = tmp_path / "project_a"
    folder_a.mkdir()
    (folder_a / "a1.py").write_text("def run_code(): pass\n", encoding="utf-8")
    (folder_a / "a2.txt").write_text("just some text\n", encoding="utf-8")

    # Skipped folder
    git_dir = folder_a / ".git"
    git_dir.mkdir()
    (git_dir / "ignored.py").write_text("def run_code(): pass\n", encoding="utf-8")

    folder_b = tmp_path / "project_b"
    folder_b.mkdir()
    (folder_b / "b1.py").write_text("def run_code(): return 123\n", encoding="utf-8")

    options = SearchOptions(query="run_code", case_sensitive=False, include_globs=["*.py"])
    worker = SearchWorker(
        folders=[(folder_a, "Projekt A"), (folder_b, "Projekt B")],
        options=options,
    )

    collected_matches: list[SearchMatch] = []
    worker.matchFound.connect(collected_matches.append)

    completed_files = []
    worker.fileCompleted.connect(completed_files.append)

    finished_data = []
    worker.searchFinished.connect(lambda m, f, s: finished_data.append((m, f, s)))

    # Synchronous thread execution for deterministic test
    worker.run()

    assert len(collected_matches) == 2
    assert len(completed_files) == 2
    assert finished_data[0][0] == 2  # total matches
    assert finished_data[0][1] == 2  # total files with matches

    # Check relative paths and folder names
    files = {m.rel_path: m.folder_name for m in collected_matches}
    assert "a1.py" in files
    assert files["a1.py"] == "Projekt A"
    assert "b1.py" in files
    assert files["b1.py"] == "Projekt B"


def test_search_worker_cancellation(qapp, tmp_path: Path):
    folder = tmp_path / "test_cancel"
    folder.mkdir()
    for i in range(10):
        (folder / f"f{i}.py").write_text("token\n", encoding="utf-8")

    worker = SearchWorker(
        folders=[(folder, "CancelTest")],
        options=SearchOptions(query="token"),
    )
    worker.cancel()
    assert worker.is_cancelled() is True

    collected = []
    worker.matchFound.connect(collected.append)
    worker.run()

    # Cancelled before start -> 0 matches collected
    assert len(collected) == 0


def test_find_in_files_dialog_ui_and_jump(qapp, tmp_path: Path):
    # Setup test workspace with a file
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    file_target = project_dir / "target.py"
    file_target.write_text(
        "line 1\n"
        "line 2: target_keyword is here\n"
        "line 3\n",
        encoding="utf-8",
    )

    win = MainWindow()
    win.workspace.set_single_folder(project_dir)

    dlg = FindInFilesDialog(win)
    assert dlg.isVisible() is False
    assert dlg.scope_combo.count() > 0

    # Set query and run search
    dlg.search_input.setText("target_keyword")
    dlg.start_search()

    # Wait for background worker to complete
    if dlg._worker:
        dlg._worker.wait(3000)
    qapp.processEvents()

    # Verify results in tree
    assert dlg.results_tree.topLevelItemCount() == 1
    file_item = dlg.results_tree.topLevelItem(0)
    assert "target.py" in file_item.text(0)
    assert file_item.childCount() == 1

    match_item = file_item.child(0)
    assert "Z. 2:" in match_item.text(1)
    assert "target_keyword is here" in match_item.text(2)

    # Test double click trigger jump to file
    emitted_signal = []
    dlg.matchSelected.connect(lambda p, line_no, c, length: emitted_signal.append((p, line_no, c, length)))

    dlg._on_item_double_clicked(match_item, 0)
    assert len(emitted_signal) == 1
    assert emitted_signal[0][0] == file_target
    assert emitted_signal[0][1] == 2  # line 2

    # Verify editor opened and cursor jumped to line 2
    active_tab = win.get_active_tab()
    assert active_tab is not None
    assert active_tab.file_path.resolve() == file_target.resolve()
    cursor = active_tab.editor.textCursor()
    assert cursor.blockNumber() + 1 == 2
    assert cursor.selectedText() == "target_keyword"

    dlg.close()
    win.close()


def test_main_window_show_find_in_files(qapp, tmp_path: Path):
    test_file = tmp_path / "code.py"
    test_file.write_text("magic_function_name = 100\n", encoding="utf-8")

    win = MainWindow()
    tab = win.open_path(test_file)
    assert tab is not None

    # Select text in editor
    cursor = tab.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(19, cursor.MoveMode.KeepAnchor)
    tab.editor.setTextCursor(cursor)
    assert tab.editor.textCursor().selectedText() == "magic_function_name"

    # Call show_find_in_files without args -> should pre-fill from selection
    win.show_find_in_files()
    assert win._find_in_files_dialog is not None
    assert win._find_in_files_dialog.search_input.text() == "magic_function_name"

    win._find_in_files_dialog.close()
    win.close()


def test_shortcuts_and_menu_contract(qapp):
    # Check shortcut registered in shortcuts dialog
    matches = [s for s in SHORTCUTS_DATA if s[1] == "In Dateien suchen"]
    assert len(matches) == 1
    cat, name, key, desc = matches[0]
    assert key == "Ctrl+Shift+F"
    assert "Projektweite Textsuche" in desc

    # Check action in main window edit menu
    win = MainWindow()
    menubar = win.menuBar()
    edit_menu = None
    for a in menubar.actions():
        if a.menu() and "Bearbeiten" in a.menu().title():
            edit_menu = a.menu()
            break

    assert edit_menu is not None
    find_actions = [a for a in edit_menu.actions() if "In Dateien suchen" in a.text()]
    assert len(find_actions) == 1
    assert find_actions[0].shortcut().toString() == "Ctrl+Shift+F"
    win.close()
