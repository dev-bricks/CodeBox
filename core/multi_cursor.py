#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MultiCursorManager - Multi-Cursor und Column Selection für CodeEditor.
Ermöglicht gleichzeitiges Editieren an mehreren Stellen im Dokument,
Spaltenauswahl (Column Selection), Vorkommen-Markierung und synchrone Tastaturbedienung.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, TYPE_CHECKING
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QPainter, QKeyEvent
)
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit

if TYPE_CHECKING:
    from core.editor import CodeEditor


AUTO_PAIRS = {
    '(': ')',
    '[': ']',
    '{': '}',
    '"': '"',
    "'": "'",
}


class MultiCursorManager:
    """Verwaltet zusätzliche Cursor und synchrone Multi-Cursor-Aktionen für einen CodeEditor."""

    def __init__(self, editor: CodeEditor):
        self.editor = editor
        self.secondary_cursors: List[QTextCursor] = []
        self._column_drag_start: Optional[QTextCursor] = None

    def has_extra_cursors(self) -> bool:
        """Gibt True zurück, wenn zusätzliche Cursor aktiv sind."""
        return len(self.secondary_cursors) > 0

    def cursor_count(self) -> int:
        """Gesamtzahl aller aktiven Cursor (Hauptcursor + Sekundär-Cursor)."""
        return 1 + len(self.secondary_cursors)

    def all_cursors(self) -> List[QTextCursor]:
        """Gibt alle aktiven Cursor in Dokument-Reihenfolge (von oben nach unten) zurück."""
        cursors = [self.editor.textCursor()] + list(self.secondary_cursors)
        return sorted(cursors, key=lambda c: min(c.position(), c.anchor()))

    def _notify_change(self):
        """Aktualisiert Markierungen, Viewport und Statusbar-Informationen."""
        if hasattr(self.editor, "highlightCurrentLine"):
            self.editor.highlightCurrentLine()
        if hasattr(self.editor, "viewport"):
            self.editor.viewport().update()
        if hasattr(self.editor, "emitCursorPosition"):
            self.editor.emitCursorPosition()

    def clear(self):
        """Entfernt alle zusätzlichen Cursor und kehrt zum Einzelcursor zurück."""
        if self.secondary_cursors:
            self.secondary_cursors.clear()
            self._column_drag_start = None
            self._notify_change()

    def add_cursor_at(self, pos: int, anchor: Optional[int] = None) -> bool:
        """Fügt einen Cursor an der angegebenen Dokumentposition hinzu."""
        doc = self.editor.document()
        max_pos = doc.characterCount() - 1
        pos = max(0, min(pos, max_pos))
        anchor = pos if anchor is None else max(0, min(anchor, max_pos))

        # Prüfen, ob an dieser Stelle bereits ein Cursor existiert
        primary = self.editor.textCursor()
        if (primary.position() == pos and primary.anchor() == anchor) or any(
            c.position() == pos and c.anchor() == anchor for c in self.secondary_cursors
        ):
            return False

        c = QTextCursor(doc)
        c.setPosition(anchor)
        if anchor != pos:
            c.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
        self.secondary_cursors.append(c)
        self.merge_cursors()
        self._notify_change()
        return True

    def toggle_cursor_at(self, pos: int) -> bool:
        """Fügt einen Cursor an der Position hinzu oder entfernt ihn, falls er existiert."""
        # Prüfen, ob ein sekundärer Cursor genau hier steht
        for idx, c in enumerate(self.secondary_cursors):
            if c.position() == pos:
                self.secondary_cursors.pop(idx)
                self._notify_change()
                return False
        return self.add_cursor_at(pos)

    def add_cursor_above(self) -> bool:
        """Fügt einen Cursor in der Zeile über dem obersten Cursor ein (gleiche Spalte / Spaltenauswahl)."""
        doc = self.editor.document()
        all_c = self.all_cursors()
        top_cursor = all_c[0]
        top_block_num = top_cursor.blockNumber()

        if top_block_num <= 0:
            return False

        target_block = doc.findBlockByNumber(top_block_num - 1)
        target_text = target_block.text()
        line_len = len(target_text)

        start_col = top_cursor.selectionStart() - top_cursor.block().position()
        end_col = top_cursor.selectionEnd() - top_cursor.block().position()

        new_c = QTextCursor(doc)
        if top_cursor.hasSelection():
            t_start = target_block.position() + min(start_col, line_len)
            t_end = target_block.position() + min(end_col, line_len)
            new_c.setPosition(t_start)
            new_c.setPosition(t_end, QTextCursor.MoveMode.KeepAnchor)
        else:
            col = top_cursor.positionInBlock()
            new_c.setPosition(target_block.position() + min(col, line_len))

        self.secondary_cursors.append(new_c)
        self.merge_cursors()
        self._notify_change()
        return True

    def add_cursor_below(self) -> bool:
        """Fügt einen Cursor in der Zeile unter dem untersten Cursor ein (gleiche Spalte / Spaltenauswahl)."""
        doc = self.editor.document()
        all_c = self.all_cursors()
        bottom_cursor = all_c[-1]
        bottom_block_num = bottom_cursor.blockNumber()

        if bottom_block_num >= doc.blockCount() - 1:
            return False

        target_block = doc.findBlockByNumber(bottom_block_num + 1)
        target_text = target_block.text()
        line_len = len(target_text)

        start_col = bottom_cursor.selectionStart() - bottom_cursor.block().position()
        end_col = bottom_cursor.selectionEnd() - bottom_cursor.block().position()

        new_c = QTextCursor(doc)
        if bottom_cursor.hasSelection():
            t_start = target_block.position() + min(start_col, line_len)
            t_end = target_block.position() + min(end_col, line_len)
            new_c.setPosition(t_start)
            new_c.setPosition(t_end, QTextCursor.MoveMode.KeepAnchor)
        else:
            col = bottom_cursor.positionInBlock()
            new_c.setPosition(target_block.position() + min(col, line_len))

        self.secondary_cursors.append(new_c)
        self.merge_cursors()
        self._notify_change()
        return True

    def select_all_occurrences(self) -> int:
        """Markiert alle Vorkommen des ausgewählten Textes oder Wortes unter dem Cursor."""
        primary = self.editor.textCursor()
        query = primary.selectedText().replace('\u2029', '\n')
        if not query:
            primary.select(QTextCursor.SelectionType.WordUnderCursor)
            query = primary.selectedText().replace('\u2029', '\n')
            if query:
                self.editor.setTextCursor(primary)

        if not query:
            return 0

        text = self.editor.toPlainText()
        matches: List[Tuple[int, int]] = []
        pos = 0
        q_len = len(query)
        while True:
            idx = text.find(query, pos)
            if idx == -1:
                break
            matches.append((idx, idx + q_len))
            pos = idx + max(1, q_len)

        if not matches:
            return 0

        doc = self.editor.document()
        p_start = min(primary.position(), primary.anchor())
        p_end = max(primary.position(), primary.anchor())

        self.secondary_cursors.clear()
        primary_selected = False

        for start, end in matches:
            if not primary_selected and start == p_start and end == p_end:
                primary_selected = True
                continue
            c = QTextCursor(doc)
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.secondary_cursors.append(c)

        if not primary_selected and matches:
            first_start, first_end = matches[0]
            new_p = QTextCursor(doc)
            new_p.setPosition(first_start)
            new_p.setPosition(first_end, QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(new_p)

        self.merge_cursors()
        self._notify_change()
        return len(matches)

    def add_next_occurrence(self) -> bool:
        """Findet das nächste Vorkommen der Auswahl und fügt es als zusätzlichen Cursor hinzu."""
        primary = self.editor.textCursor()
        query = primary.selectedText().replace('\u2029', '\n')
        if not query:
            primary.select(QTextCursor.SelectionType.WordUnderCursor)
            query = primary.selectedText().replace('\u2029', '\n')
            if query:
                self.editor.setTextCursor(primary)

        if not query:
            return False

        text = self.editor.toPlainText()
        q_len = len(query)

        # Aktuell ausgewählte Bereiche erfassen
        selected_ranges = {
            (min(c.position(), c.anchor()), max(c.position(), c.anchor()))
            for c in self.all_cursors()
            if c.hasSelection()
        }

        # Startsuche hinter dem letzten ausgewählten Vorkommen
        latest_end = max((end for _, end in selected_ranges), default=primary.selectionEnd())

        def find_candidate(start_from: int) -> Optional[Tuple[int, int]]:
            pos = start_from
            while True:
                idx = text.find(query, pos)
                if idx == -1:
                    return None
                rng = (idx, idx + q_len)
                if rng not in selected_ranges:
                    return rng
                pos = idx + max(1, q_len)

        match = find_candidate(latest_end)
        if match is None:
            # Wrap around von vorne
            match = find_candidate(0)

        if match is None:
            return False

        doc = self.editor.document()
        new_c = QTextCursor(doc)
        new_c.setPosition(match[0])
        new_c.setPosition(match[1], QTextCursor.MoveMode.KeepAnchor)
        self.secondary_cursors.append(new_c)

        self.merge_cursors()
        self._notify_change()
        return True

    def column_select_between_cursors(self, start_cursor: QTextCursor, end_cursor: QTextCursor):
        """Erzeugt eine rechteckige Spaltenauswahl zwischen zwei Punkten/Cursorn."""
        doc = self.editor.document()
        start_block_num = start_cursor.blockNumber()
        start_col = start_cursor.positionInBlock()

        end_block_num = end_cursor.blockNumber()
        end_col = end_cursor.positionInBlock()

        min_block = min(start_block_num, end_block_num)
        max_block = max(start_block_num, end_block_num)
        min_col = min(start_col, end_col)
        max_col = max(start_col, end_col)

        cursors: List[QTextCursor] = []
        for b_num in range(min_block, max_block + 1):
            block = doc.findBlockByNumber(b_num)
            line_len = len(block.text())
            c_start_pos = block.position() + min(min_col, line_len)
            c_end_pos = block.position() + min(max_col, line_len)

            c = QTextCursor(doc)
            c.setPosition(c_start_pos)
            if c_start_pos != c_end_pos:
                c.setPosition(c_end_pos, QTextCursor.MoveMode.KeepAnchor)
            cursors.append(c)

        if not cursors:
            return

        # Zeile der End-Position wird zum Hauptcursor
        primary_idx = end_block_num - min_block
        if 0 <= primary_idx < len(cursors):
            primary = cursors.pop(primary_idx)
            self.editor.setTextCursor(primary)

        self.secondary_cursors = cursors
        self.merge_cursors()
        self._notify_change()

    def merge_cursors(self):
        """Verschmilzt doppelte oder überlappende Cursor-Positionen."""
        all_c = [self.editor.textCursor()] + self.secondary_cursors
        unique: List[QTextCursor] = []
        seen = set()

        for c in all_c:
            key = (min(c.position(), c.anchor()), max(c.position(), c.anchor()))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        if unique:
            self.editor.setTextCursor(unique[0])
            self.secondary_cursors = unique[1:]

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Führt synchrone Aktionen für alle aktiven Cursor aus. Gibt True zurück, wenn verarbeitet."""
        if not self.has_extra_cursors():
            return False

        key = event.key()
        modifiers = event.modifiers()

        # Escape -> Mehrfachcursor aufheben
        if key == Qt.Key.Key_Escape:
            self.clear()
            return True

        # Backspace
        if key == Qt.Key.Key_Backspace:
            self.delete_backspace()
            return True

        # Delete / Entf
        if key == Qt.Key.Key_Delete:
            self.delete_forward()
            return True

        # Return / Enter
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.insert_text("\n")
            return True

        # Tab (Einrücken / Tabulatoren einfügen)
        if key == Qt.Key.Key_Tab and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.insert_text(" " * getattr(self.editor, "tab_size", 4))
            return True

        # Shift+Tab / Backtab (Ausrücken)
        if key == Qt.Key.Key_Backtab or (key == Qt.Key.Key_Tab and (modifiers & Qt.KeyboardModifier.ShiftModifier)):
            self.unindent_cursors()
            return True

        # Navigation: Links / Rechts / Home / End
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
            self.move_cursors(key, event)
            return True

        # Ctrl+C (Kopieren)
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_C:
            self.copy_selection()
            return True

        # Ctrl+X (Ausschneiden)
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_X:
            self.cut_selection()
            return True

        # Ctrl+V (Einfügen)
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_V:
            self.paste_text()
            return True

        # Text-Eingabe (normale druckbare Zeichen)
        text = event.text()
        if text and not (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
            # Auto-Wrapping oder Auto-Pairing prüfen
            if text in AUTO_PAIRS:
                self.insert_pair_or_wrap(text)
            else:
                self.insert_text(text)
            return True

        return False

    def insert_text(self, text: str):
        """Fügt Text an allen Cursor-Positionen ein (absteigend nach Position sortiert)."""
        primary = self.editor.textCursor()
        all_c = [primary] + self.secondary_cursors

        primary.beginEditBlock()
        try:
            # Nach Dokument-Offset absteigend sortieren, damit sich frühere Offsets nicht verschieben
            sorted_indices = sorted(
                range(len(all_c)),
                key=lambda i: min(all_c[i].position(), all_c[i].anchor()),
                reverse=True
            )
            for idx in sorted_indices:
                c = all_c[idx]
                c.insertText(text)
        finally:
            primary.endEditBlock()

        self.editor.setTextCursor(all_c[0])
        self.secondary_cursors = all_c[1:]
        self.merge_cursors()
        self._notify_change()

    def insert_pair_or_wrap(self, open_char: str):
        """Ummantelt bestehende Auswahlen mit Klammern/Anführungszeichen oder fügt das Paar ein."""
        close_char = AUTO_PAIRS.get(open_char, open_char)
        primary = self.editor.textCursor()
        all_c = [primary] + self.secondary_cursors

        primary.beginEditBlock()
        try:
            sorted_indices = sorted(
                range(len(all_c)),
                key=lambda i: min(all_c[i].position(), all_c[i].anchor()),
                reverse=True
            )
            for idx in sorted_indices:
                c = all_c[idx]
                if c.hasSelection():
                    sel_text = c.selectedText().replace('\u2029', '\n')
                    c.insertText(f"{open_char}{sel_text}{close_char}")
                else:
                    c.insertText(f"{open_char}{close_char}")
                    c.movePosition(QTextCursor.MoveOperation.Left)
        finally:
            primary.endEditBlock()

        self.editor.setTextCursor(all_c[0])
        self.secondary_cursors = all_c[1:]
        self.merge_cursors()
        self._notify_change()

    def delete_backspace(self):
        """Löscht das Zeichen vor jedem Cursor oder die jeweilige Auswahl."""
        primary = self.editor.textCursor()
        all_c = [primary] + self.secondary_cursors

        primary.beginEditBlock()
        try:
            sorted_indices = sorted(
                range(len(all_c)),
                key=lambda i: min(all_c[i].position(), all_c[i].anchor()),
                reverse=True
            )
            for idx in sorted_indices:
                c = all_c[idx]
                if c.hasSelection():
                    c.removeSelectedText()
                else:
                    c.deletePreviousChar()
        finally:
            primary.endEditBlock()

        self.editor.setTextCursor(all_c[0])
        self.secondary_cursors = all_c[1:]
        self.merge_cursors()
        self._notify_change()

    def delete_forward(self):
        """Löscht das Zeichen nach jedem Cursor oder die jeweilige Auswahl."""
        primary = self.editor.textCursor()
        all_c = [primary] + self.secondary_cursors

        primary.beginEditBlock()
        try:
            sorted_indices = sorted(
                range(len(all_c)),
                key=lambda i: min(all_c[i].position(), all_c[i].anchor()),
                reverse=True
            )
            for idx in sorted_indices:
                c = all_c[idx]
                if c.hasSelection():
                    c.removeSelectedText()
                else:
                    c.deleteChar()
        finally:
            primary.endEditBlock()

        self.editor.setTextCursor(all_c[0])
        self.secondary_cursors = all_c[1:]
        self.merge_cursors()
        self._notify_change()

    def unindent_cursors(self):
        """Rückt alle Zeilen der aktiven Cursor aus (Dedent)."""
        tab_size = getattr(self.editor, "tab_size", 4)
        primary = self.editor.textCursor()
        all_c = self.all_cursors()

        # Eindeutige Blocknummern sammeln
        blocks = sorted({c.blockNumber() for c in all_c}, reverse=True)
        doc = self.editor.document()

        primary.beginEditBlock()
        try:
            for b_num in blocks:
                block = doc.findBlockByNumber(b_num)
                text = block.text()
                leading = 0
                for ch in text:
                    if ch == ' ':
                        leading += 1
                    elif ch == '\t':
                        leading += tab_size
                        break
                    else:
                        break
                to_remove = min(leading, tab_size)
                if to_remove > 0:
                    tc = QTextCursor(block)
                    tc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    for _ in range(to_remove):
                        tc.deleteChar()
        finally:
            primary.endEditBlock()

        self._notify_change()

    def move_cursors(self, key: Qt.Key, event: QKeyEvent):
        """Verschiebt alle Cursor synchron nach links, rechts, zum Zeilenanfang oder -ende."""
        keep_anchor = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        move_mode = QTextCursor.MoveMode.KeepAnchor if keep_anchor else QTextCursor.MoveMode.MoveAnchor
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

        if key == Qt.Key.Key_Left:
            op = QTextCursor.MoveOperation.WordLeft if ctrl else QTextCursor.MoveOperation.Left
        elif key == Qt.Key.Key_Right:
            op = QTextCursor.MoveOperation.WordRight if ctrl else QTextCursor.MoveOperation.Right
        elif key == Qt.Key.Key_Home:
            op = QTextCursor.MoveOperation.StartOfLine
        elif key == Qt.Key.Key_End:
            op = QTextCursor.MoveOperation.EndOfLine
        else:
            return

        all_c = [self.editor.textCursor()] + self.secondary_cursors
        for c in all_c:
            if not keep_anchor and c.hasSelection() and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                # Ohne Shift Auswahl zusammenklappen
                target_pos = min(c.position(), c.anchor()) if key == Qt.Key.Key_Left else max(c.position(), c.anchor())
                c.setPosition(target_pos)
            else:
                c.movePosition(op, move_mode)

        self.editor.setTextCursor(all_c[0])
        self.secondary_cursors = all_c[1:]
        self.merge_cursors()
        self._notify_change()

    def copy_selection(self):
        """Kopiert alle ausgewählten Textpassagen getrennt durch Zeilenumbrüche in die Zwischenablage."""
        all_c = self.all_cursors()
        selected_texts = [
            c.selectedText().replace('\u2029', '\n')
            for c in all_c
            if c.hasSelection()
        ]
        if selected_texts:
            QApplication.clipboard().setText("\n".join(selected_texts))
        else:
            lines = [c.block().text() for c in all_c]
            QApplication.clipboard().setText("\n".join(lines))

    def cut_selection(self):
        """Kopiert alle Auswahlen und löscht sie anschließend an allen Cursor-Positionen."""
        self.copy_selection()
        self.delete_backspace()

    def paste_text(self):
        """Fügt Zwischenablage-Inhalte ein. Falls Zeilenanzahl = Cursoranzahl, wird zeilenweise gematcht."""
        clip_text = QApplication.clipboard().text()
        if not clip_text:
            return

        primary = self.editor.textCursor()
        all_c = [primary] + self.secondary_cursors
        lines = clip_text.splitlines()

        # Falls genau so viele Zeilen wie Cursor vorliegen, zeilenweise einfügen
        if len(lines) == len(all_c):
            primary.beginEditBlock()
            try:
                sorted_indices = sorted(
                    range(len(all_c)),
                    key=lambda i: min(all_c[i].position(), all_c[i].anchor()),
                    reverse=True
                )
                for idx in sorted_indices:
                    all_c[idx].insertText(lines[idx])
            finally:
                primary.endEditBlock()

            self.editor.setTextCursor(all_c[0])
            self.secondary_cursors = all_c[1:]
            self.merge_cursors()
            self._notify_change()
        else:
            self.insert_text(clip_text)

    def get_extra_selections(self) -> List[QTextEdit.ExtraSelection]:
        """Erstellt visuelle ExtraSelections für alle sekundären Auswahlen."""
        selections: List[QTextEdit.ExtraSelection] = []
        if not self.secondary_cursors:
            return selections

        sel_format = QTextCharFormat()
        sel_format.setBackground(QColor(38, 79, 120))  # Standard VS Code Dark Selection (#264f78)
        sel_format.setForeground(QColor(255, 255, 255))

        for c in self.secondary_cursors:
            if c.hasSelection():
                sel = QTextEdit.ExtraSelection()
                sel.format = sel_format
                sel.cursor = c
                selections.append(sel)

        return selections

    def paint_extra_carets(self, editor: QPlainTextEdit):
        """Zeichnet für alle sekundären Cursor eine scharfe Caret-Linie im Editor-Viewport."""
        if not self.secondary_cursors:
            return

        painter = QPainter(editor.viewport())
        # Cursor-Farbe: Aus Vordergrundfarbe des Editors ableiten
        caret_color = editor.palette().color(editor.foregroundRole())
        if not caret_color.isValid() or caret_color.alpha() == 0:
            caret_color = QColor(255, 255, 255)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(caret_color)

        viewport_rect = editor.viewport().rect()
        for cursor in self.secondary_cursors:
            rect = editor.cursorRect(cursor)
            caret_rect = QRect(rect.x(), rect.y(), 2, rect.height())
            if caret_rect.intersects(viewport_rect):
                painter.drawRect(caret_rect)

        painter.end()
