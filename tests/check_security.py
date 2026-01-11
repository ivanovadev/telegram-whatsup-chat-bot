#!/usr/bin/env python3
"""
Security checker script for detecting Ukrainian language and sensitive information.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


class SecurityChecker:
    """Checker for Ukrainian language and sensitive data."""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'api_key': r'(?i)(api[_-]?key|apikey|api[_-]?secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
        'token': r'(?i)(token|access[_-]?token|auth[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
        'password': r'(?i)(password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\'\s]{6,})',
        'secret': r'(?i)(secret|secret[_-]?key)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
        'telegram_bot_token': r'\d{8,10}:[a-zA-Z0-9_-]{35}',
        'openai_key': r'sk-[a-zA-Z0-9]{20,}',
        'aws_key': r'(?i)AKIA[0-9A-Z]{16}',
        'private_key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
        'phone': r'(?i)(phone|tel)["\']?\s*[:=]\s*["\']?(\+?\d{10,15})',
        'email': r'(?i)(email|e-mail)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    }
    
    # Files and directories to skip
    SKIP_DIRS = {
        'venv', '__pycache__', '.git', 'node_modules', 
        '.venv', 'env', '.env', 'dist', 'build',
        '.pytest_cache', '.mypy_cache', '.tox'
    }
    
    SKIP_FILES = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.db', '.sqlite', '.session', '.jpg', '.png', '.gif',
        '.ico', '.pdf', '.zip', '.tar', '.gz', '.bz2'
    }
    
    # Allow certain files with expected sensitive patterns
    WHITELIST_FILES = {
        'test_db.py',
        'check_security.py',
        'README.md',
        'MANUAL_CONTROL.md',
        'SECURITY_CHECK.md',
        'QUICK_START.md',
        'example_issues.py.example',  # Example file with intentional issues
        '.gitignore_recommendations',
        '.gitignore.template',
    }
    
    def __init__(self, root_dir: str):
        """Initialize checker with root directory."""
        self.root_dir = Path(root_dir)
        self.issues: Dict[str, List[Tuple[int, str, str]]] = {}
        self.ukrainian_files: Dict[str, List[Tuple[int, str]]] = {}
        
    def has_ukrainian(self, text: str) -> bool:
        """Check if text contains Ukrainian (Cyrillic) characters."""
        ukrainian_pattern = r'[а-яА-ЯіІїЇєЄґҐ]'
        return bool(re.search(ukrainian_pattern, text))
    
    def should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        # Skip directories
        if path.is_dir() and path.name in self.SKIP_DIRS:
            return True
        
        # Skip files by extension
        if path.is_file() and path.suffix in self.SKIP_FILES:
            return True
        
        # Skip hidden files and directories
        if path.name.startswith('.') and path.name not in ['.env.example']:
            return True
            
        return False
    
    def is_whitelisted(self, path: Path) -> bool:
        """Check if file is whitelisted for sensitive data."""
        return path.name in self.WHITELIST_FILES
    
    def check_file(self, filepath: Path) -> None:
        """Check single file for issues."""
        try:
            # Try to read as text
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  Cannot read {filepath}: {e}")
            return
        
        rel_path = filepath.relative_to(self.root_dir)
        is_whitelisted = self.is_whitelisted(filepath)
        
        for line_num, line in enumerate(lines, 1):
            # Check for Ukrainian text (skip whitelisted files)
            if not is_whitelisted and self.has_ukrainian(line):
                if str(rel_path) not in self.ukrainian_files:
                    self.ukrainian_files[str(rel_path)] = []
                self.ukrainian_files[str(rel_path)].append((line_num, line.strip()))
            
            # Check for sensitive data (skip whitelisted files)
            if not is_whitelisted:
                for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        issue_key = f"{rel_path}:{pattern_name}"
                        if issue_key not in self.issues:
                            self.issues[issue_key] = []
                        
                        # Mask the sensitive value
                        matched_text = match.group(0)
                        if len(matched_text) > 50:
                            masked = matched_text[:20] + "..." + matched_text[-10:]
                        else:
                            masked = matched_text[:10] + "***"
                        
                        self.issues[issue_key].append((
                            line_num,
                            pattern_name,
                            masked
                        ))
    
    def scan_directory(self) -> None:
        """Scan entire directory recursively."""
        print(f"🔍 Scanning directory: {self.root_dir}")
        print(f"{'='*70}\n")
        
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            
            # Remove skipped directories from traversal
            dirs[:] = [d for d in dirs if not self.should_skip(root_path / d)]
            
            for filename in files:
                filepath = root_path / filename
                
                if self.should_skip(filepath):
                    continue
                
                self.check_file(filepath)
    
    def print_report(self) -> int:
        """Print scan report and return exit code."""
        total_issues = 0
        
        # Report Ukrainian language findings
        if self.ukrainian_files:
            print("📝 UKRAINIAN LANGUAGE DETECTED:")
            print(f"{'-'*70}")
            for filepath, occurrences in sorted(self.ukrainian_files.items()):
                print(f"\n📄 {filepath} ({len(occurrences)} occurrences)")
                for line_num, text in occurrences[:3]:  # Show first 3
                    print(f"   Line {line_num}: {text[:80]}")
                if len(occurrences) > 3:
                    print(f"   ... and {len(occurrences) - 3} more")
            print(f"\n{'='*70}\n")
        else:
            print("✅ No Ukrainian language detected\n")
        
        # Report sensitive data findings
        if self.issues:
            print("🔒 SENSITIVE DATA DETECTED:")
            print(f"{'-'*70}")
            
            grouped_by_file = {}
            for issue_key, occurrences in self.issues.items():
                filepath, pattern = issue_key.rsplit(':', 1)
                if filepath not in grouped_by_file:
                    grouped_by_file[filepath] = []
                grouped_by_file[filepath].extend(occurrences)
                total_issues += len(occurrences)
            
            for filepath, file_issues in sorted(grouped_by_file.items()):
                print(f"\n🚨 {filepath} ({len(file_issues)} issues)")
                for line_num, pattern_name, masked_text in file_issues:
                    print(f"   Line {line_num}: [{pattern_name}] {masked_text}")
            
            print(f"\n{'='*70}")
            print(f"❌ TOTAL: {total_issues} sensitive data issue(s) found!")
            print(f"{'='*70}\n")
            return 1
        else:
            print("✅ No sensitive data detected\n")
            return 0
    
    def print_summary(self) -> None:
        """Print summary statistics."""
        print("\n📊 SUMMARY:")
        print(f"{'-'*70}")
        print(f"Ukrainian files: {len(self.ukrainian_files)}")
        print(f"Sensitive data issues: {len(self.issues)}")
        print(f"{'='*70}\n")


def main():
    """Main entry point."""
    # Default to parent directory of tests folder
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    # Allow custom path via command line
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    
    if not root_dir.exists():
        print(f"❌ Error: Directory not found: {root_dir}")
        sys.exit(1)
    
    print("🛡️  Security Checker")
    print(f"{'='*70}\n")
    
    checker = SecurityChecker(root_dir)
    checker.scan_directory()
    exit_code = checker.print_report()
    checker.print_summary()
    
    if exit_code == 0:
        print("✅ All checks passed!")
    else:
        print("⚠️  Please review and fix the issues above.")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
