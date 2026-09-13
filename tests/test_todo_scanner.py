#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für den integrierten Aufgaben-/TODO-Scanner und das TodoPanel in CodeBox."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.todo_scanner import (
    TodoItem,
    TodoScannerManager,
    scan_file_for_todos,
    TODO_PATTERN,
)
from ui.todo_panel import TodoPanel
from ui.main_window import MainWindow


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_todo_pattern_regex():
    """Testet die reguläre Ausdruckserkennung für diverse Kommentarstile."""
    cases = [
        ("# TODO: Normaler Python-Kommentar", "TODO", None, "Normaler Python-Kommentar"),
        ("// FIXME(lukas): C-Style mit Autor", "FIXME", "lukas", "C-Style mit Autor"),
        ("/* BUG: Block-Kommentar */", "BUG", None, "Block-Kommentar */"),
        ("<!-- NOTE: HTML Kommentar -->", "NOTE", None, "HTML Kommentar -->"),
        ("-- HACK: SQL-Kommentar", "HACK", None, "SQL-Kommentar"),
        ("- [ ] TODO: Markdown Checkliste", "TODO", None, "Markdown Checkliste"),
        ("TODO: Zeilenanfang ohne Kommentarzeichen", "TODO", None, "Zeilenanfang ohne Kommentarzeichen"),
    ]

    for line, expected_tag, expected_author, expected_text in cases:
        m = TODO_PATTERN.search(line)
        assert m is not None, f"Muster nicht gefunden für: {line}"
        if m.group(1):
            tag = m.group(1).upper()
            author = m.group(2).strip() if m.group(2) else None
            text = m.group(3) or ""
        else:
            tag = m.group(4).upper()
            author = m.group(5).strip() if m.group(5) else None
            text = m.group(6) or ""
        assert tag == expected_tag
        assert author == expected_author
        assert text.strip() == expected_text

    # Negative Fälle: Normale Variablen dürfen nicht matchen
    negatives = [
        "todo_count = 5",
        "def get_todos():",
        "class TodoModel:",
        "int fixme = 0;",
    ]
    for line in negatives:
        m = TODO_PATTERN.search(line)
        assert m is None, f"Falsch-positiver Treffer für: {line}"


def test_scan_file_for_todos(tmp_path):
    """Testet das Durchsuchen einer konkreten Datei nach Aufgaben."""
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        "# Header line\n"
        "# TODO: Erste Aufgabe\n"
        "x = 42\n"
        "// FIXME(anna): Speicherleck beheben\n"
        "/* BUG: Fehler im Parser */\n"
        "print(x)\n",
        encoding="utf-8",
    )

    items = scan_file_for_todos(test_file, rel_path="sample.py", folder_name="src")
    assert len(items) == 3

    assert items[0].tag == "TODO"
    assert items[0].text == "Erste Aufgabe"
    assert items[0].line_number == 2
    assert items[0].author is None

    assert items[1].tag == "FIXME"
    assert items[1].text == "Speicherleck beheben"
    assert items[1].line_number == 4
    assert items[1].author == "anna"

    assert items[2].tag == "BUG"
    assert items[2].text == "Fehler im Parser"
    assert items[2].line_number == 5


def test_scan_file_binary_and_size_limits(tmp_path):
    """Prüft, dass Binärdateien und übergroße Dateien übersprungen werden."""
    bin_file = tmp_path / "binary.dat"
    bin_file.write_bytes(b"\x00\x01\x02# TODO: In binary file\x00")
    assert scan_file_for_todos(bin_file) == []

    large_file = tmp_path / "large.txt"
    large_file.write_text("# TODO: Test\n" * 10, encoding="utf-8")
    assert scan_file_for_todos(large_file, max_file_size_kb=0) == []


def test_todo_scanner_manager(tmp_path):
    """Testet den ScannerManager bezüglich Caching, Rescan und Gruppierung."""
    _ensure_app()
    manager = TodoScannerManager()
    manager.set_folders([tmp_path])

    f1 = tmp_path / "mod1.py"
    f1.write_text("# TODO: Refactor mod1\n# NOTE: Alles okay\n", encoding="utf-8")

    f2 = tmp_path / "mod2.py"
    f2.write_text("// FIXME: Bug in mod2\n", encoding="utf-8")

    # Einzelne Dateien synchron neu scannen
    items1 = manager.rescan_file(f1)
    assert len(items1) == 2
    items2 = manager.rescan_file(f2)
    assert len(items2) == 1

    assert manager.get_counts() == (3, 2)
    all_items = manager.get_all_todos()
    assert len(all_items) == 3

    by_file = manager.get_todos_by_file()
    assert len(by_file) == 2
    assert len(by_file[f1]) == 2
    assert len(by_file[f2]) == 1

    by_tag = manager.get_todos_by_tag()
    assert "TODO" in by_tag
    assert "NOTE" in by_tag
    assert "FIXME" in by_tag

    # Datei entfernen
    manager.remove_file(f2)
    assert manager.get_counts() == (2, 1)

    manager.clear()
    assert manager.get_counts() == (0, 0)


def test_todo_panel_ui(tmp_path):
    """Testet Filterung, Gruppierung und Tastaturinteraktion im TodoPanel."""
    _ensure_app()
    panel = TodoPanel()

    item1 = TodoItem(
        file_path=tmp_path / "a.py",
        rel_path="a.py",
        folder_name="app",
        line_number=10,
        column=3,
        tag="TODO",
        author="dev1",
        text="Feature einbauen",
        line_text="# TODO: Feature einbauen",
    )
    item2 = TodoItem(
        file_path=tmp_path / "b.py",
        rel_path="b.py",
        folder_name="app",
        line_number=25,
        column=1,
        tag="FIXME",
        author=None,
        text="Absturz bei Null",
        line_text="// FIXME: Absturz bei Null",
    )

    panel.set_todos([item1, item2])
    assert panel.tree.topLevelItemCount() == 2  # 2 Dateien
    assert "Aufgaben (2)" in panel.title_label.text()

    # Filter nach Text
    panel.search_edit.setText("Null")
    assert panel.tree.topLevelItemCount() == 1
    assert "b.py" in panel.tree.topLevelItem(0).text(0)

    # Filter zurücksetzen
    panel.search_edit.setText("")
    assert panel.tree.topLevelItemCount() == 2

    # Filter nach Tag
    idx = panel.tag_combo.findData("TODO")
    panel.tag_combo.setCurrentIndex(idx)
    assert panel.tree.topLevelItemCount() == 1
    assert "a.py" in panel.tree.topLevelItem(0).text(0)

    # Gruppierung nach Tag
    panel.tag_combo.setCurrentIndex(0)  # Alle Tags
    idx_group = panel.group_combo.findData("tag")
    panel.group_combo.setCurrentIndex(idx_group)
    assert panel.tree.topLevelItemCount() == 2  # FIX, TODO
    top_tags = [panel.tree.topLevelItem(i).text(0) for i in range(2)]
    assert any("TODO" in t for t in top_tags)
    assert any("FIXME" in t for t in top_tags)

    # Tastatur-Aktivierung (Return)
    activated = []
    panel.todoActivated.connect(lambda it: activated.append(it))

    # Erstes Kind-Element auswählen
    parent_item = panel.tree.topLevelItem(0)
    assert parent_item.childCount() > 0
    child = parent_item.child(0)
    panel.tree.setCurrentItem(child)

    event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    panel.tree.keyPressEvent(event)
    assert len(activated) == 1
    assert isinstance(activated[0], TodoItem)


def test_main_window_todo_integration(tmp_path):
    """Testet die Integration von TodoPanel in MainWindow (Tastenkürzel, Sprung, Rescan)."""
    _ensure_app()
    win = MainWindow()

    test_file = tmp_path / "hello.py"
    test_file.write_text(
        "# Begrüßung\n"
        "# TODO: Mehrsprachigkeit unterstützen\n"
        "print('Hallo Welt')\n",
        encoding="utf-8",
    )

    # Projekt öffnen
    win.open_folder(tmp_path)

    # Prüfen, ob TodoPanel und Sidebar existieren
    assert hasattr(win, "sidebar_tabs")
    assert hasattr(win, "todo_panel")
    assert hasattr(win, "todo_scanner")
    assert win.sidebar_tabs.count() >= 2
    assert win.sidebar_tabs.widget(0) == win.project_view
    assert win.sidebar_tabs.widget(1) == win.todo_panel

    # Umschalten per Methode / Shortcut
    win.show()
    win.show_todo_panel()
    assert not win.sidebar_tabs.isHidden()
    assert win.sidebar_tabs.currentWidget() == win.todo_panel

    # Rescan synchron testen
    win.todo_scanner.rescan_file(test_file)
    todos = win.todo_scanner.get_all_todos()
    assert len(todos) == 1
    assert todos[0].text == "Mehrsprachigkeit unterstützen"

    # Sprung zur Fundstelle über _on_todo_activated
    win._on_todo_activated(todos[0])
    tab = win.get_active_tab()
    assert tab is not None
    assert tab.file_path == test_file
    cursor = tab.editor.textCursor()
    assert cursor.blockNumber() == 1  # 2. Zeile (0-basiert: 1)

    # Umschalten des Projektbaums stellt Fokus wieder her
    win._toggle_project_view()
    assert win.sidebar_tabs.currentWidget() == win.project_view

    win.close()
