#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für LSP Definitionen- und Referenzen-Navigation (F12 und Shift+F12)
inklusive Heuristik-Fallback, URI-Parsing und UI-Panel.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.editor import CodeEditor
from core.symbol_search import (
    find_definition_fallback,
    find_references_fallback,
    get_definition_patterns,
)
from features.lsp_client import (
    LSPClient,
    lsp_uri_to_path,
    parse_lsp_locations,
)
from ui.references_panel import ReferencesPanel

# Sicherstellen, dass QApplication für Widget-Tests initialisiert ist
app = QApplication.instance() or QApplication(sys.argv)


class LSPUriParsingTests(unittest.TestCase):
    def test_windows_uri_to_path(self):
        uri = "file:///C:/Users/test/project/main.py"
        path = lsp_uri_to_path(uri)
        self.assertIsNotNone(path)
        self.assertEqual(str(path).replace("\\", "/").lower(), "c:/users/test/project/main.py")

    def test_uri_with_spaces_and_special_chars(self):
        uri = "file:///C:/My%20Projects/app%20v1/test.py"
        path = lsp_uri_to_path(uri)
        self.assertIsNotNone(path)
        self.assertEqual(str(path).replace("\\", "/").lower(), "c:/my projects/app v1/test.py")

    def test_invalid_scheme_returns_none(self):
        self.assertIsNone(lsp_uri_to_path("http://example.com/file.py"))
        self.assertIsNone(lsp_uri_to_path(""))
        self.assertIsNone(lsp_uri_to_path(None))


class LSPLocationParsingTests(unittest.TestCase):
    def test_parse_single_location(self):
        raw = {
            "uri": "file:///C:/project/test.py",
            "range": {
                "start": {"line": 9, "character": 4},
                "end": {"line": 9, "character": 12},
            },
        }
        locs = parse_lsp_locations(raw)
        self.assertEqual(len(locs), 1)
        self.assertEqual(locs[0]["line"], 10)  # 1-based
        self.assertEqual(locs[0]["col"], 5)   # 1-based
        self.assertEqual(locs[0]["end_line"], 10)
        self.assertEqual(locs[0]["end_col"], 13)

    def test_parse_location_list(self):
        raw = [
            {
                "uri": "file:///C:/project/a.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
            },
            {
                "uri": "file:///C:/project/b.py",
                "range": {"start": {"line": 15, "character": 8}, "end": {"line": 15, "character": 12}},
            },
        ]
        locs = parse_lsp_locations(raw)
        self.assertEqual(len(locs), 2)
        self.assertEqual(locs[0]["line"], 1)
        self.assertEqual(locs[1]["line"], 16)
        self.assertEqual(locs[1]["col"], 9)

    def test_parse_location_link(self):
        raw = [
            {
                "targetUri": "file:///C:/project/target.py",
                "targetRange": {
                    "start": {"line": 20, "character": 0},
                    "end": {"line": 25, "character": 0},
                },
                "targetSelectionRange": {
                    "start": {"line": 20, "character": 4},
                    "end": {"line": 20, "character": 14},
                },
            }
        ]
        locs = parse_lsp_locations(raw)
        self.assertEqual(len(locs), 1)
        self.assertEqual(locs[0]["line"], 21)
        self.assertEqual(locs[0]["col"], 5)

    def test_parse_empty_or_none(self):
        self.assertEqual(parse_lsp_locations(None), [])
        self.assertEqual(parse_lsp_locations([]), [])
        self.assertEqual(parse_lsp_locations({}), [])


class LSPClientRequestsTests(unittest.TestCase):
    def test_request_definition_formatting(self):
        client = LSPClient("Python")
        client._write = MagicMock()
        mock_cb = MagicMock()

        client.request_definition("file:///C:/main.py", line=10, character=5, callback=mock_cb)

        self.assertEqual(client._write.call_count, 1)
        msg = client._write.call_args[0][0]
        self.assertEqual(msg.get("method"), "textDocument/definition")
        self.assertEqual(msg.get("params"), {
            "textDocument": {"uri": "file:///C:/main.py"},
            "position": {"line": 10, "character": 5},
        })
        req_id = msg.get("id")
        self.assertIn(req_id, client._pending)
        self.assertEqual(client._pending[req_id], mock_cb)

    def test_request_references_formatting(self):
        client = LSPClient("Python")
        client._write = MagicMock()
        mock_cb = MagicMock()

        client.request_references("file:///C:/main.py", line=20, character=8, callback=mock_cb)

        self.assertEqual(client._write.call_count, 1)
        msg = client._write.call_args[0][0]
        self.assertEqual(msg.get("method"), "textDocument/references")
        self.assertEqual(msg.get("params"), {
            "textDocument": {"uri": "file:///C:/main.py"},
            "position": {"line": 20, "character": 8},
            "context": {"includeDeclaration": True},
        })


class SymbolSearchFallbackTests(unittest.TestCase):
    def test_find_definition_python_functions_and_classes(self):
        code = """import os

def helper():
    pass

class MyService:
    def process_data(self):
        helper()

async def fetch_async():
    pass
"""
        patterns = get_definition_patterns("helper")
        self.assertTrue(len(patterns) > 0)

        defs = find_definition_fallback("helper", current_path=Path("app.py"), current_text=code)
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]["line"], 3)
        self.assertEqual(defs[0]["preview"], "def helper():")

        class_defs = find_definition_fallback("MyService", current_path=Path("app.py"), current_text=code)
        self.assertEqual(len(class_defs), 1)
        self.assertEqual(class_defs[0]["line"], 6)

        async_defs = find_definition_fallback("fetch_async", current_path=Path("app.py"), current_text=code)
        self.assertEqual(len(async_defs), 1)
        self.assertEqual(async_defs[0]["line"], 10)

    def test_find_references_word_boundaries(self):
        code = """def calc(foo):
    foo_bar = 10
    total = foo + 5
    print(foo)
    return total
"""
        refs = find_references_fallback("foo", current_path=Path("calc.py"), current_text=code)
        # Should match `foo` in `calc(foo)`, `total = foo + 5`, `print(foo)`
        # Must NOT match `foo_bar`!
        self.assertEqual(len(refs), 3)
        lines = [r["line"] for r in refs]
        self.assertEqual(lines, [1, 3, 4])


class ReferencesPanelUITests(unittest.TestCase):
    def test_references_panel_population_and_activation(self):
        panel = ReferencesPanel()
        test_refs = [
            {
                "path": Path("C:/project/main.py"),
                "line": 15,
                "col": 4,
                "length": 6,
                "preview": "worker.run()",
            },
            {
                "path": Path("C:/project/worker.py"),
                "line": 42,
                "col": 8,
                "length": 6,
                "preview": "def run(self):",
            },
        ]
        panel.set_references("run", test_refs)
        self.assertEqual(panel.reference_count, 2)
        self.assertIn("2 Treffer in 2 Dateien", panel.title_label.text())

        activated = []
        panel.referenceActivated.connect(activated.append)

        # Child-Item aktivieren
        parent_item = panel.tree.topLevelItem(0)
        child_item = parent_item.child(0)
        panel._on_item_double_clicked(child_item, 0)

        self.assertEqual(len(activated), 1)
        self.assertEqual(activated[0]["line"], 15)

        # Tastatur-Enter auf Child-Item
        panel.tree.setCurrentItem(child_item)
        enter_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        panel.tree.keyPressEvent(enter_event)
        self.assertEqual(len(activated), 2)

        panel.clear_references()
        self.assertEqual(panel.reference_count, 0)
        self.assertEqual(panel.title_label.text(), "Keine Referenzen geladen")


class CodeEditorDefinitionSignalTests(unittest.TestCase):
    def test_get_symbol_at_cursor_and_request_signals(self):
        editor = CodeEditor()
        editor.setPlainText("alpha = calculate_result(beta)\ngamma = 42\n")

        # Cursor auf "calculate_result" setzen
        cursor = editor.textCursor()
        cursor.setPosition(12)  # In calculate_result
        editor.setTextCursor(cursor)

        symbol = editor.get_symbol_at_cursor()
        self.assertEqual(symbol, "calculate_result")

        def_emitted = []
        ref_emitted = []
        editor.definitionRequested.connect(lambda line, col, sym: def_emitted.append((line, col, sym)))
        editor.referencesRequested.connect(lambda line, col, sym: ref_emitted.append((line, col, sym)))

        editor.request_goto_definition()
        self.assertEqual(len(def_emitted), 1)
        self.assertEqual(def_emitted[0][2], "calculate_result")

        editor.request_find_references()
        self.assertEqual(len(ref_emitted), 1)
        self.assertEqual(ref_emitted[0][2], "calculate_result")


class MainWindowLSPIntegrationTests(unittest.TestCase):
    def setUp(self):
        from ui.main_window import MainWindow
        self.window = MainWindow()
        self.window.show()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_mainwindow_actions_and_bottom_tab(self):
        self.assertEqual(self.window.act_goto_def.shortcut().toString(), "F12")
        self.assertEqual(self.window.act_find_refs.shortcut().toString(), "Shift+F12")
        self.assertEqual(self.window.bottom_tabs.tabText(3), "Referenzen")
        self.assertIs(self.window.bottom_tabs.widget(3), self.window.references)

    def test_goto_definition_fallback_in_tab(self):
        tab = self.window.new_file()
        tab.editor.setPlainText("def my_func():\n    pass\n\nmy_func()\n")
        cursor = tab.editor.textCursor()
        cursor.setPosition(25)  # Auf my_func() Aufruf
        tab.editor.setTextCursor(cursor)

        # goto_definition ausführen
        self.window.goto_definition()

        # Cursor sollte in Zeile 1 (0-basiert blockNumber 0) stehen
        self.assertEqual(tab.editor.textCursor().blockNumber(), 0)

    def test_find_references_fallback_populates_panel(self):
        tab = self.window.new_file()
        tab.editor.setPlainText("def process():\n    process()\n    return process\n")
        cursor = tab.editor.textCursor()
        cursor.setPosition(5)  # Auf 'process'
        tab.editor.setTextCursor(cursor)

        self.window.find_references()

        self.assertFalse(self.window.bottom_tabs.isHidden())
        self.assertIs(self.window.bottom_tabs.currentWidget(), self.window.references)
        self.assertEqual(self.window.references.reference_count, 3)


if __name__ == "__main__":
    unittest.main()

