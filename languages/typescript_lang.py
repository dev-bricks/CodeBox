#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TypeScript Language Provider"""

import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class TypeScriptProvider(LanguageProvider):
    def get_name(self) -> str:
        return "TypeScript"

    def get_extensions(self) -> List[str]:
        return ["ts", "tsx"]

    def get_keywords(self) -> List[str]:
        return [
            'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'enum',
            'export', 'extends', 'false', 'finally', 'for', 'function',
            'if', 'implements', 'import', 'in', 'instanceof', 'interface',
            'let', 'new', 'null', 'package', 'private', 'protected',
            'public', 'return', 'static', 'super', 'switch', 'this',
            'throw', 'true', 'try', 'type', 'typeof', 'undefined',
            'var', 'void', 'while', 'with', 'yield', 'async', 'await',
            'of', 'readonly', 'abstract', 'as', 'declare', 'namespace',
            'keyof', 'infer', 'never', 'unknown', 'any'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'Array', 'Boolean', 'Date', 'Error', 'Function', 'JSON',
            'Map', 'Math', 'Number', 'Object', 'Promise', 'Proxy',
            'RegExp', 'Set', 'String', 'Symbol', 'WeakMap', 'WeakSet',
            'console', 'parseInt', 'parseFloat', 'isNaN', 'isFinite',
            'Record', 'Partial', 'Required', 'Readonly', 'Pick', 'Omit',
            'Exclude', 'Extract', 'ReturnType', 'Parameters'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'fn': 'function name(params: type): returnType {\n    \n}',
            'afn': 'const name = (params: type): returnType => {\n    \n};',
            'interface': 'interface Name {\n    property: type;\n}',
            'type': 'type Name = {\n    property: type;\n};',
            'class': 'class Name {\n    constructor(private param: type) {\n        \n    }\n}',
            'async': 'async function name(params: type): Promise<returnType> {\n    \n}',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        if shutil.which("ts-node"):
            return ["ts-node", file_path]
        return ["npx", "ts-node", file_path]

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        return ["ts-node", "--inspect-brk", file_path]

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("tsc"):
            return ["tsc", "--noEmit", file_path]
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
