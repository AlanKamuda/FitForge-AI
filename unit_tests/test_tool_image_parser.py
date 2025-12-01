"""
Unit Tests for Image Parser Tool
================================
Run with: python -m pytest unit_tests/test_tool_image_parser.py -v
Or simply: python unit_tests/test_tool_image_parser.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from tools.image_parser import (
            parse_workout_image,
            validate_workout_data,
            extract_with_regex,
            GEMINI_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   Gemini Available: {GEMINI_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False




def test_parse_missing_file():
    """Test handling of missing image file."""
    print("\n" + "="*60)
    print("TEST 4: Missing File Handling")
    print("="*60)
    
    from tools.image_parser import parse_workout_image
    
    result = parse_workout_image("/nonexistent/path/image.png")
    print(f"Result: {result}")
    
    assert result["status"] == "error", "Should return error status"
    assert "not found" in result["error_message"].lower(), "Should mention file not found"
    print("✅ Missing file handling passed")
    
    return True




def test_parse_real_image():
    """Test parsing a real workout image (if available)."""
    print("\n" + "="*60)
    print("TEST 6: Real Image Parsing (Optional)")
    print("="*60)
    
    from tools.image_parser import parse_workout_image, GEMINI_AVAILABLE
    
    if not GEMINI_AVAILABLE:
        print("⏭️ Skipped: Gemini not available")
        return True
    
    # Look for test images
    test_images_dir = PROJECT_ROOT / "unit_tests" / "test_images"
    if not test_images_dir.exists():
        print(f"ℹ️ Create '{test_images_dir}' and add workout screenshots to test")
        print("⏭️ Skipped: No test images directory")
        return True
    
    images = list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg"))
    if not images:
        print("⏭️ Skipped: No test images found")
        return True
    
    for img_path in images[:3]:  # Test first 3 images
        print(f"\nParsing: {img_path.name}")
        result = parse_workout_image(str(img_path))
        print(f"   Status: {result.get('status')}")
        print(f"   Method: {result.get('extraction_method', 'N/A')}")
        
        if result["status"] in ["success", "partial"]:
            print(f"   Distance: {result.get('distance_km', 'N/A')} km")
            print(f"   Duration: {result.get('duration_min', 'N/A')} min")
            print(f"   Avg HR: {result.get('avg_hr', 'N/A')} bpm")
            print(f"   Confidence: {result.get('confidence', 'N/A')}")
        else:
            print(f"   Error: {result.get('error_message', 'Unknown')}")
    
    print("\n✅ Real image parsing completed")
    return True


def test_tool_docstring():
    """Verify the tool has proper ADK-compatible docstring."""
    print("\n" + "="*60)
    print("TEST 7: ADK Docstring Format")
    print("="*60)
    
    from tools.image_parser import parse_workout_image
    
    doc = parse_workout_image.__doc__
    
    # Check required docstring elements for ADK
    checks = [
        ("Has docstring", doc is not None),
        ("Has Args section", "Args:" in doc),
        ("Has Returns section", "Returns:" in doc),
        ("Has status in returns", "status" in doc.lower()),
        ("Has type hints", "str" in str(parse_workout_image.__annotations__)),
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ Docstring format is ADK-compatible")
    else:
        print("\n⚠️ Some docstring checks failed")
    
    return all_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🧪"*30)
    print("   IMAGE PARSER TOOL - UNIT TESTS")
    print("🧪"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Missing File", test_parse_missing_file),
        ("Real Image", test_parse_real_image),
        ("ADK Docstring", test_tool_docstring),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {name}")
            print(f"   Error: {e}")
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