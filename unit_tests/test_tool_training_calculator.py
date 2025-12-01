# unit_tests/test_tool_training_calculator.py
"""
Unit Tests for Training Calculator Tool
=======================================
Run with: python -m pytest unit_tests/test_tool_training_calculator.py -v
Or simply: python unit_tests/test_tool_training_calculator.py
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
        from tools.training_calculator import (
            calculate_one_rep_max,
            calculate_training_stress,
            calculate_calories_burned,
            calculate_heart_rate_zones,
            convert_pace,
            calculate_body_metrics,
            calculate_training_volume,
            create_calculator_agent,
            get_calculator_tools,
            MET_VALUES,
            ADK_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   MET Values: {len(MET_VALUES)} activities")
        print(f"   Calculator tools: {len(get_calculator_tools())}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_one_rep_max():
    """Test 1RM calculation."""
    print("\n" + "="*60)
    print("TEST 2: One-Rep Max Calculation")
    print("="*60)
    
    from tools.training_calculator import calculate_one_rep_max
    
    # Test case 1: Standard calculation
    result1 = calculate_one_rep_max(100, 5, formula="epley")
    print(f"\n100kg × 5 reps (Epley):")
    print(f"   1RM: {result1['estimated_1rm']} kg")
    print(f"   80% of 1RM: {result1['training_percentages']['80%']} kg")
    
    assert result1["status"] == "success", "Should succeed"
    assert 115 < result1["estimated_1rm"] < 120, "Epley 100x5 should be ~116-117kg"
    print("✅ Epley formula passed")
    
    # Test case 2: Different formula
    result2 = calculate_one_rep_max(100, 5, formula="brzycki")
    print(f"\n100kg × 5 reps (Brzycki): {result2['estimated_1rm']} kg")
    assert result2["status"] == "success", "Should succeed"
    print("✅ Brzycki formula passed")
    
    # Test case 3: Average of all formulas
    result3 = calculate_one_rep_max(100, 5, formula="average")
    print(f"\n100kg × 5 reps (Average): {result3['estimated_1rm']} kg")
    assert result3["status"] == "success", "Should succeed"
    print("✅ Average formula passed")
    
    # Test case 4: Actual 1RM
    result4 = calculate_one_rep_max(140, 1)
    print(f"\n140kg × 1 rep (Actual): {result4['estimated_1rm']} kg")
    assert result4["estimated_1rm"] == 140, "1 rep should return same weight"
    print("✅ Actual 1RM passed")
    
    # Test case 5: Invalid input
    result5 = calculate_one_rep_max(-100, 5)
    assert result5["status"] == "error", "Negative weight should error"
    print("✅ Error handling passed")
    
    return True


def test_training_stress():
    """Test TSS calculation."""
    print("\n" + "="*60)
    print("TEST 3: Training Stress Score (TSS)")
    print("="*60)
    
    from tools.training_calculator import calculate_training_stress
    
    # Test case 1: Easy workout
    result1 = calculate_training_stress(45, intensity="easy", activity_type="running_easy")
    print(f"\n45 min easy run:")
    print(f"   TSS: {result1['tss']}")
    print(f"   Interpretation: {result1['tss_interpretation']}")
    print(f"   Recovery: {result1['recovery_recommendation']}")
    assert result1["status"] == "success", "Should succeed"
    assert result1["tss"] < 50, "Easy 45min should be low TSS"
    print("✅ Easy workout TSS passed")
    
    # Test case 2: Hard workout
    result2 = calculate_training_stress(60, intensity="hard", activity_type="running_hard")
    print(f"\n60 min hard run:")
    print(f"   TSS: {result2['tss']}")
    print(f"   Intensity Factor: {result2['intensity_factor']}")
    assert result2["tss"] > result1["tss"], "Hard should have higher TSS"
    print("✅ Hard workout TSS passed")
    
    # Test case 3: With heart rate data
    result3 = calculate_training_stress(60, activity_type="running_moderate", 
                                        heart_rate_avg=155, heart_rate_max=185)
    print(f"\n60 min with HR data (155 avg, 185 max):")
    print(f"   TSS: {result3['tss']}")
    assert result3["status"] == "success", "Should succeed with HR data"
    print("✅ HR-based TSS passed")
    
    return True


def test_calories_burned():
    """Test calorie calculation."""
    print("\n" + "="*60)
    print("TEST 4: Calories Burned")
    print("="*60)
    
    from tools.training_calculator import calculate_calories_burned
    
    # Test case 1: Standard calculation
    result1 = calculate_calories_burned(75, 45, "running_moderate")
    print(f"\n75kg person, 45min moderate run:")
    print(f"   Calories: {result1['calories_burned']} kcal")
    print(f"   Cal/min: {result1['calories_per_minute']}")
    print(f"   Equivalent: {result1['equivalent_food']['bananas']} bananas")
    
    assert result1["status"] == "success", "Should succeed"
    assert 400 < result1["calories_burned"] < 600, "Should be reasonable calorie range"
    print("✅ Calorie calculation passed")
    
    # Test case 2: Different activity
    result2 = calculate_calories_burned(70, 30, "strength_moderate")
    print(f"\n70kg person, 30min strength:")
    print(f"   Calories: {result2['calories_burned']} kcal")
    assert result2["calories_burned"] < result1["calories_burned"], "Strength burns less than running"
    print("✅ Activity comparison passed")
    
    return True


def test_heart_rate_zones():
    """Test HR zone calculation."""
    print("\n" + "="*60)
    print("TEST 5: Heart Rate Zones")
    print("="*60)
    
    from tools.training_calculator import calculate_heart_rate_zones
    
    # Test case 1: Age-based (percentage method)
    result1 = calculate_heart_rate_zones(age=30)
    print(f"\n30 years old (percentage method):")
    print(f"   Max HR: {result1['max_hr']} bpm")
    for zone, hr_range in result1["zones"].items():
        print(f"   {zone}: {hr_range['min']}-{hr_range['max']} bpm")
    
    assert result1["status"] == "success", "Should succeed"
    assert result1["max_hr"] == 190, "220-30 = 190"
    print("✅ Percentage method passed")
    
    # Test case 2: Karvonen method
    result2 = calculate_heart_rate_zones(age=30, resting_heart_rate=60, method="karvonen")
    print(f"\n30yo with 60bpm resting (Karvonen):")
    print(f"   Zone 2: {result2['zones']['zone2_aerobic']['min']}-{result2['zones']['zone2_aerobic']['max']} bpm")
    
    assert result2["method_used"] == "karvonen", "Should use Karvonen"
    # Karvonen zones should be higher due to HRR calculation
    assert result2["zones"]["zone2_aerobic"]["min"] > result1["zones"]["zone2_aerobic"]["min"]
    print("✅ Karvonen method passed")
    
    # Test case 3: Custom max HR
    result3 = calculate_heart_rate_zones(max_heart_rate=195)
    assert result3["max_hr"] == 195, "Should use provided max HR"
    print("✅ Custom max HR passed")
    
    return True


def test_convert_pace():
    """Test pace conversion."""
    print("\n" + "="*60)
    print("TEST 6: Pace Conversion")
    print("="*60)
    
    from tools.training_calculator import convert_pace
    
    # Test case 1: min/km to min/mi
    result1 = convert_pace(5.0, "min_per_km", "min_per_mi")
    print(f"\n5:00/km to min/mi:")
    print(f"   Result: {result1['formatted']}")
    print(f"   Value: {result1['converted_value']}")
    
    assert result1["status"] == "success", "Should succeed"
    assert 8.0 < result1["converted_value"] < 8.1, "5min/km ≈ 8:03/mi"
    print("✅ min/km to min/mi passed")
    
    # Test case 2: km/h to mph
    result2 = convert_pace(12.0, "km_per_h", "mi_per_h")
    print(f"\n12 km/h to mph: {result2['formatted']}")
    assert 7.4 < result2["converted_value"] < 7.5, "12 km/h ≈ 7.46 mph"
    print("✅ km/h to mph passed")
    
    # Test case 3: All conversions
    result3 = convert_pace(10.0, "km_per_h", "m_per_s")
    print(f"\n10 km/h → all units:")
    for unit, value in result3["all_conversions"].items():
        print(f"   {unit}: {value}")
    print("✅ All conversions passed")
    
    return True


def test_body_metrics():
    """Test body metrics calculation."""
    print("\n" + "="*60)
    print("TEST 7: Body Metrics (BMI, TDEE)")
    print("="*60)
    
    from tools.training_calculator import calculate_body_metrics
    
    # Test case 1: Standard calculation
    result1 = calculate_body_metrics(75, 175, 30, "male", "moderate")
    print(f"\n75kg, 175cm, 30yo male, moderate activity:")
    print(f"   BMI: {result1['bmi']} ({result1['bmi_category']})")
    print(f"   BMR: {result1['bmr']} kcal")
    print(f"   TDEE: {result1['tdee']} kcal")
    print(f"   Macros: {result1['macro_suggestions']['protein_g']}P / {result1['macro_suggestions']['carbs_g']}C / {result1['macro_suggestions']['fat_g']}F")
    
    assert result1["status"] == "success", "Should succeed"
    assert 22 < result1["bmi"] < 26, "BMI for 75kg/175cm should be ~24.5"
    assert 2300 < result1["tdee"] < 2700, "TDEE for active male should be reasonable"
    print("✅ Body metrics calculation passed")
    
    # Test case 2: Female
    result2 = calculate_body_metrics(60, 165, 25, "female", "active")
    print(f"\n60kg, 165cm, 25yo female, active:")
    print(f"   TDEE: {result2['tdee']} kcal")
    
    assert result2["tdee"] < result1["tdee"], "Female typically has lower TDEE"
    print("✅ Female calculation passed")
    
    return True


def test_training_volume():
    """Test volume calculation."""
    print("\n" + "="*60)
    print("TEST 8: Training Volume")
    print("="*60)
    
    from tools.training_calculator import calculate_training_volume
    
    # Test case 1: Single exercise
    result1 = calculate_training_volume(4, 8, 80)
    print(f"\n4 sets × 8 reps × 80kg:")
    print(f"   Volume: {result1['volume_per_exercise']} kg")
    print(f"   Total reps: {result1['total_reps']}")
    
    assert result1["status"] == "success", "Should succeed"
    assert result1["volume_per_exercise"] == 4 * 8 * 80, "Should be 2560kg"
    print("✅ Single exercise volume passed")
    
    # Test case 2: Multiple exercises
    result2 = calculate_training_volume(4, 8, 80, exercises=5)
    print(f"\n5 exercises × 4 sets × 8 reps × 80kg:")
    print(f"   Total volume: {result2['total_volume']} kg")
    print(f"   Category: {result2['volume_category']}")
    print(f"   Progression suggestions:")
    for p in result2["progression_suggestions"]:
        print(f"      {p['method']}: {p['example']}")
    
    assert result2["total_volume"] == 2560 * 5, "Should be 12800kg"
    print("✅ Multiple exercises volume passed")
    
    return True


def test_calculator_agent():
    """Test the ADK calculator agent creation."""
    print("\n" + "="*60)
    print("TEST 9: ADK Calculator Agent")
    print("="*60)
    
    from tools.training_calculator import create_calculator_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent = create_calculator_agent()
    
    if agent:
        print(f"✅ Calculator agent created")
        print(f"   Name: {agent.name}")
        print(f"   Has code executor: {agent.code_executor is not None}")
        assert agent.code_executor is not None, "Should have code executor"
    else:
        print("⚠️ Agent creation returned None (ADK may not be fully configured)")
    
    return True


def test_get_calculator_tools():
    """Test getting all calculator tools."""
    print("\n" + "="*60)
    print("TEST 10: Get Calculator Tools")
    print("="*60)
    
    from tools.training_calculator import get_calculator_tools
    
    tools = get_calculator_tools()
    
    print(f"Found {len(tools)} calculator tools:")
    for tool in tools:
        print(f"   - {tool.__name__}")
    
    assert len(tools) == 7, "Should have 7 calculator tools"
    print("✅ All calculator tools retrieved")
    
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 11: ADK Docstring Format")
    print("="*60)
    
    from tools.training_calculator import get_calculator_tools
    
    tools = get_calculator_tools()
    
    all_passed = True
    for func in tools:
        doc = func.__doc__
        has_doc = doc is not None
        has_args = doc and "Args:" in doc
        has_returns = doc and "Returns:" in doc
        has_example = doc and "Example:" in doc
        
        passed = has_doc and has_args and has_returns
        status = "✅" if passed else "❌"
        print(f"   {status} {func.__name__}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🧮"*30)
    print("   TRAINING CALCULATOR TOOL - UNIT TESTS")
    print("🧮"*30)
    
    tests = [
        ("Imports", test_imports),
        ("One-Rep Max", test_one_rep_max),
        ("Training Stress", test_training_stress),
        ("Calories Burned", test_calories_burned),
        ("Heart Rate Zones", test_heart_rate_zones),
        ("Pace Conversion", test_convert_pace),
        ("Body Metrics", test_body_metrics),
        ("Training Volume", test_training_volume),
        ("Calculator Agent", test_calculator_agent),
        ("Get Tools", test_get_calculator_tools),
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