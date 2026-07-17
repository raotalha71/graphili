# Graphili

**Static code graph analyzer for Python.** Point it at any Python project and get an interactive, Obsidian-style force-directed graph of your codebase — functions, classes, API endpoints, and the call connections between them. No code execution required.

<img width="959" height="511" alt="image" src="https://github.com/user-attachments/assets/c974d6fc-e618-484e-aabf-cee762ac6ec3" />

<img width="959" height="506" alt="image" src="https://github.com/user-attachments/assets/60ff16ca-068d-4dd2-b555-7ec00f8463c4" />

---

## Features

- **Zero-execution analysis** — Uses Python's `ast` module to parse source code statically. No need to install dependencies, set up databases, or run your project.
- **API endpoint detection** — Automatically identifies FastAPI/Flask-style route decorators (`@router.get`, `@app.post`, etc.) and extracts HTTP method + route path.
- **Call graph resolution** — Traces which functions call which other functions across files via import resolution.
- **Interactive graph UI** — D3.js force-directed visualization with pan, zoom, drag, search, and click-to-inspect.
- **Auto-generated summaries** — Every node gets a human-readable summary built from its metadata (args, return type, connections) — no docstring needed.
- **Stdlib only** — No third-party Python dependencies for the core analyzer. The frontend loads D3.js from CDN.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/raotalha71/graphili.git
cd graphili
```

### 2. Run the CLI (JSON output only)

```bash
python cli.py --path ./tests/tv2/ecommerce --out output/graph.json
```

This scans the project at the given path and writes a structured `graph.json` containing all nodes (functions, classes, APIs) and edges (call connections).

### 3. Launch the interactive UI

```bash
python serve.py --path ./tests/tv2/ecommerce
```

Open **http://localhost:8080** in your browser. That's it.

Use `--port` to change the port:

```bash
python serve.py --path ./tests/tv2/ecommerce --port 9000
```

---

## UI Interactions

| Action | Behavior |
|--------|----------|
| Scroll wheel | Zoom in / out |
| Click + drag background | Pan the graph |
| Click + drag a node | Move that node |
| Click a node | Highlight connections, open details sidebar |
| Type in search bar | Filter nodes by name |
| Press Escape | Clear search |
| Click empty space | Deselect, close sidebar |

---

## Project Structure

```
graphili/
├── analyzer/
│   ├── __init__.py
│   ├── discovery.py       # Finds all .py files, skips junk dirs
│   ├── visitors.py        # AST visitors that extract function/class nodes
│   ├── indexer.py          # Pass 1: builds the complete node index
│   ├── resolver.py         # Pass 2: resolves imports + calls into edges
│   ├── models.py           # Data classes: Node, Edge, Graph
│   └── similarity.py       # (planned) AST hashing for clone detection
│
├── frontend/
│   ├── index.html          # Graph UI page
│   ├── styles.css          # Dark theme styles
│   └── app.js              # D3.js force graph engine
│
├── tests/
├── output/                 # Generated graph JSON files
├── cli.py                  # CLI entry point for JSON-only output
├── serve.py                # Analyzer + HTTP server for the graph UI
├── requirements.txt
└── README.md
```

---

## How It Works

### Pass 1 — Indexing (`indexer.py` + `visitors.py`)

Walks every `.py` file, parses the AST, and extracts:
- Function and class definitions
- Argument names, type hints, return types
- Decorators (used to detect API endpoints)
- Docstrings

Each element becomes a **Node** with a fully-qualified ID like `routes.orders.checkout_cart`.

### Pass 2 — Resolving (`resolver.py`)

Re-parses each file to extract:
- Import statements → builds a name-to-module mapping
- Function calls inside each function body

Resolves each call to a node ID using three strategies:
1. **Direct match** — call name is already a known node ID
2. **Import-based** — resolve via the file's import map (e.g., `reserve_stock` → `services.inventory.reserve_stock`)
3. **Same-module** — fallback to same-file resolution

Each resolved call becomes an **Edge** (`source → target`).

### Pass 3 — Visualization (`serve.py` + `frontend/`)

The Python server runs both passes, serializes the graph to JSON, and serves it at `/api/graph`. The frontend fetches this and renders a D3.js force-directed graph.

---

## Roadmap

- [ ] **Similarity hashing** — Detect structurally identical functions using normalized AST hashing
- [ ] **VS Code extension** — Real-time graph updates on file save, embedded in a Webview panel
- [ ] **pip package** — Install via `pip install graphili` and run `graphili watch --path ./src`
- [ ] **File watcher** — Live re-analysis using `watchdog` when code changes
- [ ] **Multi-language support** — Extend beyond Python (JavaScript/TypeScript via tree-sitter)

---

## Requirements

- Python 3.9+
- No third-party dependencies for the core analyzer (`ast` is stdlib)
- A modern browser for the graph UI

---

## License

MIT
