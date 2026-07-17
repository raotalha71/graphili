"""
Pass 2: resolve imports and function calls into edges.

Must run AFTER indexer.py (Pass 1) has built the complete node index --
you can't resolve a call to a function you haven't indexed yet.

Resolution strategy (v1):
  1. Direct match: call name is already a qualified node ID (rare).
  2. Import-based: look up the first part of the call in the file's import map,
     reconstruct the qualified name, check if it's in the node index.
  3. Same-module: try {current_module}.{call_name} for local calls within a file.
"""

import ast
from pathlib import Path

from .discovery import discover_python_files, to_module_path, detect_source_root
from .models import Graph, Edge, Node


# ---------------------------------------------------------------------------
# Step 1: extract import mappings from a file
# ---------------------------------------------------------------------------

def extract_imports(tree: ast.Module) -> dict[str, str]:
    """
    Walk a file's AST and build a mapping:
        local_name -> fully_qualified_path

    Examples:
        from models.product import find_product_by_id
          -> {"find_product_by_id": "models.product.find_product_by_id"}

        from services.inventory import reserve_stock as rs
          -> {"rs": "services.inventory.reserve_stock"}

        import os
          -> {"os": "os"}
    """
    imports: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                imports[local] = alias.name

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                local = alias.asname or alias.name
                qualified = f"{module}.{alias.name}" if module else alias.name
                imports[local] = qualified

    return imports


# ---------------------------------------------------------------------------
# Step 2: extract raw call names from function bodies
# ---------------------------------------------------------------------------

def _call_target_name(node: ast.expr) -> str | None:
    """
    Unpack an ast.Call.func node into a dotted name string.
    e.g.  ast for `reserve_stock(...)` -> "reserve_stock"
          ast for `db.execute_query(...)` -> "db.execute_query"
    Returns None for things we can't represent as a simple name (e.g. chained calls).
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        prefix = _call_target_name(node.value)
        if prefix:
            return f"{prefix}.{node.attr}"
        return node.attr
    return None


def extract_calls_from_body(body: list[ast.stmt]) -> list[str]:
    """
    Walk a function's body statements and collect all call target names.
    Returns raw names like "find_product_by_id", "db.execute_query", etc.
    """
    calls: list[str] = []

    # Wrap body in a Module so ast.walk can traverse it
    wrapper = ast.Module(body=body, type_ignores=[])
    for node in ast.walk(wrapper):
        if isinstance(node, ast.Call):
            name = _call_target_name(node.func)
            if name:
                calls.append(name)

    return calls


# ---------------------------------------------------------------------------
# Step 3: resolve a raw call name to a node ID in the index
# ---------------------------------------------------------------------------

def _resolve_call(
    call_name: str,
    import_map: dict[str, str],
    module_path: str,
    node_by_id: dict[str, Node],
) -> str | None:
    """
    Try to resolve a raw call name to a node ID in the index.

    Resolution order:
      1. Direct match in node_by_id (handles fully-qualified calls)
      2. Import-based: look up first part in import_map, reconstruct qualified name
      3. Same-module: try module_path.call_name for calls within the same file
    """
    # 1. Direct match
    if call_name in node_by_id:
        return call_name

    # 2. Import-based resolution
    parts = call_name.split(".")
    first_part = parts[0]
    if first_part in import_map:
        qualified = import_map[first_part]
        if len(parts) > 1:
            # e.g. call is `db.execute_query`, import maps `db` -> `models.db`
            # try: models.db.execute_query
            qualified = qualified + "." + ".".join(parts[1:])
        if qualified in node_by_id:
            return qualified

    # 3. Same-module resolution (function calling another in the same file)
    same_module = f"{module_path}.{call_name}" if module_path else call_name
    if same_module in node_by_id:
        return same_module

    return None


# ---------------------------------------------------------------------------
# Step 4: walk function bodies and build edges
# ---------------------------------------------------------------------------

class _FunctionBodyWalker(ast.NodeVisitor):
    """
    Re-walks a file's AST to find function/method definitions
    and extract calls from their bodies.
    Tracks class context identically to FileVisitor so we reconstruct
    the same qualified IDs.
    """

    def __init__(self, module_path: str):
        self.module_path = module_path
        self._class_stack: list[str] = []
        # Maps qualified function id -> list of raw call names found in its body
        self.function_calls: dict[str, list[str]] = {}

    def _qualify(self, name: str) -> str:
        prefix = f"{self.module_path}." if self.module_path else ""
        if self._class_stack:
            return f"{prefix}{'.'.join(self._class_stack)}.{name}"
        return f"{prefix}{name}"

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle(node)

    def _handle(self, node):
        func_id = self._qualify(node.name)
        calls = extract_calls_from_body(node.body)
        self.function_calls[func_id] = calls


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_edges(root: str, graph: Graph, node_by_id: dict[str, Node], src_root: str | None = None) -> None:
    """
    Pass 2: re-parse every file, extract imports + calls,
    resolve calls to node IDs, and add Edge objects to the graph.

    Args:
        root:     Project root — where to find .py files.
        src_root: Source root — where Python module paths start.
                  If None, auto-detected via detect_source_root().

    Modifies graph.edges in place.
    """
    root_path = Path(root).resolve()

    if src_root:
        source_root = Path(src_root).resolve()
    else:
        source_root = detect_source_root(root)

    files = discover_python_files(root)

    seen_edges: set[tuple[str, str]] = set()

    for file_path in files:
        module_path = to_module_path(file_path, source_root)

        try:
            source = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        # Step 1: extract import map for this file
        import_map = extract_imports(tree)

        # Step 2: walk function bodies and extract raw call names
        walker = _FunctionBodyWalker(module_path)
        walker.visit(tree)

        # Step 3: resolve each call and create edges
        for func_id, calls in walker.function_calls.items():
            if func_id not in node_by_id:
                continue  # skip functions we didn't index (shouldn't happen)

            for call_name in calls:
                target_id = _resolve_call(call_name, import_map, module_path, node_by_id)
                if target_id and target_id != func_id:  # skip self-recursion noise
                    edge_key = (func_id, target_id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        graph.edges.append(Edge(
                            source=func_id,
                            target=target_id,
                            edge_type="calls",
                        ))
