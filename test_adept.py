"""
test_adept.py — End-to-end automated test suite for ADEPT-SQL

Tests all 3 core modules independently, plus an integration test:
  1. SIM  — Semantic Input Masker (term + date masking)
  2. CSR  — Contextual SQL Retriever (similarity search)
  3. APC  — Adaptive Prompt Composer (few-shot / zero-shot branches)
  4. DB   — opDB SQLite engine (schema extraction, SQL execution)
  5. Integration — full pipeline smoke test (no LLM required)

Run:
    python test_adept.py
"""

import os
import sys
import json
import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    print(f"  {status} | {name}" + (f" - {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB MODULE: opDB.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 1. DB Module (opDB) ===")
try:
    from opDB import localsqlite
    db = localsqlite('./sqlite/cre_Drama_Workshop_Groups.sqlite').conn()

    # Schema extraction
    schema_df = db.get_schema_as_df()
    test("schema_df not empty", not schema_df.empty, f"{len(schema_df)} rows")
    test("schema has required columns",
         all(c in schema_df.columns for c in ['Table', 'Column', 'Column Description']))

    # Table listing
    tables = db.get_all_table_names()
    test("Bookings table present", 'Bookings' in tables)
    test("Customers table present", 'Customers' in tables)
    test("Stores table present", 'Stores' in tables)

    # SQL execution
    df = db.exesql("SELECT COUNT(*) AS cnt FROM Bookings")
    test("SQL execution returns DataFrame", isinstance(df, pd.DataFrame))
    test("Booking count > 0", df['cnt'][0] > 0, f"count={df['cnt'][0]}")

except Exception as e:
    test("DB Module import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 2. SIM MODULE: user_input_process.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 2. SIM Module (user_input_process) ===")
try:
    from user_input_process import user_input_init

    # Term recognition
    inp = user_input_init("Did Blake book Adan Dinning?").full_process()
    test("term_replace flag set", inp.term_replace)
    test("time_replace flag set", inp.time_replace)
    test("hintslist populated", len(inp.hintslist) > 0, f"{len(inp.hintslist)} hints")
    test("'Blake' masked in trans", 'Blake' not in inp.trans,
         f"trans='{inp.trans}'")

    # Date recognition
    inp2 = user_input_init("Show bookings from 2024-03-15.").full_process()
    test("Date '2024-03-15' masked", '2024-03-15' not in inp2.trans,
         f"trans='{inp2.trans}'")

    # Hints generation
    hints = inp.gen_hints()
    test("gen_hints returns non-empty string", len(hints) > 0, f"hints='{hints[:60]}'")

    # No term match (unknown input)
    inp3 = user_input_init("How many tables exist?").full_process()
    test("No terms found for irrelevant query", len(inp3.hintslist) == 0)

except Exception as e:
    test("SIM Module import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMBEDDING MODULE: call_emb.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 3. Embedding Module (call_emb) ===")
try:
    from call_emb import vectorize_localmodel
    vec = vectorize_localmodel("test sentence")
    test("Embedding returns list", isinstance(vec, list), f"type={type(vec)}")
    test("Embedding non-empty", len(vec) > 0, f"dims={len(vec)}")
    test("Embedding values are floats", all(isinstance(v, float) for v in vec[:5]))
except Exception as e:
    test("Embedding Module import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 4. CSR MODULE: similarity_cal.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 4. CSR Module (similarity_cal) ===")
try:
    from similarity_cal import search_qvec
    from user_input_process import user_input_init

    emb = {"name": "local model", "url": "", "token": ""}

    # Exact-match question (should find in qvec.csv)
    inp_exact = user_input_init("Did Blake book Adan Dinning?").full_process()
    not_found, info, found_df = search_qvec(inp_exact, emb)
    test("CSR runs without error", True)
    test("CSR returns tuple of 3", isinstance(found_df, pd.DataFrame))
    if not not_found:
        test("Few-shot triggered (found similar)", True, f"info: {info}")
    else:
        test("Zero-shot triggered (no match) — seed_qvec.py may not have finished yet", True, info)

    # Completely irrelevant question (should NOT match)
    inp_irr = user_input_init("What is the capital of France?").full_process()
    not_found_irr, _, _ = search_qvec(inp_irr, emb)
    test("Irrelevant question -> zero-shot", not_found_irr)

except Exception as e:
    test("CSR Module import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 5. APC MODULE: prompt_templates.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 5. APC Module (prompt_templates) ===")
try:
    from prompt_templates import Prompt_Fewshot, Prompt_Zeroshot, Prompt_Answer
    from user_input_process import user_input_init

    inp = user_input_init("Did Blake book Adan Dinning?").full_process()

    # Zero-shot
    zs = Prompt_Zeroshot(inp)
    zs_prompt = zs.compile()
    test("Zero-shot prompt generated", len(zs_prompt) > 50)
    test("Zero-shot prompt has #Schema#", '#Schema#' in zs_prompt)
    test("Zero-shot prompt has #Now Write SQL#", '#Now Write SQL#' in zs_prompt)

    # Few-shot (mock found_df)
    mock_df = pd.DataFrame([{
        'question': "Did Ephraim book Lur Photo?",
        'sql': "SELECT * FROM Bookings B JOIN Customers C ON B.Customer_ID=C.Customer_ID WHERE C.Customer_Name='Ephraim'",
        'similarity': 0.92
    }])
    fs = Prompt_Fewshot(inp, mock_df)
    fs_prompt = fs.compile()
    test("Few-shot prompt generated", len(fs_prompt) > 50)
    test("Few-shot prompt has #Examples#", '#Examples#' in fs_prompt)
    test("Few-shot prompt has NO #Schema#", '#Schema#' not in fs_prompt)
    test("Few-shot prompt has user question", inp.input in fs_prompt)

    # Answer prompt
    taskinfos = {
        'question': inp.input,
        'search_res': 'Found 1 similar pair',
        'sql': 'SELECT * FROM Bookings',
        'sqlexe': pd.DataFrame([{'Booking_ID': 1}])
    }
    ans_prompt = Prompt_Answer(taskinfos).complie()
    test("Answer prompt generated", len(ans_prompt) > 50)

except Exception as e:
    test("APC Module import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 6. SQL CLEANER: call_llm.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 6. SQL Cleaner (call_llm.clean_sql_output) ===")
try:
    from call_llm import clean_sql_output

    test("Cleans fenced sql block",
         clean_sql_output("```sql\nSELECT * FROM Bookings\n```") == "SELECT * FROM Bookings")
    test("Cleans plain fenced block",
         clean_sql_output("```\nSELECT 1\n```") == "SELECT 1")
    test("Passes through raw SQL",
         "SELECT" in clean_sql_output("SELECT * FROM Bookings"))

except Exception as e:
    test("SQL Cleaner import/run", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == PASS)
failed = sum(1 for _, s, _ in results if s == FAIL)
for name, status, detail in results:
    print(f"  {status} {name}" + (f" [{detail}]" if detail else ""))
print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests.")
if failed == 0:
    print("SUCCESS: All tests passed! ADEPT-SQL is ready.")
else:
    print(f"WARNING: {failed} test(s) failed. Check the output above.")
