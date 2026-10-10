# 💡 ADEPT-SQL: Comprehensive Explanation of the 6 NLP Innovations

This document provides an in-depth technical explanation of the **6 Core NLP Innovations** implemented in the ADEPT-SQL project. For each idea, it covers:
1. **Why are we doing this? (The Problem)**
2. **What are we doing? (The Solution & Architecture)**
3. **Where is it implemented? (Code References)**
4. **Concrete Demonstration Example**
5. **Academic & Practical Impact**

---

## 📌 Quick Summary Table

| # | Innovation Name | Primary Focus | Problem Solved |
|---|-----------------|---------------|----------------|
| **1** | **Sliding-Window Fuzzy Entity Alignment in SIM** | Robust Entity Recognition | Typos in user queries causing 0 SQL result rows |
| **2** | **Multi-Turn Conversation Context Rewriter** | Conversational Memory | Pronouns and ellipsis in follow-up queries |
| **3** | **Dual-Direction SQL Explanation & Verification** | Neuro-Symbolic Trust | Syntactically correct SQL that fails semantic intent |
| **4** | **Ambiguity Taxonomy & Interactive Clarification** | User-in-the-Loop AI | Arbitrary LLM guessing on underspecified queries |
| **5** | **Schema-Linking Visualizer (Interactive ER Graph)** | Explainable AI (XAI) | Opaque table selection and foreign key joins |
| **6** | **Auto-Visualization Agent** | Intelligent Data Presentation | Raw tabular data dumps without instant visual insights |

---

## 1. Sliding-Window Fuzzy Entity Alignment in SIM (Semantic Input Masking)

### 🔴 Why Are We Doing This? (The Problem)
In real-world database querying, humans frequently make typographical errors (e.g., typing *"Did Blak book Adan Dinnig?"* instead of *"Did Blake book Adan Dinning?"*). 
- **Standard SQL Behavior**: SQL requires strict string matching in `WHERE` clauses. If the query runs `WHERE Customer_Name = 'Blak'`, SQLite returns **0 rows**, giving the false impression that no records exist.
- **Standard LLM Failure**: General LLMs either faithfully copy the typo into the SQL, or guess random spellings without knowing what entities actually exist inside the target database tables.

### 🟢 What Are We Doing? (The Solution)
We augmented the first stage of ADEPT-SQL (**SIM — Semantic Input Masking**) with a sliding-window n-gram fuzzy entity alignment algorithm:
1. **Offline Entity Harvesting**: The system extracts unique column values from registered database tables (`Customers.Customer_Name`, `Stores.Store_Name`, `Performers.Customer_Name`, etc.) and caches them in `backend/term.csv`.
2. **Sliding-Window Candidate Extraction**: When a user inputs a question, the SIM module scans character n-grams and word tokens across the sentence.
3. **Fuzzy String Matching**: For candidate entity tokens, it computes sequence matching similarity against known database entity strings using Levenshtein distance ratios.
4. **Auto-Correction & Masking**: If a match exceeds the similarity threshold ($\ge 0.70$), the typo is corrected to the **canonical database value** before prompt synthesis or vector search.
5. **Badge Notification**: The UI alerts the user showing which entity was auto-aligned:
   `'Blak' ➔ Blake (Customer_Name)` and `'Adan Dinnig' ➔ Adan Dinning (Store_Name)`.

### 📂 File & Code References
- **`user_input_process.py`**: `user_input_init.fuzzy_match_entities()`
- **`backend/term.csv`**: Harvested domain entities cache
- **`run.py`**: SIM preprocessing stage integration

### 🧪 Demo Example
- **User Types**: `Did Blak book Adan Dinnig?`
- **Without SIM**: `SELECT ... WHERE Customer_Name = 'Blak' AND Store_Name = 'Adan Dinnig'` ➔ **0 rows**.
- **With SIM**: Corrects to `Blake` and `Adan Dinning` ➔ **1 row returned** (`Booking_ID: 1`).

---

## 2. Context-Aware Multi-Turn Query Rewriter

### 🔴 Why Are We Doing This? (The Problem)
Natural human conversations are iterative. Users rarely ask self-contained standalone questions in one turn. Instead, they ask follow-ups such as:
- Turn 1: *"List all store names."*
- Turn 2: *"How many are there in total?"* (Referring to stores)
- Turn 3: *"What are their email addresses?"*

Standard Text-to-SQL pipelines are completely **stateless**. If you send *"How many are there in total?"* to a standalone Text-to-SQL system, it has no idea what "there" refers to. It defaults to counting bookings or throws an error.

### 🟢 What Are We Doing? (The Solution)
We implemented a **Context-Aware Query Rewriting Agent** that sits directly between the user interface and the core ADEPT pipeline:
1. **History Tracking**: The system maintains the conversation history in `st.session_state.chat_history` (retaining the last 2 conversational turns).
2. **Anaphora & Ellipsis Resolution**: When a new question arrives, the rewriter inspects whether it contains pronouns (*"he"*, *"she"*, *"it"*, *"they"*, *"their"*) or elliptical phrasing (*"and what about..."*, *"how many in total"*).
3. **Self-Contained Query Synthesis**: The rewriter uses a few-shot prompt (`Prompt_QueryRewriter`) to replace pronouns with the explicit entity subjects from the prior turn.
4. **Pipeline Injection**: The rewritten query is fed into the downstream SIM and CSR modules, ensuring perfect retrieval and zero-shot/few-shot prompt generation.
5. **Transparency**: The UI informs the user: `💬 Understood as: "How many stores are there in total?"`.

### 📂 File & Code References
- **`prompt_templates.py`**: `Prompt_QueryRewriter`
- **`pages/3-StartChat.py`**: `rewrite_query_with_context()`
- **`run.py`**: Transparent pipeline handling

### 🧪 Demo Example
- **Turn 1**: *"List all store names."* ➔ Returns 10 stores.
- **Turn 2**: *"How many are there in total?"* 
- **Rewritten**: *"How many stores are there in total?"* ➔ SQL: `SELECT COUNT(*) FROM Stores` ➔ Result: `10`.

---

## 3. Dual-Direction SQL Logic Breakdown & Semantic Verification (NL ↔ SQL)

### 🔴 Why Are We Doing This? (The Problem)
One of the most dangerous failure modes of LLMs in Text-to-SQL is **silent semantic drift**:
- The model generates SQL that is 100% syntactically valid and executes without throwing any database errors.
- However, the SQL **fails to satisfy the user's intent** (e.g., omitting a crucial `WHERE Status_Code = 'Confirmed'` filter or joining on the wrong foreign key).
- Users looking only at a clean table result assume the query is correct, leading to faulty data interpretation.

### 🟢 What Are We Doing? (The Solution)
We implemented a **Neuro-Symbolic Dual-Direction Verifier** that operates in reverse ($SQL \rightarrow NL$):
1. **Inverse Translation**: Rather than just translating English $\rightarrow$ SQL, the system takes the generated SQL and reverse-translates it into non-technical, step-by-step plain English execution logic.
2. **Constraint Checklist**: The verifier extracts all implicit and explicit constraints from the user's natural language question (e.g., filters, entity scopes, aggregations, sort orders).
3. **Cross-Verification**: It audits the SQL abstract syntax against each constraint:
   - *Entity Filter Alignment*: Checked against `WHERE` clauses.
   - *Column Projection Completeness*: Checked against `SELECT` attributes.
   - *Relational Integrity*: Checked against `JOIN` and `ON` keys.
4. **Interactive UI Card**: Displays an interactive expander card with:
   - Intent Alignment Badge: `[Verified Intent]` or `[Semantic Warning]`
   - Plain-English Query Logic Summary
   - Step-by-Step Execution Plan
   - Constraint alignment tags.

### 📂 File & Code References
- **`prompt_templates.py`**: `Prompt_SQLExplanationAndVerification`
- **`run.py`**: Step 7 `verify_sql_explanation()`
- **`pages/3-StartChat.py`**: `render_sql_explanation_verification()`

### 🧪 Demo Example
- **Question**: *"List all performers and their contact email addresses"*
- **Generated SQL**: `SELECT Customer_Name, Customer_Email_Address FROM Performers ORDER BY Customer_Name`
- **Verification Output**:
  - `Plain-English Summary`: Accesses the Performers table, retrieves the name and email address for each registered performer, and sorts them alphabetically.
  - `Constraints Checked`:
    - Performer entity scope: `Satisfied`
    - Contact email address: `Satisfied`

---

## 4. Ambiguity Taxonomy & Interactive Disambiguation Dialog

### 🔴 Why Are We Doing This? (The Problem)
Natural language queries are frequently underspecified and structurally ambiguous:
- Query: *"Show me the top bookings."*
- What does *"top"* mean?
  - Top by most recent booking date?
  - Top by highest service fee?
  - Top customers with the most bookings?
- **Standard LLM Failure**: Standard systems arbitrarily guess one interpretation without telling the user. If the guess is wrong, the user gets misleading business metrics.

### 🟢 What Are We Doing? (The Solution)
We implemented a **User-in-the-Loop Ambiguity Classifier & Disambiguation Engine**:
1. **Taxonomy Analysis**: An ambiguity detection module checks whether the user query suffers from:
   - *Missing Ranking Criterion* (*"top"*, *"best"*, *"most popular"*)
   - *Missing Aggregation Metric* (*"compare stores"*)
   - *Ambiguous Entity Scope*
2. **Execution Gatekeeper**: If structural ambiguity is detected, the pipeline pauses execution before calling the database.
3. **Interactive Candidate Selection**: The interface presents the user with a radio-button clarification dialog with valid business interpretations:
   - Option A: *Show the most recent bookings by date*
   - Option B: *Which customer has the most bookings?*
   - Option C: *Show all bookings with status confirmed*
4. **Single-Click Execution**: When the user selects their desired intent and clicks **Run Selected Interpretation**, the clarified query is immediately processed.

### 📂 File & Code References
- **`run.py`**: `check_ambiguity()`
- **`prompt_templates.py`**: `Prompt_AmbiguityCheck`
- **`pages/3-StartChat.py`**: Clarification Dialog & session state routing

### 🧪 Demo Example
- **User Query**: *"Show me the top bookings"*
- **Dialog Appears**: *"Identified Ambiguity: Missing Ranking Criterion for top bookings. Please choose the interpretation that matches your intent."*
- **User selects**: *"Show the most recent bookings by date"* ➔ Executes ordered by `Order_Date DESC`.

---

## 5. Schema-Linking Visualizer (Interactive ER Graph)

### 🔴 Why Are We Doing This? (The Problem)
In relational databases with many tables (such as Spider's `cre_Drama_Workshop_Groups` with 14 tables), understanding **Schema Linking** is the hardest part for humans:
- Which tables were selected?
- Why did the model choose `Customers` instead of `Clients`?
- What foreign key joins were navigated to connect `Customers` to `Stores` via `Bookings`?
Viewing raw SQL text (`FROM Bookings B INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID`) does not give evaluators a visual mental model of how the relational schema was traversed.

### 🟢 What Are We Doing? (The Solution)
We implemented an **Interactive Schema-Linking ER Visualizer**:
1. **SQL Abstract Syntax Tree (AST) Parsing**: When SQL is generated, the module uses `sqlglot` to parse tables, columns, and foreign key join conditions used in the query.
2. **Graph Construction**: Using `streamlit-agraph`, it builds an interactive network diagram of the database schema:
   - **Active Tables**: Tables queried in the SQL are highlighted with larger glowing nodes.
   - **Inactive Tables**: Irrelevant tables remain muted.
   - **Active Join Edges**: Foreign key joins utilized in the query are highlighted as thick green directional arrows with foreign key labels (`Customer_ID ➔ Customer_ID`).
3. **Hover Tooltips**: Hovering over any table node displays its columns and primary keys.
4. **Summary Card**: Below the graph, a summary badge explains the tables used and join paths traversed.

### 📂 File & Code References
- **`viz_utils.py`**: `render_schema_linker()`, `_parse_sql_links()`, `SCHEMA_FK_EDGES`
- **`pages/3-StartChat.py`**: Embedded under every query result tab

### 🧪 Demo Example
- **Query**: *"How many bookings does each customer have?"*
- **Visualizer Output**:
  - Highlights `Customers` and `Bookings` nodes in vibrant green.
  - Highlights the FK join edge: `Customers.Customer_ID = Bookings.Customer_ID`.
  - Displays summary: *"Tables: Bookings, Customers | Joins: Bookings ↔ Customers (Customer_ID)"*.

---

## 6. Auto-Visualization Agent

### 🔴 Why Are We Doing This? (The Problem)
Text-to-SQL applications traditionally stop once the raw table is printed. However:
- A single count (e.g., `10`) shouldn't be buried inside a 1-row table.
- A breakdown of bookings per store is far easier to understand as a **bar chart** than scanning 10 rows of numbers.
- Forcing the user to manually click chart buttons or write code to visualize data defeats the purpose of natural language data exploration.

### 🟢 What Are We Doing? (The Solution)
We built an **Heuristic Auto-Visualization Agent** that dynamically inspects the execution DataFrame:
1. **DataFrame Heuristics**:
   - **Single Scalar Value** ($1 \times 1$ numerical): Rendered as a prominent **Big Metric KPI Card**.
   - **1 Categorical + 1 Numerical Column**: Rendered as an interactive **Horizontal Bar Chart** (via Plotly Express).
   - **1 Temporal/Date + 1 Numerical Column**: Rendered as a **Line Chart** tracking trends over time.
   - **Multi-Column or Pure Text**: Rendered cleanly as a standard data table without forcing an invalid chart.
2. **Chart Override Control**: Users always have a select box to manually toggle chart types (`Bar`, `Line`, `Metric`, `Table`).
3. **Seamless Dark Theme**: All Plotly figures are styled to seamlessly match the application's dark design system.

### 📂 File & Code References
- **`viz_utils.py`**: `detect_best_chart()`, `render_auto_visualization()`
- **`pages/3-StartChat.py`**: Auto-renders beneath every successful execution table

### 🧪 Demo Example
- **Query**: *"How many bookings does each customer have?"*
- **Table Returned**: 15 rows (`Customer_Name`, `booking_count`).
- **Auto-Viz Agent**: Automatically detects 1 categorical (`Customer_Name`) + 1 numeric (`booking_count`) ➔ Renders a styled **Plotly Horizontal Bar Chart** showing customers ranked by bookings.

---

## 🎓 Summary of Technical Synergy

These 6 ideas work together as a unified, robust multi-stage system:

```
User Input
    │
    ▼
[Idea 2: Multi-Turn Context Rewriter]  ──► Resolves pronouns & conversational memory
    │
    ▼
[Idea 1: SIM Fuzzy Entity Alignment]   ──► Fixes customer & store name typos
    │
    ▼
[Idea 4: Ambiguity Classifier]         ──► Halts & asks user if query is ambiguous
    │
    ▼
[ADEPT CSR & APC Prompt Synthesis]     ──► Retrieves exemplars & constructs prompt
    │
    ▼
[Neural LLM SQL Generation]            ──► Model A (Primary) & Model B (Groq / Comparison)
    │
    ▼
[Execution against SQLite]             ──► Returns Result DataFrame
    │
    ├──► [Idea 3: Dual-Direction Verifier]   ──► Audits SQL logic & constraints in NL
    ├──► [Idea 5: Schema-Linking Visualizer] ──► Shows tables & FK join graph in 2D
    └──► [Idea 6: Auto-Visualization Agent]  ──► Plots bar/line/metric charts automatically
```

With this architecture, ADEPT-SQL is not merely a prompt wrapper, but a **resilient, explainable, and production-grade conversational database agent**.
