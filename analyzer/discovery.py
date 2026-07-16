"""
Phase: Discovery.
Finds every .py file under a project root, skipping junk directories.
This is deliberately dumb and separate from indexing -- it only answers
"which files exist", not "what's inside them".
"""

from pathlib import Path

DEFAULT_IGNORE_DIRS = {
    "venv", ".venv", "env",
    "__pycache__", ".git", ".hg", ".svn",
    "node_modules", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".tox",
    "site-packages", "migrations",  # migrations often auto-generated noise
}


def discover_python_files(root: str, extra_ignore: set[str] | None = None) -> list[Path]:
    root_path = Path(root).resolve()
    ignore = DEFAULT_IGNORE_DIRS | (extra_ignore or set())

    files = []
    for path in root_path.rglob("*.py"):
        if any(part in ignore for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def to_module_path(file_path: Path, root: Path) -> str:
    """
    Converts a file path into a dotted module path relative to root.
    e.g. root=/proj, file=/proj/routes/students.py -> "routes.students"
    """
    rel = file_path.resolve().relative_to(root.resolve())
    parts = list(rel.parts)
    parts[-1] = parts[-1].removesuffix(".py")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)
