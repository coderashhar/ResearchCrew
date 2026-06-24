import streamlit as st
import time
import re
from datetime import datetime
from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchCrew — Multi-Agent Research",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ─── Root Variables ─── */
:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: rgba(18, 18, 30, 0.6);
    --bg-card-hover: rgba(25, 25, 45, 0.8);
    --border-glass: rgba(255, 255, 255, 0.06);
    --border-glow: rgba(99, 102, 241, 0.3);
    --text-primary: #e8e8f0;
    --text-secondary: #8b8ba3;
    --text-muted: #5a5a72;
    --accent-indigo: #6366f1;
    --accent-violet: #8b5cf6;
    --accent-cyan: #22d3ee;
    --accent-emerald: #34d399;
    --accent-amber: #fbbf24;
    --accent-rose: #fb7185;
    --gradient-hero: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
    --gradient-card: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.04) 100%);
    --shadow-glow: 0 0 40px rgba(99, 102, 241, 0.15);
    --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3);
}

/* ─── Global Overrides ─── */
.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

.stApp > header {
    background: transparent !important;
}

.stMainBlockContainer {
    padding-top: 2rem !important;
}

/* ─── Sidebar ─── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d15 0%, #0a0a12 100%) !important;
    border-right: 1px solid var(--border-glass) !important;
}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text-primary) !important;
}

/* ─── Text Input ─── */
.stTextInput > div > div > input {
    background: rgba(15, 15, 25, 0.8) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.85rem 1.2rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent-indigo) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15), var(--shadow-glow) !important;
}

.stTextInput > div > div > input::placeholder {
    color: var(--text-muted) !important;
}

/* ─── Buttons ─── */
.stButton > button {
    background: var(--gradient-hero) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.85rem 2.5rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.45) !important;
}

.stButton > button:active {
    transform: translateY(0px) !important;
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: transparent !important;
    border-bottom: 1px solid var(--border-glass) !important;
    padding-bottom: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 0.75rem 1.5rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    border: none !important;
    transition: all 0.3s ease !important;
}

.stTabs [aria-selected="true"] {
    background: var(--gradient-card) !important;
    color: var(--accent-indigo) !important;
    border-bottom: 2px solid var(--accent-indigo) !important;
}

/* ─── Expander ─── */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ─── Markdown ─── */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

.stMarkdown p, .stMarkdown li {
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ─── Spinner ─── */
.stSpinner > div {
    border-top-color: var(--accent-indigo) !important;
}

/* ─── Toast / Alerts ─── */
.stAlert {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
}

/* ─── Scrollbar ─── */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.5);
}

/* ─── Hero Section ─── */
.hero-container {
    text-align: center;
    padding: 2rem 0 1rem 0;
    position: relative;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 100px;
    padding: 6px 18px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--accent-indigo);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
    font-family: 'Inter', sans-serif;
}

.hero-title {
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 0.75rem;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #e8e8f0 0%, #6366f1 50%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    font-size: 1.1rem;
    color: var(--text-secondary);
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.6;
    font-family: 'Inter', sans-serif;
}

/* ─── Pipeline Visualization ─── */
.pipeline-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 2rem 1rem;
    flex-wrap: nowrap;
    overflow-x: auto;
}

.pipeline-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    min-width: 120px;
    position: relative;
}

.node-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    border: 1px solid var(--border-glass);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}

.node-icon.waiting {
    background: rgba(20, 20, 35, 0.8);
    border-color: var(--border-glass);
}

.node-icon.running {
    background: rgba(99, 102, 241, 0.15);
    border-color: var(--accent-indigo);
    box-shadow: 0 0 25px rgba(99, 102, 241, 0.3);
    animation: nodePulse 2s ease-in-out infinite;
}

.node-icon.done {
    background: rgba(52, 211, 153, 0.12);
    border-color: var(--accent-emerald);
    box-shadow: 0 0 20px rgba(52, 211, 153, 0.2);
}

.node-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: 'Inter', sans-serif;
    transition: color 0.3s ease;
}

.node-label.running { color: var(--accent-indigo); }
.node-label.done { color: var(--accent-emerald); }

.pipeline-arrow {
    font-size: 1.2rem;
    color: var(--text-muted);
    margin: 0 6px;
    margin-bottom: 20px;
    opacity: 0.4;
    transition: all 0.3s ease;
}

.pipeline-arrow.active {
    color: var(--accent-indigo);
    opacity: 1;
    animation: arrowFlow 1.5s ease-in-out infinite;
}

.pipeline-arrow.done {
    color: var(--accent-emerald);
    opacity: 0.7;
}

@keyframes nodePulse {
    0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.2); }
    50% { box-shadow: 0 0 35px rgba(99, 102, 241, 0.45); }
}

@keyframes arrowFlow {
    0%, 100% { transform: translateX(0); opacity: 0.7; }
    50% { transform: translateX(4px); opacity: 1; }
}

/* ─── Glass Cards ─── */
.glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
    border-color: rgba(99, 102, 241, 0.15);
    box-shadow: var(--shadow-glow);
}

.glass-card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-glass);
}

.glass-card-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
}

.glass-card-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}

.glass-card-subtitle {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: 'Inter', sans-serif;
}

.glass-card-body {
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.7;
    font-family: 'Inter', sans-serif;
}

/* ─── Score Display ─── */
.score-ring {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem;
    position: relative;
}

.score-ring-inner {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: var(--bg-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}

.score-value {
    font-size: 2rem;
    font-weight: 800;
    font-family: 'Inter', sans-serif;
}

.score-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-family: 'Inter', sans-serif;
}

/* ─── Stats Row ─── */
.stats-row {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
}

.stat-item {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: 'Inter', sans-serif;
}

/* ─── Sidebar Styles ─── */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border-glass);
    margin-bottom: 1.5rem;
}

.sidebar-brand-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--gradient-hero);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
}

.sidebar-brand-text {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    line-height: 1.2;
}

.sidebar-brand-sub {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-family: 'Inter', sans-serif;
}

.agent-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.3s ease;
}

.agent-card:hover {
    border-color: rgba(99, 102, 241, 0.2);
}

.agent-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.agent-info {
    flex: 1;
}

.agent-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}

.agent-role {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: 'Inter', sans-serif;
}

/* ─── Empty State ─── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
}

.empty-state-icon {
    font-size: 4rem;
    margin-bottom: 1.5rem;
    opacity: 0.3;
}

.empty-state-text {
    font-size: 1.1rem;
    color: var(--text-muted);
    font-family: 'Inter', sans-serif;
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.6;
}

/* ─── Animations ─── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in-up {
    animation: fadeInUp 0.6s ease-out forwards;
}

.delay-1 { animation-delay: 0.1s; opacity: 0; }
.delay-2 { animation-delay: 0.2s; opacity: 0; }
.delay-3 { animation-delay: 0.3s; opacity: 0; }
.delay-4 { animation-delay: 0.4s; opacity: 0; }

/* ─── Divider ─── */
hr {
    border: none;
    border-top: 1px solid var(--border-glass);
    margin: 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ─────────────────────────────────────────────────────────
def get_node_state(step_index: int, current_step: int) -> str:
    if step_index < current_step:
        return "done"
    elif step_index == current_step:
        return "running"
    return "waiting"

def get_arrow_state(step_index: int, current_step: int) -> str:
    if step_index < current_step:
        return "done"
    elif step_index == current_step:
        return "active"
    return ""

def build_pipeline_html(current_step: int = -1) -> str:
    """Build pipeline HTML string without rendering it."""
    agents = [
        ("🔍", "Search"),
        ("📖", "Scrape"),
        ("✍️", "Writer"),
        ("🧠", "Critic"),
    ]
    nodes_html = ""
    for i, (icon, label) in enumerate(agents):
        state = get_node_state(i, current_step)
        check = " ✓" if state == "done" else ""
        nodes_html += f"""
        <div class="pipeline-node">
            <div class="node-icon {state}">{icon}{check}</div>
            <div class="node-label {state}">{label}</div>
        </div>
        """
        if i < len(agents) - 1:
            arrow_state = get_arrow_state(i, current_step)
            nodes_html += f'<div class="pipeline-arrow {arrow_state}">⟶</div>'

    return f'<div class="pipeline-container">{nodes_html}</div>'

def parse_critic_score(feedback: str) -> int:
    match = re.search(r"Score:\s*(\d+)\s*/\s*10", feedback)
    if match:
        return int(match.group(1))
    return 0

def get_score_color(score: int) -> str:
    if score >= 8:
        return "var(--accent-emerald)"
    elif score >= 6:
        return "var(--accent-amber)"
    return "var(--accent-rose)"

def render_glass_card(icon: str, title: str, subtitle: str, body: str, icon_bg: str = "rgba(99,102,241,0.12)"):
    st.markdown(f"""
    <div class="glass-card fade-in-up">
        <div class="glass-card-header">
            <div class="glass-card-icon" style="background: {icon_bg};">{icon}</div>
            <div>
                <div class="glass-card-title">{title}</div>
                <div class="glass-card-subtitle">{subtitle}</div>
            </div>
        </div>
        <div class="glass-card-body">{body}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────────────────────
if "pipeline_state" not in st.session_state:
    st.session_state.pipeline_state = {}
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "current_step" not in st.session_state:
    st.session_state.current_step = -1
if "research_history" not in st.session_state:
    st.session_state.research_history = []


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-icon">🔬</div>
        <div>
            <div class="sidebar-brand-text">ResearchCrew</div>
            <div class="sidebar-brand-sub">Multi-Agent System</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🤖 Agent Network")

    agents_info = [
        ("🔍", "Search Agent", "Web discovery", "#6366f1"),
        ("📖", "Scrape Agent", "Content extraction", "#22d3ee"),
        ("✍️", "Writer Agent", "Report synthesis", "#8b5cf6"),
        ("🧠", "Critic Agent", "Quality evaluation", "#fb7185"),
    ]

    for icon, name, role, color in agents_info:
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-dot" style="background: {color}; box-shadow: 0 0 8px {color}55;"></div>
            <div class="agent-info">
                <div class="agent-name">{icon} {name}</div>
                <div class="agent-role">{role}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Research history
    if st.session_state.research_history:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### 📜 History")
        for i, entry in enumerate(reversed(st.session_state.research_history[-5:])):
            score = parse_critic_score(entry.get("feedback", ""))
            score_color = get_score_color(score)
            st.markdown(f"""
            <div class="agent-card">
                <div class="agent-dot" style="background: {score_color};"></div>
                <div class="agent-info">
                    <div class="agent-name" style="font-size: 0.78rem;">{entry['topic'][:35]}{'...' if len(entry['topic']) > 35 else ''}</div>
                    <div class="agent-role">Score: {score}/10</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Main Content ─────────────────────────────────────────────────────────────

# Hero Section
st.markdown("""
<div class="hero-container fade-in-up">
    <div class="hero-badge">✦ AI-Powered Research Pipeline</div>
    <div class="hero-title">ResearchCrew</div>
    <div class="hero-subtitle">Four specialized AI agents collaborate to search, scrape, write, and critique — delivering comprehensive research reports in minutes.</div>
</div>
""", unsafe_allow_html=True)

# Input Section
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    topic = st.text_input(
        "Research Topic",
        placeholder="e.g. Latest breakthroughs in quantum computing",
        label_visibility="collapsed",
        key="topic_input",
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        run_clicked = st.button(
            "🚀 Start Research",
            use_container_width=True,
            disabled=st.session_state.is_running,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Single Pipeline Placeholder ──────────────────────────────────────────────
pipeline_placeholder = st.empty()

# Show idle pipeline when not running and no completed results
if not st.session_state.is_running and not st.session_state.pipeline_state:
    pipeline_placeholder.markdown(build_pipeline_html(-1), unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Results Area (single placeholder — clears on new run) ───────────────────
results_area = st.container()

# ── Run Pipeline ─────────────────────────────────────────────────────────────
if run_clicked and topic.strip():
    # Clear previous results by resetting state
    st.session_state.is_running = True
    st.session_state.pipeline_state = {}
    state = {}
    start_time = time.time()
    today = datetime.now().strftime("%B %d, %Y")

    # STEP 0 — Search Agent
    pipeline_placeholder.markdown(build_pipeline_html(0), unsafe_allow_html=True)

    with results_area:
        with st.status("🔍 **Search Agent** — Discovering relevant sources...", expanded=True) as status:
            st.markdown(f"*Searching for:* `{topic}`")
            search_agent = build_search_agent()
            search_result = search_agent.invoke({
                "messages": [("user",
                    f"Today's date is {today}. "
                    f"Find the most recent, up-to-date and reliable information about: {topic}. "
                    f"Focus on results from 2025-2026 only."
                )]
            })
            state["search_results"] = search_result['messages'][-1].content
            status.update(label="✅ **Search Agent** — Found sources!", state="complete")
            st.markdown(f"```\n{state['search_results'][:600]}{'...' if len(state['search_results']) > 600 else ''}\n```")

    # STEP 1 — Scrape Agent
    pipeline_placeholder.markdown(build_pipeline_html(1), unsafe_allow_html=True)

    with results_area:
        with st.status("📖 **Scrape Agent** — Extracting content from top sources...", expanded=True) as status:
            reader_agent = build_reader_agent()
            reader_result = reader_agent.invoke({
                "messages": [("user",
                    f"Based on the following search results about '{topic}', "
                    f"pick the most relevant URL and scrape it for deeper content.\n\n"
                    f"Search Results:\n{state['search_results'][:800]}"
                )]
            })
            state['scraped_content'] = reader_result['messages'][-1].content
            status.update(label="✅ **Scrape Agent** — Content extracted!", state="complete")
            st.markdown(f"```\n{state['scraped_content'][:600]}{'...' if len(state['scraped_content']) > 600 else ''}\n```")

    # STEP 2 — Writer Agent
    pipeline_placeholder.markdown(build_pipeline_html(2), unsafe_allow_html=True)

    with results_area:
        with st.status("✍️ **Writer Agent** — Drafting research report...", expanded=True) as status:
            research_combined = (
                f"SEARCH RESULTS:\n{state['search_results']}\n\n"
                f"DETAILED SCRAPED CONTENT:\n{state['scraped_content']}"
            )
            state["report"] = writer_chain.invoke({
                "topic": topic,
                "research": research_combined,
            })
            status.update(label="✅ **Writer Agent** — Report drafted!", state="complete")
            st.markdown("*Report generated successfully — see Results tab below.*")

    # STEP 3 — Critic Agent
    pipeline_placeholder.markdown(build_pipeline_html(3), unsafe_allow_html=True)

    with results_area:
        with st.status("🧠 **Critic Agent** — Evaluating report quality...", expanded=True) as status:
            state["feedback"] = critic_chain.invoke({
                "report": state["report"]
            })
            status.update(label="✅ **Critic Agent** — Evaluation complete!", state="complete")
            score = parse_critic_score(state["feedback"])
            st.markdown(f"**Score: {score}/10**")

    elapsed = round(time.time() - start_time, 1)
    state["elapsed"] = elapsed
    state["topic"] = topic

    # All done — show completed pipeline
    pipeline_placeholder.markdown(build_pipeline_html(4), unsafe_allow_html=True)

    # Save to session and history
    st.session_state.pipeline_state = state
    st.session_state.is_running = False

    st.session_state.research_history.append({
        "topic": topic,
        "report": state["report"],
        "feedback": state["feedback"],
        "elapsed": elapsed,
    })

    # ── Results Section ──────────────────────────────────────────────────
    with results_area:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        score = parse_critic_score(state["feedback"])
        score_color = get_score_color(score)

        # Stats Row
        word_count = len(state["report"].split())
        source_count = state["report"].lower().count("http")
        st.markdown(f"""
        <div class="stats-row fade-in-up">
            <div class="stat-item">
                <div class="stat-value" style="color: {score_color};">{score}/10</div>
                <div class="stat-label">Quality Score</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" style="color: var(--accent-indigo);">{word_count:,}</div>
                <div class="stat-label">Words</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" style="color: var(--accent-cyan);">{source_count}</div>
                <div class="stat-label">Sources</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" style="color: var(--accent-violet);">{elapsed}s</div>
                <div class="stat-label">Time Elapsed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tabs for results
        tab_report, tab_critique, tab_raw = st.tabs(["📄 Research Report", "🧠 Critic Evaluation", "🗂 Raw Data"])

        with tab_report:
            st.markdown(f"""
            <div class="glass-card fade-in-up delay-1">
                <div class="glass-card-header">
                    <div class="glass-card-icon" style="background: rgba(139,92,246,0.12);">📄</div>
                    <div>
                        <div class="glass-card-title">Research Report</div>
                        <div class="glass-card-subtitle">{topic}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(state["report"])
            st.download_button(
                label="📥 Download Report",
                data=state["report"],
                file_name=f"research_report_{topic[:30].replace(' ', '_')}.md",
                mime="text/markdown",
            )

        with tab_critique:
            # Score ring
            st.markdown(f"""
            <div style="text-align: center; padding: 1.5rem 0;" class="fade-in-up delay-2">
                <div class="score-ring" style="background: conic-gradient({score_color} {score * 36}deg, rgba(30,30,50,0.5) {score * 36}deg);">
                    <div class="score-ring-inner">
                        <div class="score-value" style="color: {score_color};">{score}</div>
                        <div class="score-label">out of 10</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="glass-card fade-in-up delay-3">
                <div class="glass-card-header">
                    <div class="glass-card-icon" style="background: rgba(251,113,133,0.12);">🧠</div>
                    <div>
                        <div class="glass-card-title">Critic Evaluation</div>
                        <div class="glass-card-subtitle">Automated quality assessment</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(state["feedback"])

        with tab_raw:
            render_glass_card(
                "🔍", "Search Results", "Raw search agent output",
                f"<pre style='white-space: pre-wrap; font-family: JetBrains Mono, monospace; font-size: 0.78rem; color: var(--text-secondary); max-height: 400px; overflow-y: auto;'>{state['search_results'][:2000]}</pre>",
                "rgba(99,102,241,0.12)"
            )
            render_glass_card(
                "📖", "Scraped Content", "Raw scrape agent output",
                f"<pre style='white-space: pre-wrap; font-family: JetBrains Mono, monospace; font-size: 0.78rem; color: var(--text-secondary); max-height: 400px; overflow-y: auto;'>{state['scraped_content'][:2000]}</pre>",
                "rgba(34,211,238,0.12)"
            )

elif not st.session_state.pipeline_state and not st.session_state.is_running:
    # Empty State
    with results_area:
        st.markdown("""
        <div class="empty-state fade-in-up">
            <div class="empty-state-icon">🧪</div>
            <div class="empty-state-text">
                Enter a research topic above and hit <strong>Start Research</strong> to activate the multi-agent pipeline. Four AI agents will collaborate to deliver a comprehensive report.
            </div>
        </div>
        """, unsafe_allow_html=True)
