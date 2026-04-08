#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Go Language Provider"""

import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class GoProvider(LanguageProvider):
    def get_name(self) -> str:
        return "Go"

    def get_extensions(self) -> List[str]:
        return ["go"]

    def get_keywords(self) -> List[str]:
        return [
            'break', 'case', 'chan', 'const', 'continue', 'default',
            'defer', 'else', 'fallthrough', 'for', 'func', 'go', 'goto',
            'if', 'import', 'interface', 'map', 'package', 'range',
            'return', 'select', 'struct', 'switch', 'type', 'var',
            'true', 'false', 'nil', 'iota'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'append', 'cap', 'close', 'complex', 'copy', 'delete',
            'imag', 'len', 'make', 'new', 'panic', 'print', 'println',
            'real', 'recover', 'bool', 'byte', 'complex64', 'complex128',
            'error', 'float32', 'float64', 'int', 'int8', 'int16',
            'int32', 'int64', 'rune', 'string', 'uint', 'uint8',
            'uint16', 'uint32', 'uint64', 'uintptr', 'fmt', 'os',
            'io', 'strings', 'strconv', 'errors'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'func': 'func name(params type) returnType {\n    \n}',
            'main': 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello")\n}',
            'struct': 'type Name struct {\n    Field Type\n}',
            'interface': 'type Name interface {\n    Method() ReturnType\n}',
            'for': 'for i := 0; i < n; i++ {\n    \n}',
            'forr': 'for i, v := range collection {\n    \n}',
            'if': 'if condition {\n    \n}',
            'iferr': 'if err != nil {\n    return err\n}',
            'switch': 'switch value {\ncase a:\n    \ndefault:\n    \n}',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        return ["go", "run", file_path]

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("dlv"):
            return ["dlv", "debug", file_path]
        return None

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        return ["go", "vet", file_path]

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
