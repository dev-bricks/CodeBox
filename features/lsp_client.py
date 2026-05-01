#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSP Client - Language Server Protocol Integration für CodeBox

Bietet grundlegende LSP-Funktionalität:
- Server-Start/Stop pro Sprache
- textDocument/didOpen, didChange, didSave
- textDocument/completion (Auto-Completion)
- textDocument/hover (Tooltip-Info)
- textDocument/publishDiagnostics (Fehler/Warnungen)
"""

import importlib.util
import json
import subprocess
import sys
import threading
import shutil
from typing import Optional, Dict, List, Callable
from pathlib import Path


# Bekannte LSP-Server pro Sprache
LSP_SERVERS = {
    "Python": {"cmd": ["pylsp"], "check": "pylsp", "module": "pylsp"},
    "JavaScript": {"cmd": ["typescript-language-server", "--stdio"], "check": "typescript-language-server"},
    "TypeScript": {"cmd": ["typescript-language-server", "--stdio"], "check": "typescript-language-server"},
    "Rust": {"cmd": ["rust-analyzer"], "check": "rust-analyzer"},
    "Go": {"cmd": ["gopls"], "check": "gopls"},
    "C++": {"cmd": ["clangd"], "check": "clangd"},
    "Java": {"cmd": ["jdtls"], "check": "jdtls"},
}


class LSPMessage:
    """Hilfsklasse zum Erstellen/Parsen von LSP JSON-RPC Nachrichten."""

    @staticmethod
    def encode(obj: dict) -> bytes:
        body = json.dumps(obj).encode('utf-8')
        header = f"Content-Length: {len(body)}\r\n\r\n".encode('ascii')
        return header + body

    @staticmethod
    def create_request(method: str, params: dict, req_id: int) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }

    @staticmethod
    def create_notification(method: str, params: dict) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }


class LSPClient:
    """LSP-Client für eine einzelne Sprache/Server-Instanz.

    Startet einen LSP-Server als Subprocess und kommuniziert über stdin/stdout.
    """

    def __init__(self, language: str, root_path: str = "."):
        self.language = language
        self.root_path = Path(root_path).resolve()
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._pending: Dict[int, Callable] = {}
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

        # Callbacks
        self.on_diagnostics: Optional[Callable] = None
        self.on_completion: Optional[Callable] = None
        self.on_hover: Optional[Callable] = None

    @property
    def server_config(self) -> Optional[dict]:
        return LSP_SERVERS.get(self.language)

    def _resolve_command(self) -> Optional[List[str]]:
        """Ermittelt das startbare Server-Kommando.

        Bei Python ist `pylsp.exe` nach einer pip-Installation nicht immer auf
        PATH. Wenn das Modul im aktuellen Interpreter vorhanden ist, startet
        CodeBox den Server deshalb über `python -m pylsp`.
        """
        config = self.server_config
        if not config:
            return None
        check = config.get("check")
        if check and shutil.which(check):
            return list(config["cmd"])
        module = config.get("module")
        if module and importlib.util.find_spec(module):
            return [sys.executable, "-m", module]
        return None

    def is_available(self) -> bool:
        """Prüft, ob der LSP-Server installiert ist."""
        return self._resolve_command() is not None

    def start(self) -> bool:
        """Startet den LSP-Server-Prozess."""
        command = self._resolve_command()
        if not command:
            return False

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.root_path)
            )
        except (FileNotFoundError, OSError):
            return False

        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # Initialize-Request senden
        self._send_request("initialize", {
            "processId": None,
            "rootUri": self.root_path.as_uri(),
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {"snippetSupport": False}
                    },
                    "hover": {},
                    "publishDiagnostics": {"relatedInformation": True}
                }
            }
        })
        self._send_notification("initialized", {})
        return True

    def stop(self):
        """Stoppt den LSP-Server."""
        self._running = False
        process = self.process
        if process:
            try:
                self._send_request("shutdown", {})
                self._send_notification("exit", {})
            except (BrokenPipeError, OSError):
                pass
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            finally:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream:
                        try:
                            stream.close()
                        except OSError:
                            pass
                self.process = None
        if (
            self._reader_thread
            and self._reader_thread.is_alive()
            and threading.current_thread() is not self._reader_thread
        ):
            self._reader_thread.join(timeout=1)
        self._reader_thread = None

    def did_open(self, uri: str, language_id: str, text: str, version: int = 1):
        """Benachrichtigt den Server über eine geöffnete Datei."""
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": version,
                "text": text
            }
        })

    def did_change(self, uri: str, text: str, version: int):
        """Benachrichtigt den Server über Änderungen."""
        self._send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": text}]
        })

    def did_save(self, uri: str, text: str = None):
        """Benachrichtigt den Server über Speichern."""
        params = {"textDocument": {"uri": uri}}
        if text is not None:
            params["text"] = text
        self._send_notification("textDocument/didSave", params)

    def request_completion(self, uri: str, line: int, character: int, callback: Callable = None):
        """Fordert Auto-Completion an."""
        self._send_request("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        }, callback=callback or self.on_completion)

    def request_hover(self, uri: str, line: int, character: int, callback: Callable = None):
        """Fordert Hover-Info an."""
        self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        }, callback=callback or self.on_hover)

    # --- Interne Methoden ---

    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _send_request(self, method: str, params: dict, callback: Callable = None):
        """Sendet einen Request an den Server."""
        req_id = self._next_id()
        msg = LSPMessage.create_request(method, params, req_id)
        if callback:
            with self._lock:
                self._pending[req_id] = callback
        self._write(msg)

    def _send_notification(self, method: str, params: dict):
        """Sendet eine Notification an den Server."""
        msg = LSPMessage.create_notification(method, params)
        self._write(msg)

    def _write(self, obj: dict):
        """Schreibt eine JSON-RPC Nachricht an stdin."""
        if self.process and self.process.stdin:
            data = LSPMessage.encode(obj)
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
            except (BrokenPipeError, OSError):
                self._running = False

    def _read_loop(self):
        """Liest Nachrichten vom Server (in separatem Thread)."""
        while self._running and self.process and self.process.stdout:
            try:
                # Header lesen
                headers = {}
                while True:
                    line = self.process.stdout.readline().decode('ascii', errors='replace').strip()
                    if not line:
                        break
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()

                content_length = int(headers.get('Content-Length', 0))
                if content_length == 0:
                    continue

                # Body lesen
                body = self.process.stdout.read(content_length)
                msg = json.loads(body.decode('utf-8'))

                self._handle_message(msg)

            except (ValueError, json.JSONDecodeError, OSError):
                continue
            except Exception:
                break
        self._running = False

    def _handle_message(self, msg: dict):
        """Verarbeitet eine eingehende Nachricht."""
        # Response auf einen Request
        if 'id' in msg and 'result' in msg:
            req_id = msg['id']
            with self._lock:
                callback = self._pending.pop(req_id, None)
            if callback:
                callback(msg['result'])

        # Server-Notification (z.B. Diagnostics)
        elif 'method' in msg:
            method = msg['method']
            params = msg.get('params', {})

            if method == 'textDocument/publishDiagnostics' and self.on_diagnostics:
                self.on_diagnostics(params)


class LSPManager:
    """Verwaltet LSP-Clients für alle Sprachen."""

    def __init__(self, root_path: str = "."):
        self.root_path = root_path
        self._clients: Dict[str, LSPClient] = {}

    def get_client(self, language: str) -> Optional[LSPClient]:
        """Holt oder erstellt einen LSP-Client für eine Sprache."""
        if language not in self._clients:
            client = LSPClient(language, self.root_path)
            if client.is_available():
                if client.start():
                    self._clients[language] = client
                    return client
            return None
        return self._clients[language]

    def stop_all(self):
        """Stoppt alle laufenden LSP-Server."""
        for client in self._clients.values():
            client.stop()
        self._clients.clear()

    def get_available_servers(self) -> List[str]:
        """Gibt eine Liste der verfügbaren LSP-Server zurück."""
        available = []
        for lang, config in LSP_SERVERS.items():
            if shutil.which(config["check"]):
                available.append(lang)
        return available
