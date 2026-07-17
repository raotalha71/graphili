"""
Phase 1 core: walks a single file's AST and extracts Node objects.
This is the "rule engine" -- no LLM, just pattern matching on the tree.
"""

import ast
from .models import Node, ArgInfo

# decorator patterns that mark a function as an API endpoint.
# matches app.post(...), router.get(...), api.put(...) etc.
API_DECORATOR_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _unparse_safe(node) -> str | None:
    """ast.unparse exists on 3.9+, this just guards against None nodes."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _decorator_to_str(dec: ast.expr) -> str:
    try:
        return ast.unparse(dec)
    except Exception:
        return "<decorator>"


def _detect_api(decorators: list[ast.expr]) -> tuple[bool, str | None, str | None]:
    """
    Looks for a decorator shaped like: something.post("/route"), app.get('/x'), etc.
    Returns (is_api, http_method, route_string).
    """
    for dec in decorators:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            method_name = dec.func.attr.lower()
            if method_name in API_DECORATOR_METHODS:
                route = None
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    route = dec.args[0].value
                return True, method_name.upper(), route
    return False, None, None


class FileVisitor(ast.NodeVisitor):
    """
    Visits one file's AST and produces a flat list of Nodes.
    Tracks class context so methods get a parent_class and a qualified id.
    """

    def __init__(self, module_path: str, file_path: str):
        self.module_path = module_path
        self.file_path = file_path
        self.nodes: list[Node] = []
        self._class_stack: list[str] = []

    def _qualify(self, name: str) -> str:
        prefix = f"{self.module_path}." if self.module_path else ""
        if self._class_stack:
            return f"{prefix}{'.'.join(self._class_stack)}.{name}"
        return f"{prefix}{name}"

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = self._qualify(node.name)
        self.nodes.append(
            Node(
                id=class_id,
                name=node.name,
                node_type="class",
                file_path=self.file_path,
                line_number=node.lineno,
                docstring=ast.get_docstring(node),
            )
        )
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node)
        # NOTE: intentionally not calling generic_visit here for nested funcs in v1.
        # Nested/inner functions are a v2 concern -- keep the graph readable for now.

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node)

    def _handle_function(self, node):
        args = []
        for a in node.args.args:
            args.append(ArgInfo(name=a.arg, type_hint=_unparse_safe(a.annotation)))

        decorators_str = [_decorator_to_str(d) for d in node.decorator_list]
        is_api, api_method, api_route = _detect_api(node.decorator_list)

        node_id = self._qualify(node.name)
        node_type = "api" if is_api else ("method" if self._class_stack else "function")

        self.nodes.append(
            Node(
                id=node_id,
                name=node.name,
                node_type=node_type,
                file_path=self.file_path,
                line_number=node.lineno,
                args=args,
                return_type=_unparse_safe(node.returns),
                decorators=decorators_str,
                is_api=is_api,
                api_method=api_method,
                api_route=api_route,
                parent_class=self._class_stack[-1] if self._class_stack else None,
                docstring=ast.get_docstring(node),
            )
        )


def extract_nodes_from_source(source: str, module_path: str, file_path: str) -> list[Node]:
    tree = ast.parse(source, filename=file_path)
    visitor = FileVisitor(module_path=module_path, file_path=file_path)
    visitor.visit(tree)
    return visitor.nodes
