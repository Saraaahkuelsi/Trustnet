import os
import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Essaie PostgreSQL (Supabase) sinon SQLite en fallback
try:
    import streamlit as st
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
except Exception:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")

if SUPABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_TYPE = "postgres"
else:
    import sqlite3
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH  = os.path.join(BASE_DIR, "output", "trustnet.db")
    DB_TYPE = "sqlite"


def get_connection():
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(SUPABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              SERIAL PRIMARY KEY,
            transaction_id  TEXT,
            customer        TEXT,
            country         TEXT,
            category        TEXT,
            quantity        REAL,
            value           REAL,
            weight          REAL,
            unit_value      REAL,
            payment_terms   TEXT,
            date            TEXT,
            trustnet_score  REAL,
            risk_level      TEXT,
            explanation     TEXT,
            violations      TEXT,
            fingerprint     TEXT,
            analyzed_at     TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_transaction(row):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (
            transaction_id, customer, country, category,
            quantity, value, weight, unit_value,
            payment_terms, date, trustnet_score, risk_level,
            explanation, violations, fingerprint, analyzed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        str(row.get("Transaction_ID", "")),
        str(row.get("Customer", "")),
        str(row.get("Country", "")),
        str(row.get("Category", "")),
        float(row.get("Quantity", 0)),
        float(row.get("Value", 0)),
        float(row.get("Weight", 0)),
        float(row.get("Unit_Value", 0)),
        str(row.get("Payment_Terms", "")),
        str(row.get("Date", "")),
        float(row.get("TrustNet_Score", 0)),
        str(row.get("Risk_Level", "")),
        " | ".join(row.get("Explanation_Detail", []) if isinstance(row.get("Explanation_Detail"), list) else []),
        " | ".join(row.get("Rule_Violations", []) if isinstance(row.get("Rule_Violations"), list) else []),
        str(row.get("Fingerprint_Hash", "")),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def get_all_transactions():
    conn = get_connection()
    if DB_TYPE == "postgres":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY analyzed_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transactions_by_risk(risk_level):
    conn = get_connection()
    if DB_TYPE == "postgres":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        WHERE risk_level = %s
        ORDER BY trustnet_score DESC
    """, (risk_level,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_transactions(keyword):
    conn = get_connection()
    if DB_TYPE == "postgres":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        WHERE customer ILIKE %s
        OR country ILIKE %s
        OR transaction_id ILIKE %s
        ORDER BY analyzed_at DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]