# unit_tests/test_tool_plan_approval.py
"""
Unit Tests for Plan Approval Tool (Long-Running Operations)
===========================================================
Run with: python -m pytest unit_tests/test_tool_plan_approval.py -v
Or simply: python unit_tests/test_tool_plan_approval.py

Note: Some tests simulate the ADK approval workflow.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Mock ToolContext for Testing
# =============================================================================

class MockToolContext:
    """Mock ToolContext for testing without full ADK."""
    
    def __init__(self, state: dict = None, confirmed: bool = None):
        self.state = state or {}
        self._confirmation_requested = False
        self._confirmation_hint = None
        self._confirmation_payload = None
        
        # Simulate tool_confirmation
        if confirmed is not None:
            self.tool_confirmation = MockConfirmation(confirmed)
        else:
            self.tool_confirmation = None
    
    def request_confirmation(self, hint: str, payload: dict):
        self._confirmation_requested = True
        self._confirmation_hint = hint
        self._confirmation_payload = payload


class MockConfirmation:
    """Mock confirmation response."""
    
    def __init__(self, confirmed: bool):
        self.confirmed = confirmed


# =============================================================================
# TESTS
# =============================================================================

def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from tools.plan_approval import (
            submit_plan_for_approval,
            check_plan_status,
            quick_modify_plan,
            assess_plan_risk,
            create_approval_app,
            create_planner_agent_with_approval,
            check_for_approval_request,
            ApprovalReason,
            APPROVAL_THRESHOLDS,
            ADK_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Approval thresholds: {len(APPROVAL_THRESHOLDS)} rules")
        print(f"   Approval reasons: {len(ApprovalReason)} types")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_assess_plan_risk_low():
    """Test risk assessment for low-risk plans."""
    print("\n" + "="*60)
    print("TEST 2: Low-Risk Plan Assessment")
    print("="*60)
    
    from tools.plan_approval import assess_plan_risk, ApprovalReason
    
    # Low-risk plan
    plan = {
        "name": "Easy Week",
        "max_intensity": 5,
        "sessions_per_week": 3,
        "daily_calories": 2200,
        "volume_change_percent": 5,
        "is_deload_week": False,
        "new_exercises": [],
    }
    
    result = assess_plan_risk(plan)
    
    print(f"Plan: Easy week, RPE 5, 3 sessions")
    print(f"Requires approval: {result['requires_approval']}")
    print(f"Risk level: {result['risk_level']}")
    print(f"Reasons: {result['reasons']}")
    
    assert not result["requires_approval"], "Low-risk plan should auto-approve"
    assert result["risk_level"] == "low", "Should be low risk"
    assert ApprovalReason.AUTO_APPROVED.value in result["reasons"]
    print("✅ Low-risk plan correctly auto-approved")
    
    return True


def test_assess_plan_risk_high_intensity():
    """Test risk assessment for high-intensity plans."""
    print("\n" + "="*60)
    print("TEST 3: High-Intensity Plan Assessment")
    print("="*60)
    
    from tools.plan_approval import assess_plan_risk, ApprovalReason
    
    # High-intensity plan
    plan = {
        "name": "Intensity Block",
        "max_intensity": 9,
        "sessions_per_week": 4,
        "daily_calories": 2500,
        "volume_change_percent": 0,
        "is_deload_week": False,
        "new_exercises": [],
    }
    
    result = assess_plan_risk(plan)
    
    print(f"Plan: Intensity block, RPE 9")
    print(f"Requires approval: {result['requires_approval']}")
    print(f"Risk level: {result['risk_level']}")
    print(f"Warnings: {result['warnings']}")
    
    assert result["requires_approval"], "High-intensity should require approval"
    assert ApprovalReason.HIGH_INTENSITY.value in result["reasons"]
    assert len(result["warnings"]) > 0, "Should have warnings"
    print("✅ High-intensity plan correctly flagged")
    
    return True


def test_assess_plan_risk_deload():
    """Test risk assessment for deload weeks."""
    print("\n" + "="*60)
    print("TEST 4: Deload Week Assessment")
    print("="*60)
    
    from tools.plan_approval import assess_plan_risk, ApprovalReason
    
    # Deload week
    plan = {
        "name": "Deload Week",
        "max_intensity": 4,
        "sessions_per_week": 2,
        "is_deload_week": True,
        "volume_change_percent": -40,
    }
    
    result = assess_plan_risk(plan)
    
    print(f"Plan: Deload week")
    print(f"Requires approval: {result['requires_approval']}")
    print(f"Risk level: {result['risk_level']}")
    
    assert result["requires_approval"], "Deload should confirm with user"
    assert ApprovalReason.DELOAD_WEEK.value in result["reasons"]
    assert result["risk_level"] == "low", "Deload is actually low risk"
    print("✅ Deload week correctly flagged for confirmation")
    
    return True


def test_assess_plan_risk_calorie_deficit():
    """Test risk assessment for low calorie plans."""
    print("\n" + "="*60)
    print("TEST 5: Low Calorie Plan Assessment")
    print("="*60)
    
    from tools.plan_approval import assess_plan_risk, ApprovalReason
    
    # Low calorie plan
    plan = {
        "name": "Aggressive Cut",
        "max_intensity": 5,
        "daily_calories": 1300,
    }
    
    result = assess_plan_risk(plan)
    
    print(f"Plan: 1300 kcal/day")
    print(f"Requires approval: {result['requires_approval']}")
    print(f"Risk level: {result['risk_level']}")
    
    assert result["requires_approval"], "Low calories should require approval"
    assert ApprovalReason.CALORIE_DEFICIT.value in result["reasons"]
    print("✅ Low calorie plan correctly flagged")
    
    return True


def test_submit_plan_auto_approve():
    """Test auto-approval flow for safe plans."""
    print("\n" + "="*60)
    print("TEST 6: Auto-Approval Flow")
    print("="*60)
    
    from tools.plan_approval import submit_plan_for_approval
    
    # Create mock context
    ctx = MockToolContext()
    
    # Submit a safe plan
    result = submit_plan_for_approval(
        tool_context=ctx,
        plan_name="Easy Recovery Week",
        plan_summary="Light training for recovery",
        max_intensity=4,
        sessions_per_week=2,
        daily_calories=2200,
        volume_change_percent=0
    )
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message'][:60]}...")
    
    assert result["status"] == "auto_approved", "Safe plan should auto-approve"
    assert "approved" in result["message"].lower()
    print("✅ Auto-approval flow works correctly")
    
    return True


def test_submit_plan_pending():
    """Test pending approval flow (first call - pause)."""
    print("\n" + "="*60)
    print("TEST 7: Pending Approval Flow (Pause)")
    print("="*60)
    
    from tools.plan_approval import submit_plan_for_approval
    
    # Create mock context (no confirmation yet)
    ctx = MockToolContext()
    
    # Submit a risky plan
    result = submit_plan_for_approval(
        tool_context=ctx,
        plan_name="Beast Mode Week",
        plan_summary="Maximum intensity training",
        max_intensity=10,
        sessions_per_week=6,
        volume_change_percent=25
    )
    
    print(f"Status: {result['status']}")
    print(f"Risk level: {result['risk_assessment']['risk_level']}")
    print(f"Confirmation requested: {ctx._confirmation_requested}")
    
    assert result["status"] == "pending", "Risky plan should be pending"
    assert ctx._confirmation_requested, "Should request confirmation"
    assert ctx._confirmation_hint is not None, "Should have hint message"
    print("✅ Pending approval flow works correctly")
    print(f"   Hint preview: {ctx._confirmation_hint[:100]}...")
    
    return True


def test_submit_plan_approved():
    """Test approval flow (second call - user approved)."""
    print("\n" + "="*60)
    print("TEST 8: Approved Flow (Resume - Accepted)")
    print("="*60)
    
    from tools.plan_approval import submit_plan_for_approval
    
    # Create mock context with approval
    ctx = MockToolContext(confirmed=True)
    
    # Submit same risky plan (now with confirmation)
    result = submit_plan_for_approval(
        tool_context=ctx,
        plan_name="Beast Mode Week",
        plan_summary="Maximum intensity training",
        max_intensity=10,
        sessions_per_week=6
    )
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message'][:60]}...")
    
    assert result["status"] == "approved", "Should be approved"
    assert "approved" in result["message"].lower()
    print("✅ Approval flow works correctly")
    
    return True


def test_submit_plan_rejected():
    """Test rejection flow (second call - user rejected)."""
    print("\n" + "="*60)
    print("TEST 9: Rejected Flow (Resume - Declined)")
    print("="*60)
    
    from tools.plan_approval import submit_plan_for_approval
    
    # Create mock context with rejection
    ctx = MockToolContext(confirmed=False)
    
    # Submit same risky plan (now with rejection)
    result = submit_plan_for_approval(
        tool_context=ctx,
        plan_name="Beast Mode Week",
        plan_summary="Maximum intensity training",
        max_intensity=10,
        sessions_per_week=6
    )
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message'][:60]}...")
    print(f"Next steps: {result['next_steps']}")
    
    assert result["status"] == "rejected", "Should be rejected"
    assert "rejected" in result["message"].lower()
    assert len(result["next_steps"]) > 0, "Should have next steps"
    print("✅ Rejection flow works correctly")
    
    return True


def test_check_plan_status():
    """Test plan status checking."""
    print("\n" + "="*60)
    print("TEST 10: Check Plan Status")
    print("="*60)
    
    from tools.plan_approval import check_plan_status
    
    # No plan
    ctx1 = MockToolContext(state={})
    result1 = check_plan_status(ctx1)
    print(f"\nNo plan: {result1['status']}")
    assert result1["status"] == "no_plan"
    
    # Pending plan
    ctx2 = MockToolContext(state={
        "app:plan_status": "pending_approval",
        "app:pending_plan": {"name": "Test Plan"}
    })
    result2 = check_plan_status(ctx2)
    print(f"Pending: {result2['status']}")
    assert result2["status"] == "pending_approval"
    
    # Active plan
    ctx3 = MockToolContext(state={
        "app:plan_status": "approved",
        "app:current_plan": {"name": "Active Plan"}
    })
    result3 = check_plan_status(ctx3)
    print(f"Active: {result3['status']}")
    assert result3["has_active_plan"] == True
    
    print("✅ Status checking works correctly")
    return True


def test_quick_modify_plan():
    """Test quick plan modifications."""
    print("\n" + "="*60)
    print("TEST 11: Quick Modifications")
    print("="*60)
    
    from tools.plan_approval import quick_modify_plan
    
    # Setup with active plan
    ctx = MockToolContext(state={
        "app:current_plan": {
            "name": "Test Plan",
            "max_intensity": 7
        },
        "app:plan_status": "approved"
    })
    
    # Safe modification
    result1 = quick_modify_plan(ctx, "skip_session", "Thursday")
    print(f"Skip session: {result1['status']}")
    assert result1["status"] == "applied", "Safe mod should apply"
    assert result1["requires_approval"] == False
    
    # Unsafe modification
    result2 = quick_modify_plan(ctx, "change_goal", "powerlifting")
    print(f"Change goal: {result2['status']}")
    assert result2["status"] == "requires_approval", "Unsafe mod needs approval"
    
    print("✅ Quick modifications work correctly")
    return True


def test_create_planner_agent():
    """Test creating the planner agent with approval workflow."""
    print("\n" + "="*60)
    print("TEST 12: Create Planner Agent")
    print("="*60)
    
    from tools.plan_approval import create_planner_agent_with_approval, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent, app = create_planner_agent_with_approval()
    
    if agent:
        print(f"✅ Agent created: {agent.name}")
        print(f"   Tools: {len(agent.tools)}")
        print(f"   App: {app.name if app else 'None'}")
        
        # Check for resumability
        if app:
            print(f"   Resumable: {app.resumability_config is not None}")
    else:
        print("⚠️ Agent creation returned None (check ADK config)")
    
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 13: ADK Docstring Format")
    print("="*60)
    
    from tools.plan_approval import (
        submit_plan_for_approval,
        check_plan_status,
        quick_modify_plan,
        assess_plan_risk
    )
    
    tools = [
        ("submit_plan_for_approval", submit_plan_for_approval),
        ("check_plan_status", check_plan_status),
        ("quick_modify_plan", quick_modify_plan),
        ("assess_plan_risk", assess_plan_risk),
    ]
    
    all_passed = True
    for name, func in tools:
        doc = func.__doc__
        has_doc = doc is not None
        has_args = doc and "Args:" in doc
        has_returns = doc and "Returns:" in doc
        
        passed = has_doc and has_args and has_returns
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "⏸️"*30)
    print("   PLAN APPROVAL TOOL - UNIT TESTS")
    print("   (Long-Running Operations / Human-in-the-Loop)")
    print("⏸️"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Low-Risk Assessment", test_assess_plan_risk_low),
        ("High-Intensity Assessment", test_assess_plan_risk_high_intensity),
        ("Deload Assessment", test_assess_plan_risk_deload),
        ("Calorie Deficit Assessment", test_assess_plan_risk_calorie_deficit),
        ("Auto-Approval Flow", test_submit_plan_auto_approve),
        ("Pending Flow (Pause)", test_submit_plan_pending),
        ("Approved Flow (Resume)", test_submit_plan_approved),
        ("Rejected Flow", test_submit_plan_rejected),
        ("Check Status", test_check_plan_status),
        ("Quick Modifications", test_quick_modify_plan),
        ("Create Agent", test_create_planner_agent),
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