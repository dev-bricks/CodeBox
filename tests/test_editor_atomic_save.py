"""Verify target preservation and document state at the real Qt save boundary."""
import os

import pytest
from PySide6.QtCore import QSaveFile
from PySide6.QtWidgets import QApplication, QMessageBox

import core.tabs as tabs


@pytest.fixture
def document(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    target = tmp_path / 'Grüße.py'
    target.write_bytes(b'original code\r\n')
    tab = tabs.EditorTab(target)
    tab.editor.setPlainText("print('Grüße')\n")
    tab.editor.document().setModified(True)
    errors = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: errors.append(args))
    yield tab, target, errors, app
    tab.editor.close()


@pytest.mark.parametrize('failure', ['open', 'short', 'exception', 'commit'])
def test_save_failure_preserves_existing_code_and_dirty_state(document, monkeypatch, failure):
    tab, target, errors, _ = document
    original_files = set(target.parent.iterdir())

    class BrokenSaveFile(QSaveFile):
        def open(self, mode):
            assert not self.directWriteFallback()
            return False if failure == 'open' else super().open(mode)

        def write(self, payload):
            assert target.read_bytes() == b'original code\r\n'
            if failure in ('short', 'exception'):
                written = super().write(payload[:5])
                if failure == 'exception':
                    raise OSError('disk full after partial write')
                return written
            return super().write(payload)

        def commit(self):
            if failure == 'commit':
                self.cancelWriting()
            return super().commit()

    monkeypatch.setattr(tabs, 'QSaveFile', BrokenSaveFile)
    assert tab.save() is False
    assert target.read_bytes() == b'original code\r\n'
    assert tab.is_modified and tab.editor.document().isModified()
    assert len(errors) == 1
    assert set(target.parent.iterdir()) == original_files


def test_invalid_utf8_does_not_open_output(document, monkeypatch):
    tab, target, errors, _ = document
    monkeypatch.setattr(tab.editor, 'toPlainText', lambda: 'bad\ud800text')
    monkeypatch.setattr(tabs, 'QSaveFile', lambda *_: pytest.fail('output opened before encoding'))
    assert tab.save() is False
    assert target.read_bytes() == b'original code\r\n'
    assert tab.is_modified and tab.editor.document().isModified()
    assert len(errors) == 1


@pytest.mark.parametrize('text', ['', 'Grüße\nzweite Zeile\n'])
def test_success_preserves_native_newlines_and_cleans_shared_document(document, text):
    tab, target, errors, _ = document
    clone = tabs.EditorTab.create_clone(tab)
    try:
        tab.editor.setPlainText(text)
        tab.editor.document().setModified(True)
        assert tab.save() is True
        assert target.read_bytes() == text.replace('\n', os.linesep).encode('utf-8')
        assert clone.editor.toPlainText() == text
        assert not tab.is_modified and not clone.is_modified
        assert not tab.editor.document().isModified()
        assert not errors
    finally:
        clone.editor.close()
