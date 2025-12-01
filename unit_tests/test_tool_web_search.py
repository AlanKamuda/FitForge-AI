# unit_tests/test_tool_web_search.py
"""
Unit Tests for Web Search Tool
==============================
Run with: python -m pytest unit_tests/test_tool_web_search.py -v
Or simply: python unit_tests/test_tool_web_search.py

Note: Some tests require internet connection and may be slow.
"""

import os
import sys
from pathlib import Path
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from tools.web_search import (
            web_search,
            search_fitness_research,
            search_injury_protocol,
            search_exercise_info,
            get_google_search_tool,
            DDGS_AVAILABLE,
            GOOGLE_SEARCH_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   DuckDuckGo available: {DDGS_AVAILABLE}")
        print(f"   Google Search available: {GOOGLE_SEARCH_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_input_validation():
    """Test input validation for web_search."""
    print("\n" + "="*60)
    print("TEST 2: Input Validation")
    print("="*60)
    
    from tools.web_search import web_search
    
    # Empty query
    result1 = web_search("")
    assert result1["status"] == "error", "Empty query should error"
    print("✅ Empty query handling passed")
    
    # None query
    result2 = web_search(None)
    assert result2["status"] == "error", "None query should error"
    print("✅ None query handling passed")
    
    # Too short query
    result3 = web_search("ab")
    assert result3["status"] == "error", "Short query should error"
    print("✅ Short query handling passed")
    
    return True


def test_basic_search():
    """Test basic web search functionality."""
    print("\n" + "="*60)
    print("TEST 3: Basic Search (requires internet)")
    print("="*60)
    
    from tools.web_search import web_search, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    # Simple search
    query = "benefits of strength training"
    print(f"Searching: '{query}'")
    
    result = web_search(query, max_results=3)
    
    print(f"Status: {result['status']}")
    print(f"Engine: {result.get('search_engine', 'N/A')}")
    print(f"Results: {result.get('result_count', 0)}")
    
    if result["status"] == "success":
        print(f"First result: {result['results'][0]['title'][:50]}...")
        assert result["result_count"] > 0, "Should have results"
        assert "summary" in result, "Should have summary"
        print("✅ Basic search passed")
    else:
        print(f"⚠️ Search failed: {result.get('error_message', 'Unknown')}")
        print("   (May be rate limited or network issue)")
    
    # Add delay to avoid rate limiting
    time.sleep(1)
    
    return True


def test_fitness_search():
    """Test fitness-specific search."""
    print("\n" + "="*60)
    print("TEST 4: Fitness Search (requires internet)")
    print("="*60)
    
    from tools.web_search import web_search, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    query = "best exercises for lower back"
    print(f"Searching (fitness type): '{query}'")
    
    result = web_search(query, max_results=3, search_type="fitness")
    
    print(f"Status: {result['status']}")
    print(f"Original query: {result.get('original_query', 'N/A')}")
    print(f"Enhanced query: {result.get('query', 'N/A')}")
    
    if result["status"] == "success":
        # Check if query was enhanced
        if result.get("query") != result.get("original_query"):
            print("✅ Query was enhanced with fitness context")
        print("✅ Fitness search passed")
    else:
        print(f"⚠️ Search failed (may be network issue)")
    
    time.sleep(1)
    return True


def test_search_fitness_research():
    """Test the specialized fitness research search."""
    print("\n" + "="*60)
    print("TEST 5: Fitness Research Search (requires internet)")
    print("="*60)
    
    from tools.web_search import search_fitness_research, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    topic = "creatine supplementation"
    print(f"Researching: '{topic}' (focus: strength)")
    
    result = search_fitness_research(topic, focus_area="strength")
    
    print(f"Status: {result['status']}")
    
    if result["status"] == "success":
        print(f"Evidence quality: {result.get('evidence_quality', 'N/A')}")
        print(f"Quality note: {result.get('quality_note', 'N/A')}")
        print(f"Results: {result.get('result_count', 0)}")
        print("✅ Fitness research search passed")
    else:
        print(f"⚠️ Search failed (may be network issue)")
    
    time.sleep(1)
    return True


def test_search_injury_protocol():
    """Test the injury protocol search."""
    print("\n" + "="*60)
    print("TEST 6: Injury Protocol Search (requires internet)")
    print("="*60)
    
    from tools.web_search import search_injury_protocol, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    description = "runner's knee pain"
    print(f"Searching: '{description}' (body part: knee)")
    
    result = search_injury_protocol(description, body_part="knee")
    
    print(f"Status: {result['status']}")
    
    if result["status"] == "success":
        print(f"Has disclaimer: {'disclaimer' in result}")
        print(f"Has warning signs: {'when_to_see_doctor' in result}")
        assert "disclaimer" in result, "Should include medical disclaimer"
        assert "when_to_see_doctor" in result, "Should include warning signs"
        print("✅ Injury protocol search passed")
    else:
        print(f"⚠️ Search failed (may be network issue)")
    
    time.sleep(1)
    return True


def test_search_exercise_info():
    """Test the exercise info search."""
    print("\n" + "="*60)
    print("TEST 7: Exercise Info Search (requires internet)")
    print("="*60)
    
    from tools.web_search import search_exercise_info, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    exercise = "Romanian deadlift"
    print(f"Searching: '{exercise}' (info type: technique)")
    
    result = search_exercise_info(exercise, info_type="technique")
    
    print(f"Status: {result['status']}")
    
    if result["status"] == "success":
        print(f"Exercise: {result.get('exercise')}")
        print(f"Info type: {result.get('info_type')}")
        print(f"Results: {len(result.get('information', []))}")
        print("✅ Exercise info search passed")
    else:
        print(f"⚠️ Search failed (may be network issue)")
    
    return True


def test_google_search_wrapper():
    """Test the Google Search wrapper."""
    print("\n" + "="*60)
    print("TEST 8: Google Search Wrapper")
    print("="*60)
    
    from tools.web_search import get_google_search_tool, GOOGLE_SEARCH_AVAILABLE
    
    tool = get_google_search_tool()
    
    if GOOGLE_SEARCH_AVAILABLE:
        assert tool is not None, "Should return tool when available"
        print(f"✅ Google Search tool retrieved: {type(tool)}")
    else:
        assert tool is None, "Should return None when not available"
        print("✅ Correctly returns None when Google Search unavailable")
    
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 9: ADK Docstring Format")
    print("="*60)
    
    from tools.web_search import (
        web_search,
        search_fitness_research,
        search_injury_protocol,
        search_exercise_info
    )
    
    tools = [
        ("web_search", web_search),
        ("search_fitness_research", search_fitness_research),
        ("search_injury_protocol", search_injury_protocol),
        ("search_exercise_info", search_exercise_info),
    ]
    
    all_passed = True
    for name, func in tools:
        doc = func.__doc__
        has_doc = doc is not None
        has_args = doc and "Args:" in doc
        has_returns = doc and "Returns:" in doc
        has_example = doc and "Example:" in doc
        
        passed = has_doc and has_args and has_returns
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        print(f"      Doc: {has_doc}, Args: {has_args}, Returns: {has_returns}, Example: {has_example}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_max_results_clamping():
    """Test that max_results is properly clamped."""
    print("\n" + "="*60)
    print("TEST 10: Max Results Clamping")
    print("="*60)
    
    from tools.web_search import web_search, DDGS_AVAILABLE
    
    if not DDGS_AVAILABLE:
        print("⏭️ Skipped: DuckDuckGo not available")
        return True
    
    # Test with very high value
    result = web_search("test query", max_results=100)
    
    if result["status"] == "success":
        assert result["result_count"] <= 10, "Should clamp to max 10"
        print(f"✅ Results clamped: requested 100, got {result['result_count']}")
    else:
        print("⚠️ Search failed (testing clamp logic skipped)")
    
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🔍"*30)
    print("   WEB SEARCH TOOL - UNIT TESTS")
    print("🔍"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Input Validation", test_input_validation),
        ("Basic Search", test_basic_search),
        ("Fitness Search", test_fitness_search),
        ("Fitness Research", test_search_fitness_research),
        ("Injury Protocol", test_search_injury_protocol),
        ("Exercise Info", test_search_exercise_info),
        ("Google Wrapper", test_google_search_wrapper),
        ("ADK Docstrings", test_tool_docstrings),
        ("Max Results", test_max_results_clamping),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"   {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)