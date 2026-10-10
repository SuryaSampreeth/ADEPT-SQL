# 💡 6 Ideas Explanation — ADEPT-SQL

> **Project**: ADEPT-SQL (English to SQL Conversion)  
> **Topic**: Detailed Explanation of the 6 Core NLP Innovations  
> **Core Question**: What are we doing, and why are we doing it?

---

## 📋 Executive Overview

In standard Text-to-SQL systems, an LLM is directly asked to convert a user question into SQL. In practice, this fragile approach fails whenever users make spelling mistakes, ask follow-up questions with pronouns, write ambiguous prompts, or receive complex results they cannot easily verify or visualize.

To solve this, we implemented **6 distinct NLP & System Innovations** around the ADEPT-SQL pipeline:

| # | Innovation Name | What Are We Doing? | Why Are We Doing It? |
|---|-----------------|--------------------|----------------------|
| **1** | **Sliding-Window Fuzzy Entity Alignment in SIM** | Auto-correcting misspelled entity names (customers, stores, performers) using database vocabulary before generating SQL. | Typos in natural language cause strict SQL `WHERE` clauses to return 0 rows. |
| **2** | **Multi-Turn Conversation Context Rewriter** | Rewriting follow-up questions containing pronouns (*"them"*, *"there"*, *"their"*) into self-contained questions using past conversation turns. | Standard Text-to-SQL is completely stateless and fails when users ask natural follow-up questions. |
| **3** | **Dual-Direction SQL Explanation & Verification** | Reverse-translating generated SQL back into plain English steps and auditing them against the user's intent. | LLMs frequently generate syntactically valid SQL that produces incorrect answers without throwing errors (silent semantic drift). |
| **4** | **Ambiguity Taxonomy & Interactive Clarification** | Detecting underspecified queries (*"top bookings"*, *"best stores"*) and presenting a 1-click clarification dialog before running SQL. | Prevents LLMs from making arbitrary guesses that give misleading business insights. |
| **5** | **Schema-Linking Visualizer (Interactive ER Graph)** | Visualizing database tables and foreign-key join paths in an interactive graph with highlighted active paths. | Makes relational reasoning explainable and transparent instead of hiding joins inside complex SQL strings. |
| **6** | **Auto-Visualization Agent** | Inspecting query results and automatically rendering KPIs, bar charts, or line charts without manual user effort. | Raw database tables are difficult to interpret at a glance; instant visual insights enhance user decision-making. |

---

## 1. Sliding-Window Fuzzy Entity Alignment (SIM)

### ❓ Why Are We Doing It? (The Problem)
When real users type queries into a database search box, typos and phonetic misspellings are extremely common:
- A user types: `"Did Blak book Adan Dinnig?"` instead of `"Did Blake book Adan Dinning?"`.
- In standard SQL, queries use strict string matching:  
  `WHERE Customer_Name = 'Blak' AND Store_Name = 'Adan Dinnig'`
- **The Result**: The query returns **0 rows**. The user is misled into thinking no such booking exists.
- General LLMs either copy the typo directly into the SQL or hallucinate spellings without knowing what records actually exist in the database.

### 🛠️ What Are We Doing? (The Solution)
We augmented the **Semantic Input Masking (SIM)** module with an offline entity harvester and a runtime fuzzy matching engine:
1. **Harvesting Entities**: Unique values from key columns (`Customer_Name`, `Store_Name`, `Performer_Name`) are extracted and stored in `backend/term.csv`.
2. **Sliding-Window Scanning**: When a user inputs text, the system scans word tokens and n-grams across the input.
3. **Similarity Scoring**: Candidate tokens are compared against harvested database values using Levenshtein distance similarity.
4. **Canonical Replacement**: Any token matching with $\ge 70\%$ similarity is replaced with the database's canonical string before the prompt is sent to the LLM.
5. **User Feedback**: The UI displays a notification showing the auto-correction (e.g., `'Blak' ➔ Blake`).

- **Key Files**: [user_input_process.py](file:///c:/nlp_case_study/user_input_process.py), [backend/term.csv](file:///c:/nlp_case_study/backend/term.csv), [run.py](file:///c:/nlp_case_study/run.py)

---

## 2. Multi-Turn Conversation Context Rewriter

### ❓ Why Are We Doing It? (The Problem)
Human conversations are inherently iterative and rely on conversational context:
- **Turn 1**: *"List all store names."* ➔ (Model returns 10 stores)
- **Turn 2**: *"How many are there in total?"*
- **Turn 3**: *"What are their email addresses?"*

Standard Text-to-SQL models are completely **stateless**. When given *"How many are there in total?"*, the model has no idea what *"there"* refers to. It either throws an error or guesses an unrelated table (like counting bookings instead of stores).

### 🛠️ What Are We Doing? (The Solution)
We built a **Context-Aware Query Rewriter** that preprocesses user inputs using conversation history:
1. **Turn History Memory**: The app tracks recent questions and responses in `st.session_state.chat_history`.
2. **Anaphora & Ellipsis Detection**: Identifies pronouns (*"he"*, *"she"*, *"it"*, *"they"*, *"their"*) and elliptical follow-ups (*"how many in total"*, *"and what about..."*).
3. **Query Expansion**: Using a specialized rewriting prompt (`Prompt_QueryRewriter`), it resolves pronouns to explicit entities from the prior turn.
4. **Execution**: The rewritten standalone query (*"How many stores are there in total?"*) is passed into the Text-to-SQL engine.
5. **Transparency**: The user sees: `💬 Understood as: "How many stores are there in total?"`.

- **Key Files**: [prompt_templates.py](file:///c:/nlp_case_study/prompt_templates.py), [pages/3-StartChat.py](file:///c:/nlp_case_study/pages/3-StartChat.py)

---

## 3. Dual-Direction SQL Logic Breakdown & Semantic Verification

### ❓ Why Are We Doing It? (The Problem)
One of the most dangerous risks of AI-generated SQL is **silent semantic drift**:
- The model generates SQL that is 100% syntactically valid and executes without throwing an error.
- However, the query **fails the user's intent** (for instance, omitting an essential filter like `WHERE Status_Code = 'Confirmed'` or grouping by the wrong column).
- Non-technical users cannot read raw SQL and assume the returned table is accurate, leading to incorrect business decisions.

### 🛠️ What Are We Doing? (The Solution)
We created a **Dual-Direction Neuro-Symbolic Verifier** that operates in reverse ($SQL \rightarrow NL$):
1. **Reverse Translation**: The generated SQL is converted into step-by-step, plain-English execution logic.
2. **Constraint Checklist**: The verifier extracts all constraints from the user's original question (filters, sorting, aggregations, entities).
3. **Audit Against SQL**: The verifier checks whether the SQL's `SELECT`, `WHERE`, `JOIN`, and `ORDER BY` clauses satisfy every extracted constraint.
4. **Interactive Explanation Card**: Displays an expandable UI card showing:
   - Intent status: `[Verified Intent]` or `[Semantic Warning]`
   - Plain-English logic summary
   - Step-by-step execution breakdown
   - Checklist of verified constraints

- **Key Files**: [prompt_templates.py](file:///c:/nlp_case_study/prompt_templates.py), [run.py](file:///c:/nlp_case_study/run.py), [pages/3-StartChat.py](file:///c:/nlp_case_study/pages/3-StartChat.py)

---

## 4. Ambiguity Taxonomy & Interactive Clarification Dialog

### ❓ Why Are We Doing It? (The Problem)
Real-world natural language queries are often underspecified and structurally ambiguous:
- Query: *"Show me the top bookings."*
- What does *"top"* mean?
  - Most recent bookings by date?
  - Highest payment or service fee?
  - Customers with the highest number of bookings?
- Standard AI models pick one arbitrary interpretation at random without telling the user, which frequently leads to inaccurate conclusions.

### 🛠️ What Are We Doing? (The Solution)
We introduced a **User-in-the-Loop Clarification Engine**:
1. **Ambiguity Classification**: An ambiguity analyzer checks for missing ranking criteria (*"top"*, *"best"*), ambiguous aggregations, or unclear entity scopes.
2. **Execution Pause**: When ambiguity is detected, query execution is paused before accessing the database.
3. **Clarification Dialog**: The user is presented with a clear radio-button selection of concrete interpretations:
   - *Option A: Show the most recent bookings by date*
   - *Option B: Which customer has the most bookings?*
   - *Option C: Show all bookings with status confirmed*
4. **Single-Click Run**: The user selects their intended meaning and clicks **Run Selected Interpretation**, executing the exact query they intended.

- **Key Files**: [run.py](file:///c:/nlp_case_study/run.py), [prompt_templates.py](file:///c:/nlp_case_study/prompt_templates.py), [pages/3-StartChat.py](file:///c:/nlp_case_study/pages/3-StartChat.py)

---

## 5. Schema-Linking Visualizer (Interactive ER Graph)

### ❓ Why Are We Doing It? (The Problem)
In relational databases with many interconnected tables (like the 14-table Drama Workshop schema), schema linking is opaque:
- Users cannot see which tables were selected or why.
- Foreign-key join paths across intermediate junction tables are hidden inside SQL code.
- Evaluators cannot quickly assess whether the model navigated the relational schema correctly.

### 🛠️ What Are We Doing? (The Solution)
We implemented an **Interactive Schema-Linking ER Visualizer**:
1. **AST Parsing**: Uses `sqlglot` to parse generated SQL queries into tables, columns, and foreign keys.
2. **Interactive Graph**: Renders a network diagram via `streamlit-agraph`:
   - Active tables used in the query glow with prominent green borders.
   - Unused tables are displayed with muted styling.
   - Active foreign-key join relationships appear as bold directional arrows labeled with join keys (`Customer_ID ➔ Customer_ID`).
3. **Tooltips & Summary**: Hovering over tables shows their column definitions, and a summary card details the tables and joins traversed.

- **Key Files**: [viz_utils.py](file:///c:/nlp_case_study/viz_utils.py), [pages/3-StartChat.py](file:///c:/nlp_case_study/pages/3-StartChat.py)

---

## 6. Auto-Visualization Agent

### ❓ Why Are We Doing It? (The Problem)
Standard database tools return raw data tables:
- A single number (e.g., total count: `10`) gets trapped inside a 1-row table.
- A distribution across categories is difficult to digest in tabular format.
- Forcing users to export data to Excel or write plotting code slows down decision-making.

### 🛠️ What Are We Doing? (The Solution)
We built an **Heuristic Auto-Visualization Engine** that automatically determines the best visual representation:
1. **Data Shape Heuristics**:
   - **$1 \times 1$ Number**: Renders an executive **KPI Metric Card**.
   - **1 Category + 1 Number**: Automatically renders an interactive **Plotly Horizontal Bar Chart**.
   - **1 Date/Time + 1 Number**: Renders a **Trend Line Chart**.
   - **Multi-column Table**: Renders an interactive data table.
2. **User Flexibility**: Users can switch chart formats via a dropdown selector anytime.
3. **Consistent Theme**: Visuals automatically inherit the dark slate color palette.

- **Key Files**: [viz_utils.py](file:///c:/nlp_case_study/viz_utils.py), [pages/3-StartChat.py](file:///c:/nlp_case_study/pages/3-StartChat.py)

---

## 🔄 How the 6 Ideas Work Together

The 6 innovations operate as a coordinated pipeline:

```
                  User Natural Language Query
                              │
                              ▼
        [Idea 2: Multi-Turn Context Rewriter]
          Resolves pronouns & past turn context
                              │
                              ▼
        [Idea 1: SIM Fuzzy Entity Alignment]
          Corrects entity spelling errors (customers, stores)
                              │
                              ▼
        [Idea 4: Ambiguity Classifier]
          Pauses & asks user if query is ambiguous
                              │
                              ▼
             [ADEPT-SQL Core Generation Engine]
          Retrieves database schema & generates SQL
                              │
                              ▼
                  [SQLite Database Execution]
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
[Idea 3: Verifier]   [Idea 5: Schema Graph]  [Idea 6: Auto-Viz]
Audits SQL logic      Shows active tables &   Plots KPI cards,
in plain English      foreign-key join paths  bar or line charts
```

Together, these 6 innovations transform basic Text-to-SQL into a **reliable, conversational, transparent, and user-friendly database assistant**.
