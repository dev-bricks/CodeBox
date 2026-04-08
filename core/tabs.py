#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tab-System fuer CodeBox - Mehrere Dateien gleichzeitig oeffnen"""

from pathlib import Path
from PySide6.QtWidgets import QTabWidget, QMessageBox
from PySide6.QtCore import Signal

from .editor import CodeEditor
from .highlighter import UniversalHighlighter
from languages import get_provider_for_extension


class EditorTab:
    """Haelt Editor + Highlighter + Metadaten fuer einen Tab"""
    def __init__(self, file_path: Path = None):
        self.file_path = file_path
        self.editor = CodeEditor()
        self.highlighter = UniversalHighlighter(self.editor.document())
        self.provider = None
        self.is_modified = False

        if file_path:
            self._load_file(file_path)

        self.editor.modificationChanged.connect(self._on_modified)

    def _load_file(self, path: Path):
        """Laedt eine Datei in den Editor"""
        self.file_path = path
        if path.exists():
            text = path.read_text(encoding='utf-8', errors='replace')
            self.editor.setPlainText(text)
        # Provider basierend auf Extension setzen
        ext = path.suffix.lstrip('.')
        provider = get_provider_for_extension(ext)
        if provider:
            self.provider = provider
            self.highlighter.set_provider(provider)
            self.editor.set_provider(provider)

    def _on_modified(self, modified):
        self.is_modified = modified

    def save(self) -> bool:
        """Speichert die Datei"""
        if self.file_path:
            try:
                self.file_path.write_text(
                    self.editor.toPlainText(), encoding='utf-8'
                )
            except OSError as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Speichern fehlgeschlagen",
                                     f"Konnte nicht speichern:\n{e}")
                return False
            self.editor.document().setModified(False)
            self.is_modified = False
            return True
        return False

    @property
    def title(self) -> str:
        name = self.file_path.name if self.file_path else "Unbenannt"
        return f"*{name}" if self.is_modified else name


class TabWidget(QTabWidget):
    """Tab-Widget fuer mehrere Editor-Tabs"""

    currentFileChanged = Signal(object)  # Path oder None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabs: dict = {}  # index -> EditorTab

        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_tab_changed)

    def open_file(self, file_path: Path) -> EditorTab:
        """Oeffnet eine Datei in einem neuen Tab (oder wechselt zu existierendem)"""
        # Pruefe ob Datei bereits offen
        for idx in range(self.count()):
            tab = self.tabs.get(idx)
            if tab and tab.file_path and tab.file_path == file_path:
                self.setCurrentIndex(idx)
                return tab

        tab = EditorTab(file_path)
        idx = self.addTab(tab.editor, tab.title)
        self.tabs[idx] = tab
        self.setCurrentIndex(idx)

        tab.editor.modificationChanged.connect(
            lambda _: self._update_tab_title(tab)
        )
        return tab

    def new_tab(self) -> EditorTab:
        """Erstellt einen neuen leeren Tab"""
        tab = EditorTab()
        idx = self.addTab(tab.editor, "Unbenannt")
        self.tabs[idx] = tab
        self.setCurrentIndex(idx)
        return tab

    def close_tab(self, index: int):
        """Schliesst einen Tab (mit Speicher-Abfrage)"""
        tab = self.tabs.get(index)
        if tab and tab.is_modified:
            reply = QMessageBox.question(
                self, "Speichern?",
                f"'{tab.title}' hat ungespeicherte Aenderungen. Speichern?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                tab.save()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.removeTab(index)
        # Tab-Dict neu aufbauen
        old_tabs = self.tabs.copy()
        self.tabs = {}
        for i in range(self.count()):
            widget = self.widget(i)
            for old_idx, old_tab in old_tabs.items():
                if old_tab.editor is widget:
                    self.tabs[i] = old_tab
                    break

    def current_tab(self) -> EditorTab:
        """Gibt den aktuellen EditorTab zurueck"""
        return self.tabs.get(self.currentIndex())

    def save_current(self) -> bool:
        """Speichert den aktuellen Tab"""
        tab = self.current_tab()
        if tab:
            return tab.save()
        return False

    def _on_tab_changed(self, index):
        tab = self.tabs.get(index)
        if tab:
            self.currentFileChanged.emit(tab.file_path)

    def _update_tab_title(self, tab: EditorTab):
        for idx in range(self.count()):
            if self.tabs.get(idx) is tab:
                self.setTabText(idx, tab.title)
                break
