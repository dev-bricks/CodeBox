from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.tabs import TabWidget


def _ensure_app():
    return QApplication.instance() or QApplication([])


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
