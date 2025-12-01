# tools/plan_approval.py
"""
FitForge AI — Plan Approval Tool (ADK Long-Running Operations)
===============================================================
Implements Human-in-the-Loop approval workflow for training plans.

This showcases ADK's Long-Running Operations feature:
  - Pauses agent execution for human review
  - Waits for approval/rejection decision
  - Resumes with the user's choice

ADK Features Used (Exercise 4):
  - ToolContext with request_confirmation()
  - tool_confirmation for checking approval status
  - App wrapper with ResumabilityConfig
  - invocation_id for resuming paused executions

Use Cases:
  - High-intensity training plans (injury risk)
  - Significant calorie deficits (health concern)
  - Deload weeks (confirm user wants reduced training)
  - New exercise introductions (safety check)
  - Major goal changes
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

# =============================================================================
# ADK IMPORTS
# =============================================================================
try:
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.tools.tool_context import ToolContext
    from google.adk.tools.function_tool import FunctionTool
    from google.adk.apps.app import App, ResumabilityConfig
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    
    ADK_AVAILABLE = True
    print("✅ Plan Approval: ADK Long-Running Operations ready")
except ImportError as e:
    ADK_AVAILABLE = False
    print(f"⚠️ Plan Approval: ADK not available: {e}")
    
    # Create dummy ToolContext for non-ADK environments
    class ToolContext:
        def __init__(self):
            self.state = {}
            self.tool_confirmation = None
        def request_confirmation(self, hint: str, payload: dict):
            pass


# =============================================================================
# APPROVAL THRESHOLDS & RULES
# =============================================================================

class ApprovalReason(Enum):
    """Reasons why a plan might need approval."""
    HIGH_INTENSITY = "high_intensity"
    LARGE_VOLUME_INCREASE = "volume_increase"
    CALORIE_DEFICIT = "calorie_deficit"
    DELOAD_WEEK = "deload_week"
    NEW_EXERCISES = "new_exercises"
    INJURY_RISK = "injury_risk"
    GOAL_CHANGE = "goal_change"
    MAJOR_SCHEDULE_CHANGE = "schedule_change"
    AUTO_APPROVED = "auto_approved"


# Thresholds for auto-approval vs requiring human approval
APPROVAL_THRESHOLDS = {
    # Intensity thresholds (RPE scale 1-10)
    "max_intensity_auto": 7,          # Auto-approve up to RPE 7
    "max_intensity_allowed": 10,      # Maximum allowed
    
    # Volume change thresholds (percentage)
    "volume_increase_auto": 10,       # Auto-approve up to 10% increase
    "volume_increase_warn": 20,       # Warn at 20%+ increase
    
    # Calorie thresholds
    "min_calories_auto": 1500,        # Auto-approve if above 1500
    "min_calories_allowed": 1200,     # Hard minimum
    
    # Session count
    "max_sessions_auto": 5,           # Auto-approve up to 5 sessions/week
    "max_sessions_warn": 7,           # Warn at 7 sessions
    
    # New exercises
    "new_exercises_auto": 2,          # Auto-approve up to 2 new exercises
    "new_exercises_warn": 5,          # Warn at 5+ new exercises
}


# =============================================================================
# PLAN RISK ASSESSMENT
# =============================================================================

def assess_plan_risk(
    plan: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    previous_plan: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Assess the risk level of a training plan and determine if approval is needed.
    
    Analyzes the plan for potential issues that warrant human review.
    
    Args:
        plan: The proposed training plan with sessions, intensity, etc.
        user_profile: Optional user profile (injuries, experience level)
        previous_plan: Optional previous plan for comparison
    
    Returns:
        Dictionary with risk assessment:
        - requires_approval: Boolean
        - risk_level: "low", "medium", "high"
        - reasons: List of approval reasons
        - warnings: List of warning messages
        - auto_approve_reasons: Why it can be auto-approved (if applicable)
    """
    
    requires_approval = False
    risk_level = "low"
    reasons = []
    warnings = []
    auto_reasons = []
    
    # Extract plan metrics (with defaults)
    max_intensity = plan.get("max_intensity", 5)
    weekly_sessions = plan.get("sessions_per_week", 3)
    daily_calories = plan.get("daily_calories", 2000)
    new_exercises = plan.get("new_exercises", [])
    is_deload = plan.get("is_deload_week", False)
    volume_change_pct = plan.get("volume_change_percent", 0)
    
    # Check user profile for special considerations
    has_injuries = False
    is_beginner = False
    if user_profile:
        has_injuries = bool(user_profile.get("injuries"))
        experience = user_profile.get("experience_level") or "intermediate"
        is_beginner = experience.lower() in ["beginner", "novice"]
    
    # -------------------------------------------------------------------------
    # Rule 1: Intensity Check
    # -------------------------------------------------------------------------
    if max_intensity > APPROVAL_THRESHOLDS["max_intensity_auto"]:
        requires_approval = True
        risk_level = "medium"
        reasons.append(ApprovalReason.HIGH_INTENSITY)
        warnings.append(f"High intensity planned (RPE {max_intensity}/10). Ensure adequate recovery.")
    else:
        auto_reasons.append(f"Intensity within safe range (RPE {max_intensity})")
    
    # -------------------------------------------------------------------------
    # Rule 2: Volume Increase Check
    # -------------------------------------------------------------------------
    if volume_change_pct > APPROVAL_THRESHOLDS["volume_increase_warn"]:
        requires_approval = True
        risk_level = "high" if volume_change_pct > 30 else "medium"
        reasons.append(ApprovalReason.LARGE_VOLUME_INCREASE)
        warnings.append(f"Large volume increase ({volume_change_pct}%). Risk of overtraining.")
    elif volume_change_pct > APPROVAL_THRESHOLDS["volume_increase_auto"]:
        warnings.append(f"Moderate volume increase ({volume_change_pct}%). Monitor fatigue.")
    else:
        auto_reasons.append(f"Volume change acceptable ({volume_change_pct}%)")
    
    # -------------------------------------------------------------------------
    # Rule 3: Calorie Deficit Check
    # -------------------------------------------------------------------------
    if daily_calories < APPROVAL_THRESHOLDS["min_calories_auto"]:
        requires_approval = True
        risk_level = "high" if daily_calories < 1300 else "medium"
        reasons.append(ApprovalReason.CALORIE_DEFICIT)
        warnings.append(f"Low calorie target ({daily_calories} kcal). Consult a professional.")
    else:
        auto_reasons.append(f"Calorie target safe ({daily_calories} kcal)")
    
    # -------------------------------------------------------------------------
    # Rule 4: Deload Week Confirmation
    # -------------------------------------------------------------------------
    if is_deload:
        requires_approval = True
        risk_level = "low"  # Deload is actually safer
        reasons.append(ApprovalReason.DELOAD_WEEK)
        warnings.append("Deload week scheduled. Training volume will be reduced.")
    
    # -------------------------------------------------------------------------
    # Rule 5: New Exercises Check
    # -------------------------------------------------------------------------
    if len(new_exercises) > APPROVAL_THRESHOLDS["new_exercises_warn"]:
        requires_approval = True
        risk_level = "medium"
        reasons.append(ApprovalReason.NEW_EXERCISES)
        warnings.append(f"{len(new_exercises)} new exercises. Take time to learn proper form.")
    elif len(new_exercises) > APPROVAL_THRESHOLDS["new_exercises_auto"]:
        warnings.append(f"{len(new_exercises)} new exercises added.")
    else:
        auto_reasons.append("New exercises within learning capacity")
    
    # -------------------------------------------------------------------------
    # Rule 6: Session Count Check
    # -------------------------------------------------------------------------
    if weekly_sessions > APPROVAL_THRESHOLDS["max_sessions_warn"]:
        requires_approval = True
        risk_level = "high"
        reasons.append(ApprovalReason.INJURY_RISK)
        warnings.append(f"{weekly_sessions} sessions/week is very high. Ensure rest days.")
    elif weekly_sessions > APPROVAL_THRESHOLDS["max_sessions_auto"]:
        warnings.append(f"{weekly_sessions} sessions/week. Monitor recovery.")
    else:
        auto_reasons.append(f"Session count appropriate ({weekly_sessions}/week)")
    
    # -------------------------------------------------------------------------
    # Rule 7: Special User Considerations
    # -------------------------------------------------------------------------
    if has_injuries and max_intensity > 6:
        requires_approval = True
        risk_level = "high"
        reasons.append(ApprovalReason.INJURY_RISK)
        warnings.append("You have noted injuries. High intensity may aggravate them.")
    
    if is_beginner and (max_intensity > 6 or weekly_sessions > 4):
        requires_approval = True
        reasons.append(ApprovalReason.INJURY_RISK)
        warnings.append("As a beginner, this plan may be too aggressive.")
    
    # Set final risk level
    if not requires_approval:
        reasons.append(ApprovalReason.AUTO_APPROVED)
    
    return {
        "requires_approval": requires_approval,
        "risk_level": risk_level,
        "reasons": [r.value for r in reasons],
        "warnings": warnings,
        "auto_approve_reasons": auto_reasons if not requires_approval else [],
        "assessed_at": datetime.now().isoformat()
    }


# =============================================================================
# MAIN ADK TOOL: Submit Plan for Approval (Long-Running Operation)
# =============================================================================

def submit_plan_for_approval(
    tool_context: ToolContext,
    plan_name: str,
    plan_summary: str,
    max_intensity: int = 5,
    sessions_per_week: int = 3,
    daily_calories: Optional[int] = None,
    volume_change_percent: float = 0,
    is_deload_week: bool = False,
    new_exercises: Optional[List[str]] = None,
    goals: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a training plan for human approval using ADK Long-Running Operations.
    
    This tool demonstrates the Human-in-the-Loop pattern:
    1. First call: Checks if approval needed, pauses if yes
    2. User reviews and approves/rejects
    3. Second call: Resumes with user's decision
    
    Low-risk plans are auto-approved. High-risk plans pause for human review.
    
    Args:
        tool_context: ADK ToolContext (automatically provided)
        plan_name: Name/title of the training plan
        plan_summary: Brief description of the plan
        max_intensity: Maximum planned intensity (RPE 1-10)
        sessions_per_week: Number of training sessions per week
        daily_calories: Target daily calories (if nutrition plan included)
        volume_change_percent: Percentage change from previous plan
        is_deload_week: Whether this is a deload/recovery week
        new_exercises: List of new exercises being introduced
        goals: Training goals (strength, endurance, fat_loss, etc.)
    
    Returns:
        Dictionary with approval status:
        - status: "approved", "rejected", "pending", or "auto_approved"
        - plan_name: The plan name
        - message: Explanation of the decision
        - risk_assessment: Detailed risk analysis
        - next_steps: What happens next
        
    Example:
        >>> result = submit_plan_for_approval(
        ...     tool_context=ctx,
        ...     plan_name="Week 5 - Intensity Block",
        ...     plan_summary="High intensity strength week with RPE 8-9 sessions",
        ...     max_intensity=9,
        ...     sessions_per_week=5
        ... )
        >>> # Returns pending status, agent pauses
        >>> # After user approves, returns approved status
    """
    
    # Build plan dictionary
    plan = {
        "name": plan_name,
        "summary": plan_summary,
        "max_intensity": max_intensity,
        "sessions_per_week": sessions_per_week,
        "daily_calories": daily_calories or 2000,
        "volume_change_percent": volume_change_percent,
        "is_deload_week": is_deload_week,
        "new_exercises": new_exercises or [],
        "goals": goals,
    }
    
    # Get user profile from session state (if available)
    user_profile = None
    if hasattr(tool_context, 'state'):
        user_profile = {
            "injuries": tool_context.state.get("user:injuries"),
            "experience_level": tool_context.state.get("user:experience_level"),
        }
    
    # Assess plan risk
    risk_assessment = assess_plan_risk(plan, user_profile)
    
    # =========================================================================
    # SCENARIO 1: Auto-approve low-risk plans
    # =========================================================================
    if not risk_assessment["requires_approval"]:
        # Store approval in session state
        if hasattr(tool_context, 'state'):
            tool_context.state["app:current_plan"] = plan
            tool_context.state["app:plan_status"] = "auto_approved"
            tool_context.state["app:plan_approved_at"] = datetime.now().isoformat()
        
        return {
            "status": "auto_approved",
            "plan_name": plan_name,
            "message": f"✅ Plan '{plan_name}' has been auto-approved! It meets all safety criteria.",
            "risk_assessment": risk_assessment,
            "next_steps": [
                "Your plan is ready to execute",
                "Start with the first session when ready",
                "Log your workouts for tracking"
            ],
            "approved_at": datetime.now().isoformat()
        }
    
    # =========================================================================
    # SCENARIO 2: First call - Request human approval (PAUSE)
    # =========================================================================
    if not tool_context.tool_confirmation:
        # Build approval request message
        warnings_text = "\n".join([f"⚠️ {w}" for w in risk_assessment["warnings"]])
        
        approval_hint = f"""
🏋️ **Training Plan Approval Required**

**Plan:** {plan_name}
**Summary:** {plan_summary}

**Risk Level:** {risk_assessment["risk_level"].upper()}

**Warnings:**
{warnings_text}

**Plan Details:**
- Intensity: RPE {max_intensity}/10
- Sessions: {sessions_per_week}/week
- Volume Change: {volume_change_percent:+.0f}%
{"- 🔄 This is a DELOAD week" if is_deload_week else ""}
{"- Calories: " + str(daily_calories) + " kcal/day" if daily_calories else ""}

**Do you approve this plan?**
"""
        
        # Request confirmation - THIS PAUSES THE AGENT
        tool_context.request_confirmation(
            hint=approval_hint,
            payload={
                "plan": plan,
                "risk_assessment": risk_assessment,
                "requested_at": datetime.now().isoformat()
            }
        )
        
        # Store pending plan in state
        if hasattr(tool_context, 'state'):
            tool_context.state["app:pending_plan"] = plan
            tool_context.state["app:plan_status"] = "pending_approval"
        
        return {
            "status": "pending",
            "plan_name": plan_name,
            "message": f"⏸️ Plan '{plan_name}' requires your approval due to {risk_assessment['risk_level']} risk level.",
            "risk_assessment": risk_assessment,
            "awaiting": "Your approval or rejection",
            "next_steps": [
                "Review the warnings above",
                "Approve if you understand the risks",
                "Reject to modify the plan"
            ]
        }
    
    # =========================================================================
    # SCENARIO 3: Resumed after user decision
    # =========================================================================
    if tool_context.tool_confirmation.confirmed:
        # USER APPROVED
        if hasattr(tool_context, 'state'):
            tool_context.state["app:current_plan"] = plan
            tool_context.state["app:plan_status"] = "approved"
            tool_context.state["app:plan_approved_at"] = datetime.now().isoformat()
            # Clear pending
            tool_context.state.pop("app:pending_plan", None)
        
        return {
            "status": "approved",
            "plan_name": plan_name,
            "message": f"✅ Plan '{plan_name}' has been APPROVED! You accepted the {risk_assessment['risk_level']} risk level.",
            "risk_assessment": risk_assessment,
            "next_steps": [
                "Your plan is now active",
                "Pay attention to the warnings",
                "Adjust if you experience any issues",
                "Log your workouts for tracking"
            ],
            "approved_at": datetime.now().isoformat()
        }
    else:
        # USER REJECTED
        if hasattr(tool_context, 'state'):
            tool_context.state["app:plan_status"] = "rejected"
            tool_context.state.pop("app:pending_plan", None)
        
        return {
            "status": "rejected",
            "plan_name": plan_name,
            "message": f"❌ Plan '{plan_name}' has been REJECTED. Let's create a safer alternative.",
            "risk_assessment": risk_assessment,
            "next_steps": [
                "Consider reducing intensity",
                "Fewer sessions per week",
                "More gradual progression",
                "Ask me to generate a modified plan"
            ],
            "rejected_at": datetime.now().isoformat()
        }


# =============================================================================
# ADDITIONAL TOOL: Check Plan Status
# =============================================================================

def check_plan_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Check the current status of the training plan.
    
    Returns information about whether a plan is active, pending approval,
    or needs to be created.
    
    Args:
        tool_context: ADK ToolContext (automatically provided)
    
    Returns:
        Dictionary with plan status:
        - has_active_plan: Boolean
        - status: Current plan status
        - plan_details: Plan information if available
    """
    
    if not hasattr(tool_context, 'state'):
        return {
            "status": "error",
            "error_message": "Session state not available"
        }
    
    plan_status = tool_context.state.get("app:plan_status", "none")
    current_plan = tool_context.state.get("app:current_plan")
    pending_plan = tool_context.state.get("app:pending_plan")
    
    if plan_status == "none":
        return {
            "has_active_plan": False,
            "status": "no_plan",
            "message": "No training plan is currently set. Create one to get started.",
            "next_steps": ["Ask me to create a training plan for your goals"]
        }
    
    if plan_status == "pending_approval":
        return {
            "has_active_plan": False,
            "status": "pending_approval",
            "message": "A plan is waiting for your approval.",
            "plan_details": pending_plan,
            "next_steps": ["Review and approve or reject the pending plan"]
        }
    
    if plan_status in ["approved", "auto_approved"]:
        return {
            "has_active_plan": True,
            "status": plan_status,
            "message": f"Your plan '{current_plan.get('name', 'Current Plan')}' is active.",
            "plan_details": current_plan,
            "approved_at": tool_context.state.get("app:plan_approved_at"),
            "next_steps": ["Execute your training sessions", "Log workouts", "Ask for adjustments if needed"]
        }
    
    if plan_status == "rejected":
        return {
            "has_active_plan": False,
            "status": "rejected",
            "message": "The last plan was rejected. Let's create a modified version.",
            "next_steps": ["Ask me to create a safer alternative plan"]
        }
    
    return {
        "has_active_plan": False,
        "status": "unknown",
        "message": "Plan status unclear.",
        "raw_status": plan_status
    }


# =============================================================================
# ADDITIONAL TOOL: Quick Approval for Simple Changes
# =============================================================================

def quick_modify_plan(
    tool_context: ToolContext,
    modification_type: str,
    modification_value: Any
) -> Dict[str, Any]:
    """
    Make quick modifications to the current plan without full re-approval.
    
    Small, safe changes can be applied immediately. Larger changes
    will trigger the approval workflow.
    
    Args:
        tool_context: ADK ToolContext (automatically provided)
        modification_type: Type of modification:
                          - "skip_session": Skip a session
                          - "reduce_intensity": Lower intensity by 1-2 RPE
                          - "add_rest_day": Add an extra rest day
                          - "swap_exercise": Replace one exercise
        modification_value: The modification details
    
    Returns:
        Dictionary with modification result
    """
    
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "error_message": "No session state"}
    
    current_plan = tool_context.state.get("app:current_plan")
    
    if not current_plan:
        return {
            "status": "error",
            "error_message": "No active plan to modify. Create a plan first."
        }
    
    # Safe modifications that don't require approval
    safe_modifications = ["skip_session", "reduce_intensity", "add_rest_day"]
    
    if modification_type in safe_modifications:
        # Apply modification
        modifications = current_plan.get("modifications", [])
        modifications.append({
            "type": modification_type,
            "value": modification_value,
            "applied_at": datetime.now().isoformat()
        })
        current_plan["modifications"] = modifications
        
        # Update state
        tool_context.state["app:current_plan"] = current_plan
        
        return {
            "status": "applied",
            "modification_type": modification_type,
            "message": f"✅ Modification applied: {modification_type}",
            "details": modification_value,
            "plan_name": current_plan.get("name"),
            "requires_approval": False
        }
    else:
        # Larger changes need approval
        return {
            "status": "requires_approval",
            "modification_type": modification_type,
            "message": f"⚠️ This modification requires plan re-approval.",
            "next_steps": ["Submit a new plan with the desired changes"]
        }


# =============================================================================
# ADK APP WRAPPER (For Resumable Workflows)
# =============================================================================

def create_approval_app(agent: Any) -> Optional[Any]:
    """
    Wrap an agent in a resumable App for Long-Running Operations.
    
    This is REQUIRED for the pause/resume workflow to work properly.
    The App saves state when paused and restores it when resumed.
    
    Args:
        agent: The LlmAgent to wrap
    
    Returns:
        App configured for resumability, or None if ADK unavailable
    
    Usage:
        agent = LlmAgent(...)
        app = create_approval_app(agent)
        runner = Runner(app=app, session_service=session_service)
    """
    
    if not ADK_AVAILABLE:
        print("❌ ADK not available. Cannot create resumable app.")
        return None
    
    return App(
        name="fitforge_approval_app",
        root_agent=agent,
        resumability_config=ResumabilityConfig(is_resumable=True)
    )


# =============================================================================
# CREATE SAMPLE PLANNER AGENT WITH APPROVAL
# =============================================================================

def create_planner_agent_with_approval(retry_config: Optional[Any] = None):
    """
    Create a planner agent that uses the approval workflow.
    
    This agent can create training plans and will pause for human approval
    when the plan has elevated risk.
    
    Args:
        retry_config: Optional retry configuration for the model
    
    Returns:
        Tuple of (agent, app) ready for use with Runner
    """
    
    if not ADK_AVAILABLE:
        print("❌ ADK not available.")
        return None, None
    
    if retry_config is None:
        retry_config = types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )
    
    planner_agent = LlmAgent(
        name="FitnessPlannerWithApproval",
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
        instruction="""You are a fitness planning assistant that creates personalized training plans.

When creating a plan, you MUST use the submit_plan_for_approval tool.

The tool will:
- AUTO-APPROVE safe, low-risk plans immediately
- PAUSE and ask for human approval on higher-risk plans

Risk factors that trigger approval:
- High intensity (RPE 8+)
- Large volume increases (>20%)
- Low calorie targets (<1500)
- Many new exercises
- User has noted injuries

When a plan is pending approval:
1. Explain why approval is needed
2. Wait for the user's decision
3. If approved: Proceed with the plan
4. If rejected: Offer to create a modified, safer plan

Always prioritize user safety and proper progression.
""",
        tools=[
            FunctionTool(func=submit_plan_for_approval),
            FunctionTool(func=check_plan_status),
            FunctionTool(func=quick_modify_plan),
        ],
    )
    
    # Wrap in resumable app
    app = create_approval_app(planner_agent)
    
    return planner_agent, app


# =============================================================================
# HELPER: Process Approval Events
# =============================================================================

def check_for_approval_request(events: list) -> Optional[Dict[str, Any]]:
    """
    Check if events contain an approval request.
    
    Use this in your workflow to detect when the agent has paused.
    
    Args:
        events: List of events from runner.run_async()
    
    Returns:
        Dict with approval_id and invocation_id if found, None otherwise
    """
    
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (part.function_call and 
                    part.function_call.name == "adk_request_confirmation"):
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id,
                        "found": True
                    }
    return None


def create_approval_response(approval_info: Dict, approved: bool) -> Any:
    """
    Create the approval response message to resume the agent.
    
    Args:
        approval_info: Dict from check_for_approval_request()
        approved: True to approve, False to reject
    
    Returns:
        Content object to pass to runner.run_async()
    """
    
    if not ADK_AVAILABLE:
        return None
    
    from google.genai import types
    
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved}
    )
    
    return types.Content(
        role="user",
        parts=[types.Part(function_response=confirmation_response)]
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main approval tool
    "submit_plan_for_approval",
    
    # Supporting tools
    "check_plan_status",
    "quick_modify_plan",
    "assess_plan_risk",
    
    # ADK integration
    "create_approval_app",
    "create_planner_agent_with_approval",
    
    # Workflow helpers
    "check_for_approval_request",
    "create_approval_response",
    
    # Constants
    "ApprovalReason",
    "APPROVAL_THRESHOLDS",
    "ADK_AVAILABLE",
]