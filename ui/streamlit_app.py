# ui/streamlit_app.py
"""
FitForge AI — Streamlit Dashboard (ADK Edition)
================================================
Interactive UI for the FitForge AI fitness assistant.
"""

import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import os

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# ========================================
# PATH SETUP
# ========================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ========================================
# CONFIGURATION
# ========================================
API_BASE = os.environ.get("FITFORGE_API_URL", "http://localhost:8000/api/v1")
REQUEST_TIMEOUT_SHORT = 5
REQUEST_TIMEOUT_LONG = 60

GOALS = ["general_fitness", "strength", "endurance", "fat_loss", "race_prep"]

MEAL_TYPES = [
    "breakfast", "lunch", "dinner", 
    "snack", "pre_workout", "post_workout"
]


@dataclass
class AppConfig:
    """Application configuration."""
    page_title: str = "FitForge AI — Your Personal Coach"
    page_icon: str = "🧠"
    layout: str = "wide"


# ========================================
# PAGE SETUP
# ========================================
st.set_page_config(
    page_title=AppConfig.page_title,
    page_icon=AppConfig.page_icon,
    layout=AppConfig.layout,
    initial_sidebar_state="expanded"
)


# ========================================
# STYLING
# ========================================
def load_styles():
    """Load custom CSS styles."""
    st.markdown("""
    <style>
        .stButton>button {
            border-radius: 8px; 
            height: 3em; 
            width: 100%;
            font-weight: 600;
        }
        .metric-card {
            background: linear-gradient(135deg, #1E1E2E 0%, #2D2D3D 100%);
            padding: 1.5rem; 
            border-radius: 12px; 
            text-align: center;
            border-left: 4px solid #FF4B4B;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            margin: 0.5rem 0;
        }
        .big-number {
            font-size: 2.5rem; 
            font-weight: bold; 
            margin: 0; 
            color: #FFF;
        }
        .label {
            font-size: 0.9rem; 
            color: #AAA;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .quote {
            font-style: italic; 
            color: #BBB; 
            text-align: center; 
            font-size: 1.1rem; 
            margin-top: 20px;
            padding: 1rem;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }
        .success-banner {
            background: linear-gradient(90deg, #00C851 0%, #007E33 100%);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            margin: 1rem 0;
        }
        .agent-status {
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-bottom: 4px;
        }
        .agent-online { 
            background: rgba(0,200,81,0.2); 
            color: #00C851; 
            border: 1px solid #00C851; 
        }
        .agent-offline { 
            background: rgba(255,75,75,0.2); 
            color: #FF4B4B; 
            border: 1px solid #FF4B4B; 
        }
        
        /* NEW: Persistent feedback card styling */
        .feedback-card {
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
    """, unsafe_allow_html=True)


# ========================================
# SESSION STATE
# ========================================
def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "user_id": "default",
        "chat_history": [],
        "current_plan": None,
        # NEW: Store last workout result for persistent display
        "last_workout_result": None,
        "show_workout_feedback": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ========================================
# API CLIENT
# ========================================
class APIClient:
    """Handles all API communication."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.root_url = base_url.replace("/api/v1", "").rstrip("/")
    
    def check_health(self) -> tuple[bool, dict]:
        """Check if the API is online."""
        try:
            response = requests.get(self.root_url, timeout=REQUEST_TIMEOUT_SHORT)
            if response.status_code == 200:
                return True, response.json()
        except requests.RequestException:
            pass
        return False, {}
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make GET request to API."""
        try:
            url = f"{self.base_url}/{endpoint}"
            params = params or {}
            params["user_id"] = st.session_state.user_id
            
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_LONG)
            
            if response.status_code == 200:
                return response.json()
            return {"error": f"API Error: {response.status_code}"}
            
        except requests.exceptions.ConnectionError:
            return {"error": "API Offline"}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def post(
        self, 
        endpoint: str, 
        data: Optional[dict] = None, 
        files: Optional[dict] = None, 
        as_form: bool = False
    ) -> dict:
        """Make POST request to API."""
        try:
            url = f"{self.base_url}/{endpoint}"
            data = data or {}
            
            if "user_id" not in data:
                data["user_id"] = st.session_state.user_id
            
            # FIX: Only use form data when files are present
            # For text-only submissions, use JSON
            if files:
                # Multipart form data for file uploads
                response = requests.post(
                    url, data=data, files=files, timeout=REQUEST_TIMEOUT_LONG
                )
            elif as_form:
                # Form URL encoded (rarely needed)
                response = requests.post(
                    url, data=data, timeout=REQUEST_TIMEOUT_LONG
                )
            else:
                # JSON body (default for text submissions)
                response = requests.post(
                    url, json=data, timeout=REQUEST_TIMEOUT_LONG
                )
            
            if response.status_code == 200:
                return response.json()
            return {"error": f"API Error: {response.status_code} - {response.text}"}
            
        except requests.exceptions.ConnectionError:
            return {"error": "API Offline"}
        except requests.RequestException as e:
            return {"error": str(e)}


# Initialize API client
api = APIClient(API_BASE)


# ========================================
# UI COMPONENTS
# ========================================
class UIComponents:
    """Reusable UI components."""
    
    @staticmethod
    def metric_card(label: str, value: str, color: str = "#FF4B4B") -> str:
        """Generate HTML for a metric card."""
        return f"""
        <div class="metric-card" style="border-left-color: {color};">
            <div class="big-number">{value}</div>
            <div class="label">{label}</div>
        </div>
        """
    
    @staticmethod
    def feedback_card(message: str, persistent: bool = False) -> None:
        """Display coach feedback with dynamic coloring."""
        # Determine color based on message sentiment
        color = "#4B9CD3"  # Default blue
        
        positive_keywords = ["Sniper", "Perfect", "Smart", "Great", "Excellent", "Good"]
        intense_keywords = ["Pushing", "Beast", "High", "Hard", "Intense"]
        caution_keywords = ["Adjusted", "Rogue", "Careful", "Rest", "Recovery"]
        
        if any(kw.lower() in message.lower() for kw in positive_keywords):
            color = "#00C851"  # Green
        elif any(kw.lower() in message.lower() for kw in intense_keywords):
            color = "#FF4B4B"  # Red
        elif any(kw.lower() in message.lower() for kw in caution_keywords):
            color = "#FFA500"  # Orange
        
        # Add persistent class for animation
        card_class = "feedback-card" if persistent else ""
        
        st.markdown(f"""
        <div class="{card_class}" style="
            background-color: {color}15;
            border-left: 6px solid {color};
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <h3 style="margin:0; color: {color}; font-size: 1.1rem;">
                💬 Coach's Feedback
            </h3>
            <p style="font-size: 1.3rem; margin-top: 8px; font-weight: 500; font-style: italic;">
                "{message}"
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def agent_status_badge(name: str, is_online: bool) -> None:
        """Display agent status badge."""
        status_class = "agent-online" if is_online else "agent-offline"
        status_icon = "✅" if is_online else "❌"
        st.markdown(
            f'<div class="agent-status {status_class}">'
            f'{status_icon} {name.title()}</div>',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def quote_box(text: str) -> None:
        """Display a styled quote box."""
        st.markdown(
            f"""<div class='quote'>"{text}"</div>""",
            unsafe_allow_html=True
        )


# ========================================
# PAGE SECTIONS
# ========================================
class HeaderSection:
    """Header and connection status."""
    
    @staticmethod
    def render(is_online: bool) -> None:
        col_title, col_status = st.columns([3, 1])
        
        with col_title:
            st.title("🧠 FitForge AI")
            st.caption("Google ADK Capstone Project • Multi-Agent Fitness Assistant")
        
        with col_status:
            if is_online:
                st.success("🟢 System Online")
            else:
                st.error("🔴 API Offline")
                st.caption(f"Trying: {API_BASE}")


class SidebarSection:
    """Sidebar with profile and stats."""
    
    @staticmethod
    def render(is_online: bool, system_status: dict) -> tuple[str, float, str]:
        """Render sidebar and return profile data."""
        with st.sidebar:
            # Profile Section
            name, weight, goal = SidebarSection._render_profile(is_online)
            
            st.divider()
            
            # Agent Status
            SidebarSection._render_agent_status(is_online, system_status)
            
            st.divider()
            
            # Daily Briefing
            SidebarSection._render_daily_briefing(is_online)
            
            st.divider()
            
            # Quick Stats
            SidebarSection._render_quick_stats(is_online)
        
        return name, weight, goal
    
    @staticmethod
    def _render_profile(is_online: bool) -> tuple[str, float, str]:
        """Render profile section."""
        st.header("👤 Profile")
        
        # Default values
        name, weight, goal = "Athlete", 75.0, "general_fitness"
        
        if is_online:
            profile = api.get("profile")
            if "error" not in profile:
                name = profile.get("name", name)
                weight = profile.get("weight_kg", weight)
                goal = profile.get("goal", goal)
        else:
            name = "Offline"
            goal = "offline"
        
        with st.expander("Edit Profile", expanded=False):
            new_name = st.text_input("Name", value=name)
            new_weight = st.number_input(
                "Weight (kg)", 
                value=float(weight), 
                min_value=30.0, 
                max_value=200.0
            )
            
            goal_index = GOALS.index(goal) if goal in GOALS else 0
            new_goal = st.selectbox("Goal", GOALS, index=goal_index)
            
            if st.button("💾 Save Profile"):
                if is_online:
                    result = api.post("profile/update", {
                        "name": new_name,
                        "weight_kg": new_weight,
                        "goal": new_goal
                    })
                    if "error" not in result:
                        st.success("✅ Profile saved!")
                        st.rerun()
                    else:
                        st.error(result["error"])
                else:
                    st.error("Cannot save: API Offline")
        
        return name, weight, goal
    
    @staticmethod
    def _render_agent_status(is_online: bool, system_status: dict) -> None:
        """Render agent status section."""
        st.markdown("### 🤖 Agent Status")
        
        if is_online:
            agents = system_status.get("agents", {})
            for agent_name, status in agents.items():
                UIComponents.agent_status_badge(agent_name, status)
        else:
            st.warning("Could not connect to Agent Orchestrator")
            st.code("Ensure python api/app.py is running")
    
    @staticmethod
    def _render_daily_briefing(is_online: bool) -> None:
        """Render daily briefing section."""
        st.markdown("### 🌅 Daily Briefing")
        
        if is_online:
            if st.button("Generate Summary"):
                with st.spinner("Coach is reviewing your day..."):
                    res = api.get("daily/summary")
                    if res.get("status") == "success":
                        st.info(res["summary"])
                    else:
                        st.error("Could not generate summary.")
        else:
            st.caption("Go online to see summary")
    
    @staticmethod
    def _render_quick_stats(is_online: bool) -> None:
        """Render quick stats section."""
        st.markdown("### 📊 Quick Stats")
        
        if is_online:
            stats = api.get("profile/stats")
            if "error" not in stats:
                st.metric("Total Workouts", stats.get("total_workouts", 0))
                st.metric("Total Distance", f"{stats.get('total_distance_km', 0)} km")
                st.metric("Current Streak", f"{stats.get('current_streak_days', 0)} days")
            else:
                st.info("Log workouts to see stats")
        else:
            st.caption("Stats unavailable offline")


# ========================================
# TAB IMPLEMENTATIONS
# ========================================
class LogTab:
    """Workout logging tab."""
    
    @staticmethod
    def render(is_online: bool) -> None:
        st.markdown("### 📝 Log Your Training")
        st.caption(
            "Drag & drop a screenshot OR describe your workout. "
            "Our Agents handle the rest."
        )
        
        # FIRST: Show persistent feedback if exists
        LogTab._show_persistent_feedback()
        
        with st.form("workout_form", clear_on_submit=True):
            col_input, col_context = st.columns([3, 2])
            
            with col_input:
                screenshot = st.file_uploader(
                    "📷 Upload Activity (Apple Watch, Strava, Garmin)", 
                    type=["png", "jpg", "jpeg"]
                )
                comment = st.text_area(
                    "✍️ OR Type Description",
                    placeholder="e.g. 'Ran 5k in 25 mins, felt strong but knee hurts a bit.'",
                    height=100
                )
            
            with col_context:
                st.write("**Bio-Context**")
                sleep = st.slider(
                    "😴 Last Night's Sleep", 
                    0.0, 12.0, 7.5, 0.5, 
                    format="%0.1f hrs"
                )
                fatigue = st.slider(
                    "🔋 Current Fatigue", 
                    1, 10, 5, 
                    help="1=Fresh, 10=Exhausted"
                )
                csv_text = st.text_input(
                    "⚡ Quick Data (Optional)", 
                    placeholder="dist, time, hr"
                )
            
            submitted = st.form_submit_button(
                "🚀 LOG WORKOUT", 
                type="primary", 
                use_container_width=True
            )
        
        LogTab._handle_submission(
            submitted, comment, screenshot, csv_text, 
            sleep, fatigue, is_online
        )
        
        # Clear feedback button
        if st.session_state.show_workout_feedback:
            if st.button("✖️ Dismiss Feedback", type="secondary"):
                st.session_state.show_workout_feedback = False
                st.session_state.last_workout_result = None
                st.rerun()
    
    @staticmethod
    def _show_persistent_feedback() -> None:
        """Show persistent workout feedback until dismissed."""
        if not st.session_state.show_workout_feedback:
            return
        
        result = st.session_state.last_workout_result
        if not result:
            return
        
        #st.balloons()
        
        # Coach feedback - PERSISTENT
        message = result.get('overall_message', 'Workout Logged Successfully.')
        UIComponents.feedback_card(message, persistent=True)
        
        # Metrics
        analysis = result.get("analysis", {})
        readiness = analysis.get('readiness_score', 100)
        fatigue = result.get('_fatigue', 5)  # We store this when submitting
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("New Readiness", f"{readiness}/100")
        c2.metric("Fatigue Impact", f"{fatigue}/10")
        c3.metric("Recovery Need", "High" if readiness < 50 else "Normal")
        c4.metric("Consistency", f"{analysis.get('consistency_percent', 0)}%")
        
        st.success("✅ Data saved to Long-Term Memory.")
        st.markdown("---")
    
    @staticmethod
    def _handle_submission(
        submitted: bool, 
        comment: str, 
        screenshot, 
        csv_text: str,
        sleep: float, 
        fatigue: int, 
        is_online: bool
    ) -> None:
        """Handle form submission."""
        if not submitted:
            return
        
        # Clear previous feedback
        st.session_state.show_workout_feedback = False
        st.session_state.last_workout_result = None
        
        if not comment and not screenshot and not csv_text:
            st.warning("⚠️ Please provide a description OR an image to log.")
            return
        
        if not is_online:
            st.error("🔴 API is Offline. Ensure api/app.py is running.")
            return
        
        with st.spinner("🤖 Extraction Agent reading data..."):
            # Prepare file upload
            files = None
            has_file = screenshot is not None
            
            if has_file:
                screenshot.seek(0)
                files = {
                    "screenshot": (
                        screenshot.name, 
                        screenshot.getvalue(), 
                        screenshot.type
                    )
                }
            
            # Prepare payload
            payload = {
                "user_comment": comment or "",
                "csv_text": csv_text or "",
                "sleep_hours": str(sleep),
                "user_id": st.session_state.user_id
            }
    
            if has_file:
                result = api.post("workout/submit", payload, files, as_form=True)
            else:
                # Text-only submission - use JSON
                result = api.post("workout/submit", payload, files=None, as_form=False)
            
        
        LogTab._display_result(result, fatigue)
    
    @staticmethod
    def _display_result(result: dict, fatigue: int) -> None:
        """Display submission result."""
        if "error" in result:
            st.error(f"❌ Error: {result['error']}")
            return
        
        # Store result for persistent display
        result['_fatigue'] = fatigue  # Store fatigue for display
        st.session_state.last_workout_result = result
        st.session_state.show_workout_feedback = True
        
        # Show toast notification
        st.toast("✅ Workout logged successfully!", icon="🎉")
        
        # Rerun to show persistent feedback
        st.rerun()


class DashboardTab:
    """Performance dashboard tab."""
    
    @staticmethod
    def render(is_online: bool) -> None:
        st.markdown("## 📊 Performance Dashboard")
        
        col_refresh, col_window = st.columns([1, 3])
        
        with col_refresh:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        with col_window:
            window = st.selectbox(
                "Analysis Window", 
                [7, 14, 28, 60], 
                index=2,
                format_func=lambda x: f"Last {x} days"
            )
        
        if not is_online:
            st.warning("Dashboard unavailable offline")
            return
        
    
        analysis = api.get("trends/analysis", {"window_days": window})
        stats = api.get("profile/stats")
        
        if "error" in analysis:
            DashboardTab._render_empty_state()
            return
        
        DashboardTab._render_metrics(analysis, stats)
        DashboardTab._render_charts(analysis)
        DashboardTab._render_recommendations(analysis)
    
    @staticmethod
    def _render_empty_state() -> None:
        """Render empty dashboard state."""
        st.warning("📊 No data available yet. Log your first workout in the Log tab!")
        st.markdown("""
        **Getting Started:**
        1. Go to the **Log** tab
        2. Describe your workout
        3. Add sleep and fatigue info
        4. Submit to see your analysis!
        """)
    
    @staticmethod
    def _render_metrics(analysis: dict, stats: dict) -> None:
        """Render metrics row."""
        st.markdown("### Key Metrics")
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            readiness = analysis.get('readiness_score', 70)
            emoji = analysis.get('readiness_emoji', '🟢')
            st.markdown(
                UIComponents.metric_card("Readiness", f"{emoji} {readiness}"),
                unsafe_allow_html=True
            )
        
        with c2:
            if "error" not in stats:
                distance = stats.get('total_distance_km', 0)
                st.markdown(
                    UIComponents.metric_card("Total Distance", f"{distance} km", "#4B9CD3"),
                    unsafe_allow_html=True
                )
            else:
                ctl = analysis.get('ctl', 0)
                st.markdown(
                    UIComponents.metric_card("CTL", f"{ctl:.0f}", "#4B9CD3"),
                    unsafe_allow_html=True
                )
        
        with c3:
            if "error" not in stats:
                streak = stats.get('current_streak_days', 0)
                st.markdown(
                    UIComponents.metric_card("Streak", f"{streak} Days", "#00C851"),
                    unsafe_allow_html=True
                )
            else:
                atl = analysis.get('atl', 0)
                st.markdown(
                    UIComponents.metric_card("ATL", f"{atl:.0f}", "#FFA500"),
                    unsafe_allow_html=True
                )
        
        with c4:
            consistency = analysis.get('consistency_percent', 0)
            st.markdown(
                UIComponents.metric_card("Consistency", f"{consistency}%", "#9B59B6"),
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _render_charts(analysis: dict) -> None:
        """Render charts section."""
        st.markdown("---")
        col_gauge, col_quote = st.columns([2, 1])
        
        with col_gauge:
            st.subheader("Readiness Gauge")
            score = analysis.get("readiness_score", 70)
            
            fig = DashboardTab._create_gauge_chart(score)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_quote:
            quote = analysis.get('motivational_quote', 'Keep pushing!')
            UIComponents.quote_box(quote)
            
            # Status display
            label = analysis.get("readiness_label", "Ready")
            if label in ["PEAK", "STRONG"]:
                st.success(f"**Status:** {label}")
            elif label == "MODERATE":
                st.info(f"**Status:** {label}")
            else:
                st.warning(f"**Status:** {label}")
            
            # Risk indicator
            risk = analysis.get("risk_level", 0)
            risk_label = "Low" if risk < 0.3 else "Moderate" if risk < 0.6 else "High"
            st.metric(
                "Overtraining Risk", 
                risk_label, 
                delta=f"{risk:.0%}", 
                delta_color="inverse"
            )
    
    @staticmethod
    def _create_gauge_chart(score: int) -> go.Figure:
        """Create readiness gauge chart."""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={
                'text': "Recovery Status", 
                'font': {'size': 20, 'color': 'white'}
            },
            delta={
                'reference': 70, 
                'increasing': {'color': "#00C851"}, 
                'decreasing': {'color': "#FF4B4B"}
            },
            gauge={
                'axis': {
                    'range': [0, 100], 
                    'tickwidth': 1, 
                    'tickcolor': "white"
                },
                'bar': {'color': "#FF4B4B"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 40], 'color': 'rgba(255,75,75,0.3)'},
                    {'range': [40, 70], 'color': 'rgba(255,165,0,0.3)'},
                    {'range': [70, 100], 'color': 'rgba(0,200,81,0.3)'}
                ],
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': score
                }
            }
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white", 'size': 14}
        )
        
        return fig
    
    @staticmethod
    def _render_recommendations(analysis: dict) -> None:
        """Render recommendations section."""
        st.markdown("### 📋 AI Recommendations")
        recs = analysis.get("recommendations", [])
        
        if recs:
            for i, rec in enumerate(recs, 1):
                st.markdown(f"{i}. {rec}")
        else:
            st.info("Log more workouts to get personalized recommendations!")


class PlanTab:
    """Training plan tab."""
    
    @staticmethod
    def render(is_online: bool, goal: str) -> None:
        st.markdown("## 📅 AI Training Plan")
        
        # Inputs
        col_goal, col_custom = st.columns([1, 1])
        
        with col_goal:
            plan_goal = st.selectbox(
                "Template Goal",
                GOALS,
                format_func=lambda x: x.replace("_", " ").title()
            )
        
        with col_custom:
            custom_req = st.text_input(
                "⚡ Custom Request (Trigger Safety: 'Marathon in 10 days')", 
                placeholder="e.g., 'Marathon in 10 days'"
            )
        
        generate = st.button(
            "🔄 Generate Plan", 
            type="primary", 
            use_container_width=True
        )
        
        # Handle generation
        if generate:
            PlanTab._generate_plan(is_online, plan_goal, custom_req)
        
        # Display current plan
        if st.session_state.current_plan:
            PlanTab._display_plan()
        else:
            st.info("Ready to generate.")
    
    @staticmethod
    def _generate_plan(is_online: bool, plan_goal: str, custom_req: str) -> None:
        """Generate a new training plan."""
        if not is_online:
            st.error("API Offline")
            return
        
        with st.spinner("🤖 Planner Agent analyzing risk..."):
            st.session_state.current_plan = None
            
            params = {"goal": plan_goal}
            if custom_req:
                params["custom_request"] = custom_req
            
            result = api.get("planner/week-plan", params)
        
        if "error" not in result:
            st.session_state.current_plan = result
            st.rerun()
        else:
            st.error(f"❌ {result['error']}")
    
    @staticmethod
    def _display_plan() -> None:
        """Display the current training plan."""
        plan = st.session_state.current_plan
        
        # Check for safety hold
        requires_approval = plan.get("requires_approval", False)
        is_approved = plan.get("approved", False)
        
        if requires_approval and not is_approved:
            PlanTab._render_safety_hold(plan)
            st.stop()
        
        # Render active plan
        PlanTab._render_active_plan(plan)
    
    @staticmethod
    def _render_safety_hold(plan: dict) -> None:
        """Render safety hold UI."""
        st.error("🛑 SAFETY PROTOCOL ACTIVATED")
        
        col_icon, col_text = st.columns([1, 5])
        with col_icon:
            st.markdown("# 🛡️")
        with col_text:
            st.markdown("### High Risk Plan Detected")
            st.caption("The Planner Agent has flagged this schedule due to high intensity.")
        
        with st.expander("Risk Analysis", expanded=True):
            reasons = plan.get("approval_reasons", ["High Volume", "Intensity > 8/10"])
            for reason in reasons:
                st.markdown(f"❌ **{reason}**")
        
        col_app, col_rej = st.columns(2)
        
        if col_app.button("✅ I Accept the Risk"):
            with st.spinner("Overriding Safety Protocols..."):
                api.post("planner/approve")
                st.session_state.current_plan["approved"] = True
                st.session_state.current_plan["status"] = "active"
                time.sleep(1)
                st.rerun()
        
        if col_rej.button("🗑️ Reject Plan"):
            st.session_state.current_plan = None
            st.rerun()
    
    @staticmethod
    def _render_active_plan(plan: dict) -> None:
        """Render active training plan."""
        st.success(f"✅ Active Plan: **{plan.get('week_focus', 'Training Schedule')}**")
        
        if plan.get("coach_explanation"):
            st.info(f"💬 **Coach:** {plan['coach_explanation']}")
        
        # Schedule table
        schedule = plan.get("training_plan", [])
        if schedule:
            df = pd.DataFrame(schedule)
            display_cols = [
                c for c in ["day", "name", "intensity_zone", "duration_min", "notes"] 
                if c in df.columns
            ]
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        
        if plan.get("motivational_message"):
            UIComponents.quote_box(f"💪 {plan['motivational_message']}")


class ChatTab:
    """Chat with coach tab."""
    
    @staticmethod
    def render(is_online: bool) -> None:
        st.markdown("## 💬 Chat with Coach")
        st.caption("Ask about your training, nutrition, recovery, or get motivation!")
        
        # Display history
        chat_container = st.container()
        with chat_container:
            for role, text in st.session_state.chat_history:
                with st.chat_message(role):
                    st.markdown(text)
        
        # Chat input
        if prompt := st.chat_input("Ask your coach anything..."):
            ChatTab._send_message(prompt, is_online)
            st.rerun()
        
        # Quick actions
        ChatTab._render_quick_actions(is_online)
    
    @staticmethod
    def _send_message(message: str, is_online: bool) -> None:
        """Send message to coach."""
        st.session_state.chat_history.append(("user", message))
        
        if not is_online:
            st.session_state.chat_history.append(("assistant", "⚠️ System is Offline"))
            return
        
        with st.spinner("🤔 Coach is thinking..."):
            try:
                result = requests.post(
                    f"{API_BASE}/chat/ask",
                    json={
                        "message": message, 
                        "user_id": st.session_state.user_id
                    },
                    timeout=REQUEST_TIMEOUT_LONG
                )
                
                if result.status_code == 200:
                    data = result.json()
                    reply = data.get("reply", "I'm here to help!")
                else:
                    reply = f"Error: {result.status_code}"
                    
            except requests.RequestException:
                reply = "Connection Error"
        
        st.session_state.chat_history.append(("assistant", reply))
    
    @staticmethod
    def _render_quick_actions(is_online: bool) -> None:
        """Render quick action buttons."""
        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("📊 Check Status", use_container_width=True):
            ChatTab._send_message("How am I doing?", is_online)
            st.rerun()
        
        if col2.button("🏋️ Today's Workout", use_container_width=True):
            ChatTab._send_message("What's my workout today?", is_online)
            st.rerun()
        
        if col3.button("💪 Motivate Me", use_container_width=True):
            ChatTab._send_message("I need motivation", is_online)
            st.rerun()
        
        if col4.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


class NutritionTab:
    """Nutrition tracking tab."""
    
    @staticmethod
    def render(is_online: bool, weight: float, goal: str) -> None:
        st.markdown("## 🍽️ Nutrition Tracking")
        
        col_log, col_summary = st.columns([1, 1])
        
        with col_log:
            NutritionTab._render_meal_log(is_online)
        
        with col_summary:
            NutritionTab._render_summary(is_online)
            NutritionTab._render_targets(is_online, weight, goal)
    
    @staticmethod
    def _render_meal_log(is_online: bool) -> None:
        """Render meal logging section."""
        st.markdown("### Log a Meal")
        
        meal_desc = st.text_area(
            "What did you eat?",
            placeholder="e.g., 3 eggs, 2 slices of toast, avocado, and a protein shake",
            height=100
        )
        
        meal_type = st.selectbox("Meal Type", MEAL_TYPES)
        
        if st.button("🍽️ Log Meal", type="primary", use_container_width=True):
            if not is_online:
                st.error("System Offline")
            elif not meal_desc:
                st.warning("Please describe your meal!")
            else:
                NutritionTab._submit_meal(meal_desc, meal_type)
    
    @staticmethod
    def _submit_meal(meal_desc: str, meal_type: str) -> None:
        """Submit meal to API."""
        with st.spinner("Analyzing nutrition..."):
            result = api.post("nutrition/log", {
                "meal_description": meal_desc,
                "meal_type": meal_type,
                "user_id": st.session_state.user_id
            })
        
        if "error" not in result and result.get("status") == "success":
            st.success("✅ Meal logged!")
            macros = result.get("macros", {})
            st.markdown(f"""
            **Estimated Macros:**
            - 🔥 Calories: {macros.get('calories', 0)}
            - 🥩 Protein: {macros.get('protein_g', 0)}g
            - 🍚 Carbs: {macros.get('carbs_g', 0)}g
            - 🥑 Fat: {macros.get('fat_g', 0)}g
            """)
        else:
            st.warning("Meal logged, but macro estimation unavailable.")
    
    @staticmethod
    def _render_summary(is_online: bool) -> None:
        """Render daily summary section."""
        st.markdown("### Today's Summary")
        
        if st.button("🔄 Refresh Summary", use_container_width=True):
            st.rerun()
        
        if not is_online:
            st.error("Offline")
            return
        
        summary = api.get("nutrition/summary")
        
        if "error" in summary or summary.get("status") != "success":
            st.info("Log meals to see your daily summary!")
            return
        
        totals = summary.get("totals", {})
        progress = summary.get("progress", {})
        
        st.markdown(f"""
        **Daily Totals:**
        - 🔥 Calories: {totals.get('calories', 0)}
        - 🥩 Protein: {totals.get('protein_g', 0)}g ({progress.get('protein', 0)}% of target)
        - 🍚 Carbs: {totals.get('carbs_g', 0)}g
        - 🥑 Fat: {totals.get('fat_g', 0)}g
        """)
        
        # Recovery score
        recovery = summary.get("recovery_score")
        if recovery:
            st.metric("Recovery Nutrition Score", f"{recovery}/100")
        
        # Recommendations
        recs = summary.get("recommendations", [])
        if recs:
            st.markdown("**Tips:**")
            for rec in recs[:2]:
                st.markdown(f"• {rec}")
    
    @staticmethod
    def _render_targets(is_online: bool, weight: float, goal: str) -> None:
        """Render nutrition targets section."""
        st.markdown("---")
        st.markdown("### 🎯 Your Targets")
        
        if not is_online:
            st.caption("Offline")
            return
        
        targets = api.get("nutrition/targets", {"weight_kg": weight, "goal": goal})
        
        if "error" not in targets:
            daily = targets.get("daily_targets", {})
            st.markdown(f"""
            Based on your profile:
            - Calories: **{daily.get('calories', 2000)}** kcal
            - Protein: **{daily.get('protein_g', 120)}**g
            - Carbs: **{daily.get('carbs_g', 250)}**g
            - Fat: **{daily.get('fat_g', 70)}**g
            """)


class Footer:
    """App footer."""
    
    @staticmethod
    def render() -> None:
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9rem;">
            🧠 <strong>FitForge AI</strong> — Google ADK Capstone Project 2025<br>
            Multi-Agent Fitness Assistant powered by Gemini
        </div>
        """, unsafe_allow_html=True)


# ========================================
# MAIN APPLICATION
# ========================================
def restore_state(is_online: bool) -> None:
    """Restore session state from API on refresh."""
    if not is_online or st.session_state.current_plan is not None:
        return
    
    try:
        restore_data = api.get("planner/active")
        if restore_data.get("found") is True:
            st.session_state.current_plan = restore_data
    except Exception:
        pass


def main():
    """Main application entry point."""
    # Initialize
    load_styles()
    init_session_state()
    
    # Check API connection
    is_online, system_status = api.check_health()
    
    # Restore state if needed
    restore_state(is_online)
    
    # Render header
    HeaderSection.render(is_online)
    
    # Render sidebar and get profile data
    name, weight, goal = SidebarSection.render(is_online, system_status)
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Log", 
        "📊 Dashboard", 
        "📅 Plan", 
        "💬 Chat", 
        "🍽️ Nutrition"
    ])
    
    with tab1:
        LogTab.render(is_online)
    
    with tab2:
        DashboardTab.render(is_online)
    
    with tab3:
        PlanTab.render(is_online, goal)
    
    with tab4:
        ChatTab.render(is_online)
    
    with tab5:
        NutritionTab.render(is_online, weight, goal)
    
    # Footer
    Footer.render()


if __name__ == "__main__":
    main()