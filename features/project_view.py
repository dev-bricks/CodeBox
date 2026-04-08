#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project View - Dateibaum-Explorer fuer CodeBox

Zeigt eine Baumstruktur des geoeffneten Projektordners an.
Unterstuetzt Doppelklick zum Oeffnen, Kontextmenue und Filter.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel,
    QPushButton, QLabel, QLineEdit, QMenu, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, QDir, Signal, QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QFont


# Dateien/Ordner die standardmaessig ausgeblendet werden
DEFAULT_HIDDEN = {
    '__pycache__', '.git', '.svn', '.hg', 'node_modules',
    '.idea', '.vscode', '.vs', 'dist', 'build', '.eggs',
    '*.pyc', '*.pyo', '.DS_Store', 'Thumbs.db'
}


class FileFilterProxy(QSortFilterProxyModel):
    """Filtert versteckte Dateien und Ordner."""

    def __init__(self, hidden_patterns=None, parent=None):
        super().__init__(parent)
        self.hidden_patterns = hidden_patterns or DEFAULT_HIDDEN
        self._filter_text = ""

    def set_filter_text(self, text: str):
        self._filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        name = model.fileName(index)

        # Versteckte Muster filtern
        for pattern in self.hidden_patterns:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return False
            elif name == pattern:
                return False

        # Textfilter
        if self._filter_text:
            if self._filter_text not in name.lower():
                # Ordner trotzdem zeigen (koennen passende Kinder haben)
                if model.isDir(index):
                    return True
                return False

        return True


class ProjectView(QWidget):
    """Dateibaum-Widget fuer das Projekt-Panel.

    Signals:
        fileDoubleClicked(Path): Emittiert wenn eine Datei doppelgeklickt wird.
    """

    fileDoubleClicked = Signal(object)  # Path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 4, 4, 0)

        self.title_label = QLabel("Projekt")
        self.title_label.setStyleSheet("font-weight: bold; color: #ccc;")
        header.addWidget(self.title_label)

        header.addStretch()

        btn_open = QPushButton("Ordner...")
        btn_open.setFixedWidth(60)
        btn_open.setStyleSheet("font-size: 10px;")
        btn_open.clicked.connect(self._open_folder_dialog)
        header.addWidget(btn_open)

        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.setFixedWidth(80)
        btn_refresh.setStyleSheet("font-size: 10px;")
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)

        layout.addLayout(header)

        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Datei filtern...")
        self.filter_input.setStyleSheet(
            "QLineEdit { background: #2a2a2a; color: #ccc; border: 1px solid #444; "
            "padding: 3px; margin: 2px 4px; font-size: 11px; }"
        )
        self.filter_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_input)

        # File System Model
        self.fs_model = QFileSystemModel()
        self.fs_model.setReadOnly(True)
        self.fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        # Proxy fuer Filterung
        self.proxy = FileFilterProxy(parent=self)
        self.proxy.setSourceModel(self.fs_model)
        self.proxy.setDynamicSortFilter(True)

        # Tree View
        self.tree = QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #1e1e1e;
                color: #cccccc;
                border: none;
                outline: none;
            }
            QTreeView::item:hover {
                background-color: #2a2a2a;
            }
            QTreeView::item:selected {
                background-color: #264f78;
            }
            QTreeView::branch {
                background-color: #1e1e1e;
            }
        """)

        # Nur den Name-Column anzeigen, Rest ausblenden
        self.tree.hideColumn(1)  # Size
        self.tree.hideColumn(2)  # Type
        self.tree.hideColumn(3)  # Date Modified

        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self.tree)

    def set_root(self, path: str):
        """Setzt den Wurzelordner des Dateibaums."""
        self._root_path = Path(path)
        root_index = self.fs_model.setRootPath(path)
        proxy_root = self.proxy.mapFromSource(root_index)
        self.tree.setRootIndex(proxy_root)
        self._update_git_info()

    def _update_git_info(self):
        """Aktualisiert die Git-Branch-Anzeige im Titel."""
        if not self._root_path:
            self.title_label.setText("")
            return
        from features.git_integration import GitRepo
        repo = GitRepo(str(self._root_path))
        if repo.is_git_repo():
            branch = repo.get_branch()
            self.title_label.setText(f"{self._root_path.name}  [{branch}]")
        else:
            self.title_label.setText(self._root_path.name)

    def _open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Projektordner waehlen")
        if path:
            self.set_root(path)

    def _refresh(self):
        """Aktualisiert die Ansicht."""
        if self._root_path:
            self.set_root(str(self._root_path))

    def _on_filter_changed(self, text: str):
        self.proxy.set_filter_text(text)

    def _on_double_click(self, proxy_index):
        """Oeffnet die Datei bei Doppelklick."""
        source_index = self.proxy.mapToSource(proxy_index)
        if not self.fs_model.isDir(source_index):
            file_path = Path(self.fs_model.filePath(source_index))
            self.fileDoubleClicked.emit(file_path)

    def _on_context_menu(self, position):
        """Zeigt ein Kontextmenue an."""
        proxy_index = self.tree.indexAt(position)
        if not proxy_index.isValid():
            return

        source_index = self.proxy.mapToSource(proxy_index)
        file_path = Path(self.fs_model.filePath(source_index))
        is_dir = self.fs_model.isDir(source_index)

        menu = QMenu(self)

        if not is_dir:
            act_open = menu.addAction("Oeffnen")
            act_open.triggered.connect(lambda: self.fileDoubleClicked.emit(file_path))

        act_reveal = menu.addAction("Im Explorer zeigen")
        act_reveal.triggered.connect(lambda: self._reveal_in_explorer(file_path))

        menu.addSeparator()

        act_copy_path = menu.addAction("Pfad kopieren")
        act_copy_path.triggered.connect(
            lambda: self._copy_to_clipboard(str(file_path))
        )

        if is_dir:
            act_new_file = menu.addAction("Neue Datei...")
            act_new_file.triggered.connect(lambda: self._new_file_in(file_path))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _reveal_in_explorer(self, path: Path):
        """Oeffnet den Ordner im System-Dateimanager."""
        import subprocess, sys
        target = str(path.parent if path.is_file() else path)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", f"/select,{path}"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", target])
        except OSError:
            pass

    def _copy_to_clipboard(self, text: str):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _new_file_in(self, directory: Path):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Neue Datei", "Dateiname:")
        if ok and name:
            new_path = directory / name
            if new_path.exists():
                QMessageBox.warning(self, "Fehler", f"'{name}' existiert bereits.")
                return
            new_path.write_text("", encoding='utf-8')
            self.fileDoubleClicked.emit(new_path)
