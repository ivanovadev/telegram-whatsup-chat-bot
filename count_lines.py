#!/usr/bin/env python3
"""Count lines of code in the telegram-whatsup-chat-bot repository.

This script analyzes the codebase and provides statistics about:
- Total lines of code
- Lines by file type (Python, Markdown, Shell, etc.)
- Lines by service/directory
- Code vs comments vs blank lines

Usage:
    python3 count_lines.py
    python3 count_lines.py --detailed
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse


class CodeCounter:
    """Count lines of code in the repository."""
    
    # Directories to exclude from counting
    EXCLUDE_DIRS = {
        'venv', '__pycache__', '.git', 'node_modules', 
        '.pytest_cache', '.mypy_cache', 'dist', 'build',
        'egg-info', '.tox', 'htmlcov', '.coverage'
    }
    
    # File extensions to count
    FILE_TYPES = {
        '.py': 'Python',
        '.md': 'Markdown',
        '.sh': 'Shell',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.json': 'JSON',
        '.txt': 'Text',
        '.env': 'Config',
        '.ini': 'Config',
        '.cfg': 'Config',
    }
    
    def __init__(self, root_path: str):
        """Initialize counter with repository root path."""
        self.root_path = Path(root_path).resolve()
        self.stats = {
            'total_files': 0,
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'by_type': defaultdict(lambda: {'files': 0, 'lines': 0, 'code': 0}),
            'by_service': defaultdict(lambda: {'files': 0, 'lines': 0, 'code': 0}),
            'files_processed': []
        }
    
    def should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        # Check if any parent directory is in exclude list
        for parent in path.parents:
            if parent.name in self.EXCLUDE_DIRS:
                return True
        # Check if directory itself is excluded
        if path.is_dir() and path.name in self.EXCLUDE_DIRS:
            return True
        return False
    
    def is_comment_line(self, line: str, ext: str) -> bool:
        """Check if line is a comment."""
        line = line.strip()
        if not line:
            return False
        
        if ext == '.py':
            return line.startswith('#') or line.startswith('"""') or line.startswith("'''")
        elif ext == '.sh':
            return line.startswith('#')
        elif ext in ['.yaml', '.yml']:
            return line.startswith('#')
        
        return False
    
    def count_file(self, file_path: Path) -> dict:
        """Count lines in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total = len(lines)
            blank = sum(1 for line in lines if not line.strip())
            comments = sum(1 for line in lines if self.is_comment_line(line, file_path.suffix))
            code = total - blank - comments
            
            return {
                'total': total,
                'code': code,
                'comments': comments,
                'blank': blank
            }
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}", file=sys.stderr)
            return {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
    
    def get_service_name(self, file_path: Path) -> str:
        """Get service name from file path."""
        try:
            rel_path = file_path.relative_to(self.root_path)
            parts = rel_path.parts
            
            if len(parts) > 0:
                # First directory is usually the service name
                service = parts[0]
                if service.endswith('-service'):
                    return service
                elif service in ['shared_services', 'handlers', 'storage', 'tests']:
                    return service
                else:
                    return 'root'
            return 'root'
        except ValueError:
            return 'external'
    
    def scan(self):
        """Scan repository and count lines."""
        print(f"📊 Scanning repository: {self.root_path}")
        print(f"🚫 Excluding: {', '.join(sorted(self.EXCLUDE_DIRS))}\n")
        
        for file_path in self.root_path.rglob('*'):
            # Skip if excluded
            if self.should_exclude(file_path):
                continue
            
            # Skip if not a file
            if not file_path.is_file():
                continue
            
            # Skip if not a recognized file type
            ext = file_path.suffix
            if ext not in self.FILE_TYPES:
                continue
            
            # Count lines in file
            counts = self.count_file(file_path)
            if counts['total'] == 0:
                continue
            
            # Update stats
            file_type = self.FILE_TYPES[ext]
            service = self.get_service_name(file_path)
            
            self.stats['total_files'] += 1
            self.stats['total_lines'] += counts['total']
            self.stats['code_lines'] += counts['code']
            self.stats['comment_lines'] += counts['comments']
            self.stats['blank_lines'] += counts['blank']
            
            self.stats['by_type'][file_type]['files'] += 1
            self.stats['by_type'][file_type]['lines'] += counts['total']
            self.stats['by_type'][file_type]['code'] += counts['code']
            
            self.stats['by_service'][service]['files'] += 1
            self.stats['by_service'][service]['lines'] += counts['total']
            self.stats['by_service'][service]['code'] += counts['code']
            
            self.stats['files_processed'].append({
                'path': file_path.relative_to(self.root_path),
                'type': file_type,
                'service': service,
                'lines': counts['total'],
                'code': counts['code']
            })
    
    def print_summary(self, detailed: bool = False):
        """Print statistics summary."""
        print("=" * 60)
        print("📈 CODE STATISTICS SUMMARY")
        print("=" * 60)
        
        # Overall stats
        print(f"\n📁 Total Files: {self.stats['total_files']:,}")
        print(f"📝 Total Lines: {self.stats['total_lines']:,}")
        print(f"💻 Code Lines: {self.stats['code_lines']:,}")
        print(f"💬 Comment Lines: {self.stats['comment_lines']:,}")
        print(f"⬜ Blank Lines: {self.stats['blank_lines']:,}")
        
        if self.stats['total_lines'] > 0:
            code_pct = (self.stats['code_lines'] / self.stats['total_lines']) * 100
            print(f"📊 Code Percentage: {code_pct:.1f}%")
        
        # By file type
        print(f"\n{'─' * 60}")
        print("📚 By File Type:")
        print(f"{'─' * 60}")
        print(f"{'Type':<15} {'Files':<10} {'Total Lines':<15} {'Code Lines':<15}")
        print(f"{'─' * 60}")
        
        for file_type in sorted(self.stats['by_type'].keys(), 
                               key=lambda x: self.stats['by_type'][x]['lines'], 
                               reverse=True):
            data = self.stats['by_type'][file_type]
            print(f"{file_type:<15} {data['files']:<10} {data['lines']:<15,} {data['code']:<15,}")
        
        # By service
        print(f"\n{'─' * 60}")
        print("🔧 By Service/Directory:")
        print(f"{'─' * 60}")
        print(f"{'Service':<30} {'Files':<10} {'Total Lines':<15} {'Code Lines':<15}")
        print(f"{'─' * 60}")
        
        for service in sorted(self.stats['by_service'].keys(), 
                             key=lambda x: self.stats['by_service'][x]['lines'], 
                             reverse=True):
            data = self.stats['by_service'][service]
            print(f"{service:<30} {data['files']:<10} {data['lines']:<15,} {data['code']:<15,}")
        
        # Detailed file list
        if detailed:
            print(f"\n{'─' * 60}")
            print("📄 Detailed File List:")
            print(f"{'─' * 60}")
            print(f"{'File Path':<50} {'Type':<15} {'Lines':<10} {'Code':<10}")
            print(f"{'─' * 60}")
            
            for file_info in sorted(self.stats['files_processed'], 
                                   key=lambda x: x['lines'], 
                                   reverse=True):
                path_str = str(file_info['path'])
                if len(path_str) > 47:
                    path_str = '...' + path_str[-44:]
                print(f"{path_str:<50} {file_info['type']:<15} {file_info['lines']:<10,} {file_info['code']:<10,}")
        
        print(f"\n{'=' * 60}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Count lines of code in telegram-whatsup-chat-bot repository')
    parser.add_argument('--detailed', '-d', action='store_true', 
                       help='Show detailed file-by-file breakdown')
    parser.add_argument('--path', '-p', type=str, default=None,
                       help='Path to repository (default: current directory)')
    args = parser.parse_args()
    
    # Determine repository root
    if args.path:
        repo_path = args.path
    else:
        # Assume script is in repository root
        repo_path = os.path.dirname(os.path.abspath(__file__))
    
    # Create counter and scan
    counter = CodeCounter(repo_path)
    counter.scan()
    counter.print_summary(detailed=args.detailed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
