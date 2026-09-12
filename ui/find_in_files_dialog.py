#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find In Files Dialog - Projektweite Textsuche & Grep-Tool für CodeBox.

Ermöglicht das schnelle Durchsuchen aller Dateien des aktuellen Arbeitsbereichs
oder einzelner Ordner nach Text und regulären Ausdrücken mit:
- Optionen: Groß-/Kleinschreibung, Ganzes Wort, Regex
- Glob-Filter für Dateitypen (Einschließen / Ausschließen)
- Asynchroner Hintergrund-Worker (QThread) ohne UI-Blockade
- Hierarchische Treffer-Liste nach Dateien mit Zeilennummern und Vorschau
- Direktsprung in den Editor mit Cursor- und Treffer-Hervorhebung
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.file_search import (
    FileSearchResult,
    SearchOptions,
    SearchWorker,
)
from ui.command_palette import FILE_ICONS

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class FindInFilesDialog(QDialog):
    """Projektweiter Suchdialog für CodeBox."""

    matchSelected = Signal(object, int, int, int)  # file_path, line, col, length

    def __init__(self, main_window: "MainWindow", parent: Optional[QWidget] = None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle("In Dateien suchen")
        self.setMinimumWidth(640)
        self.setMinimumHeight(480)
        self.resize(760, 580)
        self.setModal(False)

        self._worker: Optional[SearchWorker] = None
        self._current_results: List[FileSearchResult] = []
        self._total_matches = 0

        self._setup_ui()
        self._setup_shortcuts()
        self._update_scope_options()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # ---- Suchfelder & Filter (Grid) ----
        grid = QGridLayout()
        grid.setSpacing(6)

        # Zeile 0: Suchbegriff
        self.search_label = QLabel("&Suchen nach:")
        self.search_label.setToolTip("Suchbegriff oder regulärer Ausdruck (Alt+S)")
        self.search_input = QLineEdit()
        self.search_input.setObjectName("find_in_files_input")
        self.search_input.setPlaceholderText("Suchbegriff oder regulären Ausdruck eingeben...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName("Projektweites Suchfeld")
        self.search_input.setAccessibleDescription("Suchbegriff oder regulären Ausdruck für die projektweite Suche eingeben.")
        self.search_input.returnPressed.connect(self.start_search)
        self.search_label.setBuddy(self.search_input)
        grid.addWidget(self.search_label, 0, 0)
        grid.addWidget(self.search_input, 0, 1, 1, 3)

        # Zeile 1: Schalter (Case, Word, Regex)
        options_layout = QHBoxLayout()
        options_layout.setSpacing(12)

        self.cb_case = QCheckBox("Groß-/&Kleinschreibung (Alt+K)")
        self.cb_case.setObjectName("find_in_files_case")
        self.cb_case.setToolTip("Unterscheidet zwischen Groß- und Kleinschreibung")
        self.cb_case.setAccessibleName("Groß- und Kleinschreibung beachten")

        self.cb_word = QCheckBox("&Ganzes Wort (Alt+G)")
        self.cb_word.setObjectName("find_in_files_word")
        self.cb_word.setToolTip("Findet nur ganze Wörter mit Wortgrenzen")
        self.cb_word.setAccessibleName("Nur ganze Wörter suchen")

        self.cb_regex = QCheckBox("&Regulärer Ausdruck (Alt+R)")
        self.cb_regex.setObjectName("find_in_files_regex")
        self.cb_regex.setToolTip("Interpretiert den Suchbegriff als regulären Ausdruck")
        self.cb_regex.setAccessibleName("Regulären Ausdruck verwenden")

        options_layout.addWidget(self.cb_case)
        options_layout.addWidget(self.cb_word)
        options_layout.addWidget(self.cb_regex)
        options_layout.addStretch()

        grid.addLayout(options_layout, 1, 1, 1, 3)

        # Zeile 2: Dateifilter (Include)
        self.include_label = QLabel("&Dateien einschließen:")
        self.include_label.setToolTip("Glob-Filter für einzuschließende Dateien (z. B. *.py, *.ts)")
        self.include_input = QLineEdit()
        self.include_input.setObjectName("find_in_files_include")
        self.include_input.setPlaceholderText("z. B. *.py, *.js, *.html (leer = alle Dateien)")
        self.include_input.setClearButtonEnabled(True)
        self.include_input.setAccessibleName("Dateimuster einschließen")
        self.include_input.setAccessibleDescription("Dateien filtern, die durchsucht werden sollen, z. B. *.py")
        self.include_input.returnPressed.connect(self.start_search)
        self.include_label.setBuddy(self.include_input)
        grid.addWidget(self.include_label, 2, 0)
        grid.addWidget(self.include_input, 2, 1, 1, 3)

        # Zeile 3: Dateifilter (Exclude)
        self.exclude_label = QLabel("&Ausschließen:")
        self.exclude_label.setToolTip("Glob-Filter für auszuschließende Dateien oder Pfade")
        self.exclude_input = QLineEdit()
        self.exclude_input.setObjectName("find_in_files_exclude")
        self.exclude_input.setPlaceholderText("z. B. *.min.js, dist/* (Standard-Caches werden ignoriert)")
        self.exclude_input.setClearButtonEnabled(True)
        self.exclude_input.setAccessibleName("Dateimuster ausschließen")
        self.exclude_input.setAccessibleDescription("Dateien oder Pfade von der Suche ausschließen, z. B. dist/*")
        self.exclude_input.returnPressed.connect(self.start_search)
        self.exclude_label.setBuddy(self.exclude_input)
        grid.addWidget(self.exclude_label, 3, 0)
        grid.addWidget(self.exclude_input, 3, 1, 1, 3)

        # Zeile 4: Bereich (Scope)
        self.scope_label = QLabel("&Suchbereich:")
        self.scope_combo = QComboBox()
        self.scope_combo.setObjectName("find_in_files_scope")
        self.scope_combo.setToolTip("Wählt den zu durchsuchenden Arbeitsbereich oder Ordner")
        self.scope_combo.setAccessibleName("Suchbereich auswählen")
        self.scope_label.setBuddy(self.scope_combo)
        grid.addWidget(self.scope_label, 4, 0)
        grid.addWidget(self.scope_combo, 4, 1, 1, 3)

        root_layout.addLayout(grid)

        # ---- Aktionsleiste (Suchen, Abbrechen, Leeren, Aufklappen) ----
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        self.btn_search = QPushButton("🔍 Suchen")
        self.btn_search.setObjectName("find_in_files_btn_search")
        self.btn_search.setStyleSheet("font-weight: bold; min-width: 90px; padding: 5px 12px;")
        self.btn_search.setAccessibleName("Suche starten")
        self.btn_search.clicked.connect(self.start_search)
        actions_layout.addWidget(self.btn_search)

        self.btn_cancel = QPushButton("⏹ Abbrechen")
        self.btn_cancel.setObjectName("find_in_files_btn_cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setAccessibleName("Laufende Suche abbrechen")
        self.btn_cancel.clicked.connect(self.cancel_search)
        actions_layout.addWidget(self.btn_cancel)

        self.btn_clear = QPushButton("Leeren")
        self.btn_clear.setObjectName("find_in_files_btn_clear")
        self.btn_clear.setAccessibleName("Suchergebnisse leeren")
        self.btn_clear.clicked.connect(self.clear_results)
        actions_layout.addWidget(self.btn_clear)

        actions_layout.addStretch()

        self.btn_expand = QPushButton("Alle ausklappen")
        self.btn_expand.setStyleSheet("font-size: 11px;")
        self.btn_expand.setAccessibleName("Alle Dateitreffer ausklappen")
        self.btn_expand.clicked.connect(self._expand_all)
        actions_layout.addWidget(self.btn_expand)

        self.btn_collapse = QPushButton("Alle einklappen")
        self.btn_collapse.setStyleSheet("font-size: 11px;")
        self.btn_collapse.setAccessibleName("Alle Dateitreffer einklappen")
        self.btn_collapse.clicked.connect(self._collapse_all)
        actions_layout.addWidget(self.btn_collapse)

        root_layout.addLayout(actions_layout)

        # ---- Status- und Fortschrittsanzeige ----
        status_box = QHBoxLayout()
        self.status_label = QLabel("Bereit zum Suchen.")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        self.status_label.setAccessibleName("Suchstatus")
        status_box.addWidget(self.status_label)

        status_box.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("find_in_files_progress")
        self.progress_bar.setFixedSize(140, 12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setAccessibleName("Suchfortschritt")
        status_box.addWidget(self.progress_bar)

        root_layout.addLayout(status_box)

        # ---- Treffer-Baum (TreeWidget) ----
        self.results_tree = QTreeWidget()
        self.results_tree.setObjectName("find_in_files_tree")
        self.results_tree.setHeaderLabels(["Datei / Treffer", "Zeile", "Vorschau"])
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_tree.setColumnWidth(0, 260)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setAccessibleName("Suchergebnisse nach Dateien und Zeilen")
        self.results_tree.setAccessibleDescription(
            "Hierarchische Liste der Suchtreffer. Enter oder Doppelklick springt direkt an die Position im Editor."
        )
        self.results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.results_tree.itemActivated.connect(self._on_item_double_clicked)
        root_layout.addWidget(self.results_tree)

    def _setup_shortcuts(self):
        """Richtet praktische Tastenkürzel für den Dialog ein."""
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        QShortcut(QKeySequence("Alt+C"), self, self.cb_case.toggle)
        QShortcut(QKeySequence("Alt+W"), self, self.cb_word.toggle)
        QShortcut(QKeySequence("Alt+R"), self, self.cb_regex.toggle)

    def _on_escape(self):
        """Bricht bei laufender Suche ab oder schließt das Fenster."""
        if self._worker and self._worker.isRunning():
            self.cancel_search()
        else:
            self.close()

    def _update_scope_options(self, custom_target: Optional[Path] = None):
        """Aktualisiert die Auswahl im Suchbereichs-Kombinationsfeld."""
        self.scope_combo.clear()

        ws = getattr(self.main_window, "workspace", None)
        folders = ws.folders if ws else []

        if not folders:
            # Fallback auf Projekt-Root oder Verzeichnis der aktiven Datei
            tab = self.main_window.get_active_tab()
            if tab and tab.file_path:
                self.scope_combo.addItem(
                    f"Dateiverzeichnis: {tab.file_path.parent.name}",
                    [(tab.file_path.parent, tab.file_path.parent.name)],
                )
            else:
                self.scope_combo.addItem("Aktueller Ordner", [(Path.cwd(), "Arbeitsverzeichnis")])
            return

        # Gesamter Arbeitsbereich
        all_targets: List[Tuple[Path, str]] = [(f.path, f.name) for f in folders]
        self.scope_combo.addItem(f"Gesamter Arbeitsbereich ({len(folders)} Ordner)", all_targets)

        # Einzelne Ordner
        for f in folders:
            self.scope_combo.addItem(f"Ordner: {f.name}", [(f.path, f.name)])

        # Gegebenenfalls gezielten Ordner vorselektieren
        if custom_target:
            resolved_target = custom_target.resolve()
            for idx in range(self.scope_combo.count()):
                data = self.scope_combo.itemData(idx)
                if data and len(data) == 1 and data[0][0] == resolved_target:
                    self.scope_combo.setCurrentIndex(idx)
                    break

    def open_for_search(
        self,
        initial_query: Optional[str] = None,
        target_path: Optional[Path] = None,
    ):
        """Öffnet den Dialog und setzt optional einen Suchbegriff und Zielordner."""
        self._update_scope_options(custom_target=target_path)

        if initial_query:
            self.search_input.setText(initial_query)
            self.search_input.selectAll()

        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

    def start_search(self):
        """Startet den asynchronen Suchlauf über den SearchWorker."""
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText("Bitte einen Suchbegriff eingeben.")
            return

        # Bestehende Suche abbrechen falls noch aktiv
        self.cancel_search()

        # Optionen zusammenstellen
        include_str = self.include_input.text().strip()
        include_globs = [g.strip() for g in include_str.split(",") if g.strip()]

        exclude_str = self.exclude_input.text().strip()
        exclude_globs = [g.strip() for g in exclude_str.split(",") if g.strip()]

        options = SearchOptions(
            query=query,
            case_sensitive=self.cb_case.isChecked(),
            whole_word=self.cb_word.isChecked(),
            is_regex=self.cb_regex.isChecked(),
            include_globs=include_globs,
            exclude_globs=exclude_globs,
        )

        selected_folders: List[Tuple[Path, str]] = self.scope_combo.currentData() or []
        if not selected_folders:
            self.status_label.setText("Keine durchsuchbaren Ordner gefunden.")
            return

        self.clear_results()
        self.btn_search.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Unbestimmter Modus bis Datei-Scan beendet
        self.status_label.setText(f"Suche nach '{query}' läuft...")

        self._worker = SearchWorker(folders=selected_folders, options=options, parent=self)
        self._worker.fileCompleted.connect(self._on_file_completed)
        self._worker.searchProgress.connect(self._on_search_progress)
        self._worker.searchFinished.connect(self._on_search_finished)
        self._worker.searchError.connect(self._on_search_error)
        self._worker.start()

    def cancel_search(self):
        """Bricht den aktuellen Suchlauf ab."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)
            self.status_label.setText("Suche abgebrochen.")
            self._reset_buttons()

    def clear_results(self):
        """Leert den Trefferbaum und setzt die Statistik zurück."""
        self.results_tree.clear()
        self._current_results.clear()
        self._total_matches = 0
        self.status_label.setText("Bereit.")

    def _reset_buttons(self):
        self.btn_search.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _on_search_progress(self, current: int, total: int, file_name: str):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.status_label.setText(f"Scanne ({current}/{total}): {file_name}")

    def _on_file_completed(self, file_result: FileSearchResult):
        """Fügt eine Datei mit ihren Treffern in den Ergebnisbaum ein."""
        self._current_results.append(file_result)
        self._total_matches += len(file_result.matches)

        # Icon ermitteln
        ext = file_result.file_path.suffix.lower()
        icon = FILE_ICONS.get(ext, "📄")

        # Top-Level Datei-Item
        file_item = QTreeWidgetItem(self.results_tree)
        file_title = f"{icon} {file_result.rel_path} ({len(file_result.matches)})"
        file_item.setText(0, file_title)
        file_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
        file_item.setData(0, Qt.ItemDataRole.UserRole, (file_result.file_path, 1, 1, 0))

        # Untergeordnete Treffer-Items
        for m in file_result.matches:
            match_item = QTreeWidgetItem(file_item)
            match_item.setText(0, "")
            match_item.setText(1, f"Z. {m.line_number}:")
            match_item.setText(2, m.line_text.strip())
            match_item.setFont(1, QFont("Consolas", 9))
            match_item.setFont(2, QFont("Consolas", 9))
            match_item.setForeground(1, QColor("#569cd6"))
            match_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                (m.file_path, m.line_number, m.column, m.match_length),
            )

        file_item.setExpanded(True)

    def _on_search_finished(self, total_matches: int, total_files: int, elapsed_secs: float):
        """Wird aufgerufen, wenn der Suchlauf beendet ist."""
        self._reset_buttons()
        ms = int(elapsed_secs * 1000)
        time_str = f"{elapsed_secs:.2f}s" if elapsed_secs >= 1.0 else f"{ms}ms"
        if total_matches == 0:
            self.status_label.setText(f"Keine Treffer gefunden ({time_str}).")
        else:
            file_word = "Datei" if total_files == 1 else "Dateien"
            match_word = "Treffer" if total_matches == 1 else "Treffer"
            self.status_label.setText(
                f"{total_matches} {match_word} in {total_files} {file_word} gefunden ({time_str})."
            )

    def _on_search_error(self, err_msg: str):
        """Behandelt Fehler während des Suchlaufs."""
        self._reset_buttons()
        self.status_label.setText(f"Fehler: {err_msg}")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Öffnet die Datei an der genauen Zeilen- und Spaltenposition im Editor."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        file_path, line, col, length = data
        self.matchSelected.emit(file_path, line, col, length)

        if hasattr(self.main_window, "open_path_at"):
            self.main_window.open_path_at(file_path, line, col, length)

    def _expand_all(self):
        self.results_tree.expandAll()

    def _collapse_all(self):
        self.results_tree.collapseAll()
