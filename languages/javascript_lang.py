#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JavaScript Language Provider"""

import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class JavaScriptProvider(LanguageProvider):
    def get_name(self) -> str:
        return "JavaScript"

    def get_extensions(self) -> List[str]:
        return ["js", "mjs", "cjs"]

    def get_keywords(self) -> List[str]:
        return [
            'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export',
            'extends', 'false', 'finally', 'for', 'function', 'if',
            'import', 'in', 'instanceof', 'let', 'new', 'null', 'return',
            'static', 'super', 'switch', 'this', 'throw', 'true', 'try',
            'typeof', 'var', 'void', 'while', 'with', 'yield', 'async',
            'await', 'of'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'Array', 'Boolean', 'Date', 'Error', 'Function', 'JSON',
            'Map', 'Math', 'Number', 'Object', 'Promise', 'Proxy',
            'RegExp', 'Set', 'String', 'Symbol', 'WeakMap', 'WeakSet',
            'console', 'parseInt', 'parseFloat', 'isNaN', 'isFinite',
            'decodeURI', 'encodeURI', 'setTimeout', 'setInterval',
            'clearTimeout', 'clearInterval', 'fetch', 'require', 'module'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'fn': 'function name(params) {\n    \n}',
            'afn': 'const name = (params) => {\n    \n};',
            'class': 'class Name {\n    constructor(params) {\n        \n    }\n}',
            'if': 'if (condition) {\n    \n}',
            'for': 'for (let i = 0; i < length; i++) {\n    \n}',
            'foreach': 'array.forEach((item) => {\n    \n});',
            'try': 'try {\n    \n} catch (error) {\n    \n}',
            'log': 'console.log();',
            'async': 'async function name(params) {\n    \n}',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        return ["node", file_path]

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        return ["node", "--inspect-brk", file_path]

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("eslint"):
            return ["eslint", "-f", "compact", file_path]
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
