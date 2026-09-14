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
    ("Datei", "Ordner öffnen...", "Ctrl+Shift+O", "Öffnet einen Projektordner als einzelnen Arbeitsbereich"),
    ("Datei", "Ordner zum Arbeitsbereich hinzufügen...", "", "Fügt einen weiteren Projektordner zum Arbeitsbereich hinzu"),
    ("Datei", "Arbeitsbereich öffnen...", "", "Lädt einen .codebox-workspace Arbeitsbereich"),
    ("Datei", "Arbeitsbereich speichern unter...", "", "Speichert den aktuellen Arbeitsbereich in eine Datei"),
    ("Datei", "Arbeitsbereich schließen", "", "Schließt alle Ordner des aktuellen Arbeitsbereichs"),
    ("Datei", "Schnell öffnen (Quick Open)", "Ctrl+P", "Öffnet die Schnellauswahl für Projektdateien"),
    ("Datei", "Speichern", "Ctrl+S", "Speichert die aktuelle Datei"),
    ("Datei", "Beenden", "Ctrl+Q", "Schließt die CodeBox-Anwendung"),

    # Bearbeiten
    ("Bearbeiten", "Rückgängig", "Ctrl+Z", "Macht die letzte Änderung rückgängig"),
    ("Bearbeiten", "Wiederherstellen", "Ctrl+Y", "Stellt die letzte rückgängig gemachte Änderung wieder her"),
    ("Bearbeiten", "Suchen", "Ctrl+F", "Öffnet den Suchen- und Ersetzen-Dialog"),
    ("Bearbeiten", "Ersetzen", "Ctrl+H", "Öffnet den Suchen- und Ersetzen-Dialog im Ersetzen-Modus"),
    ("Bearbeiten", "In Dateien suchen", "Ctrl+Shift+F", "Projektweite Textsuche über alle Workspace-Ordner"),
    ("Bearbeiten", "Weitersuchen", "F3", "Springt zum nächsten Suchtreffer"),
    ("Bearbeiten", "Rückwärts suchen", "Shift+F3", "Springt zum vorherigen Suchtreffer"),
    ("Bearbeiten", "Treffer ersetzen (Dialog)", "Alt+R", "Ersetzt das aktuell ausgewählte Vorkommen"),
    ("Bearbeiten", "Alle ersetzen (Dialog)", "Alt+A", "Ersetzt alle Vorkommen im gesamten Dokument"),
    ("Bearbeiten", "Vorheriger Treffer (Suchfeld)", "Shift+Enter", "Springt aus dem Suchfeld zum vorherigen Treffer"),
    ("Bearbeiten", "Gehe zu Zeile", "Ctrl+G", "Springt zu einer bestimmten Zeilennummer"),
    ("Bearbeiten", "Zur Definition springen", "F12", "Springt zur Definition des aktuellen Symbols"),
    ("Bearbeiten", "Alle Referenzen suchen", "Shift+F12", "Sucht alle Vorkommen und Referenzen des aktuellen Symbols"),
    ("Bearbeiten", "Cursor oberhalb hinzufügen", "Ctrl+Alt+Up", "Fügt einen weiteren Cursor in der Zeile darüber ein (Spaltenauswahl)"),
    ("Bearbeiten", "Cursor unterhalb hinzufügen", "Ctrl+Alt+Down", "Fügt einen weiteren Cursor in der Zeile darunter ein (Spaltenauswahl)"),
    ("Bearbeiten", "Alle Vorkommen markieren", "Ctrl+Shift+L", "Markiert alle Vorkommen des aktuellen Worts oder der Auswahl mit Multi-Cursorn"),
    ("Bearbeiten", "Nächstes Vorkommen hinzufügen", "Ctrl+Alt+L", "Fügt das nächste Vorkommen zur Mehrfachauswahl hinzu"),
    ("Bearbeiten", "Mehrfachcursor aufheben", "Escape", "Hebt alle zusätzlichen Cursor auf und kehrt zum Einzelcursor zurück"),
    ("Bearbeiten", "Multi-Cursor an Klickposition", "Alt+Klick", "Setzt oder entfernt einen zusätzlichen Cursor an der angeklickten Stelle"),
    ("Bearbeiten", "Einstellungen", "Ctrl+,", "Öffnet die Programmeinstellungen"),
    ("Bearbeiten", "Vim-Modus umschalten", "Ctrl+Alt+V", "Schaltet modales Editieren (Normal, Insert, Visual) ein/aus"),
    ("Bearbeiten", "Befehlspalette", "Ctrl+Shift+P", "Öffnet die interaktive Befehlspalette für alle IDE-Aktionen"),
    ("Bearbeiten", "Plugins & Sprachen", "", "Öffnet die Plugin- und Sprachverwaltung"),

    # Ausführen
    ("Ausführen", "Ausführen", "F5", "Führt das aktuelle Skript oder Programm aus"),
    ("Ausführen", "Stoppen", "Shift+F5", "Bricht den laufenden Ausführungsprozess ab"),
    ("Ausführen", "Breakpoint umschalten", "F9", "Setzt oder entfernt einen Breakpoint in der aktuellen Zeile"),
    ("Ausführen", "Alle Breakpoints löschen", "Ctrl+Shift+F9", "Löscht alle gesetzten Breakpoints im aktuellen Editor"),

    # Ansicht
    ("Ansicht", "Projektbaum umschalten", "Ctrl+B", "Blendet den Datei- und Projektbaum ein/aus"),
    ("Ansicht", "Aufgaben & TODOs umschalten", "Ctrl+Alt+T", "Blendet die Aufgaben- und TODO-Seitenleiste ein/aus"),
    ("Ansicht", "Terminal umschalten", "Ctrl+`", "Blendet das integrierte Terminal ein/aus"),
    ("Ansicht", "Git-Diff anzeigen", "Ctrl+Alt+D", "Öffnet den Git Diff-Viewer für geänderte Dateien"),
    ("Ansicht", "Git-Commit Dialog", "Ctrl+Alt+C", "Öffnet den Dialog zum Stagen und Committen von Git-Änderungen"),
    ("Ansicht", "Code-Faltung umschalten", "Ctrl+Shift+[", "Klappt die Funktion oder Klasse an der Cursorposition ein oder aus"),
    ("Ansicht", "Alle Blöcke einklappen", "Ctrl+Alt+[", "Klappt alle Funktionen und Klassen im Dokument ein"),
    ("Ansicht", "Alle Blöcke ausklappen", "Ctrl+Alt+]", "Klappt alle Funktionen und Klassen im Dokument aus"),
    ("Ansicht", "Editor nach rechts teilen", "Ctrl+\\", "Teilt den Editor in zwei nebeneinanderliegende Spalten"),
    ("Ansicht", "Editor nach unten teilen", "Ctrl+Shift+\\", "Teilt den Editor in zwei übereinanderliegende Zeilen"),
    ("Ansicht", "Editor-Teilung aufheben", "Ctrl+Alt+W", "Schließt die geteilte Ansicht und kehrt zum Einzeleditor zurück"),
    ("Ansicht", "Fokus zwischen geteilten Ansichten", "F6", "Wechselt den Tastaturfokus zwischen den geteilten Editorhälften"),
    ("Ansicht", "Tab zur anderen Ansicht verschieben", "Ctrl+Alt+M", "Verschiebt das aktuelle Dokument in die andere Editorhälfte"),

    # Editor & Navigation
    ("Editor", "Zeilenkommentar umschalten", "Ctrl+/", "Kommentiert die aktuelle Zeile oder Auswahl aus/ein"),
    ("Editor", "Zeile / Auswahl duplizieren", "Ctrl+D", "Dupliziert die aktuelle Zeile oder den ausgewählten Text"),
    ("Editor", "Zeile nach oben verschieben", "Alt+Up", "Verschiebt die aktuelle Zeile eine Zeile nach oben"),
    ("Editor", "Zeile nach unten verschieben", "Alt+Down", "Verschiebt die aktuelle Zeile eine Zeile nach unten"),
    ("Editor", "Auto-Vervollständigung", "Ctrl+Space", "Öffnet das Autocomplete-Popup"),
    ("Editor", "Vorschlag übernehmen", "Tab / Enter", "Fügt den ausgewählten Autocomplete-Vorschlag ein"),
    ("Editor", "Einrücken", "Tab", "Rückt die aktuelle Zeile oder Auswahl ein"),
    ("Editor", "Ausrücken", "Shift+Tab", "Rückt die aktuelle Zeile oder Auswahl aus"),
    ("Editor", "Schrift vergrößern", "Ctrl+Mausrad hoch", "Erhöht die Schriftgröße im Editor"),
    ("Editor", "Schrift verkleinern", "Ctrl+Mausrad runter", "Verringert die Schriftgröße im Editor"),

    # Vim-Modus
    ("Vim-Modus", "Normal-Navigation", "h / j / k / l", "Bewegt Cursor links / runter / rauf / rechts"),
    ("Vim-Modus", "Wort-Navigation", "w / b / e", "Springt zum nächsten Wortanfang, vorherigen Wortanfang oder Wortende"),
    ("Vim-Modus", "Zeilenanfang / -ende", "0 / ^ / $", "Springt zu Spalte 0, erstem Zeichen oder Zeilenende"),
    ("Vim-Modus", "Dokumentsprung", "gg / G / <N>G", "Springt zu Zeile 1, letzter Zeile oder Zeile N"),
    ("Vim-Modus", "Einfügemodus", "i / I / a / A / o / O", "Einfügen vor/nach Cursor, Zeilenanfang/-ende, neue Zeile unten/oben"),
    ("Vim-Modus", "Zeichen / Zeile löschen", "x / dd / D", "Löscht Zeichen, ganze Zeile oder bis Zeilenende"),
    ("Vim-Modus", "Wort / Zeile ändern", "cw / cc / C", "Ändert Wort, ganze Zeile oder bis Zeilenende und wechselt in Insert"),
    ("Vim-Modus", "Kopieren & Einfügen", "yy / yw / p / P", "Kopiert Zeile/Wort und fügt nach bzw. vor dem Cursor ein"),
    ("Vim-Modus", "Visuelle Markierung", "v / V", "Zeichenweise bzw. zeilenweise visuelle Textauswahl"),
    ("Vim-Modus", "Rückgängig / Wiederholen", "u / Ctrl+R", "Macht letzte Änderung rückgängig oder wiederholt sie"),

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
