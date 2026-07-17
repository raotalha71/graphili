"""
v2 entry point. One-shot CLI: point it at a project root, get graph.json out.

Usage:
    python cli.py --path ./tests/sample_project
    python cli.py --path ./tests/sample_project --out output/graph.json
    python cli.py --path ./my_monorepo --src ./my_monorepo/src
"""

import argparse
import json
from pathlib import Path

from analyzer.indexer import build_index
from analyzer.resolver import resolve_edges
from analyzer.discovery import detect_source_root


def main():
    parser = argparse.ArgumentParser(description="Graphili — static code graph analyzer")
    parser.add_argument("--path", required=True, help="Root of the project to analyze")
    parser.add_argument("--out", default="output/graph.json", help="Where to write graph JSON")
    parser.add_argument(
        "--src", default=None,
        help="Source root override (where Python module paths start). "
             "Auto-detected if not provided."
    )
    args = parser.parse_args()

    # Detect or use provided source root
    if args.src:
        src_root = str(Path(args.src).resolve())
        print(f"Source root (manual): {src_root}")
    else:
        src_root_path = detect_source_root(args.path)
        src_root = str(src_root_path)
        project_root = str(Path(args.path).resolve())
        if src_root != project_root:
            print(f"Source root (auto-detected): {src_root}")
        else:
            print(f"Source root: {src_root}")

    print(f"Scanning {args.path} ...")
    graph, node_by_id = build_index(args.path, src_root=src_root)

    # --- Pass 2: resolve imports + calls into edges ---
    print("Resolving edges ...")
    resolve_edges(args.path, graph, node_by_id, src_root=src_root)

    print(f"Found {len(graph.nodes)} nodes total:")
    by_type = {}
    for n in graph.nodes:
        by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
    for t, count in sorted(by_type.items()):
        print(f"  {t:10s} : {count}")

    print(f"\nResolved {len(graph.edges)} edges:")
    for e in graph.edges:
        print(f"  {e.source} --> {e.target}  [{e.edge_type}]")

    api_nodes = [n for n in graph.nodes if n.is_api]
    if api_nodes:
        print(f"\nAPI endpoints detected:")
        for n in api_nodes:
            print(f"  [{n.api_method}] {n.api_route}  ->  {n.id}  (line {n.line_number})")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")
    print(f"\nWrote graph to {out_path}")


if __name__ == "__main__":
    main()
