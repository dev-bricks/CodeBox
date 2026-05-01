# CodeBox Configuration Module

import json
from pathlib import Path

DEFAULT_SETTINGS = {
    "font_family": "Consolas",
    "font_size": 10,
    "tab_size": 4,
    "theme": "dark",
    "auto_save": False,
    "show_minimap": True,
    "recent_files": []
}

_SETTINGS_FILE = Path(__file__).parent / "settings.json"


def load_settings() -> dict:
    """Lädt Einstellungen aus settings.json"""
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                settings = DEFAULT_SETTINGS.copy()
                settings.update(saved)
                return settings
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Speichert Einstellungen"""
    try:
        with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
