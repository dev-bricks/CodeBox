"""References panel for LSP and fallback symbol references."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ReferencesTreeWidget(QTreeWidget):
    """QTreeWidget mit Tastatur-Enter-Unterstützung zum Anspringen von Referenzen."""

    itemActivatedByKey = Signal(QTreeWidgetItem)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item:
                self.itemActivatedByKey.emit(item)
                event.accept()
                return
        super().keyPressEvent(event)


class ReferencesPanel(QWidget):
    """Barrierefreies Panel zur Anzeige von Referenzen und Definitionen."""

    referenceActivated = Signal(dict)

    HEADERS = ["Datei / Fundstelle", "Zeile", "Spalte", "Code-Vorschau"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header-Leiste
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        self.title_label = QLabel("Keine Referenzen geladen")
        bold_font = QFont(self.title_label.font())
        bold_font.setBold(True)
        self.title_label.setFont(bold_font)
        self.title_label.setAccessibleName("Referenzen Status")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.clear_btn = QPushButton("Leeren")
        self.clear_btn.setToolTip("Leert die aktuelle Referenzen-Liste")
        self.clear_btn.setAccessibleName("Referenzen leeren")
        self.clear_btn.clicked.connect(self.clear_references)
        header_layout.addWidget(self.clear_btn)

        layout.addLayout(header_layout)

        # Tree Widget
        self.tree = ReferencesTreeWidget()
        self.tree.setColumnCount(len(self.HEADERS))
        self.tree.setHeaderLabels(self.HEADERS)
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAccessibleName("Referenzen-Panel")
        self.tree.setAccessibleDescription(
            "Symbol-Referenzen und Definitionen. Doppelklick oder Eingabetaste springt zur Fundstelle."
        )
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemActivatedByKey.connect(self._on_item_key_activated)

        layout.addWidget(self.tree)

    @property
    def reference_count(self) -> int:
        count = 0
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            count += parent.childCount()
        return count

    def set_references(
        self,
        symbol: str,
        references: Iterable[Mapping],
        title: Optional[str] = None,
        workspace_root: Optional[Path] = None,
    ):
        """Befüllt das Panel mit den übergebenen Referenzen."""
        self.tree.clear()
        ref_list = list(references or [])
        if not ref_list:
            self.title_label.setText(f"Keine Referenzen für '{symbol}' gefunden")
            return

        # Nach Datei gruppieren
        grouped: dict[str, list[dict]] = defaultdict(list)
        for ref in ref_list:
            p = ref.get("path")
            key = str(p) if p else "(Unbekannte Datei)"
            grouped[key].append(dict(ref))

        file_count = len(grouped)
        total_count = len(ref_list)

        if title:
            self.title_label.setText(title)
        else:
            self.title_label.setText(
                f"Referenzen für '{symbol}' ({total_count} Treffer in {file_count} Datei{'en' if file_count != 1 else ''})"
            )

        for file_key, items in grouped.items():
            disp_path = file_key
            if workspace_root:
                try:
                    rel = Path(file_key).relative_to(workspace_root)
                    disp_path = str(rel)
                except ValueError:
                    disp_path = Path(file_key).name

            file_item = QTreeWidgetItem([
                f"{disp_path} ({len(items)})",
                "",
                "",
                "",
            ])
            file_item.setFirstColumnSpanned(False)
            file_item_font = QFont(self.tree.font())
            file_item_font.setBold(True)
            file_item.setFont(0, file_item_font)
            file_item.setData(0, Qt.ItemDataRole.UserRole, {"is_group": True, "path": file_key})

            for it in items:
                line = int(it.get("line") or 1)
                col = int(it.get("col") or 1)
                preview = str(it.get("preview") or "").strip()
                child = QTreeWidgetItem([
                    "",
                    str(line),
                    str(col),
                    preview,
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, it)
                file_item.addChild(child)

            self.tree.addTopLevelItem(file_item)
            file_item.setExpanded(True)

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.resizeColumnToContents(2)

    def clear_references(self):
        """Leert den Baum und setzt die Anzeige zurück."""
        self.tree.clear()
        self.title_label.setText("Keine Referenzen geladen")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and not data.get("is_group"):
            self.referenceActivated.emit(data)

    def _on_item_key_activated(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            if data.get("is_group"):
                item.setExpanded(not item.isExpanded())
            else:
                self.referenceActivated.emit(data)
