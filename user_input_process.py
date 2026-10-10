import re
import difflib
from datetime import datetime
import pandas as pd
import os

current_dir = os.getcwd()


class user_input_init():
    def __init__(self, input):
        self.input = input
        self.trans = input
        self.normalized_input = input  # Question with typos replaced by canonical entities
        self.hintslist = []
        self.fuzzy_matches = []  # Tracks typo corrections: [{'raw': ..., 'canonical': ..., 'field': ..., 'score': ...}]

        self.time_replace = False
        self.term_replace = False

    def time_recognition(self):
        """
        Replace specific date/month strings in the user query with generic placeholders.
        Supports multiple formats (YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, YYYY年MM月DD日, etc.)
        This helps the CSR retrieve structurally similar QS pairs regardless of date values.
        """
        dd_patterns = [
            r'(\d{2,4}-\d{1,2}-\d{1,2})',        # YYYY-MM-DD
            r'(\d{2,4}/\d{1,2}/\d{1,2})',          # YYYY/MM/DD
            r'(\d{2,4}\\\d{1,2}\\\d{1,2})',        # YYYY\\MM\\DD
            r'(\d{2,4}\.\d{1,2}\.\d{1,2})',        # YYYY.MM.DD
            r'(\d{2,4}年\d{1,2}月\d{1,2}日)'        # YYYY年MM月DD日
        ]
        combined_dd_pattern = '|'.join(dd_patterns)

        mm_patterns = [
            r'(\d{2,4}-\d{1,2})',       # YYYY-MM
            r'(\d{2,4}/\d{1,2})',       # YYYY/MM
            r'(\d{2,4}\\\d{1,2})',      # YYYY\\MM
            r'(\d{2,4}\.\d{1,2})',      # YYYY.MM
            r'(\d{2,4}年\d{1,2}月)'     # YYYY年MM月
        ]
        combined_mm_pattern = '|'.join(mm_patterns)

        # Find and replace full date matches first (more specific)
        dd_dates = []
        matches = re.findall(combined_dd_pattern, self.input)
        for match in matches:
            match = list([x.strip() for x in match if x.strip() != ''])[0]
            dd_dates.append(match)

        for dd in dd_dates:
            self.trans = self.trans.replace(dd, '[date]')

        # Then match month-only patterns
        mm_dates = []
        matches = re.findall(combined_mm_pattern, self.trans)
        for match in matches:
            match = list([x.strip() for x in match if x.strip() != ''])[0]
            mm_dates.append(match)

        for mm in mm_dates:
            self.trans = self.trans.replace(mm, '[month]')

        print('[SIM] Date masking result:', self.trans)
        self.time_replace = True
        return self

    def term_recognition(self):
        """
        SIM Module: Typo-Tolerant Terminology Alignment (Idea 1).
        Performs sliding-window n-gram fuzzy matching on entity spans against the domain
        term dictionary (backend/term.csv) using difflib.
        
        Handles both:
          1. Multi-word entity typos (e.g. 'Adan Dinnig' -> 'Adan Dinning', 'Shery Foto' -> 'Shery Photo')
          2. Single-word entity typos (e.g. 'Blak' -> 'Blake', 'Horald' -> 'Harold')
        
        Replaces matched spans in self.trans with semantic field placeholders [Field Description],
        builds hint sentences with canonical names, and records typo matches in self.fuzzy_matches.
        """
        term_csv_path = os.path.join(current_dir, "backend/term.csv")
        meta_csv_path = os.path.join(current_dir, "backend/dbmata.csv")

        if not os.path.exists(term_csv_path):
            print('[SIM] Warning: term.csv not found. Skipping term recognition.')
            self.term_replace = True
            return self

        term_df = pd.read_csv(term_csv_path)

        field_df = None
        if os.path.exists(meta_csv_path):
            field_df = pd.read_csv(meta_csv_path)

        # Build term list with metadata
        terms_info = []
        for _, row in term_df.dropna(subset=['term']).iterrows():
            t_str = str(row['term']).strip()
            f_name = str(row['field']).strip()
            f_des = f_name
            if field_df is not None:
                try:
                    f_des = field_df[field_df['Column'] == f_name]['Column Description'].values[0]
                except (IndexError, KeyError):
                    f_des = f_name
            words = t_str.split()
            terms_info.append({
                'term': t_str,
                'term_lower': t_str.lower(),
                'field': f_name,
                'field_des': str(f_des),
                'word_count': len(words)
            })

        max_n = max([t['word_count'] for t in terms_info]) if terms_info else 1

        # Tokenize current text into word tokens with character spans
        tokens = [(m.group(), m.start(), m.end()) for m in re.finditer(r'\b[A-Za-z0-9_]+\b', self.trans)]

        matches = []
        used_token_indices = set()

        # Sliding window n-gram matching from max_n down to 1 (longer entities matched first)
        for n in range(max_n, 0, -1):
            for i in range(len(tokens) - n + 1):
                span_indices = set(range(i, i + n))
                if span_indices & used_token_indices:
                    continue

                start_char = tokens[i][1]
                end_char = tokens[i + n - 1][2]
                raw_span = self.trans[start_char:end_char]
                raw_lower = raw_span.lower()

                best_match = None
                best_score = 0.0

                for t in terms_info:
                    if t['word_count'] != n:
                        continue

                    # Exact match
                    if raw_lower == t['term_lower']:
                        best_match = t
                        best_score = 1.0
                        break

                    # Skip common SQL command words / question words for fuzzy single-word matching
                    SQL_STOPWORDS = {'list', 'show', 'find', 'tell', 'give', 'what', 'which', 'who', 'how', 'many', 'all', 'any', 'each', 'every', 'name', 'names', 'store', 'stores', 'group', 'order', 'date', 'total'}
                    if n == 1 and raw_lower in SQL_STOPWORDS:
                        continue

                    # Fuzzy match
                    score = difflib.SequenceMatcher(None, raw_lower, t['term_lower']).ratio()
                    # Multi-word entities require >= 0.70 ratio; single words require >= 0.75 (min length 4)
                    cutoff = 0.70 if n >= 2 else (0.75 if len(raw_span) >= 4 else 0.85)

                    if score >= cutoff and score > best_score:
                        best_match = t
                        best_score = score

                if best_match and best_score >= 0.70:
                    matches.append({
                        'start': start_char,
                        'end': end_char,
                        'raw': raw_span,
                        'canonical': best_match['term'],
                        'field': best_match['field'],
                        'field_des': best_match['field_des'],
                        'score': best_score,
                        'is_fuzzy': (raw_lower != best_match['term_lower'])
                    })
                    used_token_indices.update(span_indices)

        # Replace in self.trans and self.normalized_input in reverse character position
        matches.sort(key=lambda m: m['start'], reverse=True)
        for m in matches:
            self.trans = self.trans[:m['start']] + f"[{m['field_des']}]" + self.trans[m['end']:]
            self.normalized_input = self.normalized_input[:m['start']] + m['canonical'] + self.normalized_input[m['end']:]
            self.hintslist.append([m['canonical'], m['field'], m['field_des']])

            if m['is_fuzzy']:
                self.fuzzy_matches.append({
                    'raw': m['raw'],
                    'canonical': m['canonical'],
                    'field': m['field'],
                    'score': round(m['score'], 2)
                })
                print(f"[SIM] Fuzzy typo matched '{m['raw']}' -> '{m['canonical']}' ({m['field']}, score: {m['score']:.2f})")
            else:
                print(f"[SIM] Exact matched term '{m['canonical']}' -> field '{m['field']}' ({m['field_des']})")

        print('[SIM] Masked question:', self.trans)
        if self.fuzzy_matches:
            print('[SIM] Normalized question:', self.normalized_input)
        self.term_replace = True
        return self


    def gen_hints(self):
        """Build a hint sentence string for the prompt, from discovered terms."""
        if not self.term_replace:
            self.term_recognition()
        hint_str = ''
        for item in self.hintslist:
            hint_str += f"Use exact entity value '{item[0]}' for field [{item[1]}], means {item[2]}; "
        return hint_str


    def full_process(self):
        """
        Run the full Semantic Input Masker (SIM) pipeline:
        1. Term recognition & masking
        2. Time/date recognition & masking
        Returns self for chaining.
        """
        print("[SIM] Processing user input...")
        self.term_recognition()
        self.time_recognition()
        return self


if __name__ == '__main__':
    inp = user_input_init("Did Blake book Adan Dinning on 2024-03-15?")
    inp.full_process()
    hints = inp.gen_hints()
    print("\nMasked question:", inp.trans)
    print("Hints:", hints)