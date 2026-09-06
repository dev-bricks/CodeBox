#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrierter Regex-Such- und Ersetzen-Dialog mit Voransicht für CodeBox.
Ermöglicht Suche, Regex-Ausdrücke, Voransicht von Ersetzungen und Navigation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.editor import CodeEditor
    from ui.main_window import MainWindow


class FindReplaceDialog(QDialog):
    """Integrierter Such- und Ersetzen-Dialog mit Regex- und Vorschau-Unterstützung."""

    searchRequested = Signal(str, bool, bool, bool)

    def __init__(self, main_window: "MainWindow", initial_mode: str = "find", parent: Optional[QWidget] = None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle("Suchen und Ersetzen")
        self.setMinimumWidth(560)
        self.resize(620, 460)
        self.setModal(False)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(120)
        self._debounce_timer.timeout.connect(self._update_live_results)

        self._setup_ui()
        self.set_mode(initial_mode)

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # Eingabefelder
        grid = QGridLayout()
        grid.setSpacing(6)

        # Suchen
        self.search_label = QLabel("Suchen nach:")
        self.search_input = QLineEdit()
        self.search_input.setObjectName("find_search_input")
        self.search_input.setPlaceholderText("Suchbegriff oder Regex...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setToolTip("Suchbegriff oder regulären Ausdruck eingeben (Enter für nächsten Treffer)")
        self.search_input.setAccessibleName("Suchtext")
        self.search_input.setAccessibleDescription("Eingabefeld für den zu suchenden Text oder regulären Ausdruck")
        self.search_input.textChanged.connect(self._schedule_update)
        self.search_input.returnPressed.connect(self.find_next)

        self.btn_prev = QPushButton("↑ Vorheriger")
        self.btn_prev.setObjectName("find_prev_btn")
        self.btn_prev.setToolTip("Vorherigen Treffer anspringen (Shift+Enter / Shift+F3)")
        self.btn_prev.setAccessibleName("Vorheriger Treffer")
        self.btn_prev.clicked.connect(self.find_prev)

        self.btn_next = QPushButton("↓ Nächster")
        self.btn_next.setObjectName("find_next_btn")
        self.btn_next.setToolTip("Nächsten Treffer anspringen (Enter / F3)")
        self.btn_next.setAccessibleName("Nächster Treffer")
        self.btn_next.clicked.connect(self.find_next)

        grid.addWidget(self.search_label, 0, 0)
        grid.addWidget(self.search_input, 0, 1)
        grid.addWidget(self.btn_prev, 0, 2)
        grid.addWidget(self.btn_next, 0, 3)

        # Ersetzen
        self.replace_label = QLabel("Ersetzen durch:")
        self.replace_input = QLineEdit()
        self.replace_input.setObjectName("find_replace_input")
        self.replace_input.setPlaceholderText("Ersetzungstext (unterstützt Regex-Gruppen \\1, \\2)...")
        self.replace_input.setClearButtonEnabled(True)
        self.replace_input.setToolTip("Ersetzungstext eingeben (bei Regex: \\1, \\2 für Capture-Groups)")
        self.replace_input.setAccessibleName("Ersetzungstext")
        self.replace_input.setAccessibleDescription("Eingabefeld für den Text, durch den Treffer ersetzt werden")
        self.replace_input.textChanged.connect(self._schedule_update)
        self.replace_input.returnPressed.connect(self.replace_current)

        self.btn_replace = QPushButton("Ersetzen")
        self.btn_replace.setObjectName("replace_btn")
        self.btn_replace.setToolTip("Aktuellen Treffer ersetzen (Alt+R)")
        self.btn_replace.setAccessibleName("Treffer ersetzen")
        self.btn_replace.clicked.connect(self.replace_current)

        self.btn_replace_all = QPushButton("Alle ersetzen")
        self.btn_replace_all.setObjectName("replace_all_btn")
        self.btn_replace_all.setToolTip("Alle Treffer im Dokument auf einmal ersetzen (Alt+A)")
        self.btn_replace_all.setAccessibleName("Alle Treffer ersetzen")
        self.btn_replace_all.clicked.connect(self.replace_all)

        grid.addWidget(self.replace_label, 1, 0)
        grid.addWidget(self.replace_input, 1, 1)
        grid.addWidget(self.btn_replace, 1, 2)
        grid.addWidget(self.btn_replace_all, 1, 3)

        root_layout.addLayout(grid)

        # Optionen
        opt_layout = QHBoxLayout()
        opt_layout.setSpacing(14)

        self.cb_case = QCheckBox("Groß-/&Kleinschreibung")
        self.cb_case.setObjectName("find_case_checkbox")
        self.cb_case.setToolTip("Groß- und Kleinschreibung exakt beachten")
        self.cb_case.setAccessibleName("Groß- und Kleinschreibung beachten")
        self.cb_case.stateChanged.connect(self._schedule_update)
        opt_layout.addWidget(self.cb_case)

        self.cb_words = QCheckBox("Ganzes &Wort")
        self.cb_words.setObjectName("find_words_checkbox")
        self.cb_words.setToolTip("Nur ganze Wörter suchen (Wortgrenzen beachten)")
        self.cb_words.setAccessibleName("Nur ganze Wörter suchen")
        self.cb_words.stateChanged.connect(self._schedule_update)
        opt_layout.addWidget(self.cb_words)

        self.cb_regex = QCheckBox("Re&gex")
        self.cb_regex.setObjectName("find_regex_checkbox")
        self.cb_regex.setToolTip("Suchbegriff als regulären Python-Ausdruck interpretieren")
        self.cb_regex.setAccessibleName("Regulären Ausdruck verwenden")
        self.cb_regex.stateChanged.connect(self._schedule_update)
        opt_layout.addWidget(self.cb_regex)

        opt_layout.addStretch()
        root_layout.addLayout(opt_layout)

        # Status & Trefferanzeige
        status_bar_layout = QHBoxLayout()
        self.status_label = QLabel("Bereit")
        self.status_label.setObjectName("find_status_label")
        self.status_label.setAccessibleName("Suchstatus")
        status_bar_layout.addWidget(self.status_label)
        status_bar_layout.addStretch()

        self.btn_toggle_preview = QPushButton("Voransicht")
        self.btn_toggle_preview.setObjectName("toggle_preview_btn")
        self.btn_toggle_preview.setCheckable(True)
        self.btn_toggle_preview.setChecked(True)
        self.btn_toggle_preview.setToolTip("Voransicht der Treffer und Ersetzungen ein-/ausblenden")
        self.btn_toggle_preview.setAccessibleName("Voransicht umschalten")
        self.btn_toggle_preview.toggled.connect(self._on_toggle_preview)
        status_bar_layout.addWidget(self.btn_toggle_preview)
        root_layout.addLayout(status_bar_layout)

        # Voransicht-Bereich
        self.preview_group = QGroupBox("Voransicht der Ersetzungen")
        self.preview_group.setObjectName("find_preview_group")
        preview_layout = QVBoxLayout(self.preview_group)
        preview_layout.setContentsMargins(6, 6, 6, 6)

        self.preview_table = QTableWidget()
        self.preview_table.setObjectName("find_preview_table")
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["Zeile", "Spalte", "Original", "Ersetzung"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAccessibleName("Voransichtstabelle")
        self.preview_table.setAccessibleDescription("Tabelle der gefundenen Treffer mit Zeile, Spalte und Vorschau der Ersetzung")
        self.preview_table.itemClicked.connect(self._on_table_item_activated)
        self.preview_table.itemDoubleClicked.connect(self._on_table_item_activated)
        preview_layout.addWidget(self.preview_table)

        root_layout.addWidget(self.preview_group, 1)

        # Untere Leiste mit Schließen
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_close = QPushButton("Schließen")
        self.btn_close.setObjectName("find_close_btn")
        self.btn_close.setToolTip("Suchdialog schließen (Esc)")
        self.btn_close.setAccessibleName("Dialog schließen")
        self.btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_close)
        root_layout.addLayout(bottom_layout)

    def _get_current_editor(self) -> Optional["CodeEditor"]:
        if not self.main_window or not hasattr(self.main_window, "tab_widget"):
            return None
        tab = self.main_window.tab_widget.current_tab()
        return tab.editor if tab else None

    def set_mode(self, mode: str):
        """Setzt den Modus auf 'find' oder 'replace' und fokussiert das entsprechende Feld."""
        editor = self._get_current_editor()
        if editor and editor.textCursor().hasSelection():
            selected = editor.textCursor().selectedText().replace("\u2029", "\n")
            if "\n" not in selected and len(selected) <= 100:
                self.search_input.setText(selected)

        if mode == "replace":
            self.replace_input.setFocus()
            self.replace_input.selectAll()
        else:
            self.search_input.setFocus()
            self.search_input.selectAll()
        self._update_live_results()

    def _schedule_update(self):
        self._debounce_timer.start()

    def _on_toggle_preview(self, checked: bool):
        self.preview_group.setVisible(checked)
        if checked:
            self._update_live_results()

    def _update_live_results(self):
        editor = self._get_current_editor()
        if not editor:
            self.status_label.setText("Kein aktiver Editor vorhanden.")
            self.preview_table.setRowCount(0)
            return

        pattern = self.search_input.text()
        replacement = self.replace_input.text()
        case_sensitive = self.cb_case.isChecked()
        whole_word = self.cb_words.isChecked()
        is_regex = self.cb_regex.isChecked()

        if not pattern:
            editor.clearSearchHighlight()
            self.status_label.setText("Bereit")
            self.status_label.setStyleSheet("")
            self.preview_table.setRowCount(0)
            return

        # Syntax-Check & Preview
        previews, total, err = editor.get_replace_preview(
            pattern=pattern,
            replacement=replacement,
            case_sensitive=case_sensitive,
            is_regex=is_regex,
            whole_word=whole_word,
            max_items=100,
        )

        if err:
            editor.clearSearchHighlight()
            self.status_label.setText(f"Regex-Fehler: {err}")
            self.status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            self.preview_table.setRowCount(0)
            return

        self.status_label.setStyleSheet("")
        editor.highlightSearchResults(
            pattern=pattern,
            case_sensitive=case_sensitive,
            is_regex=is_regex,
            whole_word=whole_word,
        )

        if total == 0:
            self.status_label.setText("Keine Treffer gefunden.")
        elif total == 1:
            self.status_label.setText("1 Treffer gefunden.")
        else:
            shown = len(previews)
            if shown < total:
                self.status_label.setText(f"{total} Treffer gefunden ({shown} in Voransicht).")
            else:
                self.status_label.setText(f"{total} Treffer gefunden.")

        # Tabelle befüllen
        self.preview_table.setRowCount(0)
        for row_idx, item in enumerate(previews):
            self.preview_table.insertRow(row_idx)
            item_line = QTableWidgetItem(str(item["line"]))
            item_line.setData(Qt.ItemDataRole.UserRole, (item["start"], item["end"]))
            item_col = QTableWidgetItem(str(item["col"]))
            item_orig = QTableWidgetItem(item["original"])
            item_rep = QTableWidgetItem(item["replacement"])

            self.preview_table.setItem(row_idx, 0, item_line)
            self.preview_table.setItem(row_idx, 1, item_col)
            self.preview_table.setItem(row_idx, 2, item_orig)
            self.preview_table.setItem(row_idx, 3, item_rep)

    def _on_table_item_activated(self, table_item: QTableWidgetItem):
        row = table_item.row()
        item_line = self.preview_table.item(row, 0)
        if not item_line:
            return
        span = item_line.data(Qt.ItemDataRole.UserRole)
        if not span:
            return
        start, end = span
        editor = self._get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
            editor.setTextCursor(cursor)
            editor.centerCursor()
            editor.setFocus()

    def find_next(self):
        """Springt zum nächsten Treffer."""
        editor = self._get_current_editor()
        if not editor:
            return
        pattern = self.search_input.text()
        if not pattern:
            return
        found = editor.find_next(
            pattern=pattern,
            case_sensitive=self.cb_case.isChecked(),
            is_regex=self.cb_regex.isChecked(),
            whole_word=self.cb_words.isChecked(),
            forward=True,
        )
        if not found:
            self.status_label.setText("Kein weiterer Treffer gefunden.")

    def find_prev(self):
        """Springt zum vorherigen Treffer."""
        editor = self._get_current_editor()
        if not editor:
            return
        pattern = self.search_input.text()
        if not pattern:
            return
        found = editor.find_next(
            pattern=pattern,
            case_sensitive=self.cb_case.isChecked(),
            is_regex=self.cb_regex.isChecked(),
            whole_word=self.cb_words.isChecked(),
            forward=False,
        )
        if not found:
            self.status_label.setText("Kein vorheriger Treffer gefunden.")

    def replace_current(self):
        """Ersetzt den aktuellen Treffer."""
        editor = self._get_current_editor()
        if not editor:
            return
        pattern = self.search_input.text()
        replacement = self.replace_input.text()
        if not pattern:
            return
        editor.replace_current(
            pattern=pattern,
            replacement=replacement,
            case_sensitive=self.cb_case.isChecked(),
            is_regex=self.cb_regex.isChecked(),
            whole_word=self.cb_words.isChecked(),
        )
        self._update_live_results()

    def replace_all(self):
        """Ersetzt alle Treffer im Dokument."""
        editor = self._get_current_editor()
        if not editor:
            return
        pattern = self.search_input.text()
        replacement = self.replace_input.text()
        if not pattern:
            return
        count = editor.replace_all(
            pattern=pattern,
            replacement=replacement,
            case_sensitive=self.cb_case.isChecked(),
            is_regex=self.cb_regex.isChecked(),
            whole_word=self.cb_words.isChecked(),
        )
        self.status_label.setText(f"{count} Vorkommen ersetzt.")
        if hasattr(self.main_window, "status_bar"):
            self.main_window.status_bar.showMessage(f"{count} Vorkommen ersetzt.", 4000)
        self._update_live_results()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() == Qt.Key.Key_F3:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_prev()
            else:
                self.find_next()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        editor = self._get_current_editor()
        if editor:
            editor.clearSearchHighlight()
        event.accept()
