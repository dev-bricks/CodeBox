# -*- coding: utf-8 -*-
"""
TranslationSystem - Multi-Language Support für CodeBox
======================================================
Version: 2.0.0 (Policy P-006 Tier-2 6-Sprachen-Standard)
Quelle: Policy P-006 / CONVENTIONS.md

Unterstützte Sprachen:
- de: Deutsch (Standard)
- en: English
- es: Español
- zh: 简体中文
- ja: 日本語
- ru: Русский

Deterministische 4-Stufen-Fallback-Kette:
  target_lang -> 'en' -> 'de' -> key

Verwendung:
-----------
from translator import get_translator, t, TranslationSystem

translator = get_translator('de')
label.setText(t('Datei'))
translator.set_language('es')
label.setText(t('Datei'))
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def detect_system_language() -> str:
    """Ermittelt die Systemsprache (de, en, es, zh, ja, ru). Fallback: 'de'."""
    try:
        import locale
        loc, _ = locale.getlocale()
        if loc:
            loc = loc.lower()
            if loc.startswith("de"):
                return "de"
            if loc.startswith("en"):
                return "en"
            if loc.startswith("es"):
                return "es"
            if loc.startswith("zh"):
                return "zh"
            if loc.startswith("ja"):
                return "ja"
            if loc.startswith("ru"):
                return "ru"
    except Exception:
        pass
    return "de"


class TranslationSystem:
    """Multi-Language Support System v2.0 with deterministic fallbacks."""

    SUPPORTED_LANGUAGES: Tuple[str, ...] = ("de", "en", "es", "zh", "ja", "ru")
    FALLBACK_LANGUAGES: Tuple[str, ...] = ("en", "de")
    LANGUAGE_NAMES: Dict[str, str] = {
        "de": "Deutsch",
        "en": "English",
        "es": "Español",
        "zh": "简体中文",
        "ja": "日本語",
        "ru": "Русский",
    }
    LANGUAGE_DISPLAY_NAMES: Dict[str, str] = {
        "de": "Deutsch (de)",
        "en": "English (en)",
        "es": "Español (es)",
        "zh": "简体中文 (zh)",
        "ja": "日本語 (ja)",
        "ru": "Русский (ru)",
    }

    def __init__(self, default_lang: str = "de", app_dir: Optional[Path] = None):
        """
        Initialisiert das Translation-System.

        Args:
            default_lang: Standard-Sprache ('de', 'en', 'es', 'zh', 'ja', 'ru')
            app_dir: Verzeichnis der Anwendung (default: Verzeichnis von translator.py)
        """
        self.current_lang = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "de"

        if app_dir is None:
            app_dir = Path(__file__).resolve().parent
        self.app_dir = Path(app_dir)

        self.translations_file = self.app_dir / "locales" / "translations.json"
        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Lädt Übersetzungen aus translations.json."""
        if self.translations_file.exists():
            try:
                with open(self.translations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.translations = data
                else:
                    self.translations = {}
            except Exception:
                self.translations = {}
        else:
            self.translations = {}

    def _save_translations(self) -> None:
        """Speichert Übersetzungen atomar in translations.json."""
        self.translations_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.translations_file.with_suffix(self.translations_file.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.translations, f, indent=2, ensure_ascii=False)
        tmp.replace(self.translations_file)

    def _new_translation_entry(self, de: str, en: str = "") -> Dict[str, str]:
        return {
            "de": de,
            "en": en,
            "es": "",
            "zh": "",
            "ja": "",
            "ru": "",
        }

    def t(self, key: str, **kwargs) -> str:
        """
        Übersetzt einen Key in die aktuelle Sprache mit 4-stufiger Fallback-Hierarchie:
        target -> en -> de -> key.

        Args:
            key: Translation-Key
            **kwargs: Optionale Platzhalter für .format()

        Returns:
            Übersetzter und formatierter Text
        """
        entry = self.translations.get(key)
        if isinstance(entry, dict):
            fallback_chain = (self.current_lang, *self.FALLBACK_LANGUAGES)
            for language in fallback_chain:
                value = entry.get(language)
                if isinstance(value, str) and value:
                    if kwargs:
                        try:
                            return value.format(**kwargs)
                        except (KeyError, IndexError, ValueError):
                            return value
                    return value

        if kwargs:
            try:
                return key.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return key
        return key

    def set_language(self, lang: str) -> bool:
        """Setzt die aktive Sprache, falls sie unterstützt wird."""
        if lang in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang
            return True
        return False

    def get_language(self) -> str:
        """Gibt die aktuell aktive Sprache zurück."""
        return self.current_lang

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Gibt die Liste der unterstützen Sprach-Codes zurück."""
        return list(cls.SUPPORTED_LANGUAGES)

    @classmethod
    def get_language_names(cls) -> Dict[str, str]:
        """Gibt das Mapping der Sprach-Codes auf native Namen zurück."""
        return dict(cls.LANGUAGE_NAMES)

    @classmethod
    def get_language_display_names(cls) -> Dict[str, str]:
        """Gibt das Mapping der Sprach-Codes auf Anzeigenamen zurück."""
        return dict(cls.LANGUAGE_DISPLAY_NAMES)

    def add_translation(self, key: str, de: str, en: str, **other_langs):
        """Fügt einen neuen Übersetzungseintrag hinzu oder aktualisiert ihn."""
        entry = self._new_translation_entry(de, en)
        for lang, val in other_langs.items():
            if lang in self.SUPPORTED_LANGUAGES:
                entry[lang] = val
        self.translations[key] = entry
        self._save_translations()


_default_translator: Optional[TranslationSystem] = None


def get_translator(lang: Optional[str] = None, app_dir: Optional[Path] = None) -> TranslationSystem:
    """Gibt die globale Singleton-Instanz von TranslationSystem zurück."""
    global _default_translator
    if _default_translator is None:
        _default_translator = TranslationSystem(lang or "de", app_dir)
    else:
        if app_dir is not None and _default_translator.app_dir != Path(app_dir):
            _default_translator = TranslationSystem(lang or _default_translator.current_lang, app_dir)
        elif lang is not None and lang != _default_translator.current_lang:
            _default_translator.set_language(lang)
    return _default_translator


def t(key: str, **kwargs) -> str:
    """Globale Hilfsfunktion zur Übersetzung mit der Standard-Instanz."""
    return get_translator().t(key, **kwargs)
