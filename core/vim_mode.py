#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vim Mode Engine - Modales Editieren für CodeBox (Normal, Insert, Visual, Visual Line).

Bietet die kanonische Vim-Zustandsmaschine für CodeEditor:
- NORMAL: Effiziente Navigation (h/j/k/l, w/b/e, 0/^/$, gg/G), Ziffern-Präfixe (z.B. 3w, 5j),
  Operatoren (dd, dw, de, d$, cc, cw, yy, p, P, x, r, ~, J, >>, <<, u, Ctrl+R).
- INSERT: Gewohntes Tippen, Rückkehr zu NORMAL per Escape oder Ctrl+[.
- VISUAL: Zeichenweise Markierung mit selektiven Transformationen (d, y, c, >, <, u, U, ~).
- VISUAL_LINE: Zeilenweise Markierung für ganze Codeblöcke.
- Block-Cursor im Normal-/Visual-Modus, I-Beam im Insert-Modus.
- Statusbar-Feedback mit Modusanzeige (-- NORMAL --, -- INSERT --, etc.) und Befehlspuffer.
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple, TYPE_CHECKING
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import (
    QTextCursor, QKeyEvent, QGuiApplication, QFontMetrics
)

if TYPE_CHECKING:
    from core.editor import CodeEditor


class VimMode(str, Enum):
    """Zustände der Vim-Engine."""
    NORMAL = "NORMAL"
    INSERT = "INSERT"
    VISUAL = "VISUAL"
    VISUAL_LINE = "VISUAL_LINE"


def char_type(c: str) -> int:
    """Klassifiziert Zeichen nach Vim-Wortregeln: 0 = Whitespace, 1 = Wort (alnum/_), 2 = Sonstige."""
    if c.isspace():
        return 0
    if c.isalnum() or c == '_':
        return 1
    return 2


def find_next_word_start(text: str, pos: int) -> int:
    """Findet den Anfang des nächsten Worts im Text ab Position pos."""
    length = len(text)
    if pos >= length:
        return length

    ctype = char_type(text[pos])
    i = pos
    if ctype != 0:
        # Aktuelles Wort gleichen Typs überspringen
        while i < length and char_type(text[i]) == ctype:
            i += 1
    # Whitespace überspringen
    while i < length and text[i].isspace():
        i += 1
    return min(i, length)


def find_prev_word_start(text: str, pos: int) -> int:
    """Findet den Anfang des vorherigen Worts im Text vor Position pos."""
    if pos <= 0:
        return 0

    i = pos - 1
    # Führenden Whitespace rückwärts überspringen
    while i > 0 and text[i].isspace():
        i -= 1
    if i <= 0:
        return 0

    target_type = char_type(text[i])
    while i > 0 and char_type(text[i - 1]) == target_type:
        i -= 1
    return max(0, i)


def find_next_word_end(text: str, pos: int) -> int:
    """Findet das Ende des aktuellen oder nächsten Worts im Text ab Position pos."""
    length = len(text)
    if pos >= length - 1:
        return max(0, length - 1)

    i = pos + 1
    # Whitespace überspringen falls am Wortende
    while i < length and text[i].isspace():
        i += 1
    if i >= length:
        return max(0, length - 1)

    target_type = char_type(text[i])
    while i + 1 < length and char_type(text[i + 1]) == target_type:
        i += 1
    return min(i, length - 1)


class VimEngine(QObject):
    """Zentrale Vim-Zustandsmaschine für einen CodeEditor."""

    modeChanged = Signal(str)
    commandBufferChanged = Signal(str)
    statusMessage = Signal(str)
    findRequested = Signal(bool)  # True = vorwärts (/), False = rückwärts (?)

    def __init__(self, editor: CodeEditor, parent=None):
        super().__init__(parent or editor)
        self.editor = editor
        self._enabled: bool = False
        self._mode: VimMode = VimMode.NORMAL

        self._count_buffer: str = ""
        self._operator_buffer: str = ""
        self._visual_anchor: int = 0
        self._visual_line_start: int = 0

        self._register_text: str = ""
        self._register_is_line: bool = False

    # ---- Aktivierung & Modus ----

    def is_enabled(self) -> bool:
        """Prüft, ob der Vim-Modus aktiv ist."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Aktiviert oder deaktiviert den Vim-Modus."""
        self._enabled = bool(enabled)
        if self._enabled:
            self.set_mode(VimMode.NORMAL)
        else:
            self._update_cursor_width()
            self.modeChanged.emit("")
            self.commandBufferChanged.emit("")

    def get_mode(self) -> VimMode:
        """Gibt den aktuellen Vim-Zustand zurück."""
        return self._mode

    def set_mode(self, mode: VimMode):
        """Wechselt den Zustand der Zustandsmaschine."""
        if not self._enabled:
            self._mode = mode
            return

        self._mode = mode
        self.reset_buffers()

        tc = self.editor.textCursor()

        if mode == VimMode.NORMAL:
            tc.clearSelection()
            self.editor.setTextCursor(tc)
            self._update_cursor_width()
        elif mode == VimMode.INSERT:
            self._update_cursor_width()
        elif mode == VimMode.VISUAL:
            self._visual_anchor = tc.position()
            if not tc.atBlockEnd() and not tc.hasSelection():
                tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                self.editor.setTextCursor(tc)
            self._update_cursor_width()
        elif mode == VimMode.VISUAL_LINE:
            block = tc.block()
            self._visual_line_start = block.blockNumber()
            self._update_visual_line_selection(self._visual_line_start)
            self._update_cursor_width()

        self.modeChanged.emit(self._mode.value)

    def _update_cursor_width(self):
        """Aktualisiert die Cursor-Breite (Block-Cursor im Normal-/Visual-Modus, I-Beam im Insert-Modus)."""
        if not self._enabled:
            self.editor.setCursorWidth(1)
            return

        if self._mode in (VimMode.NORMAL, VimMode.VISUAL, VimMode.VISUAL_LINE):
            fm: QFontMetrics = self.editor.fontMetrics()
            char_w = fm.horizontalAdvance(' ') if hasattr(fm, 'horizontalAdvance') else fm.width(' ')
            self.editor.setCursorWidth(max(2, char_w))
        else:
            self.editor.setCursorWidth(2)

    def reset_buffers(self):
        """Setzt Ziffern- und Operator-Puffer zurück."""
        self._count_buffer = ""
        self._operator_buffer = ""
        self.commandBufferChanged.emit("")

    def get_command_buffer(self) -> str:
        """Gibt den formatierten aktuellen Befehlspuffer zurück (z.B. '3d')."""
        buf = ""
        if self._count_buffer:
            buf += self._count_buffer
        if self._operator_buffer:
            buf += self._operator_buffer
        return buf

    def _get_count(self) -> int:
        """Gibt den aktuellen Zähler-Multiplikator zurück (mindestens 1)."""
        if self._count_buffer:
            try:
                val = int(self._count_buffer)
                return max(1, val)
            except ValueError:
                return 1
        return 1

    # ---- Register & Zwischenablage ----

    def _set_register(self, text: str, is_line: bool = False):
        """Speichert Text im internen Vim-Register und synchronisiert die System-Zwischenablage."""
        self._register_text = text
        self._register_is_line = is_line
        try:
            cb = QGuiApplication.clipboard()
            if cb:
                cb.setText(text)
        except Exception:
            pass

    def _get_register(self) -> Tuple[str, bool]:
        """Liest den aktuellen Register-Text und den Zeilen-Status aus."""
        if self._register_text:
            return self._register_text, self._register_is_line
        try:
            cb = QGuiApplication.clipboard()
            if cb:
                txt = cb.text()
                if txt:
                    return txt, txt.endswith('\n')
        except Exception:
            pass
        return "", False

    # ---- Tastenverarbeitung ----

    def handle_key_event(self, event: QKeyEvent) -> bool:
        """Fängt Tastaturevents für die Vim-Engine ab.

        Returns:
            True, wenn das Event von der Vim-Engine konsumiert wurde.
            False, wenn es an das Standard-Editorhandling weitergereicht werden soll.
        """
        if not self._enabled:
            return False

        # INSERT-Modus
        if self._mode == VimMode.INSERT:
            return self._handle_insert_mode(event)

        # VISUAL & VISUAL_LINE Modus
        if self._mode in (VimMode.VISUAL, VimMode.VISUAL_LINE):
            return self._handle_visual_mode(event)

        # NORMAL-Modus
        return self._handle_normal_mode(event)

    def _handle_insert_mode(self, event: QKeyEvent) -> bool:
        """Verarbeitet Tastaturevents im Insert-Modus."""
        key = event.key()
        modifiers = event.modifiers()

        # Escape oder Ctrl+[ verlässt den Insert-Modus
        if key == Qt.Key.Key_Escape or (
            bool(modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_BracketLeft
        ):
            tc = self.editor.textCursor()
            if tc.positionInBlock() > 0:
                tc.movePosition(QTextCursor.MoveOperation.Left)
                self.editor.setTextCursor(tc)
            self.set_mode(VimMode.NORMAL)
            return True

        return False

    def _handle_visual_mode(self, event: QKeyEvent) -> bool:
        """Verarbeitet Tastaturevents im Visual- und Visual-Line-Modus."""
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()

        # Escape oder Ctrl+[ bricht Visual-Modus ab
        if key == Qt.Key.Key_Escape or (
            bool(modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_BracketLeft
        ):
            self.set_mode(VimMode.NORMAL)
            return True

        # v / V zum Umschalten oder Beenden
        if text == 'v':
            if self._mode == VimMode.VISUAL:
                self.set_mode(VimMode.NORMAL)
            else:
                self.set_mode(VimMode.VISUAL)
            return True
        if text == 'V':
            if self._mode == VimMode.VISUAL_LINE:
                self.set_mode(VimMode.NORMAL)
            else:
                self.set_mode(VimMode.VISUAL_LINE)
            return True

        # Ziffern-Multiplikator
        if text in "123456789" or (text == "0" and self._count_buffer):
            self._count_buffer += text
            self.commandBufferChanged.emit(self.get_command_buffer())
            return True

        count = self._get_count()

        # Löschen (d oder x)
        if text in ('d', 'x') or key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            tc = self.editor.textCursor()
            sel = tc.selectedText().replace("\u2029", "\n")
            is_line = (self._mode == VimMode.VISUAL_LINE)
            if is_line and not sel.endswith("\n"):
                sel += "\n"
            self._set_register(sel, is_line=is_line)
            tc.removeSelectedText()
            self.set_mode(VimMode.NORMAL)
            return True

        # Ändern (c)
        if text == 'c':
            tc = self.editor.textCursor()
            sel = tc.selectedText().replace("\u2029", "\n")
            is_line = (self._mode == VimMode.VISUAL_LINE)
            self._set_register(sel, is_line=is_line)
            tc.removeSelectedText()
            self.set_mode(VimMode.INSERT)
            return True

        # Kopieren / Yank (y)
        if text == 'y':
            tc = self.editor.textCursor()
            sel = tc.selectedText().replace("\u2029", "\n")
            is_line = (self._mode == VimMode.VISUAL_LINE)
            if is_line and not sel.endswith("\n"):
                sel += "\n"
            self._set_register(sel, is_line=is_line)
            self.set_mode(VimMode.NORMAL)
            self.statusMessage.emit("Yanked selection")
            return True

        # Einrücken / Ausrücken (> / <)
        if text == '>':
            self.editor.indent_selection()
            self.set_mode(VimMode.NORMAL)
            return True
        if text == '<':
            self.editor.unindent_selection()
            self.set_mode(VimMode.NORMAL)
            return True

        # Case-Transformation (~, u, U)
        if text == '~':
            tc = self.editor.textCursor()
            sel = tc.selectedText()
            tc.insertText(sel.swapcase())
            self.set_mode(VimMode.NORMAL)
            return True
        if text == 'u':
            tc = self.editor.textCursor()
            sel = tc.selectedText()
            tc.insertText(sel.lower())
            self.set_mode(VimMode.NORMAL)
            return True
        if text == 'U':
            tc = self.editor.textCursor()
            sel = tc.selectedText()
            tc.insertText(sel.upper())
            self.set_mode(VimMode.NORMAL)
            return True

        # Navigation im Visual-Modus
        if self._mode == VimMode.VISUAL:
            handled = self._navigate_visual_char(key, text, count)
        else:
            handled = self._navigate_visual_line(key, text, count)

        if handled:
            self.reset_buffers()
            return True

        return True

    def _navigate_visual_char(self, key: int, text: str, count: int) -> bool:
        """Bewegt das aktive Ende der zeichenweisen Markierung."""
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()

        new_pos = pos
        if text == 'h' or key == Qt.Key.Key_Left:
            new_pos = max(0, pos - count)
        elif text == 'l' or key == Qt.Key.Key_Right:
            new_pos = min(len(full_text), pos + count)
        elif text == 'j' or key == Qt.Key.Key_Down:
            tc.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, count)
            new_pos = tc.position()
        elif text == 'k' or key == Qt.Key.Key_Up:
            tc.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, count)
            new_pos = tc.position()
        elif text == 'w':
            for _ in range(count):
                new_pos = find_next_word_start(full_text, new_pos)
        elif text == 'b':
            for _ in range(count):
                new_pos = find_prev_word_start(full_text, new_pos)
        elif text == 'e':
            for _ in range(count):
                new_pos = find_next_word_end(full_text, new_pos)
            new_pos = min(len(full_text), new_pos + 1)
        elif text == '0' or key == Qt.Key.Key_Home:
            tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
            new_pos = tc.position()
        elif text == '$' or key == Qt.Key.Key_End:
            tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
            new_pos = tc.position()
        elif text == '^':
            tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
            block_text = tc.block().text()
            indent = len(block_text) - len(block_text.lstrip())
            new_pos = tc.position() + indent
        elif text == 'G':
            tc.movePosition(QTextCursor.MoveOperation.End)
            new_pos = tc.position()
        else:
            return False

        # Markierung von Anker bis new_pos aufbauen
        tc.setPosition(self._visual_anchor)
        tc.setPosition(new_pos, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(tc)
        return True

    def _navigate_visual_line(self, key: int, text: str, count: int) -> bool:
        """Erweitert die zeilenweise Markierung nach oben oder unten."""
        tc = self.editor.textCursor()
        cur_line = tc.blockNumber()

        new_line = cur_line
        if text == 'j' or key == Qt.Key.Key_Down:
            new_line = cur_line + count
        elif text == 'k' or key == Qt.Key.Key_Up:
            new_line = max(0, cur_line - count)
        elif text == 'G':
            new_line = self.editor.document().blockCount() - 1
        elif text == 'g':
            new_line = 0
        else:
            return False

        self._update_visual_line_selection(new_line)
        return True

    def _update_visual_line_selection(self, target_line: int):
        """Markiert vollständige Zeilen zwischen dem Zeilenanker und target_line."""
        doc = self.editor.document()
        max_blocks = doc.blockCount()
        target_line = max(0, min(max_blocks - 1, target_line))

        start_line = min(self._visual_line_start, target_line)
        end_line = max(self._visual_line_start, target_line)

        b1 = doc.findBlockByNumber(start_line)
        b2 = doc.findBlockByNumber(end_line)

        tc = QTextCursor(doc)
        tc.setPosition(b1.position())
        if b2.next().isValid():
            tc.setPosition(b2.next().position(), QTextCursor.MoveMode.KeepAnchor)
        else:
            tc.setPosition(b2.position() + b2.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(tc)

    # ---- NORMAL Modus ----

    def _handle_normal_mode(self, event: QKeyEvent) -> bool:
        """Verarbeitet Tastaturevents im Normal-Modus."""
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        # Escape bricht Operator- und Ziffernpuffer ab
        if key == Qt.Key.Key_Escape or (ctrl and key == Qt.Key.Key_BracketLeft):
            self.reset_buffers()
            tc = self.editor.textCursor()
            tc.clearSelection()
            self.editor.setTextCursor(tc)
            return True

        # Ziffernpräfix sammeln (außer führendes 0, das ist Zeilenanfang)
        if not self._operator_buffer and (
            text in "123456789" or (text == "0" and self._count_buffer)
        ):
            self._count_buffer += text
            self.commandBufferChanged.emit(self.get_command_buffer())
            return True

        # Sub-Operator Handling (wenn Operator aktiv ist)
        if self._operator_buffer:
            return self._handle_operator_subcommand(key, text, ctrl)

        # Standalone Navigation
        if text == 'h' or key == Qt.Key.Key_Left:
            self._move_h(self._get_count())
            self.reset_buffers()
            return True
        if text == 'l' or key == Qt.Key.Key_Right:
            self._move_l(self._get_count())
            self.reset_buffers()
            return True
        if text == 'j' or key == Qt.Key.Key_Down:
            self._move_j(self._get_count())
            self.reset_buffers()
            return True
        if text == 'k' or key == Qt.Key.Key_Up:
            self._move_k(self._get_count())
            self.reset_buffers()
            return True

        # Wort-Navigation
        if text == 'w':
            self._move_w(self._get_count())
            self.reset_buffers()
            return True
        if text == 'b':
            self._move_b(self._get_count())
            self.reset_buffers()
            return True
        if text == 'e':
            self._move_e(self._get_count())
            self.reset_buffers()
            return True

        # Zeilen-Navigation
        if text == '0' or key == Qt.Key.Key_Home:
            self._move_0()
            self.reset_buffers()
            return True
        if text == '^':
            self._move_caret()
            self.reset_buffers()
            return True
        if text == '$' or key == Qt.Key.Key_End:
            self._move_dollar()
            self.reset_buffers()
            return True

        # Datei-Navigation
        if text == 'G':
            self._move_G(self._get_count() if self._count_buffer else 0)
            self.reset_buffers()
            return True

        # Halbseiten-/Ganzseiten-Scroll
        if ctrl and key == Qt.Key.Key_D:
            self._scroll_half_page(down=True)
            return True
        if ctrl and key == Qt.Key.Key_U:
            self._scroll_half_page(down=False)
            return True

        # Modus-Wechsel in INSERT
        if text == 'i':
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'I':
            self._move_caret()
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'a':
            tc = self.editor.textCursor()
            if not tc.atBlockEnd():
                tc.movePosition(QTextCursor.MoveOperation.Right)
                self.editor.setTextCursor(tc)
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'A':
            tc = self.editor.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
            self.editor.setTextCursor(tc)
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'o':
            self._insert_newline_below()
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'O':
            self._insert_newline_above()
            self.set_mode(VimMode.INSERT)
            return True

        # Modus-Wechsel in VISUAL
        if text == 'v':
            self.set_mode(VimMode.VISUAL)
            return True
        if text == 'V':
            self.set_mode(VimMode.VISUAL_LINE)
            return True

        # Löschen & Ersetzen
        if text == 'x' or key == Qt.Key.Key_Delete:
            self._delete_char(self._get_count())
            self.reset_buffers()
            return True
        if text == 'X' or key == Qt.Key.Key_Backspace:
            self._backspace_char(self._get_count())
            self.reset_buffers()
            return True
        if text == 's':
            self._delete_char(1)
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'S':
            self._change_lines(1)
            return True
        if text == 'D':
            self._delete_to_end_of_line()
            self.reset_buffers()
            return True
        if text == 'C':
            self._delete_to_end_of_line()
            self.set_mode(VimMode.INSERT)
            return True
        if text == 'Y':
            self._yank_lines(1)
            self.reset_buffers()
            return True

        # Paste (p / P)
        if text == 'p':
            self._paste_after(self._get_count())
            self.reset_buffers()
            return True
        if text == 'P':
            self._paste_before(self._get_count())
            self.reset_buffers()
            return True

        # Undo / Redo
        if text == 'u':
            self.editor.undo()
            self.reset_buffers()
            return True
        if ctrl and key == Qt.Key.Key_R:
            self.editor.redo()
            self.reset_buffers()
            return True

        # Join Lines (J)
        if text == 'J':
            self._join_lines()
            self.reset_buffers()
            return True

        # Toggle Case (~)
        if text == '~':
            self._toggle_case()
            self.reset_buffers()
            return True

        # Suche (/)
        if text == '/':
            self.findRequested.emit(True)
            self.reset_buffers()
            return True

        # Operator-Puffer starten
        if text in ('d', 'c', 'y', 'g', 'r', '>', '<'):
            self._operator_buffer = text
            self.commandBufferChanged.emit(self.get_command_buffer())
            return True

        return True

    def _handle_operator_subcommand(self, key: int, text: str, ctrl: bool) -> bool:
        """Verarbeitet den Folgebefehl für einen aktiven Operator (z.B. dd, dw, cw, gg, rX)."""
        op = self._operator_buffer
        count = self._get_count()

        # Replace single char (r<char>)
        if op == 'r':
            if text and key not in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                tc = self.editor.textCursor()
                if not tc.atBlockEnd():
                    tc.deleteChar()
                    tc.insertText(text * count)
                    tc.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, max(0, count - 1))
                    self.editor.setTextCursor(tc)
            self.reset_buffers()
            return True

        # gg Motion
        if op == 'g':
            if text == 'g':
                self._move_gg(count if self._count_buffer else 1)
            self.reset_buffers()
            return True

        # Line-wise Indent (>> / <<)
        if op == '>' and text == '>':
            self.editor.indent_selection()
            self.reset_buffers()
            return True
        if op == '<' and text == '<':
            self.editor.unindent_selection()
            self.reset_buffers()
            return True

        # Operator d (Delete)
        if op == 'd':
            if text == 'd':
                self._delete_lines(count)
                self.reset_buffers()
                return True
            if text == 'w':
                self._delete_words(count)
                self.reset_buffers()
                return True
            if text == 'e':
                self._delete_to_word_end(count)
                self.reset_buffers()
                return True
            if text == '$':
                self._delete_to_end_of_line()
                self.reset_buffers()
                return True
            if text == '0':
                self._delete_to_start_of_line()
                self.reset_buffers()
                return True
            if text == 'G':
                self._delete_to_end_of_file()
                self.reset_buffers()
                return True

        # Operator c (Change)
        if op == 'c':
            if text == 'c':
                self._change_lines(count)
                return True
            if text == 'w':
                self._delete_to_word_end(count)
                self.set_mode(VimMode.INSERT)
                return True
            if text == 'e':
                self._delete_to_word_end(count)
                self.set_mode(VimMode.INSERT)
                return True
            if text == '$':
                self._delete_to_end_of_line()
                self.set_mode(VimMode.INSERT)
                return True

        # Operator y (Yank)
        if op == 'y':
            if text == 'y':
                self._yank_lines(count)
                self.reset_buffers()
                return True
            if text == 'w':
                self._yank_words(count)
                self.reset_buffers()
                return True
            if text == '$':
                self._yank_to_end_of_line()
                self.reset_buffers()
                return True

        # Unbekannte Kombination abbringen
        self.reset_buffers()
        return True

    # ---- Navigation Implementierung ----

    def _move_h(self, count: int):
        tc = self.editor.textCursor()
        col = tc.positionInBlock()
        steps = min(col, count)
        tc.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, steps)
        self.editor.setTextCursor(tc)

    def _move_l(self, count: int):
        tc = self.editor.textCursor()
        line_len = len(tc.block().text())
        col = tc.positionInBlock()
        max_col = max(0, line_len - 1)
        steps = max(0, min(max_col - col, count))
        tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, steps)
        self.editor.setTextCursor(tc)

    def _move_j(self, count: int):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, count)
        self._ensure_cursor_not_past_end(tc)
        self.editor.setTextCursor(tc)

    def _move_k(self, count: int):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, count)
        self._ensure_cursor_not_past_end(tc)
        self.editor.setTextCursor(tc)

    def _ensure_cursor_not_past_end(self, tc: QTextCursor):
        block_text = tc.block().text()
        if len(block_text) > 0 and tc.positionInBlock() >= len(block_text):
            tc.movePosition(QTextCursor.MoveOperation.Left)

    def _move_w(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_next_word_start(full_text, pos)
        tc.setPosition(pos)
        self.editor.setTextCursor(tc)

    def _move_b(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_prev_word_start(full_text, pos)
        tc.setPosition(pos)
        self.editor.setTextCursor(tc)

    def _move_e(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_next_word_end(full_text, pos)
        tc.setPosition(pos)
        self.editor.setTextCursor(tc)

    def _move_0(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
        self.editor.setTextCursor(tc)

    def _move_caret(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
        text = tc.block().text()
        indent = len(text) - len(text.lstrip())
        tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, indent)
        self.editor.setTextCursor(tc)

    def _move_dollar(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
        if len(tc.block().text()) > 0 and tc.positionInBlock() > 0:
            tc.movePosition(QTextCursor.MoveOperation.Left)
        self.editor.setTextCursor(tc)

    def _move_gg(self, target_line_1_based: int):
        doc = self.editor.document()
        block_num = max(0, min(doc.blockCount() - 1, target_line_1_based - 1))
        block = doc.findBlockByNumber(block_num)
        if block.isValid():
            tc = QTextCursor(block)
            self.editor.setTextCursor(tc)

    def _move_G(self, target_line_1_based: int):
        doc = self.editor.document()
        if target_line_1_based > 0:
            block_num = max(0, min(doc.blockCount() - 1, target_line_1_based - 1))
        else:
            block_num = doc.blockCount() - 1
        block = doc.findBlockByNumber(block_num)
        if block.isValid():
            tc = QTextCursor(block)
            self.editor.setTextCursor(tc)

    def _scroll_half_page(self, down: bool):
        sb = self.editor.verticalScrollBar()
        step = max(1, sb.pageStep() // 2)
        if down:
            sb.setValue(sb.value() + step)
            self._move_j(max(1, step // 20))
        else:
            sb.setValue(sb.value() - step)
            self._move_k(max(1, step // 20))

    # ---- Edit & Operator Implementierung ----

    def _insert_newline_below(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
        line = tc.block().text()
        indent = len(line) - len(line.lstrip())
        provider = getattr(self.editor, '_provider', None)
        triggers = provider.get_indent_triggers() if provider else [':', '{']
        if any(line.rstrip().endswith(t) for t in triggers):
            indent += getattr(self.editor, 'tab_size', 4)
        tc.insertText("\n" + " " * indent)
        self.editor.setTextCursor(tc)

    def _insert_newline_above(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
        line = tc.block().text()
        indent = len(line) - len(line.lstrip())
        tc.insertText(" " * indent + "\n")
        tc.movePosition(QTextCursor.MoveOperation.Up)
        tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
        self.editor.setTextCursor(tc)

    def _delete_char(self, count: int):
        tc = self.editor.textCursor()
        if not tc.atBlockEnd():
            rem = len(tc.block().text()) - tc.positionInBlock()
            del_len = min(count, rem)
            tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, del_len)
            self._set_register(tc.selectedText(), is_line=False)
            tc.removeSelectedText()
            self._ensure_cursor_not_past_end(tc)
            self.editor.setTextCursor(tc)

    def _backspace_char(self, count: int):
        tc = self.editor.textCursor()
        col = tc.positionInBlock()
        if col > 0:
            del_len = min(count, col)
            tc.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, del_len)
            self._set_register(tc.selectedText(), is_line=False)
            tc.removeSelectedText()
            self.editor.setTextCursor(tc)

    def _delete_lines(self, count: int):
        tc = self.editor.textCursor()
        start_block = tc.block()
        end_block = start_block
        for _ in range(count - 1):
            if end_block.next().isValid():
                end_block = end_block.next()

        tc.setPosition(start_block.position())
        if end_block.next().isValid():
            tc.setPosition(end_block.next().position(), QTextCursor.MoveMode.KeepAnchor)
        else:
            if start_block.previous().isValid():
                prev_block = start_block.previous()
                tc.setPosition(prev_block.position() + prev_block.length() - 1)
            tc.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)

        del_text = tc.selectedText().replace("\u2029", "\n")
        if not del_text.endswith("\n"):
            del_text += "\n"
        self._set_register(del_text, is_line=True)
        tc.removeSelectedText()
        self._ensure_cursor_not_past_end(tc)
        self.editor.setTextCursor(tc)

    def _change_lines(self, count: int):
        tc = self.editor.textCursor()
        start_block = tc.block()
        text = start_block.text()
        indent = len(text) - len(text.lstrip())

        self._delete_lines(count)
        tc = self.editor.textCursor()
        tc.insertText(" " * indent)
        self.editor.setTextCursor(tc)
        self.set_mode(VimMode.INSERT)

    def _delete_to_end_of_line(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        tc.removeSelectedText()
        self.editor.setTextCursor(tc)

    def _delete_to_start_of_line(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        tc.removeSelectedText()
        self.editor.setTextCursor(tc)

    def _delete_words(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_next_word_start(full_text, pos)
        tc.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        tc.removeSelectedText()
        self.editor.setTextCursor(tc)

    def _delete_to_word_end(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_next_word_end(full_text, pos)
        tc.setPosition(min(len(full_text), pos + 1), QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        tc.removeSelectedText()
        self.editor.setTextCursor(tc)

    def _delete_to_end_of_file(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
        tc.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=True)
        tc.removeSelectedText()
        self.editor.setTextCursor(tc)

    def _yank_lines(self, count: int):
        tc = self.editor.textCursor()
        block = tc.block()
        lines = []
        for _ in range(count):
            lines.append(block.text())
            if not block.next().isValid():
                break
            block = block.next()
        yanked = "\n".join(lines) + "\n"
        self._set_register(yanked, is_line=True)
        self.statusMessage.emit(f"{len(lines)} line(s) yanked")

    def _yank_words(self, count: int):
        tc = self.editor.textCursor()
        pos = tc.position()
        full_text = self.editor.toPlainText()
        for _ in range(count):
            pos = find_next_word_start(full_text, pos)
        tc.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        self.statusMessage.emit("Word yanked")

    def _yank_to_end_of_line(self):
        tc = self.editor.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        self._set_register(tc.selectedText(), is_line=False)
        self.statusMessage.emit("Yanked to end of line")

    def _paste_after(self, count: int):
        text, is_line = self._get_register()
        if not text:
            return
        tc = self.editor.textCursor()
        tc.beginEditBlock()
        for _ in range(count):
            if is_line:
                tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
                tc.insertText("\n" + text.rstrip("\n"))
            else:
                if not tc.atBlockEnd():
                    tc.movePosition(QTextCursor.MoveOperation.Right)
                tc.insertText(text)
        tc.endEditBlock()
        self.editor.setTextCursor(tc)

    def _paste_before(self, count: int):
        text, is_line = self._get_register()
        if not text:
            return
        tc = self.editor.textCursor()
        tc.beginEditBlock()
        for _ in range(count):
            if is_line:
                tc.movePosition(QTextCursor.MoveOperation.StartOfLine)
                tc.insertText(text.rstrip("\n") + "\n")
                tc.movePosition(QTextCursor.MoveOperation.Up)
            else:
                tc.insertText(text)
        tc.endEditBlock()
        self.editor.setTextCursor(tc)

    def _join_lines(self):
        tc = self.editor.textCursor()
        block = tc.block()
        nxt = block.next()
        if nxt.isValid():
            tc.beginEditBlock()
            tc.setPosition(block.position() + len(block.text()))
            text2 = nxt.text()
            lead_spaces = len(text2) - len(text2.lstrip())
            tc.setPosition(nxt.position() + lead_spaces, QTextCursor.MoveMode.KeepAnchor)
            tc.insertText(" ")
            tc.endEditBlock()
            self.editor.setTextCursor(tc)

    def _toggle_case(self):
        tc = self.editor.textCursor()
        if not tc.atBlockEnd():
            tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            ch = tc.selectedText()
            tc.insertText(ch.swapcase())
            self.editor.setTextCursor(tc)
