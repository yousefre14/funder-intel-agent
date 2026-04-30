"""
Funder Intelligence Agent — Streamlit Web Interface

This transforms the command-line agent into a web application.
Any non-technical user can type a funder name and get results.

Run with:
    streamlit run app.py

WHY STREAMLIT?
  - Python-native (no HTML/CSS/JavaScript needed)
  - Built for data/AI apps
  - Free hosting on Streamlit Community Cloud
  - Goes from script → web app in ~100 lines
"""
from tools.path import get_output_dir, get_output_path, get_safe_name
import streamlit as st
import os
import time
from datetime import datetime

# ---- Page Configuration ----
# This MUST be the first Streamlit command in the file
st.set_page_config(
    page_title="Funder Intelligence Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="auto",
)


# ============================================================
# IMPORT YOUR AGENTS (with error handling)
# ============================================================

@st.cache_resource
def load_agents():
    """
    Import all agents once and cache them.
    
    WHY @st.cache_resource?
    Streamlit reruns the entire script on every interaction.
    Without caching, it would re-import everything every click.
    cache_resource tells Streamlit: "import once, reuse forever."
    """
    try:
        from agents.reasercher import research_funder
        from agents.mapper import create_alignment_brief
        from agents.connector import find_connection_paths
        from agents.drafters import draft_initial_outreach, draft_followup
        from tools.org_knowledge import build_knowledge_base, print_knowledge_status
        import config
        
        return {
            "research": research_funder,
            "alignment": create_alignment_brief,
            "connections": find_connection_paths,
            "drafts": draft_initial_outreach,
            "followup": draft_followup,
            "build_kb": build_knowledge_base,
            "config": config,
        }
    except Exception as e:
        st.error(f"Failed to load agents: {e}")
        return None


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():
    """Render the sidebar with settings and info"""
    
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/search--v1.png", width=60)
        st.title("Funder Intel Agent")
        st.caption("AI-powered funder research & outreach")
        
        st.divider()
        
        # ---- Mode Selection ----
        st.subheader("⚙️ Mode")
        mode = st.radio(
            "Choose what to run:",
            [
                "🚀 Full Pipeline",
                "📋 Research Only",
                "🎯 Alignment Only",
                "🔗 Connections Only",
                "✉️ Outreach Drafts Only",
            ],
            index=0,
        )
        
        st.divider()
        
        # ---- Organization Settings ----
        st.subheader("🏢 Organization")
        org_name = st.text_input(
            "Your org name",
            value="Rural Opportunity Institute",
        )
        
        known_funders = st.text_area(
            "Your current funders (one per line)",
            value="Appalachian Regional Commission\nBenedum Foundation\nSisters of Charity Foundation",
            height=100,
        )
        
        st.divider()
        
        # ---- Knowledge Base Status ----
        st.subheader("📚 Knowledge Base")
        
        kb_path = os.path.join("data", "org_knowledge")
        if os.path.exists(kb_path):
            docs = [f for f in os.listdir(kb_path) 
                    if f.endswith(('.md', '.txt')) and f.lower() != 'readme.md']
            st.success(f"{len(docs)} document(s) loaded")
            for doc in docs:
                st.caption(f"  📄 {doc}")
        else:
            st.warning("No documents found")
        
        if st.button("🔄 Rebuild Knowledge Base"):
            agents = load_agents()
            if agents:
                agents["build_kb"](force_rebuild=True)
                st.success("Knowledge base rebuilt!")
        
        st.divider()
        
        # ---- Output Files ----
        st.subheader("📂 Output Files")
        output_path = os.path.join("data", "output")
        if os.path.exists(output_path):
            files = sorted(os.listdir(output_path))
            if files:
                for f in files[-10:]:  # Show last 10 files
                    st.caption(f"📄 {f}")
            else:
                st.caption("No output files yet")
        
        st.divider()
        
        # ---- API Usage ----
        st.subheader("📊 API Usage (this session)")
        agents = load_agents()
        if agents:
            config = agents["config"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Groq", config.TOTAL_REQUESTS.get("groq", 0))
            col2.metric("Gemini", config.TOTAL_REQUESTS.get("gemini", 0))
            col3.metric("Tavily", config.TOTAL_REQUESTS.get("tavily", 0))
        
        st.divider()
        st.caption("Built by Yousef Reda")
        st.caption("Total cost: \$0.00")
    
    # Parse known funders into list
    funder_list = [f.strip() for f in known_funders.strip().split("\n") if f.strip()]
    
    return mode, org_name, funder_list


# ============================================================
# MAIN INTERFACE
# ============================================================

def render_main(mode, org_name, known_funders):
    """Render the main content area"""
    
    # ---- Header ----
    st.title("🔍 Funder Intelligence & Outreach Agent")
    st.markdown(
        "Enter a funder name below. The agent will research them, "
        "map alignment to your org, find connection paths, and draft outreach emails."
    )
    
    # ---- Input Section ----
    col1, col2 = st.columns([2, 1])
    
    with col1:
        funder_name = st.text_input(
            "🏛️ Funder Name",
            placeholder="e.g., Ford Foundation, Kresge Foundation...",
        )
    
    with col2:
        website_url = st.text_input(
            "🌐 Website URL (optional)",
            placeholder="https://www.fordfoundation.org",
        )
    
    if not website_url:
        website_url = None
    
    # ---- Run Button ----
    run_button = st.button(
        "🚀 Run Agent" if "Full" in mode else f"Run {mode.split(' ', 1)[1]}",
        type="primary",
        use_container_width=True,
        disabled=not funder_name,
    )
    
    if not funder_name:
        st.info("👆 Enter a funder name above to get started.")
        render_previous_results()
        return
    
    if run_button:
        run_pipeline(funder_name, website_url, mode, org_name, known_funders)
    else:
        # Show existing results if available
        render_existing_results(funder_name)


# ============================================================
# PIPELINE EXECUTION
# ============================================================

def run_pipeline(funder_name, website_url, mode, org_name, known_funders):
    """Execute the selected pipeline mode with progress tracking"""
    
    agents = load_agents()
    if not agents:
        st.error("Failed to load agents. Check your configuration.")
        return
    
    # Initialize results storage in session state
    if "results" not in st.session_state:
        st.session_state.results = {}
    
    safe_name = get_safe_name(funder_name)
    
    start_time = time.time()
    
    # ---- Determine which stages to run ----
    run_research = "Full" in mode or "Research" in mode
    run_alignment = "Full" in mode or "Alignment" in mode
    run_connections = "Full" in mode or "Connections" in mode
    run_outreach = "Full" in mode or "Outreach" in mode
    
    # For alignment/connections/outreach only, we need existing research
    if not run_research and (run_alignment or run_connections or run_outreach):
        profile_path = f"data/output/{safe_name}_profile.md"
        if not os.path.exists(profile_path):
            st.error(f"No existing research found for '{funder_name}'. Run Full Pipeline first.")
            return
    
    # ---- Progress tracking ----
    total_stages = sum([run_research, run_alignment, run_connections, run_outreach])
    current_stage = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = {}
    
    # ════════════════════════════════════════
    # STAGE 1: RESEARCH
    # ════════════════════════════════════════
    if run_research:
        current_stage += 1
        status_text.markdown(f"**Stage {current_stage}/{total_stages}: 🔍 Researching {funder_name}...**")
        progress_bar.progress(current_stage / (total_stages + 1))
        
        try:
            with st.spinner(f"Researching {funder_name}... (web search, 990 data, website scraping)"):
                research_result = agents["research"](funder_name, website_url)
                results["research"] = research_result
        except Exception as e:
            st.error(f"Research failed: {e}")
            return
    else:
        # Load existing research
        profile_path = f"data/output/{safe_name}_profile.md"
        if os.path.exists(profile_path):
            with open(profile_path) as f:
                profile_content = f.read()
            results["research"] = {"profile": profile_content}
    
    # ════════════════════════════════════════
    # STAGE 2: ALIGNMENT
    # ════════════════════════════════════════
    if run_alignment and results.get("research"):
        current_stage += 1
        status_text.markdown(f"**Stage {current_stage}/{total_stages}: 🎯 Mapping alignment...**")
        progress_bar.progress(current_stage / (total_stages + 1))
        
        try:
            with st.spinner("Analyzing alignment — mapping your work to their language..."):
                alignment_result = agents["alignment"](
                    funder_name=funder_name,
                    funder_profile=results["research"]["profile"],
                )
                results["alignment"] = alignment_result
        except Exception as e:
            st.error(f"Alignment mapping failed: {e}")
    
    # ════════════════════════════════════════
    # STAGE 3: CONNECTIONS
    # ════════════════════════════════════════
    if run_connections:
        current_stage += 1
        status_text.markdown(f"**Stage {current_stage}/{total_stages}: 🔗 Finding connection paths...**")
        progress_bar.progress(current_stage / (total_stages + 1))
        
        try:
            with st.spinner("Searching for warm introduction paths..."):
                connection_result = agents["connections"](
                    target_name=funder_name,
                    our_org_name=org_name,
                    our_known_funders=known_funders,
                )
                results["connections"] = connection_result
        except Exception as e:
            st.error(f"Connection research failed: {e}")
    
    # ════════════════════════════════════════
    # STAGE 4: OUTREACH DRAFTS
    # ════════════════════════════════════════
    if run_outreach and results.get("research"):
        current_stage += 1
        status_text.markdown(f"**Stage {current_stage}/{total_stages}: ✉️ Drafting outreach emails...**")
        progress_bar.progress(current_stage / (total_stages + 1))
        
        try:
            with st.spinner("Generating calibrated outreach drafts..."):
                outreach_result = agents["drafts"](
                    funder_name=funder_name,
                    funder_profile=results["research"]["profile"],
                    alignment_brief=results.get("alignment", {}).get("alignment_brief", ""),
                    connection_paths=results.get("connections", {}).get("connection_analysis", ""),
                )
                results["outreach"] = outreach_result
        except Exception as e:
            st.error(f"Outreach drafting failed: {e}")
    
    # ════════════════════════════════════════
    # COMPLETE
    # ════════════════════════════════════════
    elapsed = time.time() - start_time
    progress_bar.progress(1.0)
    status_text.markdown(f"**✅ Complete! Time: {elapsed:.1f}s | Cost: \$0.00**")
    
    # Store in session state
    st.session_state.results[funder_name] = results
    
    # Display results
    render_results(funder_name, results, elapsed)


# ============================================================
# RESULTS DISPLAY
# ============================================================

def render_results(funder_name, results, elapsed=None):
    """Display results in organized tabs"""
    
    st.divider()
    
    if elapsed:
        col1, col2, col3 = st.columns(3)
        col1.metric("⏱️ Time", f"{elapsed:.1f}s")
        col2.metric("💰 Cost", "\$0.00")
        col3.metric("📄 Stages", len(results))
    
    # ---- Tabs for each result type ----
    tab_names = []
    tab_data = []
    
    if "research" in results and "profile" in results["research"]:
        tab_names.append("📋 Profile")
        tab_data.append(("research", results["research"]["profile"]))
    
    if "alignment" in results and "alignment_brief" in results["alignment"]:
        tab_names.append("🎯 Alignment")
        tab_data.append(("alignment", results["alignment"]["alignment_brief"]))
    
    if "connections" in results and "connection_analysis" in results["connections"]:
        tab_names.append("🔗 Connections")
        tab_data.append(("connections", results["connections"]["connection_analysis"]))
    
    if "outreach" in results and "drafts" in results["outreach"]:
        tab_names.append("✉️ Outreach")
        tab_data.append(("outreach", results["outreach"]["drafts"]))
    
    if not tab_names:
        st.warning("No results to display.")
        return
    
    tabs = st.tabs(tab_names)
    
    for i, tab in enumerate(tabs):
        with tab:
            result_type, content = tab_data[i]
            
            # Display the content
            st.markdown(content)
            
            st.divider()
            
            # Download button for each tab
            safe_name = funder_name.lower().replace(" ", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            
            st.download_button(
                label=f"📥 Download {tab_names[i].split(' ', 1)[1]}",
                data=content,
                file_name=f"{safe_name}_{result_type}.md",
                mime="text/markdown",
            )
    
    # ---- Download All button ----
    st.divider()
    
    all_content = f"# Funder Intelligence Report: {funder_name}\n"
    all_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    for result_type, content in tab_data:
        all_content += f"\n\n{'=' * 60}\n"
        all_content += f"## {result_type.upper()}\n"
        all_content += f"{'=' * 60}\n\n"
        all_content += content
    
    safe_name = funder_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    st.download_button(
        label="📥 Download Complete Report",
        data=all_content,
        file_name=f"{safe_name}_complete_report.md",
        mime="text/markdown",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# EXISTING / PREVIOUS RESULTS
# ============================================================

def render_existing_results(funder_name):
    """Load and display existing results from files"""
    
    safe_name = funder_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    output_dir = get_output_dir()
    
    files_to_check = {
        "research": f"{safe_name}_profile.md",
        "alignment": f"{safe_name}_alignment.md",
        "connections": f"{safe_name}_connections.md",
        "outreach": f"{safe_name}_outreach_drafts.md",
    }
    
    found_files = {}
    for result_type, filename in files_to_check.items():
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            with open(filepath) as f:
                found_files[result_type] = f.read()
    
    if found_files:
        st.info(f"📂 Found existing results for **{funder_name}**. Click 'Run Agent' to regenerate, or browse below.")
        
        results = {}
        for result_type, content in found_files.items():
            if result_type == "research":
                results["research"] = {"profile": content}
            elif result_type == "alignment":
                results["alignment"] = {"alignment_brief": content}
            elif result_type == "connections":
                results["connections"] = {"connection_analysis": content}
            elif result_type == "outreach":
                results["outreach"] = {"drafts": content}
        
        render_results(funder_name, results)


def render_previous_results():
    """Show a list of previously researched funders"""
    
    output_dir = get_output_dir()
    if not os.path.exists(output_dir):
        return
    
    # Find all profile files (indicates a completed research)
    profiles = [f for f in os.listdir(output_dir) if f.endswith("_profile.md")]
    
    if not profiles:
        return
    
    st.divider()
    st.subheader("📂 Previously Researched Funders")
    
    for profile_file in sorted(profiles):
        # Extract funder name from filename
        name = profile_file.replace("_profile.md", "").replace("_", " ").title()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{name}**")
        with col2:
            # Count how many output files exist for this funder
            prefix = profile_file.replace("_profile.md", "")
            related_files = [f for f in os.listdir(output_dir) if f.startswith(prefix)]
            st.caption(f"{len(related_files)} files")


# ============================================================
# CUSTOM CSS
# ============================================================

def apply_custom_css():
    """Dark theme with accent colors — easy on the eyes"""
    
    st.markdown("""
    <style>
        /* ═══════════════════════════════════
           GLOBAL STYLES
           ═══════════════════════════════════ */
        
        /* Main background */
        .stApp {
            background: linear-gradient(180deg, #0E1117 0%, #131720 100%);
        }
        
        /* All text */
        .stMarkdown, .stText, p, span, label {
            color: #C8D6E5 !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #E8EEF4 !important;
        }
        
        /* ═══════════════════════════════════
           SIDEBAR
           ═══════════════════════════════════ */
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #141B2D 0%, #0E1117 100%);
            border-right: 1px solid #1E2A3A;
        }
        
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] label {
            color: #A0B0C0 !important;
        }
        
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #4FC3F7 !important;
        }
        
        /* ═══════════════════════════════════
           CARDS & CONTAINERS
           ═══════════════════════════════════ */
        
        /* Custom card styling */
        .metric-card {
            background: linear-gradient(135deg, #1A1F2E 0%, #1E2638 100%);
            border: 1px solid #2A3448;
            border-radius: 12px;
            padding: 20px;
            margin: 8px 0;
            transition: transform 0.2s, border-color 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #4FC3F7;
        }
        
        .metric-card h3 {
            color: #4FC3F7 !important;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-card .value {
            color: #FFFFFF !important;
            font-size: 1.8rem;
            font-weight: 700;
        }
        
        .metric-card .subtitle {
            color: #6B7B8D !important;
            font-size: 0.8rem;
        }
        
        /* Status cards */
        .status-card {
            background: linear-gradient(135deg, #1A2332 0%, #1E2840 100%);
            border: 1px solid #2A3A4E;
            border-radius: 12px;
            padding: 16px 20px;
            margin: 6px 0;
        }
        
        .status-success {
            border-left: 4px solid #66BB6A;
        }
        
        .status-warning {
            border-left: 4px solid #FFA726;
        }
        
        .status-info {
            border-left: 4px solid #4FC3F7;
        }
        
        .status-error {
            border-left: 4px solid #EF5350;
        }
        
        /* ═══════════════════════════════════
           TABS
           ═══════════════════════════════════ */
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #141B2D;
            border-radius: 12px;
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 12px 24px;
            border-radius: 8px;
            color: #8899AA !important;
            background-color: transparent;
            font-weight: 500;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: #FFFFFF !important;
            background-color: #1E2A3A;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #1E3A5F !important;
            color: #4FC3F7 !important;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            background-color: #141B2D;
            border-radius: 0 0 12px 12px;
            padding: 20px;
            border: 1px solid #1E2A3A;
            border-top: none;
        }
        
        /* ═══════════════════════════════════
           BUTTONS
           ═══════════════════════════════════ */
        
        .stButton > button {
            background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
            color: white !important;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 600;
            letter-spacing: 0.5px;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #42A5F5 0%, #1E88E5 100%);
            box-shadow: 0 4px 15px rgba(30, 136, 229, 0.4);
            transform: translateY(-1px);
        }
        
        .stDownloadButton > button {
            background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%);
            color: white !important;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 500;
        }
        
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #43A047 0%, #2E7D32 100%);
            box-shadow: 0 4px 15px rgba(46, 125, 50, 0.4);
        }
        
        /* ═══════════════════════════════════
           INPUTS
           ═══════════════════════════════════ */
        
        .stTextInput > div > div > input {
            background-color: #1A1F2E;
            border: 1px solid #2A3448;
            border-radius: 10px;
            color: #E0E0E0;
            padding: 12px 16px;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #4FC3F7;
            box-shadow: 0 0 0 2px rgba(79, 195, 247, 0.2);
        }
        
        .stTextArea > div > div > textarea {
            background-color: #1A1F2E;
            border: 1px solid #2A3448;
            border-radius: 10px;
            color: #E0E0E0;
        }
        
        /* ═══════════════════════════════════
           PROGRESS BAR
           ═══════════════════════════════════ */
        
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #1E88E5, #4FC3F7, #81D4FA);
            border-radius: 10px;
        }
        
        .stProgress > div > div {
            background-color: #1A1F2E;
            border-radius: 10px;
        }
        
        /* ═══════════════════════════════════
           METRICS
           ═══════════════════════════════════ */
        
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #4FC3F7 !important;
            font-weight: 700;
        }
        
        [data-testid="stMetricLabel"] {
            color: #8899AA !important;
        }
        
        /* ═══════════════════════════════════
           ALERTS & INFO BOXES
           ═══════════════════════════════════ */
        
        .stAlert {
            background-color: #1A2332;
            border-radius: 10px;
            border: 1px solid #2A3A4E;
        }
        
        /* ═══════════════════════════════════
           DIVIDERS
           ═══════════════════════════════════ */
        
        hr {
            border-color: #1E2A3A !important;
        }
        
        /* ═══════════════════════════════════
           EXPANDERS
           ═══════════════════════════════════ */
        
        .streamlit-expanderHeader {
            background-color: #1A1F2E;
            border-radius: 10px;
            color: #C8D6E5 !important;
        }
        
        /* ═══════════════════════════════════
           RADIO BUTTONS
           ═══════════════════════════════════ */
        
        .stRadio > div {
            background-color: #141B2D;
            border-radius: 10px;
            padding: 8px;
        }
        
        /* ═══════════════════════════════════
           SCROLLBAR
           ═══════════════════════════════════ */
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #0E1117;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #2A3448;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #3A4A5E;
        }
        
        /* ═══════════════════════════════════
           HIDE STREAMLIT BRANDING
           ═══════════════════════════════════ */
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN APP
# ============================================================

def main():
    """Main app entry point"""
    
    # Apply styling
    apply_custom_css()
    
    # Render sidebar and get settings
    mode, org_name, known_funders = render_sidebar()
    
    # Render main content
    render_main(mode, org_name, known_funders)


if __name__ == "__main__":
    main()
