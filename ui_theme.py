"""
ui_theme.py — Shared CSS Design System for ADEPT-SQL Capstone UI
=================================================================
Call inject_global_css() at the top of every page to apply the full
design system: dark theme, card components, badge chips, typography,
pipeline flow chips, and animated metric tiles.

Usage:
    from ui_theme import inject_global_css, page_header, stat_card, badge
    inject_global_css()
"""

import streamlit as st


# ── Master CSS String ────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Google Fonts ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root variables ──────────────────────────────────────────────── */
:root {
    --bg-base:        #0f172a;
    --bg-card:        #1e293b;
    --bg-card-hover:  #263348;
    --accent:         #6366f1;
    --accent-glow:    rgba(99,102,241,0.18);
    --accent-emerald: #10b981;
    --accent-amber:   #f59e0b;
    --accent-rose:    #f43f5e;
    --accent-cyan:    #06b6d4;
    --text-primary:   #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted:     #64748b;
    --border:         rgba(255,255,255,0.07);
    --border-accent:  rgba(99,102,241,0.40);
    --radius-sm:      8px;
    --radius-md:      12px;
    --radius-lg:      18px;
    --shadow:         0 4px 24px rgba(0,0,0,0.35);
    --shadow-glow:    0 0 24px rgba(99,102,241,0.22);
}

/* ── Base typography ─────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
code, pre, .stCode {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 4px; }

/* ── Main container padding ──────────────────────────────────────── */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* ── Sidebar polish ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1a2540 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: var(--text-secondary) !important;
    font-size: 0.85rem;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
    padding: 4px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    padding: 8px 20px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(99,102,241,0.4) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid var(--border) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #818cf8) !important;
    border: none !important;
    box-shadow: 0 2px 12px rgba(99,102,241,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 20px rgba(99,102,241,0.55) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    transform: translateY(-1px) !important;
}

/* ── Input fields ────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

/* ── Expanders ───────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    color: var(--text-primary) !important;
    transition: background 0.2s;
}
.streamlit-expanderHeader:hover {
    background: var(--bg-card-hover) !important;
    border-color: var(--border-accent) !important;
}
.streamlit-expanderContent {
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
    background: rgba(30,41,59,0.6) !important;
}

/* ── Dataframe / Table ───────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    overflow: hidden;
}

/* ── Chat messages ───────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border) !important;
    margin-bottom: 12px !important;
}

/* ── Info / Warning / Error / Success ────────────────────────────── */
.stAlert {
    border-radius: var(--radius-sm) !important;
    border-left-width: 4px !important;
}

/* ── Metric ──────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s, transform 0.2s;
}
[data-testid="stMetric"]:hover {
    border-color: var(--border-accent) !important;
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

/* ── Code blocks ─────────────────────────────────────────────────── */
.stCode, pre {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
}

/* ── Selectbox / Multiselect ─────────────────────────────────────── */
.stSelectbox > div, .stMultiSelect > div {
    background: var(--bg-card) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Custom component classes ────────────────────────────────────── */

/* Hero header */
.adept-hero {
    background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(16,185,129,0.06) 100%);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-lg);
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.adept-hero::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -10%;
    width: 350px;
    height: 350px;
    background: radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%);
    pointer-events: none;
}
.adept-hero h1 {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #f1f5f9 30%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}
.adept-hero .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    font-weight: 400;
    margin-bottom: 1.2rem;
}

/* Pill tag */
.pill-tag {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    color: #a5b4fc;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 12px;
    border-radius: 999px;
    margin: 2px 4px 2px 0;
    letter-spacing: 0.04em;
}
.pill-tag-green {
    background: rgba(16,185,129,0.12);
    border-color: rgba(16,185,129,0.30);
    color: #6ee7b7;
}
.pill-tag-amber {
    background: rgba(245,158,11,0.12);
    border-color: rgba(245,158,11,0.30);
    color: #fcd34d;
}

/* Status dot */
.status-dot-green::before {
    content: '●';
    color: #10b981;
    margin-right: 6px;
    animation: pulse-green 2s infinite;
}
.status-dot-grey::before {
    content: '●';
    color: #64748b;
    margin-right: 6px;
}
@keyframes pulse-green {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Feature card */
.feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.4rem 1.5rem;
    height: 100%;
    transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
    position: relative;
    overflow: hidden;
}
.feature-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-3px);
    box-shadow: var(--shadow-glow);
}
.feature-card .feature-icon {
    font-size: 2rem;
    margin-bottom: 0.7rem;
    display: block;
}
.feature-card h4 {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.4rem;
}
.feature-card p {
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.55;
}
.feature-card .query-chip {
    display: inline-block;
    background: rgba(99,102,241,0.10);
    border: 1px dashed rgba(99,102,241,0.30);
    color: #a5b4fc;
    font-size: 0.72rem;
    padding: 2px 9px;
    border-radius: 6px;
    margin-top: 0.6rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Pipeline stage chip */
.pipeline-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(30,41,59,0.9);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-secondary);
    white-space: nowrap;
}
.pipeline-arrow {
    color: var(--text-muted);
    font-size: 1.1rem;
    padding: 0 2px;
}

/* Status bar card */
.status-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: border-color 0.2s;
}
.status-card.active { border-left: 3px solid var(--accent-emerald); }
.status-card.inactive { border-left: 3px solid var(--text-muted); }
.status-card.demo { border-left: 3px solid var(--accent-amber); }

/* Demo prompt chip */
.prompt-chip {
    display: inline-block;
    background: rgba(30,41,59,0.9);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 0.80rem;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}
.prompt-chip:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-glow);
}

/* Section divider with label */
.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* Innovation badge */
.idea-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.30);
    color: #a5b4fc;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 999px;
    letter-spacing: 0.04em;
}

/* Page section header */
.page-section-header {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 1.5rem 0 0.6rem 0;
    border-top: 1px solid var(--border);
    margin-top: 1.5rem;
}

/* Step list items */
.step-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 8px 0;
}
.step-number {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
</style>
"""


def inject_global_css():
    """Inject the full ADEPT-SQL design system CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_hero(title: str, subtitle: str, tags: list[str] = None):
    """Render an executive-style page hero header with title, subtitle, and pill tags."""
    tags_html = ""
    if tags:
        for tag in tags:
            tags_html += f'<span class="pill-tag">{tag}</span>'
    st.markdown(f"""
        <div class="adept-hero">
            <h1>{title}</h1>
            <div class="subtitle">{subtitle}</div>
            <div>{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)


def section_label(text: str):
    """Render a styled uppercase section label with a divider line."""
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def feature_card_html(icon: str, title: str, desc: str, query: str = None) -> str:
    """Return HTML for a single feature card."""
    chip = f'<span class="query-chip">Try: {query}</span>' if query else ""
    return f"""
        <div class="feature-card">
            <span class="feature-icon">{icon}</span>
            <h4>{title}</h4>
            <p>{desc}</p>
            {chip}
        </div>
    """


def idea_badge(number: int, label: str) -> str:
    """Return HTML for an Idea badge chip."""
    return f'<span class="idea-badge">💡 Idea {number}: {label}</span>'


def pipeline_flow_html() -> str:
    """Return HTML for the 7-stage pipeline flow diagram."""
    stages = [
        ("🔤", "User Input"),
        ("🔍", "SIM (Fuzzy)"),
        ("🧠", "CSR (Retrieval)"),
        ("⚡", "APC (Few-Shot)"),
        ("🤖", "LLM → SQL"),
        ("🗄️", "Execute"),
        ("✅", "Verify & Viz"),
    ]
    chips = ""
    for i, (icon, name) in enumerate(stages):
        chips += f'<span class="pipeline-chip">{icon} {name}</span>'
        if i < len(stages) - 1:
            chips += '<span class="pipeline-arrow">→</span>'
    return f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:1rem 0;">{chips}</div>'
