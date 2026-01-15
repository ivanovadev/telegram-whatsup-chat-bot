#!/usr/bin/env python3
"""
README Validator and Auto-Corrector

This script checks README files for:
- Proper markdown formatting
- Consistent header structure
- Trailing whitespace
- Multiple blank lines
- Missing required sections
- Broken internal structure
- Code block formatting (language tags, unclosed blocks)
- Structure validation (files/dirs mentioned actually exist)
- Heading hierarchy (no skipped levels)
- Consistent bullet point style
- TODO/FIXME comments
- Empty sections
- Broken markdown links
- Auto-generate and update project structure in README
- Validate and update Available commands section

Usage:
    python3 check_readme.py                    # Check only
    python3 check_readme.py --fix              # Check and auto-fix
    python3 check_readme.py --path dir/        # Check specific directory
    python3 check_readme.py --check-structure  # Validate structure references
    python3 check_readme.py --update-structure # Generate and update project structure
    python3 check_readme.py --update-commands  # Update Available commands from code
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Set


class ReadmeChecker:
    """Check and fix README files."""
    
    def __init__(self, root_path: str, fix: bool = False, check_structure: bool = False, update_structure: bool = False, update_commands: bool = False):
        self.root_path = Path(root_path).resolve()
        self.fix = fix
        self.check_structure = check_structure
        self.update_structure = update_structure
        self.update_commands = update_commands
        self.issues_found = 0
        self.files_checked = 0
        self.files_fixed = 0
        self.structure_issues = 0
        
    def find_readme_files(self) -> List[Path]:
        """Find all README.md files in the project."""
        readme_files = []
        for root, dirs, files in os.walk(self.root_path):
            # Skip virtual environments and cache directories
            dirs[:] = [d for d in dirs if d not in {'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache'}]
            
            for file in files:
                if file.lower() == 'readme.md':
                    readme_files.append(Path(root) / file)
        
        return sorted(readme_files)
    
    def check_and_fix_file(self, filepath: Path) -> Tuple[List[str], bool]:
        """
        Check and optionally fix a README file.
        
        Returns:
            (list of issues, whether file was modified)
        """
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            return ([f"❌ Cannot read file: {e}"], False)
        
        content = original_content
        modified = False
        
        # Check 1: Trailing whitespace
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line and line.strip():  # Has trailing whitespace
                issues.append(f"Line {i}: Trailing whitespace")
                new_lines.append(line.rstrip())
                modified = True
            else:
                new_lines.append(line)
        
        if modified:
            content = '\n'.join(new_lines)
        
        # Check 2: Multiple consecutive blank lines (more than 2)
        old_content = content
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        if content != old_content:
            issues.append("Multiple consecutive blank lines (>3)")
            modified = True
        
        # Check 3: File should end with single newline
        if content and not content.endswith('\n'):
            issues.append("Missing final newline")
            content += '\n'
            modified = True
        elif content.endswith('\n\n'):
            issues.append("Multiple trailing newlines")
            content = content.rstrip('\n') + '\n'
            modified = True
        
        # Check 4: Code blocks should have language tags
        code_blocks_without_lang = re.findall(r'\n```\n', content)
        if code_blocks_without_lang:
            issues.append(f"Found {len(code_blocks_without_lang)} code block(s) without language tag")
        
        # Check 5: Inconsistent header spacing
        # Headers should have blank line before (except first line and after another header)
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            if i > 0 and line.startswith('#') and not line.startswith('```'):
                prev_line = lines[i-1].strip()
                # If previous line is not empty and not a header
                if prev_line and not prev_line.startswith('#'):
                    issues.append(f"Header at line {i+1} should have blank line before it")
                    if self.fix:
                        new_lines.append('')
                        modified = True
            new_lines.append(line)
        
        if modified and self.fix:
            content = '\n'.join(new_lines)
        
        # Check 6: Title should be H1 (single #)
        lines = content.split('\n')
        first_header_line = None
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                first_header_line = (i, line)
                break
        
        if first_header_line:
            line_num, line = first_header_line
            if not line.strip().startswith('# ') or line.strip().startswith('## '):
                issues.append(f"First header should be H1 (single #)")
        
        # Check 7: Headers should have space after #
        for i, line in enumerate(lines, 1):
            if line.startswith('#') and not line.startswith('```'):
                # Count leading #
                hash_count = len(line) - len(line.lstrip('#'))
                after_hash = line[hash_count:]
                if after_hash and not after_hash.startswith(' '):
                    issues.append(f"Line {i}: Header should have space after #")
        
        # Check 8: List items should have space after marker
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith('-') or stripped.startswith('*'):
                if len(stripped) > 1 and stripped[1] != ' ':
                    issues.append(f"Line {i}: List item should have space after marker")
        
        # Check 9: Unclosed code blocks
        code_block_count = content.count('```')
        if code_block_count % 2 != 0:
            issues.append(f"Unclosed code block detected (found {code_block_count} backtick fences)")
        
        # Check 10: Consistent bullet point style (all - or all *, not mixed in same section)
        bullet_lines = []
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith('- ') or stripped.startswith('* '):
                bullet_lines.append((i, stripped[0]))
        
        if bullet_lines:
            # Check if there's mixing within proximity (same list)
            for i in range(len(bullet_lines) - 1):
                line_num1, char1 = bullet_lines[i]
                line_num2, char2 = bullet_lines[i + 1]
                # If lines are close together (within 2 lines) and use different markers
                if abs(line_num2 - line_num1) <= 2 and char1 != char2:
                    issues.append(f"Line {line_num2}: Inconsistent bullet style (mixing - and *)")
                    break
        
        # Check 11: Heading hierarchy (no skipped levels)
        heading_levels = []
        for i, line in enumerate(lines, 1):
            if line.startswith('#') and not line.startswith('```'):
                level = len(line) - len(line.lstrip('#'))
                if level <= 6:  # Valid heading levels
                    heading_levels.append((i, level))
        
        for i in range(len(heading_levels) - 1):
            line_num1, level1 = heading_levels[i]
            line_num2, level2 = heading_levels[i + 1]
            # Check if we skip more than one level
            if level2 > level1 + 1:
                issues.append(f"Line {line_num2}: Skipped heading level (H{level1} → H{level2})")
        
        # Check 12: TODO/FIXME/XXX comments in documentation
        todo_pattern = re.compile(r'\b(TODO|FIXME|XXX|HACK|BUG)\b', re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            if todo_pattern.search(line):
                issues.append(f"Line {i}: Contains TODO/FIXME comment")
        
        # Check 13: Empty sections (heading followed by another heading with no content)
        for i in range(len(lines) - 1):
            if lines[i].startswith('#') and not lines[i].startswith('```'):
                # Check next non-empty line
                next_line_idx = i + 1
                while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                    next_line_idx += 1
                
                if next_line_idx < len(lines):
                    next_line = lines[next_line_idx]
                    if next_line.startswith('#') and not next_line.startswith('```'):
                        issues.append(f"Line {i+1}: Empty section (heading with no content)")
        
        # Check 14: Broken markdown links [text](url)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        for i, line in enumerate(lines, 1):
            matches = link_pattern.findall(line)
            for text, url in matches:
                # Check for common issues
                if not url.strip():
                    issues.append(f"Line {i}: Empty link URL for '{text}'")
                elif url.startswith('http') and ' ' in url:
                    issues.append(f"Line {i}: Link URL contains spaces")
        
        # Fix tree structures if requested and structure checking is enabled
        tree_fixes = 0
        if self.fix and self.check_structure:
            content, tree_fixes = self.fix_tree_structures(filepath, content)
            if tree_fixes > 0:
                issues.append(f"Auto-fixed {tree_fixes} tree structure(s) to match filesystem")
                modified = True
        
        # Apply fix if requested
        if self.fix and modified:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return (issues, True)
            except Exception as e:
                issues.append(f"❌ Cannot write file: {e}")
                return (issues, False)
        
        return (issues, False)
    
    def extract_file_references(self, content: str, readme_dir: Path) -> Set[str]:
        """Extract file and directory references from README content."""
        references = set()
        
        # Pattern 1: File paths in code blocks (e.g., app/main.py, handlers/inbox.py)
        # Match paths like: app/main.py, services/channel_handler.py, etc.
        file_patterns = [
            r'(?:^|\s)([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]+)+)',  # path/to/file.ext
            r'`([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]+)+)`',        # `path/to/file`
            r'├── ([a-zA-Z0-9_.-]+)',                          # Tree structure
            r'└── ([a-zA-Z0-9_.-]+)',                          # Tree structure
            r'│\s+├── ([a-zA-Z0-9_.-]+)',                     # Tree structure nested
            r'│\s+└── ([a-zA-Z0-9_.-]+)',                     # Tree structure nested
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                # Skip common non-file patterns
                if any(skip in match for skip in ['http://', 'https://', '://', '@', 'example.com']):
                    continue
                # Skip if it looks like a command or variable
                if match.startswith('$') or match.startswith('-'):
                    continue
                references.add(match)
        
        return references
    
    def parse_tree_structure(self, content: str) -> Dict[str, List[str]]:
        """
        Parse directory tree structures from README.
        Returns dict of {directory_path: [files in that directory]}
        """
        structures = {}
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for lines ending with / that could be a directory root
            if line.strip().endswith('/') and not line.strip().startswith('#'):
                base_dir = line.strip().rstrip('/')
                
                # Check if next line has tree structure
                if i + 1 < len(lines) and ('├──' in lines[i + 1] or '└──' in lines[i + 1]):
                    i += 1  # Move to first tree line
                    
                    # Parse the tree starting from this base directory
                    current_path_stack = [base_dir]
                    
                    while i < len(lines) and ('├──' in lines[i] or '└──' in lines[i] or '│' in lines[i]):
                        tree_line = lines[i]
                        
                        # Calculate indent level (count leading spaces and │ chars)
                        stripped = tree_line.lstrip()
                        indent_chars = len(tree_line) - len(stripped)
                        
                        # Extract item name
                        item = None
                        if '├──' in tree_line:
                            item = tree_line.split('├──', 1)[-1].strip()
                        elif '└──' in tree_line:
                            item = tree_line.split('└──', 1)[-1].strip()
                        
                        if item:
                            # Remove comments
                            item = item.split('#')[0].strip()
                            
                            # Count the depth by looking at '│' characters and indentation
                            depth = tree_line.count('│')
                            
                            # Adjust path stack to current depth
                            while len(current_path_stack) > depth + 1:
                                current_path_stack.pop()
                            
                            parent_path = '/'.join(current_path_stack)
                            
                            if item.endswith('/'):
                                # It's a directory
                                dir_name = item.rstrip('/')
                                full_path = f"{parent_path}/{dir_name}"
                                current_path_stack.append(dir_name)
                                if full_path not in structures:
                                    structures[full_path] = []
                            else:
                                # It's a file
                                if parent_path not in structures:
                                    structures[parent_path] = []
                                structures[parent_path].append(item)
                        
                        i += 1
                    continue
            
            i += 1
        
        return structures
    
    def validate_tree_structure(self, filepath: Path, structures: Dict[str, List[str]]) -> List[str]:
        """Validate that documented tree structures match actual directories."""
        issues = []
        
        readme_dir = filepath.parent
        
        for dir_path, documented_files in structures.items():
            # Try multiple possible locations for the directory
            possible_dirs = [
                readme_dir / dir_path,
                self.root_path / dir_path,
            ]
            
            actual_dir = None
            for pdir in possible_dirs:
                if pdir.exists() and pdir.is_dir():
                    actual_dir = pdir
                    break
            
            if not actual_dir:
                continue  # Directory itself doesn't exist, skip validation
            
            # Get actual files in the directory
            try:
                actual_files = set()
                for item in actual_dir.iterdir():
                    if item.name not in {'__pycache__', '__init__.py', '.DS_Store'}:
                        actual_files.add(item.name)
            except PermissionError:
                continue
            
            # Compare documented vs actual
            documented_set = set(documented_files)
            
            # Find files that are documented but don't exist
            missing_in_fs = documented_set - actual_files
            for missing_file in missing_in_fs:
                # Skip if it's a placeholder
                if '...' in missing_file or 'example' in missing_file.lower():
                    continue
                issues.append(f"📁 {dir_path}/{missing_file} - documented but doesn't exist")
            
            # Find files that exist but aren't documented
            missing_in_docs = actual_files - documented_set
            # Only report significant files (not common extras)
            significant_missing = [f for f in missing_in_docs 
                                  if not f.startswith('.') 
                                  and f.endswith(('.py', '.js', '.ts', '.md', '.sh'))]
            
            for undoc_file in significant_missing:
                issues.append(f"📝 {dir_path}/{undoc_file} - exists but not documented")
        
        return issues
    
    def generate_tree_structure(self, base_dir: Path, max_depth: int = 3) -> str:
        """Generate tree structure string for a directory.
        
        Args:
            base_dir: Directory to generate tree for
            max_depth: Maximum depth to traverse
            
        Returns:
            Tree structure as string
        """
        lines = []
        
        def add_tree_lines(current_dir: Path, prefix: str = "", depth: int = 0):
            """Recursively add tree lines."""
            if depth >= max_depth:
                return
            
            try:
                items = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                # Filter out unwanted items
                items = [item for item in items if item.name not in {
                    '__pycache__', '.DS_Store', 'venv', '.git', 
                    'node_modules', '.pytest_cache', '__init__.py'
                }]
                
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    extension_prefix = "    " if is_last else "│   "
                    
                    if item.is_dir():
                        lines.append(f"{prefix}{current_prefix}{item.name}/")
                        add_tree_lines(item, prefix + extension_prefix, depth + 1)
                    else:
                        lines.append(f"{prefix}{current_prefix}{item.name}")
            
            except PermissionError:
                pass
        
        add_tree_lines(base_dir)
        return '\n'.join(lines)
    
    def fix_tree_structures(self, filepath: Path, content: str) -> Tuple[str, int]:
        """Fix tree structures in README by regenerating them from actual filesystem.
        
        Returns:
            (updated_content, number_of_fixes)
        """
        fixes = 0
        lines = content.split('\n')
        readme_dir = filepath.parent
        
        i = 0
        new_lines = []
        
        while i < len(lines):
            line = lines[i]
            
            # Look for directory tree roots (lines ending with /)
            if line.strip().endswith('/') and not line.strip().startswith('#'):
                base_dir_name = line.strip().rstrip('/')
                
                # Check if next line has tree structure
                if i + 1 < len(lines) and ('├──' in lines[i + 1] or '└──' in lines[i + 1]):
                    # Find the actual directory
                    possible_dirs = [
                        readme_dir / base_dir_name,
                        self.root_path / base_dir_name,
                    ]
                    
                    actual_dir = None
                    for pdir in possible_dirs:
                        if pdir.exists() and pdir.is_dir():
                            actual_dir = pdir
                            break
                    
                    if actual_dir:
                        # Skip all old tree lines
                        tree_start = i + 1
                        tree_end = tree_start
                        while tree_end < len(lines) and ('├──' in lines[tree_end] or '└──' in lines[tree_end] or '│' in lines[tree_end]):
                            tree_end += 1
                        
                        # Generate new tree structure
                        new_tree = self.generate_tree_structure(actual_dir)
                        
                        # Add the directory line
                        new_lines.append(line)
                        # Add new tree structure
                        new_lines.extend(new_tree.split('\n'))
                        
                        fixes += 1
                        i = tree_end
                        continue
            
            new_lines.append(line)
            i += 1
        
        return '\n'.join(new_lines), fixes
    
    def generate_project_structure(self) -> str:
        """Generate complete project structure tree for README.
        
        Returns:
            Formatted tree structure string
        """
        lines = []
        lines.append("telegram-whatsup-chat-bot/")
        
        # Directories to include at root level
        root_dirs = ['auto-reply-service', 'group-posts-service', 'channel-posts-service', 
                     'shared_services', 'tests']
        root_files = ['README.md', 'MANUAL_CONTROL.md']
        
        # Get actual directories and files
        actual_dirs = []
        actual_files = []
        
        for item in sorted(self.root_path.iterdir()):
            if item.is_dir() and item.name in root_dirs:
                actual_dirs.append(item)
            elif item.is_file() and item.name in root_files:
                actual_files.append(item)
        
        # Generate tree for each service directory
        for i, dir_path in enumerate(sorted(actual_dirs)):
            is_last_dir = (i == len(actual_dirs) - 1) and not actual_files
            prefix = "└── " if is_last_dir else "├── "
            extension_prefix = "    " if is_last_dir else "│   "
            
            dir_name = dir_path.name
            lines.append(f"{prefix}{dir_name}/")
            
            # Generate sub-structure for this directory
            sub_lines = self._generate_directory_tree(dir_path, extension_prefix, max_depth=2)
            lines.extend(sub_lines)
        
        # Add root files
        for i, file_path in enumerate(sorted(actual_files)):
            is_last = i == len(actual_files) - 1
            prefix = "└── " if is_last else "├── "
            lines.append(f"{prefix}{file_path.name}")
        
        return '\n'.join(lines)
    
    def _generate_directory_tree(self, base_dir: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0) -> List[str]:
        """Generate tree structure for a directory.
        
        Args:
            base_dir: Directory to generate tree for
            prefix: Prefix for current level
            max_depth: Maximum depth to traverse
            current_depth: Current depth level
            
        Returns:
            List of tree lines
        """
        lines = []
        
        if current_depth >= max_depth:
            return lines
        
        try:
            items = sorted(base_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            
            # Filter out unwanted items
            skip_items = {
                '__pycache__', '.DS_Store', 'venv', '.git', 
                'node_modules', '.pytest_cache', '.venv', 'data',
                '.env', '.env.example'
            }
            
            items = [item for item in items if item.name not in skip_items]
            
            # Only show important files/dirs at depth 1+
            if current_depth > 0:
                # At deeper levels, only show directories and key files
                important_extensions = {'.py', '.md', '.txt', '.sh', '.json', '.ini'}
                items = [item for item in items 
                        if item.is_dir() or 
                        (item.is_file() and any(item.name.endswith(ext) for ext in important_extensions))]
            
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                extension_prefix = "    " if is_last else "│   "
                
                if item.is_dir():
                    lines.append(f"{prefix}{current_prefix}{item.name}/")
                    # Add comment for known directories
                    if current_depth == 0:
                        comment = self._get_directory_comment(item.name)
                        if comment:
                            lines[-1] = lines[-1].rstrip() + f"      # {comment}"
                    
                    # Recursively add subdirectories
                    sub_lines = self._generate_directory_tree(
                        item, 
                        prefix + extension_prefix, 
                        max_depth, 
                        current_depth + 1
                    )
                    lines.extend(sub_lines)
                else:
                    lines.append(f"{prefix}{current_prefix}{item.name}")
        
        except PermissionError:
            pass
        
        return lines
    
    def _get_directory_comment(self, dir_name: str) -> str:
        """Get comment for known directories."""
        comments = {
            'app': 'Entry point',
            'handlers': 'inbox, control',
            'services': 'suggester, budget_guard',
            'storage': 'database',
            'content': 'Content generators (channel, person, tech, etc.)',
            'shared_services': 'Shared code (budget_guard, channel_content, etc.)',
            'tests': 'Test files'
        }
        return comments.get(dir_name, "")
    
    def extract_commands_from_code(self) -> List[Tuple[str, str]]:
        """Extract all commands from codebase with their descriptions.
        
        Returns:
            List of (command, description) tuples
        """
        commands = []
        
        # Look in group-posts-service/services/channel_handler.py
        handler_file = self.root_path / "group-posts-service" / "services" / "channel_handler.py"
        
        if not handler_file.exists():
            return commands
        
        try:
            with open(handler_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # Command descriptions mapping
            command_descriptions = {
                'status': 'Check budget and service status',
                'travel': 'Generate evening travel post',
                'travel morning': 'Generate morning travel post',
                'news': 'Generate news summary',
                'tech': 'Generate tech device post',
                'person': 'Generate famous person post',
                'ukraine': 'Generate Ukraine news',
                'spider': 'Generate spider post',
                'quote': 'Generate quote of the day',
                'africa': 'Generate Africa exploration post',
                'canary': 'Generate Canary Wharf post',
                'uk': 'Generate UK post',
                'job': 'Generate job vacancies',
                'weather': 'Generate weather forecast',
            }
            
            # Extract from sequential_services list
            sequential_pattern = re.compile(r'sequential_services\s*=\s*\[(.*?)\]', re.DOTALL)
            match = sequential_pattern.search(code_content)
            if match:
                services_block = match.group(1)
                # Extract commands from tuples like ("command", func)
                command_pattern = re.compile(r'\("([^"]+)"')
                found_commands = command_pattern.findall(services_block)
                for cmd in found_commands:
                    if cmd != 'status':  # status is special, handled separately
                        desc = command_descriptions.get(cmd, f'Generate {cmd} content')
                        commands.append((cmd, desc))
            
            # Also check individual command handlers for any we might have missed
            handler_pattern = re.compile(r'elif text_lower\s*==\s*"([^"]+)"')
            handler_commands = handler_pattern.findall(code_content)
            for cmd in handler_commands:
                if cmd not in [c[0] for c in commands]:  # Not already added
                    desc = command_descriptions.get(cmd, f'Generate {cmd} content')
                    commands.append((cmd, desc))
            
            # Add status command (it's in sequential_services but with None)
            if 'status' in code_content:
                commands.insert(0, ('status', command_descriptions.get('status', 'Check budget and service status')))
            
            # Sort commands (status first, then alphabetical)
            commands = sorted(commands, key=lambda x: (x[0] != 'status', x[0]))
            
        except Exception as e:
            print(f"⚠️  Error extracting commands from code: {e}")
        
        return commands
    
    def update_readme_commands(self, readme_path: Path) -> bool:
        """Update the Available commands section in README with commands from code.
        
        Args:
            readme_path: Path to README.md file
            
        Returns:
            True if commands were updated, False otherwise
        """
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Cannot read README: {e}")
            return False
        
        # Extract commands from code
        code_commands = self.extract_commands_from_code()
        
        if not code_commands:
            print("⚠️  No commands found in code")
            return False
        
        # Find the Available commands section
        header_pattern = re.compile(r'\*\*Available commands:\*\*', re.IGNORECASE)
        header_match = header_pattern.search(content)
        
        if not header_match:
            print("⚠️  'Available commands' section not found in README")
            return False
        
        # Find the end of the commands list (next ** header or end of section)
        start_pos = header_match.end()
        next_header = re.search(r'\n\*\*[^*]', content[start_pos:])
        if next_header:
            end_pos = start_pos + next_header.start()
        else:
            end_pos = start_pos + 500  # Limit search
        
        commands_section = content[start_pos:end_pos]
        
        # Generate new commands list
        new_commands_lines = []
        travel_added = False
        for cmd, desc in code_commands:
            # Handle special case: travel / travel morning
            if cmd == 'travel morning':
                # Skip - will be added with travel
                continue
            elif cmd == 'travel' and not travel_added:
                new_commands_lines.append(f"- `travel` / `travel morning` - Generate travel posts")
                travel_added = True
            else:
                new_commands_lines.append(f"- `{cmd}` - {desc}")
        
        new_commands_text = '\n'.join(new_commands_lines)
        
        # Replace the commands section
        # Find where the list starts (after header and newline)
        list_start = commands_section.find('- `')
        if list_start == -1:
            list_start = 0
        
        # Find where the list ends (before next section or end)
        # Look for the last command line (line starting with - `)
        lines = commands_section.split('\n')
        list_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('- `'):
                # This is a command line, find where it ends
                list_end = sum(len(l) + 1 for l in lines[:i+1])  # +1 for newline
            elif line.strip().startswith('**') or line.strip().startswith('See'):
                # Next section or reference, stop here
                list_end = sum(len(l) + 1 for l in lines[:i])  # +1 for newline
                break
        
        if list_end == 0:
            # Fallback: find last backtick
            list_end = commands_section.rfind('`')
            if list_end != -1:
                list_end = commands_section.find('\n', list_end)
                if list_end == -1:
                    list_end = len(commands_section)
            else:
                list_end = len(commands_section)
        
        # Replace the commands list
        new_content = (
            content[:start_pos + list_start] +
            new_commands_text +
            content[start_pos + list_end:]
        )
        
        if new_content != content:
            try:
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Updated commands list in {readme_path.name}")
                return True
            except Exception as e:
                print(f"❌ Cannot write README: {e}")
                return False
        else:
            print("ℹ️  Commands list is already up to date")
            return True
    
    def update_readme_structure(self, readme_path: Path) -> bool:
        """Update the Architecture section in README with current project structure.
        
        Args:
            readme_path: Path to README.md file
            
        Returns:
            True if structure was updated, False otherwise
        """
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Cannot read README: {e}")
            return False
        
        # Find the Architecture section
        # Look for "## 🏗️ Architecture" or "## Architecture" followed by code block
        # Find the header first
        header_match = re.search(r'##\s+.*?Architecture', content)
        if not header_match:
            print("⚠️  Architecture section header not found in README")
            return False
        
        # Find the code block after the header
        header_end = header_match.end()
        # Look for ``` that starts after header (with possible blank lines)
        code_start = content.find('```', header_end)
        if code_start == -1:
            print("⚠️  Code block not found after Architecture header")
            return False
        
        # Find the end of the code block
        code_end = content.find('\n```', code_start + 3)
        if code_end == -1:
            print("⚠️  Code block not properly closed")
            return False
        
        # Extract the header part (including newlines before code block)
        header_part = content[header_match.start():code_start]
        
        # Generate new structure
        new_structure = self.generate_project_structure()
        
        # Replace the structure block
        new_content = (
            content[:header_match.start()] +
            header_part +
            '```\n' +
            new_structure +
            '\n```' +
            content[code_end + 5:]  # +5 to skip '\n```'
        )
        
        if new_content != content:
            try:
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Updated project structure in {readme_path.name}")
                return True
            except Exception as e:
                print(f"❌ Cannot write README: {e}")
                return False
        else:
            print("ℹ️  Project structure is already up to date")
            return True
    
    def extract_commands_from_readme(self, content: str) -> List[str]:
        """Extract command list from README 'Available commands' section.
        
        Args:
            content: README content
            
        Returns:
            List of command names found
        """
        commands = []
        
        # Look for "Available commands:" or "**Available commands:**" section
        # Find the section header first
        header_pattern = re.compile(r'\*\*Available commands:\*\*', re.IGNORECASE)
        header_match = header_pattern.search(content)
        
        if not header_match:
            return commands
        
        # Get content after the header until next section or end
        start_pos = header_match.end()
        # Look for next ** header or end of file
        next_header = re.search(r'\n\*\*[^*]', content[start_pos:])
        if next_header:
            commands_section = content[start_pos:start_pos + next_header.start()]
        else:
            commands_section = content[start_pos:start_pos + 500]  # Limit to 500 chars
        
        # Extract commands from list items like: - `command` - description
        # Pattern matches: - `command` or - `command / command2`
        command_pattern = re.compile(r'-\s+`([^`]+)`')
        found_commands = command_pattern.findall(commands_section)
        
        # Process commands - handle slashes and split
        for cmd in found_commands:
            cmd = cmd.strip()
            if '/' in cmd:
                # Split commands like "travel / travel morning"
                parts = [p.strip() for p in cmd.split('/')]
                commands.extend(parts)
            else:
                commands.append(cmd)
        
        return list(set(commands))  # Remove duplicates
    
    def find_commands_in_code(self, command_name: str) -> bool:
        """Check if a command exists in the codebase.
        
        Args:
            command_name: Command to search for
            
        Returns:
            True if command found in code
        """
        # Look in group-posts-service/services/channel_handler.py
        handler_file = self.root_path / "group-posts-service" / "services" / "channel_handler.py"
        
        if not handler_file.exists():
            return False
        
        try:
            with open(handler_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # Check for command handlers like: elif text_lower == "command":
            # Only check for actual command handlers, not just any occurrence
            # Command name is already lowercase from extract_commands_from_readme
            
            # Pattern 1: Command handler (elif text_lower == "command":)
            handler_pattern = rf'elif text_lower\s*==\s*["\']{re.escape(command_name)}["\']'
            if re.search(handler_pattern, code_content, re.IGNORECASE):
                return True
            
            # Pattern 2: In sequential_services list (tuple format like ("command", func))
            # This is more specific - look for tuple with command name as first element
            # Must be in sequential_services context to avoid false positives
            tuple_pattern = rf'\(["\']{re.escape(command_name)}["\']\s*,\s*(?:self\._|None)'
            if re.search(tuple_pattern, code_content, re.IGNORECASE):
                return True
            
            # Pattern 3: In ALL_SERVICE_COMMANDS list (for test files)
            # Look for command in list with comment or in list context
            list_pattern = rf'["\']{re.escape(command_name)}["\']\s*,?\s*(?:#|$)'
            # Only match if it's in a list context (after another list item or at start of line)
            list_context_pattern = rf'(?:^|\s|,)\s*["\']{re.escape(command_name)}["\']\s*,?\s*(?:#|$)'
            if re.search(list_context_pattern, code_content, re.MULTILINE | re.IGNORECASE):
                # Verify it's actually in a commands list, not just any string
                # Check if it's in ALL_SERVICE_COMMANDS or similar
                if 'ALL_SERVICE_COMMANDS' in code_content or 'SERVICES' in code_content:
                    return True
            
            return False
        except Exception:
            return False
    
    def validate_commands(self, filepath: Path) -> List[str]:
        """Validate that commands listed in README exist in code.
        
        Args:
            filepath: Path to README file
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Only check main README.md (resolve paths for comparison)
        filepath_resolved = filepath.resolve()
        root_readme = self.root_path / "README.md"
        if filepath_resolved != root_readme.resolve():
            return issues
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [f"❌ Cannot read file: {e}"]
        
        # Extract commands from README
        readme_commands = self.extract_commands_from_readme(content)
        
        if not readme_commands:
            return issues  # No commands section found, skip validation
        
        # Check each command
        for cmd in readme_commands:
            cmd_clean = cmd.strip().lower()
            # Skip empty or very short commands
            if len(cmd_clean) < 2:
                continue
            
            # Check if command exists in code
            found_in_code = self.find_commands_in_code(cmd_clean)
            
            # Check for known aliases/mappings
            command_mappings = {
                'london': 'canary',  # london was renamed to canary
                'phrase': 'quote',   # phrase is actually quote
            }
            
            if not found_in_code:
                mapped_cmd = command_mappings.get(cmd_clean)
                if mapped_cmd and self.find_commands_in_code(mapped_cmd):
                    issues.append(f"📝 Command '{cmd}' in README maps to '{mapped_cmd}' in code (consider updating README)")
                else:
                    issues.append(f"⚠️  Command '{cmd}' listed in README but not found in code")
            else:
                # Command found, but check if there's a better name
                if cmd_clean in command_mappings:
                    mapped_cmd = command_mappings[cmd_clean]
                    if self.find_commands_in_code(mapped_cmd):
                        issues.append(f"💡 Command '{cmd}' in README should be '{mapped_cmd}' (current code uses '{mapped_cmd}')")
        
        return issues
    
    def validate_structure(self, filepath: Path) -> List[str]:
        """Validate that files/directories mentioned in README actually exist."""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [f"❌ Cannot read file: {e}"]
        
        # Get the directory containing this README (base for relative paths)
        readme_dir = filepath.parent
        
        # Part 1: Parse and validate tree structures
        tree_structures = self.parse_tree_structure(content)
        if tree_structures:
            tree_issues = self.validate_tree_structure(filepath, tree_structures)
            issues.extend(tree_issues)
        
        # Part 2: Extract and validate general file references
        references = self.extract_file_references(content, readme_dir)
        
        # Check each reference
        for ref in references:
            # Try multiple possible locations
            possible_paths = [
                readme_dir / ref,           # Relative to README location
                self.root_path / ref,       # Relative to project root
            ]
            
            # Check if any of the possible paths exist
            exists = any(p.exists() for p in possible_paths)
            
            if not exists:
                # Filter out likely false positives
                # Skip if it's likely a placeholder or example
                if any(skip in ref.lower() for skip in [
                    'example', 'your_', 'my_', 'path/to', 'xxx', 'yyy',
                    'username', 'userid', 'api_key', 'token', 'secret'
                ]):
                    continue
                
                # Skip venv paths (venv is not committed to git)
                if 'venv/' in ref or ref.startswith('venv/'):
                    continue
                
                # Skip common build/generated directories
                if any(skip in ref for skip in [
                    '__pycache__/', 'node_modules/', 'dist/', 'build/',
                    '.pytest_cache/', '.mypy_cache/'
                ]):
                    continue
                
                # Skip if it's too generic (single level, no extension)
                if '/' not in ref or (ref.count('/') == 1 and '.' not in ref.split('/')[-1]):
                    continue
                
                # Skip documentation references that are common patterns
                if ref.endswith('/') or ref.startswith('...'):
                    continue
                    
                issues.append(f"📁 Referenced path not found: {ref}")
        
        return issues
    
    def check_all(self) -> bool:
        """Check all README files. Returns True if all checks pass."""
        main_readme = self.root_path / "README.md"
        
        # If update_structure is enabled, update main README first
        if self.update_structure and main_readme.exists():
            print("🔄 Updating project structure in README.md...")
            if self.update_readme_structure(main_readme):
                print("✅ Project structure updated!\n")
            else:
                print("⚠️  Could not update project structure\n")
        
        # If update_commands is enabled, update commands list
        if self.update_commands and main_readme.exists():
            print("🔄 Updating commands list in README.md...")
            if self.update_readme_commands(main_readme):
                print("✅ Commands list updated!\n")
            else:
                print("⚠️  Could not update commands list\n")
        
        readme_files = self.find_readme_files()
        
        if not readme_files:
            print("⚠️  No README.md files found")
            return True
        
        print(f"📝 Found {len(readme_files)} README file(s)\n")
        
        all_passed = True
        
        for filepath in readme_files:
            self.files_checked += 1
            rel_path = filepath.relative_to(self.root_path)
            
            issues, was_fixed = self.check_and_fix_file(filepath)
            
            # Check structure if requested
            structure_issues = []
            if self.check_structure:
                structure_issues = self.validate_structure(filepath)
                if structure_issues:
                    self.structure_issues += len(structure_issues)
                    issues.extend(structure_issues)
            
            # Check commands if this is main README
            command_issues = []
            if filepath.name == "README.md" and filepath.parent == self.root_path:
                command_issues = self.validate_commands(filepath)
                if command_issues:
                    issues.extend(command_issues)
            
            if issues:
                all_passed = False
                self.issues_found += len(issues)
                
                if was_fixed:
                    self.files_fixed += 1
                    print(f"🔧 {rel_path}")
                    print(f"   Fixed {len(issues) - len(structure_issues)} issue(s):")
                else:
                    print(f"⚠️  {rel_path}")
                    print(f"   Found {len(issues)} issue(s):")
                
                # Show command issues first (if any), then other issues
                command_issue_list = [i for i in issues if 'Command' in i or '📝' in i or '💡' in i]
                other_issues = [i for i in issues if i not in command_issue_list]
                sorted_issues = command_issue_list + other_issues
                
                for issue in sorted_issues[:5]:  # Show first 5 issues
                    print(f"   • {issue}")
                
                if len(sorted_issues) > 5:
                    print(f"   • ... and {len(sorted_issues) - 5} more")
                print()
        
        # Summary
        print("=" * 60)
        print(f"📊 README Check Summary:")
        print(f"   Files checked: {self.files_checked}")
        print(f"   Issues found: {self.issues_found}")
        
        if self.check_structure:
            print(f"   Structure issues: {self.structure_issues}")
        
        if self.fix:
            print(f"   Files fixed: {self.files_fixed}")
        
        print("=" * 60)
        
        if all_passed:
            print("✅ All README files are properly formatted!")
            if self.check_structure and self.structure_issues == 0:
                print("✅ All referenced files/directories exist!")
            return True
        else:
            if self.fix:
                print("🔧 Issues were automatically fixed!")
                if self.check_structure and self.structure_issues > 0:
                    print(f"⚠️  Structure validation found {self.structure_issues} missing references")
                # After fixing, consider it a pass
                return True
            else:
                print("⚠️  Issues found. Run with --fix to auto-correct.")
                if self.check_structure and self.structure_issues > 0:
                    print(f"⚠️  Structure validation found {self.structure_issues} missing references")
                return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check and fix README files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 check_readme.py                       # Check only
  python3 check_readme.py --fix                 # Check and auto-fix
  python3 check_readme.py --check-structure     # Validate structure references
  python3 check_readme.py --fix --check-structure  # Fix and validate structure
  python3 check_readme.py --path services/      # Check specific directory
  python3 check_readme.py --fix --path .        # Fix all README files
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        default=None,
        help='Path to check (default: project root)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Automatically fix issues'
    )
    parser.add_argument(
        '--check-structure',
        action='store_true',
        help='Validate that files/directories mentioned in README exist'
    )
    parser.add_argument(
        '--path',
        dest='path_option',
        help='Path to check (alternative syntax)'
    )
    parser.add_argument(
        '--update-structure',
        action='store_true',
        help='Generate and update project structure in README.md'
    )
    parser.add_argument(
        '--update-commands',
        action='store_true',
        help='Update Available commands section in README.md from code'
    )
    
    args = parser.parse_args()
    
    # Determine the path to check
    if args.path_option:
        check_path = args.path_option
    elif args.path:
        check_path = args.path
    else:
        # Default to project root (parent of tests directory)
        script_dir = Path(__file__).parent
        check_path = script_dir.parent
    
    check_path = Path(check_path).resolve()
    
    if not check_path.exists():
        print(f"❌ Error: Path does not exist: {check_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("📝 README Checker & Auto-Corrector")
    print("=" * 60)
    print(f"Path: {check_path}")
    print(f"Mode: {'Fix' if args.fix else 'Check only'}")
    if args.check_structure:
        print(f"Structure Validation: Enabled")
    if args.update_structure:
        print(f"Structure Update: Enabled")
    if args.update_commands:
        print(f"Commands Update: Enabled")
    print("=" * 60)
    print()
    
    checker = ReadmeChecker(check_path, fix=args.fix, check_structure=args.check_structure, update_structure=args.update_structure, update_commands=args.update_commands)
    success = checker.check_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
