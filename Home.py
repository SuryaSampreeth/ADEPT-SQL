import json
import streamlit as st
from streamlit import session_state as ss
from ui_theme import inject_global_css, page_hero, section_label, feature_card_html, pipeline_flow_html

st.set_page_config(
    page_title="ADEPT-SQL",
    page_icon="🧠",
    layout="wide",
)
inject_global_css()
st.logo("logobar.png", icon_image="logonew.png", size="large")

# ── Sidebar Tech Specs & System Details ───────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="background: rgba(30,41,59,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px; margin-top: 0.5rem; margin-bottom: 12px;">
        <div style="font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #818cf8; margin-bottom: 8px;">
            About This App
        </div>
        <div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.55;">
            ADEPT-SQL lets you talk to your database in plain English.
            <br><br>
            Instead of writing complex SQL queries by hand, you can ask questions like:
            <br>
            <span style="color: #a5b4fc; font-style: italic;">"How many stores are there?"</span> or <span style="color: #a5b4fc; font-style: italic;">"List all customer names"</span>.
            <br><br>
            The system understands your question, translates it into the correct database query, and shows you the live results.
        </div>
    </div>

    <div style="background: rgba(30,41,59,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px;">
        <div style="font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #34d399; margin-bottom: 8px;">
            How It Works
        </div>
        <div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.6;">
            1. <b>Ask</b> — Type your question in everyday words.<br>
            2. <b>Translate</b> — The AI converts it into a SQL query.<br>
            3. <b>Fetch</b> — The query runs against the database.<br>
            4. <b>Result</b> — View the answers, tables, and charts.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Hero Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="adept-hero" style="text-align: center; padding: 2.6rem 2rem 2.2rem 2rem;">
    <h1 style="font-size: 2.9rem; font-weight: 900; margin: 0 0 0.5rem 0; letter-spacing: -0.02em;
               background: linear-gradient(135deg, #ffffff 20%, #818cf8 100%);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        ADEPT-SQL
    </h1>
    <div style="font-size: 1.25rem; color: #94a3b8; font-weight: 500; letter-spacing: 0.02em;">
        English to SQL Conversion
    </div>
</div>
""", unsafe_allow_html=True)


# ── Pipeline Architecture ─────────────────────────────────────────────────────
section_label("🏗️ 7-Stage Adaptive Pipeline Architecture")
st.markdown(pipeline_flow_html(), unsafe_allow_html=True)

with st.expander("📖 Pipeline Stage Details", expanded=False):
    stages_desc = [
        ("🔤 Stage 1 — SIM (Semantic Input Masking)", "Normalizes user input: date masking, entity extraction, and **fuzzy n-gram entity alignment** (Idea 1) to correct typos in customer/store names before SQL generation."),
        ("🧠 Stage 2 — CSR (Case-based Semantic Retrieval)", "Embeds the masked question using sentence-transformers and retrieves the top-K similar Question-SQL pairs from the in-memory vector index using cosine similarity."),
        ("⚡ Stage 3 — APC (Adaptive Prompt Constructor)", "Branches on CSR similarity score: high confidence → few-shot prompt (inject exemplar Q-SQL pairs); low confidence → zero-shot with schema-only context."),
        ("🤖 Stage 4 — Neural SQL Generation (LLM)", "Calls the configured LLM (OpenRouter / Ollama) with the constructed prompt. Supports concurrent Model A + B in dual-comparison mode."),
        ("🗄️ Stage 5 — SQL Execution", "Executes generated SQL against SQLite via SQLAlchemy. Returns result DataFrame or captures error for the verification stage."),
        ("💬 Stage 6 — Natural Language Answer", "Synthesizes a plain-English answer from the SQL result using a second LLM call."),
        ("✅ Stage 7 — Dual-Direction Verification & Visualization", "**Idea 3**: LLM verifies SQL faithfulness in both directions (NL→SQL + SQL→NL). **Idea 5**: Schema-linking ER graph. **Idea 6**: Auto-visualization agent."),
    ]
    for title, desc in stages_desc:
        st.markdown(f"**{title}**")
        st.caption(desc)
        st.divider()


st.markdown("<br>", unsafe_allow_html=True)


# ── NLP Innovation Showcase ────────────────────────────────────────────────────
section_label("🌟 6 NLP Innovations Implemented")

cards = [
    ("🔤", "Idea 1 — Fuzzy Entity Alignment",
     "Sliding-window n-gram fuzzy matching in the SIM module corrects entity typos (customer names, store names) before SQL generation — bypassing the LLM's zero-shot guessing.",
     "Did Blak book Adan Dinnig?"),
    ("💬", "Idea 2 — Multi-Turn Context Rewriter",
     "An LLM-based context rewriter resolves pronouns and ellipsis in follow-up questions ('How many are there?') into self-contained queries using the last 2 conversation turns.",
     "How many are there in total?"),
    ("🔬", "Idea 3 — Dual-Direction Semantic Verification",
     "After SQL generation, the system bidirectionally verifies: NL→SQL faithfulness AND SQL→NL semantic alignment, producing a step-by-step execution plan and constraint checklist.",
     "List all performers and their emails"),
    ("🎯", "Idea 4 — Ambiguity Detection & Clarification",
     "Detects structurally underspecified queries (missing rank criterion, aggregate metric, temporal reference) and interactively presents candidate interpretations via radio selection.",
     "Show me the top bookings"),
    ("🗺️", "Idea 5 — Schema-Linking Visualizer",
     "Parses the generated SQL with sqlglot to extract tables/columns/joins, then renders an interactive ER graph where used nodes glow green and active FK join edges are highlighted.",
     "How many bookings per customer?"),
    ("📊", "Idea 6 — Auto-Visualization Agent",
     "Inspects the result DataFrame for column types, shape and cardinality; auto-selects the optimal chart: Metric card (scalar), Bar chart (cat+num), Line chart (temporal), or graceful table fallback.",
     "How many bookings per customer?"),
]

row1 = st.columns(3)
row2 = st.columns(3)
for i, (icon, title, desc, query) in enumerate(cards):
    col = (row1 + row2)[i]
    with col:
        st.markdown(feature_card_html(icon, title, desc, query), unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)


# ── Quick Start Guide ─────────────────────────────────────────────────────────
section_label("🚀 Quick Start — Faculty Demo Guide")

c_a, c_b = st.columns([1, 1])
with c_a:
    st.markdown("""
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.4rem 1.6rem;">
        <div style="font-weight:700;font-size:0.95rem;color:#f1f5f9;margin-bottom:0.9rem;">
            ⚙️ Step 1 — Configure in Settings
        </div>
        <div style="font-size:0.84rem;color:#94a3b8;line-height:1.7;">
            <b>1.</b> Go to <b>Settings</b> → LLM tab → type <code>demo</code> in the API key field → Connect<br>
            <b>2.</b> Go to <b>DataSource</b> tab → select <b>Tutorial DB</b> → Connect<br>
            <b>3.</b> Return here once the status lights turn green
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_b:
    st.markdown("""
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.4rem 1.6rem;">
        <div style="font-weight:700;font-size:0.95rem;color:#f1f5f9;margin-bottom:0.9rem;">
            💬 Step 2 — Demo Query Sequence
        </div>
        <div style="font-size:0.84rem;color:#94a3b8;line-height:1.7;">
            <b>Idea 1:</b> <code>Did Blak book Adan Dinnig?</code><br>
            <b>Idea 2:</b> <code>List all stores.</code> → then <code>How many are there?</code><br>
            <b>Idea 3:</b> <code>List all performers and their emails</code><br>
            <b>Idea 4:</b> <code>Show me the top bookings</code><br>
            <b>Idea 5 &amp; 6:</b> <code>How many bookings per customer?</code>
        </div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:1rem;font-size:0.78rem;color:#475569;text-align:center;">
    ADEPT-SQL &nbsp;|&nbsp; English to SQL Conversion &nbsp;|&nbsp;
    <a href="https://github.com/lilichennn/ADEPT-SQL-DEMO" style="color:#6366f1;text-decoration:none;">GitHub Repository</a>
</div>
""", unsafe_allow_html=True)
