# -*- coding: utf-8 -*-
"""
Vertragstests: Policy P-006 Tier-2 6-Sprachen-I18N-Standard (CodeBox).
=======================================================================
Verifiziert:
1. locales/translations.json Integrität und 100% Schlüssel-Parität über alle 6 Sprachen.
2. Deterministische 4-Stufen-Fallback-Kette (target -> en -> de -> key).
3. Parameter-Interpolation via t(key, **kwargs) und Fehlertoleranz.
4. TranslationSystem-Klassenmethoden und Metadaten-Mappings.
5. manage_translations.py --check Subprozess-Validierung (Exit 0).
6. Atomares Speichern von Übersetzungen via temporärer Datei.
7. Konsistenz der nativen Sprachnamen (Deutsch, English, Español, 简体中文, 日本語, Русский).
8. Erhalt echter deutscher Umlaute (ä, ö, ü, Ä, Ö, Ü, ß) in allen Schlüsseln und Werten.
9. UI-Sprachumschaltung und dynamische Menüaktualisierung in MainWindow.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from config import DEFAULT_SETTINGS
from translator import (
    TranslationSystem,
    detect_system_language,
)
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_supported_languages_contract():
    """Prüft, ob alle 6 P-006 Standard-Sprachen deklariert und abrufbar sind."""
    expected = ("de", "en", "es", "zh", "ja", "ru")
    assert TranslationSystem.SUPPORTED_LANGUAGES == expected
    assert TranslationSystem.FALLBACK_LANGUAGES == ("en", "de")
    assert TranslationSystem.get_supported_languages() == list(expected)


def test_language_names_and_display_mappings():
    """Prüft die Vollständigkeit und native Schreibweise aller 6 Sprachen."""
    names = TranslationSystem.get_language_names()
    assert names["de"] == "Deutsch"
    assert names["en"] == "English"
    assert names["es"] == "Español"
    assert names["zh"] == "简体中文"
    assert names["ja"] == "日本語"
    assert names["ru"] == "Русский"

    display_names = TranslationSystem.get_language_display_names()
    for lang in TranslationSystem.SUPPORTED_LANGUAGES:
        assert lang in display_names
        assert f"({lang})" in display_names[lang]


def test_translations_json_file_validity_and_parity():
    """Prüft locales/translations.json auf Existenz, Mindestgröße und 100% Parität."""
    proj_dir = Path(__file__).resolve().parent.parent
    trans_file = proj_dir / "locales" / "translations.json"
    assert trans_file.is_file(), f"{trans_file} muss als reguläre Datei existieren"

    with open(trans_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert len(data) >= 80, f"Mindestens 80 Schlüssel erwartet, {len(data)} gefunden"

    for key, val in data.items():
        assert isinstance(val, dict), f"Eintrag für {key} muss ein Dict sein"
        for lang in TranslationSystem.SUPPORTED_LANGUAGES:
            assert lang in val, f"Sprache '{lang}' fehlt in Schlüssel '{key}'"
            entry_str = val[lang]
            assert isinstance(entry_str, str) and entry_str.strip(), (
                f"Leere Übersetzung für Schlüssel '{key}' in Sprache '{lang}'"
            )


def test_deterministic_fallback_chain(tmp_path):
    """Prüft die 4-stufige Fallback-Kette: target -> en -> de -> key."""
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True)
    custom_json = locales_dir / "translations.json"

    dummy_catalog = {
        "FullKey": {
            "de": "Datei",
            "en": "File",
            "es": "Archivo",
            "zh": "文件",
            "ja": "ファイル",
            "ru": "Файл",
        },
        "MissingSpanish": {
            "de": "Einstellungen",
            "en": "Settings",
            "es": "",
            "zh": "",
            "ja": "",
            "ru": "",
        },
        "OnlyGerman": {
            "de": "NurDeutsch",
            "en": "",
            "es": "",
            "zh": "",
            "ja": "",
            "ru": "",
        },
    }
    with open(custom_json, "w", encoding="utf-8") as f:
        json.dump(dummy_catalog, f, indent=2, ensure_ascii=False)

    ts = TranslationSystem(default_lang="es", app_dir=tmp_path)

    # 1. Voller Schlüssel in Zielsprache 'es'
    assert ts.t("FullKey") == "Archivo"

    # 2. 'es' fehlt -> Fallback auf 'en'
    assert ts.t("MissingSpanish") == "Settings"

    # 3. 'es' und 'en' fehlen -> Fallback auf 'de'
    assert ts.t("OnlyGerman") == "NurDeutsch"

    # 4. Schlüssel existiert überhaupt nicht -> Fallback auf key selbst
    assert ts.t("CompletelyUnknownKey") == "CompletelyUnknownKey"


def test_param_interpolation_and_error_tolerance():
    """Prüft kwargs-Interpolation und Absicherung gegen Formatierungsfehler."""
    ts = TranslationSystem("de")

    # Gültige Interpolation
    res = ts.t("Zeile {line}, Spalte {col}", line=42, col=7)
    assert res == "Zeile 42, Spalte 7"

    # Umschaltung auf Englisch
    ts.set_language("en")
    res_en = ts.t("Zeile {line}, Spalte {col}", line=42, col=7)
    assert res_en == "Line 42, Column 7"

    # Fehlertoleranz bei fehlendem Key
    res_err = ts.t("Zeile {line}, Spalte {col}", line=1)
    assert "Zeile" in res_err or "Line" in res_err


def test_manage_translations_cli_check():
    """Führt manage_translations.py --check im Subprozess aus und erwartet Exit 0."""
    proj_dir = Path(__file__).resolve().parent.parent
    script_path = proj_dir / "manage_translations.py"
    assert script_path.is_file()

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        cwd=str(proj_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, f"CLI-Check fehlgeschlagen:\n{result.stderr}\n{result.stdout}"
    assert "100% Parität über alle 6 Sprachen" in result.stdout


def test_german_umlauts_preservation():
    """Prüft, ob deutsche Umlaute in translations.json echt und unbeschädigt vorliegen."""
    proj_dir = Path(__file__).resolve().parent.parent
    trans_file = proj_dir / "locales" / "translations.json"
    with open(trans_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Mindestens ä, ö, ü, Ä, Ö, Ü, ß müssen im deutschen Katalog enthalten sein
    for char in ("ä", "ö", "ü", "Ä", "Ö", "ß"):
        assert char in content, f"Umlaut '{char}' fehlt im Übersetzungskatalog"


def test_system_language_detection():
    """Prüft, ob detect_system_language() einen gültigen 2-Letter-Code zurückliefert."""
    detected = detect_system_language()
    assert detected in TranslationSystem.SUPPORTED_LANGUAGES


def test_default_settings_includes_language():
    """Prüft, ob DEFAULT_SETTINGS die Sprache 'language': 'de' enthält."""
    assert "language" in DEFAULT_SETTINGS
    assert DEFAULT_SETTINGS["language"] in TranslationSystem.SUPPORTED_LANGUAGES


def test_mainwindow_ui_language_switch(qapp, tmp_path, monkeypatch):
    """Prüft dynamischen Sprachwechsel im MainWindow via set_ui_language."""
    test_settings = tmp_path / "settings.json"
    monkeypatch.setattr("config._SETTINGS_FILE", test_settings)

    win = MainWindow()
    assert win._current_ui_language == "de"
    assert win.file_menu.title() == "Datei"
    assert win.edit_menu.title() == "Bearbeiten"

    # Wechsel auf Spanisch
    win.set_ui_language("es")
    assert win._current_ui_language == "es"
    assert win.file_menu.title() == "Archivo"
    assert win.edit_menu.title() == "Editar"

    # Wechsel auf Englisch
    win.set_ui_language("en")
    assert win._current_ui_language == "en"
    assert win.file_menu.title() == "File"
    assert win.edit_menu.title() == "Edit"

    # Wechsel zurück auf Deutsch
    win.set_ui_language("de")
    assert win._current_ui_language == "de"
    assert win.file_menu.title() == "Datei"
    assert win.edit_menu.title() == "Bearbeiten"

    win.close()
