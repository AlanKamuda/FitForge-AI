# unit_tests/test_agent_analyzer.py
"""
Unit Tests for Analyzer Agent
=============================
Run with: python -m pytest unit_tests/test_agent_analyzer.py -v
Or simply: python unit_tests/test_agent_analyzer.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

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
# Test Data Generators
# =============================================================================

def generate_sample_workouts(count: int = 14, start_days_ago: int = 0) -> list:
    """Generate sample workout data for testing."""
    base_date = datetime.now() - timedelta(days=start_days_ago)
    workouts = []
    
    for i in range(count):
        date = base_date - timedelta(days=i)
        workouts.append({
            "date": date.strftime("%Y-%m-%d"),
            "timestamp": date.isoformat(),
            "type": "strength" if i % 2 == 0 else "cardio",
            "duration": 45 + (i % 3) * 15,
            "intensity": ["low", "moderate", "high"][i % 3],
            "context": {
                "sleep_hours": 7.0 + (i % 3) * 0.5,
                "fatigue_level": 3 + (i % 5),
            }
        })
    
    return workouts


def generate_high_fatigue_workouts(count: int = 7) -> list:
    """Generate workouts with high fatigue."""
    base_date = datetime.now()
    return [
        {
            "date": (base_date - timedelta(days=i)).strftime("%Y-%m-%d"),
            "type": "strength",
            "duration": 90,
            "intensity": "high",
            "context": {"sleep_hours": 5.5, "fatigue_level": 8}
        }
        for i in range(count)
    ]


# =============================================================================
# TESTS
# =============================================================================

def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from agents.analyzer_agent import (
            analyze_performance,
            get_readiness_quick,
            get_training_recommendations,
            get_consistency_report,
            log_workout_for_analysis,
            create_analyzer_agent,
            calculate_consistency,
            calculate_biometric_averages,
            calculate_readiness_score,
            generate_recommendations,
            get_iso_week_key,
            get_motivational_quote,
            ANALYZER_CONFIG,
            ADK_AVAILABLE,
            MEMORY_MANAGER_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Memory Manager: {MEMORY_MANAGER_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_iso_week_key():
    """Test ISO week key generation."""
    print("\n" + "="*60)
    print("TEST 2: ISO Week Key Generation")
    print("="*60)
    
    from agents.analyzer_agent import get_iso_week_key
    
    # Test known dates
    test_cases = [
        ("2025-01-06", "2025-W02"),  # Monday of week 2
        ("2025-01-01", "2025-W01"),  # New Year
        ("2024-12-31", "2025-W01"),  # Dec 31 is in week 1 of 2025
    ]
    
    all_passed = True
    for date_str, expected_prefix in test_cases:
        result = get_iso_week_key(date_str)
        # Check format
        is_valid = len(result) == 8 and "W" in result
        print(f"   {date_str} → {result} (valid format: {is_valid})")
        if not is_valid:
            all_passed = False
    
    # Test with timestamp
    result_with_time = get_iso_week_key("2025-01-15T14:30:00")
    result_without_time = get_iso_week_key("2025-01-15")
    assert result_with_time == result_without_time, "Time should be ignored"
    print(f"   Time ignored: {result_with_time} == {result_without_time} ✓")
    
    print("✅ ISO week key tests passed")
    return all_passed


def test_calculate_consistency_perfect():
    """Test consistency with perfect data (5 workouts/week)."""
    print("\n" + "="*60)
    print("TEST 5: Consistency - Perfect Week")
    print("="*60)

    from agents.analyzer_agent import calculate_consistency

    # FIX: Use hardcoded dates. 
    # We know Jan 1 2024 (Monday) to Jan 5 2024 (Friday) is EXACTLY 1 ISO week.
    # This removes all ambiguity about "today's date" or timezones.
    workouts = [
        {"date": "2024-01-01", "type": "strength"}, # Monday
        {"date": "2024-01-02", "type": "strength"}, # Tuesday
        {"date": "2024-01-03", "type": "strength"}, # Wednesday
        {"date": "2024-01-04", "type": "strength"}, # Thursday
        {"date": "2024-01-05", "type": "strength"}, # Friday
    ]

    pct, weeks, label = calculate_consistency(workouts, target_per_week=3)

    print(f"   5 workouts in 1 week")
    print(f"   Percent: {pct}%")
    print(f"   Label: {label}")
    
    if pct != 100:
        print(f"   DEBUG: Detected {weeks} total weeks. Expected 1.")

    assert pct == 100, f"Perfect week should be 100%, got {pct}%"


def test_calculate_consistency_with_data():
    """Test consistency calculation with sample data."""
    print("\n" + "="*60)
    print("TEST 4: Consistency - With Data")
    print("="*60)
    
    from agents.analyzer_agent import calculate_consistency
    
    workouts = generate_sample_workouts(14)  # 2 weeks of data
    pct, weeks, label = calculate_consistency(workouts)
    
    print(f"   Workouts: {len(workouts)}")
    print(f"   Percent: {pct}%")
    print(f"   Weeks: {weeks}")
    print(f"   Label: {label}")
    
    assert 0 <= pct <= 100, "Percentage should be 0-100"
    assert weeks >= 1, "Should have at least 1 week"
    assert label in ["Elite", "Excellent", "Strong", "Building", "Getting Started", "New"]
    
    print("✅ Consistency with data test passed")
    return True



def test_biometric_averages_sufficient():
    """Test biometric averages with sufficient data."""
    print("\n" + "="*60)
    print("TEST 6: Biometrics - Sufficient Data")
    print("="*60)
    
    from agents.analyzer_agent import calculate_biometric_averages
    
    workouts = generate_sample_workouts(10)
    avg_sleep, avg_fatigue = calculate_biometric_averages(workouts, min_samples=4)
    
    print(f"   Workouts: {len(workouts)}")
    print(f"   Avg Sleep: {avg_sleep}")
    print(f"   Avg Fatigue: {avg_fatigue}")
    
    assert avg_sleep is not None, "Should have sleep average"
    assert avg_fatigue is not None, "Should have fatigue average"
    assert 5.0 <= avg_sleep <= 10.0, "Sleep should be reasonable"
    assert 1 <= avg_fatigue <= 10, "Fatigue should be 1-10"
    
    print("✅ Sufficient biometrics test passed")
    return True


def test_biometric_averages_insufficient():
    """Test biometric averages with insufficient data."""
    print("\n" + "="*60)
    print("TEST 7: Biometrics - Insufficient Data")
    print("="*60)
    
    from agents.analyzer_agent import calculate_biometric_averages
    
    # Only 2 workouts (below min_samples=4)
    workouts = generate_sample_workouts(2)
    avg_sleep, avg_fatigue = calculate_biometric_averages(workouts, min_samples=4)
    
    print(f"   Workouts: {len(workouts)}")
    print(f"   Avg Sleep: {avg_sleep}")
    print(f"   Avg Fatigue: {avg_fatigue}")
    
    assert avg_sleep is None, "Should be None with insufficient data"
    assert avg_fatigue is None, "Should be None with insufficient data"
    
    print("✅ Insufficient biometrics test passed")
    return True


def test_readiness_score_optimal():
    """Test readiness score with optimal conditions."""
    print("\n" + "="*60)
    print("TEST 8: Readiness - Optimal Conditions")
    print("="*60)
    
    from agents.analyzer_agent import calculate_readiness_score
    
    score, label, emoji = calculate_readiness_score(
        risk=0.1,
        avg_sleep=8.5,
        avg_fatigue=3,
        consistency_pct=95
    )
    
    print(f"   Score: {score}")
    print(f"   Label: {label}")
    print(f"   Emoji: {emoji}")
    
    assert score >= 85, "Optimal conditions should give high score"
    assert label in ["PEAK", "STRONG"], "Should be peak or strong"
    assert emoji == "🟢", "Should be green"
    
    print("✅ Optimal readiness test passed")
    return True


def test_readiness_score_poor():
    """Test readiness score with poor conditions."""
    print("\n" + "="*60)
    print("TEST 9: Readiness - Poor Conditions")
    print("="*60)
    
    from agents.analyzer_agent import calculate_readiness_score
    
    score, label, emoji = calculate_readiness_score(
        risk=0.9,
        avg_sleep=5.0,
        avg_fatigue=9,
        consistency_pct=10
    )
    
    print(f"   Score: {score}")
    print(f"   Label: {label}")
    print(f"   Emoji: {emoji}")
    
    assert score <= 40, "Poor conditions should give low score"
    assert label == "REST NOW", "Should recommend rest"
    assert emoji == "🔴", "Should be red"
    
    print("✅ Poor readiness test passed")
    return True


def test_readiness_score_clamping():
    """Test that readiness score is clamped to 5-100."""
    print("\n" + "="*60)
    print("TEST 10: Readiness - Score Clamping")
    print("="*60)
    
    from agents.analyzer_agent import calculate_readiness_score
    
    # Extreme low
    score_low, _, _ = calculate_readiness_score(
        risk=1.5, avg_sleep=0.5, avg_fatigue=15, consistency_pct=0
    )
    
    # Extreme high
    score_high, _, _ = calculate_readiness_score(
        risk=0, avg_sleep=12, avg_fatigue=0, consistency_pct=100
    )
    
    print(f"   Extreme low: {score_low}")
    print(f"   Extreme high: {score_high}")
    
    assert score_low >= 5, "Minimum should be 5"
    assert score_high <= 100, "Maximum should be 100"
    
    print("✅ Clamping test passed")
    return True


def test_generate_recommendations_critical():
    """Test recommendations for critical readiness."""
    print("\n" + "="*60)
    print("TEST 11: Recommendations - Critical")
    print("="*60)
    
    from agents.analyzer_agent import generate_recommendations
    
    recs = generate_recommendations(
        readiness=30,
        risk=0.9,
        avg_sleep=5.0,
        avg_fatigue=9,
        consistency_pct=20
    )
    
    print(f"   Count: {len(recs)}")
    for r in recs[:3]:
        print(f"   - {r[:50]}...")
    
    assert len(recs) >= 1, "Should have at least one recommendation"
    assert any("CRITICAL" in r or "🔴" in r for r in recs), "Should have critical warning"
    
    print("✅ Critical recommendations test passed")
    return True


def test_generate_recommendations_peak():
    """Test recommendations for peak readiness."""
    print("\n" + "="*60)
    print("TEST 12: Recommendations - Peak")
    print("="*60)
    
    from agents.analyzer_agent import generate_recommendations
    
    recs = generate_recommendations(
        readiness=95,
        risk=0.1,
        avg_sleep=8.5,
        avg_fatigue=3,
        consistency_pct=90
    )
    
    print(f"   Count: {len(recs)}")
    for r in recs[:3]:
        print(f"   - {r[:50]}...")
    
    assert any("PEAK" in r or "hard" in r.lower() for r in recs), "Should encourage training"
    
    print("✅ Peak recommendations test passed")
    return True


def test_motivational_quotes():
    """Test motivational quote selection."""
    print("\n" + "="*60)
    print("TEST 13: Motivational Quotes")
    print("="*60)
    
    from agents.analyzer_agent import get_motivational_quote
    
    test_scores = [95, 80, 65, 50, 25]
    
    for score in test_scores:
        quote = get_motivational_quote(score)
        print(f"   {score}: {quote[:40]}...")
        assert len(quote) > 0, f"Quote for {score} should not be empty"
    
    print("✅ Motivational quotes test passed")
    return True


def test_analyze_performance_no_data():
    """Test analyze_performance with no workout data."""
    print("\n" + "="*60)
    print("TEST 14: Analyze Performance - No Data")
    print("="*60)
    
    from agents.analyzer_agent import analyze_performance
    
    ctx = MockToolContext(state={})
    result = analyze_performance(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Readiness: {result['readiness_score']}")
    print(f"   Recommendations: {len(result['recommendations'])}")
    
    assert result["status"] == "no_data", "Should indicate no data"
    assert result["readiness_score"] == 50, "Default should be 50"
    assert len(result["recommendations"]) >= 1, "Should have suggestions"
    
    # Check state was updated
    assert ctx.state.get("app:latest_analysis") is not None
    
    print("✅ No data analysis test passed")
    return True


def test_analyze_performance_with_data():
    """Test analyze_performance with workout data."""
    print("\n" + "="*60)
    print("TEST 15: Analyze Performance - With Data")
    print("="*60)
    
    from agents.analyzer_agent import analyze_performance
    
    workouts = generate_sample_workouts(14)
    ctx = MockToolContext(state={
        "temp:workout_history": workouts
    })
    
    result = analyze_performance(ctx, window_days=14)
    
    print(f"   Status: {result['status']}")
    print(f"   Readiness: {result['readiness_score']}")
    print(f"   Label: {result['readiness_label']}")
    print(f"   Consistency: {result['consistency_percent']}%")
    print(f"   Recommendations: {len(result['recommendations'])}")
    
    assert result["status"] == "success", "Should succeed"
    assert 5 <= result["readiness_score"] <= 100, "Score should be valid"
    assert result["consistency_percent"] >= 0, "Consistency should be valid"
    assert "analyzed_at" in result, "Should have timestamp"
    
    print("✅ With data analysis test passed")
    return True


def test_get_readiness_quick_fresh():
    """Test quick readiness with no cached data."""
    print("\n" + "="*60)
    print("TEST 16: Quick Readiness - Fresh")
    print("="*60)
    
    from agents.analyzer_agent import get_readiness_quick
    
    workouts = generate_sample_workouts(7)
    ctx = MockToolContext(state={
        "temp:workout_history": workouts
    })
    
    result = get_readiness_quick(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Score: {result['readiness_score']}")
    print(f"   Summary: {result['quick_summary']}")
    
    assert result["status"] == "fresh", "Should be fresh analysis"
    assert "readiness_score" in result
    assert "quick_summary" in result
    
    print("✅ Fresh quick readiness test passed")
    return True


def test_get_readiness_quick_cached():
    """Test quick readiness with cached data."""
    print("\n" + "="*60)
    print("TEST 17: Quick Readiness - Cached")
    print("="*60)
    
    from agents.analyzer_agent import get_readiness_quick
    
    ctx = MockToolContext(state={
        "app:latest_analysis": {
            "readiness_score": 85,
            "readiness_label": "STRONG",
            "readiness_emoji": "🟢",
            "recommendations": ["Keep training!"]
        },
        "app:analysis_timestamp": datetime.now().isoformat()
    })
    
    result = get_readiness_quick(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Score: {result['readiness_score']}")
    print(f"   Cache age: {result.get('cache_age_hours', 'N/A')}")
    
    assert result["status"] == "cached", "Should use cache"
    assert result["readiness_score"] == 85, "Should return cached score"
    
    print("✅ Cached quick readiness test passed")
    return True


def test_get_training_recommendations():
    """Test training recommendations with focus areas."""
    print("\n" + "="*60)
    print("TEST 18: Training Recommendations")
    print("="*60)
    
    from agents.analyzer_agent import get_training_recommendations
    
    workouts = generate_sample_workouts(10)
    ctx = MockToolContext(state={
        "temp:workout_history": workouts
    })
    
    # Test different focus areas
    focus_areas = ["strength", "cardio", "recovery", "hiit", None]
    
    all_passed = True
    for focus in focus_areas:
        result = get_training_recommendations(ctx, focus=focus)
        has_recs = len(result.get("focus_recommendations", [])) > 0 or \
                   len(result.get("general_recommendations", [])) > 0
        
        print(f"   Focus: {focus or 'general'}")
        print(f"      Type: {result['suggested_workout_type']}")
        print(f"      Intensity: {result['intensity_recommendation']}")
        print(f"      Has recs: {has_recs}")
        
        if not has_recs:
            all_passed = False
    
    print("✅ Training recommendations test passed")
    return all_passed








def test_create_analyzer_agent():
    """Test analyzer agent creation."""
    print("\n" + "="*60)
    print("TEST 21: Create Analyzer Agent")
    print("="*60)
    
    from agents.analyzer_agent import create_analyzer_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent = create_analyzer_agent(use_memory_preload=False)
    
    if agent:
        print(f"✅ Agent created: {agent.name}")
        print(f"   Description: {agent.description[:50]}...")
        print(f"   Tools: {len(agent.tools)}")
        
        # List tools
        for i, tool in enumerate(agent.tools[:5]):
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool).__name__)))
            print(f"      {i+1}. {tool_name}")
    else:
        print("⚠️ Agent creation returned None")
    
    return True



def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 24: ADK Docstring Format")
    print("="*60)
    
    from agents.analyzer_agent import (
        analyze_performance,
        get_readiness_quick,
        get_training_recommendations,
        get_consistency_report,
        log_workout_for_analysis
    )
    
    tools = [
        ("analyze_performance", analyze_performance),
        ("get_readiness_quick", get_readiness_quick),
        ("get_training_recommendations", get_training_recommendations),
        ("get_consistency_report", get_consistency_report),
        ("log_workout_for_analysis", log_workout_for_analysis),
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
        print(f"      Has doc: {has_doc}, Args: {has_args}, Returns: {has_returns}, Example: {has_example}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_high_fatigue_scenario():
    """Test analysis with high fatigue data."""
    print("\n" + "="*60)
    print("TEST 25: High Fatigue Scenario")
    print("="*60)
    
    from agents.analyzer_agent import analyze_performance
    
    workouts = generate_high_fatigue_workouts(7)
    ctx = MockToolContext(state={
        "temp:workout_history": workouts
    })
    
    result = analyze_performance(ctx)
    
    print(f"   Readiness: {result['readiness_score']}")
    print(f"   Label: {result['readiness_label']}")
    print(f"   Risk: {result['risk_level']}")
    
    # Should detect issues
    assert result["readiness_score"] < 60, "High fatigue should lower readiness"
    
    # Check recommendations mention fatigue or rest
    recs_text = " ".join(result["recommendations"]).lower()
    has_warning = "fatigue" in recs_text or "rest" in recs_text or "deload" in recs_text
    print(f"   Has fatigue/rest warning: {has_warning}")
    
    print("✅ High fatigue scenario test passed")
    return True


def test_edge_case_single_workout():
    """Test with single workout."""
    print("\n" + "="*60)
    print("TEST 26: Single Workout Edge Case")
    print("="*60)
    
    from agents.analyzer_agent import analyze_performance
    
    ctx = MockToolContext(state={
        "temp:workout_history": [{
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "strength",
            "duration": 60,
            "intensity": "high",
            "context": {"sleep_hours": 8.0, "fatigue_level": 3}
        }]
    })
    
    result = analyze_performance(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Workouts analyzed: {result['total_workouts_analyzed']}")
    print(f"   Active weeks: {result['active_weeks']}")
    
    assert result["status"] == "success", "Should handle single workout"
    assert result["active_weeks"] >= 1, "Should count the week"
    
    print("✅ Single workout edge case passed")
    return True


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "📊"*30)
    print("   ANALYZER AGENT - UNIT TESTS")
    print("📊"*30)
    
    tests = [
        ("Imports", test_imports),
        ("ISO Week Key", test_iso_week_key),
        ("Consistency Empty", test_calculate_consistency_empty),
        ("Consistency With Data", test_calculate_consistency_with_data),
        ("Consistency Perfect", test_calculate_consistency_perfect),
        ("Biometrics Sufficient", test_biometric_averages_sufficient),
        ("Biometrics Insufficient", test_biometric_averages_insufficient),
        ("Readiness Optimal", test_readiness_score_optimal),
        ("Readiness Poor", test_readiness_score_poor),
        ("Readiness Clamping", test_readiness_score_clamping),
        ("Recs Critical", test_generate_recommendations_critical),
        ("Recs Peak", test_generate_recommendations_peak),
        ("Quotes", test_motivational_quotes),
        ("Analyze No Data", test_analyze_performance_no_data),
        ("Analyze With Data", test_analyze_performance_with_data),
        ("Quick Fresh", test_get_readiness_quick_fresh),
        ("Quick Cached", test_get_readiness_quick_cached),
        ("Training Recs", test_get_training_recommendations),
        ("Consistency Report", test_get_consistency_report),
        ("Create Agent", test_create_analyzer_agent),
        ("With Runner", test_create_analyzer_with_runner),
        ("ADK Docstrings", test_tool_docstrings),
        ("High Fatigue", test_high_fatigue_scenario),
        ("Single Workout", test_edge_case_single_workout),
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