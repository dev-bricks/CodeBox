#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tastenkürzel-Übersicht für CodeBox.
Zeigt alle verfügbaren Hotkeys und Shortcuts in einem übersichtlichen Dialog an.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
)


SHORTCUTS_DATA = [
    # Datei
    ("Datei", "Neu", "Ctrl+N", "Erstellt eine neue leere Datei"),
    ("Datei", "Öffnen...", "Ctrl+O", "Öffnet eine bestehende Datei"),
    ("Datei", "Speichern", "Ctrl+S", "Speichert die aktuelle Datei"),
    ("Datei", "Beenden", "Ctrl+Q", "Schließt die CodeBox-Anwendung"),

    # Bearbeiten
    ("Bearbeiten", "Rückgängig", "Ctrl+Z", "Macht die letzte Änderung rückgängig"),
    ("Bearbeiten", "Wiederherstellen", "Ctrl+Y", "Stellt die letzte rückgängig gemachte Änderung wieder her"),
    ("Bearbeiten", "Suchen", "Ctrl+F", "Öffnet den Suchen-Dialog"),
    ("Bearbeiten", "Gehe zu Zeile", "Ctrl+G", "Springt zu einer bestimmten Zeilennummer"),
    ("Bearbeiten", "Einstellungen", "Ctrl+,", "Öffnet die Programmeinstellungen"),
    ("Bearbeiten", "Plugins & Sprachen", "Ctrl+Shift+P", "Öffnet die Plugin- und Sprachverwaltung"),

    # Ausführen
    ("Ausführen", "Ausführen", "F5", "Führt das aktuelle Skript oder Programm aus"),
    ("Ausführen", "Stoppen", "Shift+F5", "Bricht den laufenden Ausführungsprozess ab"),

    # Ansicht
    ("Ansicht", "Projektbaum umschalten", "Ctrl+B", "Blendet den Datei- und Projektbaum ein/aus"),
    ("Ansicht", "Terminal umschalten", "Ctrl+`", "Blendet das integrierte Terminal ein/aus"),

    # Editor & Navigation
    ("Editor", "Auto-Vervollständigung", "Ctrl+Space", "Öffnet das Autocomplete-Popup"),
    ("Editor", "Vorschlag übernehmen", "Tab / Enter", "Fügt den ausgewählten Autocomplete-Vorschlag ein"),
    ("Editor", "Einrücken", "Tab", "Rückt die aktuelle Zeile oder Auswahl ein"),
    ("Editor", "Ausrücken", "Shift+Tab", "Rückt die aktuelle Zeile oder Auswahl aus"),
    ("Editor", "Schrift vergrößern", "Ctrl+Mausrad hoch", "Erhöht die Schriftgröße im Editor"),
    ("Editor", "Schrift verkleinern", "Ctrl+Mausrad runter", "Verringert die Schriftgröße im Editor"),

    # Hilfe
    ("Hilfe", "Tastenkürzel-Übersicht", "F1", "Öffnet diese Tastenkürzel-Referenz"),
]


class ShortcutsDialog(QDialog):
    """Dialog zur Anzeige aller Tastenkombinationen mit Suchfilter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CodeBox Tastenkürzel-Übersicht")
        self.resize(650, 480)
        self.setup_ui()
        self.populate_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header / Suchfeld
        top_layout = QHBoxLayout()
        label = QLabel("<b>Tastenkombinationen</b>")
        top_layout.addWidget(label)
        top_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("shortcuts_search_input")
        self.search_input.setPlaceholderText("Filtern nach Funktion oder Tastenkürzel...")
        self.search_input.setToolTip("Suchbegriff eingeben, um Tastenkürzel oder Aktionen zu filtern")
        self.search_input.setAccessibleName("Tastenkürzel filtern")
        self.search_input.setAccessibleDescription("Filtert die Liste der Tastenkürzel in Echtzeit nach Kategorie, Aktion, Tastenkürzel oder Beschreibung")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_table)
        top_layout.addWidget(self.search_input)
        layout.addLayout(top_layout)

        # Tabelle
        self.table = QTableWidget()
        self.table.setObjectName("shortcuts_table")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Kategorie", "Aktion", "Tastenkürzel", "Beschreibung"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName("Tastenkürzel-Tabelle")
        self.table.setAccessibleDescription("Tabelle aller verfügbaren Tastenkombinationen mit Kategorie, Aktion, Tastenkürzel und Beschreibung")
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton("Schließen")
        self.btn_close.setObjectName("shortcuts_close_button")
        self.btn_close.setToolTip("Schließt die Tastenkürzel-Übersicht")
        self.btn_close.setAccessibleName("Tastenkürzel-Übersicht schließen")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def populate_table(self):
        self.table.setRowCount(0)
        for cat, action, shortcut, desc in SHORTCUTS_DATA:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cat))
            self.table.setItem(row, 1, QTableWidgetItem(action))
            self.table.setItem(row, 2, QTableWidgetItem(shortcut))
            self.table.setItem(row, 3, QTableWidgetItem(desc))

    def filter_table(self, text: str):
        query = text.lower().strip()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
