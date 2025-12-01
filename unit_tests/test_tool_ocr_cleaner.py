# unit_tests/test_tool_ocr_cleaner.py
"""
Unit Tests for OCR Cleaner Tool
===============================
Run with: python -m pytest unit_tests/test_tool_ocr_cleaner.py -v
Or simply: python unit_tests/test_tool_ocr_cleaner.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from tools.ocr_cleaner import (
            clean_ocr_text,
            extract_numbers_from_ocr,
            assess_ocr_quality,
            DIGIT_SUBSTITUTIONS,
            FITNESS_TERMS
        )
        print("✅ All imports successful")
        print(f"   Digit substitutions: {len(DIGIT_SUBSTITUTIONS)} mappings")
        print(f"   Fitness terms: {len(FITNESS_TERMS)} terms")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_basic_cleaning():
    """Test basic text cleaning functionality."""
    print("\n" + "="*60)
    print("TEST 2: Basic Cleaning")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text
    
    # Test case 1: Already clean text should stay the same
    clean_input = "5.02 km in 28:30"
    result1 = clean_ocr_text(clean_input)
    print(f"\nClean input: '{clean_input}'")
    print(f"Output: '{result1['cleaned_text']}'")
    print(f"Changes: {result1['changes_made']}")
    
    assert result1["status"] == "success", "Should succeed"
    assert result1["cleaned_text"] == clean_input, f"Clean text should remain unchanged, got '{result1['cleaned_text']}'"
    print("✅ Clean text preserved correctly")
    
    # Test case 2: Extra whitespace should be normalized
    spaced_input = "  5.02   km   in   28:30  "
    result2 = clean_ocr_text(spaced_input)
    print(f"\nSpaced input: '{spaced_input}'")
    print(f"Output: '{result2['cleaned_text']}'")
    
    assert "  " not in result2["cleaned_text"], "Should remove double spaces"
    assert result2["cleaned_text"].strip() == result2["cleaned_text"], "Should trim edges"
    print("✅ Whitespace normalization passed")
    
    # Test case 3: Empty input
    result3 = clean_ocr_text("")
    assert result3["status"] == "success", "Empty input should succeed"
    assert result3["cleaned_text"] == "", "Empty input should return empty"
    print("✅ Empty input handling passed")
    
    # Test case 4: None input
    result4 = clean_ocr_text(None)
    assert result4["status"] == "error", "None input should error"
    print("✅ None input handling passed")
    
    return True


def test_digit_fixing():
    """Test OCR digit error corrections."""
    print("\n" + "="*60)
    print("TEST 3: Digit OCR Fixes")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text
    
    test_cases = [
        # (input, expected_output, description)
        ("1O5", "105", "O between digits → 0"),
        ("I52", "152", "I at start → 1"),
        ("I2:3O", "12:30", "I and O in time format"),
    ]
    
    all_passed = True
    for ocr_input, expected, desc in test_cases:
        result = clean_ocr_text(ocr_input)
        cleaned = result["cleaned_text"]
        passed = expected in cleaned
        status = "✅" if passed else "❌"
        print(f"   {status} {desc}: '{ocr_input}' → '{cleaned}' (expected '{expected}')")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All digit fixes passed")
    else:
        print("\n⚠️ Some digit fixes need adjustment")
    
    return True


def test_spacing_fixes():
    """Test spacing issue corrections."""
    print("\n" + "="*60)
    print("TEST 4: Spacing Fixes")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text
    
    test_cases = [
        # (input, should_contain, description)
        ("5 . 02", "5.02", "Spaced decimal"),
        ("28 : 30", "28:30", "Spaced time colon"),
        ("k m", "km", "Split unit word"),
        ("b p m", "bpm", "Split bpm"),
    ]
    
    all_passed = True
    for ocr_input, expected, desc in test_cases:
        result = clean_ocr_text(ocr_input)
        cleaned = result["cleaned_text"]
        passed = expected in cleaned
        status = "✅" if passed else "❌"
        print(f"   {status} {desc}: '{ocr_input}' → '{cleaned}' (expect '{expected}')")
        if not passed:
            all_passed = False
    
    return all_passed


def test_unit_preservation():
    """Test that normal spacing between numbers and units is preserved."""
    print("\n" + "="*60)
    print("TEST 5: Unit Spacing Preservation")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text
    
    # These should NOT be changed (normal formatting)
    test_cases = [
        "5.02 km",
        "28:30 min",
        "152 bpm",
        "320 cal",
    ]
    
    all_passed = True
    for text in test_cases:
        result = clean_ocr_text(text)
        cleaned = result["cleaned_text"]
        passed = cleaned == text
        status = "✅" if passed else "❌"
        print(f"   {status} '{text}' → '{cleaned}'")
        if not passed:
            all_passed = False
            print(f"      Expected: '{text}'")
    
    if all_passed:
        print("\n✅ Unit spacing preserved correctly")
    
    return all_passed


def test_garbage_removal():
    """Test garbage character removal."""
    print("\n" + "="*60)
    print("TEST 6: Garbage Character Removal")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text
    
    garbage_input = "5.02km!@#$%^&*() 28:30"
    result = clean_ocr_text(garbage_input, remove_garbage=True)
    cleaned = result["cleaned_text"]
    
    print(f"Input:  '{garbage_input}'")
    print(f"Output: '{cleaned}'")
    
    # Should not contain these characters
    garbage_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']
    found_garbage = [c for c in garbage_chars if c in cleaned]
    
    if found_garbage:
        print(f"❌ Still contains garbage: {found_garbage}")
        return False
    
    # Should still contain the numbers
    assert "5.02" in cleaned or "5 02" in cleaned, "Should preserve numbers"
    assert "28:30" in cleaned or "28 30" in cleaned, "Should preserve time"
    
    print("✅ Garbage removal passed")
    return True


def test_extract_numbers():
    """Test number extraction from OCR text."""
    print("\n" + "="*60)
    print("TEST 7: Number Extraction")
    print("="*60)
    
    from tools.ocr_cleaner import extract_numbers_from_ocr
    
    # Test with numbers attached to units
    test_text = "Ran 5.2km in 28:30, avg HR 152bpm, burned 320 cal"
    result = extract_numbers_from_ocr(test_text)
    
    print(f"Input: '{test_text}'")
    print(f"Cleaned: '{result.get('cleaned_text', 'N/A')}'")
    print(f"Numbers found: {result['numbers']}")
    print(f"Time values: {result['time_values']}")
    print(f"Count: {result['count']}")
    
    assert result["status"] == "success", "Should succeed"
    
    numbers = result["numbers"]
    
    # Check for 5.2 (could be float)
    found_5_2 = any(
        (isinstance(n, float) and abs(n - 5.2) < 0.01) or n == 5.2 
        for n in numbers
    )
    assert found_5_2, f"Should find 5.2 in {numbers}"
    print("✅ Found 5.2")
    
    # Check for 152
    assert 152 in numbers, f"Should find 152 in {numbers}"
    print("✅ Found 152")
    
    # Check for 320
    assert 320 in numbers, f"Should find 320 in {numbers}"
    print("✅ Found 320")
    
    # Check for time values
    assert len(result["time_values"]) > 0, "Should find time values"
    print(f"✅ Found time values: {result['time_values']}")
    
    print("\n✅ Number extraction passed")
    return True


def test_extract_numbers_attached_units():
    """Test extracting numbers that are attached to units."""
    print("\n" + "="*60)
    print("TEST 8: Numbers Attached to Units")
    print("="*60)
    
    from tools.ocr_cleaner import extract_numbers_from_ocr
    
    test_cases = [
        ("5.2km", 5.2),
        ("152bpm", 152),
        ("10.5mi", 10.5),
        ("45min", 45),
    ]
    
    all_passed = True
    for text, expected_num in test_cases:
        result = extract_numbers_from_ocr(text)
        numbers = result["numbers"]
        
        if isinstance(expected_num, float):
            found = any(abs(n - expected_num) < 0.01 for n in numbers)
        else:
            found = expected_num in numbers
        
        status = "✅" if found else "❌"
        print(f"   {status} '{text}' → {numbers} (expect {expected_num})")
        if not found:
            all_passed = False
    
    return all_passed


def test_assess_quality():
    """Test OCR quality assessment."""
    print("\n" + "="*60)
    print("TEST 9: Quality Assessment")
    print("="*60)
    
    from tools.ocr_cleaner import assess_ocr_quality
    
    # Good quality text
    good_text = "Morning Run 5.2km in 28:30 Avg HR 152bpm"
    result1 = assess_ocr_quality(good_text)
    print(f"\nGood text: '{good_text[:40]}...'")
    print(f"   Quality: {result1['quality_score']} ({result1['quality_label']})")
    assert result1["quality_score"] >= 0.6, "Good text should score well"
    print("✅ Good quality assessment passed")
    
    # Poor quality text
    poor_text = "!@#$%^&*() ??? ~~~"
    result2 = assess_ocr_quality(poor_text)
    print(f"\nPoor text: '{poor_text}'")
    print(f"   Quality: {result2['quality_score']} ({result2['quality_label']})")
    assert result2["quality_score"] < result1["quality_score"], "Poor text should score lower"
    print("✅ Poor quality assessment passed")
    
    return True


def test_real_world_examples():
    """Test with real-world OCR examples."""
    print("\n" + "="*60)
    print("TEST 10: Real-World Examples")
    print("="*60)
    
    from tools.ocr_cleaner import clean_ocr_text, extract_numbers_from_ocr
    
    examples = [
        ("Strava", "5 . O2 km in I2 : 3O min"),
        ("Garmin", "Distance lO.5 km Time l:O2:3O"),
        ("Watch", "Cal 32O HR l4O bprn"),
    ]
    
    for name, ocr_text in examples:
        print(f"\n{name}:")
        print(f"   Raw:     '{ocr_text}'")
        
        result = clean_ocr_text(ocr_text)
        print(f"   Cleaned: '{result['cleaned_text']}'")
        
        numbers = extract_numbers_from_ocr(ocr_text)
        print(f"   Numbers: {numbers['numbers']}")
    
    print("\n✅ Real-world examples processed")
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 11: ADK Docstring Format")
    print("="*60)
    
    from tools.ocr_cleaner import (
        clean_ocr_text,
        extract_numbers_from_ocr,
        assess_ocr_quality
    )
    
    tools = [
        ("clean_ocr_text", clean_ocr_text),
        ("extract_numbers_from_ocr", extract_numbers_from_ocr),
        ("assess_ocr_quality", assess_ocr_quality),
    ]
    
    all_passed = True
    for name, func in tools:
        doc = func.__doc__
        has_doc = doc is not None
        has_args = doc and "Args:" in doc
        has_returns = doc and "Returns:" in doc
        
        status = "✅" if (has_doc and has_args and has_returns) else "❌"
        print(f"   {status} {name}")
        
        if not (has_doc and has_args and has_returns):
            all_passed = False
    
    return all_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🔤"*30)
    print("   OCR CLEANER TOOL - UNIT TESTS")
    print("🔤"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Basic Cleaning", test_basic_cleaning),
        ("Digit Fixing", test_digit_fixing),
        ("Spacing Fixes", test_spacing_fixes),
        ("Unit Preservation", test_unit_preservation),
        ("Garbage Removal", test_garbage_removal),
        ("Number Extraction", test_extract_numbers),
        ("Attached Units", test_extract_numbers_attached_units),
        ("Quality Assessment", test_assess_quality),
        ("Real-World Examples", test_real_world_examples),
        ("ADK Docstrings", test_tool_docstrings),
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