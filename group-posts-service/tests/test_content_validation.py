#!/usr/bin/env python3
"""Content validation tests to prevent regressions.

This test suite validates that all services generate correct content
and prevents issues that were fixed from reoccurring.

Usage:
    python3 tests/test_content_validation.py
"""

import os
import sys
import asyncio
import re
from datetime import datetime, timedelta

# Add parent directory to path
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(service_dir)
sys.path.insert(0, service_dir)
sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    env_path = os.path.join(service_dir, '.env')
    load_dotenv(env_path)
except ImportError:
    pass

from storage.db import Database
from shared_services.budget_guard import BudgetGuard
from content.london_content import LondonContentGenerator
from content.weather_content import WeatherContentGenerator
from services.job_content import JobContentGenerator


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = []
        self.failed = []
    
    def add_pass(self, test_name: str, message: str = ""):
        """Add a passed test."""
        self.passed.append((test_name, message))
        print(f"✅ PASS: {test_name}")
        if message:
            print(f"   {message}")
    
    def add_fail(self, test_name: str, message: str):
        """Add a failed test."""
        self.failed.append((test_name, message))
        print(f"❌ FAIL: {test_name}")
        print(f"   {message}")
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.passed) + len(self.failed)
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {len(self.passed)}/{total}")
        print(f"❌ Failed: {len(self.failed)}/{total}")
        
        if self.failed:
            print("\n❌ Failed tests:")
            for test_name, message in self.failed:
                print(f"   • {test_name}")
                print(f"     {message}")
        
        return len(self.failed) == 0


async def test_canary_wharf_content(results: TestResults):
    """Test Canary Wharf content generation."""
    print("\n🏢 Testing Canary Wharf Content...")
    print("-" * 60)
    
    try:
        db = Database()
        budget_guard = BudgetGuard(db)
        generator = LondonContentGenerator(budget_guard)
        
        # Test 1: Generate content (template mode)
        content = generator._generate_template([])
        
        if content:
            results.add_pass("Canary Wharf: Content generation", "Template content generated successfully")
        else:
            results.add_fail("Canary Wharf: Content generation", "Failed to generate content")
            return
        
        # Test 2: Verify no "places" field (or empty places)
        places = content.get("places", [])
        if not places or len(places) == 0:
            results.add_pass("Canary Wharf: No places to visit", "Places section correctly removed")
        else:
            results.add_fail("Canary Wharf: No places to visit", f"Found {len(places)} places - should be removed")
        
        # Test 3: Verify events field exists
        events = content.get("events", [])
        if events and len(events) > 0:
            results.add_pass("Canary Wharf: Events present", f"Found {len(events)} events")
        else:
            results.add_fail("Canary Wharf: Events present", "Events field missing or empty")
        
        # Test 4: Verify fact field exists
        fact = content.get("canary_wharf_fact", "")
        if fact:
            results.add_pass("Canary Wharf: Fact present", "Canary Wharf fact included")
        else:
            results.add_fail("Canary Wharf: Fact present", "Fact field missing")
        
        # Test 5: Verify image search term exists
        image_search = content.get("image_search_term", "")
        if image_search and "canary" in image_search.lower():
            results.add_pass("Canary Wharf: Image search term", f"Search term: {image_search}")
        else:
            results.add_fail("Canary Wharf: Image search term", "Missing or incorrect image search term")
    
    except Exception as e:
        results.add_fail("Canary Wharf: Test execution", f"Exception: {e}")


async def test_weather_cities(results: TestResults):
    """Test weather content uses correct cities."""
    print("\n🌤️ Testing Weather Content...")
    print("-" * 60)
    
    try:
        db = Database()
        budget_guard = BudgetGuard(db)
        generator = WeatherContentGenerator(budget_guard)
        
        # Test 1: Check CITIES configuration
        cities = generator.CITIES
        
        city_names = [c["name"] for c in cities]
        
        # Test 2: Verify Protaras (not Nicosia)
        if "Protaras" in city_names:
            results.add_pass("Weather: Protaras city", "Using Protaras for Cyprus")
        else:
            results.add_fail("Weather: Protaras city", f"Not using Protaras. Cities: {city_names}")
        
        # Test 3: Verify Kraków (not Warsaw)
        if "Kraków" in city_names or "Krakow" in city_names:
            results.add_pass("Weather: Kraków city", "Using Kraków for Poland")
        else:
            results.add_fail("Weather: Kraków city", f"Not using Kraków. Cities: {city_names}")
        
        # Test 4: Verify no Nicosia
        if "Nicosia" not in city_names:
            results.add_pass("Weather: No Nicosia", "Nicosia correctly replaced")
        else:
            results.add_fail("Weather: No Nicosia", "Still using Nicosia instead of Protaras")
        
        # Test 5: Verify no Warsaw
        if "Warsaw" not in city_names:
            results.add_pass("Weather: No Warsaw", "Warsaw correctly replaced")
        else:
            results.add_fail("Weather: No Warsaw", "Still using Warsaw instead of Kraków")
        
        # Test 6: Generate template content
        content = generator._generate_template()
        weather_data = content.get("weather", [])
        
        if weather_data:
            template_cities = [w.get("city") for w in weather_data]
            
            # Check template uses correct cities
            if "Protaras" in template_cities:
                results.add_pass("Weather: Template uses Protaras", "Template correctly configured")
            else:
                results.add_fail("Weather: Template uses Protaras", f"Template cities: {template_cities}")
            
            if "Kraków" in template_cities or "Krakow" in template_cities:
                results.add_pass("Weather: Template uses Kraków", "Template correctly configured")
            else:
                results.add_fail("Weather: Template uses Kraków", f"Template cities: {template_cities}")
    
    except Exception as e:
        results.add_fail("Weather: Test execution", f"Exception: {e}")


def test_job_age_requirement(results: TestResults):
    """Test job content requires recent postings (3 weeks)."""
    print("\n💼 Testing Job Content Requirements...")
    print("-" * 60)
    
    try:
        db = Database()
        budget_guard = BudgetGuard(db)
        generator = JobContentGenerator(budget_guard)
        
        # Read the source code to verify age requirement
        import inspect
        source = inspect.getsource(generator._generate_with_llm)
        source_lower = source.lower()
        
        # Test 1: Verify "3 weeks" or "21 days" mentioned in prompt
        if "3 weeks" in source_lower or "21 days" in source_lower:
            results.add_pass("Jobs: Age requirement in code", "3 weeks/21 days requirement found in code")
        else:
            results.add_fail("Jobs: Age requirement in code", "3 weeks requirement not found in prompt")
        
        # Test 2: Verify it's not "last 7 days" anymore (should be "last 3 weeks")
        if "posted within last 7 days" in source_lower or "within the last 7 days" in source_lower:
            results.add_fail("Jobs: Old 7-day requirement", "Still using old 7-day requirement")
        else:
            results.add_pass("Jobs: No 7-day requirement", "Old 7-day requirement removed")
        
        # Test 3: Generate template to ensure it works
        content = generator._generate_template([])
        vacancies = content.get("vacancies", [])
        
        if vacancies and len(vacancies) == 3:
            results.add_pass("Jobs: Template generation", f"Generated {len(vacancies)} vacancies")
        else:
            results.add_fail("Jobs: Template generation", f"Expected 3 vacancies, got {len(vacancies)}")
        
        # Test 4: Verify all vacancies have required fields
        required_fields = ["company", "job_title", "location", "salary", "company_rating", "description", "requirements", "linkedin_url"]
        all_valid = True
        for idx, vacancy in enumerate(vacancies):
            for field in required_fields:
                if field not in vacancy:
                    results.add_fail(f"Jobs: Vacancy {idx+1} field '{field}'", "Required field missing")
                    all_valid = False
        
        if all_valid and vacancies:
            results.add_pass("Jobs: Required fields", "All vacancies have required fields")
    
    except Exception as e:
        results.add_fail("Jobs: Test execution", f"Exception: {e}")


def test_command_configuration(results: TestResults):
    """Test that commands are correctly configured."""
    print("\n⚙️ Testing Command Configuration...")
    print("-" * 60)
    
    try:
        # Read services list
        from services.services_list import SERVICES
        
        # Test 1: Verify "canary" command exists
        canary_service = None
        for service in SERVICES:
            if service.get("command") == "canary":
                canary_service = service
                break
        
        if canary_service:
            results.add_pass("Commands: Canary command exists", f"Found service: {canary_service.get('name')}")
        else:
            results.add_fail("Commands: Canary command exists", "Canary command not found in services list")
        
        # Test 2: Verify no "london" command
        london_service = None
        for service in SERVICES:
            if service.get("command") == "london":
                london_service = service
                break
        
        if not london_service:
            results.add_pass("Commands: No london command", "Old 'london' command correctly removed")
        else:
            results.add_fail("Commands: No london command", "Old 'london' command still present")
        
        # Test 3: Verify all services have required fields
        required_fields = ["name", "file", "class", "description", "command"]
        for service in SERVICES:
            service_name = service.get("name", "Unknown")
            missing_fields = [f for f in required_fields if f not in service]
            
            if not missing_fields:
                results.add_pass(f"Commands: Service '{service_name}'", "All required fields present")
            else:
                results.add_fail(f"Commands: Service '{service_name}'", f"Missing fields: {missing_fields}")
    
    except Exception as e:
        results.add_fail("Commands: Test execution", f"Exception: {e}")


def test_sequential_schedule(results: TestResults):
    """Test that sequential schedule is properly configured."""
    print("\n📅 Testing Sequential Schedule...")
    print("-" * 60)
    
    try:
        from services.channel_handler import ChannelHandler
        
        # Get default times from ChannelHandler
        # We can't instantiate it without all dependencies, so we'll check the source
        import inspect
        source = inspect.getsource(ChannelHandler.__init__)
        
        # Test 1: Verify morning times are sequential (08:10, 08:20, 08:30, etc.)
        expected_times = {
            "08:10": "evening_time (travel)",
            "08:20": "morning_time (travel morning)",
            "08:30": "news",
            "08:40": "tech",
            "08:50": "person",
            "09:00": "ukraine",
            "09:10": "spider",
            "09:20": "quote",
            "09:30": "africa",
            "09:40": "london_time (canary)",
            "09:50": "uk",
            "10:00": "job",
            "10:10": "weather"
        }
        
        times_found = 0
        for time_str in expected_times.keys():
            if time_str in source:
                times_found += 1
        
        if times_found >= 10:  # At least most times should be there
            results.add_pass("Schedule: Sequential times", f"Found {times_found}/{len(expected_times)} expected times")
        else:
            results.add_fail("Schedule: Sequential times", f"Only found {times_found}/{len(expected_times)} times")
        
        # Test 2: Verify no old times (like 20:00, 19:00, etc.)
        old_times = ["20:00", "19:00", "17:00", "18:00", "12:00", "13:00", "14:00", "15:00", "16:00", "11:00"]
        old_times_count = sum(1 for t in old_times if t in source)
        
        if old_times_count == 0:
            results.add_pass("Schedule: No old times", "Old evening/scattered times removed")
        else:
            results.add_fail("Schedule: No old times", f"Found {old_times_count} references to old times")
    
    except Exception as e:
        results.add_fail("Schedule: Test execution", f"Exception: {e}")


async def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("🧪 CONTENT VALIDATION TESTS")
    print("=" * 60)
    print("Testing all changes from today to prevent regressions\n")
    
    results = TestResults()
    
    # Run all tests
    await test_canary_wharf_content(results)
    await test_weather_cities(results)
    test_job_age_requirement(results)
    test_command_configuration(results)
    test_sequential_schedule(results)
    
    # Print summary
    success = results.print_summary()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review and fix.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
