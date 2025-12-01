# unit_tests/test_agent_nutrition.py
"""
Unit Tests for Nutrition Agent
==============================
Run with: python -m pytest unit_tests/test_agent_nutrition.py -v
Or simply: python unit_tests/test_agent_nutrition.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Mock ToolContext for Testing
# =============================================================================

class MockToolContext:
    """Mock ToolContext for testing without full ADK."""
    
    def __init__(self, state: dict = None):
        self.state = state or {}


# =============================================================================
# TESTS
# =============================================================================

def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from agents.nutrition_agent import (
            log_meal,
            get_daily_nutrition_summary,
            get_macro_targets,
            suggest_next_meal,
            analyze_meal_balance,
            get_recovery_nutrition_score,
            log_water_intake,
            create_nutrition_agent,
            calculate_macro_targets,
            calculate_recovery_score,
            NUTRITION_CONFIG,
            ADK_AVAILABLE,
            NUTRITION_PARSER_READY,
            GEMINI_READY
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Nutrition Parser: {NUTRITION_PARSER_READY}")
        print(f"   Gemini: {GEMINI_READY}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_calculate_macro_targets():
    """Test macro target calculation."""
    print("\n" + "="*60)
    print("TEST 2: Calculate Macro Targets")
    print("="*60)
    
    from agents.nutrition_agent import calculate_macro_targets
    
    # Test for different goals
    goals = ["muscle_gain", "fat_loss", "maintenance"]
    
    all_passed = True
    for goal in goals:
        targets = calculate_macro_targets(75, goal, "moderate")
        
        print(f"   {goal}: {targets['calories']} kcal, {targets['protein_g']}g P")
        
        assert targets["calories"] > 0, f"Calories should be positive for {goal}"
        assert targets["protein_g"] > 0, f"Protein should be positive for {goal}"
        assert targets["carbs_g"] > 0, f"Carbs should be positive for {goal}"
        assert targets["fat_g"] > 0, f"Fat should be positive for {goal}"
    
    # Muscle gain should have more calories than fat loss
    muscle = calculate_macro_targets(75, "muscle_gain")
    fat_loss = calculate_macro_targets(75, "fat_loss")
    assert muscle["calories"] > fat_loss["calories"], "Muscle gain should have more calories"
    
    print("✅ Macro targets calculation passed")
    return True


def test_calculate_recovery_score():
    """Test recovery score calculation."""
    print("\n" + "="*60)
    print("TEST 3: Calculate Recovery Score")
    print("="*60)
    
    from agents.nutrition_agent import calculate_recovery_score
    
    targets = {"protein_g": 150, "carbs_g": 300, "calories": 2500}
    
    # Test good nutrition
    good_totals = {"total_protein_g": 160, "total_carbs_g": 280}
    good_score = calculate_recovery_score(good_totals, targets)
    
    print(f"   Good nutrition: {good_score['recovery_score']}/100 ({good_score['label']})")
    assert good_score["recovery_score"] >= 80, "Good nutrition should score 80+"
    
    # Test poor nutrition
    poor_totals = {"total_protein_g": 50, "total_carbs_g": 100}
    poor_score = calculate_recovery_score(poor_totals, targets)
    
    print(f"   Poor nutrition: {poor_score['recovery_score']}/100 ({poor_score['label']})")
    assert poor_score["recovery_score"] < 60, "Poor nutrition should score under 60"
    
    print("✅ Recovery score calculation passed")
    return True


def test_log_meal_basic():
    """Test basic meal logging."""
    print("\n" + "="*60)
    print("TEST 4: Log Meal (Basic)")
    print("="*60)
    
    from agents.nutrition_agent import log_meal
    
    ctx = MockToolContext(state={})
    
    result = log_meal(ctx, "2 eggs with toast and avocado", "breakfast")
    
    print(f"   Status: {result['status']}")
    print(f"   Meal Type: {result.get('meal_type')}")
    print(f"   Macros: {result.get('macros')}")
    print(f"   Message: {result.get('message', '')[:50]}...")
    
    assert result["status"] in ["success", "partial"], "Should parse successfully"
    assert result.get("meal_id"), "Should have meal ID"
    assert result.get("daily_running_total"), "Should have running total"
    
    # Check state was updated
    today_key = datetime.now().strftime("%Y-%m-%d")
    log_key = f"nutrition:{today_key}"
    assert ctx.state.get(log_key), "Should save to state"
    
    print("✅ Basic meal logging passed")
    return True


def test_log_meal_multiple():
    """Test logging multiple meals."""
    print("\n" + "="*60)
    print("TEST 5: Log Multiple Meals")
    print("="*60)
    
    from agents.nutrition_agent import log_meal
    
    ctx = MockToolContext(state={})
    
    meals = [
        ("oatmeal with banana", "breakfast"),
        ("chicken breast with rice", "lunch"),
        ("protein shake", "post_workout"),
    ]
    
    for desc, meal_type in meals:
        result = log_meal(ctx, desc, meal_type)
        print(f"   {meal_type}: {result.get('macros', {}).get('calories', 0)} kcal")
    
    # Check running totals
    final_total = result["daily_running_total"]
    print(f"   Daily Total: {final_total['calories']} kcal, {final_total['protein_g']}g P")
    
    assert final_total["calories"] > 0, "Should accumulate calories"
    assert final_total["protein_g"] > 0, "Should accumulate protein"
    
    # Check meal count
    today_key = datetime.now().strftime("%Y-%m-%d")
    log = ctx.state.get(f"nutrition:{today_key}")
    assert len(log["meals"]) == 3, "Should have 3 meals"
    
    print("✅ Multiple meals logging passed")
    return True


def test_log_meal_empty():
    """Test logging with empty description."""
    print("\n" + "="*60)
    print("TEST 6: Log Meal (Empty)")
    print("="*60)
    
    from agents.nutrition_agent import log_meal
    
    ctx = MockToolContext(state={})
    
    result = log_meal(ctx, "")
    
    print(f"   Status: {result['status']}")
    print(f"   Error: {result.get('error_message')}")
    
    assert result["status"] == "error", "Should fail with empty description"
    
    print("✅ Empty meal handling passed")
    return True


def test_get_daily_summary():
    """Test daily nutrition summary."""
    print("\n" + "="*60)
    print("TEST 7: Get Daily Summary")
    print("="*60)
    
    from agents.nutrition_agent import log_meal, get_daily_nutrition_summary
    
    ctx = MockToolContext(state={
        "user:weight_kg": 75,
        "user:fitness_goal": "muscle_gain"
    })
    
    # Log some meals first
    log_meal(ctx, "3 eggs, 2 toast", "breakfast")
    log_meal(ctx, "chicken rice bowl 300g", "lunch")
    
    # Get summary
    result = get_daily_nutrition_summary(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Totals: {result.get('totals')}")
    print(f"   Progress: {result.get('progress')}")
    print(f"   Recovery: {result.get('recovery_score')}/100")
    
    assert result["status"] == "success", "Should succeed with data"
    assert result.get("totals"), "Should have totals"
    assert result.get("progress"), "Should have progress"
    assert result.get("recommendations"), "Should have recommendations"
    
    print("✅ Daily summary passed")
    return True


def test_get_daily_summary_no_data():
    """Test daily summary with no meals."""
    print("\n" + "="*60)
    print("TEST 8: Daily Summary (No Data)")
    print("="*60)
    
    from agents.nutrition_agent import get_daily_nutrition_summary
    
    ctx = MockToolContext(state={})
    
    result = get_daily_nutrition_summary(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Message: {result.get('message')}")
    
    assert result["status"] == "no_data", "Should indicate no data"
    assert result.get("tips"), "Should provide tips"
    
    print("✅ No data summary handling passed")
    return True





def test_get_macro_targets_with_override():
    """Test macro targets with parameter override."""
    print("\n" + "="*60)
    print("TEST 10: Macro Targets (Override)")
    print("="*60)
    
    from agents.nutrition_agent import get_macro_targets
    
    ctx = MockToolContext(state={})
    
    result = get_macro_targets(ctx, weight_kg=90, goal="fat_loss")
    
    print(f"   Based on: {result.get('based_on')}")
    print(f"   Calories: {result['daily_targets']['calories']}")
    
    assert result["based_on"]["weight_kg"] == 90, "Should use override weight"
    assert result["based_on"]["goal"] == "fat_loss", "Should use override goal"
    
    print("✅ Macro targets override passed")
    return True


def test_suggest_next_meal_specific_goal():
    """Test meal suggestion with specific goal."""
    print("\n" + "="*60)
    print("TEST 12: Suggest Meal (Specific Goal)")
    print("="*60)
    
    from agents.nutrition_agent import suggest_next_meal
    
    ctx = MockToolContext(state={
        "user:weight_kg": 75
    })
    
    result = suggest_next_meal(ctx, specific_goal="high_protein")
    
    print(f"   Goal: high_protein")
    print(f"   Suggestions: {[s.get('name') for s in result.get('suggestions', [])[:3]]}")
    
    assert result["status"] == "success", "Should succeed"
    
    print("✅ Specific goal suggestion passed")
    return True


def test_recovery_nutrition_score():
    """Test recovery nutrition score tool."""
    print("\n" + "="*60)
    print("TEST 13: Recovery Nutrition Score")
    print("="*60)
    
    from agents.nutrition_agent import log_meal, get_recovery_nutrition_score
    
    ctx = MockToolContext(state={
        "user:weight_kg": 75,
        "user:fitness_goal": "muscle_gain"
    })
    
    # Log good post-workout nutrition
    log_meal(ctx, "whey protein shake with banana and oats", "post_workout")
    log_meal(ctx, "chicken breast 200g with rice 150g", "lunch")
    
    result = get_recovery_nutrition_score(ctx, workout_intensity="high")
    
    print(f"   Status: {result['status']}")
    print(f"   Score: {result.get('recovery_score')}/100")
    print(f"   Label: {result.get('label')}")
    print(f"   Advice: {result.get('advice', [])[:2]}")
    
    assert result["status"] == "success", "Should succeed"
    assert result.get("recovery_score") >= 0, "Should have valid score"
    assert result.get("breakdown"), "Should have breakdown"
    
    print("✅ Recovery nutrition score passed")
    return True


def test_recovery_score_no_data():
    """Test recovery score with no nutrition data."""
    print("\n" + "="*60)
    print("TEST 14: Recovery Score (No Data)")
    print("="*60)
    
    from agents.nutrition_agent import get_recovery_nutrition_score
    
    ctx = MockToolContext(state={})
    
    result = get_recovery_nutrition_score(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Message: {result.get('message')}")
    
    assert result["status"] == "no_data", "Should indicate no data"
    
    print("✅ No data recovery score passed")
    return True


def test_log_water_intake():
    """Test water intake logging."""
    print("\n" + "="*60)
    print("TEST 15: Log Water Intake")
    print("="*60)
    
    from agents.nutrition_agent import log_water_intake
    
    ctx = MockToolContext(state={
        "user:weight_kg": 75
    })
    
    # Log water
    result1 = log_water_intake(ctx, 500, "morning")
    print(f"   First: {result1['daily_total_ml']}ml / {result1['daily_target_ml']}ml")
    
    result2 = log_water_intake(ctx, 750, "with lunch")
    print(f"   After lunch: {result2['daily_total_ml']}ml")
    
    result3 = log_water_intake(ctx, 1000)
    print(f"   Progress: {result3['progress_percent']}%")
    
    assert result1["status"] == "success", "Should succeed"
    assert result3["daily_total_ml"] == 2250, "Should accumulate"
    assert result3["progress_percent"] > 0, "Should show progress"
    
    print("✅ Water intake logging passed")
    return True


def test_analyze_meal_balance():
    """Test meal balance analysis."""
    print("\n" + "="*60)
    print("TEST 16: Analyze Meal Balance")
    print("="*60)
    
    from agents.nutrition_agent import analyze_meal_balance
    
    # Create state with multiple days of data
    ctx = MockToolContext(state={})
    
    # Simulate 3 days of data
    for i in range(3):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        ctx.state[f"nutrition:{date}"] = {
            "date": date,
            "meals": [{"type": "lunch"}],
            "total_calories": 2000 + i * 100,
            "total_protein_g": 120 + i * 10,
            "total_carbs_g": 250,
            "total_fat_g": 70
        }
    
    result = analyze_meal_balance(ctx, days=7)
    
    print(f"   Status: {result['status']}")
    print(f"   Days analyzed: {result.get('days_analyzed')}")
    print(f"   Average daily: {result.get('average_daily')}")
    print(f"   Consistency: {result.get('consistency_score')}")
    
    assert result["status"] == "success", "Should succeed with data"
    assert result.get("days_analyzed") >= 3, "Should analyze available days"
    assert result.get("patterns"), "Should identify patterns"
    
    print("✅ Meal balance analysis passed")
    return True


def test_analyze_meal_balance_insufficient():
    """Test meal analysis with insufficient data."""
    print("\n" + "="*60)
    print("TEST 17: Analyze Balance (Insufficient)"  )
    print("="*60)
    
    from agents.nutrition_agent import analyze_meal_balance
    
    ctx = MockToolContext(state={})
    
    result = analyze_meal_balance(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Days: {result.get('days_with_data')}")
    
    assert result["status"] == "insufficient_data", "Should indicate insufficient data"
    
    print("✅ Insufficient data handling passed")
    return True


def test_create_nutrition_agent():
    """Test nutrition agent creation."""
    print("\n" + "="*60)
    print("TEST 18: Create Nutrition Agent")
    print("="*60)
    
    from agents.nutrition_agent import create_nutrition_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent = create_nutrition_agent(use_memory_preload=False)
    
    if agent:
        print(f"✅ Agent created: {agent.name}")
        print(f"   Description: {agent.description[:50]}...")
        print(f"   Tools: {len(agent.tools)}")
        
        # List tools
        for i, tool in enumerate(agent.tools[:7]):
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool).__name__)))
            print(f"      {i+1}. {tool_name}")
        if len(agent.tools) > 7:
            print(f"      ... and {len(agent.tools) - 7} more")
    else:
        print("⚠️ Agent creation returned None")
    
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 19: ADK Docstring Format")
    print("="*60)
    
    from agents.nutrition_agent import (
        log_meal,
        get_daily_nutrition_summary,
        get_macro_targets,
        suggest_next_meal,
        analyze_meal_balance,
        get_recovery_nutrition_score,
        log_water_intake
    )
    
    tools = [
        ("log_meal", log_meal),
        ("get_daily_nutrition_summary", get_daily_nutrition_summary),
        ("get_macro_targets", get_macro_targets),
        ("suggest_next_meal", suggest_next_meal),
        ("analyze_meal_balance", analyze_meal_balance),
        ("get_recovery_nutrition_score", get_recovery_nutrition_score),
        ("log_water_intake", log_water_intake),
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


def test_complete_workflow():
    """Test complete nutrition workflow."""
    print("\n" + "="*60)
    print("TEST 20: Complete Workflow")
    print("="*60)
    
    from agents.nutrition_agent import (
        log_meal,
        get_macro_targets,
        get_daily_nutrition_summary,
        suggest_next_meal,
        get_recovery_nutrition_score,
        log_water_intake
    )
    
    ctx = MockToolContext(state={
        "user:weight_kg": 75,
        "user:fitness_goal": "muscle_gain",
        "user:name": "Test Athlete"
    })
    
    # Step 1: Get targets
    print("   Step 1: Get macro targets")
    targets = get_macro_targets(ctx)
    print(f"      → {targets['daily_targets']['calories']} kcal target")
    
    # Step 2: Log breakfast
    print("   Step 2: Log breakfast")
    breakfast = log_meal(ctx, "oatmeal with protein powder and banana", "breakfast")
    print(f"      → {breakfast['macros']['calories']} kcal logged")
    
    # Step 3: Log water
    print("   Step 3: Log water")
    water = log_water_intake(ctx, 500)
    print(f"      → {water['daily_total_ml']}ml logged")
    
    # Step 4: Get suggestion for lunch
    print("   Step 4: Get lunch suggestion")
    suggestion = suggest_next_meal(ctx)
    print(f"      → Suggested: {suggestion['suggested_meal_type']}")
    
    # Step 5: Log lunch
    print("   Step 5: Log lunch")
    lunch = log_meal(ctx, "grilled chicken 200g with brown rice", "lunch")
    print(f"      → {lunch['macros']['protein_g']}g protein")
    
    # Step 6: Check daily summary
    print("   Step 6: Check daily summary")
    summary = get_daily_nutrition_summary(ctx)
    print(f"      → Progress: {summary['progress']['protein']}% protein")
    
    # Step 7: Recovery score
    print("   Step 7: Get recovery score")
    recovery = get_recovery_nutrition_score(ctx, "moderate")
    print(f"      → Score: {recovery['recovery_score']}/100")
    
    print("✅ Complete workflow passed")
    return True


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🥗"*30)
    print("   NUTRITION AGENT - UNIT TESTS")
    print("🥗"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Calculate Macro Targets", test_calculate_macro_targets),
        ("Calculate Recovery Score", test_calculate_recovery_score),
        ("Log Meal Basic", test_log_meal_basic),
        ("Log Multiple Meals", test_log_meal_multiple),
        ("Log Meal Empty", test_log_meal_empty),
        ("Daily Summary", test_get_daily_summary),
        ("Summary No Data", test_get_daily_summary_no_data),
        ("Macro Targets Override", test_get_macro_targets_with_override),
        ("Suggest Specific Goal", test_suggest_next_meal_specific_goal),
        ("Recovery Score", test_recovery_nutrition_score),
        ("Recovery No Data", test_recovery_score_no_data),
        ("Log Water", test_log_water_intake),
        ("Analyze Balance", test_analyze_meal_balance),
        ("Analyze Insufficient", test_analyze_meal_balance_insufficient),
        ("Create Agent", test_create_nutrition_agent),
        ("ADK Docstrings", test_tool_docstrings),
        ("Complete Workflow", test_complete_workflow),
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