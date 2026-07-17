"""
Graphili — Local dev server.

Runs the analyzer pipeline on a project, then serves the graph UI.

Usage:
    python serve.py --path ./tests/tv2/ecommerce
    python serve.py --path ./tests/tv2/ecommerce --port 9000
"""

import argparse
import json
import http.server
from pathlib import Path

from analyzer.indexer import build_index
from analyzer.resolver import resolve_edges
from analyzer.discovery import detect_source_root


class GraphHandler(http.server.BaseHTTPRequestHandler):
    """
    Serves the frontend static files and the graph JSON API.
    Class-level attributes are set by main() before the server starts.
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
        # Quieter logs — just method + path
        if args:
            print(f"  {args[0]}")


def main():
    parser = argparse.ArgumentParser(
        description="Graphili — analyze a project and launch the graph UI"
    )
    parser.add_argument(
        "--path", required=True,
        help="Root of the Python project to analyze"
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port to serve on (default: 8080)"
    )
    parser.add_argument(
        "--src", default=None,
        help="Source root override (where Python module paths start). "
             "Auto-detected if not provided."
    )
    args = parser.parse_args()

    project_path = args.path

    # ── Detect source root ─────────────────────────────────
    if args.src:
        src_root = str(Path(args.src).resolve())
        print(f"\n  Source root (manual): {src_root}")
    else:
        src_root_path = detect_source_root(project_path)
        src_root = str(src_root_path)
        project_resolved = str(Path(project_path).resolve())
        if src_root != project_resolved:
            print(f"\n  Source root (auto-detected): {src_root}")

    # ── Run analyzer pipeline ──────────────────────────────
    print(f"  Analyzing {project_path} ...")
    graph, node_by_id = build_index(project_path, src_root=src_root)
    resolve_edges(project_path, graph, node_by_id, src_root=src_root)

    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    api_count  = sum(1 for n in graph.nodes if n.is_api)

    print(f"  Found {node_count} nodes, {edge_count} edges, {api_count} API endpoints\n")

    # ── Configure handler ──────────────────────────────────
    GraphHandler.graph_json  = json.dumps(graph.to_dict())
    GraphHandler.frontend_dir = str(Path(__file__).parent / "frontend")
    GraphHandler.project_path = project_path
    GraphHandler.src_root = src_root

    # ── Start server ───────────────────────────────────────
    server = http.server.HTTPServer(("localhost", args.port), GraphHandler)

    print()
    print("  +--------------------------------------------+")
    print("  |                                            |")
    print("  |   Graphili is running!                     |")
    print("  |                                            |")
    print(f"  |   Open:  http://localhost:{args.port}            |")
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


if __name__ == "__main__":
    main()
