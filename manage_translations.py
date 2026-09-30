# -*- coding: utf-8 -*-
"""
manage_translations.py - Multi-Language Scanner & Parity Validator für CodeBox
==============================================================================
Policy P-006 Tier-2 6-Sprachen-Standard (DE, EN, ES, ZH, JA, RU).

Verwendung:
    python manage_translations.py --check
    python manage_translations.py --stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from translator import TranslationSystem

SUPPORTED_LANGUAGES = TranslationSystem.SUPPORTED_LANGUAGES
TRANSLATION_FILE = "locales/translations.json"


def check_translations(source_dir: str = ".") -> int:
    """Prüft translations.json auf 100% Parität über alle 6 Sprachen."""
    trans_file = Path(source_dir) / TRANSLATION_FILE
    if not trans_file.is_file():
        print(f"[!] Übersetzungsdatei nicht gefunden: {trans_file}")
        return 1

    try:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[!] Fehler beim Lesen von {trans_file}: {exc}")
        return 1

    total_keys = len(data)
    print(f"=== Translation Parity Check: {total_keys} Keys in {trans_file} ===")

    missing: Dict[str, List[str]] = {lang: [] for lang in SUPPORTED_LANGUAGES}
    for key, trans in data.items():
        if not isinstance(trans, dict):
            print(f"[!] Ungültiger Eintrag (kein dict) für Key: {key}")
            return 1
        for lang in SUPPORTED_LANGUAGES:
            val = trans.get(lang)
            if not val or not isinstance(val, str) or not val.strip():
                missing[lang].append(key)

    has_error = False
    for lang in SUPPORTED_LANGUAGES:
        lang_missing = missing[lang]
        status = "OK" if not lang_missing else f"FEHLEN {len(lang_missing)}"
        print(f"  [{status}] {lang} ({TranslationSystem.LANGUAGE_NAMES.get(lang, lang)}): {total_keys - len(lang_missing)}/{total_keys}")
        if lang_missing:
            has_error = True
            for m in lang_missing[:5]:
                print(f"       - {m}")
            if len(lang_missing) > 5:
                print(f"       ... und {len(lang_missing) - 5} weitere")

    if has_error:
        print("\n[!] Translation Parity Check FEHLGESCHLAGEN.")
        return 1

    print("\n[ok] 100% Parität über alle 6 Sprachen nach Policy P-006.")
    return 0


def stats_translations(source_dir: str = ".") -> int:
    """Zeigt Statistiken zur Übersetzungsabdeckung an."""
    trans_file = Path(source_dir) / TRANSLATION_FILE
    if not trans_file.is_file():
        print(f"[!] Übersetzungsdatei nicht gefunden: {trans_file}")
        return 1

    with open(trans_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_keys = len(data)
    print(f"=== Translation Catalog Stats ({total_keys} Keys) ===")
    for lang in SUPPORTED_LANGUAGES:
        present = sum(1 for v in data.values() if isinstance(v, dict) and v.get(lang) and v[lang].strip())
        pct = (present / total_keys * 100) if total_keys else 0
        name = TranslationSystem.LANGUAGE_NAMES.get(lang, lang)
        print(f"  - {lang} ({name}): {present}/{total_keys} ({pct:.1f}%)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CodeBox Translation Manager & Parity Validator")
    parser.add_argument("--check", action="store_true", help="Prüfe 100% Parität über alle 6 Sprachen")
    parser.add_argument("--stats", action="store_true", help="Zeige Statistiken zur Übersetzungsabdeckung")
    parser.add_argument("--dir", default=".", help="Projektverzeichnis (Standard: .)")

    args = parser.parse_args()

    if args.check:
        return check_translations(args.dir)
    elif args.stats:
        return stats_translations(args.dir)
    else:
        # Default behavior: run check
        return check_translations(args.dir)


if __name__ == "__main__":
    sys.exit(main())
