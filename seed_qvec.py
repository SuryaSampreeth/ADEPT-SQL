"""
Seed script: generates the qvec.csv file with representative Question-SQL pairs
for the cre_Drama_Workshop_Groups.sqlite tutorial database.

Run this ONCE after setting up your embedding model to populate the CSR store.
Usage:
    python seed_qvec.py
"""

import pandas as pd
import os
import sys

# Make sure we're running from the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from user_input_process import user_input_init
from call_emb import vectorize_localmodel

# ──────────────────────────────────────────────────────────────────────────────
# Representative Question-SQL pairs for cre_Drama_Workshop_Groups.sqlite
# Covers: lookup, count, join, filter, group-by, order-by, aggregation patterns
# ──────────────────────────────────────────────────────────────────────────────
QS_PAIRS = [
    # ── Lookup / Existence ───────────────────────────────────────────────────
    {
        "question": "Did Blake book Adan Dinning?",
        "sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE C.Customer_Name = 'Blake' AND S.Store_Name = 'Adan Dinning'"""
    },
    {
        "question": "Did Harold book Adan Dinning?",
        "sql": """SELECT O.Order_ID, C.Customer_Name, S.Store_Name, O.Order_Date
FROM Customer_Orders O
INNER JOIN Customers C ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID
INNER JOIN Stores S ON CAST(O.Store_ID AS TEXT) = S.Store_ID
WHERE C.Customer_Name = 'Harold' AND S.Store_Name = 'Adan Dinning'"""
    },
    {
        "question": "Did Blake book Shery Photo?",
        "sql": """SELECT O.Order_ID, C.Customer_Name, S.Store_Name, O.Order_Date
FROM Customer_Orders O
INNER JOIN Customers C ON CAST(O.Customer_ID AS TEXT) = C.Customer_ID
INNER JOIN Stores S ON CAST(O.Store_ID AS TEXT) = S.Store_ID
WHERE C.Customer_Name = 'Blake' AND S.Store_Name = 'Shery Photo'"""
    },
    {
        "question": "Did Ephraim book Lur Photo?",
        "sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE C.Customer_Name = 'Ephraim' AND S.Store_Name = 'Lur Photo'"""
    },

    # ── Count queries ─────────────────────────────────────────────────────────
    {
        "question": "How many bookings are there in total?",
        "sql": "SELECT COUNT(*) AS total_bookings FROM Bookings"
    },
    {
        "question": "How many customers are there?",
        "sql": "SELECT COUNT(*) AS total_customers FROM Customers"
    },
    {
        "question": "How many stores are there?",
        "sql": "SELECT COUNT(*) AS total_stores FROM Stores"
    },

    # ── List / Enumerate ──────────────────────────────────────────────────────
    {
        "question": "List all store names.",
        "sql": "SELECT Store_Name FROM Stores ORDER BY Store_Name"
    },
    {
        "question": "List all customer names.",
        "sql": "SELECT Customer_Name FROM Customers ORDER BY Customer_Name"
    },
    {
        "question": "Show all bookings with their status.",
        "sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Status_Code, B.Order_Date
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
ORDER BY B.Order_Date DESC"""
    },

    # ── Bookings per customer ─────────────────────────────────────────────────
    {
        "question": "How many bookings does each customer have?",
        "sql": """SELECT C.Customer_Name, COUNT(B.Booking_ID) AS booking_count
FROM Customers C
LEFT JOIN Bookings B ON C.Customer_ID = B.Customer_ID
GROUP BY C.Customer_Name
ORDER BY booking_count DESC"""
    },
    {
        "question": "Which customer has the most bookings?",
        "sql": """SELECT C.Customer_Name, COUNT(B.Booking_ID) AS booking_count
FROM Customers C
INNER JOIN Bookings B ON C.Customer_ID = B.Customer_ID
GROUP BY C.Customer_Name
ORDER BY booking_count DESC
LIMIT 1"""
    },

    # ── Bookings per store ────────────────────────────────────────────────────
    {
        "question": "How many bookings does each store have?",
        "sql": """SELECT S.Store_Name, COUNT(B.Booking_ID) AS booking_count
FROM Stores S
LEFT JOIN Bookings B ON S.Store_ID = B.Store_ID
GROUP BY S.Store_Name
ORDER BY booking_count DESC"""
    },
    {
        "question": "Which store has the most bookings?",
        "sql": """SELECT S.Store_Name, COUNT(B.Booking_ID) AS booking_count
FROM Stores S
INNER JOIN Bookings B ON S.Store_ID = B.Store_ID
GROUP BY S.Store_Name
ORDER BY booking_count DESC
LIMIT 1"""
    },

    # ── Status filter ─────────────────────────────────────────────────────────
    {
        "question": "Show all bookings with status 'good'.",
        "sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Order_Date
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE B.Status_Code = 'good'"""
    },
    {
        "question": "Show all bookings with status 'stop'.",
        "sql": """SELECT B.Booking_ID, C.Customer_Name, S.Store_Name, B.Order_Date
FROM Bookings B
INNER JOIN Customers C ON B.Customer_ID = C.Customer_ID
INNER JOIN Stores S ON B.Store_ID = S.Store_ID
WHERE B.Status_Code = 'stop'"""
    },

    # ── Services ──────────────────────────────────────────────────────────────
    {
        "question": "What services are available and what are their prices?",
        "sql": """SELECT S.Product_Name, S.Service_Type_Code, S.Product_Price
FROM Services S
ORDER BY S.Product_Price DESC"""
    },
    {
        "question": "List all services booked in each booking.",
        "sql": """SELECT B.Booking_ID, SV.Product_Name, SV.Product_Price
FROM Bookings_Services BS
INNER JOIN Bookings B ON BS.Order_ID = B.Booking_ID
INNER JOIN Services SV ON BS.Product_ID = SV.Service_ID
ORDER BY B.Booking_ID"""
    },

    # ── Performers ────────────────────────────────────────────────────────────
    {
        "question": "List all performers and their phone numbers.",
        "sql": """SELECT Customer_Name, Customer_Phone
FROM Performers
ORDER BY Customer_Name"""
    },
    {
        "question": "Show the names of all performers.",
        "sql": """SELECT Customer_Name
FROM Performers
ORDER BY Customer_Name"""
    },
    {
        "question": "Which performers are in each booking?",
        "sql": """SELECT B.Booking_ID, P.Customer_Name AS Performer_Name
FROM Performers_in_Bookings PB
INNER JOIN Bookings B ON PB.Order_ID = B.Booking_ID
INNER JOIN Performers P ON PB.Performer_ID = P.Performer_ID
ORDER BY B.Booking_ID"""
    },
]


def seed_qvec(output_path="./backend/qvec.csv", emb_name="local model"):
    print(f"Seeding {len(QS_PAIRS)} Question-SQL pairs into {output_path} ...")
    emb = {"name": emb_name, "url": "", "token": ""}

    rows = []
    for i, qs in enumerate(QS_PAIRS):
        q = qs["question"]
        sql = qs["sql"]

        # Apply SIM masking to the question before vectorizing
        masked = user_input_init(q).full_process()
        qmask = masked.trans

        # Vectorize the masked question
        if emb_name == "local model":
            qvec = vectorize_localmodel(qmask)
        else:
            from call_emb import callm3e
            qvec = callm3e(emb).init_prompt(qmask).call()

        if qvec == 'Emb Fail':
            print(f"  [FAIL] [{i+1}/{len(QS_PAIRS)}] FAILED to embed: {q[:60]}")
            continue

        rows.append({
            "question": q,
            "qmask": qmask,
            "qvec": str(qvec),
            "sql": sql
        })
        print(f"  [OK] [{i+1}/{len(QS_PAIRS)}] {q[:60]}")

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=True)
    print(f"\nDone! {len(rows)} pairs saved to {output_path}")
    return df


if __name__ == "__main__":
    seed_qvec()
