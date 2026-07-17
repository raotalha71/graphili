"""
Core data structures for the code graph.
Every function/class in the analyzed codebase becomes a Node.
Every resolved call between them becomes an Edge (added in Phase 3 / resolver.py).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArgInfo:
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None


@dataclass
class Node:
    id: str                      # fully-qualified id, e.g. "routes.students.enroll_student"
    name: str                    # short name, e.g. "enroll_student"
    node_type: str                # "function" | "class" | "api" | "method"
    file_path: str                # relative path to the file
    line_number: int
    args: list[ArgInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    is_api: bool = False
    api_method: Optional[str] = None   # "GET" | "POST" | etc, if is_api
    api_route: Optional[str] = None    # "/students", if is_api
    parent_class: Optional[str] = None  # set if this is a method
    docstring: Optional[str] = None
    ast_hash: Optional[str] = None      # filled in by similarity.py later

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "file": self.file_path,
            "line": self.line_number,
            "args": [
                {"name": a.name, "type": a.type_hint, "default": a.default}
                for a in self.args
            ],
            "return_type": self.return_type,
            "decorators": self.decorators,
            "is_api": self.is_api,
            "api_method": self.api_method,
            "api_route": self.api_route,
            "parent_class": self.parent_class,
            "docstring": self.docstring,
            "ast_hash": self.ast_hash,
        }


@dataclass
class Edge:
    source: str   # node id of the caller
    target: str   # node id of the callee
    edge_type: str = "calls"  # room to grow: "calls" | "imports" | "inherits"

    def to_dict(self):
        return {"source": self.source, "target": self.target, "type": self.edge_type}


@dataclass
class Graph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
