"""Remote Editing via SSH/SFTP for CodeBox.

Supports opening, editing, and saving files on remote servers.
Uses paramiko for SSH/SFTP operations.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("CodeBox.Remote")

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


@dataclass
class RemoteHost:
    """SSH connection configuration."""
    name: str
    hostname: str
    port: int = 22
    username: str = ""
    key_file: str = ""  # Path to SSH private key (empty = password auth)
    password: str = ""  # Only used if key_file is empty


class SFTPSession:
    """Manages an SFTP session for remote file operations."""

    def __init__(self, host: RemoteHost):
        self.host = host
        self._ssh: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._local_cache: dict[str, str] = {}  # remote_path -> local_temp_path

    def connect(self) -> bool:
        """Establishes SSH connection and opens SFTP channel.

        Returns:
            True on success, False on failure.
        """
        if not PARAMIKO_AVAILABLE:
            logger.error("paramiko nicht installiert. Installation: pip install paramiko")
            return False

        try:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": self.host.hostname,
                "port": self.host.port,
                "username": self.host.username,
            }

            if self.host.key_file and os.path.exists(self.host.key_file):
                connect_kwargs["key_filename"] = self.host.key_file
            elif self.host.password:
                connect_kwargs["password"] = self.host.password

            self._ssh.connect(**connect_kwargs)
            self._sftp = self._ssh.open_sftp()
            logger.info("SFTP verbunden: %s@%s:%d", self.host.username, self.host.hostname, self.host.port)
            return True
        except Exception as e:
            logger.error("SSH-Verbindung fehlgeschlagen: %s", e)
            self._ssh = None
            self._sftp = None
            return False

    def disconnect(self):
        """Closes SFTP and SSH connections, cleans up temp files."""
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._ssh:
            self._ssh.close()
            self._ssh = None

        # Temp-Dateien aufräumen
        for local_path in self._local_cache.values():
            try:
                os.unlink(local_path)
            except OSError:
                pass
        self._local_cache.clear()
        logger.info("SFTP getrennt: %s", self.host.name)

    @property
    def is_connected(self) -> bool:
        return self._sftp is not None

    def list_dir(self, remote_path: str) -> List[str]:
        """Lists files in a remote directory."""
        if not self._sftp:
            return []
        try:
            return self._sftp.listdir(remote_path)
        except IOError as e:
            logger.error("Verzeichnis nicht lesbar: %s (%s)", remote_path, e)
            return []

    def download_file(self, remote_path: str) -> Optional[str]:
        """Downloads a remote file to a temporary local path.

        Args:
            remote_path: Absolute path on the remote server.

        Returns:
            Local temporary file path, or None on failure.
        """
        if not self._sftp:
            return None

        try:
            # Temp-Datei mit passendem Suffix erstellen
            suffix = Path(remote_path).suffix or ".txt"
            fd, local_path = tempfile.mkstemp(suffix=suffix, prefix="codebox_remote_")
            os.close(fd)

            self._sftp.get(remote_path, local_path)
            self._local_cache[remote_path] = local_path
            logger.info("Heruntergeladen: %s -> %s", remote_path, local_path)
            return local_path
        except Exception as e:
            logger.error("Download fehlgeschlagen: %s (%s)", remote_path, e)
            return None

    def upload_file(self, remote_path: str, local_path: str = None) -> bool:
        """Uploads a local file to the remote server.

        Args:
            remote_path: Target path on the remote server.
            local_path: Local source path. If None, uses cached path.

        Returns:
            True on success.
        """
        if not self._sftp:
            return False

        if local_path is None:
            local_path = self._local_cache.get(remote_path)
            if not local_path:
                logger.error("Keine lokale Datei für %s", remote_path)
                return False

        try:
            self._sftp.put(local_path, remote_path)
            logger.info("Hochgeladen: %s -> %s", local_path, remote_path)
            return True
        except Exception as e:
            logger.error("Upload fehlgeschlagen: %s (%s)", remote_path, e)
            return False

    def stat(self, remote_path: str) -> Optional[dict]:
        """Returns file info (size, mtime) for a remote path."""
        if not self._sftp:
            return None
        try:
            attrs = self._sftp.stat(remote_path)
            return {
                "size": attrs.st_size,
                "mtime": attrs.st_mtime,
                "mode": attrs.st_mode,
            }
        except IOError:
            return None
