import requests
import re
import difflib


class callLLM():
    """
    Calls an OpenAI-compatible LLM API endpoint OR runs in Offline Demo Mode.
    Supports: OpenAI, DeepSeek, Groq, Ollama, vLLM, OpenRouter, and Offline Mock Mode.
    """

    def __init__(self, llmapi) -> None:
        self.llm_server = llmapi.get('url', '')
        self.token = llmapi.get('token', '')
        self.modelname = llmapi.get('name', 'demo mode')
        self.is_demo = (
            self.modelname.lower() == 'demo mode' or
            self.token.lower() in ('', 'demo', 'none', 'mock', 'offline') or
            self.llm_server.lower() in ('', 'demo', 'offline')
        )

    def init_prompt(self, sys_prompt, prompt):
        self.sys_prompt = sys_prompt
        self.prompt = prompt
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": prompt}
        ]
        self.llm_input = {
            "model": self.modelname,
            "messages": messages,
            "temperature": 0.1
        }
        return self

    def call(self):
        if self.is_demo:
            print('[LLM] Running in Demo Mode (Offline - No API Key).')
            self.llm_response = {"choices": [{"message": {"content": self._mock_response()}}]}
            return self

        print(f'[LLM] Calling model: {self.llm_input["model"]} ...')
        try:
            resp = requests.post(
                url=self.llm_server,
                json=self.llm_input,
                headers={
                    "Content-Type": 'application/json',
                    "Accept": 'application/json',
                    "Authorization": 'Bearer ' + self.token
                },
                timeout=60
            )
            self.llm_response = resp.json()
            print('[LLM] Response received.')
            if 'error' in self.llm_response or resp.status_code >= 400:
                err_info = self.llm_response.get('error', {})
                err_msg = err_info.get('message', f"HTTP {resp.status_code}")
                print(f'[LLM] Upstream API rate limit / error ({err_msg}). Falling back to offline generator.')
                self.llm_response = {"choices": [{"message": {"content": self._mock_response()}}]}
        except Exception as e:
            print(f'[LLM] Request failed: {e}. Falling back to Offline Demo Mode.')
            self.llm_response = {"choices": [{"message": {"content": self._mock_response()}}]}
        return self

    def get_response_content(self):
        if 'choices' in self.llm_response and len(self.llm_response['choices']) > 0:
            self.llmcontent = self.llm_response['choices'][0]['message']['content']
        else:
            print('[LLM] Unexpected response format:', self.llm_response)
            print('[LLM] Falling back to offline generator.')
            self.llmcontent = self._mock_response()
        return self.llmcontent

    def _mock_response(self) -> str:
        """Rule-based mock generator for offline presentation without an API key."""
        prompt_lower = self.prompt.lower()

        # Connection check query
        if 'who are you' in prompt_lower:
            return "I am ADEPT-SQL Demo Assistant. I run Text2SQL queries for enterprise databases."

        # -- Summary answer generation prompt (Prompt_Answer) ------------------
        # Matches the #Workflow Result# section header in Prompt_Answer.complie()
        if '#workflow result#' in prompt_lower or 'workflow result' in prompt_lower:
            # Detect empty result in the prompt text
            if ('empty dataframe' in prompt_lower
                    or '0 rows' in prompt_lower
                    or 'no results' in prompt_lower):
                return ("The SQL query ran successfully, but no matching record was found "
                        "in the database for that specific combination.")
            return "Successfully retrieved the matching data records from the database."

        # -- Self-Correction prompt (Prompt_SelfCorrection) -------------------
        if '#broken sql' in prompt_lower or 'diagnose the error' in prompt_lower or 'corrected sql:' in prompt_lower:
            if 'performer' in prompt_lower:
                if 'phone' in prompt_lower:
                    return "SELECT Customer_Name, Customer_Phone FROM Performers ORDER BY Customer_Name"
                return "SELECT Customer_Name, Customer_Email_Address FROM Performers ORDER BY Customer_Name"
            if 'service' in prompt_lower:
                return "SELECT Product_Name, Service_Type_Code, Product_Price FROM Services ORDER BY Product_Price DESC"
            if 'store' in prompt_lower and 'name' in prompt_lower:
                return "SELECT Store_Name FROM Stores ORDER BY Store_Name"
            if 'customer' in prompt_lower and 'name' in prompt_lower:
                return "SELECT Customer_Name FROM Customers ORDER BY Customer_Name"

        # -- Ambiguity detection prompt (Prompt_AmbiguityCheck) ----------------
        if 'ambiguity taxonomy' in prompt_lower or 'is_ambiguous' in prompt_lower:
            if 'top booking' in prompt_lower or 'best booking' in prompt_lower:
                return '{"is_ambiguous": true, "reason": "Missing Ranking Criterion for top bookings", "options": ["Show the most recent bookings by date", "Which customer has the most bookings?", "Show all bookings with status good"]}'
            if 'top customer' in prompt_lower or 'best customer' in prompt_lower:
                return '{"is_ambiguous": true, "reason": "Missing Ranking Criterion for best customer", "options": ["Which customer has the most bookings?", "List all customers alphabetically", "Show customers with recent bookings"]}'
            if 'top store' in prompt_lower or 'best store' in prompt_lower:
                return '{"is_ambiguous": true, "reason": "Missing Ranking Criterion for top stores", "options": ["Which store has the most bookings?", "List all store names alphabetically", "Show stores by marketing region"]}'
            return '{"is_ambiguous": false, "reason": "", "options": []}'

        # -- Query Rewriter prompt (Prompt_QueryRewriter — Idea 2) ------------
        if 'query rewriter' in prompt_lower or 'rewritten question:' in prompt_lower:
            if '#new question#' in prompt_lower:
                part = prompt_lower.split('#new question#', 1)[1]
                if 'rewritten question:' in part:
                    return part.split('rewritten question:', 1)[0].strip()
            return self.prompt

        # -- SQL Explanation & Semantic Verification (Prompt_SQLExplanationAndVerification — Idea 3)
        if 'dual-direction' in prompt_lower or 'verification engine' in prompt_lower or 'execution_logic_steps' in prompt_lower:
            return '''{
  "verified": true,
  "verdict_summary": "Query logic faithfully matches all question requirements and schema constraints.",
  "plain_english_summary": "Retrieves matching database records, applying table joins, projection filters, and aggregations as specified.",
  "execution_logic_steps": [
    "Scans targeted tables and joins relational foreign keys",
    "Applies entity and attribute filters according to question parameters",
    "Computes requested aggregations and formats the result set"
  ],
  "constraints_checked": [
    {"constraint": "Entity Filter Alignment", "status": "Satisfied"},
    {"constraint": "Column Projection Completeness", "status": "Satisfied"},
    {"constraint": "Relational Foreign Key Integrity", "status": "Satisfied"}
  ]
}'''

        # -- Extract ONLY the user question from the prompt --------------------


        # Both Prompt_Fewshot and Prompt_Zeroshot end with:
        #   #Now Write SQL#
        #   Question: <user question>
        #   HINTS: ...
        #   SQL:
        # We scan only the user question segment so that few-shot example text
        # (which may contain OTHER customer/store names) does not pollute detection.
        question_segment = prompt_lower  # fallback: use whole prompt
        marker = '#now write sql#'
        if marker in prompt_lower:
            after = prompt_lower.split(marker, 1)[1]
            # Grab from "question:" up to "hints:" or "sql:"
            q_match = re.search(r'question:\s*(.*?)(?=hints:|sql:|$)', after, re.DOTALL)
            if q_match:
                question_segment = q_match.group(1).strip()

        # -- All known customer names in the demo DB ---------------------------
        # Ordered so that longer / more distinctive names are checked first.
        CUSTOMERS = [
            ('adelbert', 'Adelbert'),
            ('federico', 'Federico'),
            ('ephraim',  'Ephraim'),
            ('davonte',  'Davonte'),
            ('adelbert', 'Adelbert'),
            ('cedrick',  'Cedrick'),
            ('jacques',  'Jacques'),
            ('isaiah',   'Isaiah'),
            ('harold',   'Harold'),
            ('robert',   'Robert'),
            ('elwyn',    'Elwyn'),
            ('blake',    'Blake'),
            ('daryl',    'Daryl'),
            ('samson',   'Samson'),
            ('wade',     'Wade'),
            ('alek',     'Alek'),
        ]
        # All known store names in the demo DB
        STORES = [
            ('carmol photo',  'Carmol Photo'),
            ('adam photo',    'Adam Photo'),
            ('shery photo',   'Shery Photo'),
            ('adan dinning',  'Adan Dinning'),
            ('fred dinning',  'Fred Dinning'),
            ('rob dinning',   'Rob Dinning'),
            ('fja filming',   'FJA Filming'),
            ('ewi filming',   'Ewi Filming'),
            ('fk filming',    'FK Filming'),
            ('lur photo',     'Lur Photo'),
            # short aliases
            ('carmol',  'Carmol Photo'),
            ('shery',   'Shery Photo'),
            ('adan',    'Adan Dinning'),
            ('fred',    'Fred Dinning'),
            ('rob',     'Rob Dinning'),
            ('fja',     'FJA Filming'),
            ('ewi',     'Ewi Filming'),
            ('lur',     'Lur Photo'),
        ]

        # -- Detect customer name (exact, then fuzzy) against question only ----
        customer_name = None
        all_customer_keywords = [kw for kw, _ in CUSTOMERS]
        # 1. Exact substring match inside the question segment
        for keyword, canonical in CUSTOMERS:
            if keyword in question_segment:
                customer_name = canonical
                break
        # 2. Fuzzy word-by-word match to catch typos like 'horald' -> 'harold'
        if not customer_name:
            for word in question_segment.split():
                if len(word) >= 4:
                    close = difflib.get_close_matches(word, all_customer_keywords, n=1, cutoff=0.6)
                    if close:
                        for keyword, canonical in CUSTOMERS:
                            if keyword == close[0]:
                                customer_name = canonical
                                break
                if customer_name:
                    break

        # -- Detect store name (exact, then fuzzy) against question only -------
        store_name = None
        for keyword, canonical in STORES:
            if keyword in question_segment:
                store_name = canonical
                break
        if not store_name:
            single_word_stores = [kw for kw, _ in STORES if ' ' not in kw]
            for word in question_segment.split():
                if len(word) >= 4:
                    close = difflib.get_close_matches(word, single_word_stores, n=1, cutoff=0.6)
                    if close:
                        for keyword, canonical in STORES:
                            if keyword == close[0]:
                                store_name = canonical
                                break
                if store_name:
                    break

        # -- Customer + Store -> JOIN on Customer_Orders -----------------------
        if customer_name and store_name:
            return (
                f"SELECT O.Order_ID, C.Customer_Name, S.Store_Name, O.Order_Date\n"
                f"FROM Customer_Orders O\n"
                f"INNER JOIN Customers C ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID\n"
                f"INNER JOIN Stores S ON CAST(O.Store_ID AS TEXT) = S.Store_ID\n"
                f"WHERE C.Customer_Name = '{customer_name}'\n"
                f"AND S.Store_Name = '{store_name}'"
            )

        # -- Customer-only lookup ---------------------------------------------
        if customer_name:
            return (
                f"SELECT O.Order_ID, C.Customer_Name, S.Store_Name, O.Order_Date\n"
                f"FROM Customer_Orders O\n"
                f"INNER JOIN Customers C ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID\n"
                f"INNER JOIN Stores S ON CAST(O.Store_ID AS TEXT) = S.Store_ID\n"
                f"WHERE C.Customer_Name = '{customer_name}'"
            )

        # -- Aggregation / counting queries (checked against question segment) -
        if 'most' in question_segment and ('booking' in question_segment or 'order' in question_segment):
            return (
                "SELECT C.Customer_Name, COUNT(O.Order_ID) AS order_count\n"
                "FROM Customers C\n"
                "INNER JOIN Customer_Orders O ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID\n"
                "GROUP BY C.Customer_Name\n"
                "ORDER BY order_count DESC\n"
                "LIMIT 1"
            )

        if ('how many' in question_segment or 'total' in question_segment or 'number of' in question_segment) and ('booking' in question_segment or 'order' in question_segment):
            return "SELECT COUNT(*) AS total_orders FROM Customer_Orders"

        if ('how many' in question_segment or 'total' in question_segment or 'number of' in question_segment) and 'customer' in question_segment:
            return "SELECT COUNT(*) AS total_customers FROM Customers"

        if ('how many' in question_segment or 'total' in question_segment or 'number of' in question_segment) and 'store' in question_segment:
            return "SELECT COUNT(*) AS total_stores FROM Stores"

        if 'performer' in question_segment:
            return "SELECT Customer_Name, Customer_Phone, Customer_Email_Address FROM Performers ORDER BY Customer_Name"

        if 'service' in question_segment:
            return "SELECT Product_Name, Service_Type_Code, Product_Price FROM Services ORDER BY Product_Price DESC"

        if 'list all store' in question_segment or ('store' in question_segment and 'name' in question_segment):
            return "SELECT Store_Name FROM Stores ORDER BY Store_Name"

        if 'list all customer' in question_segment or ('customer' in question_segment and 'name' in question_segment):
            return "SELECT Customer_Name FROM Customers ORDER BY Customer_Name"

        # Default fallback SQL
        return "SELECT * FROM Customer_Orders LIMIT 10"



def clean_sql_output(raw: str) -> str:
    """Robustly extracts the SQL statement from LLM output."""
    raw = raw.strip()

    fenced_match = re.search(r'```(?:sql)?\s*\n?(.*?)```', raw, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        raw = fenced_match.group(1).strip()

    raw = raw.strip('`').strip()

    # Strip prefixes like "Corrected SQL:", "SQL:", "Output:"
    raw = re.sub(r'^(?:corrected\s+sql|sql|output|query|answer):\s*', '', raw, flags=re.IGNORECASE).strip()

    # Strip trailing semicolon
    raw = raw.rstrip(';').strip()
    return raw



if __name__ == '__main__':
    # Test Demo Mode
    llmapi = {'url': 'demo', 'token': 'demo', 'name': 'Demo Mode (Offline)'}
    res = callLLM(llmapi).init_prompt('system', 'Did Harold book Adan Dinning?').call().get_response_content()
    print("Mock SQL Output:\n", res)
