import os, sys
pythonon_path = os.path.dirname('../')
sys.path.append(pythonon_path)
import json
import pandas as pd
import streamlit as st
from streamlit import session_state as ss

from run import adept, check_ambiguity
from eval_utils import compare_dataframes, execution_match_label
from call_llm import callLLM
from prompt_templates import Prompt_QueryRewriter
from viz_utils import render_schema_linker, render_auto_visualization
from ui_theme import inject_global_css, section_label


# ── Idea 3: Dual-Direction SQL Explanation & Semantic Verification Renderer ────
def render_sql_explanation_verification(verification: dict):
    """
    Renders natural language logic steps and constraint verification card (Idea 3).
    Always triggers for every generated query, proving dual-direction NL <-> SQL capability.
    """
    if not verification:
        return

    verified = verification.get('verified', True)
    badge = "**[Verified Intent]**" if verified else "**[Semantic Warning]**"
    label = f"SQL Logic Breakdown & Semantic Verification (Idea 3) — {badge}"

    with st.expander(label, expanded=True):
        st.markdown(f"**Intent Alignment:** {verification.get('verdict_summary', 'Logic verified.')}")

        summary = verification.get('plain_english_summary')
        if summary:
            st.info(f"**Plain-English Query Logic:** {summary}")

        steps = verification.get('execution_logic_steps', [])
        if steps:
            st.markdown("**Step-by-Step Execution Plan:**")
            for idx, step in enumerate(steps, 1):
                st.markdown(f"{idx}. {step}")

        constraints = verification.get('constraints_checked', [])
        if constraints:
            st.markdown("**Constraint & Constraint Alignment Check:**")
            cols = st.columns(min(len(constraints), 3) if len(constraints) > 0 else 1)
            for i, c in enumerate(constraints):
                col = cols[i % len(cols)]
                status = c.get('status', 'Satisfied')
                with col:
                    st.caption(f"**{c.get('constraint', 'Constraint')}**: `{status}`")


# ── Backward Compatibility: Self-Correction Loop Renderer ─────────────────────
def render_correction_loop(correction_log: list):
    """
    Optional retry trace expander.
    """
    if not correction_log:
        return
    had_retry = any(e['status'] == 'failed' for e in correction_log)
    if not had_retry:
        return
    with st.expander("SQL Execution Trace", expanded=False):
        for entry in correction_log:
            attempt = entry.get('attempt', '?')
            status = entry.get('status', '')
            error = entry.get('error')
            fixed = entry.get('fixed_sql')
            st.markdown(f"##### Attempt {attempt}")
            if status == 'success':
                st.success(f"Attempt {attempt} — SQL executed successfully.")
            elif status == 'failed' and fixed:
                st.warning(f"Attempt {attempt} — Failed: {error}")
                st.code(fixed, language='sql')


def readjson(file):
    try:
        with open("./backend/" + file, 'r') as openfile:
            return json.load(openfile)
    except Exception:
        return {}


def rewrite_query_with_context(question: str, history: list, llm: dict) -> tuple:
    """
    (Idea 2) Attempt to rewrite a follow-up question into a self-contained one
    using recent conversation exchanges as context.
    """
    if not history:
        return question, None
    try:
        recent = []
        for h in history[-2:]:
            recent.append({"role": "user", "content": h.get('user', '')})
            if h.get('answer'):
                recent.append({"role": "assistant", "content": h.get('answer', '')})

        rewrite_prompt = Prompt_QueryRewriter(recent, question).compile()
        raw = callLLM(llm).init_prompt(
            'You are a query rewriter. Output ONLY the rewritten question, nothing else.',
            rewrite_prompt
        ).call().get_response_content().strip()

        if (raw
                and raw != 'LLM Fail'
                and len(raw) < 400
                and raw.lower().strip() != question.lower().strip()):
            return raw, raw
        return question, None
    except Exception:
        return question, None


# ── PAGE START ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADEPT-SQL | Chat",
    layout="wide",
)
inject_global_css()
st.logo("logobar.png", icon_image='logonew.png', size='large')


# ── Sidebar: status, toggles, and tech details ─────────────────────────────────
enable_ambiguity = True
with st.sidebar:
    st.markdown("""<div style='font-size:0.75rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#818cf8;padding:4px 0 6px 0;'>Live System Status</div>""", unsafe_allow_html=True)
    _llm_info = ss.get('llm') or readjson('llm.json')
    _llm_b_info = ss.get('llm_b') or readjson('llm_b.json')
    _emb_info = ss.get('emb') or readjson('emb.json')
    _db_info = ss.get('userdb') or readjson('db.json')

    st.caption(f"**Model A:** `{_llm_info.get('name', 'Offline')}`")
    if _llm_b_info.get('active'):
        st.caption(f"**Model B:** `{_llm_b_info.get('name', 'Active')}`")
    st.caption(f"**Vector:** `{_emb_info.get('name', 'Local')}`")
    st.caption(f"**DB:** `{_db_info.get('db_name', 'Connected')}`")

    st.sidebar.divider()
    st.sidebar.markdown("""<div style='font-size:0.75rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#818cf8;padding:2px 0 8px 0;'>Innovation Toggles</div>""", unsafe_allow_html=True)
    enable_ambiguity = st.sidebar.checkbox(
        "Ambiguity Clarification",
        value=True,
        help="Idea 4 — Detect underspecified queries and prompt user for interactive disambiguation"
    )
    enable_schema_linker = st.sidebar.checkbox(
        "Schema-Linking Visualizer",
        value=True,
        help="Idea 5 — Interactive ER graph showing which tables, columns and joins were used in the generated SQL"
    )
    enable_auto_viz = st.sidebar.checkbox(
        "Auto-Visualization",
        value=True,
        help="Idea 6 — Automatically plot query results as bar/line/metric charts; includes manual chart-type override"
    )
    st.sidebar.divider()
    if st.sidebar.button("Clear Chat History", use_container_width=True):
        ss.chat_history = []
        ss.clarification = None
        ss.pending_query = None
        st.rerun()

    # Simple friendly tip card in sidebar
    st.markdown("""
    <div style="background: rgba(30,41,59,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px; margin-top: 14px;">
        <div style="font-size: 0.78rem; font-weight: 700; color: #34d399; margin-bottom: 6px;">
            Tip
        </div>
        <div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.5;">
            Type any question in natural English. The assistant translates your words into a database query, runs it safely, and shows you the results.
        </div>
    </div>
    """, unsafe_allow_html=True)


demo_broken_sql = None

# Page header
st.markdown("""
<div style="margin-bottom:1.2rem;">
    <h2 style="font-size:1.6rem;font-weight:800;margin:0;background:linear-gradient(135deg,#f1f5f9 30%,#818cf8 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
        Chat with your Database
    </h2>
    <p style="color:#64748b;font-size:0.85rem;margin:4px 0 0 0;">Ask questions in plain English — ADEPT-SQL translates them to precise SQL queries.</p>
</div>
""", unsafe_allow_html=True)

# ── Load Model B config if not in session ─────────────────────────────────────
if 'llm_b' not in ss:
    ss.llm_b = readjson('llm_b.json')

model_b_active = ss.get('llm_b', {}).get('active', False)

if model_b_active:
    st.markdown(f"""
    <div style='background:rgba(99,102,241,0.10);border:1px solid rgba(99,102,241,0.25);border-radius:10px;
                padding:10px 16px;font-size:0.875rem;color:#a5b4fc;margin-bottom:0.8rem;'>
        <b>Dual-Model Mode Active</b> &mdash; Comparing
        <code style='background:rgba(99,102,241,0.15);padding:1px 6px;border-radius:4px;'>{ss.llm.get('name','Model A')}</code>
        vs
        <code style='background:rgba(99,102,241,0.15);padding:1px 6px;border-radius:4px;'>{ss.llm_b.get('name','Model B')}</code>
        using Execution Match
    </div>
    """, unsafe_allow_html=True)
else:
    st.caption("*Single-model mode. Configure Model B in Settings to enable side-by-side comparison.*")


# Guard: require settings to be configured
if 'llm' not in ss or not ss.llm.get('active', False):
    st.warning('LLM not connected. Please configure it on the Settings page first.')
    st.stop()

if 'emb' not in ss or not ss.emb.get('active', False):
    st.warning('Embedding model not connected. Please configure it on the Settings page first.')
    st.stop()

if 'userdb' not in ss or not ss.userdb.get('conn', False):
    st.warning('Database not connected. Please configure it on the Settings page first.')
    st.stop()

# ── Chat history & Idea 4 State Initialisation ─────────────────────────────────
if 'chat_history' not in ss:
    ss.chat_history = []
if 'clarification' not in ss:
    ss.clarification = None
if 'pending_query' not in ss:
    ss.pending_query = None


# Re-render all previous exchanges so the conversation is visible after reruns
for _hist_i, past in enumerate(ss.chat_history):
    with st.chat_message("user"):
        st.write(past['user'])
    with st.chat_message("assistant"):
        st.write(past.get('answer', ''))
        if past.get('rewritten'):
            st.caption(f"Understood as: *\"{past['rewritten']}\"*")
        if past.get('fuzzy_matches'):
            badges = " · ".join([f"`{m['raw']}` -> **{m['canonical']}** ({m['field']})" for m in past['fuzzy_matches']])
            st.info(f"**SIM Typo Alignment:** Auto-corrected entity: {badges}")
        with st.expander("View Generated SQL", expanded=False):
            if past.get('sql'):
                st.code(past['sql'], language='sql', wrap_lines=True)
            else:
                st.info("No SQL generated.")
        render_sql_explanation_verification(past.get('sql_verification'))
        render_correction_loop(past.get('correction_log', []))
        if past.get('error'):
            st.error(f"SQL Error: {past['error']}")
        elif past.get('table') is not None and not past['table'].empty:
            df_past = past['table'].T.drop_duplicates().T
            st.dataframe(df_past, use_container_width=True)
            st.caption(f"Showing {len(df_past)} row(s)")
            render_auto_visualization(df_past, past.get('user', ''), unique_key=f"hist_{_hist_i}")
        render_schema_linker(past.get('sql', ''))


# ── Idea 4: Interactive Ambiguity Clarification Dialog ─────────────────────────
if ss.get('clarification'):
    with st.chat_message("user"):
        st.write(ss.clarification['original_query'])
    with st.chat_message("assistant"):
        st.markdown("#### Query Clarification (Idea 4)")
        st.warning(f"**Identified Ambiguity:** {ss.clarification.get('reason', 'Query contains multiple valid interpretations.')}")
        st.markdown("Please choose the interpretation that matches your intent:")

        chosen_option = st.radio(
            "Interpretations:",
            options=ss.clarification['options'],
            key="ambiguity_radio_choice"
        )
        col_run_opt, col_run_orig = st.columns([2, 2])
        with col_run_opt:
            if st.button("Run Selected Interpretation", type="primary"):
                ss.pending_query = {
                    'execute_query': chosen_option,
                    'display_user': ss.clarification['original_query'],
                    'rewritten_text': f"Clarified: \"{chosen_option}\""
                }
                ss.clarification = None
                st.rerun()
        with col_run_orig:
            if st.button("Run Original Query Anyway"):
                ss.pending_query = {
                    'execute_query': ss.clarification['effective_question'],
                    'display_user': ss.clarification['original_query'],
                    'rewritten_text': ss.clarification.get('rewritten_text')
                }
                ss.clarification = None
                st.rerun()

# ── Chat input & Dispatcher ────────────────────────────────────────────────────
user_input = st.chat_input("Ask a question about your data...")


run_execution = False
effective_question = None
rewritten_text = None
display_user_query = None

if user_input:
    ss.clarification = None
    display_user_query = user_input
    effective_question = user_input

    # ── Idea 2: Context-aware query rewriting ──────────────────────────────────
    if ss.chat_history:
        with st.spinner("Understanding context..."):
            effective_question, rewritten_text = rewrite_query_with_context(
                user_input, ss.chat_history, ss.llm
            )

    # ── Idea 4: Ambiguity Pre-Check (only on new queries) ──────────────────────
    if enable_ambiguity:
        with st.spinner("Checking query specificity (Idea 4)..."):
            amb_res = check_ambiguity(effective_question, ss.llm)
        if amb_res.get('is_ambiguous') and amb_res.get('options'):
            ss.clarification = {
                'original_query': user_input,
                'effective_question': effective_question,
                'rewritten_text': rewritten_text,
                'reason': amb_res.get('reason', 'Query contains ambiguity.'),
                'options': amb_res.get('options', [])
            }
            st.rerun()

    run_execution = True

elif ss.get('pending_query'):
    pq = ss.pending_query
    display_user_query = pq['display_user']
    effective_question = pq['execute_query']
    rewritten_text = pq.get('rewritten_text')
    ss.pending_query = None
    run_execution = True

if run_execution and effective_question:
    with st.chat_message("user"):
        st.write(display_user_query)

    if model_b_active:
        # ── Dual-model mode ───────────────────────────────────────────────────
        with st.spinner("Running Model A..."):
            out_a = adept(effective_question, ss.llm, ss.emb, ss.userdb,
                          demo_broken_sql=demo_broken_sql or None)
        with st.spinner("Running Model B..."):
            out_b = adept(effective_question, ss.llm_b, ss.emb, ss.userdb,
                          demo_broken_sql=demo_broken_sql or None)

        with st.chat_message("assistant"):
            st.subheader("Dual-Model Comparison")

            # Execution Match verdict
            match = compare_dataframes(out_a['table'], out_b['table'])
            label = execution_match_label(out_a['table'], out_b['table'])
            if match:
                st.success(f"**Execution Match: {label}** — Both models produced identical query results.")
            else:
                st.error(f"**Execution Match: {label}** — The two models returned different results.")

            # ── Idea 1, 2 & 3 status indicators ─────────────────────────────────
            if out_a.get('fuzzy_matches'):
                badges = " · ".join([f"`{m['raw']}` -> **{m['canonical']}** ({m['field']})" for m in out_a['fuzzy_matches']])
                st.info(f"**SIM Typo Alignment:** Auto-corrected entity: {badges}")
            if rewritten_text:
                st.caption(f"Understood as: *\"{effective_question}\"*")
            if out_a.get('corrected'):
                st.caption("Model A SQL was auto-corrected (1 retry)")
            if out_b.get('corrected'):
                st.caption("Model B SQL was auto-corrected (1 retry)")

            st.divider()

            # Side-by-side tabs
            tab_a, tab_b, tab_compare = st.tabs([
                f"Model A — {ss.llm.get('name', 'Model A')}",
                f"Model B — {ss.llm_b.get('name', 'Model B')}",
                "SQL Comparison"
            ])

            # ── Tab A ─────────────────────────────────────────────────────────
            with tab_a:
                st.markdown(f"**Answer:** {out_a['answer']}")
                with st.expander("View Model A SQL"):
                    if out_a['sql']:
                        st.code(out_a['sql'], language='sql', wrap_lines=True)
                    else:
                        st.error("No SQL was generated.")
                render_sql_explanation_verification(out_a.get('sql_verification'))
                render_correction_loop(out_a.get('correction_log', []))
                if out_a['error']:
                    st.error(f"SQL Error: {out_a['error']}")
                elif out_a['table'].empty:
                    st.info("SQL ran successfully but returned no rows.")
                else:
                    df_a = out_a['table'].T.drop_duplicates().T
                    st.dataframe(df_a, use_container_width=True)
                    st.caption(f"Showing {len(df_a)} row(s)")
                    if enable_auto_viz:
                        render_auto_visualization(df_a, effective_question, unique_key="tab_a")
                if enable_schema_linker:
                    render_schema_linker(out_a.get('sql', ''))

            # ── Tab B ─────────────────────────────────────────────────────────
            with tab_b:
                st.markdown(f"**Answer:** {out_b['answer']}")
                with st.expander("View Model B SQL"):
                    if out_b['sql']:
                        st.code(out_b['sql'], language='sql', wrap_lines=True)
                    else:
                        st.error("No SQL was generated.")
                render_sql_explanation_verification(out_b.get('sql_verification'))
                render_correction_loop(out_b.get('correction_log', []))
                if out_b['error']:
                    st.error(f"SQL Error: {out_b['error']}")
                elif out_b['table'].empty:
                    st.info("SQL ran successfully but returned no rows.")
                else:
                    df_b = out_b['table'].T.drop_duplicates().T
                    st.dataframe(df_b, use_container_width=True)
                    st.caption(f"Showing {len(df_b)} row(s)")
                    if enable_auto_viz:
                        render_auto_visualization(df_b, effective_question, unique_key="tab_b")
                if enable_schema_linker:
                    render_schema_linker(out_b.get('sql', ''))

            # ── Tab Compare ───────────────────────────────────────────────────
            with tab_compare:
                st.markdown("#### Side-by-Side SQL Diff")
                col_a, col_b_col = st.columns(2)
                with col_a:
                    st.markdown(f"**{ss.llm.get('name', 'Model A')} SQL:**")
                    st.code(out_a['sql'] or '-- No SQL generated', language='sql', wrap_lines=True)
                with col_b_col:
                    st.markdown(f"**{ss.llm_b.get('name', 'Model B')} SQL:**")
                    st.code(out_b['sql'] or '-- No SQL generated', language='sql', wrap_lines=True)

                st.divider()
                st.markdown("#### Result Tables")
                col_ra, col_rb = st.columns(2)
                with col_ra:
                    st.markdown(f"**Model A Result** ({len(out_a['table'])} rows):")
                    if out_a['error']:
                        st.error(out_a['error'])
                    elif out_a['table'].empty:
                        st.info("No rows returned.")
                    else:
                        st.dataframe(out_a['table'].T.drop_duplicates().T, use_container_width=True)
                with col_rb:
                    st.markdown(f"**Model B Result** ({len(out_b['table'])} rows):")
                    if out_b['error']:
                        st.error(out_b['error'])
                    elif out_b['table'].empty:
                        st.info("No rows returned.")
                    else:
                        st.dataframe(out_b['table'].T.drop_duplicates().T, use_container_width=True)

        # Save to chat history
        ss.chat_history.append({
            'user': display_user_query,
            'rewritten': rewritten_text,
            'answer': out_a.get('answer', ''),
            'sql': out_a.get('sql', ''),
            'table': out_a.get('table', pd.DataFrame()),
            'sql_verification': out_a.get('sql_verification'),
            'corrected': out_a.get('corrected', False),
            'error': out_a.get('error'),
            'correction_log': out_a.get('correction_log', []),
            'fuzzy_matches': out_a.get('fuzzy_matches', []),
        })

    else:
        # ── Single-model mode ─────────────────────────────────────────────────
        with st.spinner("Thinking..."):
            out = adept(effective_question, ss.llm, ss.emb, ss.userdb,
                        demo_broken_sql=demo_broken_sql or None)

        with st.chat_message("assistant"):
            st.write(out['answer'])

            if out.get('fuzzy_matches'):
                badges = " · ".join([f"`{m['raw']}` -> **{m['canonical']}** ({m['field']})" for m in out['fuzzy_matches']])
                st.info(f"**SIM Typo Alignment:** Auto-corrected entity: {badges}")

            if rewritten_text:
                st.caption(f"Understood as: *\"{effective_question}\"*")

            with st.expander("View Generated SQL"):
                if out['sql']:
                    st.code(out['sql'], language='sql', wrap_lines=True)
                else:
                    st.error("No SQL was generated.")

            render_sql_explanation_verification(out.get('sql_verification'))
            render_correction_loop(out.get('correction_log', []))

            if out['error']:
                st.error(f"SQL Execution Error: {out['error']}")
                st.info("Try rephrasing your question or checking the Settings page to ensure the correct database is selected.")
            elif out['table'].empty:
                st.info("SQL ran successfully but returned no rows.")
            else:
                df_display = out['table'].T.drop_duplicates().T
                st.dataframe(df_display, use_container_width=True)
                st.caption(f"Showing {len(df_display)} row(s)")
                if enable_auto_viz:
                    render_auto_visualization(df_display, effective_question, unique_key="single")

            if enable_schema_linker:
                render_schema_linker(out.get('sql', ''))

        ss.chat_history.append({
            'user': display_user_query,
            'rewritten': rewritten_text,
            'answer': out.get('answer', ''),
            'sql': out.get('sql', ''),
            'table': out.get('table', pd.DataFrame()),
            'sql_verification': out.get('sql_verification'),
            'corrected': out.get('corrected', False),
            'error': out.get('error'),
            'correction_log': out.get('correction_log', []),
            'fuzzy_matches': out.get('fuzzy_matches', []),
        })