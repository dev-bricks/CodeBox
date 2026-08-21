#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugins-Dialog für CodeBox.
Zeigt installierte und eingebaute Sprach-Erweiterungen an und erlaubt das Neuladen oder Erstellen neuer Plugins.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QTextEdit,
    QMessageBox,
    QInputDialog,
    QGroupBox,
    QSplitter,
)

from languages import get_all_providers
from features.plugin_manager import PluginManager


class PluginsDialog(QDialog):
    """Dialog zur Anzeige und Verwaltung von Sprach-Plugins."""

    def __init__(self, plugin_manager: Optional[PluginManager] = None, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager or PluginManager()
        self.setWindowTitle("CodeBox Plugins & Sprachen")
        self.resize(780, 520)
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header Info
        header_label = QLabel(
            "<b>Installierte Sprachunterstützungen und Plugins</b><br>"
            "<span style='color: #888;'>CodeBox unterstützt eingebaute Provider sowie benutzerdefinierte .json- und .py-Plugins.</span>"
        )
        main_layout.addWidget(header_label)

        # Splitter für Tabelle oben und Details unten
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Tabelle
        self.table = QTableWidget()
        self.table.setObjectName("plugins_table")
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Sprache", "Typ", "Version", "Endungen", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName("Installierte Sprach-Plugins und Provider")
        self.table.setAccessibleDescription("Liste aller registrierten Sprachen und Plugins mit Typ, Version, Dateiendungen und Status")
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        # Details-Box
        details_box = QGroupBox("Plugin-Details")
        details_layout = QVBoxLayout(details_box)
        self.details_text = QTextEdit()
        self.details_text.setObjectName("plugin_details_text")
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Wähle ein Plugin oder eine Sprache aus der Liste für Details...")
        self.details_text.setAccessibleName("Plugin-Details")
        self.details_text.setAccessibleDescription("Detaillierte Beschreibung, Syntaxmuster und Konfiguration des ausgewählten Plugins")
        details_layout.addWidget(self.details_text)
        splitter.addWidget(details_box)

        splitter.setSizes([300, 160])
        main_layout.addWidget(splitter)

        # Button-Leiste
        btn_layout = QHBoxLayout()

        self.btn_open_folder = QPushButton("Plugin-Ordner öffnen")
        self.btn_open_folder.setObjectName("btn_open_plugin_folder")
        self.btn_open_folder.setToolTip("Öffnet das lokale Verzeichnis für externe Plugins im Datei-Explorer")
        self.btn_open_folder.setAccessibleName("Plugin-Ordner öffnen")
        self.btn_open_folder.clicked.connect(self._open_plugin_folder)
        btn_layout.addWidget(self.btn_open_folder)

        self.btn_create = QPushButton("Neues JSON-Plugin...")
        self.btn_create.setObjectName("btn_create_plugin")
        self.btn_create.setToolTip("Erstellt eine neue JSON-Plugin-Vorlage für eine Sprache")
        self.btn_create.setAccessibleName("Neues JSON-Plugin erstellen")
        self.btn_create.clicked.connect(self._create_plugin_template)
        btn_layout.addWidget(self.btn_create)

        self.btn_reload = QPushButton("Neu laden")
        self.btn_reload.setObjectName("btn_reload_plugins")
        self.btn_reload.setToolTip("Lädt alle Sprach-Plugins aus dem Plugin-Verzeichnis neu")
        self.btn_reload.setAccessibleName("Plugins neu laden")
        self.btn_reload.clicked.connect(self._reload_plugins)
        btn_layout.addWidget(self.btn_reload)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Schließen")
        self.btn_close.setObjectName("btn_close_plugins_dialog")
        self.btn_close.setToolTip("Schließt den Plugin-Dialog")
        self.btn_close.setAccessibleName("Plugin-Dialog schließen")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(btn_layout)

    def refresh_list(self):
        """Aktualisiert die Tabelle der verfügbaren Sprachen und Plugins."""
        self.table.setRowCount(0)
        all_providers = get_all_providers()
        plugins_by_name = {p.name: p for p in self.plugin_manager.get_all_plugins()}

        # 1. Alle registrierten Provider
        for provider in all_providers:
            name = provider.get_name()
            plugin_info = plugins_by_name.get(name)

            if plugin_info:
                p_type = "JSON Plugin" if plugin_info.plugin_type == "declarative_json" else "Python Plugin"
                version = plugin_info.version
                status = "Aktiv" if plugin_info.enabled else "Deaktiviert"
            else:
                p_type = "Eingebaut"
                version = "1.0.0"
                status = "Aktiv"

            ext_str = ", ".join(f".{e}" for e in provider.get_extensions())

            row = self.table.rowCount()
            self.table.insertRow(row)

            item_name = QTableWidgetItem(name)
            item_name.setData(Qt.ItemDataRole.UserRole, (provider, plugin_info))
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, QTableWidgetItem(p_type))
            self.table.setItem(row, 2, QTableWidgetItem(version))
            self.table.setItem(row, 3, QTableWidgetItem(ext_str))
            self.table.setItem(row, 4, QTableWidgetItem(status))

        # 2. Fehlerhafte Plugins anzeigen
        failed = self.plugin_manager.get_failed_plugins()
        for path_str, err in failed.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(Path(path_str).name)
            item_name.setData(Qt.ItemDataRole.UserRole, (None, path_str, err))
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, QTableWidgetItem("Fehlerhaft"))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("Fehler"))

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.details_text.clear()
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        if len(data) == 2:
            provider, plugin_info = data
            name = provider.get_name()
            exts = ", ".join(f".{e}" for e in provider.get_extensions())
            kw_count = len(provider.get_keywords())
            bi_count = len(provider.get_builtins())
            snip_count = len(provider.get_snippets())
            run_cmd_list = provider.get_run_command("beispiel.ext")
            run_cmd = " ".join(str(part) for part in run_cmd_list) if run_cmd_list else "-"
            comment = provider.get_comment_style()
            comment_single = comment[0] if (comment and len(comment) > 0 and comment[0]) else "-"
            comment_multi = (
                f"{comment[1][0]} ... {comment[1][1]}"
                if (comment and len(comment) > 1 and comment[1] and len(comment[1]) >= 2)
                else "Keine"
            )

            lines = [
                f"<b>Sprache:</b> {name}",
                f"<b>Dateiendungen:</b> {exts}",
                f"<b>Keywords:</b> {kw_count} | <b>Built-ins:</b> {bi_count} | <b>Snippets:</b> {snip_count}",
                f"<b>Ausführen-Befehl:</b> <code>{run_cmd}</code>",
                f"<b>Kommentar-Zeichen:</b> <code>{comment_single}</code> (Mehrzeilig: <code>{comment_multi}</code>)",
            ]
            if plugin_info:
                if plugin_info.description:
                    lines.append(f"<b>Beschreibung:</b> {plugin_info.description}")
                if plugin_info.author:
                    lines.append(f"<b>Autor:</b> {plugin_info.author}")
                if plugin_info.file_path:
                    lines.append(f"<b>Dateipfad:</b> {plugin_info.file_path}")
            else:
                lines.append("<i>Eingebauter Standard-Sprachprovider von CodeBox.</i>")

            self.details_text.setHtml("<br>".join(lines))

        elif len(data) == 3:
            _, path_str, err = data
            self.details_text.setHtml(
                f"<b style='color: red;'>Fehler beim Laden des Plugins:</b><br>"
                f"<b>Datei:</b> {path_str}<br><br>"
                f"<b>Fehlermeldung:</b><br><pre>{err}</pre>"
            )

    def _open_plugin_folder(self):
        target_dir = self.plugin_manager.get_primary_plugin_dir()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(str(target_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target_dir)])
            else:
                subprocess.Popen(["xdg-open", str(target_dir)])
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", f"Konnte Ordner nicht öffnen:\n{exc}")

    def _reload_plugins(self):
        try:
            loaded = self.plugin_manager.discover_and_load_all()
            self.refresh_list()
            QMessageBox.information(
                self, "Erfolg", f"Plugins neu geladen. {len(loaded)} Plugin(s) aktiv."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Neuladen:\n{exc}")

    def _create_plugin_template(self):
        name, ok = QInputDialog.getText(self, "Neues Sprach-Plugin", "Name der Sprache (z.B. Lua, Ruby, Zig):")
        if not ok or not name.strip():
            return
        name = name.strip()

        ext, ok = QInputDialog.getText(
            self, "Dateiendungen", f"Dateiendungen für {name} kommagetrennt (z.B. {name.lower()}, {name.lower()}s):"
        )
        if not ok:
            return
        if not ext.strip():
            extensions = [name.lower()]
        else:
            extensions = [e.strip().lstrip(".") for e in ext.split(",") if e.strip()]
        if not extensions:
            extensions = [name.lower()]

        try:
            primary_dir = self.plugin_manager.get_primary_plugin_dir()
            path = self.plugin_manager.create_declarative_template(primary_dir, name, extensions)
            self.plugin_manager.load_plugin(path)
            self.refresh_list()
            QMessageBox.information(
                self, "Plugin erstellt", f"Plugin-Vorlage wurde erstellt und geladen:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Erstellen:\n{exc}")
