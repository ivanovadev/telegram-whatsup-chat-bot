#!/usr/bin/env python3
"""
Generate project structure tree and update README.md.

This script:
1. Scans the project directory structure
2. Generates a markdown tree representation
3. Updates the Architecture section in README.md
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Set


# Directories and files to ignore
IGNORE_PATTERNS = {
    '__pycache__', '.git', '.venv', 'venv', 'node_modules', '.pytest_cache',
    '.mypy_cache', '.DS_Store', '*.pyc', '*.pyo', '*.db', '*.db-journal',
    '*.session', '*.session-journal', '.env', 'data', '.idea', '.vscode',
    '*.swp', '*.swo', 'Thumbs.db', 'what-is-not-work-well.json'
}

# Files to always include (even if in ignore patterns)
ALWAYS_INCLUDE = {
    'requirements.txt', 'README.md', '.env.example', 'run.sh', 'MANUAL_CONTROL.md',
    'pytest.ini', '.gitignore'
}

# Directories to show contents of (with limited depth)
SHOW_CONTENTS = {
    'auto-reply-service', 'group-posts-service', 'channel-posts-service',
    'shared_services', 'tests'
}

# Maximum depth for directory traversal
MAX_DEPTH = 4


def should_ignore(name: str, is_dir: bool = False) -> bool:
    """Check if file/directory should be ignored."""
    if name in ALWAYS_INCLUDE:
        return False
    
    # Check ignore patterns
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    
    # Ignore hidden files (except .env.example)
    if name.startswith('.') and name != '.env.example':
        return True
    
    return False


def get_tree_structure(root: Path, prefix: str = "", is_last: bool = True, depth: int = 0, base_name: str = "") -> List[str]:
    """Generate tree structure recursively."""
    lines = []
    
    if depth == 0:
        # Root level
        lines.append(f"{base_name}/")
    else:
        # Directory entry
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{base_name}/")
        prefix = prefix + ("    " if is_last else "│   ")
    
    if depth >= MAX_DEPTH:
        return lines
    
    try:
        items = sorted([item for item in root.iterdir() if not should_ignore(item.name, item.is_dir())])
        
        # Separate directories and files
        dirs = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]
        
        # Process directories first
        for i, item in enumerate(dirs):
            is_last_item = (i == len(dirs) - 1) and len(files) == 0
            sub_lines = get_tree_structure(
                item, prefix, is_last_item, depth + 1, item.name
            )
            lines.extend(sub_lines)
        
        # Process files
        for i, item in enumerate(files):
            is_last_item = i == len(files) - 1
            connector = "└── " if is_last_item else "├── "
            lines.append(f"{prefix}{connector}{item.name}")
    
    except PermissionError:
        pass
    
    return lines


def generate_structure_tree(project_root: Path) -> str:
    """Generate complete project structure tree."""
    lines = []
    lines.append("```")
    lines.append("telegram-whatsup-chat-bot/")
    
    # Get top-level items
    try:
        items = sorted([
            item for item in project_root.iterdir()
            if not should_ignore(item.name, item.is_dir())
            and item.name not in ['README.md', 'MANUAL_CONTROL.md', 'DIRECTORY_ANALYSIS.md', 'ARCHITECTURE_ANALYSIS.md']
        ])
        
        # Separate directories and files
        dirs = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]
        
        # Process important directories with details
        for i, item in enumerate(dirs):
            is_last = (i == len(dirs) - 1) and len(files) == 0
            
            if item.name in SHOW_CONTENTS:
                # Show contents for important directories
                sub_lines = get_tree_structure(item, "", is_last, 1, item.name)
                lines.extend(sub_lines)
            else:
                # Just show directory name
                connector = "└── " if is_last and len(files) == 0 else "├── "
                lines.append(f"{connector}{item.name}/")
        
        # Process root-level files
        for i, item in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{connector}{item.name}")
        
        # Always include README.md and MANUAL_CONTROL.md at the end
        if 'README.md' not in [f.name for f in files]:
            lines.append("├── README.md")
        if 'MANUAL_CONTROL.md' not in [f.name for f in files]:
            if 'README.md' not in [f.name for f in files]:
                lines.append("└── MANUAL_CONTROL.md")
            else:
                lines.append("└── MANUAL_CONTROL.md")
    
    except Exception as e:
        print(f"Error generating structure: {e}", file=sys.stderr)
        return ""
    
    lines.append("```")
    return "\n".join(lines)


def update_readme_structure(readme_path: Path, new_structure: str) -> bool:
    """Update the Architecture section in README.md."""
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the Architecture section
        # Pattern: ## 🏗️ Architecture followed by ``` ... ```
        pattern = r'(## 🏗️ Architecture\s*\n\s*```\s*\n)(.*?)(\n```)'
        
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            print("❌ Could not find Architecture section in README.md", file=sys.stderr)
            return False
        
        # Extract structure from new_structure (remove ``` markers)
        structure_lines = new_structure.split('\n')
        if structure_lines[0] == '```':
            structure_lines = structure_lines[1:]
        if structure_lines[-1] == '```':
            structure_lines = structure_lines[:-1]
        structure_content = '\n'.join(structure_lines)
        
        # Replace the structure
        new_content = content[:match.start()] + match.group(1) + structure_content + match.group(3) + content[match.end():]
        
        # Write back
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"❌ Error updating README.md: {e}", file=sys.stderr)
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1]).resolve()
    else:
        # Default to parent of tests/ directory
        script_dir = Path(__file__).parent.resolve()
        project_root = script_dir.parent
    
    if not project_root.exists():
        print(f"❌ Error: Project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)
    
    readme_path = project_root / "README.md"
    if not readme_path.exists():
        print(f"❌ Error: README.md not found: {readme_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📁 Scanning project structure: {project_root}")
    
    # Generate structure
    structure_tree = generate_structure_tree(project_root)
    
    if not structure_tree:
        print("❌ Failed to generate structure tree", file=sys.stderr)
        sys.exit(1)
    
    # Update README
    if update_readme_structure(readme_path, structure_tree):
        print(f"✅ Updated Architecture section in README.md")
        sys.exit(0)
    else:
        print("❌ Failed to update README.md", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
