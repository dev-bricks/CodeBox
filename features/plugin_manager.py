#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin-Manager für CodeBox.
Verwaltet dynamische Sprach-Erweiterungen (Python-Module und deklarative JSON-Dateien).
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from languages import (
    LanguageProvider,
    DeclarativeLanguageProvider,
    register_provider,
    unregister_provider,
)


@dataclass
class PluginInfo:
    """Metadaten und Status eines CodeBox-Plugins."""
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    provider: Optional[LanguageProvider] = None
    file_path: Optional[str] = None
    plugin_type: str = "declarative_json"  # 'declarative_json', 'python', 'builtin'
    enabled: bool = True
    error: Optional[str] = None
    extensions: List[str] = field(default_factory=list)


class PluginManager:
    """
    Entdeckt, lädt, aktiviert und deaktiviert Sprach-Plugins für CodeBox.
    """

    def __init__(self, plugin_dirs: Optional[List[Union[str, Path]]] = None):
        self._plugin_dirs: List[Path] = []
        if plugin_dirs:
            for p in plugin_dirs:
                self._plugin_dirs.append(Path(p).resolve())
        else:
            self._plugin_dirs = self._default_search_dirs()

        self._plugins: Dict[str, PluginInfo] = {}
        self._failed_plugins: Dict[str, str] = {}

    def _default_search_dirs(self) -> List[Path]:
        dirs: List[Path] = []
        # 1. User Home Directory (.codebox/plugins)
        user_home_plugins = Path.home() / ".codebox" / "plugins"
        dirs.append(user_home_plugins)

        # 2. Windows AppData / Roaming
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "CodeBox" / "plugins")

        # 3. Project / Application Root plugins/
        app_root = Path(__file__).resolve().parent.parent
        dirs.append(app_root / "plugins")

        # Unique paths preserving order
        unique_dirs = []
        for d in dirs:
            if d not in unique_dirs:
                unique_dirs.append(d)
        return unique_dirs

    def get_plugin_dirs(self) -> List[Path]:
        """Gibt die konfigurierten Suchpfade für Plugins zurück."""
        return list(self._plugin_dirs)

    def add_plugin_dir(self, directory: Union[str, Path]) -> None:
        """Fügt ein neues Suchverzeichnis hinzu."""
        path = Path(directory).resolve()
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def get_primary_plugin_dir(self) -> Path:
        """Gibt das bevorzugte Zielverzeichnis für neue Benutzer-Plugins zurück."""
        primary = Path.home() / ".codebox" / "plugins"
        try:
            primary.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return primary

    def discover_and_load_all(self) -> List[PluginInfo]:
        """
        Durchsucht alle konfigurierten Verzeichnisse nach .json- und .py-Plugins.
        """
        loaded = []
        for directory in self._plugin_dirs:
            if directory.exists() and directory.is_dir():
                # Lade JSON-Sprachdefinitionen
                for json_file in sorted(directory.glob("*.json")):
                    try:
                        info = self.load_plugin(json_file)
                        if info and info.enabled:
                            loaded.append(info)
                    except Exception as exc:
                        self._failed_plugins[str(json_file)] = str(exc)

                # Lade Python-Sprachmodule
                for py_file in sorted(directory.glob("*.py")):
                    if py_file.name.startswith("__"):
                        continue
                    try:
                        info = self.load_plugin(py_file)
                        if info and info.enabled:
                            loaded.append(info)
                    except Exception as exc:
                        self._failed_plugins[str(py_file)] = str(exc)
        return loaded

    def load_plugin(self, path: Union[str, Path]) -> PluginInfo:
        """
        Lädt ein einzelnes Plugin aus einer Datei (.json oder .py).
        """
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Plugin file does not exist: {file_path}")

        if file_path.suffix.lower() == ".json":
            return self._load_json_plugin(file_path)
        elif file_path.suffix.lower() == ".py":
            return self._load_python_plugin(file_path)
        else:
            raise ValueError(f"Unsupported plugin file type: {file_path.suffix}")

    def _load_json_plugin(self, file_path: Path) -> PluginInfo:
        try:
            provider = DeclarativeLanguageProvider.from_json_file(file_path)
            name = provider.get_name()
            register_provider(provider, override=True)
            info = PluginInfo(
                name=name,
                version=provider.version,
                author=provider.author,
                description=provider.description,
                provider=provider,
                file_path=str(file_path),
                plugin_type="declarative_json",
                enabled=True,
                extensions=provider.get_extensions(),
            )
            self._plugins[name] = info
            self._failed_plugins.pop(str(file_path), None)
            return info
        except Exception as exc:
            self._failed_plugins[str(file_path)] = str(exc)
            info = PluginInfo(
                name=file_path.stem,
                file_path=str(file_path),
                plugin_type="declarative_json",
                enabled=False,
                error=str(exc),
            )
            self._plugins[file_path.stem] = info
            raise

    def _load_python_plugin(self, file_path: Path) -> PluginInfo:
        module_name = f"codebox_plugin_{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {file_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 1. Prüfe auf setup() Funktion
            if hasattr(module, "setup") and callable(module.setup):
                setup_res = module.setup(self)
                if isinstance(setup_res, LanguageProvider):
                    provider = setup_res
                elif isinstance(setup_res, PluginInfo):
                    self._plugins[setup_res.name] = setup_res
                    return setup_res
                else:
                    provider = getattr(module, "PROVIDER", None)
            else:
                provider = getattr(module, "PROVIDER", None)

            # 2. Wenn kein expliziter Provider, suche nach LanguageProvider-Klassen
            if not provider:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, LanguageProvider)
                        and attr not in (LanguageProvider, DeclarativeLanguageProvider)
                    ):
                        provider = attr()
                        break

            if not provider or not isinstance(provider, LanguageProvider):
                raise ValueError(
                    f"Python plugin '{file_path.name}' does not provide a LanguageProvider subclass or setup() method"
                )

            name = provider.get_name()
            register_provider(provider, override=True)

            version = getattr(module, "__version__", "1.0.0")
            author = getattr(module, "__author__", "")
            description = getattr(module, "__doc__", "") or ""

            info = PluginInfo(
                name=name,
                version=version,
                author=author,
                description=description.strip(),
                provider=provider,
                file_path=str(file_path),
                plugin_type="python",
                enabled=True,
                extensions=provider.get_extensions(),
            )
            self._plugins[name] = info
            self._failed_plugins.pop(str(file_path), None)
            return info
        except Exception as exc:
            self._failed_plugins[str(file_path)] = str(exc)
            info = PluginInfo(
                name=file_path.stem,
                file_path=str(file_path),
                plugin_type="python",
                enabled=False,
                error=str(exc),
            )
            self._plugins[file_path.stem] = info
            raise

    def unload_plugin(self, name: str) -> bool:
        """Deaktiviert ein Plugin und entfernt den Provider aus der Registry."""
        info = self._plugins.get(name)
        if info:
            unregister_provider(name)
            info.enabled = False
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        """Aktiviert ein zuvor deaktiviertes Plugin wieder."""
        info = self._plugins.get(name)
        if info and info.provider and not info.enabled:
            register_provider(info.provider, override=True)
            info.enabled = True
            return True
        return False

    def get_loaded_plugins(self) -> List[PluginInfo]:
        """Gibt alle erfolgreich geladenen Plugins zurück."""
        return [p for p in self._plugins.values() if p.enabled and not p.error]

    def get_all_plugins(self) -> List[PluginInfo]:
        """Gibt alle bekannten Plugins (inkl. deaktivierter oder fehlerhafter) zurück."""
        return list(self._plugins.values())

    def get_failed_plugins(self) -> Dict[str, str]:
        """Gibt ein Mapping von Dateipfaden zu Fehlermeldungen zurück."""
        return dict(self._failed_plugins)

    def create_declarative_template(
        self, target_dir: Union[str, Path], name: str, extensions: List[str]
    ) -> Path:
        """Erstellt eine JSON-Vorlage für eine neue Sprache."""
        directory = Path(target_dir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / f"{name.lower()}_plugin.json"

        template = {
            "name": name,
            "version": "1.0.0",
            "author": "Dein Name",
            "description": f"Sprachunterstützung für {name}",
            "extensions": [ext.lstrip(".") for ext in extensions],
            "keywords": ["if", "else", "for", "while", "return", "function", "var", "let", "const"],
            "builtins": ["print", "len", "log"],
            "snippets": {
                "fn": "function name() {\n    \n}",
                "if": "if (condition) {\n    \n}"
            },
            "run_command": [name.lower(), "{file}"],
            "debug_command": None,
            "linter_command": None,
            "comment_style": ["//", ["/*", "*/"]],
            "bracket_pairs": {"(": ")", "[": "]", "{": "}"},
            "auto_close_pairs": {"(": ")", "[": "]", "{": "}", "\"": "\"", "'": "'"},
            "indent_triggers": ["{"],
            "dedent_triggers": ["}"]
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

        return file_path
