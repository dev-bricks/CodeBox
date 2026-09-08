#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tab-System für CodeBox - Mehrere Dateien gleichzeitig öffnen und geteilte Ansichten"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QTabWidget, QMessageBox
from PySide6.QtCore import Signal
from PySide6.QtGui import QTextDocument

from .editor import CodeEditor
from .highlighter import UniversalHighlighter
from languages import get_provider_for_extension


class EditorTab:
    """Hält Editor + Highlighter + Metadaten für einen Tab"""

    def __init__(
        self,
        file_path: Optional[Path] = None,
        shared_doc: Optional[QTextDocument] = None,
        provider=None,
    ):
        self.file_path = file_path
        self.editor = CodeEditor()
        self.provider = provider
        self.is_modified = False
        self.is_shared_clone = shared_doc is not None

        if shared_doc is not None:
            self.editor.setDocument(shared_doc)
            self.highlighter = None  # Geteiltes Dokument besitzt bereits einen UniversalHighlighter
            if provider:
                self.editor.set_provider(provider)
            if file_path:
                self.editor.setProperty("file_path", str(file_path))
            self.is_modified = shared_doc.isModified()
            self.editor.update_folds()
        else:
            self.highlighter = UniversalHighlighter(self.editor.document())
            if file_path:
                self._load_file(file_path)

        self.editor.modificationChanged.connect(self._on_modified)

    @classmethod
    def create_clone(cls, source_tab: "EditorTab") -> "EditorTab":
        """Erzeugt eine geteilte Ansicht (Klon), die dasselbe Dokument synchron teilt."""
        return cls(
            file_path=source_tab.file_path,
            shared_doc=source_tab.editor.document(),
            provider=source_tab.provider,
        )

    def _load_file(self, path: Path):
        """Lädt eine Datei in den Editor"""
        self.file_path = path
        self.editor.setProperty("file_path", str(path))
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
        self.editor.update_folds()

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
    """Tab-Widget für mehrere Editor-Tabs mit Unterstützung für geteilte Ansichten."""

    currentFileChanged = Signal(object)  # Path oder None
    tabFocused = Signal(object, object)  # (TabWidget, EditorTab)
    tabCountChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editor_tab_widget")
        self.setAccessibleName("Editor-Tabs")
        self.setAccessibleDescription("Reiterleiste für geöffnete Code-Dateien")
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabs: dict[int, EditorTab] = {}  # index -> EditorTab

        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_tab_changed)
        self.tabBar().tabMoved.connect(self._on_tab_moved)
        self.tabBar().tabBarClicked.connect(self._on_tab_bar_clicked)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.tabFocused.emit(self, self.current_tab())

    def _on_tab_bar_clicked(self, index: int):
        tab = self.tabs.get(index)
        self.tabFocused.emit(self, tab)

    def _on_tab_editor_focused(self, tab: EditorTab):
        self.tabFocused.emit(self, tab)

    def _rebuild_tab_map(self):
        """Baut die Index-Map anhand der aktuellen Tab-Reihenfolge neu auf."""
        old_tabs = list(self.tabs.values())
        self.tabs = {}
        for i in range(self.count()):
            widget = self.widget(i)
            for tab in old_tabs:
                if tab.editor is widget:
                    self.tabs[i] = tab
                    self.setTabToolTip(i, str(tab.file_path) if tab.file_path else "Neues Dokument (ungespeichert)")
                    break

    def open_file(self, file_path: Path) -> EditorTab:
        """Öffnet eine Datei in einem neuen Tab (oder wechselt zu existierendem)"""
        # Prüfe, ob die Datei bereits offen ist
        for idx in range(self.count()):
            tab = self.tabs.get(idx)
            if tab and tab.file_path and tab.file_path == file_path:
                self.setCurrentIndex(idx)
                return tab

        tab = EditorTab(file_path)
        idx = self.addTab(tab.editor, tab.title)
        self.tabs[idx] = tab
        self.setTabToolTip(idx, str(file_path))
        self.setCurrentIndex(idx)

        tab.editor.modificationChanged.connect(
            lambda _: self._update_tab_title(tab)
        )
        tab.editor.focusReceived.connect(
            lambda t=tab: self._on_tab_editor_focused(t)
        )
        self.tabCountChanged.emit(self.count())
        return tab

    def clone_tab(self, source_tab: EditorTab) -> EditorTab:
        """Klont einen EditorTab als geteilte Ansicht in dieses TabWidget."""
        if source_tab.file_path:
            for idx in range(self.count()):
                tab = self.tabs.get(idx)
                if tab and tab.file_path and tab.file_path == source_tab.file_path:
                    self.setCurrentIndex(idx)
                    return tab

        tab = EditorTab.create_clone(source_tab)
        idx = self.addTab(tab.editor, tab.title)
        self.tabs[idx] = tab
        self.setTabToolTip(idx, str(tab.file_path) if tab.file_path else "Geteilte Ansicht")
        self.setCurrentIndex(idx)

        tab.editor.modificationChanged.connect(
            lambda _: self._update_tab_title(tab)
        )
        tab.editor.focusReceived.connect(
            lambda t=tab: self._on_tab_editor_focused(t)
        )
        self.tabCountChanged.emit(self.count())
        return tab

    def move_tab_from(self, source_widget: "TabWidget", index: int) -> Optional[EditorTab]:
        """Verschiebt einen Tab aus einem anderen TabWidget in dieses."""
        tab = source_widget.tabs.get(index)
        if not tab:
            return None

        source_widget.removeTab(index)
        source_widget._rebuild_tab_map()
        source_widget.tabCountChanged.emit(source_widget.count())
        current_source = source_widget.current_tab()
        source_widget.currentFileChanged.emit(
            current_source.file_path if current_source else None
        )

        idx = self.addTab(tab.editor, tab.title)
        self.tabs[idx] = tab
        self.setTabToolTip(idx, str(tab.file_path) if tab.file_path else "Neues Dokument (ungespeichert)")
        self.setCurrentIndex(idx)
        self._rebuild_tab_map()

        tab.editor.modificationChanged.connect(
            lambda _: self._update_tab_title(tab)
        )
        tab.editor.focusReceived.connect(
            lambda t=tab: self._on_tab_editor_focused(t)
        )
        self.tabCountChanged.emit(self.count())
        self.currentFileChanged.emit(tab.file_path)
        return tab

    def new_tab(self) -> EditorTab:
        """Erstellt einen neuen leeren Tab"""
        tab = EditorTab()
        idx = self.addTab(tab.editor, "Unbenannt")
        self.tabs[idx] = tab
        self.setTabToolTip(idx, "Neues Dokument (ungespeichert)")
        self.setCurrentIndex(idx)
        tab.editor.modificationChanged.connect(
            lambda _: self._update_tab_title(tab)
        )
        tab.editor.focusReceived.connect(
            lambda t=tab: self._on_tab_editor_focused(t)
        )
        self.tabCountChanged.emit(self.count())
        return tab

    def close_tab(self, index: int, prompt: bool = True) -> bool:
        """Schließt einen Tab (mit Speicher-Abfrage)"""
        tab = self.tabs.get(index)
        if tab and tab.is_modified and prompt and not getattr(tab, "is_shared_clone", False):
            reply = QMessageBox.question(
                self, "Speichern?",
                f"'{tab.title}' hat ungespeicherte Änderungen. Speichern?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                if not tab.save():
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        self.removeTab(index)
        self._rebuild_tab_map()
        current = self.current_tab()
        self.currentFileChanged.emit(current.file_path if current else None)
        self.tabCountChanged.emit(self.count())
        return True

    def _on_tab_moved(self, _from: int, _to: int):
        """Hält die Tab-Map nach Drag-and-drop im Sync."""
        self._rebuild_tab_map()

    def current_tab(self) -> Optional[EditorTab]:
        """Gibt den aktuellen EditorTab zurück"""
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
            self.tabFocused.emit(self, tab)

    def _update_tab_title(self, tab: EditorTab):
        for idx in range(self.count()):
            if self.tabs.get(idx) is tab:
                self.setTabText(idx, tab.title)
                self.setTabToolTip(idx, str(tab.file_path) if tab.file_path else "Neues Dokument (ungespeichert)")
                break
