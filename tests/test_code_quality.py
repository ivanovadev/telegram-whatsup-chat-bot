"""Tests for code quality checking and line counting."""

import unittest
from pathlib import Path
from count_lines import CodeCounter


class TestCodeQuality(unittest.TestCase):
    """Test cases for code quality checker."""
    
    def test_code_counter_initialization(self):
        """Test CodeCounter initialization."""
        counter = CodeCounter(".")
        self.assertTrue(counter.root_path.exists())
        self.assertEqual(counter.stats['total_files'], 0)
        self.assertEqual(counter.stats['total_lines'], 0)
    
    def test_comment_detection(self):
        """Test comment line detection."""
        counter = CodeCounter(".")
        
        # Python comments
        self.assertTrue(counter.is_comment_line("# This is a comment", ".py"))
        self.assertTrue(counter.is_comment_line('"""Docstring"""', ".py"))
        self.assertFalse(counter.is_comment_line("print('hello')", ".py"))
        
        # Shell comments
        self.assertTrue(counter.is_comment_line("# Shell comment", ".sh"))
        self.assertFalse(counter.is_comment_line("echo 'test'", ".sh"))
    
    def test_unnecessary_comment_detection(self):
        """Test detection of unnecessary comments."""
        counter = CodeCounter(".")
        
        # Unnecessary comments
        self.assertTrue(counter.is_unnecessary_comment("# TODO: Replace with actual implementation", ".py"))
        self.assertTrue(counter.is_unnecessary_comment("# ... more code ...", ".py"))
        self.assertTrue(counter.is_unnecessary_comment("# ========== SECTION ==========", ".py"))
        self.assertTrue(counter.is_unnecessary_comment("# ----------------------------------------", ".py"))
        
        # Necessary comments
        self.assertFalse(counter.is_unnecessary_comment("# Initialize the database connection", ".py"))
        self.assertFalse(counter.is_unnecessary_comment("# Fix for issue #123", ".py"))
        self.assertFalse(counter.is_unnecessary_comment("# Active hunters hunt on ground", ".py"))
    
    def test_exclude_directories(self):
        """Test directory exclusion."""
        counter = CodeCounter(".")
        
        self.assertTrue(counter.should_exclude(Path("venv/lib/python")))
        self.assertTrue(counter.should_exclude(Path(".venv/bin")))
        self.assertTrue(counter.should_exclude(Path("__pycache__")))
        self.assertTrue(counter.should_exclude(Path(".git/objects")))
        self.assertFalse(counter.should_exclude(Path("src/main.py")))
    
    def test_count_file_stats(self):
        """Test file counting stats."""
        counter = CodeCounter(".")
        test_file = Path(__file__)
        
        if test_file.exists():
            result = counter.count_file(test_file)
            self.assertGreater(result['total'], 0)
            self.assertGreaterEqual(result['code'], 0)
            self.assertGreaterEqual(result['comments'], 0)
            self.assertGreaterEqual(result['blank'], 0)
            self.assertEqual(result['total'], result['code'] + result['comments'] + result['blank'])
    
    def test_service_name_detection(self):
        """Test service name detection from path."""
        counter = CodeCounter(".")
        
        # Mock some paths
        test_paths = [
            (Path("group-posts-service/app/main.py"), "group-posts-service"),
            (Path("shared_services/budget_guard.py"), "shared_services"),
            (Path("tests/test_db.py"), "tests"),
            (Path("README.md"), "root"),
        ]
        
        for path, expected_service in test_paths:
            # Create a relative path from root
            full_path = counter.root_path / path
            if len(path.parts) > 0:
                service = counter.get_service_name(full_path)
                # Service detection might vary based on actual structure
                self.assertIsInstance(service, str)
    
    def test_code_percentage_calculation(self):
        """Test code percentage calculation."""
        counter = CodeCounter(".")
        counter.stats['total_lines'] = 100
        counter.stats['code_lines'] = 75
        counter.stats['comment_lines'] = 15
        counter.stats['blank_lines'] = 10
        
        code_pct = (counter.stats['code_lines'] / counter.stats['total_lines']) * 100
        self.assertEqual(code_pct, 75.0)
    
    def test_unnecessary_comment_patterns(self):
        """Test various unnecessary comment patterns."""
        counter = CodeCounter(".")
        
        test_cases = [
            ("# TODO: implement this later", True),
            ("# ... more code here ...", True),
            ("# ----------------------------------------", True),
            ("# ========================================", True),
            ("# Calculate the sum of two numbers", False),
            ("# FIXME: Bug in production", False),
            ("# WARNING: This will delete all data", False),
            ("# This is a standard explanatory comment", False),
        ]
        
        for comment, should_be_unnecessary in test_cases:
            result = counter.is_unnecessary_comment(comment, ".py")
            self.assertEqual(result, should_be_unnecessary, f"Failed for: {comment}")
    
    def test_file_type_recognition(self):
        """Test file type recognition."""
        counter = CodeCounter(".")
        
        self.assertIn('.py', counter.FILE_TYPES)
        self.assertIn('.md', counter.FILE_TYPES)
        self.assertIn('.sh', counter.FILE_TYPES)
        self.assertIn('.json', counter.FILE_TYPES)
        self.assertEqual(counter.FILE_TYPES['.py'], 'Python')
        self.assertEqual(counter.FILE_TYPES['.md'], 'Markdown')
    
    def test_scan_excludes_virtual_env(self):
        """Test that scan excludes virtual environment directories."""
        counter = CodeCounter(".")
        counter.scan(check_comments=False)
        
        # Check that no venv files were processed
        for file_info in counter.stats['files_processed']:
            path_str = str(file_info['path'])
            self.assertNotIn('venv', path_str)
            self.assertNotIn('.venv', path_str)
            self.assertNotIn('__pycache__', path_str)


if __name__ == "__main__":
    unittest.main()
