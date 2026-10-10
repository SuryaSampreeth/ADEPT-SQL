from typing import Type
from user_input_process import user_input_init
import pandas as pd
import os

current_dir = os.getcwd()


# ─────────────────────────────────────────────────────────────────────────────
# FEW-SHOT PROMPT: used when CSR finds similar QS pairs (similarity > threshold)
# The schema is intentionally omitted — the LLM imitates the example SQL structure.
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_Fewshot:
    def __init__(self, user_input: Type[user_input_init], foundqadf: pd.DataFrame):
        self.user_input_cls = user_input
        self.foundqadf = foundqadf.reset_index(drop=True)

    def compile_examples(self):
        examples = ""
        for i in range(self.foundqadf.shape[0]):
            q = 'Question: ' + self.foundqadf['question'][i]
            a = 'SQL: ' + self.foundqadf['sql'][i]
            examples += '\n'.join([q, a]) + '\n\n'
        return examples.strip()

    def compile(self):
        examples = self.compile_examples()
        hints = self.user_input_cls.gen_hints()
        user_question = getattr(self.user_input_cls, 'normalized_input', self.user_input_cls.input)

        if not hints.strip():
            hints = 'No specific terminology hints for this question.'

        prompt = f"""
#Character#
You are an expert SQL writer. Your best skill is mimicking similar SQL statements to write new SQL for new questions.
You can replace specific entity names and time values in SQL while keeping the structure the same.

#Task#
Write a SQL statement to answer the user question, modeled after the following Examples.

#Rules#
1. Use the canonical entity values and field names from HINTS in your WHERE conditions (e.g. use exact names from HINTS, never typos).
2. Imitate the Examples precisely — reuse the same JOINs, WHERE patterns, and aggregations.
3. Add line breaks for readability.
4. Output ONLY a single valid SQL statement. No explanations, no markdown.
5. The SQL must be executable by pd.read_sql_query().

#Examples#
{examples}

#Now Write SQL#
Question: {user_question}
HINTS: {hints}
SQL:"""
        return prompt



# ─────────────────────────────────────────────────────────────────────────────
# ZERO-SHOT PROMPT: used when no similar QS pairs found
# Includes a dynamically filtered schema (only relevant tables/columns).
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_Zeroshot:
    def __init__(self, user_input: Type[user_input_init]):
        self.user_input_cls = user_input
        meta_path = os.path.join(current_dir, 'backend/dbmata.csv')
        if os.path.exists(meta_path):
            self.meta = pd.read_csv(meta_path, index_col=0)
        else:
            self.meta = pd.DataFrame(columns=['Table', 'Table Description', 'Column', 'Column Description'])

    def identify_table_fields(self):
        """
        APC: Adaptive schema selection.
        Selects only table fields relevant to the user question via:
        1. Hints from SIM terminology matching (direct field links)
        2. Vocabulary overlap between user query words and metadata strings
        """
        fields = set()

        # Part 1: Fields found directly from SIM hint list
        hintslist = self.user_input_cls.hintslist
        if len(hintslist) > 0:
            fields = fields | set([h[1] for h in hintslist])

        # Part 2: Fields identified by word-level overlap with metadata
        query_words = set(self.user_input_cls.input.lower().split())
        for i in range(self.meta.shape[0]):
            line = list(self.meta.iloc[i])
            line_str = ','.join([str(j).lower() for j in line])
            if any(word in line_str for word in query_words if len(word) > 2):
                col_name = line[2] if len(line) > 2 else ''
                if col_name:
                    fields.add(col_name)

        return list(fields)

    def compile_meta(self):
        """Build a clean schema string for only the relevant tables."""
        fields = self.identify_table_fields()

        if not fields or self.meta.empty:
            return 'Schema not available. Write the SQL based on your best understanding.'

        # Find tables that contain relevant fields
        submeta = self.meta[self.meta['Column'].isin(fields)]
        tables = set(submeta['Table'])

        # Expand to include ALL fields from relevant tables (not just matched ones)
        submeta = self.meta[self.meta['Table'].isin(tables)]

        schema = []
        for table in sorted(tables):
            sub = self.meta[self.meta['Table'] == table].fillna('')
            table_desc_values = set(sub['Table Description'])
            table_desc = ' '.join([d for d in table_desc_values if d])
            schema.append(f'Table: {table}  -- {table_desc}' if table_desc else f'Table: {table}')
            schema.append('Columns:')
            for _, row in sub.iterrows():
                col_desc = row.get('Column Description', row['Column'])
                schema.append(f'  - {row["Column"]}  ({col_desc})')
            schema.append('')

        return '\n'.join(schema)

    def compile(self):
        user_question = getattr(self.user_input_cls, 'normalized_input', self.user_input_cls.input)
        hints = self.user_input_cls.gen_hints()
        schema = self.compile_meta()

        if not hints.strip():
            hints = 'No specific terminology hints for this question.'

        prompt = f"""
#Character#
You are an expert SQL writer working for a company. You are familiar with the database schema and write precise SQL queries for staff questions.

#Task#
Write a SQL query to answer the following question. Use the provided Schema and HINTS.

#Rules#
1. Use field names as-is from the Schema and canonical entity values from HINTS in your WHERE conditions. Do NOT invent table/column names.
2. Use HINTS to correctly filter or join on the right values.
3. Add line breaks for readability.
4. Output ONLY a single valid SQL statement. No explanations, no markdown.
5. The SQL must be executable by pd.read_sql_query().

#Schema#
{schema}

#Now Write SQL#
Question: {user_question}
HINTS: {hints}
SQL:"""
        return prompt



# ─────────────────────────────────────────────────────────────────────────────
# ANSWER SUMMARY PROMPT: explains the completed Text2SQL task to the user
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_Answer:
    def __init__(self, taskinfos) -> None:
        self.taskinfos = taskinfos

    def complie(self):
        prompt = f"""
#Character#
You are a friendly Text2SQL assistant. Your tone is clear and concise.

#Task#
Summarize the following Text2SQL workflow result to the user in plain language.

#Rules#
1. Briefly explain what the SQL does (JOINs, filters, aggregations used).
2. Directly answer the user's question using the query result.
3. Keep your response under 60 words.
4. Do NOT repeat the SQL itself.

#Workflow Result#
User Question: {self.taskinfos['question']}
Search Result: {self.taskinfos['search_res']}
SQL Generated:
{self.taskinfos['sql']}
SQL Execution Result (first 3 rows):
{self.taskinfos['sqlexe']}
"""
        return prompt


# ─────────────────────────────────────────────────────────────────────────────
# QUERY REWRITER PROMPT — multi-turn conversation context resolution
# Rewrites follow-up questions (with pronouns / references) into self-contained
# questions using recent conversation history, before entering the ADEPT pipeline.
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_QueryRewriter:
    def __init__(self, chat_history: list, current_question: str):
        """
        chat_history: list of dicts with keys 'role' ('user'/'assistant') and 'content'
        current_question: the new question from the user
        """
        self.chat_history = chat_history
        self.current_question = current_question

    def compile(self):
        history_str = ""
        for turn in self.chat_history:
            role = "User" if turn.get("role") == "user" else "Assistant"
            history_str += f"{role}: {turn.get('content', '')}\n"

        prompt = f"""You are a query rewriter for a database chatbot.

#Task#
Given the conversation history and a new user question, rewrite the question to be fully self-contained.

#Rules#
1. If the new question contains pronouns or references like "he", "she", "it", "they", "that store", "the same", "his", "her", "him", "also", "and what about" — replace them with the actual entity names from the history.
2. If the question is ALREADY self-contained and does NOT reference previous turns — output it EXACTLY as-is. Do NOT change it.
3. Output ONLY the rewritten question. No explanation. No prefix like "Rewritten:" or "Answer:".

#Conversation History#
{history_str.strip()}

#New Question#
{self.current_question}

Rewritten Question:"""
        return prompt


# ─────────────────────────────────────────────────────────────────────────────
# IDEA 3: DUAL-DIRECTION SQL EXPLANATION & SEMANTIC VERIFICATION (NL <-> SQL)
# Translates the generated SQL back into human-readable logical steps and
# cross-verifies whether every constraint in the user's question is satisfied.
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_SQLExplanationAndVerification:
    def __init__(self, question: str, sql: str, schema_summary: str = ""):
        self.question = question
        self.sql = sql
        self.schema_summary = schema_summary

    def compile(self) -> str:
        schema_section = f"\n#Database Schema Context#\n{self.schema_summary.strip()}\n" if self.schema_summary else ""
        prompt = f"""You are an expert Text-to-SQL analyst and verification engine.

#Task#
Perform a dual-direction evaluation:
1. Explain the logic of the generated SQL in simple, non-technical plain English steps.
2. Verify whether the SQL faithfully and completely satisfies all constraints, filters, and aggregations specified in the user's natural language question.
{schema_section}
#User Question#
{self.question}

#Generated SQL#
{self.sql}

#Evaluation Guidelines#
- Logic Steps: Identify the primary database operations: tables queried/joined, filters (WHERE), groupings/aggregations (COUNT/SUM/AVG), and ordering/limits.
- Constraint Verification: Check if all user-specified entities, conditions, and targets are present in the SQL.
- Verdict: "Verified" if the SQL accurately captures the question's intent; "Discrepancy Detected" if a constraint is missing or mismatched.

#Output Format#
You MUST respond with valid JSON ONLY. Do not include markdown code fences (```json). Do not add preamble or commentary.
Format:
{{
  "verified": true,
  "verdict_summary": "Query logic faithfully matches all question requirements.",
  "plain_english_summary": "<1-2 sentences summarizing what this SQL calculates in plain English>",
  "execution_logic_steps": [
    "<Step 1: e.g. Accesses table Performers to retrieve performer records>",
    "<Step 2: e.g. Selects the Customer_Name and Customer_Email_Address fields>"
  ],
  "constraints_checked": [
    {{"constraint": "Performer entity scope", "status": "Satisfied"}},
    {{"constraint": "Contact email address retrieval", "status": "Satisfied"}}
  ]
}}

JSON:"""
        return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Backward Compatibility: Prompt_SelfCorrection
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_SelfCorrection:
    def __init__(self, original_question: str, broken_sql: str, error_message: str, schema: str = ""):
        self.original_question = original_question
        self.broken_sql = broken_sql
        self.error_message = error_message
        self.schema = schema

    def compile(self):
        schema_section = ""
        if self.schema and self.schema.strip():
            schema_section = f"\n#Database Schema (Actual Valid Tables & Columns)#\n{self.schema.strip()}\n"

        prompt = f"""You are an expert SQL debugger.

#Task#
The SQL query below was generated to answer a user's question but failed to execute against the SQLite database.
Diagnose the error using the database error message and the schema below, then output a corrected, valid SQL query.

#User's Original Question#
{self.original_question}

#Broken SQL (that failed)#
{self.broken_sql}

#Database Error Message#
{self.error_message}
{schema_section}
#Rules#
1. Output ONLY the corrected SQL. No explanation. No markdown formatting. No backticks.
2. Check the Database Schema carefully! You MUST use the EXACT table and column names from the schema. Do NOT invent or guess column names.
3. Fix the specific issue identified by the error message (e.g. replace non-existent column names with the real column names present in the schema).
4. Preserve the user's original query intent, filtering, ordering, and structure.
5. The output must be valid SQLite syntax and executable by pd.read_sql_query().

Corrected SQL:"""
        return prompt


# ─────────────────────────────────────────────────────────────────────────────
# IDEA 4: AMBIGUITY DETECTION PROMPT — detects underspecified queries
# Evaluates queries against an explicit 5-point ambiguity taxonomy:
#   1. Missing Ranking Metric (e.g. "top", "best" without a sort column)
#   2. Missing Aggregation Metric (e.g. "summary" without count/sum/group)
#   3. Underspecified Temporal Scope (e.g. "recent", "latest" without timeframe)
#   4. Ambiguous Entity Reference (unresolved or multi-entity match)
#   5. Multi-Path Operation (multiple valid SQL interpretations)
# ─────────────────────────────────────────────────────────────────────────────
class Prompt_AmbiguityCheck:
    def __init__(self, question: str, schema_summary: str = ""):
        self.question = question
        self.schema_summary = schema_summary

    def compile(self) -> str:
        schema_part = f"\n#Database Schema Context#\n{self.schema_summary.strip()}\n" if self.schema_summary else ""

        prompt = f"""You are a natural language understanding assistant specializing in database query disambiguation.

#Task#
Analyze the user's question to determine whether it is structurally AMBIGUOUS or CLEAR for SQL generation.
{schema_part}
#Ambiguity Taxonomy & Evaluation Criteria#
A question is AMBIGUOUS if and only if it triggers at least one of these criteria:
1. Missing Ranking Criterion: Words like "top", "best", "leading", "popular" are used without specifying by what metric (e.g. "top bookings" — by date? by amount? by customer frequency?).
2. Missing Aggregation Metric: Requests an overview or summary without specifying whether to count, list, or aggregate.
3. Incomplete Temporal Scope: Relative time terms like "recent", "latest", "past" without an explicit date, interval, or sort column.
4. Unresolved Entity Reference: A reference that could correspond to multiple different entities or tables.
5. Multi-Path SQL Resolution: Multiple fundamentally different SQL queries could equally satisfy the phrasing.

If the question is specific and clearly maps to a single SQL query (e.g. "List all store names", "Did Blake book Adan Dinning?", "How many bookings are there?"), it is CLEAR.

#Output Format#
You MUST respond with valid JSON only. Do not add markdown code fences. Do not add commentary.
If CLEAR:
{{"is_ambiguous": false, "reason": "", "options": []}}

If AMBIGUOUS:
{{"is_ambiguous": true, "reason": "<Short explanation of why it is ambiguous>", "options": ["<Clarified natural language question 1>", "<Clarified natural language question 2>", "<Clarified natural language question 3>"]}}

Each option must be a complete, self-contained natural language question that can be directly converted into SQL.

#User Question#
{self.question}

JSON:"""
        return prompt




if __name__ == "__main__":

    # Test zero-shot prompt
    user_input = 'How many Bookings are there in total?'
    processed = user_input_init(user_input).full_process()
    p = Prompt_Zeroshot(processed).compile()
    print(p)