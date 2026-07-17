"""
Graphili — Static Code Graph Analyzer.

Single entry point for all Graphili operations.

Usage:
    # Launch the interactive graph UI (default)
    python run.py --path ./tests/tv2/ecommerce

    # Export graph as JSON only (no server)
    python run.py --path ./tests/tv2/ecommerce --export output/graph.json

    # Specify a custom port for the UI
    python run.py --path ./tests/tv2/ecommerce --port 9000

    # Override the source root for monorepos / src layouts
    python run.py --path ./my_monorepo --src ./my_monorepo/src
"""

import argparse
import json
import http.server
from pathlib import Path

from .analyzer.indexer import build_index
from .analyzer.resolver import resolve_edges
from .analyzer.discovery import detect_source_root


# ═══════════════════════════════════════════════════════════════
#  HTTP Handler — serves frontend + graph API
# ═══════════════════════════════════════════════════════════════

class GraphHandler(http.server.BaseHTTPRequestHandler):
    """
    Serves the frontend static files and the graph JSON API.
    Class-level attributes are set before the server starts.
    """
    graph_json: str = "{}"
    frontend_dir: str = ""
    project_path: str = ""
    src_root: str = ""

    def do_GET(self):
        # API endpoint → return graph JSON
        if self.path == "/api/graph":
            self._send_json(self.graph_json)
            return

        # Static file serving from frontend/
        req_path = self.path.lstrip("/")
        if req_path == "" or req_path == "index.html":
            req_path = "index.html"

        file_path = Path(self.frontend_dir) / req_path

        if file_path.exists() and file_path.is_file():
            content = file_path.read_bytes()
            content_type = self._guess_type(file_path.suffix)
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, f"File not found: {req_path}")

    def do_POST(self):
        if self.path == "/api/refresh":
            print(f"\n  [Refresh] Re-analyzing {GraphHandler.project_path} ...")
            graph, node_by_id = build_index(GraphHandler.project_path, src_root=GraphHandler.src_root)
            resolve_edges(GraphHandler.project_path, graph, node_by_id, src_root=GraphHandler.src_root)
            GraphHandler.graph_json = json.dumps(graph.to_dict())

            node_count = len(graph.nodes)
            edge_count = len(graph.edges)
            api_count  = sum(1 for n in graph.nodes if n.is_api)
            print(f"  [Refresh] Found {node_count} nodes, {edge_count} edges, {api_count} API endpoints\n")

            self._send_json('{"status": "ok"}')
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, json_str: str):
        data = json_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _guess_type(ext: str) -> str:
        return {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".png":  "image/png",
            ".svg":  "image/svg+xml",
            ".ico":  "image/x-icon",
        }.get(ext, "application/octet-stream")

    def log_message(self, format, *args):
        if args:
            print(f"  {args[0]}")


# ═══════════════════════════════════════════════════════════════
#  Core pipeline — shared by both modes
# ═══════════════════════════════════════════════════════════════

def run_analysis(project_path: str, src_override: str | None = None):
    """
    Run the full Graphili analysis pipeline.

    Returns: (graph, node_by_id, src_root)
    """
    # ── Detect source root ─────────────────────────────────
    if src_override:
        src_root = str(Path(src_override).resolve())
        print(f"  Source root (manual): {src_root}")
    else:
        src_root_path = detect_source_root(project_path)
        src_root = str(src_root_path)
        project_resolved = str(Path(project_path).resolve())
        if src_root != project_resolved:
            print(f"  Source root (auto-detected): {src_root}")
        else:
            print(f"  Source root: {src_root}")

    # ── Pass 1: Index ──────────────────────────────────────
    print(f"  Scanning {project_path} ...")
    graph, node_by_id = build_index(project_path, src_root=src_root)

    # ── Pass 2: Resolve ────────────────────────────────────
    print("  Resolving edges ...")
    resolve_edges(project_path, graph, node_by_id, src_root=src_root)

    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    api_count  = sum(1 for n in graph.nodes if n.is_api)
    print(f"  Found {node_count} nodes, {edge_count} edges, {api_count} API endpoints\n")

    return graph, node_by_id, src_root


# ═══════════════════════════════════════════════════════════════
#  Mode 1: Export — write JSON and exit
# ═══════════════════════════════════════════════════════════════

def mode_export(project_path: str, export_path: str, src_override: str | None = None):
    """Analyze the project and write the graph to a JSON file."""
    graph, node_by_id, _ = run_analysis(project_path, src_override)

    # ── Print detailed report ──────────────────────────────
    by_type = {}
    for n in graph.nodes:
        by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
    for t, count in sorted(by_type.items()):
        print(f"  {t:10s} : {count}")

    print(f"\n  Edges:")
    for e in graph.edges:
        print(f"    {e.source} --> {e.target}  [{e.edge_type}]")

    api_nodes = [n for n in graph.nodes if n.is_api]
    if api_nodes:
        print(f"\n  API endpoints:")
        for n in api_nodes:
            print(f"    [{n.api_method}] {n.api_route}  ->  {n.id}  (line {n.line_number})")

    # ── Write JSON ─────────────────────────────────────────
    out_path = Path(export_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")
    print(f"\n  Wrote graph to {out_path}")


# ═══════════════════════════════════════════════════════════════
#  Mode 2: Serve — launch the interactive graph UI
# ═══════════════════════════════════════════════════════════════

def mode_serve(project_path: str, port: int, src_override: str | None = None):
    """Analyze the project and launch the graph UI server."""
    graph, node_by_id, src_root = run_analysis(project_path, src_override)

    # ── Configure handler ──────────────────────────────────
    GraphHandler.graph_json   = json.dumps(graph.to_dict())
    GraphHandler.frontend_dir = str(Path(__file__).parent / "frontend")
    GraphHandler.project_path = project_path
    GraphHandler.src_root     = src_root

    # ── Start server ───────────────────────────────────────
    server = http.server.HTTPServer(("localhost", port), GraphHandler)

    print()
    print("  +--------------------------------------------+")
    print("  |                                            |")
    print("  |   Graphili is running!                     |")
    print("  |                                            |")
    print(f"  |   Open:  http://localhost:{port}            |")
    print("  |                                            |")
    print("  |   Press Ctrl+C to stop                     |")
    print("  |                                            |")
    print("  +--------------------------------------------+")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down ...")
        server.server_close()


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Graphili — Static Code Graph Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --path ./my_project                     Launch the graph UI
  python run.py --path ./my_project --export graph.json Export JSON only
  python run.py --path ./my_project --port 9000         Custom port
  python run.py --path ./monorepo --src ./monorepo/src  Override source root
        """
    )
    parser.add_argument(
        "--path", default=".",
        help="Root of the Python project to analyze (defaults to current directory)"
    )
    parser.add_argument(
        "--export", default=None, metavar="FILE",
        help="Export graph as JSON to FILE and exit (no server). "
             "If omitted, launches the interactive graph UI instead."
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port to serve the UI on (default: 8080)"
    )
    parser.add_argument(
        "--src", default=None,
        help="Source root override (where Python module paths start). "
             "Auto-detected if not provided."
    )
    args = parser.parse_args()

    print()
    print("  Graphili v1.05")
    print("  ------------------------------------------")

    if args.export:
        mode_export(args.path, args.export, args.src)
    else:
        mode_serve(args.path, args.port, args.src)


if __name__ == "__main__":
    main()
