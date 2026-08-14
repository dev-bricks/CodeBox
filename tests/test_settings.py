#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit-Tests für CodeBox Einstellungs-Persistenz und Dialog (TW-CB-05)"""

import pytest
from PySide6.QtWidgets import QApplication

from config import DEFAULT_SETTINGS, load_settings, save_settings
from ui.settings_dialog import SettingsDialog
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_default_settings_keys():
    """Prüft, ob alle Standard-Einstellungs-Schlüssel vorhanden sind."""
    required_keys = {"font_family", "font_size", "tab_size", "theme", "auto_save", "show_minimap"}
    for key in required_keys:
        assert key in DEFAULT_SETTINGS


def test_settings_dialog_initialization(qapp, tmp_path, monkeypatch):
    """Prüft die Initialisierung des Einstellungsdialogs."""
    test_settings_file = tmp_path / "settings.json"
    monkeypatch.setattr("config._SETTINGS_FILE", test_settings_file)

    custom_settings = {
        "font_family": "Courier New",
        "font_size": 14,
        "tab_size": 2,
        "theme": "light",
        "auto_save": True,
        "show_minimap": False
    }
    save_settings(custom_settings)

    dialog = SettingsDialog()
    retrieved = dialog.get_settings()

    assert retrieved["font_size"] == 14
    assert retrieved["tab_size"] == 2
    assert retrieved["theme"] == "light"
    assert retrieved["auto_save"] is True
    assert retrieved["show_minimap"] is False


def test_main_window_applies_settings(qapp, tmp_path, monkeypatch):
    """Prüft, ob das Hauptfenster die geladenen Einstellungen auf Editor-Tabs anwendet."""
    test_settings_file = tmp_path / "settings.json"
    monkeypatch.setattr("config._SETTINGS_FILE", test_settings_file)

    custom_settings = {
        "font_family": "Consolas",
        "font_size": 16,
        "tab_size": 8,
        "theme": "dark",
        "auto_save": False,
        "show_minimap": True
    }
    save_settings(custom_settings)

    window = MainWindow()

    # Tab 1 sollte bereits Einstellungen haben
    tab = window.tab_widget.current_tab()
    assert tab is not None
    font = tab.editor.font()
    assert font.pointSize() == 16

    # Dialog manuell öffnen und ausführen simulieren
    dialog = SettingsDialog(window)
    dialog.font_size_spin.setValue(18)
    dialog.tab_size_spin.setValue(4)
    dialog.accept()

    # Nach accept() sollte MainWindow Settings neu laden und anwenden
    window._settings = load_settings()
    window._apply_settings()

    assert tab.editor.font().pointSize() == 18

    window.close()
