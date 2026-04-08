#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rust Language Provider"""

import sys
import shutil
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class RustProvider(LanguageProvider):
    def get_name(self) -> str:
        return "Rust"

    def get_extensions(self) -> List[str]:
        return ["rs"]

    def get_keywords(self) -> List[str]:
        return [
            'as', 'async', 'await', 'break', 'const', 'continue', 'crate',
            'dyn', 'else', 'enum', 'extern', 'false', 'fn', 'for', 'if',
            'impl', 'in', 'let', 'loop', 'match', 'mod', 'move', 'mut',
            'pub', 'ref', 'return', 'self', 'Self', 'static', 'struct',
            'super', 'trait', 'true', 'type', 'unsafe', 'use', 'where',
            'while', 'yield'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'bool', 'char', 'f32', 'f64', 'i8', 'i16', 'i32', 'i64',
            'i128', 'isize', 'u8', 'u16', 'u32', 'u64', 'u128', 'usize',
            'str', 'String', 'Vec', 'Box', 'Option', 'Result', 'Some',
            'None', 'Ok', 'Err', 'HashMap', 'HashSet', 'println', 'print',
            'eprintln', 'format', 'vec', 'todo', 'unimplemented', 'panic',
            'assert', 'assert_eq', 'assert_ne', 'dbg', 'Clone', 'Debug',
            'Display', 'Default', 'Iterator', 'Into', 'From'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'fn': 'fn name(params: Type) -> ReturnType {\n    \n}',
            'struct': 'struct Name {\n    field: Type,\n}',
            'enum': 'enum Name {\n    Variant,\n}',
            'impl': 'impl Name {\n    fn new() -> Self {\n        \n    }\n}',
            'match': 'match value {\n    pattern => result,\n    _ => default,\n}',
            'for': 'for item in iter {\n    \n}',
            'if': 'if condition {\n    \n}',
            'main': 'fn main() {\n    \n}',
            'test': '#[test]\nfn test_name() {\n    \n}',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        output = file_path.rsplit('.', 1)[0]
        if sys.platform == "win32":
            output += ".exe"
            return ["cmd", "/c", f'rustc -o "{output}" "{file_path}" && "{output}"']
        return ["bash", "-c", f'rustc -o "{output}" "{file_path}" && "{output}"']

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("rust-gdb"):
            output = file_path.rsplit('.', 1)[0]
            return ["rust-gdb", output]
        return None

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        return ["rustc", "--edition", "2021", file_path]

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
