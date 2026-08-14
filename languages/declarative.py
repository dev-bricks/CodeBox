#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Declarative Language Provider für CodeBox.
Ermöglicht das Definieren neuer Sprachen über JSON/Dict ohne Python-Code.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .base import LanguageProvider


class DeclarativeLanguageProvider(LanguageProvider):
    """
    Sprach-Provider, der deklarativ über ein Wörterbuch oder eine JSON-Datei konfiguriert wird.
    """

    def __init__(
        self,
        name: str,
        extensions: List[str],
        keywords: Optional[List[str]] = None,
        builtins: Optional[List[str]] = None,
        snippets: Optional[Dict[str, str]] = None,
        run_command: Optional[Union[List[str], str]] = None,
        debug_command: Optional[Union[List[str], str]] = None,
        linter_command: Optional[Union[List[str], str]] = None,
        comment_single: str = "//",
        comment_multi_start: Optional[str] = "/*",
        comment_multi_end: Optional[str] = "*/",
        bracket_pairs: Optional[Dict[str, str]] = None,
        auto_close_pairs: Optional[Dict[str, str]] = None,
        indent_triggers: Optional[List[str]] = None,
        dedent_triggers: Optional[List[str]] = None,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
    ):
        if not name or not isinstance(name, str):
            raise ValueError("Provider 'name' must be a non-empty string")
        if not extensions:
            raise ValueError("Provider must define at least one file extension")

        self._name = name.strip()
        self._extensions = [ext.lower().lstrip(".") for ext in extensions if ext.strip()]
        self._keywords = list(keywords or [])
        self._builtins = list(builtins or [])
        self._snippets = dict(snippets or {})
        self._run_command = run_command
        self._debug_command = debug_command
        self._linter_command = linter_command
        self._comment_single = comment_single
        self._comment_multi = (comment_multi_start, comment_multi_end) if (comment_multi_start and comment_multi_end) else None
        self._bracket_pairs = dict(bracket_pairs) if bracket_pairs is not None else {'(': ')', '[': ']', '{': '}'}
        self._auto_close_pairs = dict(auto_close_pairs) if auto_close_pairs is not None else {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        self._indent_triggers = list(indent_triggers or ['{'])
        self._dedent_triggers = list(dedent_triggers or ['}'])
        self._version = version
        self._author = author
        self._description = description

    def get_name(self) -> str:
        return self._name

    def get_extensions(self) -> List[str]:
        return list(self._extensions)

    def get_keywords(self) -> List[str]:
        return list(self._keywords)

    def get_builtins(self) -> List[str]:
        return list(self._builtins)

    def get_snippets(self) -> Dict[str, str]:
        return dict(self._snippets)

    def _resolve_cmd(self, cmd_template: Union[List[str], str], file_path: str) -> List[str]:
        if isinstance(cmd_template, str):
            formatted = cmd_template.replace("{file}", file_path)
            # Auf Windows/Unix passend splitten bzw. Shell-Command aufbauen
            if sys.platform == "win32":
                return ["cmd", "/c", formatted]
            return ["bash", "-c", formatted]
        result = []
        for part in cmd_template:
            result.append(part.replace("{file}", file_path))
        return result

    def get_run_command(self, file_path: str) -> List[str]:
        if self._run_command:
            return self._resolve_cmd(self._run_command, file_path)
        # Fallback: Versuche Dateinamen direkt auszuführen
        return [file_path]

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        if self._debug_command:
            return self._resolve_cmd(self._debug_command, file_path)
        return None

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if self._linter_command:
            cmd = self._resolve_cmd(self._linter_command, file_path)
            # Prüfe, ob Executable existiert
            if cmd and shutil.which(cmd[0]):
                return cmd
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return (self._comment_single, self._comment_multi)

    def get_bracket_pairs(self) -> Dict[str, str]:
        return dict(self._bracket_pairs)

    def get_auto_close_pairs(self) -> Dict[str, str]:
        return dict(self._auto_close_pairs)

    def get_indent_triggers(self) -> List[str]:
        return list(self._indent_triggers)

    def get_dedent_triggers(self) -> List[str]:
        return list(self._dedent_triggers)

    @property
    def version(self) -> str:
        return self._version

    @property
    def author(self) -> str:
        return self._author

    @property
    def description(self) -> str:
        return self._description

    @classmethod
    def from_dict(cls, data: dict) -> DeclarativeLanguageProvider:
        """Erzeugt einen DeclarativeLanguageProvider aus einem Wörterbuch."""
        name = data.get("name")
        extensions = data.get("extensions")
        if not name:
            raise ValueError("Plugin dictionary must specify 'name'")
        if not extensions or not isinstance(extensions, list):
            raise ValueError("Plugin dictionary must specify 'extensions' as a list of strings")

        # Comment style parsing
        comment_single = "//"
        comment_multi_start = "/*"
        comment_multi_end = "*/"
        comment_style = data.get("comment_style")
        if isinstance(comment_style, (list, tuple)) and len(comment_style) >= 1:
            comment_single = str(comment_style[0])
            if len(comment_style) >= 2 and isinstance(comment_style[1], (list, tuple)) and len(comment_style[1]) >= 2:
                comment_multi_start = str(comment_style[1][0])
                comment_multi_end = str(comment_style[1][1])
            elif len(comment_style) >= 2 and comment_style[1] is None:
                comment_multi_start = None
                comment_multi_end = None
        elif isinstance(comment_style, dict):
            comment_single = str(comment_style.get("single", "//"))
            comment_multi_start = comment_style.get("multi_start", "/*")
            comment_multi_end = comment_style.get("multi_end", "*/")

        return cls(
            name=name,
            extensions=extensions,
            keywords=data.get("keywords", []),
            builtins=data.get("builtins", []),
            snippets=data.get("snippets", {}),
            run_command=data.get("run_command"),
            debug_command=data.get("debug_command"),
            linter_command=data.get("linter_command"),
            comment_single=comment_single,
            comment_multi_start=comment_multi_start,
            comment_multi_end=comment_multi_end,
            bracket_pairs=data.get("bracket_pairs"),
            auto_close_pairs=data.get("auto_close_pairs"),
            indent_triggers=data.get("indent_triggers"),
            dedent_triggers=data.get("dedent_triggers"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
        )

    @classmethod
    def from_json_file(cls, file_path: Union[str, Path]) -> DeclarativeLanguageProvider:
        """Lädt einen DeclarativeLanguageProvider aus einer JSON-Datei."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Plugin JSON file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        """Konvertiert den Provider zurück in ein Wörterbuch für Serialisierung."""
        return {
            "name": self._name,
            "version": self._version,
            "author": self._author,
            "description": self._description,
            "extensions": self._extensions,
            "keywords": self._keywords,
            "builtins": self._builtins,
            "snippets": self._snippets,
            "run_command": self._run_command,
            "debug_command": self._debug_command,
            "linter_command": self._linter_command,
            "comment_style": (self._comment_single, self._comment_multi),
            "bracket_pairs": self._bracket_pairs,
            "auto_close_pairs": self._auto_close_pairs,
            "indent_triggers": self._indent_triggers,
            "dedent_triggers": self._dedent_triggers,
        }
