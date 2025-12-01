# 🧠 FitForge AI — Intelligent Fitness Orchestrator

<div align="center">

![FitForge AI Banner](https://img.shields.io/badge/Google%20ADK-Capstone%202025-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-8E44AD?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A Multi-Agent Fitness Concierge Powered by Google's Gen AI Agents SDK**

[Features](#-key-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Demo](#-demo) • [Roadmap](#-roadmap)

</div>

---

## 🎯 The Problem

Modern fitness data is **fragmented across dozens of apps** that don't communicate:

| Data Type | Scattered Across |
|-----------|------------------|
| 🏃 Workouts | Strava, Garmin, Apple Health, Peloton |
| 🍎 Nutrition | MyFitnessPal, Cronometer, Lose It! |
| 😴 Recovery | Whoop, Oura, Eight Sleep |
| 🧠 Subjective Feel | *Only in your head* |

**The result?** Training apps that can only see partial data make recommendations that look smart on charts but feel completely wrong in real life.

> *"My app told me to do intervals today, but it doesn't know I barely slept and did a hard hike yesterday that I forgot to log."*

---

## 💡 The Solution

FitForge AI acts as a **unified orchestration layer** for your training life.
┌─────────────────────────────────────────────────────────────────┐
│ YOUR REALITY │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Strava │ │ Garmin │ │ Sleep │ │ "I feel │ │
│ │ Screenshot│ │ Export │ │ Data │ │ tired" │ │
│ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ │
│ │ │ │ │ │
│ └────────────┴────────────┴────────────┘ │
│ │ │
│ ┌─────▼─────┐ │
│ │ FitForge │ │
│ │ AI │ │
│ └─────┬─────┘ │
│ │ │
│ ┌─────────────┼─────────────┐ │
│ ▼ ▼ ▼ │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Unified │ │ Smart │ │ Safe │ │
│ │ History │ │ Planning │ │ Guidance │ │
│ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────────┘

text


---

## ✨ Key Features

### 1. 📸 Zero-Click Workout Logging

**Drop a screenshot. Done.**

| What You Do | What FitForge Does |
|-------------|-------------------|
| Finish your run | Take a screenshot of your watch/app |
| Drag & drop into FitForge | Gemini Vision extracts all metrics |
| That's it | Distance, pace, HR, duration — all logged automatically |

```python
# Behind the scenes
extracted = {
    "activity_type": "run",
    "distance_km": 5.2,
    "duration_min": 28,
    "avg_pace": "5:23/km",
    "avg_heart_rate": 156,
    "calories": 412
}
No manual data entry. Just a screenshot.

2. 🛡️ Safety Hold — Human in the Loop
FitForge won't blindly execute risky plans.

text

┌────────────────────────────────────────────────────────────┐
│  🛑 SAFETY PROTOCOL ACTIVATED                              │
│                                                            │
│  Your request: "Marathon plan in 10 days"                  │
│                                                            │
│  ⚠️  Risk Analysis:                                        │
│      ❌ Volume increase: 340% (safe limit: 10%)            │
│      ❌ Insufficient base training detected                │
│      ❌ High injury probability: 78%                       │
│                                                            │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ ✅ I Accept Risk │  │ 🗑️ Reject Plan   │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────────────────────────────────────────┘
The AI can be ambitious, but YOU must approve risky plans.

3. 🧮 Grounded Math, Not Hallucinated Numbers
LLMs are great at language but unreliable for calculations. FitForge uses real Python tools for anything numeric:

Metric	Calculation Method
Training Stress Score (TSS)	Python function with HR zones
Calorie needs	Mifflin-St Jeor + activity factor
Recovery time	Based on workout intensity + sleep
Weekly volume limits	10% rule with individual adjustments
Python

# Example: TSS is CALCULATED, not guessed
def calculate_tss(duration_min: float, intensity_factor: float, ftp: float) -> float:
    """Training Stress Score — deterministic, not LLM-generated."""
    normalized_power = intensity_factor * ftp
    return (duration_min * normalized_power * intensity_factor) / (ftp * 3600) * 100
4. 🧠 Persistent Memory
FitForge remembers your history, injuries, and preferences across sessions:

Python

# Your context persists
{
    "user:name": "Alex",
    "user:injuries": ["left knee - 2023", "plantar fasciitis - 2024"],
    "user:goal": "sub-4 marathon",
    "user:weekly_limit_km": 60,
    "user:workout_log": [...],  # Full history
    "app:current_plan": {...}   # Active training plan
}
🏗️ Architecture
FitForge uses a multi-agent orchestration pattern built on Google's ADK:

text

                         ┌─────────────────┐
                         │   USER INPUT    │
                         │  (text/image)   │
                         └────────┬────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │      ORCHESTRATOR       │
                    │   (Intent Detection)    │
                    └─────────────┬───────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   EXTRACTION    │    │     COACH       │    │    PLANNER      │
│     AGENT       │    │     AGENT       │    │     AGENT       │
│                 │    │                 │    │                 │
│ • Vision OCR   │    │ • Motivation    │    │ • Weekly plans  │
│ • Text parsing │    │ • Q&A           │    │ • Risk analysis │
│ • Data cleanup │    │ • Daily summary │    │ • Periodization │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │      ANALYZER AGENT     │
                    │                         │
                    │  • Readiness score      │
                    │  • TSS / CTL / ATL      │
                    │  • Risk assessment      │
                    │  • Recommendations      │
                    └─────────────┬───────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   PERSISTENT MEMORY     │
                    │      (SQLite)           │
                    └─────────────────────────┘
Agent Responsibilities
Agent	Role	Key Tools
🎭 Orchestrator	Routes requests to appropriate agents	Intent detection, context management
📸 Extraction	Converts unstructured data to structured	Gemini Vision, regex parsing
🏋️ Coach	Conversational interface, motivation	Chat history, personality
📅 Planner	Creates periodized training schedules	Templates, AI generation
📊 Analyzer	Calculates metrics and readiness	Python math tools
🍎 Nutrition	Tracks meals and macros	Calorie estimation
🔬 Research	Answers training methodology questions	Grounded search
🚀 Quick Start
Prerequisites
Requirement	Version
Python	3.10+
Google API Key	Gemini 2.0 Flash access
OS	macOS, Linux, Windows
Installation
Bash

# 1. Clone the repository
git clone https://github.com/your-username/fitforge-ai.git
cd fitforge-ai

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
Configuration
Create a .env file in the project root:

env

# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional
FITFORGE_API_URL=http://localhost:8000/api/v1
DEBUG=false
Running the App
You need two terminal windows:

Terminal 1 — Backend API

Bash

python api/app.py
text

🚀 FITFORGE AI API v2.2.0
══════════════════════════════════════════
📊 Agents Status:
   • Orchestrator: ✅
   • Analyzer:     ✅
   • Planner:      ✅
   • Coach:        ✅
══════════════════════════════════════════
🔗 API Docs: http://localhost:8000/docs
Terminal 2 — Streamlit UI

Bash

streamlit run ui/streamlit_app.py
Open http://localhost:8501 in your browser.

📱 Demo
Logging a Workout
Workout Logging Demo

Go to the 📝 Log tab
Drop a screenshot OR type a description
Add sleep/fatigue context
Click LOG WORKOUT
See instant feedback and updated stats
Generating a Training Plan
Plan Generation Demo

Go to the 📅 Plan tab
Select your goal
(Optional) Add a custom request
Click Generate Plan
Review and approve if flagged as risky
📁 Project Structure
text

fitforge-ai/
├── 📁 api/
│   └── app.py              # FastAPI backend
├── 📁 ui/
│   └── streamlit_app.py    # Streamlit frontend
├── 📁 agents/
│   ├── orchestrator.py     # Main routing logic
│   ├── extraction_agent.py # Vision & text extraction
│   ├── coach_agent.py      # Conversational coaching
│   ├── planner_agent.py    # Training plan generation
│   ├── analyzer_agent.py   # Performance analysis
│   ├── nutrition_agent.py  # Meal tracking
│   └── research_agent.py   # Training methodology Q&A
├── 📁 memory/
│   └── session_manager.py  # Persistent storage
├── 📁 tools/
│   └── calculators.py      # Deterministic math functions
├── 📁 tests/
│   └── ...                 # Unit tests
├── .env.example            # Environment template
├── requirements.txt        # Dependencies
└── README.md               # This file
🗺️ Roadmap
✅ Completed (v1.0)
 Multi-agent orchestration
 Vision-based workout extraction
 Text workout logging
 Safety Hold for risky plans
 Persistent memory
 Performance dashboard
 Chat interface
🚧 In Progress (v1.1)
 Improved extraction accuracy
 Better error handling
 Enhanced coach personality
🔮 Future (v2.0+)
Feature	Description
📸 Visual Nutrition	Snap a photo of your meal → instant macro estimates
🔗 Direct API Integrations	Connect to Strava, Garmin, Apple Health directly
🎙️ Voice Mode	Real-time voice coaching during workouts
📱 Mobile App	Native iOS/Android experience
🌅 Daily Briefings	Morning/evening push summaries
👥 Multi-user Support	Household/team accounts
⚠️ Medical Disclaimer
<div align="center">
FitForge AI is a proof-of-concept, NOT a medical or clinical tool.

</div>
This application can generate training suggestions, but it does NOT replace:

👨‍⚕️ A physician
🏥 A physical therapist
🏃 A certified coach
The built-in Safety Hold is an algorithmic safeguard, not medical judgment.

Always consult a healthcare professional before starting or changing a training program.

🤖 AI Transparency
How AI Was Used in Building This Project
Aspect	Approach
Architecture	Human-designed agents, orchestration, and safety mechanisms
Implementation	AI-assisted code generation for boilerplate (FastAPI, Streamlit)
Review	All AI-generated code manually reviewed, edited, and tested
Decisions	Architectural and safety choices made by humans
FitForge uses Gemini 2.0 Flash for:

Natural language understanding
Vision-based data extraction
Conversational responses
All numeric calculations use deterministic Python functions, not LLM outputs.

🛠️ Tech Stack
Layer	Technology
AI Framework	Google Gen AI Agents SDK (ADK)
LLM	Gemini 2.0 Flash
Vision	Gemini Vision API
Backend	FastAPI
Frontend	Streamlit
Database	SQLite (persistent sessions)
Language	Python 3.10+
🤝 Contributing
Contributions are welcome! Here's how:

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
Ideas for Contributions
🧪 Additional unit tests
📊 New analysis metrics
🎨 UI/UX improvements
📝 Documentation
🌐 Internationalization
