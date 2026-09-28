#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug-Panel für CodeBox — Watch-Expressions (Variablenüberwachung) und Call-Stack (Aufruf-Stapel)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.debugger import (
    StackFrame,
    WatchExpression,
    parse_pdb_stack,
    safe_eval_expression,
)


class WatchTreeWidget(QTreeWidget):
    """Baumansicht für Überwachungsausdrücke mit Tastatur- und Kontextmenüunterstützung."""

    deleteRequested = Signal(QTreeWidgetItem)
    editRequested = Signal(QTreeWidgetItem)
    refreshRequested = Signal(QTreeWidgetItem)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item:
                self.deleteRequested.emit(item)
                event.accept()
                return
        elif event.key() == Qt.Key.Key_F2:
            item = self.currentItem()
            if item:
                self.editRequested.emit(item)
                event.accept()
                return
        super().keyPressEvent(event)


class CallStackTreeWidget(QTreeWidget):
    """Baumansicht für den Call-Stack mit Enter-Navigation zu Quelldatei und Zeile."""

    frameActivated = Signal(str, int)  # file_path, line_number

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item:
                self._activate_item(item)
                event.accept()
                return
        super().keyPressEvent(event)

    def _activate_item(self, item: QTreeWidgetItem):
        raw_path = item.data(0, Qt.ItemDataRole.UserRole)
        raw_line = item.data(1, Qt.ItemDataRole.UserRole)
        if raw_path is not None and raw_line is not None:
            self.frameActivated.emit(str(raw_path), int(raw_line))


class DebugPanel(QWidget):
    """Barrierefreies Panel zur Variablenüberwachung und Visualisierung des Aufruf-Stapels."""

    frameActivated = Signal(str, int)  # file_path, line_number
    watchAdded = Signal(str)
    watchRemoved = Signal(str)
    refreshRequested = Signal()

    WATCH_HEADERS = ["Ausdruck", "Wert", "Typ"]
    STACK_HEADERS = ["Frame", "Funktion", "Datei", "Zeile", "Quelltext"]

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._is_active_session: bool = False
        self._watches: Dict[str, WatchExpression] = {}
        self._frames: List[StackFrame] = []
        self._output_panel = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # 1. Header Toolbar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(2, 2, 2, 2)

        self.status_label = QLabel("Debugger: Bereit (keine aktive Sitzung)")
        bold_font = QFont(self.status_label.font())
        bold_font.setBold(True)
        self.status_label.setFont(bold_font)
        self.status_label.setAccessibleName("Debugger Status")
        self.status_label.setAccessibleDescription("Zeigt an, ob aktuell eine Debug-Sitzung aktiv ist.")
        header_bar.addWidget(self.status_label)

        header_bar.addStretch()

        self.refresh_btn = QPushButton("Aktualisieren")
        self.refresh_btn.setToolTip("Aktualisiert Stack und Watch-Expressions (w & p)")
        self.refresh_btn.setAccessibleName("Debugger aktualisieren")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_bar.addWidget(self.refresh_btn)

        self.get_stack_btn = QPushButton("Stapel abrufen (w)")
        self.get_stack_btn.setToolTip("Fragt den aktuellen Call-Stack via 'w' beim Debugger ab")
        self.get_stack_btn.setAccessibleName("Call-Stack abrufen")
        self.get_stack_btn.clicked.connect(self.request_stack_update)
        header_bar.addWidget(self.get_stack_btn)

        self.clear_btn = QPushButton("Leeren")
        self.clear_btn.setToolTip("Leert die Call-Stack Anzeige und setzt Variablenwerte zurück")
        self.clear_btn.setAccessibleName("Debugger-Panel leeren")
        self.clear_btn.clicked.connect(self.clear_debug_data)
        header_bar.addWidget(self.clear_btn)

        main_layout.addLayout(header_bar)

        # 2. Splitter: Links Watch-Expressions, Rechts Call-Stack
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("debug_splitter")

        # --- Linke Seite: Überwachungsausdrücke (Watch) ---
        watch_container = QWidget()
        watch_layout = QVBoxLayout(watch_container)
        watch_layout.setContentsMargins(2, 2, 2, 2)
        watch_layout.setSpacing(4)

        watch_header = QHBoxLayout()
        watch_title = QLabel("Überwachung (Watch Expressions)")
        watch_title.setStyleSheet("font-weight: bold; color: #4ec9b0;")
        watch_title.setAccessibleName("Titel Überwachung")
        watch_header.addWidget(watch_title)

        watch_header.addStretch()

        self.watch_input = QLineEdit()
        self.watch_input.setPlaceholderText("Ausdruck (z. B. x, len(data), self.name)...")
        self.watch_input.setToolTip("Neuen Ausdruck zur Überwachung eintragen und Enter drücken")
        self.watch_input.setAccessibleName("Ausdruck Eingabefeld")
        self.watch_input.returnPressed.connect(self._on_add_watch_clicked)
        watch_header.addWidget(self.watch_input)

        self.add_watch_btn = QPushButton("+ Hinzufügen")
        self.add_watch_btn.setToolTip("Ausdruck zur Überwachung hinzufügen")
        self.add_watch_btn.setAccessibleName("Ausdruck hinzufügen")
        self.add_watch_btn.clicked.connect(self._on_add_watch_clicked)
        watch_header.addWidget(self.add_watch_btn)

        watch_layout.addLayout(watch_header)

        self.watch_tree = WatchTreeWidget()
        self.watch_tree.setColumnCount(len(self.WATCH_HEADERS))
        self.watch_tree.setHeaderLabels(self.WATCH_HEADERS)
        self.watch_tree.setRootIsDecorated(False)
        self.watch_tree.setAlternatingRowColors(True)
        self.watch_tree.setAccessibleName("Watch-Expressions Tabelle")
        self.watch_tree.setAccessibleDescription(
            "Liste der überwachten Variablen und Ausdrücke. F2 zum Bearbeiten, Entf zum Löschen."
        )
        self.watch_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.watch_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.watch_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.watch_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.watch_tree.customContextMenuRequested.connect(self._on_watch_context_menu)
        self.watch_tree.deleteRequested.connect(self._on_watch_delete_requested)
        self.watch_tree.editRequested.connect(self._on_watch_edit_requested)
        self.watch_tree.itemDoubleClicked.connect(self._on_watch_double_clicked)
        watch_layout.addWidget(self.watch_tree)

        self.splitter.addWidget(watch_container)

        # --- Rechte Seite: Aufruf-Stapel (Call-Stack) ---
        stack_container = QWidget()
        stack_layout = QVBoxLayout(stack_container)
        stack_layout.setContentsMargins(2, 2, 2, 2)
        stack_layout.setSpacing(4)

        stack_header = QHBoxLayout()
        stack_title = QLabel("Aufruf-Stapel (Call-Stack)")
        stack_title.setStyleSheet("font-weight: bold; color: #569cd6;")
        stack_title.setAccessibleName("Titel Aufruf-Stapel")
        stack_header.addWidget(stack_title)

        self.stack_count_label = QLabel("(0 Frames)")
        self.stack_count_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.stack_count_label.setAccessibleName("Anzahl Stack-Frames")
        stack_header.addWidget(self.stack_count_label)

        stack_header.addStretch()

        self.jump_top_btn = QPushButton("Aktueller Frame")
        self.jump_top_btn.setToolTip("Springt zur aktuellen Codezeile des Debuggers")
        self.jump_top_btn.setAccessibleName("Zum aktuellen Frame springen")
        self.jump_top_btn.clicked.connect(self._jump_to_current_frame)
        stack_header.addWidget(self.jump_top_btn)

        stack_layout.addLayout(stack_header)

        self.stack_tree = CallStackTreeWidget()
        self.stack_tree.setColumnCount(len(self.STACK_HEADERS))
        self.stack_tree.setHeaderLabels(self.STACK_HEADERS)
        self.stack_tree.setRootIsDecorated(False)
        self.stack_tree.setAlternatingRowColors(True)
        self.stack_tree.setAccessibleName("Call-Stack Tabelle")
        self.stack_tree.setAccessibleDescription(
            "Liste der Aufruf-Frames. Doppelklick oder Eingabetaste springt direkt zur Quellcode-Zeile."
        )
        self.stack_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.stack_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.stack_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.stack_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.stack_tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.stack_tree.itemDoubleClicked.connect(self._on_stack_item_double_clicked)
        self.stack_tree.frameActivated.connect(self.frameActivated.emit)
        self.stack_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stack_tree.customContextMenuRequested.connect(self._on_stack_context_menu)
        stack_layout.addWidget(self.stack_tree)

        self.splitter.addWidget(stack_container)
        self.splitter.setSizes([450, 550])

        main_layout.addWidget(self.splitter)

        # 3. Schnellauswertung (Evaluate Expression) Leiste am unteren Rand
        eval_bar = QHBoxLayout()
        eval_bar.setContentsMargins(2, 2, 2, 2)
        eval_label = QLabel("Schnellauswertung:")
        eval_label.setToolTip("Wertet beliebige Python-Ausdrücke im aktuellen Debug-Kontext aus")
        eval_label.setAccessibleName("Schnellauswertung Label")
        eval_bar.addWidget(eval_label)

        self.eval_input = QLineEdit()
        self.eval_input.setPlaceholderText("Ausdruck auswerten (Enter)...")
        self.eval_input.setToolTip("Ausdruck eingeben und Enter drücken zur sofortigen Auswertung")
        self.eval_input.setAccessibleName("Schnellauswertung Eingabefeld")
        self.eval_input.returnPressed.connect(self._on_eval_clicked)
        eval_bar.addWidget(self.eval_input)

        self.eval_btn = QPushButton("Auswerten")
        self.eval_btn.setToolTip("Ausdruck sofort auswerten")
        self.eval_btn.setAccessibleName("Schnellauswertung ausführen")
        self.eval_btn.clicked.connect(self._on_eval_clicked)
        eval_bar.addWidget(self.eval_btn)

        self.eval_result_label = QLabel("")
        self.eval_result_label.setAccessibleName("Auswertungsergebnis")
        self.eval_result_label.setStyleSheet("color: #dcdcaa; padding-left: 6px;")
        eval_bar.addWidget(self.eval_result_label)

        self.add_eval_to_watch_btn = QPushButton("Zu Überwachung")
        self.add_eval_to_watch_btn.setToolTip("Ausgewerteten Ausdruck zu den dauerhaften Watch-Expressions hinzufügen")
        self.add_eval_to_watch_btn.setAccessibleName("Ausgewerteten Ausdruck zu Überwachung hinzufügen")
        self.add_eval_to_watch_btn.setEnabled(False)
        self.add_eval_to_watch_btn.clicked.connect(self._on_add_eval_to_watch)
        eval_bar.addWidget(self.add_eval_to_watch_btn)

        main_layout.addLayout(eval_bar)

    # ---- Sitzungsverwaltung ----

    def is_session_active(self) -> bool:
        """Prüft, ob eine Debugger-Sitzung aktiv ist."""
        return self._is_active_session

    def set_session_active(self, active: bool):
        """Aktualisiert die Statusanzeige und Button-Verfügbarkeit."""
        self._is_active_session = active
        if active:
            self.status_label.setText("● Debug-Sitzung aktiv")
            self.status_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
            self.get_stack_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
        else:
            self.status_label.setText("Debugger: Bereit (keine aktive Sitzung)")
            self.status_label.setStyleSheet("color: #888888; font-weight: bold;")

    def attach_output_panel(self, output_panel):
        """Verknüpft das DebugPanel mit dem OutputPanel für automatische Aktualisierungen."""
        self._output_panel = output_panel
        if hasattr(output_panel, "processFinished"):
            output_panel.processFinished.connect(lambda code, out: self.set_session_active(False))
        if hasattr(output_panel, "inputSent"):
            output_panel.inputSent.connect(self._on_debugger_command_sent)

    def _on_debugger_command_sent(self, text: str):
        """Reagiert auf Debugger-Befehle (s, n, r, c) und aktualisiert den Status."""
        cmd = text.strip()
        if cmd in ("s", "n", "r", "c", "step", "next", "return", "continue"):
            self.set_session_active(True)

    # ---- Überwachungsausdrücke (Watch Expressions) ----

    def add_watch(
        self,
        expression: str,
        value: str = "<nicht ausgewertet>",
        type_name: str = "",
        status: str = "pending",
    ) -> bool:
        """Fügt einen neuen Ausdruck zur Überwachung hinzu oder aktualisiert ihn."""
        expr_clean = expression.strip()
        if not expr_clean:
            return False

        if expr_clean in self._watches:
            watch = self._watches[expr_clean]
            watch.value = value
            watch.type_name = type_name
            watch.status = status
            self._update_watch_item_in_tree(watch)
            return True

        watch = WatchExpression(
            expression=expr_clean,
            value=value,
            type_name=type_name,
            status=status,
        )
        self._watches[expr_clean] = watch

        item = QTreeWidgetItem([watch.expression, watch.value, watch.type_name])
        item.setData(0, Qt.ItemDataRole.UserRole, watch.expression)
        self._apply_watch_item_style(item, watch.status)
        self.watch_tree.addTopLevelItem(item)

        self.watchAdded.emit(expr_clean)
        return True

    def remove_watch(self, expression: str):
        """Entfernt einen Ausdruck aus der Überwachung."""
        expr_clean = expression.strip()
        if expr_clean in self._watches:
            del self._watches[expr_clean]

        for i in range(self.watch_tree.topLevelItemCount()):
            item = self.watch_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == expr_clean:
                self.watch_tree.takeTopLevelItem(i)
                self.watchRemoved.emit(expr_clean)
                break

    def clear_watches(self):
        """Entfernt alle Überwachungsausdrücke."""
        self._watches.clear()
        self.watch_tree.clear()

    def get_watches(self) -> List[Dict[str, Any]]:
        """Gibt alle registrierten Überwachungsausdrücke als Liste von Dictionaries zurück."""
        return [w.to_dict() for w in self._watches.values()]

    def set_watch_value(
        self,
        expression: str,
        value: str,
        type_name: str = "",
        status: str = "ok",
    ):
        """Aktualisiert Wert und Typ eines bestehenden Überwachungsausdrucks."""
        expr_clean = expression.strip()
        if expr_clean in self._watches:
            watch = self._watches[expr_clean]
            watch.value = value
            watch.type_name = type_name
            watch.status = status
            self._update_watch_item_in_tree(watch)

    def _update_watch_item_in_tree(self, watch: WatchExpression):
        for i in range(self.watch_tree.topLevelItemCount()):
            item = self.watch_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == watch.expression:
                item.setText(1, watch.value)
                item.setText(2, watch.type_name)
                self._apply_watch_item_style(item, watch.status)
                break

    def _apply_watch_item_style(self, item: QTreeWidgetItem, status: str):
        if status == "ok":
            item.setForeground(1, QColor("#9cdcfe"))
            item.setForeground(2, QColor("#4ec9b0"))
        elif status == "error":
            item.setForeground(1, QColor("#f48771"))
            item.setForeground(2, QColor("#f48771"))
        else:
            item.setForeground(1, QColor("#888888"))
            item.setForeground(2, QColor("#888888"))

    def _on_add_watch_clicked(self):
        expr = self.watch_input.text().strip()
        if expr:
            self.add_watch(expr)
            self.watch_input.clear()
            if self._output_panel and hasattr(self._output_panel, "is_running") and self._output_panel.is_running():
                self._evaluate_watch_in_debugger(expr)

    def _on_watch_delete_requested(self, item: QTreeWidgetItem):
        expr = item.data(0, Qt.ItemDataRole.UserRole)
        if expr:
            self.remove_watch(expr)

    def _on_watch_edit_requested(self, item: QTreeWidgetItem):
        old_expr = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_expr:
            return
        new_expr, ok = QInputDialog.getText(
            self,
            "Ausdruck bearbeiten",
            "Neuer Überwachungsausdruck:",
            QLineEdit.EchoMode.Normal,
            old_expr,
        )
        if ok and new_expr.strip() and new_expr.strip() != old_expr:
            self.remove_watch(old_expr)
            self.add_watch(new_expr.strip())

    def _on_watch_double_clicked(self, item: QTreeWidgetItem, column: int):
        if column == 0:
            self._on_watch_edit_requested(item)
        else:
            val = item.text(1)
            if val:
                QApplication.clipboard().setText(val)

    def _on_watch_context_menu(self, pos):
        item = self.watch_tree.itemAt(pos)
        menu = QMenu(self)

        if item:
            expr = item.data(0, Qt.ItemDataRole.UserRole)
            val = item.text(1)

            act_edit = menu.addAction("Ausdruck bearbeiten (F2)")
            act_edit.triggered.connect(lambda: self._on_watch_edit_requested(item))

            act_copy = menu.addAction("Wert kopieren")
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(val))

            act_eval = menu.addAction(f"'{expr}' neu auswerten")
            act_eval.triggered.connect(lambda: self._evaluate_watch_in_debugger(expr))

            menu.addSeparator()

            act_del = menu.addAction("Ausdruck entfernen (Entf)")
            act_del.triggered.connect(lambda: self.remove_watch(expr))

        act_clear = menu.addAction("Alle Ausdrücke entfernen")
        act_clear.triggered.connect(self.clear_watches)

        menu.exec(self.watch_tree.viewport().mapToGlobal(pos))

    # ---- Aufruf-Stapel (Call-Stack) ----

    def set_call_stack(self, frames: List[StackFrame]):
        """Aktualisiert die Call-Stack Anzeige mit einer Liste von StackFrames."""
        self._frames = list(frames)
        self.stack_tree.clear()

        for frame in self._frames:
            item = QTreeWidgetItem([
                frame.display_frame(),
                frame.function_name,
                frame.file_name,
                str(frame.line_number),
                frame.code_line,
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, frame.file_path)
            item.setData(1, Qt.ItemDataRole.UserRole, frame.line_number)
            item.setToolTip(0, f"{frame.file_path}:{frame.line_number}")

            if frame.is_current:
                font = QFont(item.font(0))
                font.setBold(True)
                item.setFont(0, font)
                item.setFont(1, font)
                item.setForeground(0, QColor("#4ec9b0"))
                item.setForeground(1, QColor("#4ec9b0"))

            self.stack_tree.addTopLevelItem(item)

        count = len(self._frames)
        self.stack_count_label.setText(f"({count} Frame{'s' if count != 1 else ''})")
        if count > 0:
            self.set_session_active(True)

    def load_call_stack_text(self, text: str):
        """Parst Textausgabe (z. B. von PDB 'where') und setzt den Aufruf-Stapel."""
        frames = parse_pdb_stack(text)
        self.set_call_stack(frames)

    def clear_call_stack(self):
        """Leert den Aufruf-Stapel."""
        self._frames.clear()
        self.stack_tree.clear()
        self.stack_count_label.setText("(0 Frames)")

    def clear_debug_data(self):
        """Leert Stack und setzt Ausdrücke zurück."""
        self.clear_call_stack()
        for w in self._watches.values():
            w.value = "<nicht ausgewertet>"
            w.type_name = ""
            w.status = "pending"
            self._update_watch_item_in_tree(w)
        self.eval_result_label.setText("")
        self.add_eval_to_watch_btn.setEnabled(False)

    def _on_stack_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        raw_path = item.data(0, Qt.ItemDataRole.UserRole)
        raw_line = item.data(1, Qt.ItemDataRole.UserRole)
        if raw_path is not None and raw_line is not None:
            self.frameActivated.emit(str(raw_path), int(raw_line))

    def _jump_to_current_frame(self):
        """Springt zum aktuell aktiven Frame (Markierung mit ▶ oder oberster Frame)."""
        if not self._frames:
            return
        target = next((f for f in self._frames if f.is_current), self._frames[-1])
        self.frameActivated.emit(target.file_path, target.line_number)

    def _on_stack_context_menu(self, pos):
        item = self.stack_tree.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        raw_path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        raw_line = int(item.data(1, Qt.ItemDataRole.UserRole) or 1)
        code_line = item.text(4)

        act_jump = menu.addAction("Zu dieser Zeile springen (Enter)")
        act_jump.triggered.connect(lambda: self.frameActivated.emit(raw_path, raw_line))

        act_copy_path = menu.addAction("Dateipfad kopieren")
        act_copy_path.triggered.connect(lambda: QApplication.clipboard().setText(raw_path))

        if code_line:
            act_copy_code = menu.addAction("Quellcodezeile kopieren")
            act_copy_code.triggered.connect(lambda: QApplication.clipboard().setText(code_line))

        menu.exec(self.stack_tree.viewport().mapToGlobal(pos))

    # ---- Auswertung & PDB-Anbindung ----

    def _on_refresh_clicked(self):
        """Fordert Aktualisierung von Stack und Watch-Expressions an."""
        self.refreshRequested.emit()
        self.request_stack_update()
        self.evaluate_all_watches_in_debugger()

    def request_stack_update(self):
        """Sendet 'w' an den laufenden Prozess, falls vorhanden."""
        if self._output_panel and hasattr(self._output_panel, "is_running") and self._output_panel.is_running():
            self._output_panel.send_input("w")

    def _evaluate_watch_in_debugger(self, expression: str):
        """Sendet 'p <expr>' an den aktiven Debugger."""
        if self._output_panel and hasattr(self._output_panel, "is_running") and self._output_panel.is_running():
            self._output_panel.send_input(f"p {expression}")

    def evaluate_all_watches_in_debugger(self):
        """Wertet alle Watch-Expressions im aktiven Debugger aus."""
        for expr in self._watches:
            self._evaluate_watch_in_debugger(expr)

    def evaluate_all_local(self, context: Optional[Dict[str, Any]] = None):
        """Wertet alle Watch-Expressions in einem lokalen Python-Kontext aus (z. B. für Tests oder Offline)."""
        ctx = context or {}
        for expr in self._watches:
            val, type_name, status = safe_eval_expression(expr, ctx)
            self.set_watch_value(expr, val, type_name, status)

    # ---- Schnellauswertung (Evaluate Expression) ----

    def _on_eval_clicked(self):
        expr = self.eval_input.text().strip()
        if not expr:
            return

        if self._output_panel and hasattr(self._output_panel, "is_running") and self._output_panel.is_running():
            self._output_panel.send_input(f"p {expr}")
            self.eval_result_label.setText(f"Auswertung an Debugger gesendet: 'p {expr}'")
            self.add_eval_to_watch_btn.setEnabled(True)
        else:
            val, type_name, status = safe_eval_expression(expr)
            if status == "ok":
                self.eval_result_label.setText(f"= {val} ({type_name})")
                self.eval_result_label.setStyleSheet("color: #4ec9b0; padding-left: 6px;")
            else:
                self.eval_result_label.setText(f"Fehler: {val}")
                self.eval_result_label.setStyleSheet("color: #f48771; padding-left: 6px;")
            self.add_eval_to_watch_btn.setEnabled(True)

    def _on_add_eval_to_watch(self):
        expr = self.eval_input.text().strip()
        if expr:
            self.add_watch(expr)
            self.add_eval_to_watch_btn.setEnabled(False)

    def handle_debugger_output(self, output_text: str):
        """Analysiert debugger-ausgaben und aktualisiert automatisch Stack oder Auswertungen."""
        if not output_text:
            return

        # PDB Stack Output erkennen
        if "(" in output_text and ")" in output_text and ("-> " in output_text or "<module>" in output_text):
            parsed = parse_pdb_stack(output_text)
            if parsed:
                self.set_call_stack(parsed)
