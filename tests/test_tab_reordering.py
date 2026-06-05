from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.tabs import TabWidget


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_close_tab_emits_current_file_changed_with_correct_tab():
    """Regression (B-009): close_tab() muss currentFileChanged mit dem neu
    aktiven Tab emittieren, nicht mit dem gerade geschlossenen.
    Vor dem Fix: removeTab() löst currentChanged mit veralteter Tab-Map aus,
    sodass das Signal den falschen (entfernten) Tab enthält."""
    _ensure_app()
    widget = TabWidget()

    first = widget.new_tab()
    first.file_path = Path("first.py")
    second = widget.new_tab()
    second.file_path = Path("second.py")

    emitted_paths = []
    widget.currentFileChanged.connect(lambda p: emitted_paths.append(p))

    widget.close_tab(0)

    assert widget.count() == 1
    # Das letzte Signal muss second.file_path sein, nicht first.file_path
    assert emitted_paths, "currentFileChanged wurde nie emittiert"
    assert emitted_paths[-1] == Path("second.py"), (
        f"Falscher Pfad emittiert: {emitted_paths[-1]!r}"
    )

    widget.close()


def test_close_last_tab_emits_none():
    """Regression (B-009): Wird der letzte Tab geschlossen, muss
    currentFileChanged(None) emittiert werden, damit die UI zurückgesetzt wird."""
    _ensure_app()
    widget = TabWidget()
    widget.new_tab()

    emitted_paths = []
    widget.currentFileChanged.connect(lambda p: emitted_paths.append(p))

    widget.close_tab(0)

    assert widget.count() == 0
    assert None in emitted_paths, (
        f"currentFileChanged(None) wurde nie emittiert; bekommen: {emitted_paths}"
    )


def test_new_tab_title_shows_asterisk_when_modified():
    """Regression (B-005): new_tab() muss _update_tab_title verbinden, damit
    der Tab-Titel '*Unbenannt' zeigt, sobald Inhalt geändert wurde."""
    _ensure_app()
    widget = TabWidget()
    tab = widget.new_tab()

    # Modifikationsstatus direkt setzen → modificationChanged feuert
    tab.editor.document().setModified(True)

    idx = widget.currentIndex()
    title = widget.tabText(idx)
    assert title.startswith("*"), (
        f"Erwartet '*Unbenannt', bekommen: {title!r}"
    )
    widget.close()


def test_current_tab_tracks_tab_reordering():
    _ensure_app()
    widget = TabWidget()

    first = widget.new_tab()
    first.file_path = Path("first.py")
    second = widget.new_tab()
    second.file_path = Path("second.py")

    widget.tabBar().moveTab(0, 1)

    current_widget = widget.widget(widget.currentIndex())
    expected = next(tab for tab in widget.tabs.values() if tab.editor is current_widget)

    assert widget.current_tab() is expected
    assert widget.tabs[widget.currentIndex()] is expected

    widget.close()
