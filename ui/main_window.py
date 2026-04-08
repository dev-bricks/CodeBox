#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CodeBox Hauptfenster"""

from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QStatusBar, QLabel, QComboBox, QToolBar, QFileDialog,
    QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt

from core.tabs import TabWidget
from core.output import OutputPanel
from features.terminal import TerminalWidget
from features.project_view import ProjectView
from languages import get_provider_for_extension, get_provider_by_name, get_all_providers
from features.lsp_client import LSPManager


class MainWindow(QMainWindow):
    """CodeBox Hauptfenster"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CodeBox v0.1.0")
        self.setGeometry(100, 100, 1200, 800)
        self._lsp_manager = LSPManager()

        self.setup_ui()
        self.setup_shortcuts()
        self.new_file()

    def setup_ui(self):
        # ---- Menuebar ----
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Datei")
        file_menu.addAction("Neu", self.new_file, "Ctrl+N")
        file_menu.addAction("Oeffnen...", self.open_file, "Ctrl+O")
        file_menu.addAction("Speichern", self.save_file, "Ctrl+S")
        file_menu.addSeparator()
        file_menu.addAction("Beenden", self.close, "Ctrl+Q")

        edit_menu = menubar.addMenu("Bearbeiten")
        edit_menu.addAction("Rueckgaengig", self._undo, "Ctrl+Z")
        edit_menu.addAction("Wiederherstellen", self._redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Suchen", self._find, "Ctrl+F")
        edit_menu.addAction("Gehe zu Zeile", self._goto_line, "Ctrl+G")

        run_menu = menubar.addMenu("Ausfuehren")
        run_menu.addAction("Ausfuehren", self.run_current, "F5")
        run_menu.addAction("Stoppen", self._stop_run, "Shift+F5")

        # ---- Toolbar ----
        toolbar = QToolBar("Hauptleiste")
        self.addToolBar(toolbar)
        toolbar.addAction("Neu", self.new_file)
        toolbar.addAction("Oeffnen", self.open_file)
        toolbar.addAction("Speichern", self.save_file)
        toolbar.addSeparator()
        toolbar.addAction("Run", self.run_current)

        # Sprach-Auswahl in Toolbar
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("(Auto)")
        for p in get_all_providers():
            self.lang_combo.addItem(p.get_name())
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        toolbar.addWidget(QLabel("  Sprache: "))
        toolbar.addWidget(self.lang_combo)

        # ---- Ansicht-Menue ----
        view_menu = menubar.addMenu("Ansicht")
        self._toggle_project_action = view_menu.addAction(
            "Projektbaum", self._toggle_project_view, "Ctrl+B"
        )
        self._toggle_terminal_action = view_menu.addAction(
            "Terminal", self._toggle_terminal, "Ctrl+`"
        )

        # Theme-Submenue
        from features.theme_manager import get_available_themes, apply_theme
        theme_menu = view_menu.addMenu("Theme")
        for theme_name in get_available_themes():
            theme_menu.addAction(
                theme_name.capitalize(),
                lambda checked=False, t=theme_name: apply_theme(QApplication.instance(), t)
            )

        # ---- Central Widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Horizontaler Splitter: ProjectView | Editor+Output
        self.h_splitter = QSplitter(Qt.Horizontal)

        # Linke Seite: Project-View (Dateibaum)
        self.project_view = ProjectView()
        self.project_view.fileDoubleClicked.connect(self._open_file_from_project)
        self.h_splitter.addWidget(self.project_view)

        # Rechte Seite: Vertikaler Splitter (Editor oben, Output/Terminal unten)
        self.v_splitter = QSplitter(Qt.Vertical)

        # Tab-Widget (Editor)
        self.tab_widget = TabWidget()
        self.tab_widget.currentFileChanged.connect(self._on_file_changed)
        self.v_splitter.addWidget(self.tab_widget)

        # Unteres Panel: Tabs mit Output und Terminal
        self.bottom_tabs = QTabWidget()
        self.output = OutputPanel()
        self.output.run_btn.clicked.connect(self.run_current)
        self.bottom_tabs.addTab(self.output, "Ausgabe")

        self.terminal = TerminalWidget()
        self.bottom_tabs.addTab(self.terminal, "Terminal")

        self.v_splitter.addWidget(self.bottom_tabs)
        self.v_splitter.setSizes([600, 200])

        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.setSizes([220, 980])

        layout.addWidget(self.h_splitter)

        # ---- Statusbar ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.pos_label = QLabel("Zeile 1, Spalte 1")
        self.lang_label = QLabel("Keine Sprache")
        self.enc_label = QLabel("UTF-8")
        self.status_bar.addPermanentWidget(self.pos_label)
        self.status_bar.addPermanentWidget(self.lang_label)
        self.status_bar.addPermanentWidget(self.enc_label)

    def setup_shortcuts(self):
        pass  # Shortcuts sind bereits ueber Menuebar definiert

    # ---- Datei-Aktionen ----

    def new_file(self):
        self.tab_widget.new_tab()
        self.output.run_btn.setEnabled(False)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei oeffnen", "",
            "Alle Dateien (*);;Python (*.py);;JavaScript (*.js);;C++ (*.cpp *.h)"
        )
        if path:
            tab = self.tab_widget.open_file(Path(path))
            if tab and tab.provider:
                self.lang_label.setText(tab.provider.get_name())
                self.output.run_btn.setEnabled(True)
                self._connect_lsp(tab, Path(path))
            self._connect_cursor(tab)

    def _connect_lsp(self, tab, file_path: Path):
        """Verbindet den Tab mit dem LSP-Server fuer die Sprache."""
        if not tab or not tab.provider:
            return
        lang_name = tab.provider.get_name()
        client = self._lsp_manager.get_client(lang_name)
        if not client:
            return

        uri = file_path.resolve().as_uri()
        lang_id = lang_name.lower()
        text = tab.editor.toPlainText()

        # Diagnostics-Callback: Fehler im Editor markieren
        def on_diag(params):
            diags = params.get("diagnostics", [])
            errors = []
            severity_map = {1: "error", 2: "warning", 3: "info", 4: "hint"}
            for d in diags:
                rng = d.get("range", {})
                start = rng.get("start", {})
                errors.append({
                    "line": start.get("line", 0) + 1,  # LSP ist 0-basiert, Editor 1-basiert
                    "col": start.get("character", 0),
                    "message": d.get("message", ""),
                    "severity": severity_map.get(d.get("severity", 1), "error"),
                })
            tab.editor.set_linter_errors(errors)

        client.on_diagnostics = on_diag
        client.did_open(uri, lang_id, text)

        # Completion-Callback: LSP-Ergebnisse als Completer-Words
        def on_completion(result):
            items = result if isinstance(result, list) else result.get("items", [])
            words = [i.get("label", "") for i in items if i.get("label")]
            if words:
                tab.editor.set_completer_words(words)

        client.on_completion = on_completion

        # didChange bei Textaenderungen
        version = [1]
        def on_text_changed():
            version[0] += 1
            client.did_change(uri, tab.editor.toPlainText(), version[0])
        tab.editor.textChanged.connect(on_text_changed)

        # Speichern an LSP melden
        tab._lsp_uri = uri
        tab._lsp_client = client

    def save_file(self):
        tab = self.tab_widget.current_tab()
        if not tab:
            return
        if not tab.file_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Speichern unter", "",
                "Alle Dateien (*);;Python (*.py);;JavaScript (*.js);;C++ (*.cpp)"
            )
            if path:
                tab.file_path = Path(path)
                # Provider setzen basierend auf neuer Extension
                ext = tab.file_path.suffix.lstrip('.')
                provider = get_provider_for_extension(ext)
                if provider:
                    tab.provider = provider
                    tab.highlighter.set_provider(provider)
                    tab.editor.set_provider(provider)
                    self.lang_label.setText(provider.get_name())
        tab.save()
        # LSP: didSave melden
        if hasattr(tab, '_lsp_client') and tab._lsp_client:
            tab._lsp_client.did_save(tab._lsp_uri, tab.editor.toPlainText())

    # ---- Bearbeiten-Aktionen ----

    def _undo(self):
        tab = self.tab_widget.current_tab()
        if tab:
            tab.editor.undo()

    def _redo(self):
        tab = self.tab_widget.current_tab()
        if tab:
            tab.editor.redo()

    def _find(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Suchen", "Suchbegriff:")
        if ok and text:
            tab = self.tab_widget.current_tab()
            if tab:
                count = tab.editor.highlightSearchResults(text)
                self.status_bar.showMessage(f"{count} Treffer gefunden", 3000)

    def _goto_line(self):
        from PySide6.QtWidgets import QInputDialog
        from PySide6.QtGui import QTextCursor
        tab = self.tab_widget.current_tab()
        if not tab:
            return
        line, ok = QInputDialog.getInt(
            self, "Gehe zu Zeile", "Zeile:", 1, 1, tab.editor.blockCount()
        )
        if ok:
            cursor = tab.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line - 1)
            tab.editor.setTextCursor(cursor)
            tab.editor.centerCursor()

    # ---- Ausfuehren ----

    def run_current(self):
        tab = self.tab_widget.current_tab()
        if not tab or not tab.file_path:
            QMessageBox.warning(self, "Ausfuehren", "Bitte zuerst eine Datei speichern.")
            return
        # Automatisch speichern vor dem Ausfuehren
        tab.save()
        if tab.provider:
            cmd = tab.provider.get_run_command(str(tab.file_path))
            self.output.run_command(cmd)
        else:
            QMessageBox.warning(self, "Ausfuehren",
                                "Keine Sprachunterstuetzung fuer diese Datei.")

    def _stop_run(self):
        self.output.stop_process()

    # ---- Events ----

    def _on_file_changed(self, file_path):
        if file_path:
            self.setWindowTitle(f"CodeBox - {file_path.name}")
            tab = self.tab_widget.current_tab()
            if tab and tab.provider:
                self.lang_label.setText(tab.provider.get_name())
                self.output.run_btn.setEnabled(True)
            self._connect_cursor(tab)
            # ProjectView und Terminal auf Projektordner setzen
            project_dir = str(file_path.parent)
            if not self.project_view._root_path:
                self.project_view.set_root(project_dir)
            self.terminal.set_working_dir(project_dir)
        else:
            self.setWindowTitle("CodeBox")
            self.lang_label.setText("Keine Sprache")
            self.output.run_btn.setEnabled(False)

    def _on_language_changed(self, lang_name):
        if lang_name == "(Auto)":
            return
        tab = self.tab_widget.current_tab()
        if tab:
            provider = get_provider_by_name(lang_name)
            if provider:
                tab.provider = provider
                tab.highlighter.set_provider(provider)
                tab.editor.set_provider(provider)
                self.lang_label.setText(provider.get_name())
                self.output.run_btn.setEnabled(True)

    def _connect_cursor(self, tab):
        if tab:
            try:
                tab.editor.cursorPositionInfo.disconnect()
            except TypeError:
                pass
            tab.editor.cursorPositionInfo.connect(
                lambda line, col: self.pos_label.setText(f"Zeile {line}, Spalte {col}")
            )

    def _open_file_from_project(self, file_path):
        """Oeffnet eine Datei aus dem Projektbaum."""
        tab = self.tab_widget.open_file(file_path)
        if tab and tab.provider:
            self.lang_label.setText(tab.provider.get_name())
            self.output.run_btn.setEnabled(True)
        self._connect_cursor(tab)

    def _toggle_project_view(self):
        """Blendet den Projektbaum ein/aus."""
        self.project_view.setVisible(not self.project_view.isVisible())

    def _toggle_terminal(self):
        """Blendet das untere Panel ein/aus und wechselt zum Terminal-Tab."""
        if self.bottom_tabs.isVisible() and self.bottom_tabs.currentWidget() == self.terminal:
            self.bottom_tabs.hide()
        else:
            self.bottom_tabs.show()
            self.bottom_tabs.setCurrentWidget(self.terminal)
            self.terminal.input.setFocus()

    def closeEvent(self, event):
        # Alle Tabs pruefen auf ungespeicherte Aenderungen
        unsaved = []
        for idx in range(self.tab_widget.count()):
            tab = self.tab_widget.tabs.get(idx)
            if tab and tab.is_modified:
                unsaved.append(self.tab_widget.tabText(idx))
        if unsaved:
            names = "\n".join(f"  - {n}" for n in unsaved)
            reply = QMessageBox.question(
                self, "Beenden",
                f"Es gibt ungespeicherte Aenderungen in:\n{names}\n\nTrotzdem beenden?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        # Terminal-Prozess sauber beenden
        if hasattr(self, 'terminal'):
            self.terminal.close()
        # LSP-Server stoppen
        self._lsp_manager.stop_all()
        event.accept()
