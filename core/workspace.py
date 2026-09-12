#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace Manager - Multi-Root Workspace Unterstützung für CodeBox.

Verwaltet mehrere Projektordner (Roots) in einem gemeinsamen Arbeitsbereich:
- WorkspaceFolder: Datenklasse für einzelne Ordner im Arbeitsbereich
- WorkspaceManager: Zustandsverwaltung, Ereignissignale, Laden und Speichern
  von .codebox-workspace JSON-Dateien und projektübergreifende Dateisuche.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from PySide6.QtCore import QObject, Signal

DEFAULT_WORKSPACE_SKIP_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
    ".vs",
    ".eggs",
}


@dataclass
class WorkspaceFolder:
    """Ein einzelner Wurzelordner innerhalb eines Arbeitsbereichs."""

    path: Path
    name: str

    def to_dict(self, base_dir: Optional[Path] = None) -> dict:
        """Serialisiert den Ordner für das Workspace-JSON.

        Nutzt relative Pfade wenn base_dir gegeben ist, um Portabilität zu sichern.
        """
        if base_dir is not None:
            try:
                rel = os.path.relpath(self.path, base_dir)
                path_str = rel.replace("\\", "/")
            except ValueError:
                path_str = str(self.path).replace("\\", "/")
        else:
            path_str = str(self.path).replace("\\", "/")
        return {"path": path_str, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict, base_dir: Optional[Path] = None) -> Optional[WorkspaceFolder]:
        """Erstellt einen WorkspaceFolder aus einem Dict-Eintrag."""
        raw_path = data.get("path")
        if not raw_path:
            return None
        p = Path(raw_path)
        if not p.is_absolute() and base_dir is not None:
            p = (base_dir / p).resolve()
        else:
            p = p.resolve()
        name = data.get("name") or p.name or str(p)
        return cls(path=p, name=name)


class WorkspaceManager(QObject):
    """Zentraler Manager für Multi-Root-Arbeitsbereiche in CodeBox.

    Signals:
        foldersChanged: Wird emittiert, wenn Ordner hinzugefügt, entfernt oder geleert werden.
        activeFolderChanged(object): Wird emittiert, wenn der aktive Ordner gewechselt wird (Optional[Path]).
        workspaceLoaded(str): Wird emittiert, wenn ein Workspace aus einer Datei geladen wurde.
    """

    foldersChanged = Signal()
    activeFolderChanged = Signal(object)
    workspaceLoaded = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._folders: List[WorkspaceFolder] = []
        self._active_folder: Optional[Path] = None
        self._workspace_path: Optional[Path] = None
        self._name: str = ""

    @property
    def name(self) -> str:
        """Name des Arbeitsbereichs."""
        if self._name:
            return self._name
        if self._folders:
            if len(self._folders) == 1:
                return self._folders[0].name
            return f"{self._folders[0].name} (Arbeitsbereich)"
        return "Kein Arbeitsbereich"

    @name.setter
    def name(self, val: str):
        self._name = val

    @property
    def folders(self) -> List[WorkspaceFolder]:
        """Liste aller Ordner im Arbeitsbereich."""
        return list(self._folders)

    @property
    def folder_paths(self) -> List[Path]:
        """Liste aller absoluten Pfade der Ordner im Arbeitsbereich."""
        return [f.path for f in self._folders]

    @property
    def active_folder(self) -> Optional[Path]:
        """Der aktuell fokussierte oder ausgewählte Wurzelordner."""
        return self._active_folder

    @property
    def workspace_path(self) -> Optional[Path]:
        """Pfad zur geladenen .codebox-workspace Datei oder None."""
        return self._workspace_path

    @property
    def is_multi_root(self) -> bool:
        """Gibt True zurück, wenn mehr als ein Ordner im Arbeitsbereich liegt."""
        return len(self._folders) > 1

    @property
    def is_empty(self) -> bool:
        """Gibt True zurück, wenn keine Ordner geöffnet sind."""
        return len(self._folders) == 0

    def has_folder(self, path: Path | str) -> bool:
        """Prüft, ob ein Ordner bereits im Arbeitsbereich enthalten ist."""
        resolved = Path(path).resolve()
        return any(f.path == resolved for f in self._folders)

    def get_folder(self, path: Path | str) -> Optional[WorkspaceFolder]:
        """Gibt das WorkspaceFolder-Objekt für einen Pfad zurück, falls vorhanden."""
        resolved = Path(path).resolve()
        for f in self._folders:
            if f.path == resolved:
                return f
        return None

    def add_folder(
        self,
        path: Path | str,
        name: Optional[str] = None,
        make_active: bool = True,
    ) -> bool:
        """Fügt einen Ordner zum Arbeitsbereich hinzu.

        Args:
            path: Absoluter oder relativer Pfad zum Ordner.
            name: Optionaler Anzeigename. Falls None, wird der Ordnername verwendet.
            make_active: Ob der neue Ordner sofort aktiv gesetzt werden soll.

        Returns:
            True, wenn der Ordner erfolgreich hinzugefügt wurde, sonst False.
        """
        try:
            resolved = Path(path).resolve()
        except (ValueError, OSError):
            return False

        if not resolved.exists() or not resolved.is_dir():
            return False

        # Bereits vorhanden?
        for f in self._folders:
            if f.path == resolved:
                if make_active and self._active_folder != resolved:
                    self.set_active_folder(resolved)
                return True

        folder_name = name or resolved.name or str(resolved)
        wf = WorkspaceFolder(path=resolved, name=folder_name)
        self._folders.append(wf)

        if make_active or self._active_folder is None:
            self._active_folder = resolved
            self.activeFolderChanged.emit(self._active_folder)

        self.foldersChanged.emit()
        return True

    def remove_folder(self, path: Path | str) -> bool:
        """Entfernt einen Ordner aus dem Arbeitsbereich."""
        try:
            resolved = Path(path).resolve()
        except (ValueError, OSError):
            return False

        idx = -1
        for i, f in enumerate(self._folders):
            if f.path == resolved:
                idx = i
                break

        if idx == -1:
            return False

        self._folders.pop(idx)

        # Aktiven Ordner nachführen, falls der gelöschte aktiv war
        if self._active_folder == resolved:
            if self._folders:
                self._active_folder = self._folders[0].path
            else:
                self._active_folder = None
            self.activeFolderChanged.emit(self._active_folder)

        self.foldersChanged.emit()
        return True

    def set_active_folder(self, path: Optional[Path | str]):
        """Setzt den aktiven Wurzelordner."""
        if path is None:
            if self._active_folder is not None:
                self._active_folder = None
                self.activeFolderChanged.emit(None)
            return

        resolved = Path(path).resolve()
        if self._active_folder == resolved:
            return

        self._active_folder = resolved
        self.activeFolderChanged.emit(self._active_folder)

    def set_single_folder(self, path: Path | str, name: Optional[str] = None) -> bool:
        """Ersetzt alle bestehenden Ordner durch einen einzigen neuen Ordner."""
        try:
            resolved = Path(path).resolve()
        except (ValueError, OSError):
            return False

        if not resolved.exists() or not resolved.is_dir():
            return False

        self._folders.clear()
        self._workspace_path = None
        self._name = ""
        return self.add_folder(resolved, name=name, make_active=True)

    def clear(self):
        """Leert alle Ordner und setzt den Arbeitsbereich zurück."""
        self._folders.clear()
        self._active_folder = None
        self._workspace_path = None
        self._name = ""
        self.activeFolderChanged.emit(None)
        self.foldersChanged.emit()

    def find_folder_for_file(self, file_path: Path | str) -> Optional[Path]:
        """Ermittelt, zu welchem Workspace-Ordner eine gegebene Datei gehört.

        Gibt bei geschachtelten Ordnern den spezifischsten (längsten) Pfad zurück.
        """
        try:
            resolved_file = Path(file_path).resolve()
        except (ValueError, OSError):
            return None

        matching: List[Path] = []
        for f in self._folders:
            try:
                resolved_file.relative_to(f.path)
                matching.append(f.path)
            except ValueError:
                continue

        if not matching:
            return None

        matching.sort(key=lambda p: len(str(p)), reverse=True)
        return matching[0]

    def save_workspace(self, file_path: Path | str) -> bool:
        """Speichert die Konfiguration in eine .codebox-workspace Datei."""
        try:
            target = Path(file_path).resolve()
            base_dir = target.parent
            data = {
                "name": self._name or (self._folders[0].name if self._folders else "Workspace"),
                "folders": [f.to_dict(base_dir=base_dir) for f in self._folders],
                "settings": {},
            }
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._workspace_path = target
            return True
        except (OSError, ValueError):
            return False

    def load_workspace(self, file_path: Path | str) -> bool:
        """Lädt einen Arbeitsbereich aus einer .codebox-workspace Datei."""
        try:
            target = Path(file_path).resolve()
            if not target.exists() or not target.is_file():
                return False

            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)

            base_dir = target.parent
            folders_data = data.get("folders", [])

            new_folders: List[WorkspaceFolder] = []
            for item in folders_data:
                wf = WorkspaceFolder.from_dict(item, base_dir=base_dir)
                if wf and wf.path.exists() and wf.path.is_dir():
                    new_folders.append(wf)

            self._folders = new_folders
            self._name = data.get("name", target.stem)
            self._workspace_path = target

            if self._folders:
                self._active_folder = self._folders[0].path
            else:
                self._active_folder = None

            self.workspaceLoaded.emit(str(target))
            self.foldersChanged.emit()
            self.activeFolderChanged.emit(self._active_folder)
            return True
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    def collect_all_files(
        self,
        max_files: int = 2000,
        skip_dirs: Optional[Set[str]] = None,
    ) -> List[Tuple[str, Path, str]]:
        """Sammelt Dateien aus allen Wurzelordnern des Arbeitsbereichs.

        Returns:
            Liste von Tupeln: (relativer_pfad_mit_forward_slashes, absoluter_Path, ordner_name)
        """
        collected: List[Tuple[str, Path, str]] = []
        ignored = skip_dirs or DEFAULT_WORKSPACE_SKIP_DIRS

        for folder in self._folders:
            root_path = folder.path
            if not root_path.exists():
                continue

            for root, dirs, files in os.walk(str(root_path)):
                dirs[:] = [
                    d for d in dirs
                    if d not in ignored and not d.startswith(".")
                ]

                for f in files:
                    if f.startswith(".") and f != ".gitignore":
                        continue
                    abs_p = Path(root) / f
                    try:
                        rel_p = abs_p.relative_to(root_path)
                        rel_str = str(rel_p).replace("\\", "/")
                    except ValueError:
                        rel_str = f

                    collected.append((rel_str, abs_p, folder.name))

                    if len(collected) >= max_files:
                        return collected

        return collected
