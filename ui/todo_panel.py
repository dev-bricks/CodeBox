#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO- & Aufgaben-Seitenleiste für CodeBox.

Listet im Projekt gefundene Aufgaben (TODO, FIXME, BUG, HACK, XXX, NOTE)
übersichtlich und barrierefrei auf. Unterstützt Gruppierung nach Datei oder Tag,
Echtzeit-Text- und Tag-Filterung sowie Direktsprung in den Editor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.todo_scanner import DEFAULT_TODO_TAGS, TodoItem, TodoScannerManager

TAG_COLORS: Dict[str, str] = {
    "BUG": "#f14c4c",
    "FIXME": "#f14c4c",
    "HACK": "#cca700",
    "XXX": "#cca700",
    "TODO": "#3794ff",
    "NOTE": "#73c991",
}


class TodoTreeWidget(QTreeWidget):
    """QTreeWidget mit Tastatur-Enter-Unterstützung zum Anspringen von Aufgaben."""

    itemActivatedByKey = Signal(QTreeWidgetItem)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item:
                self.itemActivatedByKey.emit(item)
                event.accept()
                return
        super().keyPressEvent(event)


class TodoPanel(QWidget):
    """Barrierefreie Seitenleiste zur Anzeige und Navigation von Aufgaben im Code."""

    todoActivated = Signal(object)  # Emittiert TodoItem
    rescanRequested = Signal()
    countsChanged = Signal(int, int)  # total_items, total_files

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._all_items: List[TodoItem] = []
        self._scanner_manager: Optional[TodoScannerManager] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 1. Header-Zeile: Titel / Zähler und Aktualisieren-Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.setSpacing(4)

        self.title_label = QLabel("Aufgaben")
        title_font = QFont(self.title_label.font())
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAccessibleName("Aufgaben Status")
        header_layout.addWidget(self.title_label, 1)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setObjectName("todo_panel_refresh_button")
        self.btn_refresh.setFixedHeight(22)
        self.btn_refresh.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        self.btn_refresh.setToolTip("Arbeitsbereich nach Aufgaben neu durchsuchen")
        self.btn_refresh.setAccessibleName("Aufgaben aktualisieren")
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # 2. Filter- & Gruppierungsleiste
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        self.tag_combo = QComboBox()
        self.tag_combo.setObjectName("todo_panel_tag_combo")
        self.tag_combo.setFixedHeight(22)
        self.tag_combo.setStyleSheet("font-size: 10px;")
        self.tag_combo.setToolTip("Nach Tag filtern")
        self.tag_combo.setAccessibleName("Tag Filter")
        self.tag_combo.addItem("Alle Tags", "")
        for tag in DEFAULT_TODO_TAGS:
            self.tag_combo.addItem(tag, tag)
        self.tag_combo.currentIndexChanged.connect(self._apply_filter)
        controls_layout.addWidget(self.tag_combo)

        self.group_combo = QComboBox()
        self.group_combo.setObjectName("todo_panel_group_combo")
        self.group_combo.setFixedHeight(22)
        self.group_combo.setStyleSheet("font-size: 10px;")
        self.group_combo.setToolTip("Gruppierung der Aufgaben")
        self.group_combo.setAccessibleName("Gruppierung")
        self.group_combo.addItem("Nach Datei", "file")
        self.group_combo.addItem("Nach Tag", "tag")
        self.group_combo.currentIndexChanged.connect(self._apply_filter)
        controls_layout.addWidget(self.group_combo)

        layout.addLayout(controls_layout)

        # 3. Suchfilter-Eingabe
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("todo_panel_search_edit")
        self.search_edit.setFixedHeight(22)
        self.search_edit.setStyleSheet("font-size: 11px;")
        self.search_edit.setPlaceholderText("Filter (Text, Datei, Autor)...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setAccessibleName("Aufgaben Suchfilter")
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        # 4. Aufgaben-Baumansicht
        self.tree = TodoTreeWidget()
        self.tree.setObjectName("todo_panel_tree")
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Aufgabe / Datei", "Zeile"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setAccessibleName("Aufgaben- und TODO-Baum")
        self.tree.setAccessibleDescription(
            "Listet gefundene Aufgabenkommentare im Arbeitsbereich auf. "
            "Doppelklick oder Eingabetaste springt direkt zur Fundstelle."
        )

        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemActivatedByKey.connect(self._on_item_key_activated)
        layout.addWidget(self.tree)

        # 5. Statuszeile am unteren Rand
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        self.status_label.setAccessibleName("Aufgaben Statusleiste")
        layout.addWidget(self.status_label)

    def set_scanner_manager(self, manager: TodoScannerManager):
        """Verknüpft das Panel mit einem TodoScannerManager."""
        self._scanner_manager = manager
        manager.scanStarted.connect(self._on_scan_started)
        manager.scanProgress.connect(self._on_scan_progress)
        manager.scanFinished.connect(self._on_scan_finished)
        manager.todosUpdated.connect(self.set_todos)

    def set_todos(self, items: Iterable[TodoItem]):
        """Aktualisiert die Aufgabenliste und baut den Baum neu auf."""
        self._all_items = list(items)
        self._update_counts()
        self._apply_filter()

    def set_scanning(self, is_scanning: bool):
        """Aktualisiert die Ladeanzeige."""
        self.btn_refresh.setEnabled(not is_scanning)
        if is_scanning:
            self.status_label.setText("Scan läuft...")
        else:
            self._update_counts()

    def _on_refresh_clicked(self):
        if self._scanner_manager:
            self._scanner_manager.start_scan()
        self.rescanRequested.emit()

    def _on_scan_started(self):
        self.set_scanning(True)

    def _on_scan_progress(self, scanned: int, total: int):
        self.status_label.setText(f"Scanne {scanned}/{total} Dateien...")

    def _on_scan_finished(self, total_items: int, total_files: int):
        self.set_scanning(False)
        self.status_label.setText(f"{total_items} Aufgaben in {total_files} Dateien gefunden")

    def _update_counts(self):
        item_count = len(self._all_items)
        file_count = len({item.file_path for item in self._all_items})
        if item_count == 0:
            self.title_label.setText("Aufgaben (0)")
            self.status_label.setText("Keine Aufgaben gefunden")
        else:
            self.title_label.setText(f"Aufgaben ({item_count})")
            self.status_label.setText(f"{item_count} Aufgaben in {file_count} Dateien")
        self.countsChanged.emit(item_count, file_count)

    def _apply_filter(self):
        """Filtert und gruppiert die Elemente im TreeWidget."""
        search_query = self.search_edit.text().strip().lower()
        selected_tag = self.tag_combo.currentData() or ""
        group_mode = self.group_combo.currentData() or "file"

        filtered_items: List[TodoItem] = []
        for item in self._all_items:
            if selected_tag and item.tag.upper() != selected_tag.upper():
                continue
            if search_query:
                match_text = (
                    search_query in item.text.lower()
                    or search_query in item.rel_path.lower()
                    or (item.author and search_query in item.author.lower())
                    or search_query in item.tag.lower()
                )
                if not match_text:
                    continue
            filtered_items.append(item)

        self.tree.clear()

        if not filtered_items:
            empty_item = QTreeWidgetItem(["Keine passenden Aufgaben", ""])
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tree.addTopLevelItem(empty_item)
            return

        if group_mode == "tag":
            self._build_tree_grouped_by_tag(filtered_items)
        else:
            self._build_tree_grouped_by_file(filtered_items)

        self.tree.expandAll()

    def _build_tree_grouped_by_file(self, items: List[TodoItem]):
        from collections import defaultdict

        grouped: Dict[Path, List[TodoItem]] = defaultdict(list)
        for item in items:
            grouped[item.file_path].append(item)

        for file_path in sorted(grouped.keys(), key=lambda p: str(p).lower()):
            file_items = grouped[file_path]
            first = file_items[0]
            display_title = first.rel_path if first.rel_path else file_path.name
            if first.folder_name and not display_title.startswith(first.folder_name):
                display_title = f"[{first.folder_name}] {display_title}"

            parent_item = QTreeWidgetItem([f"{display_title} ({len(file_items)})", ""])
            font = QFont(parent_item.font(0))
            font.setBold(True)
            parent_item.setFont(0, font)
            parent_item.setToolTip(0, str(file_path))
            parent_item.setData(0, Qt.ItemDataRole.UserRole, None)

            for item in sorted(file_items, key=lambda x: x.line_number):
                tag_str = f"[{item.tag}]"
                author_str = f"({item.author}) " if item.author else ""
                label = f"{tag_str} {author_str}{item.text}" if item.text else tag_str
                line_str = f"Z. {item.line_number}"

                child_item = QTreeWidgetItem([label, line_str])
                child_item.setData(0, Qt.ItemDataRole.UserRole, item)
                child_item.setToolTip(0, f"{item.file_path}:{item.line_number}\n{item.line_text}")

                color_hex = TAG_COLORS.get(item.tag.upper())
                if color_hex:
                    child_item.setForeground(0, QColor(color_hex))

                parent_item.addChild(child_item)

            self.tree.addTopLevelItem(parent_item)

    def _build_tree_grouped_by_tag(self, items: List[TodoItem]):
        from collections import defaultdict

        grouped: Dict[str, List[TodoItem]] = defaultdict(list)
        for item in items:
            grouped[item.tag.upper()].append(item)

        for tag in sorted(grouped.keys()):
            tag_items = grouped[tag]
            parent_item = QTreeWidgetItem([f"{tag} ({len(tag_items)})", ""])
            font = QFont(parent_item.font(0))
            font.setBold(True)
            parent_item.setFont(0, font)

            color_hex = TAG_COLORS.get(tag)
            if color_hex:
                parent_item.setForeground(0, QColor(color_hex))

            for item in sorted(tag_items, key=lambda x: (str(x.file_path).lower(), x.line_number)):
                display_file = item.rel_path if item.rel_path else item.file_path.name
                author_str = f"({item.author}) " if item.author else ""
                label = f"{display_file}: {author_str}{item.text}" if item.text else display_file
                line_str = f"Z. {item.line_number}"

                child_item = QTreeWidgetItem([label, line_str])
                child_item.setData(0, Qt.ItemDataRole.UserRole, item)
                child_item.setToolTip(0, f"{item.file_path}:{item.line_number}\n{item.line_text}")

                parent_item.addChild(child_item)

            self.tree.addTopLevelItem(parent_item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int):
        self._activate_item(item)

    def _on_item_key_activated(self, item: QTreeWidgetItem):
        self._activate_item(item)

    def _activate_item(self, item: QTreeWidgetItem):
        todo = item.data(0, Qt.ItemDataRole.UserRole)
        if todo and isinstance(todo, TodoItem):
            self.todoActivated.emit(todo)
        elif item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        todo: Optional[TodoItem] = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        if todo and isinstance(todo, TodoItem):
            act_jump = menu.addAction("Zur Fundstelle springen")
            act_jump.triggered.connect(lambda: self.todoActivated.emit(todo))

            act_copy_path = menu.addAction("Dateipfad kopieren")
            act_copy_path.triggered.connect(
                lambda: QApplication.clipboard().setText(str(todo.file_path))
            )

            act_copy_text = menu.addAction("Aufgabentext kopieren")
            act_copy_text.triggered.connect(
                lambda: QApplication.clipboard().setText(todo.text)
            )

            act_copy_line = menu.addAction("Ganze Zeile kopieren")
            act_copy_line.triggered.connect(
                lambda: QApplication.clipboard().setText(todo.line_text)
            )
        else:
            # Ordner-/Datei-Kopfzeile
            if item.childCount() > 0:
                act_expand = menu.addAction("Alles aufklappen" if not item.isExpanded() else "Zuklappen")
                act_expand.triggered.connect(lambda: item.setExpanded(not item.isExpanded()))

        menu.exec(self.tree.viewport().mapToGlobal(pos))
