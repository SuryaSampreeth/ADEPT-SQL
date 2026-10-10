import sqlite3
import pandas as pd

sql = """SELECT O.Order_ID, C.Customer_Name, S.Store_Name, O.Order_Date
FROM Customer_Orders O
INNER JOIN Customers C ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID
INNER JOIN Stores S ON CAST(O.Store_ID AS TEXT) = S.Store_ID
WHERE C.Customer_Name = 'Blake'
AND S.Store_Name = 'Shery Photo'"""

print("Running DB query...")
try:
    conn = sqlite3.connect("./sqlite/cre_Drama_Workshop_Groups.sqlite")
    df = pd.read_sql_query(sql, conn)
    print("Rows:", len(df))
    print(df)
except Exception as e:
    print("Error:", e)
