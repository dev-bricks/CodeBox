#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für CodeBox-Minimap und ihre Editor-Einstellung."""

import gc
import weakref

import pytest
from PySide6.QtWidgets import QApplication

from config import load_settings, save_settings
from core.editor import CodeEditor, Minimap
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_minimap_navigation_and_visibility(qapp):
    editor = CodeEditor()
    editor.resize(520, 280)
    editor.setPlainText("\n".join(f"def function_{i}(): return {i}" for i in range(120)))
    editor.show()
    qapp.processEvents()

    assert isinstance(editor.minimap, Minimap)
    assert editor.is_minimap_visible()
    assert editor.minimap.isVisible()
    assert editor.viewportMargins().right() == Minimap.WIDTH
    assert editor.verticalScrollBar().maximum() > 0

    editor.minimap._scroll_to_position(editor.minimap.height())
    qapp.processEvents()
    assert editor.verticalScrollBar().value() == editor.verticalScrollBar().maximum()
    assert editor.minimap.viewport_rect.top() > 0

    editor.set_minimap_visible(False)
    assert not editor.is_minimap_visible()
    assert not editor.minimap.isVisible()
    assert editor.viewportMargins().right() == 0

    editor.set_minimap_visible(True)
    assert editor.minimap.isVisible()
    assert editor.viewportMargins().right() == Minimap.WIDTH
    editor.close()


def test_minimap_signal_connections_release_closed_editor(qapp):
    references = []
    for _ in range(3):
        editor = CodeEditor()
        editor.setPlainText("first\nsecond")
        assert editor.minimap._document_lines() == ["first", "second"]
        editor.appendPlainText("third")
        assert editor.minimap._cached_lines is None
        assert editor.minimap._document_lines() == ["first", "second", "third"]
        references.append(weakref.ref(editor))
        editor.close()
        del editor
    gc.collect()
    qapp.processEvents()
    assert all(reference() is None for reference in references)


def test_main_window_applies_minimap_setting(qapp, tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr("config._SETTINGS_FILE", settings_file)
    save_settings({"show_minimap": False})

    window = MainWindow()
    tab = window.tab_widget.current_tab()
    assert tab is not None
    assert not tab.editor.is_minimap_visible()

    settings = load_settings()
    settings["show_minimap"] = True
    window._settings = settings
    window._apply_settings()
    assert tab.editor.is_minimap_visible()
    window.close()
