#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Palette & Quick-Open Datei-Finder für CodeBox.

Unterstützt zwei Modi:
- Quick-Open (Ctrl+P): Schnelles Suchen und Öffnen von Dateien im aktuellen Projekt.
- Befehlspalette (Ctrl+Shift+P oder führendes '>'): Durchsuchen und Ausführen
  aller Menü- und Editor-Befehle inklusive Shortcuts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QWidget,
    QMenu,
)

if TYPE_CHECKING:
    from ui.main_window import MainWindow

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
    ".vs",
    ".eggs",
}

FILE_ICONS = {
    ".py": "🐍",
    ".js": "📜",
    ".ts": "📘",
    ".json": "📋",
    ".html": "🌐",
    ".css": "🎨",
    ".md": "📝",
    ".txt": "📄",
    ".ico": "🖼️",
    ".png": "🖼️",
    ".svg": "🎨",
    ".toml": "⚙️",
    ".yaml": "⚙️",
    ".yml": "⚙️",
    ".sh": "⚡",
    ".bat": "⚡",
}


class PaletteItemWidget(QWidget):
    """Benutzerdefinierte Darstellung für Treffer in der Befehlspalette."""

    def __init__(
        self,
        primary_text: str,
        secondary_text: str = "",
        icon_str: str = "📄",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Icon / Emoji
        self.icon_label = QLabel(icon_str)
        self.icon_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.icon_label)

        # Haupttext (Dateiname oder Befehlsname)
        self.primary_label = QLabel(primary_text)
        self.primary_label.setStyleSheet(
            "font-weight: bold; color: #ffffff; font-size: 12px;"
        )
        layout.addWidget(self.primary_label)

        layout.addStretch()

        # Sekundärtext (Pfad oder Tastenkürzel)
        if secondary_text:
            self.secondary_label = QLabel(secondary_text)
            self.secondary_label.setStyleSheet(
                "color: #888888; font-size: 11px; font-family: Consolas, monospace;"
            )
            layout.addWidget(self.secondary_label)


class CommandPaletteDialog(QDialog):
    """Zentrale Befehls- und Schnellauswahlpalette für CodeBox."""

    commandTriggered = Signal(object)
    fileSelected = Signal(object)

    def __init__(
        self,
        main_window: "MainWindow",
        mode: str = "files",  # "files" oder "commands"
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.current_mode = mode  # "files" | "commands"

        self._all_files: List[Tuple[str, Path]] = []  # (rel_path_str, abs_path)
        self._all_commands: List[Tuple[str, str, str, Callable[[], None]]] = []
        # (category, title, shortcut, callback)

        self._setup_window_properties()
        self._setup_ui()
        self._collect_commands()
        self._collect_files()

        self.set_mode(mode)

    def _setup_window_properties(self):
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedWidth(640)
        self.setMaximumHeight(420)
        self.setAccessibleName("Befehlspalette und Schnellauswahl")
        self.setAccessibleDescription(
            "Ermöglicht schnelles Öffnen von Projektdateien und Ausführen von Befehlen"
        )

        # Styling im CodeBox Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                border: 1px solid #007acc;
                border-radius: 6px;
            }
            QLineEdit {
                background-color: #252526;
                color: #f1f1f1;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 13px;
                selection-background-color: #094771;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                outline: none;
                color: #cccccc;
            }
            QListWidget::item {
                border-radius: 3px;
                padding: 2px;
                margin: 1px 4px;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QListWidget::item:selected {
                background-color: #04395e;
                color: #ffffff;
            }
            QLabel#footer_hint {
                color: #777777;
                font-size: 11px;
                padding: 4px 8px;
            }
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Suchfeld
        self.search_input = QLineEdit()
        self.search_input.setObjectName("palette_search_input")
        self.search_input.setAccessibleName("Paletten-Suchfeld")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)

        # Ergebnisliste
        self.results_list = QListWidget()
        self.results_list.setObjectName("palette_results_list")
        self.results_list.setAccessibleName("Suchergebnisse")
        self.results_list.itemActivated.connect(self._on_item_activated)
        self.results_list.itemClicked.connect(self._on_item_activated)
        layout.addWidget(self.results_list)

        # Fußzeile mit Hinweisen
        self.footer_label = QLabel()
        self.footer_label.setObjectName("footer_hint")
        layout.addWidget(self.footer_label)

    def set_mode(self, mode: str):
        """Wechselt zwischen 'files' und 'commands'."""
        self.current_mode = mode
        if mode == "commands":
            if not self.search_input.text().startswith(">"):
                self.search_input.setText(">")
            self.search_input.setPlaceholderText("> Befehl eingeben... (Esc zum Schließen)")
            self.footer_label.setText("Enter zum Ausführen | Pfeiltasten zur Navigation | Esc zum Schließen")
        else:
            if self.search_input.text().startswith(">"):
                self.search_input.setText("")
            self.search_input.setPlaceholderText("Datei suchen... (Tippe '>' für Befehle, Esc zum Schließen)")
            self.footer_label.setText("Enter zum Öffnen | Pfeiltasten zur Navigation | Tippe '>' für Befehle")

        self.search_input.setFocus()
        self._update_results()

    def _on_search_text_changed(self, text: str):
        # Wenn der Nutzer '>' tippt, automatischer Wechsel in den Befehlsmodus
        if text.startswith(">") and self.current_mode != "commands":
            self.current_mode = "commands"
            self.search_input.setPlaceholderText("> Befehl eingeben... (Esc zum Schließen)")
            self.footer_label.setText("Enter zum Ausführen | Pfeiltasten zur Navigation | Esc zum Schließen")
        elif not text.startswith(">") and self.current_mode == "commands":
            self.current_mode = "files"
            self.search_input.setPlaceholderText("Datei suchen... (Tippe '>' für Befehle, Esc zum Schließen)")
            self.footer_label.setText("Enter zum Öffnen | Pfeiltasten zur Navigation | Tippe '>' für Befehle")

        self._update_results()

    def _collect_files(self):
        """Indexiert die Dateien des aktuellen Projektordners oder Arbeitsbereichs."""
        self._all_files.clear()

        # Multi-Root Workspace Support
        if (
            hasattr(self.main_window, "workspace")
            and self.main_window.workspace
            and not self.main_window.workspace.is_empty
        ):
            ws = self.main_window.workspace
            is_multi = ws.is_multi_root
            self.root_dir = ws.active_folder or (ws.folders[0].path if ws.folders else Path.cwd())
            results = ws.collect_all_files(max_files=3000, skip_dirs=SKIP_DIRS)
            for rel_str, abs_p, folder_name in results:
                display_str = f"[{folder_name}] {rel_str}" if is_multi else rel_str
                self._all_files.append((display_str, abs_p))
            return

        root_dir = None
        if hasattr(self.main_window, "project_view") and self.main_window.project_view:
            pv_root = getattr(self.main_window.project_view, "_root_path", None)
            if pv_root and Path(pv_root).is_dir():
                root_dir = Path(pv_root)

        if not root_dir:
            active_tab = self.main_window.get_active_tab_widget().current_tab()
            if active_tab and active_tab.file_path and active_tab.file_path.parent.is_dir():
                root_dir = active_tab.file_path.parent
            else:
                root_dir = Path.cwd()

        self.root_dir = root_dir.resolve()

        collected = []
        max_files = 3000
        for root, dirs, files in os.walk(self.root_dir):
            # Ignoriere Standard-Verzeichnisse
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for f in files:
                if f.startswith(".") and f != ".gitignore":
                    continue
                abs_p = Path(root) / f
                try:
                    rel_p = abs_p.relative_to(self.root_dir)
                    collected.append((str(rel_p).replace("\\", "/"), abs_p))
                except ValueError:
                    collected.append((f, abs_p))

                if len(collected) >= max_files:
                    break
            if len(collected) >= max_files:
                break

        self._all_files = collected

    def _collect_commands(self):
        """Sammelt alle Aktionen aus der Menüleiste von MainWindow."""
        self._all_commands.clear()
        menubar = self.main_window.menuBar()

        for action in menubar.actions():
            menu = action.menu()
            if menu:
                menu_title = menu.title().replace("&", "")
                self._harvest_menu_actions(menu, menu_title)

        # Ergänze Schnellaktionen
        quick_actions = [
            ("Ansicht", "Git-Diff-Viewer öffnen", "Ctrl+Alt+D", lambda: self.main_window.show_diff()),
            ("Ansicht", "Projektbaum ein-/ausblenden", "Ctrl+B", self.main_window._toggle_project_view),
            ("Ansicht", "Terminal ein-/ausblenden", "Ctrl+`", self.main_window._toggle_terminal),
            ("Datei", "Datei schnell öffnen (Quick Open)", "Ctrl+P", self.main_window.show_quick_open),
            ("Bearbeiten", "In Dateien suchen (Projektweite Textsuche)", "Ctrl+Shift+F", self.main_window.show_find_in_files),
            ("Bearbeiten", "Zur Definition springen (Go to Definition)", "F12", self.main_window.goto_definition),
            ("Bearbeiten", "Alle Referenzen suchen (Find References)", "Shift+F12", self.main_window.find_references),
            ("Bearbeiten", "Befehlspalette öffnen", "Ctrl+Shift+P", self.main_window.show_command_palette),
            ("Bearbeiten", "Plugins & Sprachen verwalten", "", self.main_window.open_plugins_dialog),
            ("Bearbeiten", "Einstellungen", "Ctrl+,", self.main_window.open_settings_dialog),
        ]
        for cat, title, sc, cb in quick_actions:
            if not any(c[1] == title for c in self._all_commands):
                self._all_commands.append((cat, title, sc, cb))

    def _harvest_menu_actions(self, menu: QMenu, category: str):
        for act in menu.actions():
            if act.isSeparator():
                continue
            sub = act.menu()
            if sub:
                sub_title = f"{category} > {sub.title().replace('&', '')}"
                self._harvest_menu_actions(sub, sub_title)
            else:
                title = act.text().replace("&", "")
                if not title:
                    continue
                shortcut = act.shortcut().toString() if not act.shortcut().isEmpty() else ""
                cb = act.trigger
                self._all_commands.append((category, title, shortcut, cb))

    def _update_results(self):
        """Aktualisiert die angezeigten Ergebnisse anhand des Suchbegriffs."""
        self.results_list.clear()
        query = self.search_input.text().strip()

        if self.current_mode == "commands":
            clean_query = query[1:].strip().lower() if query.startswith(">") else query.lower()
            matched = []
            for cat, title, shortcut, cb in self._all_commands:
                full_text = f"{cat} {title} {shortcut}".lower()
                if not clean_query or clean_query in full_text:
                    # Scoring
                    score = 0
                    if clean_query:
                        if title.lower().startswith(clean_query):
                            score += 100
                        elif clean_query in title.lower():
                            score += 50
                        if clean_query in cat.lower():
                            score += 20
                    matched.append((score, cat, title, shortcut, cb))

            matched.sort(key=lambda x: (-x[0], x[1], x[2]))

            for _, cat, title, shortcut, cb in matched[:50]:
                item = QListWidgetItem(self.results_list)
                item.setData(Qt.ItemDataRole.UserRole, ("command", cb))
                widget = PaletteItemWidget(
                    primary_text=f"{cat}: {title}",
                    secondary_text=shortcut,
                    icon_str="⚡",
                )
                item.setSizeHint(widget.sizeHint())
                self.results_list.setItemWidget(item, widget)

        else:
            clean_query = query.lower()
            matched = []
            for rel_str, abs_path in self._all_files:
                filename = abs_path.name.lower()
                rel_lower = rel_str.lower()
                if not clean_query or clean_query in rel_lower:
                    score = 0
                    if clean_query:
                        if filename.startswith(clean_query):
                            score += 100
                        elif clean_query in filename:
                            score += 50
                        else:
                            score += 10
                    matched.append((score, rel_str, abs_path))

            matched.sort(key=lambda x: (-x[0], len(x[1]), x[1]))

            for _, rel_str, abs_path in matched[:60]:
                item = QListWidgetItem(self.results_list)
                item.setData(Qt.ItemDataRole.UserRole, ("file", abs_path))
                ext = abs_path.suffix.lower()
                icon_str = FILE_ICONS.get(ext, "📄")
                widget = PaletteItemWidget(
                    primary_text=abs_path.name,
                    secondary_text=rel_str,
                    icon_str=icon_str,
                )
                item.setSizeHint(widget.sizeHint())
                self.results_list.setItemWidget(item, widget)

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def _on_item_activated(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, payload = data
        self.accept()

        if item_type == "file":
            self.fileSelected.emit(payload)
            self.main_window.open_path(payload)
        elif item_type == "command":
            self.commandTriggered.emit(payload)
            # Callback ausführen
            if callable(payload):
                payload()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if key == Qt.Key.Key_Down:
            cur = self.results_list.currentRow()
            if cur < self.results_list.count() - 1:
                self.results_list.setCurrentRow(cur + 1)
            event.accept()
            return
        elif key == Qt.Key.Key_Up:
            cur = self.results_list.currentRow()
            if cur > 0:
                self.results_list.setCurrentRow(cur - 1)
            event.accept()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cur_item = self.results_list.currentItem()
            if cur_item:
                self._on_item_activated(cur_item)
            event.accept()
            return
        elif key == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return

        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # Oben zentrieren bezogen auf das Hauptfenster
        if self.main_window:
            mw_geom = self.main_window.geometry()
            x = mw_geom.x() + (mw_geom.width() - self.width()) // 2
            y = mw_geom.y() + 60
            self.move(x, y)
        self.search_input.setFocus()
