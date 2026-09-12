#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Symbol Search & Fallback Provider für CodeBox.

Bietet schnelle, heuristische Symbol- und Referenzsuche, falls kein LSP-Server
installiert oder aktiv ist oder der Language Server für eine Datei keine Ergebnisse liefert.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    ".idea",
    ".vscode",
}

MAX_FILE_SIZE_BYTES = 1024 * 1024 * 2  # 2 MB Begrenzung pro Textdatei


def get_definition_patterns(symbol: str) -> List[re.Pattern]:
    """Erstellt reguläre Ausdrücke zur Erkennung typischer Definitionen für das Symbol."""
    escaped = re.escape(symbol)
    patterns = [
        # Python: def func / async def func / class Class / Var =
        rf"^\s*(?:async\s+)?def\s+{escaped}\b",
        rf"^\s*class\s+{escaped}\b",
        rf"^\s*{escaped}\s*=",
        # JS / TS: function func / class Class / const/let/var x = / type / interface
        rf"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+{escaped}\b",
        rf"^\s*(?:export\s+)?class\s+{escaped}\b",
        rf"^\s*(?:export\s+)?(?:const|let|var)\s+{escaped}\s*=",
        rf"^\s*(?:export\s+)?(?:interface|type)\s+{escaped}\b",
        # Rust / Go / C / C++
        rf"^\s*(?:pub(?:\([^)]*\))?\s+)?fn\s+{escaped}\b",
        rf"^\s*func\s+(?:\([^)]+\)\s+)?{escaped}\b",
        rf"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+{escaped}\b",
    ]
    return [re.compile(p, re.MULTILINE) for p in patterns]


def _scan_text_for_definitions(
    text: str,
    patterns: List[re.Pattern],
    symbol: str,
    path: Optional[Path],
) -> List[dict]:
    results: List[dict] = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines):
        for pat in patterns:
            m = pat.search(line)
            if m:
                # Spalte des Symbols ermitteln
                col_idx = line.find(symbol)
                if col_idx < 0:
                    col_idx = m.start()
                results.append({
                    "path": path,
                    "line": line_idx + 1,
                    "col": col_idx + 1,
                    "length": len(symbol),
                    "preview": line.strip(),
                    "source": "Definition (Fallback)",
                })
                break
    return results


def find_definition_fallback(
    symbol: str,
    current_path: Optional[Path] = None,
    current_text: Optional[str] = None,
    workspace_folders: Optional[List[Path]] = None,
) -> List[dict]:
    """Sucht nach Definitionen eines Symbols im aktuellen Dokument und Workspace."""
    if not symbol or not symbol.strip():
        return []
    symbol = symbol.strip()
    patterns = get_definition_patterns(symbol)
    results: List[dict] = []

    # 1. Zuerst das aktuelle Dokument durchsuchen
    if current_text:
        doc_matches = _scan_text_for_definitions(current_text, patterns, symbol, current_path)
        results.extend(doc_matches)
        if results:
            return results

    # 2. Falls im aktiven Dokument nichts gefunden wurde: Workspace durchsuchen
    if workspace_folders:
        current_resolved = current_path.resolve() if current_path and current_path.exists() else None
        for folder in workspace_folders:
            folder_path = Path(folder).resolve()
            if not folder_path.is_dir():
                continue
            for root, dirs, files in folder_path.walk():
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                for fname in files:
                    if fname.startswith("."):
                        continue
                    file_path = root / fname
                    if current_resolved and file_path == current_resolved:
                        continue
                    try:
                        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                            continue
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                    except (OSError, UnicodeError):
                        continue

                    matches = _scan_text_for_definitions(content, patterns, symbol, file_path)
                    if matches:
                        results.extend(matches)
                        # Sobald wir eine konkrete Definition finden, zurückgeben
                        if len(results) >= 10:
                            return results

    return results


def find_references_fallback(
    symbol: str,
    current_path: Optional[Path] = None,
    current_text: Optional[str] = None,
    workspace_folders: Optional[List[Path]] = None,
    max_results: int = 250,
) -> List[dict]:
    """Sucht nach allen Vorkommen (Ganzwort) des Symbols im aktuellen Dokument und Workspace."""
    if not symbol or not symbol.strip():
        return []
    symbol = symbol.strip()
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    results: List[dict] = []

    # 1. Aktives Dokument
    if current_text:
        for line_idx, line in enumerate(current_text.splitlines()):
            for match in pattern.finditer(line):
                results.append({
                    "path": current_path,
                    "line": line_idx + 1,
                    "col": match.start() + 1,
                    "length": len(symbol),
                    "preview": line.strip(),
                    "source": "Referenz (Text)",
                })
                if len(results) >= max_results:
                    return results

    # 2. Workspace
    if workspace_folders:
        current_resolved = current_path.resolve() if current_path and current_path.exists() else None
        for folder in workspace_folders:
            folder_path = Path(folder).resolve()
            if not folder_path.is_dir():
                continue
            for root, dirs, files in folder_path.walk():
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                for fname in files:
                    if fname.startswith("."):
                        continue
                    file_path = root / fname
                    if current_resolved and file_path == current_resolved:
                        continue
                    try:
                        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                            continue
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                    except (OSError, UnicodeError):
                        continue

                    for line_idx, line in enumerate(content.splitlines()):
                        for match in pattern.finditer(line):
                            results.append({
                                "path": file_path,
                                "line": line_idx + 1,
                                "col": match.start() + 1,
                                "length": len(symbol),
                                "preview": line.strip(),
                                "source": "Referenz (Text)",
                            })
                            if len(results) >= max_results:
                                return results

    return results
