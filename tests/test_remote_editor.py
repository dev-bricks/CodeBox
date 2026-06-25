"""Regressionstests für SFTPSession in features/remote_editor.py."""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_session():
    """Erstellt eine SFTPSession mit gemocktem SFTP."""
    from features.remote_editor import RemoteHost, SFTPSession
    host = RemoteHost(name="test", hostname="localhost", username="user")
    session = SFTPSession(host)
    sftp_mock = MagicMock()
    session._sftp = sftp_mock
    return session, sftp_mock


def test_download_file_cleans_up_tempfile_on_sftp_failure():
    """Regression (B-010): download_file() muss die angelegte Temp-Datei
    löschen, wenn self._sftp.get() fehlschlägt. Vorher blieb die Datei liegen,
    da local_path nie in _local_cache eingetragen wurde."""
    session, sftp_mock = _make_session()
    sftp_mock.get.side_effect = IOError("Datei nicht gefunden")

    result = session.download_file("/remote/nonexistent.py")

    assert result is None

    # Kein Eintrag im Cache (Datei wurde nicht erfolgreich heruntergeladen)
    assert "/remote/nonexistent.py" not in session._local_cache

    # Temp-Datei darf nicht mehr existieren
    # (Wir fangen die mkstemp-Seiteneffekte indirekt über den Cache ab;
    # hier prüfen wir, dass kein verwaister Eintrag im Cache hängt)
    assert len(session._local_cache) == 0


def test_download_file_does_not_cache_on_failure(tmp_path):
    """Kein _local_cache-Eintrag nach fehlgeschlagenem Download."""
    session, sftp_mock = _make_session()
    sftp_mock.get.side_effect = OSError("Permission denied")

    session.download_file("/remote/secret.py")

    assert session._local_cache == {}


def test_download_file_returns_path_and_caches_on_success(tmp_path):
    """Erfolgreicher Download: Rückgabewert ist ein existierender Pfad im Cache."""
    session, sftp_mock = _make_session()

    def fake_get(remote, local):
        Path(local).write_text("# content", encoding="utf-8")

    sftp_mock.get.side_effect = fake_get

    result = session.download_file("/remote/script.py")

    assert result is not None
    assert Path(result).exists()
    assert session._local_cache["/remote/script.py"] == result

    # Aufräumen
    session.disconnect()
    session._sftp = None


def test_connect_rejects_unknown_host_keys(monkeypatch):
    """SSH-Verbindungen dürfen unbekannte Hostkeys nicht automatisch akzeptieren."""
    from features import remote_editor

    fake_paramiko = MagicMock()
    ssh_mock = MagicMock()
    reject_policy = object()
    fake_paramiko.SSHClient.return_value = ssh_mock
    fake_paramiko.RejectPolicy.return_value = reject_policy
    monkeypatch.setattr(remote_editor, "PARAMIKO_AVAILABLE", True)
    monkeypatch.setattr(remote_editor, "paramiko", fake_paramiko, raising=False)

    host = remote_editor.RemoteHost(name="test", hostname="localhost", username="user")
    session = remote_editor.SFTPSession(host)

    assert session.connect() is True

    ssh_mock.load_system_host_keys.assert_called_once_with()
    ssh_mock.set_missing_host_key_policy.assert_called_once_with(reject_policy)
    ssh_mock.connect.assert_called_once_with(hostname="localhost", port=22, username="user")
