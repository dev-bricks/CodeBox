"""Unit tests for optional linter discovery and output normalization."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from features.linter import (
    parse_eslint_output,
    parse_flake8_output,
    parse_ruff_output,
    run_linter,
)


class LinterParsingTests(unittest.TestCase):
    def test_ruff_json_is_normalized(self):
        errors = parse_ruff_output(
            '[{"filename":"sample.py","code":"F401",'
            '"message":"imported but unused","location":{"row":3,"column":5}}]'
        )
        self.assertEqual(errors[0]["line"], 3)
        self.assertEqual(errors[0]["col"], 5)
        self.assertEqual(errors[0]["source"], "ruff")
        self.assertEqual(errors[0]["severity"], "error")

    def test_eslint_json_maps_warning_and_error(self):
        errors = parse_eslint_output(
            '[{"filePath":"app.js","messages":['
            '{"line":2,"column":4,"severity":1,"ruleId":"semi","message":"Missing semicolon"},'
            '{"line":5,"column":1,"severity":2,"ruleId":"no-undef","message":"x is not defined"}'
            ']}]'
        )
        self.assertEqual([item["severity"] for item in errors], ["warning", "error"])
        self.assertEqual(errors[1]["code"], "no-undef")

    def test_flake8_text_handles_windows_paths(self):
        errors = parse_flake8_output(
            "C:\\work\\sample.py:4:7: F401 imported but unused\n"
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["line"], 4)
        self.assertEqual(errors[0]["col"], 7)
        self.assertEqual(errors[0]["code"], "F401")

    def test_run_linter_is_optional_and_uses_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("import os\n", encoding="utf-8")
            completed = subprocess.CompletedProcess([], 1, '[{"code":"F401","message":"unused",'
                                                       '"location":{"row":1,"column":1}}]', "")
            with patch("features.linter.resolve_linter", return_value=(
                ["ruff", "check"], parse_ruff_output, "ruff"
            )), patch("features.linter.subprocess.run", return_value=completed) as run:
                errors = run_linter("Python", path)
            self.assertEqual(errors[0]["source"], "ruff")
            self.assertEqual(run.call_args.kwargs["cwd"], str(path.parent))


if __name__ == "__main__":
    unittest.main()
