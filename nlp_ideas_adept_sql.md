# 🧠 Five NLP Enhancement Ideas for ADEPT-SQL
> All ideas verified against actual project code. Each idea maps directly to existing files.

---

## Project Quick Summary (What We Are Working With)

| Module | File | What It Does |
|---|---|---|
| **SIM** — Semantic Input Masker | `user_input_process.py` | Masks entity names & dates in user query. e.g. "Did **Blake** book **Adan Dinning**?" → "Did **[customer name]** book **[store name]**?" |
| **CSR** — Contextual SQL Retriever | `similarity_cal.py` + `call_emb.py` | Embeds masked query, searches `backend/qvec.csv` via cosine similarity to find similar historical Q-SQL pairs |
| **APC** — Adaptive Prompt Composer | `prompt_templates.py` | If similarity > 0.85 → **Few-Shot** (examples + no schema). Else → **Zero-Shot** (dynamic schema selection) |
| **LLM** | `call_llm.py` | Calls OpenAI/DeepSeek/Ollama API or offline mock to generate SQL |
| **DB** | `opDB.py` | Runs the SQL against the SQLite database |
| **UI** | `pages/3-StartChat.py` | Streamlit chat interface, also has dual-model comparison mode |

---

## Idea 1 — Fuzzy Typo-Tolerant Entity Matching in SIM

### What is the Problem Right Now?

In [`user_input_process.py`](file:///c:/nlp_case_study/user_input_process.py) the `term_recognition()` method (lines 66–115) does **exact substring matching**:

```python
if term_lower in trans_lower:   # ← only works if the user types exactly right
```

It checks if the term from `backend/term.csv` (e.g. `"Blake"`, `"Adan Dinning"`) appears **word-for-word** in the user's question. If the user types a typo:

- *"Did **Blak** book **Adan Dining**?"* → SIM finds nothing → CSR gets `0.0` similarity → Zero-Shot kicks in with a wrong schema → LLM produces bad SQL.

### What Will We Do?

Replace exact matching with **fuzzy string matching** using the `rapidfuzz` library (already installable via pip).

The logic:
1. Tokenize the user's question into words/bigrams/trigrams.
2. For each token, compare it against every term in `backend/term.csv` using **fuzzy ratio score** (Levenshtein distance ratio).
3. If a token scores above **80%** similarity to a known term — treat it as that term, mask it, and add the hint.

### What Changes in the Code?

- **File to change**: [`user_input_process.py`](file:///c:/nlp_case_study/user_input_process.py) — only `term_recognition()` method.
- **File to change**: [`requirements.txt`](file:///c:/nlp_case_study/requirements.txt) — add `rapidfuzz`.
- **Zero changes** to CSR, APC, LLM, or UI.

### What the User Will See?

- *"Did Blak book Adan Dining?"* will now correctly get masked → CSR will find the right similar query → Few-Shot branch will produce the correct SQL.
- The UI will show the corrected entity hint: `"[Blak] fuzzy-matched to [Blake] (Customer Name)"`.

### NLP Concept Used

**Approximate String Matching / Edit Distance** — the same technique used in spell-checkers, search engines, and NER disambiguation.

---

## Idea 2 — Multi-Turn Conversation Memory (Context-Aware Follow-Up Questions)

### What is the Problem Right Now?

In [`pages/3-StartChat.py`](file:///c:/nlp_case_study/pages/3-StartChat.py) (line 74–175), every user question is sent directly and independently to the `adept()` function in `run.py`. There is no memory of what was asked before.

If a user has this chat:
- Turn 1: *"Which customer has the most bookings?"* → Answer: **"Samson with 3 bookings."**
- Turn 2: *"What stores did he visit?"* → **FAILS** because "he" has no meaning without Turn 1.

The current system treats Turn 2 as a fresh, unrelated question.

### What Will We Do?

Add a **Conversation History Buffer** in `st.session_state`. Before any new question enters the ADEPT pipeline, pass the last 2 turns + the new question to a **Query Rewriter prompt** via the LLM. The LLM rewrites the follow-up into a self-contained question.

Flow:
```
Turn 2 input: "What stores did he visit?"
  ↓ [Query Rewriter Prompt]
  ↓ LLM receives: [History: "Samson has most bookings"] + "What stores did he visit?"
  ↓ Rewrites to: "What stores did Samson visit?"
  ↓ [Rewritten question enters the full ADEPT pipeline normally]
```

### What Changes in the Code?

- **File to change**: [`pages/3-StartChat.py`](file:///c:/nlp_case_study/pages/3-StartChat.py) — add session history list, add rewrite step before calling `adept()`.
- **File to change**: [`prompt_templates.py`](file:///c:/nlp_case_study/prompt_templates.py) — add a new `Prompt_QueryRewriter` class.
- **Zero changes** to SIM, CSR, APC, DB modules.

### What the User Will See?

- Real multi-turn conversation. Users can ask *"And what about him?", "What was the date?", "Give me more details"* naturally.
- The UI will show the rewritten question in a small caption so the user can see what the system understood.

### NLP Concept Used

**Co-reference Resolution & Dialogue Context** — the core NLP skill in any conversational AI / chatbot system (same as how ChatGPT remembers context across turns).

---

## Idea 3 — SQL Self-Correction Loop (Auto-Retry on Error)

### What is the Problem Right Now?

In [`run.py`](file:///c:/nlp_case_study/run.py) lines 82–96:

```python
try:
    resdf = dbconn.exesql(sql)
except Exception as e:
    sql_error = str(e)   # ← error is logged, user gets nothing
```

When the generated SQL has a bug (wrong table alias, missing GROUP BY, SQLite syntax nuance), the system **gives up immediately** and returns an error to the user. The user has to rephrase and try again manually.

### What Will We Do?

When SQL execution fails, catch the specific database error and immediately send a **Self-Correction Prompt** back to the LLM:

```
"You wrote this SQL: <broken SQL>
The database returned this error: <error message>
The relevant table schema is: <schema>
Fix the SQL so it runs correctly. Output ONLY valid SQL."
```

Max **2 retry attempts** before truly giving up.

### What Changes in the Code?

- **File to change**: [`run.py`](file:///c:/nlp_case_study/run.py) — wrap Step 5 execution inside a retry loop.
- **File to change**: [`prompt_templates.py`](file:///c:/nlp_case_study/prompt_templates.py) — add `Prompt_SelfCorrection` class.
- **Zero changes** to SIM, CSR, APC, UI, or embedding modules.

### What the User Will See?

- Instead of an error message, the system will silently retry and show the corrected SQL + result.
- On the UI (`pages/3-StartChat.py`), a small badge like `"⚡ Auto-corrected (1 retry)"` will show when a retry was needed.
- On the Evaluation page (`pages/4-Evaluation.py`), benchmark accuracy will visibly improve.

### NLP Concept Used

**LLM Self-Reflection / Iterative Reasoning** — a widely studied NLP technique where the model uses its own output + error feedback to produce a better result. Similar to "chain-of-thought self-correction" in research papers.

---

## Idea 4 — Query Intent Ambiguity Detection & Clarification

### What is the Problem Right Now?

When a user asks vague questions like:
- *"Show me the top bookings"* — Top by what? Count? Date? Store rating?
- *"Get the best customer"* — Best by number of bookings? Alphabetically?

The LLM **makes a silent assumption** and generates SQL based on that assumption. There is no way for the user to know the system guessed wrong until they see an unexpected result.

### What Will We Do?

Add an **Ambiguity Detection step** right after SIM (before CSR). Send the masked question to the LLM with a short classification prompt:

```
"Is this question ambiguous? Does it have multiple valid SQL interpretations?
If YES: list 2–3 specific interpretations as short options.
If NO: just say CLEAR."
```

- If the LLM says **CLEAR** → continue the normal ADEPT pipeline.
- If the LLM detects **ambiguity** → pause, show the user clickable clarification options in the Streamlit UI (radio buttons). The user picks one, and that refined question runs through the pipeline.

### What Changes in the Code?

- **File to change**: [`run.py`](file:///c:/nlp_case_study/run.py) — add optional pre-check step that returns `{"ambiguous": True, "options": [...]}`.
- **File to change**: [`pages/3-StartChat.py`](file:///c:/nlp_case_study/pages/3-StartChat.py) — handle ambiguous response by showing radio buttons before executing.
- **File to change**: [`prompt_templates.py`](file:///c:/nlp_case_study/prompt_templates.py) — add `Prompt_AmbiguityCheck` class.

### What the User Will See?

User types: *"Show me the top bookings"*

The chatbot responds (without running SQL yet):
> 🤔 **I want to make sure I understand you correctly. Did you mean:**
> - ○ The booking with the **highest Booking ID**
> - ○ The customer with the **most number of bookings**
> - ○ The **most recently made** booking

User picks one → SQL runs correctly for that specific intent.

### NLP Concept Used

**Intent Disambiguation & Pragmatic NLU** — a standard NLP technique in voice assistants and chatbots. Used in Siri, Alexa, and Google Assistant to resolve vague commands before acting on them.

---

## Idea 5 — Hybrid BM25 + Dense Retrieval for Better Few-Shot Example Selection

### What is the Problem Right Now?

In [`similarity_cal.py`](file:///c:/nlp_case_study/similarity_cal.py) the CSR module uses **only cosine similarity between sentence embeddings** to find the best matching historical Q-SQL pair from `backend/qvec.csv`.

Sentence embeddings are great for semantic meaning but **weak on specific structural keywords**. For example:
- User asks: *"Which customer has the **most** bookings?"*
- A stored question: *"List all customers and their booking **count**"*

Both sound semantically close in embedding space — but the SQL structures are very different (`ORDER BY ... LIMIT 1` vs `GROUP BY`). The embedding-only approach can pick the wrong example for Few-Shot.

### What Will We Do?

Replace the pure cosine similarity with a **hybrid scoring approach**:

1. **Dense score** (existing): cosine similarity from `all-MiniLM-L6-v2` embeddings (already in the code).
2. **Sparse score (new)**: BM25 keyword relevance score using `rank-bm25` library — catches structural SQL keywords like *"count", "most", "average", "between", "total"*.
3. **Combined score**: `final_score = 0.6 × dense_score + 0.4 × bm25_score`
4. Rank all candidate Q-SQL pairs by combined score and use the top matches.

### What Changes in the Code?

- **File to change**: [`similarity_cal.py`](file:///c:/nlp_case_study/similarity_cal.py) — update `search_qvec()` to compute BM25 scores alongside cosine, combine them.
- **File to change**: [`requirements.txt`](file:///c:/nlp_case_study/requirements.txt) — add `rank-bm25`.
- **Zero changes** to SIM, APC, LLM, DB, or UI.

### What the User Will See?

- More accurate SQL generation for aggregation queries (*"most", "average", "total", "top N"*) because the CSR picks structurally better Few-Shot examples.
- On the Evaluation page (`pages/4-Evaluation.py`), the benchmark Execution Match score should improve — especially on Questions 2 and 4 in the benchmark which involve aggregation.

### NLP Concept Used

**Hybrid Information Retrieval** — combining lexical (keyword/BM25) and semantic (dense vector) signals. This is the same technique used in modern search engines (Elasticsearch hybrid mode, RAG pipelines) and is a fundamental NLP retrieval concept.

---

## Summary Table

| # | Idea | Problem It Fixes | Files Changed | Extra Library Needed | NLP Concept |
|---|---|---|---|---|---|
| **1** | Fuzzy Entity Matching | Typos in customer/store names break SIM entirely | `user_input_process.py`, `requirements.txt` | `rapidfuzz` | Approximate String Matching |
| **2** | Multi-Turn Memory | Follow-up questions like "what about him?" fail | `3-StartChat.py`, `prompt_templates.py` | None | Co-reference Resolution / Dialogue Context |
| **3** | SQL Self-Correction Loop | SQL errors show as blank result, user must retry manually | `run.py`, `prompt_templates.py` | None | LLM Self-Reflection / Iterative Reasoning |
| **4** | Ambiguity Clarification | Vague queries produce wrong SQL silently | `run.py`, `3-StartChat.py`, `prompt_templates.py` | None | Intent Disambiguation |
| **5** | Hybrid BM25 + Dense CSR | Wrong Few-Shot examples chosen for aggregation queries | `similarity_cal.py`, `requirements.txt` | `rank-bm25` | Hybrid Information Retrieval |

> [!NOTE]
> Ideas 2, 3, and 4 require **no new libraries** — they only use the LLM already configured in the project.
> Ideas 1 and 5 require one small pip install each (`rapidfuzz` and `rank-bm25`).

> [!IMPORTANT]
> All 5 ideas are **directly wired into the existing ADEPT-SQL pipeline** — they are extensions, not replacements. The existing SIM → CSR → APC → LLM → DB flow is preserved in all cases.
