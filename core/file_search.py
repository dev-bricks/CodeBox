#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Search Engine - Projektweite Textsuche für CodeBox.

Stellt Datenstrukturen, reguläre Suchmuster-Kompilierung, Glob-Filter
und einen asynchronen Such-Worker (QThread) für Multi-Root-Arbeitsbereiche bereit:
- SearchMatch: Repräsentiert einen einzelnen Treffer (Datei, Zeile, Spalte, Text).
- FileSearchResult: Gruppiert alle Treffer einer Datei.
- SearchOptions: Konfigurationsparameter (Regex, Case-Sensitivity, Globs etc.).
- SearchWorker: Hintergrund-Thread für flüssiges Durchsuchen ohne UI-Blockade.
"""

from __future__ import annotations

import fnmatch
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

from PySide6.QtCore import QObject, QThread, Signal

from core.workspace import DEFAULT_WORKSPACE_SKIP_DIRS


@dataclass
class SearchMatch:
    """Repräsentiert einen einzelnen Suchtreffer innerhalb einer Datei."""

    file_path: Path
    rel_path: str
    folder_name: str
    line_number: int  # 1-basiert
    column: int  # 1-basiert
    match_length: int
    line_text: str  # Ganze Zeile für Vorschau


@dataclass
class FileSearchResult:
    """Gruppiert alle Suchtreffer einer Datei."""

    file_path: Path
    rel_path: str
    folder_name: str
    matches: List[SearchMatch] = field(default_factory=list)


@dataclass
class SearchOptions:
    """Optionen für die dateiübergreifende Textsuche."""

    query: str
    case_sensitive: bool = False
    whole_word: bool = False
    is_regex: bool = False
    include_globs: List[str] = field(default_factory=list)
    exclude_globs: List[str] = field(default_factory=list)
    max_results: int = 5000
    max_file_size_kb: int = 4096


def is_binary_file(file_path: Path) -> bool:
    """Prüft schnell, ob eine Datei binär ist (Null-Byte im Header oder unlesbar)."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except (OSError, PermissionError):
        return True


def compile_search_regex(options: SearchOptions) -> Tuple[Optional[re.Pattern], Optional[str]]:
    """Kompiliert das Suchmuster anhand der Optionen.

    Returns:
        (pattern, error_message): pattern ist None wenn ungültig, mit Fehlermeldung.
    """
    raw_query = options.query
    if not raw_query:
        return None, "Suchbegriff darf nicht leer sein."

    flags = 0 if options.case_sensitive else re.IGNORECASE

    if options.is_regex:
        pattern_str = raw_query
    else:
        pattern_str = re.escape(raw_query)

    if options.whole_word:
        pattern_str = rf"\b{pattern_str}\b"

    try:
        compiled = re.compile(pattern_str, flags)
        return compiled, None
    except re.error as e:
        return None, f"Ungültiger regulärer Ausdruck: {e}"


def matches_glob_patterns(
    filename: str,
    rel_path_str: str,
    include_globs: List[str],
    exclude_globs: List[str],
) -> bool:
    """Prüft, ob eine Datei den Include- und Exclude-Glob-Mustern entspricht."""
    # Exclude-Prüfung hat Vorrang
    normalized_rel = rel_path_str.replace("\\", "/")
    for exc in exclude_globs:
        exc = exc.strip()
        if not exc:
            continue
        exc_norm = exc.replace("\\", "/")
        if fnmatch.fnmatch(filename, exc) or fnmatch.fnmatch(normalized_rel, exc_norm):
            return False

    # Include-Prüfung: Falls Muster angegeben, muss mindestens eines passen
    active_includes = [inc.strip() for inc in include_globs if inc.strip()]
    if active_includes:
        matched_any = False
        for inc in active_includes:
            inc_norm = inc.replace("\\", "/")
            if fnmatch.fnmatch(filename, inc) or fnmatch.fnmatch(normalized_rel, inc_norm):
                matched_any = True
                break
        if not matched_any:
            return False

    return True


def search_file(
    file_path: Path,
    rel_path: str,
    folder_name: str,
    pattern: re.Pattern,
    max_file_size_kb: int = 4096,
) -> List[SearchMatch]:
    """Durchsucht eine einzelne Datei Zeile für Zeile nach dem gegebenen Suchmuster."""
    try:
        size = file_path.stat().st_size
        if size > max_file_size_kb * 1024:
            return []
    except (OSError, PermissionError):
        return []

    if is_binary_file(file_path):
        return []

    matches: List[SearchMatch] = []
    encodings = ["utf-8", "cp1252", "latin-1"]

    content = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.readlines()
            break
        except (UnicodeDecodeError, OSError):
            continue

    if content is None:
        return []

    for line_idx, line in enumerate(content, start=1):
        clean_line = line.rstrip("\r\n")
        for m in pattern.finditer(clean_line):
            col = m.start() + 1
            length = max(1, m.end() - m.start())
            matches.append(
                SearchMatch(
                    file_path=file_path,
                    rel_path=rel_path,
                    folder_name=folder_name,
                    line_number=line_idx,
                    column=col,
                    match_length=length,
                    line_text=clean_line,
                )
            )

    return matches


class SearchWorker(QThread):
    """Hintergrund-Thread zum Durchsuchen eines oder mehrerer Projektordner.

    Signale:
        matchFound(object): Emittiert SearchMatch bei jedem Fund.
        fileCompleted(object): Emittiert FileSearchResult wenn eine Datei Treffer hatte.
        searchProgress(int, int, str): Emittiert (gescannte_Dateien, Gesamtdateien, aktueller_Pfad).
        searchFinished(int, int, float): Emittiert (Gesamttreffer, betroffene_Dateien, Laufzeit_Sekunden).
        searchError(str): Emittiert eine Fehlermeldung (z. B. fehlerhafter Regex).
    """

    matchFound = Signal(object)  # SearchMatch
    fileCompleted = Signal(object)  # FileSearchResult
    searchProgress = Signal(int, int, str)  # (current, total, file_name)
    searchFinished = Signal(int, int, float)  # (total_matches, total_files, elapsed_secs)
    searchError = Signal(str)

    def __init__(
        self,
        folders: List[Tuple[Path, str]],  # Liste aus (Wurzelpfad, Anzeigename)
        options: SearchOptions,
        skip_dirs: Optional[Set[str]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.folders = folders
        self.options = options
        self.skip_dirs = skip_dirs or DEFAULT_WORKSPACE_SKIP_DIRS
        self._is_cancelled = False

    def cancel(self):
        """Bricht die Suche ab."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """Gibt zurück, ob die Suche abgebrochen wurde."""
        return self._is_cancelled

    def run(self):
        """Führt den Suchlauf im Hintergrund durch."""
        start_time = time.perf_counter()

        pattern, err = compile_search_regex(self.options)
        if err or pattern is None:
            self.searchError.emit(err or "Fehler beim Kompilieren des Suchmusters.")
            return

        # 1. Dateien einsammeln
        files_to_scan: List[Tuple[Path, str, str]] = []  # (abs_path, rel_path, folder_name)
        for root_path, folder_name in self.folders:
            if self._is_cancelled:
                break
            if not root_path.exists() or not root_path.is_dir():
                continue

            for dirpath, dirnames, filenames in os.walk(str(root_path)):
                if self._is_cancelled:
                    break
                # Ignorierte Verzeichnisse filtern
                dirnames[:] = [
                    d for d in dirnames
                    if d not in self.skip_dirs and not d.startswith(".")
                ]

                for fname in filenames:
                    if fname.startswith(".") and fname != ".gitignore":
                        continue
                    abs_p = Path(dirpath) / fname
                    try:
                        rel_p = abs_p.relative_to(root_path)
                        rel_str = str(rel_p).replace("\\", "/")
                    except ValueError:
                        rel_str = fname

                    if matches_glob_patterns(
                        fname,
                        rel_str,
                        self.options.include_globs,
                        self.options.exclude_globs,
                    ):
                        files_to_scan.append((abs_p, rel_str, folder_name))

        total_files = len(files_to_scan)
        total_matches = 0
        total_files_with_matches = 0

        # 2. Dateien durchsuchen
        for idx, (abs_p, rel_str, folder_name) in enumerate(files_to_scan, start=1):
            if self._is_cancelled:
                break

            if idx % 10 == 0 or idx == total_files:
                self.searchProgress.emit(idx, total_files, rel_str)

            file_matches = search_file(
                abs_p,
                rel_str,
                folder_name,
                pattern,
                max_file_size_kb=self.options.max_file_size_kb,
            )

            if file_matches:
                total_files_with_matches += 1
                total_matches += len(file_matches)
                for m in file_matches:
                    self.matchFound.emit(m)
                self.fileCompleted.emit(
                    FileSearchResult(
                        file_path=abs_p,
                        rel_path=rel_str,
                        folder_name=folder_name,
                        matches=file_matches,
                    )
                )

            if total_matches >= self.options.max_results:
                break

        elapsed = time.perf_counter() - start_time
        self.searchFinished.emit(total_matches, total_files_with_matches, elapsed)
