#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CodeEditor - Erweiterter Editor mit Zeilennummern, Bracket Matching und Auto-Completion"""

from typing import List, Dict
from PySide6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QCompleter
)
from PySide6.QtCore import Qt, QSize, QRect, Signal
from PySide6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QTextCharFormat, QTextCursor
)


class LineNumberArea(QWidget):
    """Zeichnet Zeilennummern für den CodeEditor"""
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class Minimap(QWidget):
    """Kompakte Code-Vorschau mit synchronisiertem Editor-Viewport.

    Die Vorschau malt alle Dokumentzeilen in eine schmale, nicht editierbare
    Fläche. Ein Klick oder Ziehen positioniert die vertikale Scrollbar des
    Haupteditors an der entsprechenden Dokumentstelle.
    """

    WIDTH = 110

    def __init__(self, editor: "CodeEditor", parent=None):
        super().__init__(parent or editor)
        self.editor = editor
        self.viewport_rect = QRect()
        self._dragging = False
        self.setFixedWidth(self.WIDTH)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Minimap: klicken oder ziehen, um zu navigieren")
        self.setStyleSheet(
            "QWidget { background-color: #1a1a1a; "
            "border-left: 1px solid #333; }"
        )

        self._cached_lines = None
        self._cached_max_chars = 1

        editor.textChanged.connect(self._invalidate_cache)
        editor.cursorPositionChanged.connect(self.update)
        editor.blockCountChanged.connect(lambda _count: self._invalidate_cache())
        editor.updateRequest.connect(self._editor_update_requested)
        editor.verticalScrollBar().valueChanged.connect(lambda _value: self.update())
        editor.document().contentsChanged.connect(self._invalidate_cache)

    def _editor_update_requested(self, _rect, _dy):
        """Zeichnet die Vorschau nach Scroll- und Viewport-Updates neu."""
        self.update()

    def _invalidate_cache(self):
        self._cached_lines = None
        self.update()

    def _document_lines(self):
        if self._cached_lines is not None:
            return self._cached_lines
        document = self.editor.document()
        block = document.firstBlock()
        lines = []
        max_c = 1
        while block.isValid():
            t = block.text()
            lines.append(t)
            if len(t) > max_c:
                max_c = len(t)
            block = block.next()
        self._cached_lines = lines or [""]
        self._cached_max_chars = max_c
        return self._cached_lines

    def _visible_block_range(self, line_count):
        first = self.editor.firstVisibleBlock()
        if not first.isValid():
            return 0, min(1, line_count)

        start = max(0, first.blockNumber())
        end = min(line_count, start + 1)
        block = first
        viewport_height = self.editor.viewport().height()
        while block.isValid():
            top = int(self.editor.blockBoundingGeometry(block)
                      .translated(self.editor.contentOffset()).top())
            bottom = top + int(self.editor.blockBoundingRect(block).height())
            if top > viewport_height:
                break
            if bottom >= 0:
                end = min(line_count, block.blockNumber() + 1)
            block = block.next()
        return start, max(start + 1, end)

    def _update_viewport_rect(self, line_count):
        start, end = self._visible_block_range(line_count)
        height = max(1, self.height())
        top = int(start * height / line_count)
        bottom = int(end * height / line_count)
        self.viewport_rect = QRect(0, top, self.width(), max(4, bottom - top))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(26, 26, 26))

        lines = self._document_lines()
        line_count = len(lines)
        self._update_viewport_rect(line_count)
        height = max(1, self.height())
        width = max(1, self.width() - 8)
        max_chars = max(1, self._cached_max_chars)

        for index, line in enumerate(lines):
            y = int(index * height / line_count)
            next_y = int((index + 1) * height / line_count)
            line_height = max(1, next_y - y)
            text = line.expandtabs(4).strip()
            if not text:
                continue
            bar_width = max(2, min(width, 3 + int(width * len(text) / max_chars)))
            if text.startswith(("#", "//", "/*", "*")):
                color = QColor(82, 120, 82)
            elif text.startswith(("def ", "class ", "function ")):
                color = QColor(90, 140, 205)
            else:
                color = QColor(125, 125, 125)
            painter.fillRect(4, y, bar_width, max(1, min(2, line_height)), color)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(100, 100, 200, 70))
        painter.drawRect(self.viewport_rect)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(120, 120, 220))
        painter.drawRect(self.viewport_rect)

        current_line = self.editor.textCursor().blockNumber()
        if 0 <= current_line < line_count:
            y = int(current_line * height / line_count)
            painter.fillRect(2, y, self.width() - 4, max(1, int(height / line_count)),
                             QColor(210, 210, 120, 110))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._scroll_to_position(event.position().y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self._scroll_to_position(event.position().y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _scroll_to_position(self, y):
        """Setzt die Editor-Scrollbar auf die geklickte Dokumentposition."""
        ratio = max(0.0, min(1.0, float(y) / max(1, self.height())))
        scrollbar = self.editor.verticalScrollBar()
        scrollbar.setValue(round(ratio * scrollbar.maximum()))


class CodeEditor(QPlainTextEdit):
    """Code-Editor mit Zeilennummern, Highlighting, Auto-Completion und Bracket Matching"""

    cursorPositionInfo = Signal(int, int)  # Zeile, Spalte
    completionRequested = Signal(int, int, str)  # LSP: Zeile, Spalte, Prefix (0-basiert)
    modificationChanged = Signal(bool)

    BRACKETS = {'(': ')', '[': ']', '{': '}', ')': '(', ']': '[', '}': '{'}
    OPEN_BRACKETS = '([{'
    CLOSE_BRACKETS = ')]}'

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_selections = []
        self.bracket_selections = []
        self.error_selections = []

        self.autocomplete_enabled = True
        self.bracket_matching_enabled = True
        self.linter_errors: List[Dict] = []

        self.lineNumberArea = LineNumberArea(self)
        self.minimap = Minimap(self)
        self._minimap_visible = True

        self.completer = None
        self._provider = None
        self.tab_size = 4

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.cursorPositionChanged.connect(self.emitCursorPosition)
        self.cursorPositionChanged.connect(self.matchBrackets)
        self.document().modificationChanged.connect(self.modificationChanged.emit)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        self.apply_editor_settings("Consolas", 10, 4)

    def apply_editor_settings(self, font_family: str = "Consolas", font_size: int = 10, tab_size: int = 4):
        """Wendet Schriftart, Schriftgröße und Tab-Breite an."""
        self.tab_size = int(tab_size or 4)
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        fm = self.fontMetrics()
        space_width = fm.horizontalAdvance(' ') if hasattr(fm, 'horizontalAdvance') else fm.width(' ')
        if hasattr(self, 'setTabStopDistance'):
            self.setTabStopDistance(space_width * self.tab_size)
        else:
            self.setTabStopWidth(space_width * self.tab_size)
        self.updateLineNumberAreaWidth(0)

    def set_minimap_visible(self, visible: bool):
        """Zeigt oder verbirgt die Minimap und aktualisiert den Randabstand."""
        self._minimap_visible = bool(visible)
        self.minimap.setVisible(self._minimap_visible)
        self.updateLineNumberAreaWidth(0)
        self.minimap.update()

    def is_minimap_visible(self) -> bool:
        """Gibt zurück, ob die Minimap für diesen Editor sichtbar sein soll."""
        return self._minimap_visible

    def set_completer_words(self, words: List[str]):
        """Setzt die Completion-Wörter"""
        self.completer = QCompleter(sorted(set(words)), self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        popup = self.completer.popup()
        popup.setStyleSheet("""
            QListView {
                background-color: #2d2d2d; color: #ddd;
                border: 1px solid #555;
                selection-background-color: #2a82da;
            }
        """)

    def set_provider(self, provider):
        """Setzt den Language-Provider für Completion und Indent"""
        self._provider = provider
        if provider:
            words = provider.get_keywords() + provider.get_builtins() + list(provider.get_snippets().keys())
            self.set_completer_words(words)

    def insert_completion(self, completion: str):
        if not completion:
            return
        tc = self.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.movePosition(QTextCursor.MoveOperation.StartOfWord, QTextCursor.MoveMode.KeepAnchor)
        tc.removeSelectedText()
        if self._provider and completion in self._provider.get_snippets():
            tc.insertText(self._provider.get_snippets()[completion])
        else:
            tc.insertText(completion)
        self.setTextCursor(tc)

    def text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def indent_selection(self, spaces: int = None):
        """Rückt die aktuelle Zeile oder alle markierten Zeilen ein."""
        if spaces is None:
            spaces = self.tab_size
        cursor = self.textCursor()
        indent_str = ' ' * spaces

        if not cursor.hasSelection():
            cursor.insertText(indent_str)
            return

        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        doc = self.document()
        start_block = doc.findBlock(start_pos)
        end_block = doc.findBlock(end_pos)

        if end_block.position() == end_pos and end_block != start_block:
            end_block = end_block.previous()

        cursor.beginEditBlock()
        block = start_block
        while block.isValid():
            tc = QTextCursor(block)
            tc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            tc.insertText(indent_str)
            if block == end_block:
                break
            block = block.next()
        cursor.endEditBlock()

        new_cursor = self.textCursor()
        new_cursor.setPosition(start_block.position())
        new_cursor.setPosition(end_block.position() + end_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(new_cursor)

    def unindent_selection(self, spaces: int = None):
        """Rückt die aktuelle Zeile oder alle markierten Zeilen aus (dedent)."""
        if spaces is None:
            spaces = self.tab_size
        cursor = self.textCursor()

        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        doc = self.document()
        start_block = doc.findBlock(start_pos)
        end_block = doc.findBlock(end_pos)

        if cursor.hasSelection() and end_block.position() == end_pos and end_block != start_block:
            end_block = end_block.previous()

        cursor.beginEditBlock()
        block = start_block
        while block.isValid():
            text = block.text()
            leading_spaces = 0
            for char in text:
                if char == ' ':
                    leading_spaces += 1
                elif char == '\t':
                    leading_spaces += spaces
                    break
                else:
                    break
            remove_count = min(spaces, leading_spaces)
            if remove_count > 0:
                tc = QTextCursor(block)
                tc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                for _ in range(remove_count):
                    tc.deleteChar()
            if block == end_block:
                break
            block = block.next()
        cursor.endEditBlock()

        if cursor.hasSelection():
            new_cursor = self.textCursor()
            new_cursor.setPosition(start_block.position())
            new_cursor.setPosition(end_block.position() + end_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(new_cursor)

    def toggle_comment(self):
        """Schaltet den Zeilenkommentar für die aktuelle Zeile oder Auswahl um."""
        comment_prefix = "# "
        if self._provider:
            style = self._provider.get_comment_style()
            if style and style[0]:
                comment_prefix = style[0] + " "

        comment_token = comment_prefix.rstrip()

        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        doc = self.document()
        start_block = doc.findBlock(start_pos)
        end_block = doc.findBlock(end_pos)

        if cursor.hasSelection() and end_block.position() == end_pos and end_block != start_block:
            end_block = end_block.previous()

        all_commented = True
        has_non_empty = False
        block = start_block
        while block.isValid():
            text = block.text().strip()
            if text:
                has_non_empty = True
                if not text.startswith(comment_token):
                    all_commented = False
                    break
            if block == end_block:
                break
            block = block.next()

        if not has_non_empty:
            all_commented = False

        cursor.beginEditBlock()
        block = start_block
        while block.isValid():
            text = block.text()
            tc = QTextCursor(block)
            tc.movePosition(QTextCursor.MoveOperation.StartOfBlock)

            if all_commented:
                stripped_left = text.lstrip()
                if stripped_left.startswith(comment_prefix):
                    indent = len(text) - len(stripped_left)
                    tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, indent)
                    for _ in range(len(comment_prefix)):
                        tc.deleteChar()
                elif stripped_left.startswith(comment_token):
                    indent = len(text) - len(stripped_left)
                    tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, indent)
                    for _ in range(len(comment_token)):
                        tc.deleteChar()
            else:
                if text.strip():
                    tc.insertText(comment_prefix)

            if block == end_block:
                break
            block = block.next()
        cursor.endEditBlock()

    def duplicate_line_or_selection(self):
        """Dupliziert die aktuelle Zeile oder den markierten Bereich."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.setPosition(cursor.selectionEnd())
            cursor.insertText(selected)
            self.setTextCursor(cursor)
        else:
            block = cursor.block()
            text = block.text()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n" + text)
            self.setTextCursor(cursor)

    def move_line_up(self):
        """Verschiebt die aktuelle Zeile nach oben."""
        cursor = self.textCursor()
        block = cursor.block()
        prev = block.previous()
        if not prev.isValid():
            return
        col = cursor.positionInBlock()
        curr_text = block.text()
        prev_text = prev.text()

        cursor.beginEditBlock()
        tc = QTextCursor(prev)
        tc.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        tc.removeSelectedText()
        tc.insertText(curr_text)

        tc2 = QTextCursor(block)
        tc2.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        tc2.removeSelectedText()
        tc2.insertText(prev_text)
        cursor.endEditBlock()

        new_cursor = QTextCursor(prev)
        new_cursor.setPosition(prev.position() + min(col, len(curr_text)))
        self.setTextCursor(new_cursor)

    def move_line_down(self):
        """Verschiebt die aktuelle Zeile nach unten."""
        cursor = self.textCursor()
        block = cursor.block()
        nxt = block.next()
        if not nxt.isValid():
            return
        col = cursor.positionInBlock()
        curr_text = block.text()
        nxt_text = nxt.text()

        cursor.beginEditBlock()
        tc = QTextCursor(block)
        tc.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        tc.removeSelectedText()
        tc.insertText(nxt_text)

        tc2 = QTextCursor(nxt)
        tc2.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        tc2.removeSelectedText()
        tc2.insertText(curr_text)
        cursor.endEditBlock()

        new_cursor = QTextCursor(nxt)
        new_cursor.setPosition(nxt.position() + min(col, len(curr_text)))
        self.setTextCursor(new_cursor)

    def keyPressEvent(self, event):
        # Completer aktiv?
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape,
                               Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        # Tab & Shift+Tab / Backtab (Einrücken / Ausrücken)
        if event.key() == Qt.Key.Key_Backtab or (
            event.key() == Qt.Key.Key_Tab and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ):
            self.unindent_selection(self.tab_size)
            return

        if event.key() == Qt.Key.Key_Tab:
            if self.textCursor().hasSelection():
                self.indent_selection(self.tab_size)
            else:
                self.textCursor().insertText(' ' * self.tab_size)
            return

        # Ctrl+/ oder Ctrl+# (Kommentar umschalten)
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (
            event.key() in (Qt.Key.Key_Slash, Qt.Key.Key_NumberSign) or event.text() in ('/', '#')
        ):
            self.toggle_comment()
            return

        # Ctrl+D (Zeile/Selektion duplizieren)
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_D:
            self.duplicate_line_or_selection()
            return

        # Alt+Up / Alt+Down (Zeile verschieben)
        if (event.modifiers() & Qt.KeyboardModifier.AltModifier) and event.key() == Qt.Key.Key_Up:
            self.move_line_up()
            return
        if (event.modifiers() & Qt.KeyboardModifier.AltModifier) and event.key() == Qt.Key.Key_Down:
            self.move_line_down()
            return

        # Auto-Indent bei Enter
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = len(line) - len(line.lstrip())
            # Indent-Trigger prüfen
            triggers = self._provider.get_indent_triggers() if self._provider else [':', '{']
            if any(line.rstrip().endswith(t) for t in triggers):
                indent += self.tab_size
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(' ' * indent)
            return

        # Auto-Close Brackets
        auto_close = self._provider.get_auto_close_pairs() if self._provider else \
            {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        if event.text() in auto_close:
            close_char = auto_close[event.text()]
            cursor = self.textCursor()
            pos = cursor.position()
            text = self.toPlainText()
            # Wrap selection in brackets/quotes instead of discarding it
            if cursor.hasSelection():
                selected = cursor.selectedText().replace(' ', '\n')
                cursor.insertText(event.text() + selected + close_char)
                self.setTextCursor(cursor)
                return
            # Skip over existing closing char when open == close (quotes)
            if (event.text() == close_char
                    and pos < len(text)
                    and text[pos] == close_char):
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(close_char)
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        super().keyPressEvent(event)

        # Auto-Completion Trigger
        if self.autocomplete_enabled and self.completer:
            prefix = self.text_under_cursor()
            if len(prefix) < 2:
                self.completer.popup().hide()
                return
            cursor = self.textCursor()
            self.completionRequested.emit(
                cursor.blockNumber(), cursor.columnNumber(), prefix
            )
            if prefix != self.completer.completionPrefix():
                self.completer.setCompletionPrefix(prefix)
                self.completer.popup().setCurrentIndex(
                    self.completer.completionModel().index(0, 0)
                )
            cr = self.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0) +
                        self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)

    # ---- Bracket Matching ----

    def matchBrackets(self):
        self.bracket_selections = []
        if not self.bracket_matching_enabled:
            self.highlightCurrentLine()
            return
        cursor = self.textCursor()
        text = self.toPlainText()
        pos = cursor.position()
        if pos > len(text):
            self.highlightCurrentLine()
            return

        char_at = text[pos] if pos < len(text) else ''
        char_before = text[pos - 1] if pos > 0 else ''
        bracket_char, bracket_pos = None, None

        if char_at in self.BRACKETS:
            bracket_char, bracket_pos = char_at, pos
        elif char_before in self.BRACKETS:
            bracket_char, bracket_pos = char_before, pos - 1

        if bracket_char and bracket_pos is not None:
            match_pos = self._find_matching_bracket(text, bracket_pos, bracket_char)
            if match_pos is not None:
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(80, 80, 0))
                fmt.setForeground(QColor(255, 255, 0))
                for p in [bracket_pos, match_pos]:
                    sel = QTextEdit.ExtraSelection()
                    sel.format = fmt
                    cur = self.textCursor()
                    cur.setPosition(p)
                    cur.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
                    sel.cursor = cur
                    self.bracket_selections.append(sel)
        self.highlightCurrentLine()

    def _find_matching_bracket(self, text, pos, bracket):
        if bracket in self.OPEN_BRACKETS:
            target = self.BRACKETS[bracket]
            direction, start, end = 1, pos + 1, len(text)
        else:
            target = self.BRACKETS[bracket]
            direction, start, end = -1, pos - 1, -1
        count = 1
        i = start
        while i != end:
            if text[i] == bracket:
                count += 1
            elif text[i] == target:
                count -= 1
                if count == 0:
                    return i
            i += direction
        return None

    # ---- Cursor ----

    def emitCursorPosition(self):
        cursor = self.textCursor()
        self.cursorPositionInfo.emit(cursor.blockNumber() + 1, cursor.columnNumber() + 1)

    # ---- Line Numbers ----

    def lineNumberAreaWidth(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        fm = self.fontMetrics()
        char_width = fm.horizontalAdvance('9') if hasattr(fm, 'horizontalAdvance') else fm.width('9')
        return 20 + char_width * digits

    def updateLineNumberAreaWidth(self, _):
        right_margin = self.minimap.width() if self._minimap_visible else 0
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, right_margin, 0)
        self._position_minimap()

    def _position_minimap(self):
        if not hasattr(self, "minimap"):
            return
        cr = self.contentsRect()
        width = self.minimap.width()
        self.minimap.setGeometry(
            QRect(cr.right() - width + 1, cr.top(), width, cr.height())
        )

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )
        self._position_minimap()

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(35, 35, 35))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = blockNumber + 1
                has_error = any(e['line'] == line_num and e.get('severity') == 'error'
                                for e in self.linter_errors)
                has_warning = any(e['line'] == line_num and e.get('severity') == 'warning'
                                  for e in self.linter_errors)
                if has_error:
                    painter.setPen(QColor(255, 80, 80))
                elif has_warning:
                    painter.setPen(QColor(255, 200, 80))
                else:
                    painter.setPen(QColor(100, 100, 100))
                painter.drawText(0, top, self.lineNumberArea.width() - 5,
                                 self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, str(line_num))
            block = block.next()
            if not block.isValid():
                break
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    # ---- Highlighting ----

    def highlightCurrentLine(self):
        extraSelections = (list(self.search_selections) +
                           list(self.bracket_selections) +
                           list(self.error_selections))
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(45, 45, 45))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.insert(0, selection)
        self.setExtraSelections(extraSelections)

    # ---- Search ----

    def highlightSearchResults(self, pattern: str, case_sensitive: bool = False):
        from PySide6.QtGui import QTextDocument
        self.search_selections = []
        if not pattern:
            self.highlightCurrentLine()
            return 0
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        cursor = QTextCursor(self.document())
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(100, 100, 0))
        fmt.setForeground(QColor(255, 255, 255))
        count = 0
        while True:
            cursor = self.document().find(pattern, cursor, flags)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            sel.cursor = cursor
            self.search_selections.append(sel)
            count += 1
        self.highlightCurrentLine()
        return count

    def clearSearchHighlight(self):
        self.search_selections = []
        self.highlightCurrentLine()

    def set_linter_errors(self, errors: List[Dict]):
        """Setzt Linter-Fehler und aktualisiert Markierungen"""
        self.linter_errors = errors
        self.error_selections = []
        for error in errors:
            line = error.get('line', 1) - 1
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                continue
            sel = QTextEdit.ExtraSelection()
            if error.get('severity') == 'error':
                sel.format.setUnderlineColor(QColor(255, 80, 80))
            else:
                sel.format.setUnderlineColor(QColor(255, 200, 80))
            sel.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor
            self.error_selections.append(sel)
        self.lineNumberArea.update()
        self.highlightCurrentLine()
