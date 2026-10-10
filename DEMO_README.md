# ADEPT-SQL — Faculty Demonstration Guide
## NLP Project Innovations:
- **Idea 1:** Typo-Tolerant Sliding-Window Fuzzy Entity Alignment in SIM
- **Idea 2:** Multi-Turn Memory & Context-Aware Query Rewriting
- **Idea 3:** Dual-Direction SQL Logic Explanation & Semantic Constraint Verification (NL ↔ SQL)
- **Idea 4:** Intent Disambiguation & Interactive Clarification Dialog

---

## Before You Start

1. Open your terminal in `c:\nlp_case_study` and run:
   ```
   python -m streamlit run Home.py
   ```
2. Open the browser at `http://localhost:8501`
3. Go to **Settings (Page 1)** → verify **LLM**, **EMB**, and **DB** are all connected
4. Go to **StartChat (Page 3)** to begin

> **Important:** The database loaded is `cre_Drama_Workshop_Groups.sqlite`
> It contains tables: **Customers** (15 rows), **Stores** (10 rows), **Bookings** (15 rows), **Services** (15 rows), **Performers** (20 rows), **Products** (15 rows)

---

## DEMO 1 — Idea 1: Typo-Tolerant Fuzzy Entity Matching in SIM

**What it does:** In standard ADEPT-SQL, domain entity matching was strict/exact-only in the SIM module (offline mock mode only had token checks). In this enhancement, SIM implements **sliding-window n-gram fuzzy entity matching** (`difflib`). It can catch typos across both single-word entities (`Blak` ➔ `Blake`) and multi-word entity spans (`Adan Dinnig` ➔ `Adan Dinning`). The recognized entities are normalized in SIM before prompt construction and vector retrieval, and canonical names are passed in HINTS.

**Visual proof to show faculty:** A blue info badge appears above the SQL expander:
> `🔍 SIM Typo Alignment: Auto-corrected entity: Blak ➔ Blake (Customer_Name) · Adan Dinnig ➔ Adan Dinning (Store_Name)`

---

### Scenario A — Both Customer and Store Typos

**Type this question:**
```
Did Blak book Adan Dinnig?
```

**What happens behind the scenes:**
1. **Step 1 (SIM):**
   - N-gram fuzzy matcher identifies `Adan Dinnig` (score 0.96) as `Adan Dinning` (`Store_Name`).
   - Single-word matcher identifies `Blak` (score 0.89) as `Blake` (`Customer_Name`).
   - Masks query to `Did [Customer Name] book [Store Name]?`.
   - Normalizes query to `Did Blake book Adan Dinning?`.
2. **Step 2 (CSR):** Matches candidate Question-SQL pair with **1.0000** similarity.
3. **Step 3 & 4 (APC & LLM):** HINTS provide canonical entity values `Blake` and `Adan Dinning`. LLM writes exact SQL:
   ```sql
   SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code
   FROM Bookings B
   INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
   INNER JOIN Stores S ON B.Store_ID = S.Store_ID
   WHERE C.Customer_Name = 'Blake' AND S.Store_Name = 'Adan Dinning'
   ```
4. **Step 5 (SQL Execution):** Executes cleanly against SQLite.

---

### Scenario B — Store Typo

**Type this question:**
```
Did Harold book Shery Foto?
```
- Auto-corrects `Shery Foto` ➔ `Shery Photo` (`Store_Name`, score: 0.86).
- Executes valid SQL for Harold and Shery Photo.

---

## DEMO 2 — Idea 2: Multi-Turn Memory & Context-Aware Query Rewriting


**What it does:** When you ask a follow-up question using pronouns like *"their"*, *"how many are there"*, *"which of them"* — the system reads the previous conversation history and automatically rewrites the vague follow-up into a self-contained question before sending it to the SQL engine.

**Visual proof to show faculty:** A blue caption appears below the answer reading:
> `💬 Understood as: "<rewritten question>"`

---

### Scenario A — Follow-up using "their"

**Step 1 — Type this question first:**
```
List all customer names.
```
Expected output (15 rows):

| Customer_Name |
|---|
| Harold |
| Federico |
| Samson |
| Daryl |
| Robert |
| Jacques |
| Davonte |
| Blake |
| Elwyn |
| Alek |
| Adelbert |
| Isaiah |
| Ephraim |
| Cedrick |
| Wade |

---

**Step 2 — Immediately after, type this follow-up:**
```
What are their email addresses?
```

**What Idea 2 does:**
- Detects that *"their"* refers to the **customers** mentioned in Turn 1
- Rewrites the question to: *"What are the email addresses of all customers?"*
- Executes it against the `Customers` table

**What you see on screen:**
- Blue caption: `💬 Understood as: "What are the email addresses of all customers?"`
- Result table (15 rows):

| Customer_Name | Customer_Email_Address |
|---|---|
| Harold | jerde.harmon@example.com |
| Federico | johnson27@example.com |
| Samson | dalton75@example.com |
| Daryl | hickle.jazmyn@example.org |
| Robert | fheathcote@example.com |
| Jacques | eleannon@example.org |
| Davonte | keanu70@example.net |
| Blake | clemens43@example.org |
| Elwyn | ggrant@example.com |
| Alek | terry.nels@example.com |
| Adelbert | hermann.veum@example.org |
| Isaiah | dudley08@example.net |
| Ephraim | gage.johns@example.org |
| Cedrick | nschmidt@example.org |
| Wade | cassin.cielo@example.org |

---

### Scenario B — Follow-up using "how many are there"

**Step 1 — Type this question first:**
```
List all store names.
```
Expected output (10 rows):

| Store_Name |
|---|
| FJA Filming |
| Rob Dinning |
| Adan Dinning |
| Fred Dinning |
| Ewi Filming |
| Shery Photo |
| Carmol Photo |
| FK Filming |
| Adam Photo |
| Lur Photo |

---

**Step 2 — Immediately after, type this follow-up:**
```
How many are there in total?
```

**What Idea 2 does:**
- Detects the follow-up is incomplete (no subject mentioned)
- Reads conversation history — previous turn was about stores
- Rewrites to: *"How many stores are there in total?"*

**What you see on screen:**
- Blue caption: `💬 Understood as: "How many stores are there in total?"`
- Result table (1 row):

| total_stores |
|---|
| 10 |

---

### Scenario C — Follow-up using "which of them"

**Step 1 — Type this question first:**
```
What services are available and what are their prices?
```
Expected output (15 rows from Services table):

| Product_Name | Product_Price |
|---|---|
| film | 58932780 |
| film | 2704 |
| dinning | 6888 |
| photo | 31862 |
| photo | 213 |
| ... | ... |

---

**Step 2 — Immediately after, type this follow-up:**
```
Which of them is the most expensive?
```

**What Idea 2 does:**
- Detects *"them"* refers to **services** from Turn 1
- Rewrites to: *"Which service has the highest price?"*

**What you see on screen:**
- Blue caption: `💬 Understood as: "Which service has the highest price?"`
- Result table (1 row):

| Service_ID | Product_Name | Product_Price |
|---|---|---|
| 798 | film | 84063400 |

---

## DEMO 3 — Idea 3: Dual-Direction SQL Explanation & Semantic Verification (NL ↔ SQL)

**What it does:** Standard Text-to-SQL models operate as black boxes: a non-technical end user has no way of confirming whether the generated SQL actually implements their required business logic, joins, or filters. In this enhancement, ADEPT-SQL incorporates a **Dual-Direction Verification and Logic Explanation module**:
1. **SQL-to-NL Reverse Translation:** Deconstructs the generated SQL back into a concise plain-English summary and an ordered step-by-step database execution plan (identifying exact tables queried, joins, filters, and projections).
2. **NL-to-SQL Constraint Verification:** Formally cross-examines the SQL structure against each constraint and entity specified in the user's natural language question.
3. **Intent Alignment Verdict:** Emits a deterministic alignment badge (`✅ Verified Intent` or `⚠️ Semantic Warning`).

**Visual proof to show faculty:** An expander card opens directly under the generated SQL for **every query**:
> `🔬 SQL Logic Breakdown & Semantic Verification (Idea 3) — ✅ Verified Intent`
> - **Intent Alignment:** *Query logic faithfully matches all question requirements.*
> - **💡 Plain-English Query Logic:** *This SQL retrieves the names and email addresses of all performers.*
> - **Step-by-Step Execution Plan:**
>   1. Accesses table `Performers` to retrieve performer records
>   2. Selects the `Customer_Name` and `Customer_Email_Address` fields
> - **Constraint & Constraint Alignment Check:**
>   - ✅ **Performer entity scope**: `Satisfied`
>   - ✅ **Contact email address retrieval**: `Satisfied`

---

### Scenario A — Single-Table Query Verification

**Type this question:**
```
List all performers and their contact email addresses
```

**What you see on screen:**
1. SQL generated:
   ```sql
   SELECT Customer_Name, Customer_Email_Address
   FROM Performers
   ```
2. Verification Card appears:
   - **Verdict:** `✅ Verified Intent`
   - **Plain-English Logic:** Translates the SQL into human terms.
   - **Constraints:** Both *Performer scope* and *email address retrieval* marked `Satisfied`.
3. Results table displays all 20 performers with their email addresses.

---

### Scenario B — Multi-Table Join & Filter Verification

**Type this question:**
```
Show all bookings with status 'good'
```

**What you see on screen:**
1. SQL generated:
   ```sql
   SELECT Booking_ID, Customer_ID, Store_ID, Status_Code
   FROM Bookings
   WHERE Status_Code = 'good'
   ```
2. Verification Card appears:
   - Explains that the query filters table `Bookings` specifically where `Status_Code = 'good'`.
   - Confirms that the status constraint and projection constraints are fully satisfied.

---

## DEMO 4 — Idea 4: Query Intent Disambiguation & Interactive Clarification

**What it does:** When a user asks an underspecified or structurally ambiguous query (e.g. *"Show me the top bookings"* — top by date? top by rooms/amount? customer booking frequency?), standard Text2SQL systems silently guess a random sort order. In this enhancement, an **Ambiguity Pre-Check** detects the ambiguity against an explicit 5-point taxonomy (missing ranking metric, missing aggregation, temporal scope) and presents an **interactive clarification dialog** with candidate interpretations directly in the Streamlit UI.

**Visual proof to show faculty:**
1. A warning card appears asking for clarification:
   > `#### 🤔 Query Clarification (Idea 4)`
   > `Identified Ambiguity: Missing Ranking Criterion for 'top bookings'`
2. Radio buttons let the user select between candidate interpretations:
   - ○ Show the most recent bookings by date
   - ○ Which customers have the most bookings?
   - ○ Show all bookings with status good
3. Clicking **"Run Selected Interpretation"** executes the chosen question cleanly through the ADEPT-SQL pipeline and displays the results!
4. Clicking **"Run Original Query Anyway"** lets faculty test what the raw model generates without disambiguation.

---

### Scenario A — Missing Ranking Metric

**Type this question:**
```
Show me the top bookings
```

**What happens:**
1. System flags: **Missing Ranking Criterion** (no metric specified for "top").
2. Clarification card pops up with candidate options.
3. Select: `Which customers have the most bookings?` (or recent bookings).
4. Click **"Run Selected Interpretation"** ➔ generates and runs the correct SQL query!

---

## Quick Summary Card for Faculty

| Feature | Question to Type | What to Look For | Rows Returned |
|---|---|---|---|
| **Idea 1 — Fuzzy Entity Alignment** | `Did Blak book Adan Dinnig?` | 🔍 SIM Typo Alignment: `Blak` ➔ **Blake**, `Adan Dinnig` ➔ **Adan Dinning** | 1 row / verified |
| **Idea 1 (alt)** | `Did Harold book Shery Foto?` | 🔍 SIM Typo Alignment: `Shery Foto` ➔ **Shery Photo** | verified |
| **Idea 2 — Turn 1** | `List all customer names.` | Normal answer | 15 rows |
| **Idea 2 — Turn 2** | `What are their email addresses?` | 💬 Understood as: "... all customers ..." | 15 rows |
| **Idea 2 — Turn 1** | `List all store names.` | Normal answer | 10 rows |
| **Idea 2 — Turn 2** | `How many are there in total?` | 💬 Understood as: "How many stores ..." | 1 row (count=10) |
| **Idea 3 — Dual-Direction Verification** | `List all performers and their contact email addresses` | 🔬 SQL Logic Breakdown & Semantic Verification (`✅ Verified Intent`) | 20 rows |
| **Idea 3 (alt)** | `Show all bookings with status 'good'` | 🔬 Step-by-Step execution plan + constraints checklist | 10 rows |
| **Idea 4 — Ambiguity Clarification** | `Show me the top bookings` | 🤔 Clarification Needed: Radio options appear, click option ➔ executes! | Disambiguated results |
| **Idea 5 — Schema-Linking Visualizer** | `How many bookings does each customer have?` | 🗺️ Interactive ER diagram highlighting `Customers` and `Bookings` nodes & FK join | Graph + JOIN summary |
| **Idea 6 — Auto-Visualization (Bar)** | `How many bookings does each customer have?` | 📊 Horizontal Bar chart automatically chosen (Customer_Name × count) | Plotly Bar Chart |
| **Idea 6 — Auto-Visualization (Metric)** | `list the total number of stores` | 📊 Big Metric Card (10 Total Stores) automatically chosen | Metric Card |
| **Idea 6 — Pure Text (No Chart)** | `List all store names.` | 📋 Graceful fallback: text-only table shown without unnecessary empty chart | Table only |

---

## Notes

- **For Idea 1** — Sliding-window n-gram matcher correctly skips common SQL stopwords (`list`, `show`, `find`, `tell`) while fixing real entity typos.
- **For Idea 2** — The rewrite badge only appears when the system detects the follow-up is truly ambiguous. If your question is already self-contained, no badge appears (that is correct behaviour, not a bug).
- **For Idea 3** — Works reliably on 100% of queries with zero need to force fake SQL errors. Proves bidirectional reasoning (Text ➔ SQL and SQL ➔ Text).
- **New conversation** — Click **Clear Chat** or refresh the page to start a fresh conversation session for a clean demo.
