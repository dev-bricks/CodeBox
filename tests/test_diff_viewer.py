#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für den integrierten Git Diff-Viewer (DiffViewerDialog, Highlighting, Navigation).
"""

import subprocess
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from features.git_integration import GitRepo
from ui.diff_viewer import (
    DiffHighlighter,
    DiffViewerDialog,
    SideBySideHighlighter,
    compute_side_by_side,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_git_repo(tmp_path):
    """Erstellt ein temporäres echtes Git-Repository mit initialem Commit und Änderungen."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "CodeBox Tester"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "tester@codebox.local"], cwd=str(tmp_path), check=True)

    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello world')\nline2\nline3\n", encoding="utf-8")

    subprocess.run(["git", "add", "hello.py"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), check=True)

    # Jetzt Datei ändern für Unstaged Diff
    test_file.write_text("print('hello CodeBox')\nline2\nnew line\nline3\n", encoding="utf-8")

    # Zweite Datei neu anlegen (untracked)
    untracked_file = tmp_path / "new_module.py"
    untracked_file.write_text("# new untracked file\n", encoding="utf-8")

    return tmp_path


def test_compute_side_by_side():
    old_text = "line1\nline2\nline3\n"
    new_text = "line1\nline2_modified\nline3\nextra\n"

    left, right = compute_side_by_side(old_text, new_text)
    assert len(left) == len(right)
    assert any("[~]" in item_left or "[-]" in item_left for item_left in left)
    assert any("[~]" in item_right or "[+]" in item_right for item_right in right)


def test_diff_highlighter_instantiation(qapp):
    from PySide6.QtGui import QTextDocument
    doc = QTextDocument()
    doc.setPlainText("--- a/foo\n+++ b/foo\n@@ -1,1 +1,2 @@\n-line1\n+line2\n")
    highlighter = DiffHighlighter(doc)
    assert highlighter is not None


def test_side_by_side_highlighter_instantiation(qapp):
    from PySide6.QtGui import QTextDocument
    doc_old = QTextDocument()
    doc_old.setPlainText("[-] deleted line\n[~] modified line\n")
    hl_old = SideBySideHighlighter("old", doc_old)
    assert hl_old is not None

    doc_new = QTextDocument()
    doc_new.setPlainText("[+] added line\n[~] modified line\n")
    hl_new = SideBySideHighlighter("new", doc_new)
    assert hl_new is not None


def test_diff_viewer_no_git_repo(qapp, tmp_path):
    dialog = DiffViewerDialog(repo_root=tmp_path)
    assert dialog.file_combo.count() >= 1
    assert "Kein Git-Repository" in dialog.file_combo.itemText(0)
    assert not dialog.btn_open_editor.isEnabled()
    dialog.close()


def test_diff_viewer_with_git_repo(qapp, temp_git_repo):
    dialog = DiffViewerDialog(repo_root=temp_git_repo)

    # Dateiauswahl sollte "(Alle geänderten Dateien)" und "hello.py" enthalten
    items = [dialog.file_combo.itemText(i) for i in range(dialog.file_combo.count())]
    assert "(Alle geänderten Dateien)" in items[0]
    assert any("hello.py" in it for it in items)

    # Diff-Text sollte im Unified View sichtbar sein
    text = dialog.unified_view.toPlainText()
    assert "hello.py" in text
    assert "+print('hello CodeBox')" in text or "+new line" in text

    # Stats
    stats_text = dialog.stats_label.text()
    assert "+" in stats_text
    assert "-" in stats_text

    dialog.close()


def test_diff_viewer_file_selection_and_side_by_side(qapp, temp_git_repo):
    dialog = DiffViewerDialog(repo_root=temp_git_repo)

    # Finde Index von hello.py
    hello_idx = -1
    for i in range(dialog.file_combo.count()):
        if "hello.py" in dialog.file_combo.itemText(i):
            hello_idx = i
            break
    assert hello_idx > 0

    dialog.file_combo.setCurrentIndex(hello_idx)
    assert dialog.btn_open_editor.isEnabled()

    # Umschalten auf Side-by-Side
    dialog.mode_combo.setCurrentIndex(1)
    assert dialog.stack.currentIndex() == 1

    base_text = dialog.base_view.toPlainText()
    mod_text = dialog.mod_view.toPlainText()
    assert "hello world" in base_text
    assert "hello CodeBox" in mod_text

    dialog.close()


def test_diff_viewer_staged_toggle(qapp, temp_git_repo):
    dialog = DiffViewerDialog(repo_root=temp_git_repo)

    # Zu Beginn: unstaged Änderungen
    assert not dialog.staged_checkbox.isChecked()
    assert "hello.py" in dialog.unified_view.toPlainText()

    # Jetzt stage hello.py
    subprocess.run(["git", "add", "hello.py"], cwd=str(temp_git_repo), check=True)

    # Staged Checkbox aktivieren
    dialog.staged_checkbox.setChecked(True)
    staged_text = dialog.unified_view.toPlainText()
    assert "hello.py" in staged_text

    dialog.close()


def test_diff_viewer_chunk_navigation(qapp, temp_git_repo):
    dialog = DiffViewerDialog(repo_root=temp_git_repo)

    # Navigiere durch Chunks
    dialog.next_chunk()
    dialog.prev_chunk()

    # Auch im Side-by-Side Modus testen
    dialog.mode_combo.setCurrentIndex(1)
    dialog.next_chunk()
    dialog.prev_chunk()

    dialog.close()


def test_diff_viewer_accessibility_attributes(qapp, temp_git_repo):
    dialog = DiffViewerDialog(repo_root=temp_git_repo)

    # Barrierefreiheit prüfen
    assert dialog.accessibleName() == "Git Diff-Viewer"
    assert "Code-Unterschiede" in dialog.accessibleDescription()

    assert dialog.file_combo.accessibleName() == "Geänderte Dateien"
    assert dialog.staged_checkbox.accessibleName() == "Nur gestagte Änderungen anzeigen"
    assert dialog.mode_combo.accessibleName() == "Ansichtsmodus"
    assert dialog.btn_prev.accessibleName() == "Vorheriger Diff-Block"
    assert dialog.btn_next.accessibleName() == "Nächster Diff-Block"
    assert dialog.btn_refresh.accessibleName() == "Diff aktualisieren"
    assert dialog.btn_open_editor.accessibleName() == "Datei im Editor öffnen"
    assert dialog.unified_view.accessibleName() == "Vereinheitlichte Diff-Ansicht"
    assert dialog.base_view.accessibleName() == "Basis-Code"
    assert dialog.mod_view.accessibleName() == "Geänderter Code"

    dialog.close()


def test_diff_viewer_open_in_editor(qapp, temp_git_repo):
    mock_main_window = MagicMock()
    dialog = DiffViewerDialog(main_window=mock_main_window, repo_root=temp_git_repo)

    # Wähle hello.py
    hello_idx = -1
    for i in range(dialog.file_combo.count()):
        if "hello.py" in dialog.file_combo.itemText(i):
            hello_idx = i
            break

    dialog.file_combo.setCurrentIndex(hello_idx)

    opened_paths = []
    dialog.fileOpenRequested.connect(lambda p: opened_paths.append(p))

    dialog.open_selected_in_editor()

    assert len(opened_paths) == 1
    assert opened_paths[0].name == "hello.py"
    mock_main_window.open_path.assert_called_once()


def test_git_repo_helpers(temp_git_repo):
    repo = GitRepo(str(temp_git_repo))
    assert repo.is_git_repo()

    head_content = repo.get_file_content_at_head("hello.py")
    assert "hello world" in head_content

    # In index testen
    index_content = repo.get_file_content_in_index("hello.py")
    assert "hello world" in index_content

    # Untracked diff testen
    untracked_diff = repo.get_diff("new_module.py")
    assert untracked_diff is not None
    assert "new_module.py" in untracked_diff


def test_diff_viewer_initial_file_selection(qapp, temp_git_repo):
    test_file = temp_git_repo / "hello.py"
    dialog = DiffViewerDialog(repo_root=temp_git_repo, initial_file=test_file)

    selected = dialog.file_combo.currentData()
    assert selected == "hello.py"
    assert dialog.btn_open_editor.isEnabled()
    dialog.close()


def test_project_view_diff_requested(qapp, tmp_path):
    from features.project_view import ProjectView

    pv = ProjectView()
    test_file = tmp_path / "sample.py"
    test_file.write_text("code = 1\n", encoding="utf-8")

    received = []
    pv.diffRequested.connect(lambda p: received.append(p))

    pv.diffRequested.emit(test_file)
    assert len(received) == 1
    assert received[0] == test_file

