#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CodeBox Hauptfenster"""

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QStatusBar, QLabel, QComboBox, QToolBar, QFileDialog,
    QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal

from core.tabs import TabWidget, EditorTab
from core.output import OutputPanel
from core.workspace import WorkspaceManager
from features.terminal import TerminalWidget
from features.project_view import ProjectView
from languages import (
    get_provider_for_extension,
    get_provider_by_name,
    get_all_providers,
    add_provider_listener,
    remove_provider_listener,
)
from features.lsp_client import LSPManager
from features.linter import LinterManager
from features.plugin_manager import PluginManager
from ui.problems_panel import ProblemsPanel
from ui.plugins_dialog import PluginsDialog
from ui.shortcuts_dialog import ShortcutsDialog
from ui.command_palette import CommandPaletteDialog
from version import format_window_title, APP_VERSION
from config import load_settings


class MainWindow(QMainWindow):
    """CodeBox Hauptfenster"""

    lspDiagnosticsReceived = Signal(object, list)
    lspCompletionsReceived = Signal(object, list)

    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        self.setWindowTitle(format_window_title())
        self.setGeometry(100, 100, 1200, 800)
        self._lsp_manager = LSPManager()
        self._lsp_tabs_by_uri = {}
        self._linter_manager = LinterManager(self)
        self._problems_by_tab = {}
        self.lspDiagnosticsReceived.connect(self._apply_lsp_diagnostics)
        self.lspCompletionsReceived.connect(self._apply_lsp_completions)
        self._linter_manager.lintFinished.connect(self._apply_linter_results)

        # Plugin-Manager & Auto-Discovery
        self._plugin_manager = PluginManager()
        self._plugin_manager.discover_and_load_all()
        add_provider_listener(self._on_providers_updated)

        self._find_dialog = None
        self._find_in_files_dialog = None
        self._active_tab_widget = None

        # Workspace-Manager für Multi-Root-Support
        self.workspace = WorkspaceManager(self)
        self.workspace.activeFolderChanged.connect(self._on_workspace_active_folder_changed)
        self.workspace.workspaceLoaded.connect(self._on_workspace_loaded)

        self.setup_ui()
        self.setup_shortcuts()
        self._apply_settings()
        self.new_file()

    def setup_ui(self):
        # ---- Menüleiste ----
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Datei")
        act_new = file_menu.addAction("Neu", self.new_file, "Ctrl+N")
        act_new.setStatusTip("Erstellt eine neue leere Datei")
        act_open = file_menu.addAction("Öffnen...", self.open_file, "Ctrl+O")
        act_open.setStatusTip("Öffnet eine bestehende Datei von der Festplatte")
        act_open_folder = file_menu.addAction("Ordner öffnen...", self.open_folder_dialog, "Ctrl+Shift+O")
        act_open_folder.setStatusTip("Öffnet einen Projektordner als einzelnen Arbeitsbereich")
        act_add_folder = file_menu.addAction("Ordner zum Arbeitsbereich hinzufügen...", self.add_workspace_folder_dialog)
        act_add_folder.setStatusTip("Fügt einen weiteren Projektordner zum aktuellen Arbeitsbereich hinzu")
        file_menu.addSeparator()
        act_open_ws = file_menu.addAction("Arbeitsbereich öffnen...", self.open_workspace_dialog)
        act_open_ws.setStatusTip("Öffnet eine .codebox-workspace Datei")
        act_save_ws = file_menu.addAction("Arbeitsbereich speichern unter...", self.save_workspace_dialog)
        act_save_ws.setStatusTip("Speichert den aktuellen Arbeitsbereich in eine Datei")
        act_close_ws = file_menu.addAction("Arbeitsbereich schließen", self.close_workspace)
        act_close_ws.setStatusTip("Schließt alle Ordner des aktuellen Arbeitsbereichs")
        file_menu.addSeparator()
        act_quick_open = file_menu.addAction("Schnell öffnen...", self.show_quick_open, "Ctrl+P")
        act_quick_open.setStatusTip("Öffnet die Schnellauswahl für Projektdateien (Quick Open)")
        act_save = file_menu.addAction("Speichern", self.save_file, "Ctrl+S")
        act_save.setStatusTip("Speichert die aktuelle Datei")
        file_menu.addSeparator()
        act_quit = file_menu.addAction("Beenden", self.close, "Ctrl+Q")
        act_quit.setStatusTip("Schließt die CodeBox-Anwendung")

        edit_menu = menubar.addMenu("Bearbeiten")
        act_undo = edit_menu.addAction("Rückgängig", self._undo, "Ctrl+Z")
        act_undo.setStatusTip("Macht die letzte Änderung rückgängig")
        act_redo = edit_menu.addAction("Wiederherstellen", self._redo, "Ctrl+Y")
        act_redo.setStatusTip("Stellt die letzte rückgängig gemachte Änderung wieder her")
        edit_menu.addSeparator()
        act_find = edit_menu.addAction("Suchen...", self._find, "Ctrl+F")
        act_find.setStatusTip("Öffnet den Suchen- und Ersetzen-Dialog")
        act_replace = edit_menu.addAction("Ersetzen...", self._replace, "Ctrl+H")
        act_replace.setStatusTip("Öffnet den Suchen- und Ersetzen-Dialog im Ersetzen-Modus")
        act_find_in_files = edit_menu.addAction("In Dateien suchen...", self.show_find_in_files, "Ctrl+Shift+F")
        act_find_in_files.setStatusTip("Durchsucht alle Projektdateien im Arbeitsbereich nach Text")
        act_find_next = edit_menu.addAction("Weitersuchen", self._find_next, "F3")
        act_find_next.setStatusTip("Springt zum nächsten Suchtreffer")
        act_find_prev = edit_menu.addAction("Rückwärts weitersuchen", self._find_prev, "Shift+F3")
        act_find_prev.setStatusTip("Springt zum vorherigen Suchtreffer")
        act_goto = edit_menu.addAction("Gehe zu Zeile...", self._goto_line, "Ctrl+G")
        act_goto.setStatusTip("Springt zu einer bestimmten Zeilennummer")
        edit_menu.addSeparator()
        act_comment = edit_menu.addAction("Zeilenkommentar umschalten", self._toggle_comment, "Ctrl+/")
        act_comment.setStatusTip("Kommentiert die aktuelle Zeile oder Auswahl aus/ein")
        act_indent = edit_menu.addAction("Einrücken", self._indent, "Tab")
        act_indent.setStatusTip("Rückt die aktuelle Zeile oder Auswahl ein")
        act_dedent = edit_menu.addAction("Ausrücken", self._dedent, "Shift+Tab")
        act_dedent.setStatusTip("Rückt die aktuelle Zeile oder Auswahl aus")
        edit_menu.addSeparator()
        selection_menu = edit_menu.addMenu("Mehrfachauswahl & Multi-Cursor")
        act_cursor_above = selection_menu.addAction("Cursor oberhalb hinzufügen", self._add_cursor_above, "Ctrl+Alt+Up")
        act_cursor_above.setStatusTip("Fügt einen weiteren Cursor in der Zeile darüber ein (Spaltenauswahl)")
        act_cursor_below = selection_menu.addAction("Cursor unterhalb hinzufügen", self._add_cursor_below, "Ctrl+Alt+Down")
        act_cursor_below.setStatusTip("Fügt einen weiteren Cursor in der Zeile darunter ein (Spaltenauswahl)")
        act_select_all_occ = selection_menu.addAction("Alle Vorkommen markieren", self._select_all_occurrences, "Ctrl+Shift+L")
        act_select_all_occ.setStatusTip("Markiert alle Vorkommen des aktuellen Wortes oder der Auswahl mit Multi-Cursorn")
        act_add_next_occ = selection_menu.addAction("Nächstes Vorkommen hinzufügen", self._add_next_occurrence, "Ctrl+Alt+L")
        act_add_next_occ.setStatusTip("Fügt das nächste Vorkommen zur Mehrfachauswahl hinzu")
        act_clear_cursors = selection_menu.addAction("Mehrfachcursor aufheben", self._clear_multi_cursors, "Escape")
        act_clear_cursors.setStatusTip("Hebt alle zusätzlichen Cursor auf und kehrt zum Einzelcursor zurück")
        edit_menu.addSeparator()
        act_palette = edit_menu.addAction("Befehlspalette...", self.show_command_palette, "Ctrl+Shift+P")
        act_palette.setStatusTip("Öffnet die Befehlspalette für alle Aktionen")
        act_plugins = edit_menu.addAction("Plugins & Sprachen...", self.open_plugins_dialog)
        act_plugins.setStatusTip("Öffnet die Verwaltung für Sprach-Erweiterungen und Plugins")
        self.act_vim_mode = edit_menu.addAction("Vim-Modus", self.toggle_vim_mode, "Ctrl+Alt+V")
        self.act_vim_mode.setCheckable(True)
        self.act_vim_mode.setChecked(bool(self._settings.get("vim_mode", False)))
        self.act_vim_mode.setStatusTip("Schaltet modales Editieren (Normal, Insert, Visual) ein oder aus")
        act_settings = edit_menu.addAction("Einstellungen...", self.open_settings_dialog, "Ctrl+,")
        act_settings.setStatusTip("Öffnet die Programmeinstellungen")

        run_menu = menubar.addMenu("Ausführen")
        act_run = run_menu.addAction("Ausführen", self.run_current, "F5")
        act_run.setStatusTip("Führt das aktuelle Skript oder Programm aus")
        act_stop = run_menu.addAction("Stoppen", self._stop_run, "Shift+F5")
        act_stop.setStatusTip("Bricht den laufenden Ausführungsprozess ab")

        # ---- Toolbar ----
        toolbar = QToolBar("Hauptleiste")
        toolbar.setObjectName("main_toolbar")
        self.addToolBar(toolbar)

        self.action_new = toolbar.addAction("Neu", self.new_file)
        self.action_new.setToolTip("Neue Datei erstellen (Ctrl+N)")
        self.action_new.setStatusTip("Erstellt eine neue leere Datei")
        self.action_new.setWhatsThis("Erstellt eine neue leere Datei im Editor")

        self.action_open = toolbar.addAction("Öffnen", self.open_file)
        self.action_open.setToolTip("Datei öffnen (Ctrl+O)")
        self.action_open.setStatusTip("Öffnet eine bestehende Datei von der Festplatte")
        self.action_open.setWhatsThis("Öffnet eine bestehende Datei von der Festplatte")

        self.action_save = toolbar.addAction("Speichern", self.save_file)
        self.action_save.setToolTip("Aktuelle Datei speichern (Ctrl+S)")
        self.action_save.setStatusTip("Speichert die aktive Datei auf die Festplatte")
        self.action_save.setWhatsThis("Speichert die aktive Datei auf die Festplatte")

        toolbar.addSeparator()

        self.action_run = toolbar.addAction("Ausführen", self.run_current)
        self.action_run.setToolTip("Aktuelle Datei ausführen (F5)")
        self.action_run.setStatusTip("Führt das aktuelle Skript oder Programm aus")
        self.action_run.setWhatsThis("Führt das aktuelle Skript oder Programm aus")

        # Sprach-Auswahl in Toolbar
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("lang_combo")
        self.lang_combo.addItem("(Auto)")
        for p in get_all_providers():
            self.lang_combo.addItem(p.get_name())
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        self.lang_combo.setToolTip("Programmiersprache für Syntax-Highlighting und Ausführung auswählen")
        self.lang_combo.setAccessibleName("Programmiersprache")
        self.lang_combo.setAccessibleDescription("Wählt die Programmiersprache für Syntax-Highlighting und Ausführung")

        self.lang_label_toolbar = QLabel("  Sprache: ")
        self.lang_label_toolbar.setToolTip("Auswahl der aktiven Programmiersprache")
        toolbar.addWidget(self.lang_label_toolbar)
        toolbar.addWidget(self.lang_combo)

        # ---- Ansicht-Menü ----
        view_menu = menubar.addMenu("Ansicht")
        self._toggle_project_action = view_menu.addAction(
            "Projektbaum", self._toggle_project_view, "Ctrl+B"
        )
        self._toggle_project_action.setStatusTip("Blendet den Datei- und Projektbaum ein oder aus")

        self._toggle_terminal_action = view_menu.addAction(
            "Terminal", self._toggle_terminal, "Ctrl+`"
        )
        self._toggle_terminal_action.setStatusTip("Blendet das integrierte Terminal ein oder aus")

        self._toggle_diff_action = view_menu.addAction(
            "Git-Diff anzeigen...", lambda: self.show_diff(), "Ctrl+Alt+D"
        )
        self._toggle_diff_action.setStatusTip("Öffnet den Git Diff-Viewer für geänderte Dateien")

        self._toggle_commit_action = view_menu.addAction(
            "Git-Commit Dialog...", lambda: self.show_git_commit(), "Ctrl+Alt+C"
        )
        self._toggle_commit_action.setStatusTip("Öffnet den Dialog zum Stagen und Committen von Git-Änderungen")

        # Theme-Submenü
        from features.theme_manager import get_available_themes, apply_theme
        theme_menu = view_menu.addMenu("Theme")
        for theme_name in get_available_themes():
            t_act = theme_menu.addAction(
                theme_name.capitalize(),
                lambda checked=False, t=theme_name: apply_theme(QApplication.instance(), t)
            )
            t_act.setStatusTip(f"Farbschema auf '{theme_name.capitalize()}' umstellen")

        # Code-Faltung Submenü
        folding_menu = view_menu.addMenu("Code-Faltung")
        self._toggle_fold_action = folding_menu.addAction(
            "Faltung umschalten", self._toggle_fold_current, "Ctrl+Shift+["
        )
        self._toggle_fold_action.setStatusTip("Klappt den aktuellen Block an der Cursorposition ein oder aus")

        self._fold_all_action = folding_menu.addAction(
            "Alles einklappen", self._fold_all, "Ctrl+Alt+["
        )
        self._fold_all_action.setStatusTip("Klappt alle Funktionen und Klassen im Dokument ein")

        self._unfold_all_action = folding_menu.addAction(
            "Alles ausklappen", self._unfold_all, "Ctrl+Alt+]"
        )
        self._unfold_all_action.setStatusTip("Klappt alle Funktionen und Klassen im Dokument aus")

        # Editor teilen Submenü
        split_menu = view_menu.addMenu("Editor teilen")
        self._split_right_action = split_menu.addAction(
            "Nach rechts teilen (vertikal)", self.split_editor_right, "Ctrl+\\"
        )
        self._split_right_action.setStatusTip("Teilt den Editor in zwei nebeneinanderliegende Spalten")

        self._split_down_action = split_menu.addAction(
            "Nach unten teilen (horizontal)", self.split_editor_down, "Ctrl+Shift+\\"
        )
        self._split_down_action.setStatusTip("Teilt den Editor in zwei übereinanderliegende Zeilen")

        self._unsplit_action = split_menu.addAction(
            "Teilung aufheben", self.unsplit_editor, "Ctrl+Alt+W"
        )
        self._unsplit_action.setStatusTip("Schließt die geteilte Ansicht und kehrt zum Einzeleditor zurück")

        self._switch_split_action = split_menu.addAction(
            "Fokus zwischen Ansichten wechseln", self.focus_other_split, "F6"
        )
        self._switch_split_action.setStatusTip("Wechselt den Tastaturfokus zwischen den geteilten Editorfenstern")

        self._move_tab_split_action = split_menu.addAction(
            "Aktiven Tab zur anderen Ansicht verschieben", self.move_tab_to_other_split, "Ctrl+Alt+M"
        )
        self._move_tab_split_action.setStatusTip("Verschiebt das aktuelle Dokument in die andere Editorhälfte")

        # ---- Hilfe-Menü ----
        help_menu = menubar.addMenu("Hilfe")
        act_shortcuts = help_menu.addAction("Tastenkürzel-Übersicht", self.open_shortcuts_dialog, "F1")
        act_shortcuts.setStatusTip("Öffnet die Übersicht aller verfügbaren Tastenkombinationen")
        act_help_plugins = help_menu.addAction("Plugins & Sprachen...", self.open_plugins_dialog)
        act_help_plugins.setStatusTip("Öffnet die Übersicht der installierten Sprach-Plugins")
        help_menu.addSeparator()
        act_about = help_menu.addAction("Über CodeBox...", self._about_dialog)
        act_about.setStatusTip("Zeigt Versions- und Programminformationen über CodeBox an")

        # ---- Central Widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Horizontaler Splitter: ProjectView | Editor+Output
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Project-View (Dateibaum)
        self.project_view = ProjectView()
        self.project_view.set_workspace(self.workspace)
        self.project_view.fileDoubleClicked.connect(self._open_file_from_project)
        self.project_view.diffRequested.connect(self.show_diff)
        self.project_view.commitRequested.connect(self.show_git_commit)
        self.project_view.findInFilesRequested.connect(lambda p: self.show_find_in_files(target_path=p))
        self.h_splitter.addWidget(self.project_view)

        # Rechte Seite: Vertikaler Splitter (Editor oben, Output/Terminal unten)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Editor-Splitter (Horizontal / Vertikal teilbar für geteilte Ansichten)
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setObjectName("editor_splitter")

        # Primäres Tab-Widget (Editor)
        self.tab_widget = TabWidget()
        self.tab_widget.setObjectName("primary_tab_widget")
        self.tab_widget.currentFileChanged.connect(self._on_file_changed)
        self.tab_widget.tabFocused.connect(self._on_tab_widget_focused)
        self.editor_splitter.addWidget(self.tab_widget)

        # Sekundäres Tab-Widget (Split-Editor)
        self.split_tab_widget = TabWidget()
        self.split_tab_widget.setObjectName("split_tab_widget")
        self.split_tab_widget.setAccessibleName("Geteilte Editor-Tabs")
        self.split_tab_widget.setAccessibleDescription("Reiterleiste für geteilte Code-Ansicht")
        self.split_tab_widget.currentFileChanged.connect(self._on_file_changed)
        self.split_tab_widget.tabFocused.connect(self._on_tab_widget_focused)
        self.split_tab_widget.tabCloseRequested.connect(self._on_split_tab_close_requested)
        self.split_tab_widget.setVisible(False)
        self.editor_splitter.addWidget(self.split_tab_widget)

        self.v_splitter.addWidget(self.editor_splitter)

        # Unteres Panel: Tabs mit Output und Terminal
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setObjectName("bottom_tabs")
        self.bottom_tabs.setAccessibleName("Unteres Bedienpanel")
        self.bottom_tabs.setAccessibleDescription("Bereich mit Reitern für Ausgabe, Terminal und Probleme")

        self.output = OutputPanel()
        self.output.run_btn.clicked.connect(self.run_current)
        self.bottom_tabs.addTab(self.output, "Ausgabe")
        self.bottom_tabs.setTabToolTip(0, "Programmausgabe und Fehlermeldungen anzeigen")

        self.terminal = TerminalWidget()
        self.bottom_tabs.addTab(self.terminal, "Terminal")
        self.bottom_tabs.setTabToolTip(1, "Integriertes Befehlszeilenterminal")

        self.problems = ProblemsPanel()
        self.problems.problemActivated.connect(self._activate_problem)
        self.bottom_tabs.addTab(self.problems, "Probleme")
        self.bottom_tabs.setTabToolTip(2, "LSP- und Linter-Diagnosen und Fehlermeldungen")

        self.v_splitter.addWidget(self.bottom_tabs)
        self.v_splitter.setSizes([600, 200])

        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.setSizes([220, 980])

        layout.addWidget(self.h_splitter)

        # ---- Statusbar ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.vim_label = QLabel("")
        self.vim_label.setObjectName("vim_label")
        self.vim_label.setToolTip("Aktueller Vim-Modus und Befehlspuffer")
        self.vim_label.setAccessibleName("Vim-Modus Status")
        self.vim_label.setStyleSheet("font-weight: bold; padding-right: 8px; color: #569cd6;")
        self.vim_label.setVisible(False)
        self.status_bar.addWidget(self.vim_label)

        self.pos_label = QLabel("Zeile 1, Spalte 1")
        self.pos_label.setToolTip("Aktuelle Cursor-Position (Zeile, Spalte)")
        self.pos_label.setAccessibleName("Cursorposition")
        self.pos_label.setAccessibleDescription("Zeigt die aktuelle Zeilen- und Spaltennummer des Cursors im Editor")

        self.lang_label = QLabel("Keine Sprache")
        self.lang_label.setToolTip("Aktive Programmiersprache für Highlighting und LSP")
        self.lang_label.setAccessibleName("Aktive Sprache")
        self.lang_label.setAccessibleDescription("Zeigt die aktuell aktive Programmiersprache")

        self.enc_label = QLabel("UTF-8")
        self.enc_label.setToolTip("Dateikodierung (UTF-8)")
        self.enc_label.setAccessibleName("Dateikodierung")
        self.enc_label.setAccessibleDescription("Zeigt die Zeichenkodierung der geöffneten Datei")

        self.status_bar.addPermanentWidget(self.pos_label)
        self.status_bar.addPermanentWidget(self.lang_label)
        self.status_bar.addPermanentWidget(self.enc_label)

    def setup_shortcuts(self):
        pass  # Shortcuts sind bereits über die Menüleiste definiert

    # ---- Split-Editor- & Tab-Verwaltung ----

    def _apply_tab_settings(self, tab: Optional[EditorTab]):
        """Wendet Schriftart-, Tab-, Minimap- und Vim-Einstellungen auf einen Tab an."""
        if tab and tab.editor and hasattr(self, '_settings') and self._settings:
            font_family = self._settings.get("font_family", "Consolas")
            font_size = int(self._settings.get("font_size", 10))
            tab_size = int(self._settings.get("tab_size", 4))
            tab.editor.apply_editor_settings(font_family, font_size, tab_size)
            tab.editor.set_minimap_visible(
                bool(self._settings.get("show_minimap", True))
            )
            tab.editor.set_vim_mode_enabled(
                bool(self._settings.get("vim_mode", False))
            )

    def get_active_tab_widget(self) -> TabWidget:
        """Gibt das aktuell aktive Tab-Widget zurück (primär oder geteilt)."""
        if (
            self._active_tab_widget is not None
            and not self._active_tab_widget.isHidden()
            and self._active_tab_widget.count() > 0
        ):
            return self._active_tab_widget
        return self.tab_widget

    def get_active_tab(self) -> Optional[EditorTab]:
        """Gibt den aktiven Tab des aktuell fokussierten Bereichs zurück."""
        tw = self.get_active_tab_widget()
        return tw.current_tab()

    def is_editor_split(self) -> bool:
        """Prüft, ob der geteilte Editor aktuell sichtbar ist."""
        return not self.split_tab_widget.isHidden()

    def split_editor(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal):
        """Teilt den Editor horizontal (nebeneinander) oder vertikal (übereinander)."""
        self.editor_splitter.setOrientation(orientation)
        if self.split_tab_widget.isHidden():
            self.split_tab_widget.setVisible(True)
            if self.split_tab_widget.count() == 0:
                active_tab = self.tab_widget.current_tab()
                if active_tab:
                    split_tab = self.split_tab_widget.clone_tab(active_tab)
                else:
                    split_tab = self.split_tab_widget.new_tab()
                self._apply_tab_settings(split_tab)
                self._connect_cursor(split_tab)

            total = (
                self.editor_splitter.width()
                if orientation == Qt.Orientation.Horizontal
                else self.editor_splitter.height()
            )
            half = max(150, total // 2)
            self.editor_splitter.setSizes([half, half])

        self._active_tab_widget = self.split_tab_widget
        cur = self.split_tab_widget.current_tab()
        if cur and cur.editor:
            cur.editor.setFocus()
            self._update_status_bar_for_tab(cur)

    def split_editor_right(self):
        """Teilt den Editor in zwei vertikale Spalten nebeneinander."""
        self.split_editor(Qt.Orientation.Horizontal)

    def split_editor_down(self):
        """Teilt den Editor in zwei horizontale Zeilen übereinander."""
        self.split_editor(Qt.Orientation.Vertical)

    def unsplit_editor(self):
        """Hebt die Teilung auf und überführt exklusive Tabs sicher in den Hauptbereich."""
        if self.split_tab_widget.isHidden():
            return

        while self.split_tab_widget.count() > 0:
            split_tab = self.split_tab_widget.tabs.get(0)
            if not split_tab:
                self.split_tab_widget.removeTab(0)
                continue
            already_in_primary = any(
                (t.file_path and split_tab.file_path and t.file_path == split_tab.file_path)
                or (t.editor.document() is split_tab.editor.document())
                for t in self.tab_widget.tabs.values()
            )
            if not already_in_primary:
                self.tab_widget.move_tab_from(self.split_tab_widget, 0)
            else:
                self.split_tab_widget.close_tab(0, prompt=False)

        self.split_tab_widget.setVisible(False)
        self._active_tab_widget = self.tab_widget
        cur = self.tab_widget.current_tab()
        if cur and cur.editor:
            cur.editor.setFocus()
            self._update_status_bar_for_tab(cur)

    def focus_other_split(self):
        """Wechselt den Tastaturfokus zwischen den beiden geteilten Editor-Fenstern."""
        if self.split_tab_widget.isHidden():
            self.split_editor_right()
            return
        if self.get_active_tab_widget() is self.split_tab_widget:
            target = self.tab_widget
        else:
            target = self.split_tab_widget
        self._active_tab_widget = target
        cur = target.current_tab()
        if cur and cur.editor:
            cur.editor.setFocus()
            self._update_status_bar_for_tab(cur)

    def move_tab_to_other_split(self):
        """Verschiebt das aktuelle Dokument in die andere Editorhälfte."""
        active_tw = self.get_active_tab_widget()
        if active_tw is self.tab_widget:
            if self.split_tab_widget.isHidden():
                self.split_tab_widget.setVisible(True)
                total = self.editor_splitter.width()
                half = max(150, total // 2)
                self.editor_splitter.setSizes([half, half])
            source_tw = self.tab_widget
            target_tw = self.split_tab_widget
        else:
            source_tw = self.split_tab_widget
            target_tw = self.tab_widget

        idx = source_tw.currentIndex()
        if idx < 0 or source_tw.count() == 0:
            return

        moved_tab = target_tw.move_tab_from(source_tw, idx)
        if moved_tab:
            self._apply_tab_settings(moved_tab)
            self._connect_cursor(moved_tab)
            self._active_tab_widget = target_tw
            moved_tab.editor.setFocus()
            self._update_status_bar_for_tab(moved_tab)

        if self.split_tab_widget.count() == 0:
            self.unsplit_editor()

    def _on_split_tab_close_requested(self, index: int):
        self.split_tab_widget.close_tab(index)
        if self.split_tab_widget.count() == 0:
            self.unsplit_editor()

    def _on_tab_widget_focused(self, widget, tab=None):
        self._active_tab_widget = widget
        t = tab or widget.current_tab()
        if t:
            self._update_status_bar_for_tab(t)

    def _update_status_bar_for_tab(self, tab: Optional[EditorTab]):
        if not tab:
            return
        if tab.provider:
            self.lang_label.setText(tab.provider.get_name())
            self.output.run_btn.setEnabled(True)
            self.lang_combo.blockSignals(True)
            idx = self.lang_combo.findText(tab.provider.get_name())
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)
        else:
            self.lang_label.setText("Keine Sprache")
            self.output.run_btn.setEnabled(False)
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(0)
            self.lang_combo.blockSignals(False)

        if tab.file_path:
            self.setWindowTitle(format_window_title(tab.file_path))
        else:
            self.setWindowTitle(format_window_title())

        cursor = tab.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.pos_label.setText(f"Zeile {line}, Spalte {col}")
        self._update_vim_status_label(tab)

    def _update_vim_status_label(self, tab: Optional[EditorTab]):
        """Aktualisiert die Vim-Modus Anzeige in der Statusleiste."""
        if not hasattr(self, "vim_label"):
            return
        if not tab or not tab.editor or not hasattr(tab.editor, "vim_engine"):
            self.vim_label.setText("")
            self.vim_label.setVisible(False)
            return

        engine = tab.editor.vim_engine
        if not engine.is_enabled():
            self.vim_label.setText("")
            self.vim_label.setVisible(False)
            return

        mode = engine.get_mode().value
        cmd_buf = engine.get_command_buffer()
        suffix = f"  [{cmd_buf}]" if cmd_buf else ""
        self.vim_label.setText(f"-- {mode} --{suffix}")
        self.vim_label.setVisible(True)

    # ---- Datei-Aktionen ----

    def new_file(self, target_widget: Optional[TabWidget] = None):
        target = target_widget or self.get_active_tab_widget()
        tab = target.new_tab()
        self.output.run_btn.setEnabled(False)
        self._connect_cursor(tab)
        self._apply_tab_settings(tab)
        self._update_status_bar_for_tab(tab)
        return tab

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei öffnen", "",
            "Alle Dateien (*);;Python (*.py);;JavaScript (*.js);;C++ (*.cpp *.h)"
        )
        if path:
            self.open_path(Path(path))

    def open_folder_dialog(self):
        """Öffnet einen Dialog zur Auswahl eines einzelnen Projektordners."""
        path = QFileDialog.getExistingDirectory(self, "Projektordner öffnen")
        if path:
            self.open_folder(Path(path))

    def open_folder(self, path: Path | str):
        """Öffnet einen Ordner als einzelnen Workspace-Ordner."""
        folder = Path(path).resolve()
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Ordner öffnen", f"Ordner nicht gefunden:\n{folder}")
            return
        self.workspace.set_single_folder(folder)
        self.status_bar.showMessage(f"Projektordner geöffnet: {folder.name}", 3000)

    def add_workspace_folder_dialog(self):
        """Öffnet einen Dialog zum Hinzufügen eines weiteren Ordners zum Arbeitsbereich."""
        path = QFileDialog.getExistingDirectory(self, "Ordner zum Arbeitsbereich hinzufügen")
        if path:
            self.add_workspace_folder(Path(path))

    def add_workspace_folder(self, path: Path | str, name: Optional[str] = None):
        """Fügt einen Ordner zum aktuellen Arbeitsbereich hinzu."""
        folder = Path(path).resolve()
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Ordner hinzufügen", f"Ordner nicht gefunden:\n{folder}")
            return
        self.workspace.add_folder(folder, name=name, make_active=True)
        self.status_bar.showMessage(f"Ordner zum Arbeitsbereich hinzugefügt: {folder.name}", 3000)

    def open_workspace_dialog(self):
        """Öffnet einen Dialog zum Laden einer .codebox-workspace Datei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Arbeitsbereich öffnen", "",
            "CodeBox Workspace (*.codebox-workspace);;JSON (*.json);;Alle Dateien (*)"
        )
        if path:
            self.open_workspace_file(Path(path))

    def open_workspace_file(self, path: Path | str) -> bool:
        """Lädt eine Arbeitsbereichs-Konfigurationsdatei."""
        ws_path = Path(path).resolve()
        if not ws_path.exists():
            QMessageBox.warning(self, "Arbeitsbereich öffnen", f"Datei nicht gefunden:\n{ws_path}")
            return False
        ok = self.workspace.load_workspace(ws_path)
        if ok:
            recent = self._settings.setdefault("recent_workspaces", [])
            p_str = str(ws_path)
            if p_str in recent:
                recent.remove(p_str)
            recent.insert(0, p_str)
            self._settings["recent_workspaces"] = recent[:10]
            from config import save_settings
            save_settings(self._settings)
            self.status_bar.showMessage(f"Arbeitsbereich '{self.workspace.name}' geladen.", 4000)
            return True
        else:
            QMessageBox.warning(self, "Arbeitsbereich öffnen", f"Fehler beim Laden des Arbeitsbereichs:\n{ws_path}")
            return False

    def save_workspace_dialog(self):
        """Öffnet einen Dialog zum Speichern des aktuellen Arbeitsbereichs."""
        default_name = f"{self.workspace.name or 'workspace'}.codebox-workspace"
        path, _ = QFileDialog.getSaveFileName(
            self, "Arbeitsbereich speichern unter", default_name,
            "CodeBox Workspace (*.codebox-workspace);;JSON (*.json);;Alle Dateien (*)"
        )
        if path:
            self.save_workspace_file(Path(path))

    def save_workspace_file(self, path: Path | str) -> bool:
        """Speichert den aktuellen Arbeitsbereich in eine Datei."""
        ws_path = Path(path).resolve()
        ok = self.workspace.save_workspace(ws_path)
        if ok:
            recent = self._settings.setdefault("recent_workspaces", [])
            p_str = str(ws_path)
            if p_str in recent:
                recent.remove(p_str)
            recent.insert(0, p_str)
            self._settings["recent_workspaces"] = recent[:10]
            from config import save_settings
            save_settings(self._settings)
            self.status_bar.showMessage(f"Arbeitsbereich gespeichert: {ws_path.name}", 3000)
            return True
        else:
            QMessageBox.warning(self, "Arbeitsbereich speichern", f"Fehler beim Speichern:\n{ws_path}")
            return False

    def close_workspace(self):
        """Schließt alle Ordner im aktuellen Arbeitsbereich."""
        self.workspace.clear()
        self.status_bar.showMessage("Arbeitsbereich geschlossen.", 3000)

    def _on_workspace_active_folder_changed(self, active_folder: Optional[Path]):
        """Reagiert auf Änderungen des aktiven Ordners im Workspace."""
        if active_folder:
            self.terminal.set_working_dir(str(active_folder))

    def _on_workspace_loaded(self, path: str):
        """Wird ausgelöst, wenn ein Workspace geladen wurde."""
        if self.workspace.active_folder:
            self.terminal.set_working_dir(str(self.workspace.active_folder))

    def open_path(self, file_path: Path, target_widget: Optional[TabWidget] = None):
        """Öffnet einen konkreten Pfad ohne Dateidialog."""
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, "Datei öffnen", f"Datei nicht gefunden:\n{path}")
            return None

        target = target_widget or self.get_active_tab_widget()

        # Prüfen, ob die Datei bereits im anderen Tab-Widget offen ist -> dann Klon erstellen für synchrones Bearbeiten
        other_tw = self.split_tab_widget if target is self.tab_widget else self.tab_widget
        other_tab = None
        for idx in range(other_tw.count()):
            t = other_tw.tabs.get(idx)
            if t and t.file_path and t.file_path.resolve() == path.resolve():
                other_tab = t
                break

        if other_tab is not None and target is not other_tw:
            tab = target.clone_tab(other_tab)
        else:
            tab = target.open_file(path)

        self._apply_tab_settings(tab)
        if tab and tab.provider:
            self.lang_label.setText(tab.provider.get_name())
            self.output.run_btn.setEnabled(True)
            self._connect_lsp(tab, path)
        self._connect_cursor(tab)
        self._update_status_bar_for_tab(tab)
        return tab

    def _connect_lsp(self, tab, file_path: Path):
        """Verbindet den Tab mit dem LSP-Server für die Sprache."""
        if not tab or not tab.provider or not file_path:
            return
        lang_name = tab.provider.get_name()
        client = self._lsp_manager.get_client(lang_name)
        if not client:
            return

        uri = file_path.resolve().as_uri()
        lang_id = lang_name.lower()
        text = tab.editor.toPlainText()
        if getattr(tab, "_lsp_client", None) is client and getattr(tab, "_lsp_uri", None) == uri:
            return

        self._lsp_tabs_by_uri[uri] = tab
        client.on_diagnostics = self._dispatch_lsp_diagnostics

        old_text_changed = getattr(tab, "_lsp_text_changed_slot", None)
        if old_text_changed:
            try:
                tab.editor.textChanged.disconnect(old_text_changed)
            except (TypeError, RuntimeError):
                pass

        old_completion_slot = getattr(tab, "_lsp_completion_slot", None)
        if old_completion_slot:
            try:
                tab.editor.completionRequested.disconnect(old_completion_slot)
            except (TypeError, RuntimeError):
                pass

        tab._lsp_uri = uri
        tab._lsp_client = client
        tab._lsp_version = 1

        client.did_open(uri, lang_id, text)

        def on_text_changed():
            tab._lsp_version += 1
            client.did_change(uri, tab.editor.toPlainText(), tab._lsp_version)
        tab.editor.textChanged.connect(on_text_changed)
        tab._lsp_text_changed_slot = on_text_changed

        def on_completion_requested(line, character, _prefix):
            self._request_lsp_completion(tab, line, character)
        tab.editor.completionRequested.connect(on_completion_requested)
        tab._lsp_completion_slot = on_completion_requested

    def _dispatch_lsp_diagnostics(self, params):
        """Leitet LSP-Diagnostics aus dem Reader-Thread in den UI-Thread."""
        tab = self._lsp_tabs_by_uri.get(params.get("uri"))
        if not tab:
            return
        severity_map = {1: "error", 2: "warning", 3: "info", 4: "hint"}
        errors = []
        for diagnostic in params.get("diagnostics", []):
            start = diagnostic.get("range", {}).get("start", {})
            errors.append({
                "line": start.get("line", 0) + 1,
                "col": start.get("character", 0) + 1,
                "message": diagnostic.get("message", ""),
                "severity": severity_map.get(diagnostic.get("severity", 1), "error"),
                "source": "LSP",
            })
        self.lspDiagnosticsReceived.emit(tab, errors)

    def _request_lsp_completion(self, tab, line: int, character: int):
        if not self._is_live_tab(tab):
            return
        client = getattr(tab, "_lsp_client", None)
        uri = getattr(tab, "_lsp_uri", None)
        if not client or not uri:
            return

        def on_completion(result):
            words = self._extract_lsp_completion_words(result)
            if words:
                self.lspCompletionsReceived.emit(tab, words)

        client.request_completion(uri, line, character, callback=on_completion)

    def _apply_lsp_diagnostics(self, tab, errors):
        if self._is_live_tab(tab):
            tab._lsp_errors = list(errors or [])
            self._refresh_problems(tab)

    def _apply_linter_results(self, tab, file_path, token, errors):
        """Apply an asynchronous save-triggered linter result if still current."""
        if not self._is_live_tab(tab):
            return
        current_path = getattr(tab, "file_path", None)
        if not current_path or Path(current_path).resolve() != Path(file_path).resolve():
            return
        if token != getattr(tab, "_linter_token", token):
            return
        tab._lint_errors = list(errors or [])
        self._refresh_problems(tab)

    def _refresh_problems(self, changed_tab=None):
        """Refresh gutter markers and the combined Problems panel."""
        all_problems = []
        live_tabs = []
        for tw in (self.tab_widget, self.split_tab_widget):
            for idx in range(tw.count()):
                tab = tw.tabs.get(idx)
                if not tab or tab in live_tabs:
                    continue
                live_tabs.append(tab)
                problems = []
                file_path = str(getattr(tab, "file_path", "") or "")
                for item in list(getattr(tab, "_lsp_errors", []) or []) + list(getattr(tab, "_lint_errors", []) or []):
                    normalized = dict(item)
                    normalized.setdefault("path", file_path)
                    normalized.setdefault("source", "LSP")
                    normalized["tab"] = tab
                    problems.append(normalized)
                tab.editor.set_linter_errors(problems)
                self._problems_by_tab[tab] = problems
                all_problems.extend(problems)
        for tab in list(self._problems_by_tab):
            if tab not in live_tabs:
                self._problems_by_tab.pop(tab, None)
        if hasattr(self, "problems"):
            self.problems.set_problems(all_problems)

    def _activate_problem(self, problem):
        """Select the owning tab and place the cursor at a problem."""
        tab = problem.get("tab") if isinstance(problem, dict) else None
        if not tab or not self._is_live_tab(tab):
            path = problem.get("path") if isinstance(problem, dict) else None
            for tw in (self.tab_widget, self.split_tab_widget):
                tab = next((
                    tw.tabs.get(idx)
                    for idx in range(tw.count())
                    if tw.tabs.get(idx)
                    and str(tw.tabs[idx].file_path or "") == str(path or "")
                ), None)
                if tab:
                    break
        if not tab:
            return
        for tw in (self.tab_widget, self.split_tab_widget):
            for idx in range(tw.count()):
                if tw.tabs.get(idx) is tab:
                    tw.setCurrentIndex(idx)
                    self._active_tab_widget = tw
                    break
        line = max(1, int(problem.get("line", 1)))
        col = max(1, int(problem.get("col", 1)))
        block = tab.editor.document().findBlockByNumber(line - 1)
        if not block.isValid():
            return
        cursor = tab.editor.textCursor()
        cursor.setPosition(block.position() + min(col - 1, len(block.text())))
        tab.editor.setTextCursor(cursor)
        tab.editor.centerCursor()
        tab.editor.setFocus()

    def _apply_lsp_completions(self, tab, words):
        if not self._is_live_tab(tab):
            return
        tab.editor.set_completer_words(words)
        completer = tab.editor.completer
        prefix = tab.editor.text_under_cursor()
        if not completer or len(prefix) < 2 or not tab.editor.hasFocus():
            return
        completer.setCompletionPrefix(prefix)
        completer.popup().setCurrentIndex(completer.completionModel().index(0, 0))
        cursor_rect = tab.editor.cursorRect()
        cursor_rect.setWidth(
            completer.popup().sizeHintForColumn(0) +
            completer.popup().verticalScrollBar().sizeHint().width()
        )
        tab.editor.completer.complete(cursor_rect)

    def _extract_lsp_completion_words(self, result):
        if not result:
            return []
        items = result.get("items", []) if isinstance(result, dict) else result
        if not isinstance(items, list):
            return []
        words = []
        for item in items:
            if isinstance(item, dict):
                label = item.get("label")
            else:
                label = str(item)
            if label:
                words.append(label)
        return sorted(set(words))

    def _is_live_tab(self, tab) -> bool:
        in_primary = any(self.tab_widget.tabs.get(idx) is tab for idx in range(self.tab_widget.count()))
        in_split = any(self.split_tab_widget.tabs.get(idx) is tab for idx in range(self.split_tab_widget.count()))
        return in_primary or in_split

    def save_file(self):
        tab = self.get_active_tab()
        if not tab:
            return
        assigned_new_path = False
        original_file_path = tab.file_path
        original_provider = tab.provider
        original_lang_label = self.lang_label.text()
        original_run_enabled = self.output.run_btn.isEnabled()
        if not tab.file_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Speichern unter", "",
                "Alle Dateien (*);;Python (*.py);;JavaScript (*.js);;C++ (*.cpp)"
            )
            if path:
                assigned_new_path = True
                tab.file_path = Path(path)
                # Provider setzen basierend auf neuer Extension
                ext = tab.file_path.suffix.lstrip('.')
                provider = get_provider_for_extension(ext)
                if provider:
                    tab.provider = provider
                    if tab.highlighter:
                        tab.highlighter.set_provider(provider)
                    tab.editor.set_provider(provider)
                    self.lang_label.setText(provider.get_name())
            else:
                return
        if not tab.save():
            if assigned_new_path:
                tab.file_path = original_file_path
                tab.provider = original_provider
                if tab.highlighter:
                    tab.highlighter.set_provider(original_provider)
                tab.editor.set_provider(original_provider)
                self.lang_label.setText(original_lang_label)
                self.output.run_btn.setEnabled(original_run_enabled)
            return
        self.get_active_tab_widget()._update_tab_title(tab)
        other_tw = self.split_tab_widget if self.get_active_tab_widget() is self.tab_widget else self.tab_widget
        for idx in range(other_tw.count()):
            other_t = other_tw.tabs.get(idx)
            if other_t and (other_t.file_path == tab.file_path or other_t.editor.document() is tab.editor.document()):
                other_tw._update_tab_title(other_t)
        self.setWindowTitle(format_window_title(tab.file_path))
        self.output.run_btn.setEnabled(bool(tab.provider))
        if tab.file_path and tab.provider and not getattr(tab, "_lsp_client", None):
            self._connect_lsp(tab, tab.file_path)
        self._after_tab_saved(tab)

    def _after_tab_saved(self, tab):
        """Notify LSP and run the optional linter after a successful save."""
        if not tab or not tab.file_path:
            return
        if tab.provider and not getattr(tab, "_lsp_client", None):
            self._connect_lsp(tab, tab.file_path)
        if getattr(tab, "_lsp_client", None):
            tab._lsp_client.did_save(tab._lsp_uri, tab.editor.toPlainText())
        if tab.provider:
            tab._linter_token = self._linter_manager.lint(
                tab, tab.provider.get_name(), tab.file_path
            )
        else:
            tab._lint_errors = []
            self._refresh_problems(tab)

    # ---- Bearbeiten-Aktionen ----

    def _undo(self):
        tab = self.get_active_tab()
        if tab:
            tab.editor.undo()

    def _redo(self):
        tab = self.get_active_tab()
        if tab:
            tab.editor.redo()

    def _open_find_replace_dialog(self, mode: str = "find"):
        from ui.search_dialog import FindReplaceDialog
        if self._find_dialog is None:
            self._find_dialog = FindReplaceDialog(self, initial_mode=mode)
        else:
            self._find_dialog.set_mode(mode)
        self._find_dialog.show()
        self._find_dialog.raise_()
        self._find_dialog.activateWindow()

    def _find(self):
        self._open_find_replace_dialog("find")

    def _replace(self):
        self._open_find_replace_dialog("replace")

    def _find_next(self):
        if self._find_dialog and self._find_dialog.isVisible():
            self._find_dialog.find_next()
        else:
            self._open_find_replace_dialog("find")

    def _find_prev(self):
        if self._find_dialog and self._find_dialog.isVisible():
            self._find_dialog.find_prev()
        else:
            self._open_find_replace_dialog("find")

    def _goto_line(self):
        from PySide6.QtWidgets import QInputDialog
        tab = self.get_active_tab()
        if not tab or not tab.editor:
            return
        line, ok = QInputDialog.getInt(
            self, "Gehe zu Zeile", "Zeile:", 1, 1, max(1, tab.editor.blockCount())
        )
        if ok:
            block = tab.editor.document().findBlockByNumber(line - 1)
            if block.isValid():
                cursor = tab.editor.textCursor()
                cursor.setPosition(block.position())
                tab.editor.setTextCursor(cursor)
                tab.editor.centerCursor()
                tab.editor.setFocus()

    def show_find_in_files(
        self,
        initial_query: Optional[str] = None,
        target_path: Optional[Path] = None,
    ):
        """Öffnet den Dialog für die datei- und projektweite Textsuche (Find in Files)."""
        from ui.find_in_files_dialog import FindInFilesDialog

        if initial_query is None:
            tab = self.get_active_tab()
            if tab and tab.editor:
                selected = tab.editor.textCursor().selectedText()
                if selected:
                    initial_query = selected

        if self._find_in_files_dialog is None:
            self._find_in_files_dialog = FindInFilesDialog(self)

        self._find_in_files_dialog.open_for_search(
            initial_query=initial_query,
            target_path=target_path,
        )

    def open_path_at(
        self,
        file_path: Path | str,
        line: int = 1,
        column: int = 1,
        length: int = 0,
    ):
        """Öffnet eine Datei und setzt Cursor und Markierung auf Zeile, Spalte und Länge."""
        from PySide6.QtGui import QTextCursor

        tab = self.open_path(Path(file_path))
        if tab and tab.editor:
            doc = tab.editor.document()
            block = doc.findBlockByNumber(max(0, line - 1))
            if block.isValid():
                cursor = tab.editor.textCursor()
                start_pos = block.position() + max(0, column - 1)
                cursor.setPosition(start_pos)
                if length > 0:
                    cursor.setPosition(start_pos + length, QTextCursor.MoveMode.KeepAnchor)
                tab.editor.setTextCursor(cursor)
                tab.editor.centerCursor()
                tab.editor.setFocus()

    def _toggle_comment(self):
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.toggle_comment()

    def _indent(self):
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.indent_selection()

    def _dedent(self):
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.unindent_selection()

    def _toggle_fold_current(self):
        """Schaltet die Faltung an der aktuellen Cursor-Zeile um."""
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.toggle_fold_at_cursor()

    def _fold_all(self):
        """Klappt alle Blöcke im aktuellen Dokument ein."""
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.fold_all()

    def _unfold_all(self):
        """Klappt alle Blöcke im aktuellen Dokument aus."""
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.unfold_all()

    def _add_cursor_above(self):
        """Fügt einen weiteren Cursor in der Zeile darüber ein."""
        tab = self.get_active_tab()
        if tab and tab.editor and hasattr(tab.editor, "multi_cursor_manager"):
            tab.editor.multi_cursor_manager.add_cursor_above()

    def _add_cursor_below(self):
        """Fügt einen weiteren Cursor in der Zeile darunter ein."""
        tab = self.get_active_tab()
        if tab and tab.editor and hasattr(tab.editor, "multi_cursor_manager"):
            tab.editor.multi_cursor_manager.add_cursor_below()

    def _select_all_occurrences(self):
        """Markiert alle Vorkommen des aktuellen Wortes oder der Auswahl mit Multi-Cursorn."""
        tab = self.get_active_tab()
        if tab and tab.editor and hasattr(tab.editor, "multi_cursor_manager"):
            count = tab.editor.multi_cursor_manager.select_all_occurrences()
            if count:
                self.statusBar().showMessage(f"{count} Vorkommen markiert (Multi-Cursor)", 3000)

    def _add_next_occurrence(self):
        """Fügt das nächste Vorkommen zur Mehrfachauswahl hinzu."""
        tab = self.get_active_tab()
        if tab and tab.editor and hasattr(tab.editor, "multi_cursor_manager"):
            if tab.editor.multi_cursor_manager.add_next_occurrence():
                self.statusBar().showMessage(
                    f"{tab.editor.multi_cursor_manager.cursor_count()} Cursor aktiv", 3000
                )

    def _clear_multi_cursors(self):
        """Hebt alle zusätzlichen Cursor auf und kehrt zum Einzelcursor zurück."""
        tab = self.get_active_tab()
        if tab and tab.editor and hasattr(tab.editor, "multi_cursor_manager"):
            tab.editor.multi_cursor_manager.clear()
            self.statusBar().showMessage("Mehrfachcursor aufgehoben", 2000)

    def open_plugins_dialog(self):
        """Öffnet den Dialog zur Verwaltung von Plugins und Sprachen."""
        dialog = PluginsDialog(self._plugin_manager, self)
        dialog.exec()

    def open_shortcuts_dialog(self):
        """Öffnet die Tastenkürzel-Übersicht."""
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def _about_dialog(self):
        """Zeigt Informationen über CodeBox an."""
        QMessageBox.about(
            self,
            "Über CodeBox",
            f"<b>CodeBox IDE v{APP_VERSION}</b><br><br>"
            "Eine moderne, leichtgewichtige Multi-Language IDE mit Unterstützung für "
            "Python, JavaScript, TypeScript, C/C++, Rust, Go, Java und erweiterbare Sprach-Plugins.<br><br>"
            "Features: LSP-Unterstützung, Linter, Terminal, Projektbaum, Minimap und Plugin-System."
        )

    def open_settings_dialog(self):
        """Öffnet den Einstellungsdialog und übernimmt geänderte Optionen."""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._apply_settings()

    def _apply_settings(self):
        """Wendet geladene oder geänderte Einstellungen auf Hauptfenster, Theme und Tabs an."""
        if not hasattr(self, '_settings') or not self._settings:
            return

        font_family = self._settings.get("font_family", "Consolas")
        font_size = int(self._settings.get("font_size", 10))
        tab_size = int(self._settings.get("tab_size", 4))
        theme = self._settings.get("theme", "dark")
        vim_mode = bool(self._settings.get("vim_mode", False))

        if hasattr(self, "act_vim_mode"):
            self.act_vim_mode.setChecked(vim_mode)

        # Theme anwenden
        from features.theme_manager import apply_theme
        apply_theme(QApplication.instance(), theme)

        # Editor-Einstellungen auf alle offenen Tabs anwenden (primär & geteilt)
        for tw in (self.tab_widget, self.split_tab_widget):
            for idx in range(tw.count()):
                tab = tw.tabs.get(idx)
                if tab and tab.editor:
                    tab.editor.apply_editor_settings(font_family, font_size, tab_size)
                    tab.editor.set_minimap_visible(
                        bool(self._settings.get("show_minimap", True))
                    )
                    tab.editor.set_vim_mode_enabled(vim_mode)

        self._update_vim_status_label(self.get_active_tab())

    def toggle_vim_mode(self, checked: Optional[bool] = None):
        """Schaltet den modalen Vim-Modus an allen offenen Editoren ein oder aus."""
        if checked is None:
            new_state = not bool(self._settings.get("vim_mode", False))
        else:
            new_state = bool(checked)
        self._settings["vim_mode"] = new_state
        from config import save_settings
        save_settings(self._settings)

        if hasattr(self, "act_vim_mode"):
            self.act_vim_mode.setChecked(new_state)

        for tw in (self.tab_widget, self.split_tab_widget):
            for idx in range(tw.count()):
                tab = tw.tabs.get(idx)
                if tab and tab.editor and hasattr(tab.editor, "set_vim_mode_enabled"):
                    tab.editor.set_vim_mode_enabled(new_state)

        active_tab = self.get_active_tab()
        self._update_vim_status_label(active_tab)
        msg = "Vim-Modus aktiviert" if new_state else "Vim-Modus deaktiviert"
        self.status_bar.showMessage(msg, 3000)

    # ---- Ausführen ----

    def run_current(self):
        tab = self.get_active_tab()
        if not tab or not tab.file_path:
            QMessageBox.warning(self, "Ausführen", "Bitte zuerst eine Datei speichern.")
            return
        # Automatisch speichern vor dem Ausführen
        if not tab.save():
            return
        self._after_tab_saved(tab)
        if tab.provider:
            cmd = tab.provider.get_run_command(str(tab.file_path))
            self.output.run_command(cmd)
        else:
            QMessageBox.warning(self, "Ausführen",
                                "Keine Sprachunterstützung für diese Datei.")

    def _stop_run(self):
        self.output.stop_process()

    # ---- Events ----

    def _on_file_changed(self, file_path):
        tab = self.get_active_tab()
        if file_path:
            self.setWindowTitle(format_window_title(file_path))
            if tab and tab.provider:
                self.lang_label.setText(tab.provider.get_name())
                self.output.run_btn.setEnabled(True)
                self._connect_lsp(tab, file_path)
            else:
                self.lang_label.setText("Keine Sprache")
                self.output.run_btn.setEnabled(False)
            self._connect_cursor(tab)
            # Ermitteln, ob die Datei zu einem bestehenden Workspace-Ordner gehört
            owning_folder = self.workspace.find_folder_for_file(file_path)
            if owning_folder:
                if self.workspace.active_folder != owning_folder:
                    self.workspace.set_active_folder(owning_folder)
                target_dir = owning_folder
            else:
                project_dir = file_path.parent
                if self.workspace.is_empty:
                    self.workspace.add_folder(project_dir, make_active=True)
                elif self.project_view._root_path != project_dir:
                    self.project_view.set_root(str(project_dir))
                target_dir = project_dir
            self.terminal.set_working_dir(str(target_dir))
        else:
            self.setWindowTitle(format_window_title())
            self.lang_label.setText("Keine Sprache")
            self.output.run_btn.setEnabled(False)
            if tab:
                self._connect_cursor(tab)

    def _on_language_changed(self, lang_name):
        if lang_name == "(Auto)":
            return
        tab = self.get_active_tab()
        if tab:
            provider = get_provider_by_name(lang_name)
            if provider:
                tab.provider = provider
                if tab.highlighter:
                    tab.highlighter.set_provider(provider)
                tab.editor.set_provider(provider)
                self.lang_label.setText(provider.get_name())
                self.output.run_btn.setEnabled(True)
                if tab.file_path:
                    self._connect_lsp(tab, tab.file_path)

    def _connect_cursor(self, tab):
        if tab:
            old_slot = getattr(tab, "_cursor_slot", None)
            if old_slot is not None:
                try:
                    tab.editor.cursorPositionInfo.disconnect(old_slot)
                except (TypeError, RuntimeError):
                    pass

            def _slot(line, col):
                extra = ""
                if hasattr(tab.editor, "multi_cursor_manager") and tab.editor.multi_cursor_manager.has_extra_cursors():
                    extra = f" ({tab.editor.multi_cursor_manager.cursor_count()} Cursor)"
                self.pos_label.setText(f"Zeile {line}, Spalte {col}{extra}")

            tab._cursor_slot = _slot
            tab.editor.cursorPositionInfo.connect(_slot)

            if hasattr(tab.editor, "vim_engine"):
                old_vmode = getattr(tab, "_vim_mode_slot", None)
                if old_vmode is not None:
                    try:
                        tab.editor.vim_engine.modeChanged.disconnect(old_vmode)
                    except (TypeError, RuntimeError):
                        pass
                old_vcmd = getattr(tab, "_vim_cmd_slot", None)
                if old_vcmd is not None:
                    try:
                        tab.editor.vim_engine.commandBufferChanged.disconnect(old_vcmd)
                    except (TypeError, RuntimeError):
                        pass

                def _vim_slot(*_args):
                    if self.get_active_tab() is tab:
                        self._update_vim_status_label(tab)

                tab._vim_mode_slot = _vim_slot
                tab._vim_cmd_slot = _vim_slot
                tab.editor.vim_engine.modeChanged.connect(_vim_slot)
                tab.editor.vim_engine.commandBufferChanged.connect(_vim_slot)

    def _open_file_from_project(self, file_path):
        """Öffnet eine Datei aus dem Projektbaum."""
        self.open_path(file_path)

    def _toggle_project_view(self):
        """Blendet den Projektbaum ein/aus."""
        was_visible = self.project_view.isVisible()
        self.project_view.setVisible(not was_visible)
        if was_visible:
            self._focus_active_editor()

    def _focus_active_editor(self):
        """Setzt den Tastaturfokus auf den aktiven Editor zurück."""
        tab = self.get_active_tab()
        if tab and tab.editor:
            tab.editor.setFocus()

    def _toggle_terminal(self):
        """Blendet das untere Panel ein/aus und wechselt zum Terminal-Tab."""
        if self.bottom_tabs.isVisible() and self.bottom_tabs.currentWidget() == self.terminal:
            self.bottom_tabs.hide()
        else:
            self.bottom_tabs.show()
            self.bottom_tabs.setCurrentWidget(self.terminal)
            self.terminal.input.setFocus()

    def show_diff(self, file_path: Optional[Path] = None, staged: bool = False):
        """Öffnet den Git Diff-Viewer für das Projekt oder eine bestimmte Datei."""
        from ui.diff_viewer import DiffViewerDialog
        repo_root = getattr(self.project_view, "_root_path", None)
        if not repo_root:
            tab = self.get_active_tab()
            if tab and tab.file_path:
                repo_root = tab.file_path.parent
            else:
                repo_root = Path.cwd()

        dialog = DiffViewerDialog(self, repo_root=Path(repo_root), initial_file=file_path, staged=staged)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def show_git_commit(self, file_path: Optional[Path] = None):
        """Öffnet den Git-Commit-Dialog für das Projekt oder eine bestimmte Datei."""
        from ui.git_commit_dialog import GitCommitDialog
        repo_root = getattr(self.project_view, "_root_path", None)
        if not repo_root:
            tab = self.get_active_tab()
            if tab and tab.file_path:
                repo_root = tab.file_path.parent
            else:
                repo_root = Path.cwd()

        dialog = GitCommitDialog(
            repo_root=Path(repo_root),
            initial_file=file_path,
            parent=self,
            main_window=self,
        )
        dialog.status_changed.connect(self.project_view._refresh)
        dialog.committed.connect(lambda msg: self.project_view._refresh())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def show_quick_open(self):
        """Öffnet die Schnellauswahl für Projektdateien (Quick Open, Ctrl+P)."""
        dlg = CommandPaletteDialog(self, mode="files")
        dlg.exec()
        return dlg

    def show_command_palette(self):
        """Öffnet die Befehlspalette für alle Aktionen (Ctrl+Shift+P)."""
        dlg = CommandPaletteDialog(self, mode="commands")
        dlg.exec()
        return dlg

    def _on_providers_updated(self):
        """Aktualisiert die Sprachauswahl in der Toolbar bei Registry-Änderungen."""
        if not hasattr(self, "lang_combo"):
            return
        current = self.lang_combo.currentText()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        self.lang_combo.addItem("(Auto)")
        for p in get_all_providers():
            self.lang_combo.addItem(p.get_name())
        idx = self.lang_combo.findText(current)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        else:
            self.lang_combo.setCurrentIndex(0)
        self.lang_combo.blockSignals(False)

    def closeEvent(self, event):
        # Listener entfernen
        remove_provider_listener(self._on_providers_updated)
        # Alle Tabs auf ungespeicherte Änderungen prüfen (primär & geteilt)
        unsaved = []
        seen_docs = set()
        for tw in (self.tab_widget, self.split_tab_widget):
            for idx in range(tw.count()):
                tab = tw.tabs.get(idx)
                if tab and tab.is_modified:
                    doc = tab.editor.document()
                    if doc not in seen_docs:
                        seen_docs.add(doc)
                        unsaved.append(tw.tabText(idx).lstrip('*'))
        if unsaved:
            names = "\n".join(f"  - {n}" for n in unsaved)
            reply = QMessageBox.question(
                self, "Beenden",
                f"Es gibt ungespeicherte Änderungen in:\n{names}\n\nTrotzdem beenden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        # Terminal-Prozess sauber beenden
        if hasattr(self, 'terminal'):
            self.terminal.close()
        # Suchen-Dialog schließen
        if getattr(self, "_find_dialog", None):
            self._find_dialog.close()
        # LSP-Server stoppen
        self._linter_manager.stop_all()
        self._lsp_manager.stop_all()
        event.accept()
