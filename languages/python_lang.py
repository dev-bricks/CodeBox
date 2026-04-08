#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python Language Provider"""

import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class PythonProvider(LanguageProvider):
    def get_name(self) -> str:
        return "Python"

    def get_extensions(self) -> List[str]:
        return ["py", "pyw", "pyi"]

    def get_keywords(self) -> List[str]:
        return [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async',
            'await', 'break', 'class', 'continue', 'def', 'del', 'elif',
            'else', 'except', 'finally', 'for', 'from', 'global', 'if',
            'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
            'self'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable',
            'chr', 'dict', 'dir', 'enumerate', 'eval', 'exec', 'filter',
            'float', 'format', 'getattr', 'globals', 'hasattr', 'hash',
            'hex', 'id', 'input', 'int', 'isinstance', 'issubclass',
            'iter', 'len', 'list', 'locals', 'map', 'max', 'min', 'next',
            'object', 'open', 'ord', 'pow', 'print', 'range', 'repr',
            'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
            'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'def': 'def name(args):\n    pass',
            'class': 'class Name:\n    def __init__(self):\n        pass',
            'if': 'if condition:\n    pass',
            'for': 'for item in items:\n    pass',
            'try': 'try:\n    pass\nexcept Exception as e:\n    pass',
            'with': 'with context as var:\n    pass',
            'main': 'if __name__ == "__main__":\n    main()',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        return ["python", "-u", file_path]

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        return ["python", "-m", "pdb", file_path]

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("flake8"):
            return ["flake8", file_path]
        elif shutil.which("pylint"):
            return ["pylint", "--output-format=text", file_path]
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("#", ('"""', '"""'))

    def get_indent_triggers(self) -> List[str]:
        return [':']

    def get_dedent_triggers(self) -> List[str]:
        return ['return', 'break', 'continue', 'pass', 'raise']
