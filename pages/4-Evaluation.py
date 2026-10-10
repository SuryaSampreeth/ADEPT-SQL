"""
4-Evaluation.py — Batch Execution Match Evaluation Studio for ADEPT-SQL
========================================================================
Benchmarks the ADEPT-SQL pipeline against the 19 representative benchmark
Question-SQL pairs from seed_qvec.py, comparing Model A and Model B using
Execution Match (identical result dataframes = match).

Preserves all evaluation logic while providing an enterprise academic
capstone UI with KPI cards, comparative accuracy charts, and expandable diffs.
"""

import os, sys
pythonon_path = os.path.dirname('../')
sys.path.append(pythonon_path)

import json
import pandas as pd
import streamlit as st
from streamlit import session_state as ss

from run import adept
from eval_utils import compare_dataframes, execution_match_label, run_sql_safe
from ui_theme import inject_global_css, page_hero, section_label

# ── Benchmark dataset (from seed_qvec.py) ─────────────────────────────────────
BENCHMARK = [
    {
        "question": "Did Blake book Adan Dinning?",
        "gold_sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE C.Customer_Name = 'Blake' AND S.Store_Name = 'Adan Dinning'"""
    },
    {
        "question": "Did Ephraim book Lur Photo?",
        "gold_sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE C.Customer_Name = 'Ephraim' AND S.Store_Name = 'Lur Photo'"""
    },
    {
        "question": "How many bookings are there in total?",
        "gold_sql": "SELECT COUNT(*) AS total_bookings FROM Bookings"
    },
    {
        "question": "How many customers are there?",
        "gold_sql": "SELECT COUNT(*) AS total_customers FROM Customers"
    },
    {
        "question": "How many stores are there?",
        "gold_sql": "SELECT COUNT(*) AS total_stores FROM Stores"
    },
    {
        "question": "List all store names.",
        "gold_sql": "SELECT Store_Name FROM Stores ORDER BY Store_Name"
    },
    {
        "question": "List all customer names.",
        "gold_sql": "SELECT Customer_Name FROM Customers ORDER BY Customer_Name"
    },
    {
        "question": "Show all bookings with their status.",
        "gold_sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code, B.Order_Date
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
ORDER BY B.Order_Date DESC"""
    },
    {
        "question": "How many bookings does each customer have?",
        "gold_sql": """SELECT C.Customer_Name, COUNT(B.Booking_ID) AS booking_count
FROM Customers C
LEFT JOIN Bookings B ON C.Customer_ID = B.Customer_ID
GROUP BY C.Customer_Name
ORDER BY booking_count DESC"""
    },
    {
        "question": "Which customer has the most bookings?",
        "gold_sql": """SELECT C.Customer_Name, COUNT(B.Booking_ID) AS booking_count
FROM Customers C
INNER JOIN Bookings B ON C.Customer_ID = B.Customer_ID
GROUP BY C.Customer_Name
ORDER BY booking_count DESC
LIMIT 1"""
    },
    {
        "question": "How many bookings does each store have?",
        "gold_sql": """SELECT S.Store_Name, COUNT(B.Booking_ID) AS booking_count
FROM Stores S
LEFT JOIN Bookings B ON S.Store_ID = B.Store_ID
GROUP BY S.Store_Name
ORDER BY booking_count DESC"""
    },
    {
        "question": "Which store has the most bookings?",
        "gold_sql": """SELECT S.Store_Name, COUNT(B.Booking_ID) AS booking_count
FROM Stores S
INNER JOIN Bookings B ON S.Store_ID = B.Store_ID
GROUP BY S.Store_Name
ORDER BY booking_count DESC
LIMIT 1"""
    },
    {
        "question": "How many services are offered?",
        "gold_sql": "SELECT COUNT(*) AS total_services FROM Services"
    },
    {
        "question": "List all services and their prices.",
        "gold_sql": "SELECT Product_Name, Product_Price FROM Services ORDER BY Product_Price DESC"
    },
    {
        "question": "How many performers are registered?",
        "gold_sql": "SELECT COUNT(*) AS total_performers FROM Performers"
    },
    {
        "question": "List all performers and their contact email addresses.",
        "gold_sql": "SELECT Customer_Name, Customer_Email_Address FROM Performers ORDER BY Customer_Name"
    },
    {
        "question": "How many bookings are confirmed?",
        "gold_sql": "SELECT COUNT(*) AS confirmed_bookings FROM Bookings WHERE Status_Code = 'Confirmed'"
    },
    {
        "question": "How many bookings are cancelled?",
        "gold_sql": "SELECT COUNT(*) AS cancelled_bookings FROM Bookings WHERE Status_Code = 'Cancelled'"
    },
    {
        "question": "Show all bookings made in 2023.",
        "gold_sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Order_Date
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE B.Order_Date LIKE '2023%'
ORDER BY B.Order_Date"""
    },
]


def readjson(file):
    try:
        with open("./backend/" + file, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


# ── PAGE SETUP ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADEPT-SQL | Evaluation Studio",
    page_icon="📊",
    layout="wide"
)
inject_global_css()
st.logo("logobar.png", icon_image='logonew.png', size='large')

# ── Load configs ──────────────────────────────────────────────────────────────
if 'llm' not in ss:
    ss.llm = readjson('llm.json')
if 'llm_b' not in ss:
    ss.llm_b = readjson('llm_b.json')
if 'emb' not in ss:
    ss.emb = readjson('emb.json')
if 'userdb' not in ss:
    ss.userdb = readjson('db.json')

model_a_active = ss.llm.get('active', False)
model_b_active = ss.llm_b.get('active', False)

# ── Page Hero Header ──────────────────────────────────────────────────────────
page_hero(
    title="Academic Benchmark Studio",
    subtitle="Rigorous empirical evaluation of ADEPT-SQL using Execution Match against Spider Cre-Drama gold standard queries.",
    tags=[
        f"Benchmark: Spider Cre_Drama ({len(BENCHMARK)} Queries)",
        "Metric: Execution Match (EM)",
        f"Model A: {ss.llm.get('name', 'Offline')}",
        f"Model B: {ss.llm_b.get('name', 'Disabled') if model_b_active else 'Single Model'}",
    ]
)

# ── Guard ─────────────────────────────────────────────────────────────────────
if not model_a_active:
    st.warning("⚠️ Model A (Primary LLM) not connected. Please go to **Settings** first.")
    st.stop()
if not ss.emb.get('active', False):
    st.warning("⚠️ Embedding model not connected. Please go to **Settings** first.")
    st.stop()
if not ss.userdb.get('conn', False):
    st.warning("⚠️ Database not connected. Please go to **Settings** first.")
    st.stop()

# ── Status Ribbon ─────────────────────────────────────────────────────────────
status_col1, status_col2 = st.columns(2)
with status_col1:
    st.markdown(f"""
    <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.25);border-radius:10px;padding:10px 16px;">
        <span style="font-weight:700;color:#818cf8;">🅰️ Primary Model:</span> 
        <span style="color:#f1f5f9;font-weight:600;">{ss.llm.get('name', 'Active')}</span>
        <span style="font-size:0.75rem;color:#10b981;margin-left:8px;">● Connected</span>
    </div>
    """, unsafe_allow_html=True)

with status_col2:
    if model_b_active:
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:10px 16px;">
            <span style="font-weight:700;color:#34d399;">🅱️ Comparison Model:</span> 
            <span style="color:#f1f5f9;font-weight:600;">{ss.llm_b.get('name', 'Active')}</span>
            <span style="font-size:0.75rem;color:#10b981;margin-left:8px;">● Dual-Eval Ready</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(100,116,139,0.08);border:1px solid rgba(100,116,139,0.20);border-radius:10px;padding:10px 16px;">
            <span style="font-weight:700;color:#94a3b8;">🅱️ Comparison Model:</span> 
            <span style="color:#64748b;">Not configured (Single-Model evaluation mode)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:1.2rem;'></div>", unsafe_allow_html=True)

# ── Benchmark preview ─────────────────────────────────────────────────────────
with st.expander(f"📋 Inspect Benchmark Dataset ({len(BENCHMARK)} Representative Queries)", expanded=False):
    preview_df = pd.DataFrame([{
        '#': i + 1,
        'Benchmark Question': b['question'],
        'Gold SQL Standard': b['gold_sql'].replace('\n', ' ')
    } for i, b in enumerate(BENCHMARK)])
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

# ── Persistent session results state ──────────────────────────────────────────
if 'eval_results' not in ss:
    ss.eval_results = None

# ── Run Evaluation Action ─────────────────────────────────────────────────────
btn_col1, btn_col2 = st.columns([3, 1])
with btn_col1:
    run_btn = st.button("▶️ Start Batch Benchmark Evaluation", type="primary", use_container_width=True)
with btn_col2:
    if ss.eval_results is not None:
        if st.button("🔄 Reset Results", use_container_width=True):
            ss.eval_results = None
            st.rerun()

if run_btn:
    total = len(BENCHMARK)
    results = []

    progress_bar = st.progress(0, text="Initializing benchmark run...")
    status_text  = st.empty()
    live_table   = st.empty()

    for i, bench in enumerate(BENCHMARK):
        q        = bench['question']
        gold_sql = bench['gold_sql']
        status_text.markdown(f"**⚡ Evaluating [{i+1}/{total}]:** *{q}*")

        # ── Gold SQL execution ────────────────────────────────────────────────
        gold_df, gold_err = run_sql_safe(gold_sql, ss.userdb)

        # ── Model A ───────────────────────────────────────────────────────────
        try:
            out_a = adept(q, ss.llm, ss.emb, ss.userdb)
            sql_a = out_a['sql']
            df_a  = out_a['table']
            err_a = out_a['error']
        except Exception as e:
            sql_a, df_a, err_a = '', pd.DataFrame(), str(e)

        match_a = compare_dataframes(df_a, gold_df)

        # ── Model B ───────────────────────────────────────────────────────────
        if model_b_active:
            try:
                out_b = adept(q, ss.llm_b, ss.emb, ss.userdb)
                sql_b = out_b['sql']
                df_b  = out_b['table']
                err_b = out_b['error']
            except Exception as e:
                sql_b, df_b, err_b = '', pd.DataFrame(), str(e)
            match_b  = compare_dataframes(df_b, gold_df)
            match_ab = compare_dataframes(df_a, df_b)
        else:
            sql_b, df_b, err_b = None, None, None
            match_b  = None
            match_ab = None

        results.append({
            'question': q,
            'gold_sql': gold_sql,
            'sql_a':    sql_a,
            'df_a':     df_a,
            'err_a':    err_a,
            'match_a':  match_a,
            'sql_b':    sql_b,
            'df_b':     df_b,
            'err_b':    err_b,
            'match_b':  match_b,
            'match_ab': match_ab,
        })

        # Live summary table update
        summary_rows = []
        for r in results:
            row = {
                '#': len(summary_rows) + 1,
                'Question': r['question'],
                'Model A': '✅ MATCH' if r['match_a'] else '❌ MISMATCH',
            }
            if model_b_active:
                row['Model B'] = '✅ MATCH' if r['match_b'] else '❌ MISMATCH'
                row['A vs B Agree'] = '✅ MATCH' if r['match_ab'] else '❌ MISMATCH'
            summary_rows.append(row)
        live_table.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        progress_bar.progress((i + 1) / total, text=f"Processed {i+1} of {total} queries")

    status_text.markdown("✅ **Evaluation completed successfully!**")
    progress_bar.empty()
    live_table.empty()
    ss.eval_results = results


# ── Render Evaluation Results (if available in state) ─────────────────────────
if ss.eval_results is not None:
    results = ss.eval_results
    n = len(results)
    acc_a = sum(1 for r in results if r['match_a']) / n * 100

    section_label("📊 Benchmark Performance Metrics")

    # Metric KPI Cards
    if model_b_active:
        acc_b = sum(1 for r in results if r['match_b']) / n * 100
        agree = sum(1 for r in results if r['match_ab']) / n * 100
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric(
                label="🅰️ Model A Accuracy",
                value=f"{acc_a:.1f}%",
                delta=f"{sum(1 for r in results if r['match_a'])}/{n} Passed"
            )
        with m_col2:
            st.metric(
                label="🅱️ Model B Accuracy",
                value=f"{acc_b:.1f}%",
                delta=f"{sum(1 for r in results if r['match_b'])}/{n} Passed"
            )
        with m_col3:
            st.metric(
                label="🔁 A vs B Agreement",
                value=f"{agree:.1f}%",
                delta=f"{sum(1 for r in results if r['match_ab'])}/{n} Matched"
            )
        with m_col4:
            st.metric(
                label="📚 Benchmark Size",
                value=f"{n} Queries",
                delta="Cre_Drama DB"
            )
    else:
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(
                label="🅰️ Model A Accuracy",
                value=f"{acc_a:.1f}%",
                delta=f"{sum(1 for r in results if r['match_a'])}/{n} Passed"
            )
        with m_col2:
            st.metric(
                label="🏆 Gold Standard",
                value="100.0%",
                delta="Spider Benchmark Ground Truth"
            )
        with m_col3:
            st.metric(
                label="📚 Queries Evaluated",
                value=f"{n}",
                delta="Zero-Shot & Few-Shot Mixed"
            )

    # ── Accuracy Comparison Chart ─────────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    section_label("📈 Comparative Accuracy Visualization")

    try:
        import plotly.express as px

        if model_b_active:
            chart_data = pd.DataFrame({
                "System": [f"Model A ({ss.llm.get('name','A')})", f"Model B ({ss.llm_b.get('name','B')})", "Agreement (A ∩ B)"],
                "Accuracy (%)": [round(acc_a, 1), round(acc_b, 1), round(agree, 1)],
                "Color": ["#6366f1", "#10b981", "#06b6d4"]
            })
        else:
            chart_data = pd.DataFrame({
                "System": [f"Model A ({ss.llm.get('name','A')})", "Gold Ground Truth"],
                "Accuracy (%)": [round(acc_a, 1), 100.0],
                "Color": ["#6366f1", "#10b981"]
            })

        fig = px.bar(
            chart_data,
            x="System",
            y="Accuracy (%)",
            text="Accuracy (%)",
            color="System",
            color_discrete_map={
                f"Model A ({ss.llm.get('name','A')})": "#6366f1",
                f"Model B ({ss.llm_b.get('name','B')})": "#10b981",
                "Agreement (A ∩ B)": "#06b6d4",
                "Gold Ground Truth": "#10b981"
            }
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(30,41,59,0.5)",
            plot_bgcolor="rgba(30,41,59,0.3)",
            height=320,
            showlegend=False,
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis=dict(range=[0, 110], title="Execution Match %"),
            xaxis=dict(title="")
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        # Fallback to standard Streamlit bar chart if Plotly has issues
        chart_df = pd.DataFrame({
            "Accuracy": {"Model A": acc_a, "Model B": acc_b if model_b_active else 100}
        })
        st.bar_chart(chart_df)

    # ── Detailed Results Section ──────────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    section_label("🔎 Query-by-Query Execution Diff & Verification")

    filter_option = st.radio(
        "Filter queries by verdict:",
        options=["All Queries", "Matches Only ✅", "Mismatches Only ❌"],
        horizontal=True
    )

    filtered_results = []
    for i, r in enumerate(results):
        if filter_option == "Matches Only ✅" and not r['match_a']:
            continue
        if filter_option == "Mismatches Only ❌" and r['match_a']:
            continue
        filtered_results.append((i, r))

    st.caption(f"Showing {len(filtered_results)} of {n} queries")

    for i, r in filtered_results:
        match_icon = "🟢" if r['match_a'] else "🔴"
        verdict_str = "MATCH" if r['match_a'] else "MISMATCH"
        expander_title = f"{match_icon} Q{i+1}: {r['question']} — {verdict_str}"

        with st.expander(expander_title, expanded=False):
            # Verdict Pills
            v_col1, v_col2, v_col3 = st.columns(3)
            with v_col1:
                if r['match_a']:
                    st.markdown("<span class='pill-tag pill-tag-green'>✅ Model A: MATCH</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='pill-tag' style='background:rgba(244,63,94,0.15);border-color:rgba(244,63,94,0.4);color:#fda4af;'>❌ Model A: MISMATCH</span>", unsafe_allow_html=True)
            with v_col2:
                if model_b_active:
                    if r['match_b']:
                        st.markdown("<span class='pill-tag pill-tag-green'>✅ Model B: MATCH</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='pill-tag' style='background:rgba(244,63,94,0.15);border-color:rgba(244,63,94,0.4);color:#fda4af;'>❌ Model B: MISMATCH</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='pill-tag'>Model B: Not Configured</span>", unsafe_allow_html=True)
            with v_col3:
                if model_b_active:
                    if r['match_ab']:
                        st.markdown("<span class='pill-tag pill-tag-green'>✅ A vs B: IDENTICAL</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='pill-tag pill-tag-amber'>⚠️ A vs B: DIVERGENT</span>", unsafe_allow_html=True)

            st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

            # SQL Diff Tabs
            sql_tabs = ["🏆 Gold Standard SQL", f"🅰️ Model A SQL ({ss.llm.get('name','Model A')})"]
            if model_b_active:
                sql_tabs.append(f"🅱️ Model B SQL ({ss.llm_b.get('name','Model B')})")
            
            tab_objs = st.tabs(sql_tabs)
            with tab_objs[0]:
                st.code(r['gold_sql'], language='sql')
            with tab_objs[1]:
                if r['sql_a']:
                    st.code(r['sql_a'], language='sql')
                else:
                    st.error(f"No SQL generated. Error: {r['err_a']}")
            if model_b_active and len(tab_objs) > 2:
                with tab_objs[2]:
                    if r['sql_b']:
                        st.code(r['sql_b'], language='sql')
                    else:
                        st.error(f"No SQL generated. Error: {r['err_b']}")

            # Result Dataframes
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#94a3b8;margin:0.8rem 0 0.4rem 0;'>Execution Output:</div>", unsafe_allow_html=True)
            res_cols = st.columns(3 if model_b_active else 2)
            with res_cols[0]:
                st.caption("🏆 Gold Standard Output")
                gold_df_local, _ = run_sql_safe(r['gold_sql'], ss.userdb)
                if gold_df_local is not None and not gold_df_local.empty:
                    st.dataframe(gold_df_local, use_container_width=True, hide_index=True)
                else:
                    st.info("No rows returned from Gold SQL.")

            with res_cols[1]:
                st.caption(f"🅰️ Model A Output")
                if r['err_a']:
                    st.error(r['err_a'])
                elif r['df_a'] is not None and not r['df_a'].empty:
                    st.dataframe(r['df_a'], use_container_width=True, hide_index=True)
                else:
                    st.info("No rows returned.")

            if model_b_active:
                with res_cols[2]:
                    st.caption(f"🅱️ Model B Output")
                    if r['err_b']:
                        st.error(r['err_b'])
                    elif r['df_b'] is not None and not r['df_b'].empty:
                        st.dataframe(r['df_b'], use_container_width=True, hide_index=True)
                    else:
                        st.info("No rows returned.")
