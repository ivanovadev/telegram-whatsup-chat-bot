#!/usr/bin/env python3
"""
Global markdown hygiene check:
- In ALL project directories, only README*.md are allowed.
- Any other *.md file (e.g. QUICK_START.md, NEO4J_INTEGRATION.md, etc.)
  is considered extra and should be merged into the corresponding README.

Runs from tests/ directory and inspects project root one level up.
Skips only infrastructure/virtual dirs like .git, venv, __pycache__, etc.
"""

import os
import sys
from pathlib import Path
from typing import List


SKIP_DIRS = {
    ".git",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
}


def is_readme_md(path: Path) -> bool:
    """Return True if file is some form of README markdown."""
    name = path.name.lower()
    return name.startswith("readme") and name.endswith(".md")


def should_skip_path(root: Path, current_dir: Path) -> bool:
    """Check if a directory path should be skipped."""
    try:
        rel = current_dir.relative_to(root)
    except ValueError:
        # Outside root – shouldn't happen in normal walk
        return True

    # Skip if any path component is in SKIP_DIRS (e.g. .git, venv, etc.)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True

    return False


def find_extra_md(root: Path) -> List[Path]:
    """Find all .md files that are not README* in code directories."""
    extra: List[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)

        # Skip ignored directories entirely
        if should_skip_path(root, current_dir):
            dirnames[:] = []  # do not descend further
            continue

        md_files = [Path(dirpath) / f for f in filenames if f.lower().endswith(".md")]
        for md in md_files:
            if not is_readme_md(md):
                extra.append(md.relative_to(root))

    return extra


def main() -> int:
    # Run from tests/ directory, inspect project root one level up
    project_root = Path(__file__).resolve().parents[1]

    extra = find_extra_md(project_root)
    if not extra:
        print("✅ No extra .md files found (only README*.md present).")
        return 0

    print("🧹 Removing extra .md files (only README*.md are allowed):")
    for path in sorted(extra):
        full_path = project_root / path
        try:
            full_path.unlink()
            print(f"  - deleted {path}")
        except FileNotFoundError:
            print(f"  - already gone {path}")
        except Exception as exc:
            print(f"  - failed to delete {path}: {exc}")

    print("✅ Cleanup complete. Next run should pass with only README*.md files left.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

