#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LanguageProvider - Abstrakte Basisklasse fuer Sprachunterstuetzung
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional


class LanguageProvider(ABC):
    """Abstrakte Basisklasse fuer Sprachunterstuetzung in CodeBox"""

    @abstractmethod
    def get_name(self) -> str:
        """Anzeigename der Sprache"""
        pass

    @abstractmethod
    def get_extensions(self) -> List[str]:
        """Unterstuetzte Dateiendungen (ohne Punkt)"""
        pass

    @abstractmethod
    def get_keywords(self) -> List[str]:
        """Keywords fuer Highlighting und Completion"""
        pass

    def get_builtins(self) -> List[str]:
        """Built-in Funktionen (optional)"""
        return []

    def get_snippets(self) -> Dict[str, str]:
        """Code-Snippets {trigger: expansion}"""
        return {}

    @abstractmethod
    def get_run_command(self, file_path: str) -> List[str]:
        """Kommando zum Ausfuehren"""
        pass

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        """Kommando zum Debuggen (None = nicht verfuegbar)"""
        return None

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        """Linter-Kommando (None = kein Linter)"""
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        """(Einzeilen-Kommentar, Mehrzeilen-Start/Ende oder None)"""
        return ("//", ("/*", "*/"))

    def get_bracket_pairs(self) -> Dict[str, str]:
        """Klammer-Paare fuer Matching"""
        return {'(': ')', '[': ']', '{': '}'}

    def get_auto_close_pairs(self) -> Dict[str, str]:
        """Auto-Close Paare"""
        return {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}

    def get_indent_triggers(self) -> List[str]:
        """Zeichen/Woerter die Einrueckung ausloesen"""
        return ['{']

    def get_dedent_triggers(self) -> List[str]:
        """Zeichen/Woerter die Ausrueckung ausloesen"""
        return ['}']
