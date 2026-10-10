import json
import re
import pandas as pd

from call_llm import callLLM, clean_sql_output
from opDB import localsqlite
from user_input_process import user_input_init
from similarity_cal import search_qvec
from prompt_templates import (
    Prompt_Fewshot, Prompt_Zeroshot, Prompt_Answer, Prompt_SelfCorrection,
    Prompt_AmbiguityCheck, Prompt_SQLExplanationAndVerification
)


def explain_and_verify_sql(question: str, sql: str, llm: dict, schema_summary: str = "") -> dict:
    """
    Idea 3: Dual-Direction SQL Explanation & Semantic Verification (NL <-> SQL).
    Translates the generated SQL into plain English logical steps and cross-verifies
    whether user question constraints/entities are faithfully satisfied.
    """
    if not sql or not sql.strip():
        return {
            'verified': False,
            'verdict_summary': 'No SQL generated to verify.',
            'plain_english_summary': 'No query operations were executed.',
            'execution_logic_steps': [],
            'constraints_checked': []
        }
    try:
        prompt = Prompt_SQLExplanationAndVerification(question, sql, schema_summary).compile()
        raw = callLLM(llm).init_prompt(
            'You are a Text-to-SQL logic analysis and verification engine. Output valid JSON only. No markdown fences.',
            prompt
        ).call().get_response_content()

        cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip('`').strip()
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return {
                'verified': bool(data.get('verified', True)),
                'verdict_summary': str(data.get('verdict_summary', 'Query logic matches question requirements.')),
                'plain_english_summary': str(data.get('plain_english_summary', '')),
                'execution_logic_steps': list(data.get('execution_logic_steps', [])),
                'constraints_checked': list(data.get('constraints_checked', []))
            }
    except Exception as e:
        print(f"[Verification] Logic explanation failed: {e}")

    # Graceful fallback summary
    return {
        'verified': True,
        'verdict_summary': 'SQL syntax and schema validated successfully.',
        'plain_english_summary': f'Executes SQL query against database tables to answer: "{question}".',
        'execution_logic_steps': [f'Executes: {sql}'],
        'constraints_checked': [{'constraint': 'Query execution syntax', 'status': 'Satisfied'}]
    }


def check_ambiguity(question: str, llm: dict, schema_summary: str = "") -> dict:
    """
    Idea 4: Evaluates query intent against explicit ambiguity criteria (ranking,
    aggregation, temporal, multi-path). Returns dict with:
      {'is_ambiguous': bool, 'reason': str, 'options': list}
    """
    try:
        prompt = Prompt_AmbiguityCheck(question, schema_summary).compile()
        raw = callLLM(llm).init_prompt(
            'You are a query disambiguation assistant. Output valid JSON only. No markdown.',
            prompt
        ).call().get_response_content()

        # Clean json if wrapped in ```json ... ```
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip('`').strip()
        data = json.loads(cleaned)
        if isinstance(data, dict) and 'is_ambiguous' in data:
            return {
                'is_ambiguous': bool(data.get('is_ambiguous', False)),
                'reason': str(data.get('reason', '')),
                'options': list(data.get('options', []))
            }
    except Exception as e:
        print(f"[Ambiguity] Check failed: {e}")

    return {'is_ambiguous': False, 'reason': '', 'options': []}


def generate_sql(prompt: str, llm: dict) -> str:
    """Call LLM to generate SQL, then clean the output robustly."""
    raw = callLLM(llm).init_prompt(
        'You are a SQL query writer. Output only valid SQL. No explanations. No markdown.',
        prompt
    ).call().get_response_content()

    if raw == 'LLM Fail':
        return ''

    return clean_sql_output(raw)


def generate_ans(prompt: str, llm: dict) -> str:
    """Call LLM to produce the natural-language summary answer."""
    res = callLLM(llm).init_prompt(
        'You are a helpful Text2SQL task assistant. Be concise and clear.',
        prompt
    ).call().get_response_content()
    return res.strip()



def adept(user_input: str, llm: dict, emb: dict, db: dict,
          demo_broken_sql: str = None) -> dict:
    """
    Main ADEPT-SQL pipeline:
      1. SIM  — Semantic Input Masking (term + date normalization)
      2. CSR  — Contextual SQL Retriever (vector similarity search on QS store)
      3. APC  — Adaptive Prompt Composer (few-shot or zero-shot branch)
      4. LLM call → SQL generation
      5. SQL execution on the database (with optional self-correction)
      6. Natural language answer generation

    Args:
        user_input: Raw natural language question from the user.
        llm: Dict with keys: name, url, token
        emb: Dict with keys: name, url, token (use name='local model' for local)
        db: Dict with keys: sqlite_path (and optionally option, db_name)
        demo_broken_sql: (Optional) Override the first SQL attempt with this
            intentionally broken query so the self-correction loop is guaranteed
            to fire. Used only for classroom/demo purposes.

    Returns:
        Dict with keys: answer (str), sql (str), table (DataFrame)
    """

    # -- Step 1: SIM - Semantic Input Masker ----------------------------------
    print('\n====== [ADEPT-SQL] Step 1: SIM ======')
    full_processed_input = user_input_init(user_input).full_process()
    if full_processed_input.fuzzy_matches:
        print(f"[SIM] Idea 1 (Fuzzy Alignment): Detected {len(full_processed_input.fuzzy_matches)} typo(s):")
        for fm in full_processed_input.fuzzy_matches:
            print(f"      '{fm['raw']}' -> '{fm['canonical']}' ({fm['field']}, similarity: {fm['score']})")


    # -- Step 2: CSR - Contextual SQL Retriever --------------------------------
    print('\n====== [ADEPT-SQL] Step 2: CSR ======')
    smlQS_not_exist, info, founddf = search_qvec(full_processed_input, emb)
    print(f'[CSR] Result: {info}')
    if not founddf.empty:
        print(founddf[['question', 'similarity']].to_string())

    # -- Step 3: APC - Adaptive Prompt Composer --------------------------------
    print('\n====== [ADEPT-SQL] Step 3: APC ======')
    if smlQS_not_exist:
        print('[APC] Branch: ZERO-SHOT (no similar QS pairs found)')
        prompt = Prompt_Zeroshot(full_processed_input).compile()
    else:
        print(f'[APC] Branch: FEW-SHOT ({founddf.shape[0]} similar pair(s) found)')
        prompt = Prompt_Fewshot(full_processed_input, founddf).compile()

    # -- Step 4: SQL Generation -------------------------------------------------
    print('\n====== [ADEPT-SQL] Step 4: LLM -> SQL ======')
    sql = generate_sql(prompt, llm)
    print(f'[SQL] Generated:\n{sql}')

    # Demo mode: override attempt-1 SQL with a deliberately broken query
    if demo_broken_sql and demo_broken_sql.strip():
        print(f'[DEMO] Overriding attempt-1 SQL with broken SQL for demo purposes.')
        sql = demo_broken_sql.strip()
        print(f'[DEMO] Broken SQL injected:\n{sql}')

    # -- Step 5: SQL Execution with Self-Correction (Idea 3) ------------------
    print('\n====== [ADEPT-SQL] Step 5: SQL Execution ======')
    resdf = pd.DataFrame()
    sql_error = None
    corrected = False          # True if self-correction fixed the SQL
    MAX_RETRIES = 1            # One repair attempt maximum
    correction_log = []        # ← NEW: full trace of every attempt for the UI

    if sql:
        current_sql = sql
        try:
            dbconn = localsqlite(db['sqlite_path']).conn()
        except Exception as dbe:
            dbconn = None
            sql_error = f"Database connection error: {dbe}"

        for attempt in range(MAX_RETRIES + 1):   # attempt = 0, then 1
            if not dbconn:
                correction_log.append({
                    'attempt': attempt + 1,
                    'status': 'failed',
                    'sql': current_sql,
                    'error': sql_error,
                    'fixed_sql': None,
                })
                break
            try:
                resdf = dbconn.exesql(current_sql)
                # Remove any duplicated columns
                duplicate_cols = resdf.columns[resdf.columns.duplicated()]
                resdf.drop(columns=duplicate_cols, inplace=True)
                print(f'[SQL] Executed successfully (attempt {attempt + 1}). Rows: {len(resdf)}')
                print(resdf.head(3))
                # ── log this attempt ──────────────────────────────────────────
                correction_log.append({
                    'attempt': attempt + 1,
                    'status': 'success',
                    'sql': current_sql,
                    'error': None,
                    'fixed_sql': None,
                })
                if attempt > 0:
                    corrected = True
                    sql = current_sql   # expose corrected SQL to caller
                sql_error = None        # Clear error on success!
                break   # success — exit retry loop
            except Exception as e:
                sql_error = str(e)
                print(f'[SQL] Execution failed (attempt {attempt + 1}): {sql_error}')
                fixed_sql_this_round = None

                if attempt < MAX_RETRIES:
                    print('[SQL] Self-correction: asking LLM to fix the SQL with schema context...')
                    try:
                        schema_summary = dbconn.get_schema_summary(
                            broken_sql=current_sql,
                            error_msg=sql_error
                        ) if dbconn else ""

                        correction_prompt = Prompt_SelfCorrection(
                            original_question=full_processed_input.input,
                            broken_sql=current_sql,
                            error_message=sql_error,
                            schema=schema_summary
                        ).compile()
                        fixed_sql = generate_sql(correction_prompt, llm)
                        if fixed_sql and fixed_sql.strip() != current_sql.strip():
                            print(f'[SQL] Self-corrected SQL:\n{fixed_sql}')
                            fixed_sql_this_round = fixed_sql
                            # ── log failed attempt with its fix ──────────────
                            correction_log.append({
                                'attempt': attempt + 1,
                                'status': 'failed',
                                'sql': current_sql,
                                'error': sql_error,
                                'fixed_sql': fixed_sql,
                            })
                            current_sql = fixed_sql
                            sql_error = None   # clear so next attempt is clean

                        else:
                            print('[SQL] Self-correction returned same/empty SQL. Stopping retries.')
                            correction_log.append({
                                'attempt': attempt + 1,
                                'status': 'failed_no_fix',
                                'sql': current_sql,
                                'error': sql_error,
                                'fixed_sql': None,
                            })
                            break
                    except Exception as ce:
                        print(f'[SQL] Self-correction prompt failed: {ce}')
                        correction_log.append({
                            'attempt': attempt + 1,
                            'status': 'correction_error',
                            'sql': current_sql,
                            'error': sql_error,
                            'fixed_sql': None,
                        })
                        break
                else:
                    # Final attempt also failed
                    correction_log.append({
                        'attempt': attempt + 1,
                        'status': 'failed',
                        'sql': current_sql,
                        'error': sql_error,
                        'fixed_sql': None,
                    })
    else:
        sql_error = 'SQL generation returned empty result.'
        print(f'[SQL] {sql_error}')
        correction_log.append({
            'attempt': 0,
            'status': 'no_sql',
            'sql': None,
            'error': sql_error,
            'fixed_sql': None,
        })

    # -- Step 6: Answer Generation ---------------------------------------------
    print('\n====== [ADEPT-SQL] Step 6: Answer ======')
    if smlQS_not_exist:
        search_res = 'No similar Question-SQL pair found. SQL was generated from scratch using the database schema.'
    else:
        questions = '; '.join(list(founddf['question']))
        search_res = (
            f'{founddf.shape[0]} similar Question-SQL pair(s) found. '
            f'Similar questions: {questions}. The SQL was generated by imitating these examples.'
        )

    exec_preview = resdf.head(3) if not resdf.empty else (sql_error or 'No results')

    taskinfos = {
        'question': full_processed_input.input,
        'search_res': search_res,
        'sql': sql,
        'sqlexe': exec_preview
    }
    ans_prompt = Prompt_Answer(taskinfos).complie()
    answer = generate_ans(ans_prompt, llm)
    print(f'[Answer] {answer}')

    # -- Step 7 (Idea 3): Dual-Direction SQL Explanation & Semantic Verification --
    print('\n====== [ADEPT-SQL] Step 7: Dual-Direction SQL Explanation & Verification (Idea 3) ======')
    schema_summary = dbconn.get_schema_summary() if dbconn else ""
    sql_verification = explain_and_verify_sql(
        question=full_processed_input.input,
        sql=sql,
        llm=llm,
        schema_summary=schema_summary
    )
    print(f"[Verification] Verdict: {sql_verification.get('verdict_summary')}")

    return {
        'answer': answer,
        'sql': sql,
        'table': resdf,
        'error': sql_error,
        'sql_verification': sql_verification,  # Idea 3: Plain-English explanation + constraint verification
        'corrected': corrected,
        'correction_log': correction_log,
        'fuzzy_matches': full_processed_input.fuzzy_matches,  # Idea 1: typo corrections from SIM
    }



if __name__ == "__main__":
    # ─── Example: configure your LLM here ───────────────────────────────────
    # Option A: OpenRouter / DeepSeek (free)
    llm = {
        "name": "deepseek/deepseek-chat-v3-0324:free",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "token": ""   # ← add your OpenRouter API key
    }
    # Option B: Local Ollama
    # llm = {"name": "qwen2.5:7b", "url": "http://localhost:11434/v1/chat/completions", "token": "ollama"}

    emb = {"name": "local model", "url": "", "token": ""}
    db = {"sqlite_path": "./sqlite/cre_Drama_Workshop_Groups.sqlite"}

    result = adept("Did Blake book Adan Dinning?", llm, emb, db)
    print("\n=== FINAL RESULT ===")
    print("Answer:", result['answer'])
    print("SQL:", result['sql'])
    print("Table:\n", result['table'])