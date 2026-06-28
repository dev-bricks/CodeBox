#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project View - Dateibaum-Explorer für CodeBox

Zeigt eine Baumstruktur des geöffneten Projektordners an.
Unterstützt Doppelklick zum Öffnen, Kontextmenü und Filter.
Git-Status-Indikatoren (M/S/U/D) werden rechts neben dem Dateinamen eingeblendet.
"""

from pathlib import Path
from typing import Optional, Dict, TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel,
    QPushButton, QLabel, QLineEdit, QMenu, QFileDialog,
    QMessageBox, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QDir, Signal, QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QFont, QColor

if TYPE_CHECKING:
    from features.git_integration import GitFileStatus


# Dateien/Ordner, die standardmäßig ausgeblendet werden
DEFAULT_HIDDEN = {
    '__pycache__', '.git', '.svn', '.hg', 'node_modules',
    '.idea', '.vscode', '.vs', 'dist', 'build', '.eggs',
    '*.pyc', '*.pyo', '.DS_Store', 'Thumbs.db'
}


def status_for_path(
    abs_path: str,
    repo_root: str,
    status_dict: Dict[str, "GitFileStatus"],
) -> Optional["GitFileStatus"]:
    """Sucht GitFileStatus für einen absoluten Dateipfad anhand eines Status-Dicts.

    Normalisiert Windows-Backslashes zu Forward-Slashes (Porcelain-Format von
    ``git status --porcelain``). Gibt None zurück, wenn der Pfad außerhalb des
    Repos liegt oder kein Status-Eintrag existiert.

    Args:
        abs_path:    Absoluter Dateipfad (Windows- oder Unix-Trennzeichen).
        repo_root:   Absoluter Pfad zum Repo-Wurzelordner.
        status_dict: Dict aus ``GitRepo.get_status()`` (Keys: Slash-relativ).

    Returns:
        GitFileStatus oder None.
    """
    try:
        rel = Path(abs_path).relative_to(repo_root)
    except ValueError:
        return None
    return status_dict.get(rel.as_posix())


class GitStatusDelegate(QStyledItemDelegate):
    """Zeichnet einen farbigen Git-Status-Badge rechts neben dem Dateinamen.

    Holt sich den absoluten Dateipfad über ``QFileSystemModel``/Proxy und
    delegiert den Lookup an die Qt-freie ``status_for_path``-Funktion.
    Ordner werden nicht beschriftet.
    """

    _BADGE_FONT_SIZE = 9

    def __init__(self, fs_model: QFileSystemModel, proxy: QSortFilterProxyModel,
                 parent=None):
        super().__init__(parent)
        self._fs_model = fs_model
        self._proxy = proxy
        self._status_dict: Dict[str, "GitFileStatus"] = {}
        self._repo_root: str = ""

    def set_status(self, repo_root: str, status_dict: Dict[str, "GitFileStatus"]):
        """Setzt den aktuellen Git-Status-Cache (wird bei set_root/refresh aufgerufen)."""
        self._repo_root = repo_root
        self._status_dict = status_dict

    def _status_for_index(self, index: QModelIndex) -> Optional["GitFileStatus"]:
        source = self._proxy.mapToSource(index)
        if not source.isValid():
            return None
        abs_path = self._fs_model.filePath(source)
        if not abs_path or not self._repo_root:
            return None
        return status_for_path(abs_path, self._repo_root, self._status_dict)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        # Ordner nicht beschriften
        source = self._proxy.mapToSource(index)
        if source.isValid() and self._fs_model.isDir(source):
            return
        status = self._status_for_index(index)
        if not (status and status.status_icon):
            return
        painter.save()
        color = status.color_hint
        if color:
            painter.setPen(QColor(color))
        badge_font = QFont("Consolas", self._BADGE_FONT_SIZE)
        badge_font.setBold(True)
        painter.setFont(badge_font)
        rect = option.rect.adjusted(0, 0, -4, 0)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            status.status_icon,
        )
        painter.restore()


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
                # Ordner trotzdem zeigen (können passende Kinder haben)
                if model.isDir(index):
                    return True
                return False

        return True


class ProjectView(QWidget):
    """Dateibaum-Widget für das Projekt-Panel.

    Signals:
        fileDoubleClicked(Path): Emittiert, wenn eine Datei doppelgeklickt wird.
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

        self.btn_open = QPushButton("Ordner...")
        self.btn_open.setObjectName("project_view_open_folder_button")
        self.btn_open.setFixedWidth(60)
        self.btn_open.setStyleSheet("font-size: 10px;")
        self.btn_open.setToolTip("Projektordner auswählen")
        self.btn_open.setAccessibleName("Projektordner auswählen")
        self.btn_open.setAccessibleDescription(
            "Öffnet einen Dialog, um den angezeigten Projektordner zu wechseln."
        )
        self.btn_open.clicked.connect(self._open_folder_dialog)
        header.addWidget(self.btn_open)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setObjectName("project_view_refresh_button")
        self.btn_refresh.setFixedWidth(80)
        self.btn_refresh.setStyleSheet("font-size: 10px;")
        self.btn_refresh.setToolTip("Projektbaum neu laden")
        self.btn_refresh.setAccessibleName("Projektbaum neu laden")
        self.btn_refresh.setAccessibleDescription(
            "Lädt den aktuell angezeigten Projektordner und seine Dateien neu."
        )
        self.btn_refresh.clicked.connect(self._refresh)
        header.addWidget(self.btn_refresh)

        layout.addLayout(header)

        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setObjectName("project_view_filter_input")
        self.filter_input.setPlaceholderText("Datei filtern...")
        self.filter_input.setToolTip("Dateien und Ordner im Projektbaum filtern")
        self.filter_input.setAccessibleName("Projektdateien filtern")
        self.filter_input.setAccessibleDescription(
            "Filtert Dateien und Ordner im Projektbaum. Ordner bleiben sichtbar,"
            " wenn sie passende Kinder enthalten können."
        )
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

        # Proxy für Filterung
        self.proxy = FileFilterProxy(parent=self)
        self.proxy.setSourceModel(self.fs_model)
        self.proxy.setDynamicSortFilter(True)

        # Tree View
        self.tree = QTreeView()
        self.tree.setObjectName("project_view_tree")
        self.tree.setModel(self.proxy)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.setAccessibleName("Projektdateien")
        self.tree.setAccessibleDescription(
            "Dateibaum des aktuellen Projekts. Das Filterfeld grenzt die angezeigten"
            " Dateien und Ordner ein."
        )
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

        # Nur die Namensspalte anzeigen, Rest ausblenden
        self.tree.hideColumn(1)  # Size
        self.tree.hideColumn(2)  # Type
        self.tree.hideColumn(3)  # Date Modified

        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        # Git-Status-Delegate (zeigt M/S/U/D-Badges neben Dateinamen)
        self.git_delegate = GitStatusDelegate(self.fs_model, self.proxy, self)
        self.tree.setItemDelegateForColumn(0, self.git_delegate)

        layout.addWidget(self.tree)

    def set_root(self, path: str):
        """Setzt den Wurzelordner des Dateibaums."""
        self._root_path = Path(path)
        root_index = self.fs_model.setRootPath(path)
        proxy_root = self.proxy.mapFromSource(root_index)
        self.tree.setRootIndex(proxy_root)
        self._update_git_info()
        self._load_git_status()

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

    def _load_git_status(self):
        """Lädt den Git-Status aller geänderten Dateien für den aktuellen Root.

        Befüllt den Cache des GitStatusDelegate, damit dieser beim Paint-Aufruf
        sofort die Badges rendern kann.
        """
        if not self._root_path:
            self.git_delegate.set_status("", {})
            return
        from features.git_integration import GitRepo
        repo = GitRepo(str(self._root_path))
        if repo.is_git_repo():
            self.git_delegate.set_status(str(self._root_path), repo.get_status())
        else:
            self.git_delegate.set_status("", {})

    def _open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Projektordner wählen")
        if path:
            self.set_root(path)

    def _refresh(self):
        """Aktualisiert die Ansicht und den Git-Status-Cache."""
        if self._root_path:
            self.set_root(str(self._root_path))

    def _on_filter_changed(self, text: str):
        self.proxy.set_filter_text(text)

    def _on_double_click(self, proxy_index):
        """Öffnet die Datei bei Doppelklick."""
        source_index = self.proxy.mapToSource(proxy_index)
        if not self.fs_model.isDir(source_index):
            file_path = Path(self.fs_model.filePath(source_index))
            self.fileDoubleClicked.emit(file_path)

    def _on_context_menu(self, position):
        """Zeigt ein Kontextmenü an."""
        proxy_index = self.tree.indexAt(position)
        if not proxy_index.isValid():
            return

        source_index = self.proxy.mapToSource(proxy_index)
        file_path = Path(self.fs_model.filePath(source_index))
        is_dir = self.fs_model.isDir(source_index)

        menu = QMenu(self)

        if not is_dir:
            act_open = menu.addAction("Öffnen")
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
        """Öffnet den Ordner im System-Dateimanager."""
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
            try:
                new_path.write_text("", encoding='utf-8')
            except OSError as e:
                QMessageBox.critical(self, "Fehler",
                                     f"Datei konnte nicht erstellt werden:\n{e}")
                return
            self.fileDoubleClicked.emit(new_path)
