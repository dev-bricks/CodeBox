import unittest
from unittest.mock import patch

from features.lsp_client import LSPClient, LSPManager


class LSPClientCommandResolutionTests(unittest.TestCase):
    def test_prefers_server_executable_when_on_path(self):
        client = LSPClient("Python")

        with patch("features.lsp_client.shutil.which", return_value="C:/bin/pylsp.exe"):
            self.assertTrue(client.is_available())
            self.assertEqual(client._resolve_command(), ["pylsp"])

    def test_python_server_falls_back_to_current_interpreter_module(self):
        client = LSPClient("Python")

        with patch("features.lsp_client.shutil.which", return_value=None), \
                patch("features.lsp_client.importlib.util.find_spec", return_value=object()), \
                patch("features.lsp_client.sys.executable", "C:/Python/python.exe"):
            self.assertTrue(client.is_available())
            self.assertEqual(
                client._resolve_command(),
                ["C:/Python/python.exe", "-m", "pylsp"],
            )

    def test_unavailable_when_no_executable_or_module_exists(self):
        client = LSPClient("Python")

        with patch("features.lsp_client.shutil.which", return_value=None), \
                patch("features.lsp_client.importlib.util.find_spec", return_value=None):
            self.assertFalse(client.is_available())
            self.assertIsNone(client._resolve_command())

    def test_available_servers_uses_module_fallback(self):
        manager = LSPManager()

        def mock_which(_):
            return None

        def mock_find_spec(name):
            return object() if name == "pylsp" else None

        with patch("features.lsp_client.shutil.which", side_effect=mock_which), \
                patch("features.lsp_client.importlib.util.find_spec", side_effect=mock_find_spec):
            self.assertEqual(manager.get_available_servers(), ["Python"])

    def test_unknown_language_is_unavailable(self):
        client = LSPClient("Unknown")

        self.assertFalse(client.is_available())
        self.assertIsNone(client._resolve_command())


class LSPReadLoopTerminationTests(unittest.TestCase):
    def test_read_loop_terminates_on_server_death(self):
        """Regressions-Test: _read_loop darf bei Server-Tod NICHT in einer
        Busy-Loop haengen (readline() liefert b'' = EOF endlos)."""
        import io
        import threading
        import types

        client = LSPClient("Python")
        client.process = types.SimpleNamespace(
            stdout=io.BytesIO(b""),
            stdin=None,
            stderr=None,
        )
        client._running = True

        t = threading.Thread(target=client._read_loop, daemon=True)
        t.start()
        t.join(timeout=2)

        self.assertFalse(t.is_alive(), "read_loop haengt in Busy-Loop (Server-Tod nicht erkannt)")
        self.assertFalse(client._running)


if __name__ == "__main__":
    unittest.main()
