#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das CodeBox Plugin-System, DeclarativeLanguageProvider und dynamische Registrierung.
"""

import json
import pytest
from PySide6.QtWidgets import QApplication

from languages import (
    LanguageProvider,
    DeclarativeLanguageProvider,
    register_provider,
    unregister_provider,
    reset_providers,
    is_provider_registered,
    get_provider_for_extension,
    get_provider_by_name,
    get_all_providers,
    add_provider_listener,
    remove_provider_listener,
)
from features.plugin_manager import PluginManager
from ui.plugins_dialog import PluginsDialog
from ui.shortcuts_dialog import ShortcutsDialog, SHORTCUTS_DATA
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def clean_providers():
    """Stellt sicher, dass vor und nach jedem Test der Standard-Zustand hergestellt wird."""
    reset_providers()
    yield
    reset_providers()


class DummyCustomProvider(LanguageProvider):
    def get_name(self) -> str:
        return "CustomLang"

    def get_extensions(self) -> list[str]:
        return ["clang", "cl"]

    def get_keywords(self) -> list[str]:
        return ["custom_kw1", "custom_kw2"]

    def get_run_command(self, file_path: str) -> list[str]:
        return ["custom-exec", file_path]


def test_dynamic_register_and_unregister():
    provider = DummyCustomProvider()
    assert not is_provider_registered("CustomLang")
    assert get_provider_for_extension("clang") is None

    # Registrieren
    register_provider(provider)
    assert is_provider_registered("CustomLang")
    assert get_provider_by_name("CustomLang") is provider
    assert get_provider_for_extension("clang") is provider
    assert get_provider_for_extension("cl") is provider
    assert get_provider_for_extension(".clang") is provider
    assert provider in get_all_providers()

    # Unregistrieren
    removed = unregister_provider("CustomLang")
    assert removed is provider
    assert not is_provider_registered("CustomLang")
    assert get_provider_for_extension("clang") is None
    assert get_provider_by_name("CustomLang") is None


def test_provider_listener_callbacks():
    calls = []

    def callback():
        calls.append(True)

    add_provider_listener(callback)

    provider = DummyCustomProvider()
    register_provider(provider)
    assert len(calls) == 1

    unregister_provider("CustomLang")
    assert len(calls) == 2

    remove_provider_listener(callback)
    register_provider(provider)
    # Nach Entfernen kein weiterer Aufruf
    assert len(calls) == 2


def test_declarative_provider_from_dict_and_json(tmp_path):
    data = {
        "name": "NimTest",
        "version": "1.2.0",
        "author": "NimDev",
        "description": "Nim support",
        "extensions": ["nim", "nims"],
        "keywords": ["proc", "type", "var", "let"],
        "builtins": ["echo", "len"],
        "snippets": {"proc": "proc name() =\n  discard"},
        "run_command": ["nim", "c", "-r", "{file}"],
        "debug_command": ["gdb", "{file}"],
        "comment_style": ["#", ["#[", "]#"]],
        "bracket_pairs": {"(": ")", "[": "]"},
        "auto_close_pairs": {"(": ")", "\"": "\""},
        "indent_triggers": [":"],
        "dedent_triggers": ["return"],
    }

    # Dict
    provider = DeclarativeLanguageProvider.from_dict(data)
    assert provider.get_name() == "NimTest"
    assert provider.get_extensions() == ["nim", "nims"]
    assert "proc" in provider.get_keywords()
    assert "echo" in provider.get_builtins()
    assert "proc" in provider.get_snippets()
    assert provider.get_run_command("main.nim") == ["nim", "c", "-r", "main.nim"]
    assert provider.get_debug_command("main.nim") == ["gdb", "main.nim"]
    assert provider.get_comment_style() == ("#", ("#[", "]#"))
    assert provider.get_bracket_pairs() == {"(": ")", "[": "]"}
    assert provider.get_indent_triggers() == [":"]
    assert provider.get_dedent_triggers() == ["return"]
    assert provider.version == "1.2.0"
    assert provider.author == "NimDev"

    # JSON File
    json_path = tmp_path / "nim_plugin.json"
    json_path.write_text(json.dumps(data), encoding="utf-8")

    loaded_provider = DeclarativeLanguageProvider.from_json_file(json_path)
    assert loaded_provider.get_name() == "NimTest"
    assert loaded_provider.get_extensions() == ["nim", "nims"]


def test_plugin_manager_json_and_py_loading(tmp_path):
    mgr = PluginManager(plugin_dirs=[tmp_path])

    # 1. JSON Plugin
    json_plugin = tmp_path / "zig_plugin.json"
    json_plugin.write_text(json.dumps({
        "name": "ZigLang",
        "extensions": ["zig"],
        "keywords": ["const", "var", "fn"],
        "run_command": ["zig", "run", "{file}"],
    }), encoding="utf-8")

    # 2. Python Plugin
    py_plugin = tmp_path / "custom_kotlin.py"
    py_plugin.write_text('''
from languages.base import LanguageProvider

class KotlinProvider(LanguageProvider):
    def get_name(self):
        return "Kotlin"
    def get_extensions(self):
        return ["kt", "kts"]
    def get_keywords(self):
        return ["fun", "val", "var"]
    def get_run_command(self, file_path):
        return ["kotlinc", "-script", file_path]
''', encoding="utf-8")

    # 3. Invalid JSON Plugin (soll nicht crashen)
    bad_plugin = tmp_path / "corrupt_plugin.json"
    bad_plugin.write_text("{ this is not valid json }", encoding="utf-8")

    loaded = mgr.discover_and_load_all()
    assert len(loaded) == 2
    names = [p.name for p in loaded]
    assert "ZigLang" in names
    assert "Kotlin" in names

    assert is_provider_registered("ZigLang")
    assert is_provider_registered("Kotlin")
    assert get_provider_for_extension("zig") is not None
    assert get_provider_for_extension("kt") is not None

    # Failed plugins check
    failed = mgr.get_failed_plugins()
    assert str(bad_plugin.resolve()) in failed

    # Unload / Deaktivieren
    assert mgr.unload_plugin("ZigLang")
    assert not is_provider_registered("ZigLang")
    assert get_provider_for_extension("zig") is None

    # Enable / Wieder aktivieren
    assert mgr.enable_plugin("ZigLang")
    assert is_provider_registered("ZigLang")


def test_plugin_manager_template_creation(tmp_path):
    mgr = PluginManager(plugin_dirs=[tmp_path])
    target = mgr.create_declarative_template(tmp_path, "VLang", ["v", "vsh"])
    assert target.exists()

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["name"] == "VLang"
    assert "v" in data["extensions"]
    assert "vsh" in data["extensions"]


def test_plugins_dialog_ui(qapp, tmp_path):
    mgr = PluginManager(plugin_dirs=[tmp_path])
    dialog = PluginsDialog(mgr)
    dialog.show()
    qapp.processEvents()

    assert dialog.table.rowCount() >= 7  # Builtins
    dialog.table.selectRow(0)
    assert len(dialog.details_text.toPlainText()) > 0

    dialog.close()


def test_shortcuts_dialog_ui(qapp):
    dialog = ShortcutsDialog()
    dialog.show()
    qapp.processEvents()

    assert dialog.table.rowCount() == len(SHORTCUTS_DATA)
    # Test Filter
    dialog.filter_table("Speichern")
    visible_count = sum(1 for r in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(r))
    assert visible_count >= 1

    dialog.filter_table("")
    visible_count_all = sum(1 for r in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(r))
    assert visible_count_all == len(SHORTCUTS_DATA)

    dialog.close()


def test_main_window_updates_on_provider_change(qapp):
    window = MainWindow()
    initial_count = window.lang_combo.count()

    provider = DummyCustomProvider()
    register_provider(provider)
    qapp.processEvents()

    assert window.lang_combo.count() == initial_count + 1
    assert window.lang_combo.findText("CustomLang") >= 0

    unregister_provider("CustomLang")
    qapp.processEvents()

    assert window.lang_combo.count() == initial_count
    assert window.lang_combo.findText("CustomLang") == -1

    window.close()


def test_highlighter_keyword_escaping_and_boundaries(qapp):
    from PySide6.QtGui import QTextDocument
    from core.highlighter import UniversalHighlighter
    from pathlib import Path

    ruby_json = Path(__file__).resolve().parent.parent / "plugins" / "ruby_plugin.json"
    assert ruby_json.exists()
    provider = DeclarativeLanguageProvider.from_json_file(ruby_json)

    doc = QTextDocument()
    hl = UniversalHighlighter(doc, provider)
    doc.setPlainText("if defined? x\n  define = 1\nend")

    # Prüfe Zeile 2: '  define = 1'
    # 'define' darf NICHT als Keyword 'defined?' gematcht werden
    block2 = doc.findBlockByLineNumber(1)
    for r, fmt in hl.highlighting_rules:
        it = r.globalMatch(block2.text())
        while it.hasNext():
            m = it.next()
            assert m.captured() != "define", "Variable 'define' must not match 'defined?'"

    # Prüfe Zeile 1: 'if defined? x' -> 'defined?' muss vollständig matchen
    block1 = doc.findBlockByLineNumber(0)
    matched_keywords = []
    for r, fmt in hl.highlighting_rules:
        it = r.globalMatch(block1.text())
        while it.hasNext():
            m = it.next()
            matched_keywords.append(m.captured())
    assert "defined?" in matched_keywords
    assert "if" in matched_keywords


def test_declarative_comment_style_variations():
    # String format
    p1 = DeclarativeLanguageProvider.from_dict({"name": "Lang1", "extensions": ["l1"], "comment_style": "#"})
    assert p1.get_comment_style() == ("#", None)

    # 1-Element list
    p2 = DeclarativeLanguageProvider.from_dict({"name": "Lang2", "extensions": ["l2"], "comment_style": ["--"]})
    assert p2.get_comment_style() == ("--", None)

    # Flat 3-element list
    p3 = DeclarativeLanguageProvider.from_dict({
        "name": "Lang3", "extensions": ["l3"], "comment_style": ["--", "--[[", "--]]"]
    })
    assert p3.get_comment_style() == ("--", ("--[[", "--]]"))

    # Dict format without multi
    p4 = DeclarativeLanguageProvider.from_dict({
        "name": "Lang4", "extensions": ["l4"], "comment_style": {"single": ";"}
    })
    assert p4.get_comment_style() == (";", None)


def test_safe_provider_lookups():
    assert get_provider_for_extension(None) is None
    assert get_provider_for_extension("") is None
    assert get_provider_for_extension("   ") is None
    assert get_provider_by_name(None) is None
    assert get_provider_by_name("") is None
    assert is_provider_registered(None) is False
    assert is_provider_registered("") is False


def test_plugin_manager_cleanup_on_vanished_file(tmp_path):
    mgr = PluginManager(plugin_dirs=[tmp_path])
    json_plugin = tmp_path / "temp_plugin.json"
    json_plugin.write_text(json.dumps({
        "name": "TempLang",
        "extensions": ["tmpl"],
        "keywords": ["test"],
    }), encoding="utf-8")

    loaded = mgr.discover_and_load_all()
    assert len(loaded) == 1
    assert is_provider_registered("TempLang")

    # Datei löschen und erneut scannen
    json_plugin.unlink()
    loaded_after = mgr.discover_and_load_all()
    assert len(loaded_after) == 0
    assert not is_provider_registered("TempLang")

