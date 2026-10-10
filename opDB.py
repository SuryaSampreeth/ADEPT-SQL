from sqlalchemy import create_engine, MetaData, text
import pandas as pd
import sqlite3
import os

current_dir = os.getcwd()


class localsqlite():
    def __init__(self, db_path):
        self.db_path = db_path

    def conn(self):
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.connection = self.engine.connect()
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.connection, resolve_fks=False)
        return self

    def exesql(self, sql):
        df = pd.read_sql_query(text(sql), self.engine).dropna(how='all')
        return df

    def get_schema_as_df(self):
        """
        Dynamically extract table + column metadata from the connected SQLite DB.
        Returns a DataFrame with columns: Table, Table Description, Column, Column Description
        (Table Description and Column Description are blank by default — user fills them in the UI)
        """
        rows = []
        for table_name, table_obj in self.metadata.tables.items():
            for col in table_obj.columns:
                rows.append({
                    'Table': table_name,
                    'Table Description': '',
                    'Column': col.name,
                    'Column Description': col.name.replace('_', ' ').title()
                })
        return pd.DataFrame(rows)

    def get_all_table_names(self):
        return list(self.metadata.tables.keys())

    def get_columns_for_table(self, table_name):
        if table_name in self.metadata.tables:
            return list(self.metadata.tables[table_name].columns.keys())
        return []

    def get_schema_summary(self, broken_sql: str = "", error_msg: str = "") -> str:
        """
        Dynamically extracts table and column names from the connected SQLite DB.
        Prioritizes tables referenced in the broken SQL query or error message so the
        LLM immediately sees the exact valid columns for the failing table.
        """
        lines = []
        all_tables = self.metadata.tables

        # Check which table names appear in the broken SQL or error message
        context_str = f"{broken_sql} {error_msg}".lower()
        focus_tables = [
            t for t in all_tables.keys()
            if t.lower() in context_str
        ]

        if focus_tables:
            lines.append("--- Target Table(s) in Failing Query ---")
            for t in focus_tables:
                cols = [c.name for c in all_tables[t].columns]
                lines.append(f"Table: {t}")
                lines.append(f"Columns: {', '.join(cols)}")
                lines.append("")

        lines.append("--- All Available Database Tables & Columns ---")
        for t, obj in all_tables.items():
            if t in focus_tables:
                continue
            cols = [c.name for c in obj.columns]
            lines.append(f"Table: {t}")
            lines.append(f"Columns: {', '.join(cols)}")
            lines.append("")

        return "\n".join(lines).strip()



if __name__ == "__main__":
    dbconn = localsqlite('./sqlite/cre_Drama_Workshop_Groups.sqlite').conn()
    sql = """
    SELECT *
    FROM Bookings B
    INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
    INNER JOIN Stores S ON B.Store_ID = S.Store_ID
    WHERE Customer_Name = 'Blake' AND Store_Name = 'Adan Dinning'
    """
    df = dbconn.exesql(sql)
    print(df)
    print("\nSchema extract:")
    print(dbconn.get_schema_as_df())
