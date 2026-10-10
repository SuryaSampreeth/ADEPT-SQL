from call_llm import callLLM
from user_input_process import user_input_init
from similarity_cal import sim_cal_obj
import pandas as pd
from opDB import localsqlite

def run_test(q):
    print(f"\n============================================================")
    print(f"TEST: '{q}'")
    print(f"============================================================\n")
    
    print("====== [ADEPT-SQL] Step 1: SIM ======")
    processed = user_input_init(q).full_process()
    print("Masked question:", processed.trans)

    print("\n====== [ADEPT-SQL] Step 2: CSR ======")
    sim_cal_obj = sim_cal(processed)
    try:
        sim_cal_obj.cal_sim()
        found_df = sim_cal_obj.found_df
        print(f"[CSR] Result: {len(found_df)} similar Question-SQL pair(s) found")
        if not found_df.empty:
            print(found_df[['question', 'similarity']])
    except Exception as e:
        print("[CSR] Error:", e)
        found_df = pd.DataFrame()

    print("\n====== [ADEPT-SQL] Step 3: APC ======")
    from prompt_templates import Prompt_Zeroshot, Prompt_Fewshot
    if found_df.empty:
        print("[APC] Branch: ZERO-SHOT")
        prompt = Prompt_Zeroshot(processed).compile()
    else:
        print("[APC] Branch: FEW-SHOT")
        prompt = Prompt_Fewshot(processed, found_df).compile()

    print("\n====== [ADEPT-SQL] Step 4: LLM -> SQL ======")
    llmapi = {'url': 'demo', 'token': 'demo', 'name': 'Demo Mode (Offline)'}
    sql_raw = callLLM(llmapi).init_prompt('system', prompt).call().get_response_content()
    print("[SQL] Generated:\n" + sql_raw)

    print("\n====== [ADEPT-SQL] Step 5: SQL Execution ======")
    db_conn = localsqlite({'sqlite_path': './sqlite/cre_Drama_Workshop_Groups.sqlite'})
    try:
        db_conn.connect()
        df = db_conn.exec(sql_raw)
        print(f"[SQL] Executed successfully. Rows returned: {len(df)}")
        print(df)
    except Exception as e:
        print("[SQL] Error:", e)

run_test("did blake book sherry photo")
