#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration Tests für Multi-Root-Workspace in CodeBox."""

from PySide6.QtWidgets import QApplication

from core.workspace import WorkspaceManager
from features.project_view import ProjectView
from ui.main_window import MainWindow
from ui.command_palette import CommandPaletteDialog


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_multi_root_project_view_ui_integration(tmp_path):
    _ensure_app()
    wm = WorkspaceManager()
    pv = ProjectView()
    pv.set_workspace(wm)

    dir_a = tmp_path / "frontend"
    dir_b = tmp_path / "backend"
    dir_a.mkdir()
    dir_b.mkdir()

    # Initial: empty workspace, workspace selector hidden
    assert pv.workspace_widget.isHidden()
    assert pv.workspace_combo.count() == 0

    # Add single folder: still hidden (standard clean UI)
    pv.add_workspace_folder(dir_a, name="Frontend")
    assert pv.workspace_widget.isHidden()
    assert pv._root_path == dir_a.resolve()

    # Add second folder: multi-root selector becomes visible
    pv.add_workspace_folder(dir_b, name="Backend")
    assert not pv.workspace_widget.isHidden()
    assert pv.workspace_combo.count() == 2
    assert "Arbeitsbereich (2 Ordner)" in pv.title_label.text()
    assert pv._root_path == dir_b.resolve()

    # Switch folder via combo
    pv.workspace_combo.setCurrentIndex(0)
    assert wm.active_folder == dir_a.resolve()
    assert pv._root_path == dir_a.resolve()

    # Remove second folder: reverts to single folder, widget hidden
    pv.remove_workspace_folder(dir_b)
    assert pv.workspace_widget.isHidden()
    assert len(wm.folders) == 1
    assert wm.active_folder == dir_a.resolve()


def test_main_window_workspace_lifecycle(tmp_path):
    _ensure_app()
    win = MainWindow()

    dir_1 = tmp_path / "service1"
    dir_2 = tmp_path / "service2"
    dir_1.mkdir()
    dir_2.mkdir()

    # Open single folder
    win.open_folder(dir_1)
    assert len(win.workspace.folders) == 1
    assert win.workspace.active_folder == dir_1.resolve()

    # Add second folder
    win.add_workspace_folder(dir_2, name="Service 2")
    assert len(win.workspace.folders) == 2
    assert win.workspace.is_multi_root
    assert not win.project_view.workspace_widget.isHidden()

    # Save workspace
    ws_file = tmp_path / "my_project.codebox-workspace"
    saved = win.save_workspace_file(ws_file)
    assert saved is True
    assert ws_file.exists()

    # Close workspace
    win.close_workspace()
    assert win.workspace.is_empty
    assert win.project_view.workspace_widget.isHidden()

    # Reload workspace
    loaded = win.open_workspace_file(ws_file)
    assert loaded is True
    assert len(win.workspace.folders) == 2
    assert win.workspace.is_multi_root
    assert not win.project_view.workspace_widget.isHidden()

    win.close()


def test_main_window_file_switching_preserves_roots(tmp_path):
    _ensure_app()
    win = MainWindow()

    dir_a = tmp_path / "client"
    dir_b = tmp_path / "server"
    dir_a.mkdir()
    dir_b.mkdir()

    file_a = dir_a / "index.js"
    file_a.write_text("console.log('client');\n", encoding="utf-8")

    file_b = dir_b / "server.py"
    file_b.write_text("print('server')\n", encoding="utf-8")

    win.open_folder(dir_a)
    win.add_workspace_folder(dir_b)
    assert len(win.workspace.folders) == 2

    # Open file in dir_a -> active folder becomes dir_a without dropping dir_b
    win.open_path(file_a)
    assert win.workspace.active_folder == dir_a.resolve()
    assert len(win.workspace.folders) == 2

    # Open file in dir_b -> active folder becomes dir_b without dropping dir_a
    win.open_path(file_b)
    assert win.workspace.active_folder == dir_b.resolve()
    assert len(win.workspace.folders) == 2

    win.close()


def test_command_palette_multi_root_search(tmp_path):
    _ensure_app()
    win = MainWindow()

    dir_a = tmp_path / "app_ui"
    dir_b = tmp_path / "app_api"
    dir_a.mkdir()
    dir_b.mkdir()

    (dir_a / "ui_component.py").write_text("# ui", encoding="utf-8")
    (dir_b / "api_route.py").write_text("# api", encoding="utf-8")

    win.open_folder(dir_a)
    win.add_workspace_folder(dir_b)

    palette = CommandPaletteDialog(win, mode="files")
    palette._collect_files()

    file_entries = [f[0] for f in palette._all_files]
    assert any("ui_component.py" in e and "app_ui" in e for e in file_entries)
    assert any("api_route.py" in e and "app_api" in e for e in file_entries)

    palette.close()
    win.close()
