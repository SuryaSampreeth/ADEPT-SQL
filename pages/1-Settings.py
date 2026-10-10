"""
1-Settings.py — Enterprise Configuration Studio for ADEPT-SQL
==============================================================
Manages credentials, model orchestrations, vectorizer embeddings,
database connections, and the CSR Question-SQL knowledge base.
"""

import os, sys
pythonon_path = os.path.dirname('../')
sys.path.append(pythonon_path)

from call_llm import callLLM
from call_emb import callm3e, vectorize_localmodel
from opDB import localsqlite
from user_input_process import user_input_init

import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import json
from ui_theme import inject_global_css, page_hero, section_label


def writejson(ssdict, file):
    json_object = json.dumps(ssdict, indent=4)
    with open("./backend/" + file, "w") as outfile:
        outfile.write(json_object)


def readjson(file):
    try:
        with open("./backend/" + file, 'r') as openfile:
            return json.load(openfile)
    except Exception:
        return {}


# ── PAGE SETUP ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADEPT-SQL | Configuration Studio",
    page_icon="⚙️",
    layout="wide",
)
inject_global_css()
st.logo("logobar.png", icon_image='logonew.png', size='large')

# ── Load persistent configurations into session state ─────────────────────────
if "llm" not in ss:
    saved_llm = readjson('llm.json')
    ss.llm = saved_llm if saved_llm else {'name': 'Demo Mode (Offline)', 'url': 'demo', 'token': 'demo', 'active': True}

if "llm_b" not in ss:
    saved_llm_b = readjson('llm_b.json')
    ss.llm_b = saved_llm_b if saved_llm_b else {'name': '', 'url': '', 'token': '', 'active': False}

if "emb" not in ss:
    saved_emb = readjson('emb.json')
    ss.emb = saved_emb if saved_emb else {'name': 'local model', 'url': 'local model', 'token': 'local model', 'active': True}

if 'userdb' not in ss or not isinstance(ss.userdb, dict) or not ss.userdb.get('conn', False):
    saved_db = readjson('db.json')
    if saved_db and saved_db.get('conn', False):
        ss.userdb = saved_db
    else:
        ss.userdb = {
            'option': 'Turtorial DB',
            'sqlite_path': "./sqlite/cre_Drama_Workshop_Groups.sqlite",
            'db_name': "cre_Drama_Workshop_Groups.sqlite",
            'conn': False
        }

# ── Hero Header ───────────────────────────────────────────────────────────────
page_hero(
    title="Enterprise Configuration Studio",
    subtitle="Configure the multi-stage neural generators, vector embeddings, and relational database connections.",
    tags=[
        f"Primary: {ss.llm.get('name', 'Offline')}",
        f"Comparison: {ss.llm_b.get('name', 'None') if ss.llm_b.get('active') else 'Disabled'}",
        f"Database: {ss.userdb.get('db_name', 'Not Connected') if ss.userdb.get('conn') else 'Disconnected'}",
        f"Embeddings: {ss.emb.get('name', 'Local')}",
    ]
)

# ── Live Status Ribbon (Real-Time System Overview) ────────────────────────────
section_label("⚡ System Connection Overview")

sc1, sc2, sc3, sc4 = st.columns(4)

with sc1:
    llm_act = ss.llm.get('active', False)
    is_demo = ss.llm.get('token', '').lower() in ('demo', 'none', 'mock', 'offline', '')
    badge_cls = "pill-tag-amber" if is_demo else ("pill-tag-green" if llm_act else "")
    status_text = "Demo Mode" if is_demo else ("Active" if llm_act else "Disconnected")
    st.markdown(f"""
    <div class="feature-card" style="padding:1rem;">
        <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;text-transform:uppercase;">Primary LLM</div>
        <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin:4px 0;">{ss.llm.get('name', 'Model A')[:20]}</div>
        <span class="pill-tag {badge_cls}">● {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

with sc2:
    llm_b_act = ss.llm_b.get('active', False)
    badge_cls = "pill-tag-green" if llm_b_act else ""
    status_text = "Active" if llm_b_act else "Disabled"
    st.markdown(f"""
    <div class="feature-card" style="padding:1rem;">
        <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;text-transform:uppercase;">Comparison Model B</div>
        <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin:4px 0;">{ss.llm_b.get('name', 'Disabled')[:20] if llm_b_act else 'Not Set'}</div>
        <span class="pill-tag {badge_cls}">● {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

with sc3:
    emb_act = ss.emb.get('active', False)
    badge_cls = "pill-tag-green" if emb_act else ""
    status_text = "Vector Ready" if emb_act else "Disconnected"
    st.markdown(f"""
    <div class="feature-card" style="padding:1rem;">
        <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;text-transform:uppercase;">Embedding Model</div>
        <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin:4px 0;">{ss.emb.get('name', 'local model')[:20]}</div>
        <span class="pill-tag {badge_cls}">● {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

with sc4:
    db_conn = ss.userdb.get('conn', False)
    badge_cls = "pill-tag-green" if db_conn else ""
    status_text = "Connected" if db_conn else "Disconnected"
    st.markdown(f"""
    <div class="feature-card" style="padding:1rem;">
        <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;text-transform:uppercase;">Database</div>
        <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin:4px 0;">{ss.userdb.get('db_name', 'None')[:20]}</div>
        <span class="pill-tag {badge_cls}">● {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

# ── Sidebar Status Monitor ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📡 System Heartbeat")
    st.checkbox("Primary LLM Connected", value=ss.llm.get('active', False), disabled=True)
    if ss.llm.get('active'):
        st.caption(f"🧠 {ss.llm.get('name','—')}")

    st.checkbox("Comparison LLM (Model B)", value=ss.llm_b.get('active', False), disabled=True)
    if ss.llm_b.get('active'):
        st.caption(f"🅱️ {ss.llm_b.get('name','—')}")

    st.checkbox("Embedding Vectorizer Ready", value=ss.emb.get('active', False), disabled=True)
    if ss.emb.get('active'):
        st.caption(f"💾 {ss.emb.get('name','—')}")

    st.checkbox("Database Connected", value=ss.userdb.get('conn', False), disabled=True)
    if ss.userdb.get('conn'):
        st.caption(f"🗄️ {ss.userdb.get('db_name','—')}")

# ── Main Tabs ─────────────────────────────────────────────────────────────────
tabllm, tabdb, tabsql = st.tabs(['🤖 LLM & Vector Models', '🗄️ Data Source & Schema', '📝 Question-SQL Pairs'])

###################### LLM TAB #######################
with tabllm:
    # ── Model A ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.25);border-radius:12px;padding:1.4rem;margin-bottom:1.5rem;'>
        <div style='font-size:0.85rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#818cf8;margin-bottom:4px;'>
            🅰️ Model A — Primary Neural SQL Generator
        </div>
        <p style='font-size:0.82rem;color:#94a3b8;margin:0 0 1rem 0;'>
            The main LLM orchestrator responsible for schema linking, query intent translation, and reasoning.
        </p>
    """, unsafe_allow_html=True)

    st.info("💡 **No API Key?** Leave fields blank or type `demo` to run in **Offline Demo Mode** with rule-based fallback SQL generator!")

    col_a1, col_a2 = st.columns([1, 1])
    with col_a1:
        ss.llm['name'] = st.text_input("Model Name", value=ss.llm.get('name', 'Demo Mode (Offline)'), key="llm_name_input")
        ss.llm['url']  = st.text_input("API URL / Endpoint", value=ss.llm.get('url', 'demo'), key="llm_url_input")
    with col_a2:
        ss.llm['token'] = st.text_input("API Key (type 'demo' for Offline Mode)", value=ss.llm.get('token', 'demo'), type="password", key="llm_token_input")
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("Connect & Verify Model A", type="primary", use_container_width=True, key="connect_model_a"):
            with st.spinner("Connecting to Model A..."):
                res = callLLM(ss.llm).init_prompt('system', 'Who are you?').call().get_response_content()

            if res == 'LLM Fail':
                st.error("❌ Connection failed! Please check the API URL and Key.")
                ss.llm['active'] = False
            else:
                st.success("✅ Model A connection verified successfully!")
                if ss.llm['token'].lower() in ('', 'demo', 'none', 'mock', 'offline'):
                    st.info("🚀 Running in **Offline Demo Mode** (Rule-based SQL Generator enabled).")
                ss.llm['active'] = True
                writejson(ss.llm, 'llm.json')
                st.markdown(f"""
                <div style="background:rgba(30,41,59,0.7);border-radius:8px;padding:12px;font-size:0.85rem;margin-top:8px;">
                    <b>Prompt:</b> Who are you?<br>
                    <b>Response:</b> {res}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Model B ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.25);border-radius:12px;padding:1.4rem;margin-bottom:1.5rem;'>
        <div style='font-size:0.85rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#34d399;margin-bottom:4px;'>
            🅱️ Model B — Comparison LLM (Side-by-Side Evaluation)
        </div>
        <p style='font-size:0.82rem;color:#94a3b8;margin:0 0 1rem 0;'>
            Configure a secondary LLM to compare performance using Execution Match. Leave blank or disable to keep single-model mode.
        </p>
    """, unsafe_allow_html=True)

    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        ss.llm_b['name'] = st.text_input("Model B Name", value=ss.llm_b.get('name', ''), placeholder="e.g. gpt-4o-mini or deepseek/deepseek-chat", key='llm_b_name')
        ss.llm_b['url']  = st.text_input("Model B URL",  value=ss.llm_b.get('url', ''), placeholder="e.g. https://openrouter.ai/api/v1/chat/completions", key='llm_b_url')
    with col_b2:
        ss.llm_b['token'] = st.text_input("Model B API Key", value=ss.llm_b.get('token', ''), placeholder="Paste API key or type 'demo'", type="password", key='llm_b_token')
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        col_b_act1, col_b_act2 = st.columns(2)
        with col_b_act1:
            if st.button("Connect Model B", use_container_width=True, key='connect_llm_b'):
                if ss.llm_b['name'].strip() == '' and ss.llm_b['token'].strip() == '':
                    st.warning("⚠️ Enter Model Name and Key to activate Model B.")
                else:
                    with st.spinner("Connecting Model B..."):
                        res_b = callLLM(ss.llm_b).init_prompt('system', 'Who are you?').call().get_response_content()
                    if res_b == 'LLM Fail':
                        st.error("❌ Model B Connection failed.")
                        ss.llm_b['active'] = False
                    else:
                        st.success("✅ Model B connected successfully!")
                        ss.llm_b['active'] = True
                        writejson(ss.llm_b, 'llm_b.json')
                        st.rerun()
        with col_b_act2:
            if st.button("Disable Model B", use_container_width=True, key='disable_llm_b'):
                ss.llm_b = {'name': '', 'url': '', 'token': '', 'active': False}
                writejson(ss.llm_b, 'llm_b.json')
                st.info("Model B disabled.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Embedding Model ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.25);border-radius:12px;padding:1.4rem;margin-bottom:1.5rem;'>
        <div style='font-size:0.85rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#22d3ee;margin-bottom:4px;'>
            💾 Embedding Vectorizer Model (CSR Retrieval)
        </div>
        <p style='font-size:0.82rem;color:#94a3b8;margin:0 0 1rem 0;'>
            Used for encoding question representations into semantic vector space for Case-based Reasoning exemplar matching.
        </p>
    """, unsafe_allow_html=True)

    col_e1, col_e2 = st.columns([1, 1])
    with col_e1:
        ss.emb['name'] = st.text_input("Embedding Model Name", key='emb1', value=ss.emb.get('name', 'local model'))
        ss.emb['url']  = st.text_input("Embedding API URL", key='emb2', value=ss.emb.get('url', 'local model'))
    with col_e2:
        ss.emb['token'] = st.text_input("Embedding API Key", key='emb3', value=ss.emb.get('token', 'local model'), type="password")
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("Test & Connect Embedding Model", use_container_width=True, key='butforemb'):
            if ss.emb['name'] != '' and ss.emb['url'] != '' and ss.emb['token'] != '':
                with st.spinner("Testing vector embedding..."):
                    if ss.emb['name'] != 'local model':
                        res = callm3e(ss.emb).init_prompt('TestText').call()
                    else:
                        res = vectorize_localmodel('TestText')

                if res == 'Emb Fail':
                    st.error("❌ Embedding model connection failed.")
                    ss.emb['active'] = False
                else:
                    st.success(f"✅ Embedding vectorizer connected! Generated vector dimension: {len(res)}D")
                    ss.emb['active'] = True
                    writejson(ss.emb, 'emb.json')
            else:
                st.error("⚠️ Incomplete form. Please fill in the details.")
                ss.emb['active'] = False

    st.markdown("</div>", unsafe_allow_html=True)


################### DataSource Tab ##################
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        width=1000,
        height=320,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=('Table'),
    )
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop('Select', axis=1)


with tabdb:
    section_label("🗄️ Database Connection Settings")

    if not ss.userdb.get('conn', False):
        ss.userdb['option'] = st.pills(
            "Database Engine",
            options=['Turtorial DB', 'Sqlite', 'MySQL'],
            default=ss.userdb.get('option', 'Turtorial DB'),
            selection_mode="single",
        )
        if ss.userdb['option'] == 'MySQL':
            c1, c2, c3 = st.columns(3)
            with c1:
                ss.userdb['ip'] = st.text_input("IP Host", value=ss.userdb.get('ip', '127.0.0.1'))
                ss.userdb['port'] = st.text_input("Port", value=ss.userdb.get('port', '3306'))
            with c2:
                ss.userdb['user_name'] = st.text_input("Username", value=ss.userdb.get('user_name', 'root'))
                ss.userdb['user_password'] = st.text_input("Password", type="password")
            with c3:
                ss.userdb['db_name'] = st.text_input("Database Name")
            ss.userdb['conn'] = False

        if ss.userdb['option'] == 'Sqlite':
            ss.userdb['sqlite_path'] = st.text_input("Database File Path", value=ss.userdb.get('sqlite_path', ''))
            if ss.userdb['sqlite_path']:
                ss.userdb['db_name'] = ss.userdb['sqlite_path'].split('/')[-1]
            ss.userdb['conn'] = False

        if ss.userdb['option'] == 'Turtorial DB':
            ss.userdb['sqlite_path'] = "./sqlite/cre_Drama_Workshop_Groups.sqlite"
            ss.userdb['db_name'] = "cre_Drama_Workshop_Groups.sqlite"
            ss.userdb['conn'] = False

        if st.button("Connect Database", type="primary", use_container_width=True):
            try:
                db = localsqlite(ss.userdb['sqlite_path']).conn()
                ss.userdb['conn'] = True
                writejson(ss.userdb, 'db.json')
                st.success("✅ Database connected successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
    else:
        db_card_col1, db_card_col2 = st.columns([3, 1])
        with db_card_col1:
            st.markdown(f"""
            <div style="background:rgba(30,41,59,0.7);border:1px solid rgba(16,185,129,0.3);border-radius:10px;padding:14px;">
                <span class="pill-tag pill-tag-green">● Connected</span>
                <span style="font-weight:700;color:#f1f5f9;margin-left:8px;">{ss.userdb.get('db_name', 'cre_Drama_Workshop_Groups.sqlite')}</span>
                <span style="color:#64748b;font-size:0.85rem;margin-left:12px;">Engine: {ss.userdb.get('option', 'Sqlite')}</span>
            </div>
            """, unsafe_allow_html=True)
        with db_card_col2:
            if st.button("Disconnect / Reconnect", use_container_width=True):
                ss.userdb['conn'] = False
                writejson(ss.userdb, 'db.json')
                st.rerun()

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    if ss.userdb.get('conn', False):
        section_label("📋 Schema Extraction & Entity Registration")

        ss.dbconn = localsqlite(ss.userdb['sqlite_path']).conn()
        ss.alltables = list(ss.dbconn.metadata.tables.keys())
        ss.alltablesdf = pd.DataFrame({"Table": ss.alltables})

        ss.alltable_cols = {'Table': [], 'Column': []}
        for table in ss.alltables:
            columns = ss.dbconn.metadata.tables[table].columns.keys()
            for i in range(len(columns)):
                ss.alltable_cols['Table'].append(table)
                ss.alltable_cols['Column'].append(list(columns)[i])
        ss.alltable_colsdf = pd.DataFrame(ss.alltable_cols)

        if 'selected_table_colsdf' not in ss:
            ss.selected_table_colsdf = pd.DataFrame(columns=['Table', 'Table Description', 'Column', 'Columns Description'])

        col4table, col4col = st.columns(2)
        with col4table:
            st.markdown("**1. Select Active Tables:**")
            ss.tableselection = dataframe_with_selections(ss.alltablesdf)
            ss.selectedtables = list(ss.tableselection['Table'])

        with col4col:
            newtable = None
            if len(ss.selectedtables) == 1:
                newtable = ss.selectedtables[0]
            elif len(ss.selectedtables) > 1:
                newtable = ss.selectedtables[-1]

            if newtable:
                st.markdown(f'**2. Columns of table `{newtable}`:**')
            else:
                st.markdown("**2. Choose Columns:**")
            ss.colselection = dataframe_with_selections(ss.alltable_colsdf[ss.alltable_colsdf['Table'] == newtable][['Column']])

        ss.selected_table_colsdf = pd.concat([
            ss.selected_table_colsdf,
            pd.DataFrame({
                'Table': [newtable] * len(ss.colselection),
                'Table Description': [''] * len(ss.colselection),
                'Column': list(ss.colselection['Column']),
                'Column Description': [''] * len(ss.colselection)
            })
        ]).drop_duplicates()

        st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
        st.markdown("**3. Review Descriptions & Mark SIM Terminology:**")
        st.caption("Check 'As Terminology' to automatically extract unique column values for Idea 1 fuzzy entity matching.")

        df_summary = ss.selected_table_colsdf.copy().reset_index()
        df_summary.insert(0, "As Terminology", False)
        edited_df = st.data_editor(
            df_summary[['As Terminology', 'Table', 'Table Description', 'Column', 'Column Description']],
            hide_index=True,
            width=2000,
            height=300,
            column_config={
                "As Terminology": st.column_config.CheckboxColumn(required=True, width='small', help="Values will be indexed for fuzzy SIM matching"),
                "Table Description": st.column_config.Column(width="large"),
                "Column Description": st.column_config.Column(width="large")
            },
            disabled=('Table', 'Column'),
            num_rows='dynamic'
        )
        selected_df = edited_df[edited_df['As Terminology']][['Table', 'Column']]

        if st.button('💾 Save Schema Metadata & Extract Terminology', type="primary", use_container_width=True):
            dbmeta = edited_df[['Table', 'Table Description', 'Column', 'Column Description']]
            dbmeta.to_csv('./backend/dbmata.csv')

            termlistdf = pd.DataFrame(columns=['table', 'field', 'term'])
            for i in range(selected_df.shape[0]):
                table = selected_df.iloc[i]['Table']
                col = selected_df.iloc[i]['Column']
                sql = f"SELECT {col} FROM {table}"
                coldf = ss.dbconn.exesql(sql)
                coltermset = set(list(coldf[col]))
                for term in coltermset:
                    termlistdf = pd.concat([termlistdf, pd.DataFrame({
                        'table': [table],
                        'field': [col],
                        'term': [term]
                    })], ignore_index=True)
            termlistdf.to_csv('./backend/term.csv')

            st.success(f"✅ Schema saved! {termlistdf.shape[0]} unique entity terms indexed for SIM fuzzy matching.")


###################### SQL TAB ##################
with tabsql:
    section_label("📝 CSR Exemplar Library (Case-based Reasoning)")

    st.markdown("""
    Add representative Question-SQL pairs to the exemplar knowledge base. ADEPT-SQL retrieves the top similar
    exemplars during the CSR stage to construct dynamic few-shot prompts for the LLM.
    """)

    if "qa_pairs" not in ss:
        ss.qa_pairs = pd.DataFrame(columns=["Question", 'Masked Question', "SQL"])

    with st.expander("➕ Add New Question-SQL Pair", expanded=False):
        Qstr = st.text_input("Natural Language Question", key="q", placeholder="e.g. How many stores are there?")
        Astr = st.text_area("Gold Standard SQL Query", key="a", placeholder="e.g. SELECT COUNT(*) FROM Stores")

        if Qstr != '' and Astr != '':
            Qmask = user_input_init(Qstr).full_process().trans
            if st.button("Add Pair to Library", key="add_qa_btn"):
                if Qmask not in set(ss.qa_pairs['Masked Question']):
                    ss.qa_pairs = pd.concat([ss.qa_pairs, pd.DataFrame({
                        "Question": [Qstr],
                        "Masked Question": [Qmask],
                        "SQL": [Astr]
                    })])
                    st.success("Exemplar added!")
                else:
                    st.error('This masked question already exists in the library!')

    st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
    st.markdown("**Current Question-SQL Exemplars:**")

    qa_df = ss.qa_pairs.copy().reset_index()
    edited_df = st.data_editor(
        qa_df[['Question', "Masked Question", 'SQL']],
        hide_index=True,
        width=2000,
        height=320,
        num_rows='dynamic'
    )

    if st.button('⚡ Vectorize & Save Exemplars into CSR Knowledge Base', type="primary", key='qssave', use_container_width=True):
        if ss.emb.get('name') != 'local model':
            embmodel = callm3e(ss.emb)
        else:
            embmodel = 'localmodel'

        qs_df = edited_df.dropna()
        qs_df_4csv = pd.DataFrame(columns=['question', 'qmask', 'qvec', 'sql'])

        with st.spinner("Generating semantic embeddings..."):
            for i in range(qs_df.shape[0]):
                q = qs_df.iloc[i]['Question']
                qmask = qs_df.iloc[i]['Masked Question']
                sql = qs_df.iloc[i]['SQL']
                if embmodel != 'localmodel':
                    qvec = embmodel.init_prompt(qmask).call()
                else:
                    qvec = vectorize_localmodel(qmask)

                qs_df_4csv = pd.concat([qs_df_4csv, pd.DataFrame({
                    'question': [q],
                    'qmask': [qmask],
                    'qvec': [str(qvec)],
                    'sql': [sql]
                })], ignore_index=True)
            qs_df_4csv.to_csv('./backend/qvec.csv')

        st.success(f"✅ {qs_df_4csv.shape[0]} exemplars vectorized and saved into `./backend/qvec.csv`!")
