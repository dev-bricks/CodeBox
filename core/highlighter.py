#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Universal Syntax Highlighter - Provider-basiert"""

import re
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)


class UniversalHighlighter(QSyntaxHighlighter):
    """Universeller Syntax-Highlighter basierend auf LanguageProvider"""

    def __init__(self, document, provider=None):
        super().__init__(document)
        self.provider = provider
        self.highlighting_rules = []
        self.multiline_rules = []
        if provider:
            self._build_rules()

    def set_provider(self, provider):
        """Wechselt den Language-Provider"""
        self.provider = provider
        self.highlighting_rules = []
        self.multiline_rules = []
        if provider:
            self._build_rules()
        self.rehighlight()

    @staticmethod
    def _keyword_pattern(word: str) -> str:
        """Erzeugt ein sicheres Regex-Muster mit passenden Wortgrenzen für Keywords."""
        prefix = r'\b' if re.match(r'^\w', word) else r'(?<!\S)'
        suffix = r'\b' if re.search(r'\w$', word) else r'(?!\w)'
        return f"{prefix}{re.escape(word)}{suffix}"

    def _build_rules(self):
        """Erstellt Highlighting-Regeln aus dem Provider"""
        self.highlighting_rules = []
        self.multiline_rules = []
        if not self.provider:
            return

        # Keywords (Blau, Fett)
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor(86, 156, 214))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        for word in self.provider.get_keywords():
            if word:
                self.highlighting_rules.append(
                    (QRegularExpression(self._keyword_pattern(word)), kw_fmt)
                )

        # Builtins (Gelb)
        bi_fmt = QTextCharFormat()
        bi_fmt.setForeground(QColor(220, 220, 170))
        for word in self.provider.get_builtins():
            if word:
                self.highlighting_rules.append(
                    (QRegularExpression(self._keyword_pattern(word)), bi_fmt)
                )

        # Decorators / Preprocessor (Lila)
        dec_fmt = QTextCharFormat()
        dec_fmt.setForeground(QColor(189, 147, 249))
        comment_style = self.provider.get_comment_style()
        comment_char = comment_style[0] if (comment_style and len(comment_style) > 0) else ""
        if comment_char == '#':
            self.highlighting_rules.append(
                (QRegularExpression(r'@[^\n]+'), dec_fmt)
            )
        elif comment_char == '//':
            self.highlighting_rules.append(
                (QRegularExpression(r'#\s*\w+'), dec_fmt)
            )

        # Strings (Orange)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor(206, 145, 120))
        self.highlighting_rules.append(
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt)
        )
        self.highlighting_rules.append(
            (QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), str_fmt)
        )

        # Numbers (Hellgrün)
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor(181, 206, 168))
        self.highlighting_rules.append(
            (QRegularExpression(r'\b[0-9]+\.?[0-9]*\b'), num_fmt)
        )

        # Function/Class Definitions (Gelb)
        def_fmt = QTextCharFormat()
        def_fmt.setForeground(QColor(220, 220, 170))
        self.highlighting_rules.append(
            (QRegularExpression(r'\bdef\s+(\w+)'), def_fmt)
        )
        self.highlighting_rules.append(
            (QRegularExpression(r'\bclass\s+(\w+)'), def_fmt)
        )
        self.highlighting_rules.append(
            (QRegularExpression(r'\bfunction\s+(\w+)'), def_fmt)
        )

        # Comments (Grün, Kursiv) - MUSS am Ende stehen
        cmt_fmt = QTextCharFormat()
        cmt_fmt.setForeground(QColor(106, 153, 85))
        cmt_fmt.setFontItalic(True)
        if comment_char:
            escaped = re.escape(comment_char)
            self.highlighting_rules.append(
                (QRegularExpression(escaped + r'[^\n]*'), cmt_fmt)
            )

        # Mehrzeilen-Kommentare / Docstrings (Block State Machine)
        multi_pair = comment_style[1] if (comment_style and len(comment_style) > 1) else None
        if multi_pair and len(multi_pair) == 2 and multi_pair[0] and multi_pair[1]:
            start_delim, end_delim = multi_pair
            self.multiline_rules.append((
                1,
                QRegularExpression(re.escape(start_delim)),
                QRegularExpression(re.escape(end_delim)),
                cmt_fmt
            ))
            # Wenn Python: zusätzlich einfache Triple-Quotes ('''...''') unterstützen
            if start_delim == '"""':
                self.multiline_rules.append((
                    2,
                    QRegularExpression(re.escape("'''")),
                    QRegularExpression(re.escape("'''")),
                    cmt_fmt
                ))

    def highlightBlock(self, text: str):
        # 1. Standard Einzelzeilen-Regeln anwenden
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # 2. Mehrzeilen-Blöcke (Kommentare / Docstrings) anwenden
        if not self.multiline_rules:
            self.setCurrentBlockState(0)
            return

        self.setCurrentBlockState(0)
        previous_state = self.previousBlockState()

        # Prüfen, ob wir uns bereits in einem Mehrzeilen-Zustand befinden
        active_rule = None
        if previous_state > 0:
            for rule in self.multiline_rules:
                if rule[0] == previous_state:
                    active_rule = rule
                    break

        start_index = 0
        if active_rule:
            state_id, _start_exp, end_exp, fmt = active_rule
            end_match = end_exp.match(text, start_index)
            if not end_match.hasMatch():
                self.setCurrentBlockState(state_id)
                self.setFormat(0, len(text), fmt)
                return
            else:
                end_pos = end_match.capturedStart()
                match_len = end_match.capturedLength()
                self.setFormat(0, end_pos + match_len, fmt)
                start_index = end_pos + match_len

        while start_index < len(text):
            earliest_match = None
            earliest_rule = None
            for rule in self.multiline_rules:
                _state_id, start_exp, _end_exp, _fmt = rule
                m = start_exp.match(text, start_index)
                if m.hasMatch():
                    if earliest_match is None or m.capturedStart() < earliest_match.capturedStart():
                        earliest_match = m
                        earliest_rule = rule

            if not earliest_match or not earliest_rule:
                break

            state_id, _start_exp, end_exp, fmt = earliest_rule
            start_pos = earliest_match.capturedStart()
            start_len = earliest_match.capturedLength()
            end_match = end_exp.match(text, start_pos + start_len)

            if not end_match.hasMatch():
                self.setCurrentBlockState(state_id)
                self.setFormat(start_pos, len(text) - start_pos, fmt)
                break
            else:
                end_pos = end_match.capturedStart()
                end_len = end_match.capturedLength()
                comment_len = (end_pos + end_len) - start_pos
                self.setFormat(start_pos, comment_len, fmt)
                start_index = end_pos + end_len
