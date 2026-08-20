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
        if provider:
            self._build_rules()

    def set_provider(self, provider):
        """Wechselt den Language-Provider"""
        self.provider = provider
        self.highlighting_rules = []
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

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
