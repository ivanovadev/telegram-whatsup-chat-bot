#!/usr/bin/env python3
"""Check and auto-fix .env files to match .env.example files.

This script:
1. Finds all .env.example files in the project
2. For each .env.example, checks if corresponding .env exists (creates if missing)
3. Automatically adds missing variables from .env.example to .env
4. Preserves existing values in .env files
"""
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Set, List, Tuple


def parse_env_file(file_path: Path, preserve_comments: bool = False) -> Tuple[Dict[str, str], List[str]]:
    """Parse .env or .env.example file and return dict of variables and original lines.
    
    Returns (variables: Dict[str, str], lines: List[str])
    Skips comments, empty lines, and lines without '='.
    """
    variables = {}
    lines = []
    
    if not file_path.exists():
        return variables, lines
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                original_line = line.rstrip('\n\r')
                line = original_line.strip()
                
                # Keep comments and empty lines if preserve_comments
                if preserve_comments:
                    if not line or line.startswith('#'):
                        lines.append(original_line)
                        continue
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Skip lines without '='
                if '=' not in line:
                    if preserve_comments:
                        lines.append(original_line)
                    continue
                
                # Extract variable name (before first '=')
                var_name = line.split('=', 1)[0].strip()
                
                # Skip if empty variable name
                if not var_name:
                    continue
                
                # Extract value
                var_value = line.split('=', 1)[1].strip()
                variables[var_name] = var_value
                
                if preserve_comments:
                    lines.append(original_line)
    
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
        return variables, lines
    
    return variables, lines


def find_env_example_files(project_root: Path) -> List[Path]:
    """Find all .env.example files in the project.
    
    Skips deprecated root-level .env.example file.
    Only includes service-specific .env.example files.
    """
    env_examples = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip venv, __pycache__, and other common ignore directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', '.venv', 'tests']]
        
        if '.env.example' in files:
            env_path = Path(root) / '.env.example'
            # Skip deprecated root-level .env.example
            if env_path.parent == project_root:
                continue
            env_examples.append(env_path)
    
    return sorted(env_examples)


def fix_env_file(example_file: Path, env_file: Path, project_root: Path) -> Tuple[bool, int]:
    """Fix .env file by adding missing variables from .env.example.
    
    Returns (success: bool, added_count: int)
    """
    # Parse .env.example
    example_vars, example_lines = parse_env_file(example_file, preserve_comments=True)
    
    if not example_vars:
        return True, 0  # No variables to add
    
    # Parse existing .env (if exists)
    env_vars, env_lines = parse_env_file(env_file, preserve_comments=True) if env_file.exists() else ({}, [])
    
    # Find missing variables
    missing_vars = set(example_vars.keys()) - set(env_vars.keys())
    
    if not missing_vars:
        return True, 0  # Nothing to add
    
    # Create or update .env file
    try:
        # Read .env.example to preserve comments and structure
        with open(example_file, 'r', encoding='utf-8') as f:
            example_content = f.read()
        
        # If .env doesn't exist, copy from .env.example
        if not env_file.exists():
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(example_content)
            rel_env = env_file.relative_to(project_root)
            print(f"✅ Created {rel_env} from .env.example")
            return True, len(missing_vars)
        
        # .env exists - add missing variables
        # Read current .env content
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        # Find lines with variables in .env.example that are missing in .env
        # Also include comments before the variable
        lines_to_add = []
        example_lines_list = example_content.split('\n')
        
        for i, line in enumerate(example_lines_list):
            line_stripped = line.strip()
            
            # Skip empty lines (but we'll add them if they're before a variable we need)
            if not line_stripped:
                continue
            
            # Check if this is a variable line
            if '=' in line_stripped and not line_stripped.startswith('#'):
                var_name = line_stripped.split('=', 1)[0].strip()
                
                if var_name in missing_vars:
                    # Include comments before this variable (up to 10 lines back)
                    comment_lines = []
                    for j in range(max(0, i - 10), i):
                        prev_line = example_lines_list[j].rstrip('\n\r')
                        prev_stripped = prev_line.strip()
                        # Include comment lines and empty lines before the variable
                        if prev_stripped.startswith('#') or not prev_stripped:
                            comment_lines.append(prev_line)
                        elif '=' in prev_stripped:
                            # Stop if we hit another variable
                            break
                    
                    # Add comments (if any) and then the variable
                    # Reverse to get correct order (oldest comment first)
                    if comment_lines:
                        lines_to_add.extend(comment_lines)
                    lines_to_add.append(line.rstrip('\n\r'))
        
        # Append missing variables to .env
        if lines_to_add:
            # Add newline if .env doesn't end with one
            if env_content and not env_content.endswith('\n'):
                env_content += '\n'
            
            # Add comment separator if needed
            if env_content and not env_content.rstrip().endswith('\n\n'):
                env_content += '\n'
            
            # Add missing variables
            env_content += '\n'.join(lines_to_add)
            if not env_content.endswith('\n'):
                env_content += '\n'
            
            # Write updated .env
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            return True, len(missing_vars)
        
    except Exception as e:
        rel_env = env_file.relative_to(project_root)
        print(f"❌ Error fixing {rel_env}: {e}", file=sys.stderr)
        return False, 0
    
    return True, 0


def check_and_fix_env_files(project_root: Path, auto_fix: bool = True) -> Tuple[bool, int]:
    """Check and optionally fix all .env files.
    
    Returns (success: bool, fixed_count: int)
    """
    fixed_count = 0
    checked_count = 0
    
    env_examples = find_env_example_files(project_root)
    
    if not env_examples:
        print("⚠️  No .env.example files found in the project")
        return True, 0  # Not an error, just no files to check
    
    print(f"📋 Found {len(env_examples)} .env.example file(s):")
    for example_file in env_examples:
        rel_path = example_file.relative_to(project_root)
        print(f"   - {rel_path}")
    print()
    
    for example_file in env_examples:
        checked_count += 1
        rel_example = example_file.relative_to(project_root)
        env_file = example_file.parent / '.env'
        rel_env = env_file.relative_to(project_root)
        
        # Parse both files
        example_vars, _ = parse_env_file(example_file)
        env_vars, _ = parse_env_file(env_file) if env_file.exists() else ({}, [])
        
        # Check if .env.example has any variables
        if not example_vars:
            print(f"⚠️  {rel_example} has no variables defined, skipping")
            continue
        
        # Find missing variables
        missing_vars = set(example_vars.keys()) - set(env_vars.keys())
        
        if missing_vars:
            if auto_fix:
                success, added = fix_env_file(example_file, env_file, project_root)
                if success and added > 0:
                    print(f"✅ {rel_env}: Added {added} missing variable(s): {', '.join(sorted(missing_vars))}")
                    fixed_count += added
                elif not success:
                    print(f"❌ {rel_env}: Failed to add missing variables")
            else:
                missing_list = ', '.join(sorted(missing_vars))
                print(f"⚠️  {rel_env} missing {len(missing_vars)} variable(s): {missing_list}")
        else:
            print(f"✅ {rel_env}: All {len(example_vars)} variables from {rel_example} are present")
    
    print()
    
    if auto_fix and fixed_count > 0:
        print(f"✅ Fixed {fixed_count} missing variable(s) across {checked_count} .env file(s)")
    elif checked_count > 0:
        print(f"✅ All {checked_count} .env file(s) match their .env.example file(s)")
    
    return True, fixed_count


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check and auto-fix .env files to match .env.example files"
    )
    parser.add_argument(
        'project_root',
        nargs='?',
        help='Project root directory (default: parent of tests/)'
    )
    parser.add_argument(
        '--no-fix',
        action='store_true',
        help='Only check, do not auto-fix missing variables'
    )
    
    args = parser.parse_args()
    
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        # Default to parent directory of tests/
        script_dir = Path(__file__).parent.resolve()
        project_root = script_dir.parent
    
    if not project_root.exists():
        print(f"❌ Error: Project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)
    
    auto_fix = not args.no_fix
    
    if auto_fix:
        print("🔍 Checking and auto-fixing .env files against .env.example files...")
    else:
        print("🔍 Checking .env files against .env.example files...")
    print(f"📁 Project root: {project_root}")
    print()
    
    success, fixed_count = check_and_fix_env_files(project_root, auto_fix=auto_fix)
    
    if success:
        if fixed_count > 0:
            print(f"✅ All .env files are now properly configured! (Fixed {fixed_count} variable(s))")
        else:
            print("✅ All .env files are properly configured!")
        sys.exit(0)
    else:
        print("❌ Some errors occurred while fixing .env files")
        sys.exit(1)


if __name__ == "__main__":
    main()
