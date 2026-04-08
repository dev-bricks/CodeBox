#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C/C++ Language Provider"""

import sys
import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class CppProvider(LanguageProvider):
    def get_name(self) -> str:
        return "C++"

    def get_extensions(self) -> List[str]:
        return ["cpp", "cc", "cxx", "hpp", "h", "c"]

    def get_keywords(self) -> List[str]:
        return [
            'alignas', 'alignof', 'auto', 'bool', 'break', 'case', 'catch',
            'char', 'class', 'const', 'constexpr', 'continue', 'default',
            'delete', 'do', 'double', 'else', 'enum', 'explicit',
            'extern', 'false', 'float', 'for', 'friend', 'goto', 'if',
            'inline', 'int', 'long', 'mutable', 'namespace', 'new',
            'noexcept', 'nullptr', 'operator', 'private', 'protected',
            'public', 'return', 'short', 'signed', 'sizeof', 'static',
            'struct', 'switch', 'template', 'this', 'throw', 'true',
            'try', 'typedef', 'typeid', 'typename', 'union', 'unsigned',
            'using', 'virtual', 'void', 'volatile', 'while',
            'include', 'define', 'ifdef', 'ifndef', 'endif', 'pragma'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'std', 'cout', 'cin', 'endl', 'string', 'vector', 'map',
            'set', 'pair', 'make_pair', 'sort', 'find', 'begin', 'end',
            'push_back', 'pop_back', 'size', 'empty', 'clear', 'printf',
            'scanf', 'malloc', 'free', 'NULL'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'main': 'int main(int argc, char* argv[]) {\n    \n    return 0;\n}',
            'class': 'class Name {\npublic:\n    Name();\n    ~Name();\nprivate:\n    \n};',
            'for': 'for (int i = 0; i < n; i++) {\n    \n}',
            'foreach': 'for (auto& item : container) {\n    \n}',
            'if': 'if (condition) {\n    \n}',
            'inc': '#include <iostream>',
            'guard': '#ifndef HEADER_H\n#define HEADER_H\n\n\n\n#endif',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        output = file_path.rsplit('.', 1)[0]
        if sys.platform == "win32":
            output += ".exe"
            return ["cmd", "/c", f'g++ -o "{output}" "{file_path}" && "{output}"']
        return ["bash", "-c", f'g++ -o "{output}" "{file_path}" && "{output}"']

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        output = file_path.rsplit('.', 1)[0]
        return ["gdb", output]

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("g++"):
            return ["g++", "-Wall", "-Wextra", "-fsyntax-only", file_path]
        return None

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
