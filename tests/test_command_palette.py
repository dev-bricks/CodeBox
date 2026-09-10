"""Automatisierte Tests für die Befehlspalette und Quick-Open Datei-Finder."""

from __future__ import annotations

import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.command_palette import CommandPaletteDialog


@pytest.fixture(scope="module")
def qapp():
    instance = QApplication.instance()
    if not instance:
        instance = QApplication([])
    return instance


@pytest.fixture
def main_window(qapp):
    win = MainWindow()
    yield win
    win.close()


def test_palette_init_files_mode(main_window):
    dlg = CommandPaletteDialog(main_window, mode="files")
    assert dlg.current_mode == "files"
    assert not dlg.search_input.text().startswith(">")
    assert dlg.results_list.count() > 0
    assert len(dlg._all_files) > 0


def test_palette_init_commands_mode(main_window):
    dlg = CommandPaletteDialog(main_window, mode="commands")
    assert dlg.current_mode == "commands"
    assert dlg.search_input.text().startswith(">")
    assert len(dlg._all_commands) > 0
    # Überprüfe, dass Standard-Befehle vorhanden sind
    titles = [cmd[1] for cmd in dlg._all_commands]
    assert any("Öffnen" in t for t in titles)
    assert any("Speichern" in t for t in titles)
    assert any("Suchen" in t for t in titles)


def test_palette_filter_files(main_window):
    dlg = CommandPaletteDialog(main_window, mode="files")
    initial_count = dlg.results_list.count()
    dlg.search_input.setText("main_window.py")
    assert dlg.results_list.count() >= 1
    assert dlg.results_list.count() <= initial_count

    # Erster Treffer muss main_window.py sein
    first_item = dlg.results_list.item(0)
    data = first_item.data(Qt.ItemDataRole.UserRole)
    assert data[0] == "file"
    assert data[1].name == "main_window.py"


def test_palette_filter_commands(main_window):
    dlg = CommandPaletteDialog(main_window, mode="commands")
    dlg.search_input.setText(">Suchen")
    assert dlg.results_list.count() >= 1
    first_item = dlg.results_list.item(0)
    data = first_item.data(Qt.ItemDataRole.UserRole)
    assert data[0] == "command"


def test_palette_mode_switch_on_prefix(main_window):
    dlg = CommandPaletteDialog(main_window, mode="files")
    assert dlg.current_mode == "files"

    # Tippe '>' -> Modus wechselt automatisch zu commands
    dlg.search_input.setText(">Terminal")
    assert dlg.current_mode == "commands"

    # Lösche Suchtext -> Modus wechselt zurück zu files
    dlg.search_input.setText("")
    assert dlg.current_mode == "files"


def test_palette_key_navigation(main_window):
    dlg = CommandPaletteDialog(main_window, mode="files")
    if dlg.results_list.count() > 1:
        dlg.results_list.setCurrentRow(0)
        assert dlg.results_list.currentRow() == 0

        # Down-Taste simulieren
        down_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        dlg.keyPressEvent(down_event)
        assert dlg.results_list.currentRow() == 1

        # Up-Taste simulieren
        up_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        dlg.keyPressEvent(up_event)
        assert dlg.results_list.currentRow() == 0


def test_palette_file_activation(main_window, tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    dlg = CommandPaletteDialog(main_window, mode="files")
    # Manuell einfügen für reproduzierbaren Aktivierungstest
    dlg._all_files = [("test_sample.py", test_file)]
    dlg._update_results()

    item = dlg.results_list.item(0)
    dlg._on_item_activated(item)

    # Prüfen, ob MainWindow den Pfad geöffnet hat
    active_tab = main_window.get_active_tab()
    assert active_tab is not None
    assert active_tab.file_path.resolve() == test_file.resolve()


def test_palette_command_activation(main_window):
    dlg = CommandPaletteDialog(main_window, mode="commands")
    executed = []
    dlg._all_commands = [("Test", "Custom Action", "Ctrl+T", lambda: executed.append(True))]
    dlg._update_results()

    item = dlg.results_list.item(0)
    dlg._on_item_activated(item)
    assert executed == [True]


def test_palette_escape_key(main_window):
    dlg = CommandPaletteDialog(main_window, mode="files")
    esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    dlg.keyPressEvent(esc_event)
    assert dlg.result() == CommandPaletteDialog.DialogCode.Rejected
