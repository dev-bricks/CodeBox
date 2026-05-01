import os
import tempfile
import threading
import unittest
from pathlib import Path

from features.lsp_client import LSPClient


@unittest.skipUnless(
    os.environ.get("CODEBOX_LSP_RUNTIME") == "1",
    "Set CODEBOX_LSP_RUNTIME=1 and install python-lsp-server[all] to run.",
)
class PythonLSPRuntimeTests(unittest.TestCase):
    def test_pylsp_diagnostics_and_completion_roundtrip(self):
        client = LSPClient("Python", tempfile.mkdtemp(prefix="codebox-lsp-"))
        if not client.is_available():
            self.skipTest("pylsp is not available on PATH or as python -m pylsp")

        root = Path(client.root_path)
        path = root / "sample.py"
        uri = path.resolve().as_uri()
        diagnostics = []
        completions = []
        diag_event = threading.Event()
        completion_event = threading.Event()

        def on_diagnostics(params):
            if params.get("uri") != uri:
                return
            batch = params.get("diagnostics", [])
            diagnostics[:] = batch
            if batch:
                diag_event.set()

        def on_completion(result):
            items = result.get("items", []) if isinstance(result, dict) else (result or [])
            completions[:] = [
                item.get("label") if isinstance(item, dict) else str(item)
                for item in items
            ]
            completion_event.set()

        try:
            self.assertTrue(client.start())
            client.on_diagnostics = on_diagnostics

            broken_text = "def broken(:\n    pass\n"
            path.write_text(broken_text, encoding="utf-8")
            client.did_open(uri, "python", broken_text, version=1)
            self.assertTrue(
                diag_event.wait(15),
                "No diagnostics received; install python-lsp-server[all] with lint plugins.",
            )
            self.assertTrue(
                any("invalid syntax" in item.get("message", "") for item in diagnostics)
            )

            completion_text = "import os\nos.pa"
            path.write_text(completion_text, encoding="utf-8")
            client.did_change(uri, completion_text, version=2)
            client.request_completion(uri, 1, 5, callback=on_completion)
            self.assertTrue(completion_event.wait(10), "No completion response received.")
            self.assertIn("path", {item for item in completions if item})
        finally:
            client.stop()


if __name__ == "__main__":
    unittest.main()
