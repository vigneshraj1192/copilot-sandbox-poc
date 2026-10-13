from pathlib import Path
from typing import List, Dict, Any, Optional
import tree_sitter_c_sharp as tscsharp
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor

CSHARP_LANG = Language(tscsharp.language())
PYTHON_LANG = Language(tspython.language())

# S-Expression queries identifying definitions and references
CSHARP_QUERY = """
(class_declaration name: (identifier) @name.def.class)
(interface_declaration name: (identifier) @name.def.interface)
(method_declaration name: (identifier) @name.def.method)
(invocation_expression expression: (member_access_expression name: (identifier) @name.ref.call))
(invocation_expression expression: (identifier) @name.ref.call)
"""

PYTHON_QUERY = """
(class_definition name: (identifier) @name.def.class)
(function_definition name: (identifier) @name.def.func)
(call function: (identifier) @name.ref.call)
(call function: (attribute attribute: (identifier) @name.ref.call))
"""

class ASTTagger:
    def __init__(self):
        self.configs = {
            ".cs": (Parser(CSHARP_LANG), Query(CSHARP_LANG, CSHARP_QUERY)),
            ".py": (Parser(PYTHON_LANG), Query(PYTHON_LANG, PYTHON_QUERY))
        }

    def extract_tags(self, file_path: Path, code_bytes: bytes) -> List[Dict[str, Any]]:
        ext = file_path.suffix.lower()
        if ext not in self.configs:
            return []

        parser, query = self.configs[ext]
        try:
            tree = parser.parse(code_bytes)
            cursor = QueryCursor(query)
            captures_dict = cursor.captures(tree.root_node)
        except Exception:
            return []

        tags = []
        for tag_name, nodes in captures_dict.items():
            parts = tag_name.split(".")
            if len(parts) < 3:
                continue
            role = parts[1]  # "def" or "ref"
            kind = parts[2]  # "class", "method", "call", etc.

            for node in nodes:
                name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                tags.append({
                    "name": name,
                    "role": role,
                    "kind": kind,
                    "line": node.start_point[0] + 1
                })
        return tags