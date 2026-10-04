#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SnippetsDialog - Verwaltung und Schnellauswahl von Code-Snippets in CodeBox.
Ermöglicht das Durchsuchen, Vorschau, Einfügen und Verwalten benutzerdefinierter Snippets.
"""

from __future__ import annotations

from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QSplitter,
    QPlainTextEdit,
    QMessageBox,
    QFormLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.snippets import Snippet, SnippetManager


class SnippetEditDialog(QDialog):
    """Subdialog zum Erstellen oder Bearbeiten eines benutzerdefinierten Snippets."""

    def __init__(self, snippet: Optional[Snippet] = None, current_language: str = "python", parent=None):
        super().__init__(parent)
        self.is_edit = snippet is not None
        self.setWindowTitle("Snippet bearbeiten" if self.is_edit else "Neues Snippet erstellen")
        self.resize(520, 420)
        self._setup_ui(snippet, current_language)

    def _setup_ui(self, snippet: Optional[Snippet], current_language: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.trigger_input = QLineEdit()
        self.trigger_input.setPlaceholderText("z. B. def, fn, clg, myhook")
        self.trigger_input.setAccessibleName("Snippet Trigger-Kürzel")
        form.addRow("Trigger (Kürzel):", self.trigger_input)

        self.lang_combo = QComboBox()
        langs = [
            ("all", "Allgemein (alle Sprachen)"),
            ("python", "Python"),
            ("javascript", "JavaScript"),
            ("typescript", "TypeScript"),
            ("cpp", "C / C++"),
            ("rust", "Rust"),
            ("go", "Go"),
            ("java", "Java"),
            ("html", "HTML"),
            ("markdown", "Markdown"),
        ]
        for val, label in langs:
            self.lang_combo.addItem(label, val)
        form.addRow("Sprache:", self.lang_combo)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Kurze Beschreibung der Vorlage")
        self.desc_input.setAccessibleName("Snippet Beschreibung")
        form.addRow("Beschreibung:", self.desc_input)

        layout.addLayout(form)

        lbl_body = QLabel("Code-Vorlage (Unterstützt $1, ${1:default} und $0 für Tab-Stops):")
        layout.addWidget(lbl_body)

        self.body_edit = QPlainTextEdit()
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.body_edit.setFont(font)
        self.body_edit.setPlaceholderText("def ${1:name}(${2:args}):\n    ${0:pass}")
        self.body_edit.setAccessibleName("Snippet Code-Vorlage")
        layout.addWidget(self.body_edit, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Speichern")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Vorbelegung
        if snippet:
            self.trigger_input.setText(snippet.trigger)
            self.desc_input.setText(snippet.description)
            self.body_edit.setPlainText(snippet.body)
            idx = self.lang_combo.findData(snippet.language.lower())
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)
        else:
            idx = self.lang_combo.findData(current_language.lower())
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)

    def _on_save_clicked(self):
        trigger = self.trigger_input.text().strip()
        body = self.body_edit.toPlainText().strip()
        if not trigger:
            QMessageBox.warning(self, "Ungültige Eingabe", "Bitte geben Sie ein Trigger-Kürzel ein.")
            self.trigger_input.setFocus()
            return
        if not body:
            QMessageBox.warning(self, "Ungültige Eingabe", "Bitte geben Sie einen Code-Körper ein.")
            self.body_edit.setFocus()
            return
        self.accept()

    def get_snippet(self) -> Snippet:
        return Snippet(
            trigger=self.trigger_input.text().strip(),
            description=self.desc_input.text().strip(),
            body=self.body_edit.toPlainText(),
            language=self.lang_combo.currentData(),
            is_custom=True,
        )


class SnippetsDialog(QDialog):
    """Hauptdialog zur Suche, Vorschau und Verwaltung von Code-Snippets."""

    snippetSelected = Signal(object)  # Emits Snippet instance

    def __init__(self, manager: Optional[SnippetManager] = None, current_language: str = "", parent=None):
        super().__init__(parent)
        self.manager = manager or SnippetManager.get_instance()
        self.current_language = current_language.lower()
        self._displayed_snippets: List[Snippet] = []

        self.setWindowTitle("CodeBox - Snippet-Manager")
        self.resize(780, 520)
        self.setMinimumSize(600, 380)
        self.setObjectName("snippets_dialog")
        self.setAccessibleName("Snippet-Manager")
        self.setAccessibleDescription("Auswahl, Vorschau und Verwaltung von Code-Vorlagen und Tab-Trigger-Snippets")

        self._setup_ui()
        self._populate_snippets()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Obere Filterleiste
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        lbl_search = QLabel("Suche:")
        filter_bar.addWidget(lbl_search)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Snippets durchsuchen (Trigger, Beschreibung, Code)...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setAccessibleName("Snippet-Suchfeld")
        self.search_edit.textChanged.connect(self._filter_snippets)
        filter_bar.addWidget(self.search_edit, 1)

        lbl_lang = QLabel("Sprache:")
        filter_bar.addWidget(lbl_lang)

        self.lang_filter = QComboBox()
        self.lang_filter.setAccessibleName("Sprachfilter")
        langs = [
            ("", "Alle Sprachen"),
            ("python", "Python"),
            ("javascript", "JavaScript"),
            ("typescript", "TypeScript"),
            ("cpp", "C / C++"),
            ("rust", "Rust"),
            ("go", "Go"),
            ("java", "Java"),
            ("html", "HTML"),
            ("markdown", "Markdown"),
            ("all", "Allgemein"),
        ]
        for val, label in langs:
            self.lang_filter.addItem(label, val)
        self.lang_filter.currentIndexChanged.connect(self._filter_snippets)
        filter_bar.addWidget(self.lang_filter)

        root_layout.addLayout(filter_bar)

        # Zentraler Splitter: Links Tabelle, Rechts Vorschau
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Trigger", "Sprache", "Beschreibung", "Herkunft"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        splitter.addWidget(self.table)

        # Vorschau-Widget
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(4, 0, 0, 0)
        preview_layout.setSpacing(4)

        self.preview_header = QLabel("Code-Vorschau:")
        self.preview_header.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(self.preview_header)

        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview_edit.setFont(font)
        self.preview_edit.setAccessibleName("Snippet-Code-Vorschau")
        preview_layout.addWidget(self.preview_edit, 1)

        splitter.addWidget(preview_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        # Untere Aktionsleiste
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.btn_new = QPushButton("Neues Snippet...")
        self.btn_new.setToolTip("Erstellt ein eigenes benutzerdefiniertes Code-Snippet")
        self.btn_new.setAccessibleName("Neues Snippet erstellen")
        self.btn_new.clicked.connect(self._on_new_snippet)
        bottom_bar.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Bearbeiten...")
        self.btn_edit.setEnabled(False)
        self.btn_edit.setToolTip("Bearbeitet das ausgewählte benutzerdefinierte Snippet")
        self.btn_edit.setAccessibleName("Ausgewähltes Snippet bearbeiten")
        self.btn_edit.clicked.connect(self._on_edit_snippet)
        bottom_bar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setToolTip("Löscht das ausgewählte benutzerdefinierte Snippet")
        self.btn_delete.setAccessibleName("Ausgewähltes Snippet löschen")
        self.btn_delete.clicked.connect(self._on_delete_snippet)
        bottom_bar.addWidget(self.btn_delete)

        bottom_bar.addStretch()

        self.btn_insert = QPushButton("Snippet einfügen (Enter)")
        self.btn_insert.setDefault(True)
        self.btn_insert.setEnabled(False)
        self.btn_insert.setToolTip("Fügt das ausgewählte Snippet in den Editor ein")
        self.btn_insert.setAccessibleName("Snippet in Dokument einfügen")
        self.btn_insert.clicked.connect(self._on_insert_clicked)
        bottom_bar.addWidget(self.btn_insert)

        self.btn_close = QPushButton("Schließen")
        self.btn_close.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_close)

        root_layout.addLayout(bottom_bar)

        # Initiale Vorbelegung des Sprachfilters
        if self.current_language:
            idx = self.lang_filter.findData(self.current_language)
            if idx >= 0:
                self.lang_filter.setCurrentIndex(idx)

    def _populate_snippets(self):
        """Lädt alle Snippets und filtert sie gemäß den aktuellen Eingaben."""
        self._filter_snippets()

    def _filter_snippets(self):
        """Aktualisiert die Tabellenansicht basierend auf Suche und Sprache."""
        query = self.search_edit.text().strip().lower()
        selected_lang = self.lang_filter.currentData()

        all_snips = self.manager.all_snippets()
        filtered: List[Snippet] = []

        for s in all_snips:
            if selected_lang and s.language not in ("", "all") and s.language != selected_lang:
                continue
            if query:
                match_trigger = query in s.trigger.lower()
                match_desc = query in s.description.lower()
                match_body = query in s.body.lower()
                if not (match_trigger or match_desc or match_body):
                    continue
            filtered.append(s)

        filtered.sort(key=lambda s: (0 if s.is_custom else 1, s.language, s.trigger))
        self._displayed_snippets = filtered

        self.table.setRowCount(len(filtered))
        for row, s in enumerate(filtered):
            item_trigger = QTableWidgetItem(s.trigger)
            item_lang = QTableWidgetItem(s.language.upper())
            item_desc = QTableWidgetItem(s.description)
            item_origin = QTableWidgetItem("Eigene" if s.is_custom else "Standard")

            if s.is_custom:
                item_origin.setForeground(Qt.GlobalColor.darkGreen)

            self.table.setItem(row, 0, item_trigger)
            self.table.setItem(row, 1, item_lang)
            self.table.setItem(row, 2, item_desc)
            self.table.setItem(row, 3, item_origin)

        if filtered:
            self.table.setCurrentCell(0, 0)
            self._on_selection_changed()
        else:
            self._update_preview(None)

    def _get_selected_snippet(self) -> Optional[Snippet]:
        row = self.table.currentRow()
        if 0 <= row < len(self._displayed_snippets):
            return self._displayed_snippets[row]
        return None

    def _on_selection_changed(self):
        snippet = self._get_selected_snippet()
        self._update_preview(snippet)
        has_sel = snippet is not None
        self.btn_insert.setEnabled(has_sel)
        self.btn_edit.setEnabled(has_sel and snippet.is_custom)
        self.btn_delete.setEnabled(has_sel and snippet.is_custom)

    def _update_preview(self, snippet: Optional[Snippet]):
        if snippet:
            self.preview_header.setText(f"Vorschau: {snippet.trigger} ({snippet.language.upper()})")
            self.preview_edit.setPlainText(snippet.body)
        else:
            self.preview_header.setText("Code-Vorschau:")
            self.preview_edit.clear()

    def _on_table_double_clicked(self, item: QTableWidgetItem):
        self._on_insert_clicked()

    def _on_insert_clicked(self):
        snippet = self._get_selected_snippet()
        if snippet:
            self.snippetSelected.emit(snippet)
            self.accept()

    def _on_new_snippet(self):
        lang = self.lang_filter.currentData() or self.current_language or "python"
        dialog = SnippetEditDialog(current_language=lang, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_s = dialog.get_snippet()
            self.manager.add_custom_snippet(new_s)
            self._filter_snippets()

    def _on_edit_snippet(self):
        snippet = self._get_selected_snippet()
        if not snippet or not snippet.is_custom:
            return
        dialog = SnippetEditDialog(snippet=snippet, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_snippet()
            self.manager.add_custom_snippet(updated)
            self._filter_snippets()

    def _on_delete_snippet(self):
        snippet = self._get_selected_snippet()
        if not snippet or not snippet.is_custom:
            return
        res = QMessageBox.question(
            self,
            "Snippet löschen",
            f"Möchten Sie das Snippet '{snippet.trigger}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self.manager.remove_custom_snippet(snippet.trigger, snippet.language)
            self._filter_snippets()
