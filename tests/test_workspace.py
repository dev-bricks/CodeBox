#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit Tests für WorkspaceFolder und WorkspaceManager (Multi-Root-Workspace)."""

from PySide6.QtWidgets import QApplication

from core.workspace import WorkspaceFolder, WorkspaceManager


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_workspace_folder_to_and_from_dict(tmp_path):
    _ensure_app()
    folder_path = tmp_path / "frontend"
    folder_path.mkdir()

    wf = WorkspaceFolder(path=folder_path, name="Frontend Client")
    d = wf.to_dict(base_dir=tmp_path)
    assert d["name"] == "Frontend Client"
    assert d["path"] == "frontend"

    # From dict with base_dir
    wf2 = WorkspaceFolder.from_dict(d, base_dir=tmp_path)
    assert wf2 is not None
    assert wf2.path == folder_path.resolve()
    assert wf2.name == "Frontend Client"


def test_workspace_manager_add_and_remove(tmp_path):
    _ensure_app()
    wm = WorkspaceManager()

    dir_a = tmp_path / "mod_a"
    dir_b = tmp_path / "mod_b"
    dir_a.mkdir()
    dir_b.mkdir()

    folders_changed_calls = []
    active_changed_calls = []

    wm.foldersChanged.connect(lambda: folders_changed_calls.append(True))
    wm.activeFolderChanged.connect(lambda p: active_changed_calls.append(p))

    assert wm.is_empty
    assert not wm.is_multi_root

    # Add first folder
    ok = wm.add_folder(dir_a, name="Modul A")
    assert ok is True
    assert len(wm.folders) == 1
    assert wm.active_folder == dir_a.resolve()
    assert wm.has_folder(dir_a)
    assert not wm.is_multi_root
    assert not wm.is_empty
    assert len(folders_changed_calls) == 1
    assert len(active_changed_calls) == 1

    # Add duplicate folder -> no duplicate added, but returns True
    ok_dup = wm.add_folder(dir_a)
    assert ok_dup is True
    assert len(wm.folders) == 1

    # Add second folder -> becomes multi-root
    ok_b = wm.add_folder(dir_b, name="Modul B", make_active=True)
    assert ok_b is True
    assert len(wm.folders) == 2
    assert wm.is_multi_root
    assert wm.active_folder == dir_b.resolve()

    # Switch active folder
    wm.set_active_folder(dir_a)
    assert wm.active_folder == dir_a.resolve()

    # Remove active folder -> switches active to remaining folder
    ok_rm = wm.remove_folder(dir_a)
    assert ok_rm is True
    assert len(wm.folders) == 1
    assert not wm.is_multi_root
    assert wm.active_folder == dir_b.resolve()

    # Clear
    wm.clear()
    assert wm.is_empty
    assert wm.active_folder is None


def test_workspace_manager_find_folder_for_file(tmp_path):
    _ensure_app()
    wm = WorkspaceManager()

    root_a = tmp_path / "service_a"
    root_b = tmp_path / "service_b"
    sub_a = root_a / "sub" / "core"
    sub_a.mkdir(parents=True)
    root_b.mkdir(parents=True)

    file_a = sub_a / "main.py"
    file_a.write_text("print(1)\n", encoding="utf-8")
    file_b = root_b / "app.py"
    file_b.write_text("print(2)\n", encoding="utf-8")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("hello", encoding="utf-8")

    wm.add_folder(root_a)
    wm.add_folder(root_b)

    assert wm.find_folder_for_file(file_a) == root_a.resolve()
    assert wm.find_folder_for_file(file_b) == root_b.resolve()
    assert wm.find_folder_for_file(outside_file) is None


def test_workspace_manager_save_and_load(tmp_path):
    _ensure_app()
    wm = WorkspaceManager()

    dir_1 = tmp_path / "src1"
    dir_2 = tmp_path / "src2"
    dir_1.mkdir()
    dir_2.mkdir()

    wm.name = "Test Workspace"
    wm.add_folder(dir_1, "Source 1")
    wm.add_folder(dir_2, "Source 2")

    ws_file = tmp_path / "project.codebox-workspace"
    saved = wm.save_workspace(ws_file)
    assert saved is True
    assert ws_file.exists()

    # Load in a fresh manager
    wm2 = WorkspaceManager()
    loaded = wm2.load_workspace(ws_file)
    assert loaded is True
    assert wm2.name == "Test Workspace"
    assert len(wm2.folders) == 2
    assert wm2.folders[0].path == dir_1.resolve()
    assert wm2.folders[0].name == "Source 1"
    assert wm2.folders[1].path == dir_2.resolve()
    assert wm2.folders[1].name == "Source 2"
    assert wm2.active_folder == dir_1.resolve()


def test_workspace_manager_collect_all_files(tmp_path):
    _ensure_app()
    wm = WorkspaceManager()

    dir_a = tmp_path / "pkg_a"
    dir_b = tmp_path / "pkg_b"
    dir_a.mkdir()
    dir_b.mkdir()

    (dir_a / "alpha.py").write_text("a", encoding="utf-8")
    (dir_a / "shared.py").write_text("shared_a", encoding="utf-8")
    (dir_b / "beta.py").write_text("b", encoding="utf-8")
    (dir_b / "shared.py").write_text("shared_b", encoding="utf-8")

    wm.add_folder(dir_a, "Package A")
    wm.add_folder(dir_b, "Package B")

    files = wm.collect_all_files()
    assert len(files) == 4

    rel_and_folders = [(f[0], f[2]) for f in files]
    assert ("alpha.py", "Package A") in rel_and_folders
    assert ("shared.py", "Package A") in rel_and_folders
    assert ("beta.py", "Package B") in rel_and_folders
    assert ("shared.py", "Package B") in rel_and_folders
