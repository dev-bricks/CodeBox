import unittest
from unittest.mock import patch

from features.lsp_client import LSPClient


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

    def test_unknown_language_is_unavailable(self):
        client = LSPClient("Unknown")

        self.assertFalse(client.is_available())
        self.assertIsNone(client._resolve_command())


if __name__ == "__main__":
    unittest.main()
