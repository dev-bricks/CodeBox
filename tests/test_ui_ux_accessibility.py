#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit- und Contract-Tests für UI-, UX-, Accessibility- und Sprach-Qualität in CodeBox."""

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.shortcuts_dialog import ShortcutsDialog, SHORTCUTS_DATA
from ui.plugins_dialog import PluginsDialog
from ui.problems_panel import ProblemsPanel
from core.tabs import TabWidget
from core.output import OutputPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_toolbar_ux_and_a11y(qapp):
    """Prüft Tooltips, StatusTips und Barrierefreiheit der Haupt-Toolbar."""
    window = MainWindow()
    try:
        # Toolbar Aktionen
        assert window.action_new.text() == "Neu"
        assert window.action_new.toolTip() == "Neue Datei erstellen (Ctrl+N)"
        assert window.action_new.statusTip() == "Erstellt eine neue leere Datei"
        assert len(window.action_new.whatsThis()) > 5

        assert window.action_open.text() == "Öffnen"
        assert window.action_open.toolTip() == "Datei öffnen (Ctrl+O)"
        assert window.action_open.statusTip() == "Öffnet eine bestehende Datei von der Festplatte"
        assert len(window.action_open.whatsThis()) > 5

        assert window.action_save.text() == "Speichern"
        assert window.action_save.toolTip() == "Aktuelle Datei speichern (Ctrl+S)"
        assert window.action_save.statusTip() == "Speichert die aktive Datei auf die Festplatte"
        assert len(window.action_save.whatsThis()) > 5

        assert window.action_run.text() == "Ausführen"
        assert window.action_run.toolTip() == "Aktuelle Datei ausführen (F5)"
        assert window.action_run.statusTip() == "Führt das aktuelle Skript oder Programm aus"
        assert len(window.action_run.whatsThis()) > 5

        # Sprach-Combo
        assert "Syntax-Highlighting" in window.lang_combo.toolTip()
        assert window.lang_combo.accessibleName() == "Programmiersprache"
        assert len(window.lang_combo.accessibleDescription()) > 10

        # Statusbar
        assert window.pos_label.accessibleName() == "Cursorposition"
        assert "Cursor-Position" in window.pos_label.toolTip()
        assert window.lang_label.accessibleName() == "Aktive Sprache"
        assert window.enc_label.accessibleName() == "Dateikodierung"
        assert window.enc_label.text() == "UTF-8"

        # Bottom Tabs
        assert window.bottom_tabs.accessibleName() == "Unteres Bedienpanel"
        assert window.bottom_tabs.tabToolTip(0) == "Programmausgabe und Fehlermeldungen anzeigen"
        assert window.bottom_tabs.tabToolTip(1) == "Integriertes Befehlszeilenterminal"
        assert window.bottom_tabs.tabToolTip(2) == "LSP- und Linter-Diagnosen und Fehlermeldungen"
    finally:
        window.close()


def test_tab_widget_ux_tooltips_and_a11y(qapp, tmp_path):
    """Prüft Tab-Tooltips mit echtem Pfad und Accessible-Attribute."""
    tabs = TabWidget()
    assert tabs.accessibleName() == "Editor-Tabs"
    assert "Reiterleiste" in tabs.accessibleDescription()

    # Leerer neuer Tab
    tab1 = tabs.new_tab()
    assert tabs.tabToolTip(0) == "Neues Dokument (ungespeichert)"

    # Datei-Tab mit Pfad
    test_file = tmp_path / "main.py"
    test_file.write_text("print('hello')", encoding="utf-8")
    tabs.open_file(test_file)
    assert tabs.tabToolTip(1) == str(test_file)

    # Nach Speichern aktualisiert
    tab1.file_path = tmp_path / "neu.py"
    tab1.save()
    tabs._update_tab_title(tab1)
    assert tabs.tabToolTip(0) == str(tab1.file_path)


def test_settings_dialog_ux_and_a11y(qapp):
    """Prüft Tooltips und AccessibleNames aller Steuerelemente im Einstellungsdialog."""
    dialog = SettingsDialog()
    assert dialog.font_combo.accessibleName() == "Schriftart"
    assert len(dialog.font_combo.toolTip()) > 5
    assert dialog.font_size_spin.accessibleName() == "Schriftgröße"
    assert len(dialog.font_size_spin.toolTip()) > 5
    assert dialog.tab_size_spin.accessibleName() == "Tab-Breite"
    assert len(dialog.tab_size_spin.toolTip()) > 5
    assert dialog.theme_combo.accessibleName() == "Farbschema"
    assert len(dialog.theme_combo.toolTip()) > 5
    assert dialog.auto_save_cb.accessibleName() == "Dateien beim Ausführen automatisch speichern"
    assert len(dialog.auto_save_cb.toolTip()) > 5
    assert dialog.minimap_cb.accessibleName() == "Minimap anzeigen"
    assert len(dialog.minimap_cb.toolTip()) > 5


def test_shortcuts_dialog_ux_and_a11y(qapp):
    """Prüft Suchfilter, Tabelle und Accessible-Attribute im ShortcutsDialog."""
    dialog = ShortcutsDialog()
    assert dialog.search_input.accessibleName() == "Tastenkürzel filtern"
    assert len(dialog.search_input.toolTip()) > 5
    assert dialog.table.accessibleName() == "Tastenkürzel-Tabelle"
    assert dialog.btn_close.accessibleName() == "Tastenkürzel-Übersicht schließen"

    # Filterung testen
    assert dialog.table.rowCount() == len(SHORTCUTS_DATA)
    dialog.filter_table("Ctrl+S")
    visible_rows = [r for r in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(r)]
    assert len(visible_rows) >= 1

    dialog.filter_table("")
    visible_rows_all = [r for r in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(r)]
    assert len(visible_rows_all) == len(SHORTCUTS_DATA)


def test_plugins_dialog_ux_and_a11y(qapp):
    """Prüft Tabelle, Detailsfeld, Buttons und Accessible-Attribute im PluginsDialog."""
    dialog = PluginsDialog()
    assert dialog.table.accessibleName() == "Installierte Sprach-Plugins und Provider"
    assert dialog.details_text.accessibleName() == "Plugin-Details"
    assert dialog.btn_open_folder.accessibleName() == "Plugin-Ordner öffnen"
    assert dialog.btn_create.accessibleName() == "Neues JSON-Plugin erstellen"
    assert dialog.btn_reload.accessibleName() == "Plugins neu laden"
    assert dialog.btn_close.accessibleName() == "Plugin-Dialog schließen"


def test_problems_and_output_panel_a11y(qapp):
    """Prüft Accessible-Attribute von ProblemsPanel und OutputPanel."""
    problems = ProblemsPanel()
    assert problems.tree.accessibleName() == "Problems-Panel"

    output = OutputPanel()
    assert output.status_label.accessibleName() == "Ausführungsstatus"
    assert output.run_btn.accessibleName() == "Aktuelle Datei ausführen"
    assert output.stop_btn.accessibleName() == "Ausführung stoppen"
    assert output.clear_btn.accessibleName() == "Ausgabe leeren"
    assert output.output.accessibleName() == "Programmausgabe"
