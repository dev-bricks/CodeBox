#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für Git-Staging & Commit-Dialog in CodeBox.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from features.git_integration import GitRepo
from features.project_view import ProjectView
from ui.git_commit_dialog import GitCommitDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Initializes a real temporary git repo with user configuration and a test file."""
    # Initialize repo
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True, capture_output=True)

    # Create initial commit
    init_file = tmp_path / "README.md"
    init_file.write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), check=True, capture_output=True)

    return tmp_path


def test_git_repo_staging_and_commit(temp_git_repo: Path):
    """Tests GitRepo staging, unstaging, discard, and commit methods."""
    repo = GitRepo(str(temp_git_repo))
    assert repo.is_git_repo()

    # Modify existing file and create a new untracked file
    readme = temp_git_repo / "README.md"
    readme.write_text("# Test Repo\nModified line.\n", encoding="utf-8")

    new_file = temp_git_repo / "new_file.py"
    new_file.write_text("print('hello')\n", encoding="utf-8")

    # Status check
    status = repo.get_status()
    assert "README.md" in status
    assert status["README.md"].is_modified
    assert not status["README.md"].is_staged
    assert "new_file.py" in status
    assert status["new_file.py"].is_untracked

    # Stage specific file
    assert repo.stage_file("README.md")
    status_after_stage = repo.get_status()
    assert status_after_stage["README.md"].is_staged

    # Unstage specific file
    assert repo.unstage_file("README.md")
    status_after_unstage = repo.get_status()
    assert not status_after_unstage["README.md"].is_staged

    # Stage all
    assert repo.stage_all()
    status_all = repo.get_status()
    assert status_all["README.md"].is_staged
    assert status_all["new_file.py"].is_staged

    # Unstage all
    assert repo.unstage_all()
    status_none = repo.get_status()
    assert not status_none["README.md"].is_staged
    assert not status_none["new_file.py"].is_staged

    # Discard changes on README.md
    assert repo.discard_file_changes("README.md")
    assert readme.read_text(encoding="utf-8") == "# Test Repo\n"

    # Discard untracked new_file.py
    assert repo.discard_file_changes("new_file.py")
    assert not new_file.exists()

    # Create change, stage and commit
    readme.write_text("# Updated header\n", encoding="utf-8")
    assert repo.stage_file("README.md")

    # Empty commit message should fail
    success, err = repo.commit("")
    assert not success

    # Valid commit
    success, msg = repo.commit("feat: update readme")
    assert success
    assert "feat: update readme" in repo.get_log(limit=1)[0]


def test_git_commit_dialog_ui(qapp, temp_git_repo: Path):
    """Tests the GitCommitDialog UI components, lists, actions and commit submission."""
    # Modify a file
    f = temp_git_repo / "README.md"
    f.write_text("# Changed text\n", encoding="utf-8")

    repo = GitRepo(str(temp_git_repo))
    dialog = GitCommitDialog(repo_root=temp_git_repo, git_repo=repo)
    dialog.show()

    # Check initially unstaged item is listed
    assert dialog.list_unstaged.count() == 1
    assert dialog.list_staged.count() == 0
    assert not dialog.btn_commit.isEnabled()

    # Stage all via button
    dialog.btn_stage_all.click()
    assert dialog.list_staged.count() == 1
    assert dialog.list_unstaged.count() == 0

    # Double click on staged item -> unstages
    staged_item = dialog.list_staged.item(0)
    dialog._on_staged_item_double_clicked(staged_item)
    assert dialog.list_staged.count() == 0
    assert dialog.list_unstaged.count() == 1

    # Double click on unstaged item -> stages
    unstaged_item = dialog.list_unstaged.item(0)
    dialog._on_unstaged_item_double_clicked(unstaged_item)
    assert dialog.list_staged.count() == 1
    assert dialog.list_unstaged.count() == 0

    # Commit button remains disabled until message is typed
    assert not dialog.btn_commit.isEnabled()
    dialog.txt_message.setPlainText("Test commit message")
    assert dialog.btn_commit.isEnabled()
    assert "19 Zeichen" in dialog.lbl_char_count.text()

    # Track signals
    committed_messages = []
    dialog.committed.connect(lambda msg: committed_messages.append(msg))

    status_changed_events = []
    dialog.status_changed.connect(lambda: status_changed_events.append(True))

    # Trigger commit
    dialog._on_commit()

    assert len(committed_messages) == 1
    assert committed_messages[0] == "Test commit message"
    assert len(status_changed_events) > 0
    assert "Test commit message" in repo.get_log(limit=1)[0]

    dialog.close()


def test_project_view_git_integration(qapp, temp_git_repo: Path):
    """Tests ProjectView commit button and context menu Git staging helpers."""
    pv = ProjectView()
    pv.show()

    # Initially no root -> btn_commit disabled
    assert not pv.btn_commit.isEnabled()

    # Set root to git repo -> btn_commit enabled
    pv.set_root(str(temp_git_repo))
    assert pv.btn_commit.isEnabled()

    # Create change
    test_file = temp_git_repo / "README.md"
    test_file.write_text("# Changes\n", encoding="utf-8")
    pv._refresh()

    repo = GitRepo(str(temp_git_repo))
    status = repo.get_status()
    assert not status["README.md"].is_staged

    # Test _stage_file
    pv._stage_file(test_file)
    status_staged = repo.get_status()
    assert status_staged["README.md"].is_staged

    # Test _unstage_file
    pv._unstage_file(test_file)
    status_unstaged = repo.get_status()
    assert not status_unstaged["README.md"].is_staged

    # Test commitRequested signal
    signals_emitted = []
    pv.commitRequested.connect(lambda p: signals_emitted.append(p))

    with patch("ui.git_commit_dialog.GitCommitDialog.exec"):
        pv.open_commit_dialog(initial_file=test_file)

    assert len(signals_emitted) == 1
    assert signals_emitted[0] == test_file

    pv.close()
