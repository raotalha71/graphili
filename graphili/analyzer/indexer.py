"""
Pass 1: build the complete node index across the whole project.
This must finish fully before resolver.py (Pass 2) tries to build edges --
you can't resolve a call to a function you haven't indexed yet.
"""

from pathlib import Path

from .discovery import discover_python_files, to_module_path, detect_source_root
from .visitors import extract_nodes_from_source
from .models import Graph, Node


def build_index(root: str, src_root: str | None = None) -> tuple[Graph, dict[str, Node]]:
    """
    Scan all .py files under `root`, extract nodes from each.

    Args:
        root:     Project root — where to find .py files.
        src_root: Source root — where Python module paths start.
                  If None, auto-detected via detect_source_root().
    """
    root_path = Path(root).resolve()

    if src_root:
        source_root = Path(src_root).resolve()
    else:
        source_root = detect_source_root(root)

    files = discover_python_files(root)

    graph = Graph()
    node_by_id: dict[str, Node] = {}

    for file_path in files:
        module_path = to_module_path(file_path, source_root)
        rel_path = str(file_path.resolve().relative_to(root_path))

        try:
            source = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"  [skip] could not read {rel_path}: {e}")
            continue

        try:
            nodes = extract_nodes_from_source(source, module_path, rel_path)
        except SyntaxError as e:
            print(f"  [skip] syntax error in {rel_path}: {e}")
            continue

        for node in nodes:
            if node.id in node_by_id:
                # duplicate qualified id -- shouldn't normally happen, flag it
                print(f"  [warn] duplicate node id: {node.id} (in {rel_path})")
            node_by_id[node.id] = node
            graph.nodes.append(node)

    return graph, node_by_id
