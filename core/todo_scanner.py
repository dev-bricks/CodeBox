#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO & Aufgaben Scanner Engine für CodeBox.

Stellt Datenstrukturen, reguläre Mustererkennung für standardisierte Aufgaben-Tags
(TODO, FIXME, BUG, HACK, XXX, NOTE), Einzelfile-Scanner und einen asynchronen
Hintergrund-Worker (QThread) für Multi-Root-Arbeitsbereiche bereit.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from PySide6.QtCore import QObject, QThread, Signal

from core.file_search import is_binary_file
from core.workspace import DEFAULT_WORKSPACE_SKIP_DIRS

DEFAULT_TODO_TAGS = ("TODO", "FIXME", "BUG", "HACK", "XXX", "NOTE")

# Regulärer Ausdruck für Standard-Kommentare und Aufgaben-Tags
# Erkennt Kommentare (#, //, /*, <!--, --, %, @, ;, *, - [ ], - [x])
# oder Zeilenanfang/Whitespace mit explizitem Tag gefolgt von Doppelpunkt.
TODO_PATTERN = re.compile(
    r'(?:(?:#|//|/\*+|<!--|--|%|@|;\s*|\*\s*|-\s*\[[ xX]\]\s*)\s*(TODO|FIXME|BUG|HACK|XXX|NOTE)\b(?:\(([^)]+)\))?\s*:?\s*(.*))'
    r'|(?:^\s*(TODO|FIXME|BUG|HACK|XXX|NOTE)\b(?:\(([^)]+)\))?\s*:\s*(.*))',
    re.IGNORECASE,
)


@dataclass
class TodoItem:
    """Repräsentiert eine gefundene Aufgabe im Quellcode."""

    file_path: Path
    rel_path: str
    folder_name: str
    line_number: int  # 1-basiert
    column: int  # 1-basiert
    tag: str  # "TODO", "FIXME", "BUG", "HACK", "XXX", "NOTE"
    author: Optional[str]  # z. B. "lukas" in TODO(lukas):
    text: str  # Beschreibungstext nach dem Tag
    line_text: str  # Gesamte Quellcodezeile für Kontext und Vorschau


def scan_file_for_todos(
    file_path: Path,
    rel_path: str = "",
    folder_name: str = "",
    tags: Optional[Iterable[str]] = None,
    max_file_size_kb: int = 4096,
) -> List[TodoItem]:
    """Durchsucht eine einzelne Datei nach TODO/FIXME-Aufgabenkommentaren."""
    try:
        size = file_path.stat().st_size
        if size > max_file_size_kb * 1024:
            return []
    except (OSError, PermissionError):
        return []

    if is_binary_file(file_path):
        return []

    allowed_tags: Optional[Set[str]] = {t.upper() for t in tags} if tags else None

    items: List[TodoItem] = []
    encodings = ["utf-8", "cp1252", "latin-1"]

    lines: Optional[List[str]] = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                lines = f.readlines()
            break
        except (UnicodeDecodeError, OSError):
            continue

    if lines is None:
        return []

    for line_idx, raw_line in enumerate(lines, start=1):
        clean_line = raw_line.rstrip("\r\n")
        m = TODO_PATTERN.search(clean_line)
        if not m:
            continue

        if m.group(1):
            tag = m.group(1).upper()
            author = m.group(2).strip() if m.group(2) else None
            raw_text = m.group(3) or ""
            col = m.start(1) + 1
        else:
            tag = m.group(4).upper()
            author = m.group(5).strip() if m.group(5) else None
            raw_text = m.group(6) or ""
            col = m.start(4) + 1

        if allowed_tags and tag not in allowed_tags:
            continue

        # Schließende Kommentarzeichen (*/ oder -->) am Zeilenende entfernen
        text = re.sub(r'(\*/|-->)\s*$', '', raw_text).strip()

        items.append(
            TodoItem(
                file_path=file_path,
                rel_path=rel_path or file_path.name,
                folder_name=folder_name,
                line_number=line_idx,
                column=col,
                tag=tag,
                author=author,
                text=text,
                line_text=clean_line,
            )
        )

    return items


class TodoScanWorker(QThread):
    """Hintergrund-Thread für den asynchronen Scan aller Workspace-Ordner."""

    itemFound = Signal(object)  # TodoItem
    fileCompleted = Signal(object, object)  # Path, List[TodoItem]
    scanProgress = Signal(int, int)  # scanned_count, total_count
    scanFinished = Signal(object)  # List[TodoItem]

    def __init__(
        self,
        folders: List[Path],
        tags: Optional[Iterable[str]] = None,
        exclude_dirs: Optional[Set[str]] = None,
        max_file_size_kb: int = 4096,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.folders = [Path(f) for f in folders if Path(f).is_dir()]
        self.tags = tags
        self.exclude_dirs = exclude_dirs or set(DEFAULT_WORKSPACE_SKIP_DIRS)
        self.max_file_size_kb = max_file_size_kb
        self._is_stopped = False

    def stop(self):
        """Bricht den laufenden Scan sicher ab."""
        self._is_stopped = True

    def run(self):
        """Führt den Scan im Hintergrund aus."""
        candidate_files: List[Tuple[Path, str, str]] = []

        # 1. Dateien einsammeln (mit Ausschluss von VCS- und Build-Ordnern)
        for folder in self.folders:
            if self._is_stopped:
                return
            folder_name = folder.name
            for root, dirs, files in os.walk(folder):
                if self._is_stopped:
                    return
                # Verzeichnisse in-place filtern
                dirs[:] = [
                    d for d in dirs
                    if d not in self.exclude_dirs and not d.startswith(".")
                ]
                for file in files:
                    if file.startswith("."):
                        continue
                    file_path = Path(root) / file
                    try:
                        rel = str(file_path.relative_to(folder))
                    except ValueError:
                        rel = file_path.name
                    candidate_files.append((file_path, rel, folder_name))

        total_files = len(candidate_files)
        all_items: List[TodoItem] = []

        # 2. Dateien scannen
        for idx, (file_path, rel_path, folder_name) in enumerate(candidate_files, start=1):
            if self._is_stopped:
                return

            if idx % 20 == 0 or idx == total_files:
                self.scanProgress.emit(idx, total_files)

            file_items = scan_file_for_todos(
                file_path=file_path,
                rel_path=rel_path,
                folder_name=folder_name,
                tags=self.tags,
                max_file_size_kb=self.max_file_size_kb,
            )

            if file_items:
                all_items.extend(file_items)
                self.fileCompleted.emit(file_path, file_items)
                for item in file_items:
                    self.itemFound.emit(item)

        if not self._is_stopped:
            self.scanFinished.emit(all_items)


class TodoScannerManager(QObject):
    """Verwaltet den Aufgaben-Cache und koordiniert asynchrone Workspace-Scans."""

    scanStarted = Signal()
    scanProgress = Signal(int, int)  # scanned, total
    scanFinished = Signal(int, int)  # total_items, total_files
    todosUpdated = Signal(object)  # List[TodoItem]

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cache: Dict[Path, List[TodoItem]] = {}
        self._folders: List[Path] = []
        self._tags: Optional[Iterable[str]] = DEFAULT_TODO_TAGS
        self._worker: Optional[TodoScanWorker] = None

    @property
    def is_scanning(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def set_folders(self, folders: List[Path | str]):
        self._folders = [Path(f) for f in folders if Path(f).is_dir()]

    def start_scan(self, folders: Optional[List[Path | str]] = None):
        """Startet einen vollständigen asynchronen Hintergrundscan."""
        if folders is not None:
            self.set_folders(folders)

        self.stop_scan()
        self._cache.clear()
        self.scanStarted.emit()

        if not self._folders:
            self.todosUpdated.emit([])
            self.scanFinished.emit(0, 0)
            return

        self._worker = TodoScanWorker(
            folders=self._folders,
            tags=self._tags,
            parent=self,
        )
        self._worker.fileCompleted.connect(self._on_worker_file_completed)
        self._worker.scanProgress.connect(self.scanProgress.emit)
        self._worker.scanFinished.connect(self._on_worker_finished)
        self._worker.start()

    def stop_scan(self):
        """Stoppt einen aktuell laufenden Scan."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None

    def _on_worker_file_completed(self, file_path: Path, items: List[TodoItem]):
        self._cache[file_path] = items

    def _on_worker_finished(self, all_items: List[TodoItem]):
        self._worker = None
        sorted_items = self.get_all_todos()
        self.todosUpdated.emit(sorted_items)
        file_count = len(self._cache)
        self.scanFinished.emit(len(sorted_items), file_count)

    def rescan_file(self, file_path: Path | str) -> List[TodoItem]:
        """Scannt eine einzelne Datei synchron neu (z.B. direkt nach dem Speichern)."""
        file_path = Path(file_path)
        if not file_path.is_file():
            if file_path in self._cache:
                del self._cache[file_path]
                self.todosUpdated.emit(self.get_all_todos())
            return []

        rel_path = file_path.name
        folder_name = ""
        for folder in self._folders:
            try:
                rel_path = str(file_path.relative_to(folder))
                folder_name = folder.name
                break
            except ValueError:
                pass

        new_items = scan_file_for_todos(
            file_path=file_path,
            rel_path=rel_path,
            folder_name=folder_name,
            tags=self._tags,
        )

        if new_items:
            self._cache[file_path] = new_items
        elif file_path in self._cache:
            del self._cache[file_path]

        self.todosUpdated.emit(self.get_all_todos())
        return new_items

    def remove_file(self, file_path: Path | str):
        """Entfernt eine gelöschte Datei aus dem Aufgaben-Cache."""
        file_path = Path(file_path)
        if file_path in self._cache:
            del self._cache[file_path]
            self.todosUpdated.emit(self.get_all_todos())

    def clear(self):
        """Leert den gesamten Cache."""
        self.stop_scan()
        self._cache.clear()
        self.todosUpdated.emit([])

    def get_all_todos(self) -> List[TodoItem]:
        """Gibt alle gecachten Aufgaben sortiert nach Pfad und Zeilennummer zurück."""
        items: List[TodoItem] = []
        for file_path in sorted(self._cache.keys(), key=lambda p: str(p).lower()):
            file_todos = sorted(self._cache[file_path], key=lambda item: item.line_number)
            items.extend(file_todos)
        return items

    def get_todos_by_file(self) -> Dict[Path, List[TodoItem]]:
        """Gruppiert gecachte Aufgaben nach Datei."""
        result: Dict[Path, List[TodoItem]] = {}
        for file_path in sorted(self._cache.keys(), key=lambda p: str(p).lower()):
            result[file_path] = sorted(self._cache[file_path], key=lambda item: item.line_number)
        return result

    def get_todos_by_tag(self) -> Dict[str, List[TodoItem]]:
        """Gruppiert gecachte Aufgaben nach Tag (TODO, FIXME etc.)."""
        result: Dict[str, List[TodoItem]] = {}
        for item in self.get_all_todos():
            result.setdefault(item.tag, []).append(item)
        return result

    def get_counts(self) -> Tuple[int, int]:
        """Gibt (Gesamtzahl Aufgaben, Anzahl betroffener Dateien) zurück."""
        total_items = sum(len(v) for v in self._cache.values())
        return total_items, len(self._cache)
