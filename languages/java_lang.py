#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Java Language Provider"""

import sys
from typing import List, Dict, Tuple, Optional
from .base import LanguageProvider


class JavaProvider(LanguageProvider):
    def get_name(self) -> str:
        return "Java"

    def get_extensions(self) -> List[str]:
        return ["java"]

    def get_keywords(self) -> List[str]:
        return [
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case',
            'catch', 'char', 'class', 'const', 'continue', 'default',
            'do', 'double', 'else', 'enum', 'extends', 'false', 'final',
            'finally', 'float', 'for', 'goto', 'if', 'implements',
            'import', 'instanceof', 'int', 'interface', 'long', 'native',
            'new', 'null', 'package', 'private', 'protected', 'public',
            'return', 'short', 'static', 'strictfp', 'super', 'switch',
            'synchronized', 'this', 'throw', 'throws', 'transient',
            'true', 'try', 'var', 'void', 'volatile', 'while', 'yield',
            'record', 'sealed', 'permits', 'non-sealed'
        ]

    def get_builtins(self) -> List[str]:
        return [
            'System', 'String', 'Integer', 'Long', 'Double', 'Float',
            'Boolean', 'Character', 'Byte', 'Short', 'Object', 'Class',
            'Math', 'Arrays', 'Collections', 'List', 'ArrayList',
            'LinkedList', 'Map', 'HashMap', 'TreeMap', 'Set', 'HashSet',
            'TreeSet', 'Optional', 'Stream', 'Collectors',
            'IOException', 'Exception', 'RuntimeException',
            'StringBuilder', 'StringBuffer', 'Thread', 'Runnable',
            'Override', 'Deprecated', 'SuppressWarnings'
        ]

    def get_snippets(self) -> Dict[str, str]:
        return {
            'main': 'public static void main(String[] args) {\n    \n}',
            'class': 'public class Name {\n    \n}',
            'sout': 'System.out.println();',
            'for': 'for (int i = 0; i < n; i++) {\n    \n}',
            'foreach': 'for (Type item : collection) {\n    \n}',
            'if': 'if (condition) {\n    \n}',
            'try': 'try {\n    \n} catch (Exception e) {\n    e.printStackTrace();\n}',
            'method': 'public ReturnType name(Type param) {\n    \n}',
        }

    def get_run_command(self, file_path: str) -> List[str]:
        import os
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        class_dir = os.path.dirname(file_path) or "."
        if sys.platform == "win32":
            return ["cmd", "/c", f'javac "{file_path}" && java -cp "{class_dir}" {class_name}']
        return ["bash", "-c", f'javac "{file_path}" && java -cp "{class_dir}" {class_name}']

    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        return None

    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        return ["javac", "-Xlint:all", file_path]

    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("//", ("/*", "*/"))
