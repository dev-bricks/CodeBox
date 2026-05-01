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

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.cursorPositionChanged.connect(self.emitCursorPosition)
        self.cursorPositionChanged.connect(self.matchBrackets)
        self.document().modificationChanged.connect(self.modificationChanged.emit)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        fm = self.fontMetrics()
        space_width = fm.horizontalAdvance(' ') if hasattr(fm, 'horizontalAdvance') else fm.width(' ')
        if hasattr(self, 'setTabStopDistance'):
            self.setTabStopDistance(space_width * 4)
        else:
            self.setTabStopWidth(space_width * 4)

        # Auto-Completion
        self.completer = None
        self._provider = None

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
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        if extra <= 0:
            return
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        # Snippet-Prüfung
        if self._provider and completion in self._provider.get_snippets():
            tc.movePosition(QTextCursor.MoveOperation.StartOfWord, QTextCursor.MoveMode.KeepAnchor)
            tc.removeSelectedText()
            tc.insertText(self._provider.get_snippets()[completion])
        else:
            tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        # Completer aktiv?
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape,
                               Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        # Auto-Indent bei Enter
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = len(line) - len(line.lstrip())
            # Indent-Trigger prüfen
            triggers = self._provider.get_indent_triggers() if self._provider else [':','{']
            if any(line.rstrip().endswith(t) for t in triggers):
                indent += 4
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(' ' * indent)
            return

        # Auto-Close Brackets
        auto_close = self._provider.get_auto_close_pairs() if self._provider else \
            {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        if event.text() in auto_close:
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(auto_close[event.text()])
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
        if pos >= len(text):
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
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

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
                                 self.fontMetrics().height(), Qt.AlignRight, str(line_num))
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
