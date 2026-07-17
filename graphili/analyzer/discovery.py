"""
Phase: Discovery.
Finds every .py file under a project root, skipping junk directories.
Also auto-detects the Python source root (where module paths start)
so that import resolution works on any project structure.

Supports:
  - Standard flat layout:       my_project/routes/users.py
  - src/ layout:                my_project/src/backend/routes/users.py
  - pyproject.toml configured:  [tool.setuptools.packages.find] where = ["src"]
  - setup.cfg configured:       [options.packages.find] where = src
  - Manual override via --src flag
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


def to_module_path(file_path: Path, src_root: Path) -> str:
    """
    Converts a file path into a dotted module path relative to the source root.

    The source root is the directory from which Python computes import paths.
    For a standard project, this is the project root.
    For a src/ layout, this is the src/ directory.

    e.g. src_root=/proj/src, file=/proj/src/backend/routes/users.py
         -> "backend.routes.users"
    """
    rel = file_path.resolve().relative_to(src_root.resolve())
    parts = list(rel.parts)
    parts[-1] = parts[-1].removesuffix(".py")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Source root auto-detection
# ---------------------------------------------------------------------------

def detect_source_root(project_root: str) -> Path:
    """
    Auto-detect where Python module paths start for a project.

    Detection strategy (in priority order):
      1. pyproject.toml — look for [tool.setuptools.packages.find] where = [...]
      2. setup.cfg — look for [options.packages.find] where = ...
      3. src/ heuristic — if a src/ dir exists with packages inside, use it
      4. __init__.py boundary — if top-level dirs ARE packages, root is source root
      5. Fallback — use project root as-is

    Returns the absolute Path to the source root directory.
    """
    root = Path(project_root).resolve()

    # Strategy 1: pyproject.toml
    result = _check_pyproject_toml(root)
    if result:
        return result

    # Strategy 2: setup.cfg
    result = _check_setup_cfg(root)
    if result:
        return result

    # Strategy 3: src/ heuristic
    result = _check_src_directory(root)
    if result:
        return result

    # Strategy 4: __init__.py boundary check
    # If top-level directories already ARE packages (have __init__.py),
    # then the project root IS the correct source root.
    # This is the standard "flat" layout — no changes needed.
    # If NO top-level dir is a package, check one level deeper.
    result = _check_init_boundary(root)
    if result:
        return result

    # Strategy 5: fallback — project root
    return root


def _check_pyproject_toml(root: Path) -> Path | None:
    """
    Parse pyproject.toml for setuptools package discovery config.

    Looks for:
        [tool.setuptools.packages.find]
        where = ["src"]
    """
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None

    try:
        content = toml_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Lightweight TOML parsing — we only need the `where` value.
    # Full TOML parsing requires tomllib (3.11+) or third-party lib.
    # We handle both formats: where = ["src"] and where = src
    import re

    # Look for the [tool.setuptools.packages.find] section
    section_match = re.search(
        r'\[tool\.setuptools\.packages\.find\]',
        content
    )
    if not section_match:
        return None

    # Extract everything after the section header until next section or EOF
    section_start = section_match.end()
    next_section = re.search(r'\n\[', content[section_start:])
    section_end = section_start + next_section.start() if next_section else len(content)
    section_content = content[section_start:section_end]

    # Find where = ["src"] or where = ["src", "lib"]
    where_match = re.search(
        r'where\s*=\s*\[([^\]]+)\]',
        section_content
    )
    if where_match:
        # Parse the list: "src", "lib" -> ["src", "lib"]
        items = re.findall(r'"([^"]+)"|\'([^\']+)\'', where_match.group(1))
        dirs = [a or b for a, b in items]
        if dirs:
            candidate = root / dirs[0]
            if candidate.is_dir():
                return candidate.resolve()

    return None


def _check_setup_cfg(root: Path) -> Path | None:
    """
    Parse setup.cfg for [options.packages.find] where = src
    """
    cfg_path = root / "setup.cfg"
    if not cfg_path.exists():
        return None

    try:
        content = cfg_path.read_text(encoding="utf-8")
    except OSError:
        return None

    import re

    # Look for [options.packages.find] section
    section_match = re.search(
        r'\[options\.packages\.find\]',
        content
    )
    if not section_match:
        return None

    section_start = section_match.end()
    next_section = re.search(r'\n\[', content[section_start:])
    section_end = section_start + next_section.start() if next_section else len(content)
    section_content = content[section_start:section_end]

    where_match = re.search(r'where\s*=\s*(\S+)', section_content)
    if where_match:
        dir_name = where_match.group(1).strip()
        candidate = root / dir_name
        if candidate.is_dir():
            return candidate.resolve()

    return None


def _check_src_directory(root: Path) -> Path | None:
    """
    If a src/ directory exists and contains Python packages
    (directories with __init__.py) or .py files, use it as source root.
    """
    src_dir = root / "src"
    if not src_dir.is_dir():
        return None

    # Check if src/ contains any packages (dirs with __init__.py)
    for child in src_dir.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            return src_dir.resolve()

    # Check if src/ contains any .py files directly
    if any(src_dir.glob("*.py")):
        return src_dir.resolve()

    return None


def _check_init_boundary(root: Path) -> Path | None:
    """
    Walk top-level children to find the package boundary.

    If ANY top-level dir has __init__.py, project root is the source root
    (standard flat layout — this returns root, same as fallback).

    If NO top-level dir has __init__.py, check common subdirectory names
    (lib/, app/, etc.) for packages inside them.
    """
    has_top_level_package = False

    for child in root.iterdir():
        if child.is_dir() and child.name not in DEFAULT_IGNORE_DIRS:
            if (child / "__init__.py").exists():
                has_top_level_package = True
                break

    if has_top_level_package:
        # Standard flat layout — root IS the source root
        return root

    # No top-level package found. Check common subdirectories.
    common_src_dirs = ["lib", "app", "packages"]
    for dir_name in common_src_dirs:
        candidate = root / dir_name
        if candidate.is_dir():
            for child in candidate.iterdir():
                if child.is_dir() and (child / "__init__.py").exists():
                    return candidate.resolve()

    return None
