#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermetic Regression Tests for Git Staging & Commit Dialog, Diff Viewer Integration,
Staged Deletion Tracking, Relative Path Resolution, and Discard Resilience.

Bug complex identified during Bugsweep 2026-09-29:
1. GitCommitDialog._open_diff_viewer imported non-existent 'GitDiffDialog' from ui.diff_viewer,
   causing an uncaught ImportError / modal warning on every diff button click.
2. In GitCommitDialog.refresh(), files staged for deletion (index_status='D', work_status=' ')
   were duplicated into unstaged_items because status.is_deleted was True, causing ghost unstaged
   deletions in the UI.
3. GitCommitDialog.refresh() failed to select relative initial_file paths (e.g. Path('README.md'))
   because relative_to against absolute repo_root threw ValueError, silently ignored.
4. DiffViewerDialog.refresh_diff() crashed with AttributeError if select_file was a str, or failed
   to match relative Path objects when CWD != repo_root.
5. DiffViewerDialog enabled 'Im Editor öffnen' for deleted files, which failed upon clicking.
6. GitRepo.discard_file_changes skipped untracked directories (target.is_file() == False) and
   failed with git restore errors.
7. GitRepo.get_diff for untracked files with Windows backslashes emitted non-standard mixed headers.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from features.git_integration import GitRepo
from ui.git_commit_dialog import GitCommitDialog
from ui.diff_viewer import DiffViewerDialog, GitDiffDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Initializes a real git repo with user configuration and a test file."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True, capture_output=True)

    init_file = tmp_path / "README.md"
    init_file.write_text("# Test Repo\nInitial line.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), check=True, capture_output=True)

    return tmp_path


def test_git_commit_dialog_diff_viewer_import_and_opening(qapp, temp_git_repo: Path):
    """Verifies GitDiffDialog alias exists and _open_diff_viewer opens DiffViewerDialog cleanly."""
    # 1. Alias check
    assert GitDiffDialog is DiffViewerDialog

    # 2. Modify file so diff exists
    readme = temp_git_repo / "README.md"
    readme.write_text("# Test Repo\nModified line.\n", encoding="utf-8")

    repo = GitRepo(str(temp_git_repo))
    dialog = GitCommitDialog(repo_root=temp_git_repo, git_repo=repo)
    dialog.show()

    # Open unstaged diff - must not throw ImportError or raise exception
    with patch("ui.diff_viewer.DiffViewerDialog.exec") as mock_exec:
        dialog._on_diff_unstaged()
        assert mock_exec.called, "DiffViewerDialog.exec() should be called without ImportError"

    # Stage file and open staged diff
    dialog._on_stage_all()
    with patch("ui.diff_viewer.DiffViewerDialog.exec") as mock_exec:
        dialog._on_diff_staged()
        assert mock_exec.called, "DiffViewerDialog.exec() should be called for staged diff"

    dialog.close()


def test_git_commit_dialog_staged_deletion_not_duplicated_in_unstaged(qapp, temp_git_repo: Path):
    """Verifies that a file staged for deletion does NOT appear in unstaged_items."""
    # Create and commit an extra file
    extra_file = temp_git_repo / "obsolete.txt"
    extra_file.write_text("to be deleted\n", encoding="utf-8")
    subprocess.run(["git", "add", "obsolete.txt"], cwd=str(temp_git_repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add obsolete file"], cwd=str(temp_git_repo), check=True, capture_output=True)

    # Delete the file and stage the deletion
    extra_file.unlink()
    repo = GitRepo(str(temp_git_repo))
    assert repo.stage_file("obsolete.txt")

    status_dict = repo.get_status()
    assert "obsolete.txt" in status_dict
    status = status_dict["obsolete.txt"]
    assert status.is_staged
    assert status.index_status == "D"
    assert status.work_status == " "

    dialog = GitCommitDialog(repo_root=temp_git_repo, git_repo=repo)
    dialog.show()

    # obsolete.txt MUST be in staged list
    assert dialog.list_staged.count() == 1
    staged_item = dialog.list_staged.item(0)
    assert "obsolete.txt" in staged_item.text()
    assert "[D]" in staged_item.text()

    # obsolete.txt MUST NOT be in unstaged list!
    assert dialog.list_unstaged.count() == 0
    assert len(dialog.unstaged_items) == 0

    dialog.close()


def test_git_commit_dialog_relative_initial_file_selection(qapp, temp_git_repo: Path):
    """Verifies that passing a relative initial_file Path selects the item in the list."""
    readme = temp_git_repo / "README.md"
    readme.write_text("# Modified\n", encoding="utf-8")

    repo = GitRepo(str(temp_git_repo))

    # Pass relative path: Path("README.md")
    dialog = GitCommitDialog(repo_root=temp_git_repo, git_repo=repo, initial_file=Path("README.md"))
    dialog.show()

    cur_item = dialog.list_unstaged.currentItem()
    assert cur_item is not None, "Relative initial_file should be selected in unstaged list"
    assert cur_item.data(0x0100) == "README.md"  # Qt.ItemDataRole.UserRole == 0x0100 (256)

    dialog.close()


def test_diff_viewer_dialog_relative_select_file_and_string_path(qapp, temp_git_repo: Path):
    """Verifies DiffViewerDialog handles relative Path and string select_file arguments."""
    readme = temp_git_repo / "README.md"
    readme.write_text("# Modified\n", encoding="utf-8")

    # 1. String path
    diff_dialog_str = DiffViewerDialog(repo_root=temp_git_repo, initial_file="README.md")
    diff_dialog_str.show()
    assert diff_dialog_str.file_combo.currentData() == "README.md"
    diff_dialog_str.close()

    # 2. Relative Path
    diff_dialog_path = DiffViewerDialog(repo_root=temp_git_repo, initial_file=Path("README.md"))
    diff_dialog_path.show()
    assert diff_dialog_path.file_combo.currentData() == "README.md"
    diff_dialog_path.close()


def test_diff_viewer_open_in_editor_disabled_for_deleted_file(qapp, temp_git_repo: Path):
    """Verifies 'Im Editor öffnen' is disabled for deleted files in DiffViewerDialog."""
    del_file = temp_git_repo / "del_me.txt"
    del_file.write_text("temp\n", encoding="utf-8")
    subprocess.run(["git", "add", "del_me.txt"], cwd=str(temp_git_repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add del_me"], cwd=str(temp_git_repo), check=True, capture_output=True)

    del_file.unlink()
    repo = GitRepo(str(temp_git_repo))
    assert repo.stage_file("del_me.txt")

    diff_dialog = DiffViewerDialog(repo_root=temp_git_repo, initial_file="del_me.txt", staged=True)
    diff_dialog.show()

    assert diff_dialog.file_combo.currentData() == "del_me.txt"
    assert not diff_dialog.btn_open_editor.isEnabled(), "Editor button must be disabled for non-existent/deleted files"

    # open_selected_in_editor should safely no-op without attempting to open non-existent file
    mock_mw = MagicMock()
    diff_dialog.main_window = mock_mw
    diff_dialog.open_selected_in_editor()
    assert not mock_mw.open_path.called

    diff_dialog.close()


def test_git_repo_discard_untracked_directory(temp_git_repo: Path):
    """Verifies GitRepo.discard_file_changes safely removes an untracked directory."""
    repo = GitRepo(str(temp_git_repo))

    untracked_dir = temp_git_repo / "new_dir"
    untracked_dir.mkdir()
    (untracked_dir / "child.txt").write_text("hello", encoding="utf-8")

    status = repo.get_status()
    # status could report "new_dir/child.txt" or "new_dir"
    rel_key = "new_dir/child.txt" if "new_dir/child.txt" in status else "new_dir"
    assert rel_key in status
    assert status[rel_key].is_untracked

    assert repo.discard_file_changes(rel_key)
    assert not (untracked_dir / "child.txt").exists()


def test_git_repo_untracked_diff_windows_path_normalization(temp_git_repo: Path):
    """Verifies GitRepo.get_diff normalizes Windows backslashes in untracked file diff headers."""
    repo = GitRepo(str(temp_git_repo))

    sub_dir = temp_git_repo / "sub"
    sub_dir.mkdir()
    (sub_dir / "untracked.py").write_text("val = 42\n", encoding="utf-8")

    diff = repo.get_diff("sub\\untracked.py")
    assert diff is not None
    assert "--- a/sub/untracked.py" in diff
    assert "+++ b/sub/untracked.py" in diff
    assert "+val = 42" in diff
