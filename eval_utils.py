"""
eval_utils.py — Execution Match helper utilities for ADEPT-SQL dual-model evaluation.

Provides a robust DataFrame comparison function for checking whether two SQL queries
produce semantically equivalent results (ignoring row/column ordering and minor
type/formatting differences).
"""

import pandas as pd
import numpy as np


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a DataFrame for comparison by:
    - Lowercasing and stripping column names
    - Sorting columns alphabetically
    - Converting all values to lowercase stripped strings
    - Sorting rows by all columns
    - Resetting index
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # Normalize column names
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

    # Sort columns alphabetically
    df = df.reindex(sorted(df.columns), axis=1)

    # Convert all values to string, lowercase, strip whitespace
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # Sort rows by all column values
    df = df.sort_values(by=list(df.columns)).reset_index(drop=True)

    return df


def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    """
    Compare two DataFrames using Execution Match semantics.

    Returns True if both DataFrames are considered equivalent:
    - Both None or both empty → True
    - One empty, one not → False
    - Otherwise, normalize and compare using pandas .equals()

    Args:
        df1: First DataFrame (e.g., from Model A SQL execution)
        df2: Second DataFrame (e.g., from Model B or Gold SQL execution)

    Returns:
        bool: True if execution results match, False otherwise.
    """
    # Handle None cases
    df1_empty = df1 is None or (isinstance(df1, pd.DataFrame) and df1.empty)
    df2_empty = df2 is None or (isinstance(df2, pd.DataFrame) and df2.empty)

    if df1_empty and df2_empty:
        return True
    if df1_empty or df2_empty:
        return False

    try:
        n1 = normalize_df(df1)
        n2 = normalize_df(df2)

        # Must have same shape
        if n1.shape != n2.shape:
            return False

        return n1.equals(n2)

    except Exception as e:
        print(f'[EvalUtils] compare_dataframes error: {e}')
        return False


def execution_match_label(df1: pd.DataFrame, df2: pd.DataFrame) -> str:
    """
    Return a human-readable execution match label.

    Returns:
        '✅ MATCH' or '❌ MISMATCH'
    """
    return '✅ MATCH' if compare_dataframes(df1, df2) else '❌ MISMATCH'


def run_sql_safe(sql: str, db_dict: dict):
    """
    Safely execute a SQL query on the configured database.

    Args:
        sql: SQL string to execute.
        db_dict: Database config dict with 'sqlite_path' key.

    Returns:
        (DataFrame | None, error_str | None)
    """
    from opDB import localsqlite

    if not sql or not sql.strip():
        return None, 'Empty SQL'

    try:
        dbconn = localsqlite(db_dict['sqlite_path']).conn()
        df = dbconn.exesql(sql)
        # Remove duplicate columns
        duplicate_cols = df.columns[df.columns.duplicated()]
        df.drop(columns=duplicate_cols, inplace=True)
        return df, None
    except Exception as e:
        return None, str(e)


if __name__ == '__main__':
    # Quick self-test
    df_a = pd.DataFrame({'Name': ['Alice', 'Bob'], 'Age': [30, 25]})
    df_b = pd.DataFrame({'Age': ['25', '30'], 'Name': ['bob', 'alice']})
    print('Test 1 (should be MATCH):', execution_match_label(df_a, df_b))

    df_c = pd.DataFrame({'Name': ['Alice'], 'Age': [30]})
    print('Test 2 (should be MISMATCH):', execution_match_label(df_a, df_c))

    print('Test 3 (both empty):', execution_match_label(pd.DataFrame(), pd.DataFrame()))
    print('Test 4 (one empty):', execution_match_label(df_a, pd.DataFrame()))
