import sqlite3
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "output", "trustnet.db")

#connection 
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

#craete the db 

def init_database():
    conn = get_connection()
    
    # Table transactions
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # Table users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE,
            full_name     TEXT,
            email         TEXT,
            password_hash TEXT,
            role          TEXT,
            active        INTEGER DEFAULT 1,
            created_at    TEXT
        )
    """)
    
    conn.commit()
    conn.close()

  #save transactions  


def save_transaction(row):
    conn = get_connection()
    conn.execute("""
        INSERT INTO transactions (
            transaction_id, customer, country, category,
            quantity, value, weight, unit_value,
            payment_terms, date, trustnet_score, risk_level,
            explanation, violations, fingerprint, analyzed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        " | ".join(row.get("Explanation_Detail", [])),
        " | ".join(row.get("Rule_Violations", [])),
        str(row.get("Fingerprint_Hash", "")),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def get_all_transactions():
    conn = get_connection()
    
    cursor = conn.execute("""
        SELECT * FROM transactions
        ORDER BY analyzed_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_transactions_by_risk(risk_level):
    conn = get_connection()
    # Getting only transactions with certain level of risk
    cursor = conn.execute("""
        SELECT * FROM transactions
        WHERE risk_level = ?
        ORDER BY trustnet_score DESC
    """, (risk_level,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def search_transactions(keyword):
    conn = get_connection()
    # Serach by keyword
    cursor = conn.execute("""
        SELECT * FROM transactions
        WHERE customer LIKE ?
        OR country LIKE ?
        OR transaction_id LIKE ?
        ORDER BY analyzed_at DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    rows = cursor.fetchall()
    conn.close()
    return rows
# Users functions

def init_default_users():
    import bcrypt
    conn = get_connection()
    
    # Vérifier si des utilisateurs existent déjà
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Créer les 3 utilisateurs par défaut
        default_users = [
            ("admin",     "Administrateur TrustNet", "admin@trustnet.com",     "admin",     "trustnet2024"),
            ("analyste1", "Analyste Commercial",     "analyste@trustnet.com",  "analyste",  "trustnet2024"),
            ("auditeur1", "Auditeur Douanier",       "auditeur@trustnet.com",  "auditeur",  "trustnet2024"),
        ]
        
        for username, full_name, email, role, password in default_users:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
            conn.execute("""
                INSERT INTO users (username, full_name, email, password_hash, role, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (username, full_name, email, hashed, role, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        print(" Utilisateurs par défaut créés dans la base")
    
    conn.close()



def load_transactions_as_dataframe():
    import pandas as pd
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM transactions ORDER BY analyzed_at DESC")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    # Renommer les colonnes pour correspondre au pipeline
    df = df.rename(columns={
        "transaction_id": "Transaction_ID",
        "customer":       "Customer",
        "country":        "Country",
        "category":       "Category",
        "quantity":       "Quantity",
        "value":          "Value",
        "weight":         "Weight",
        "unit_value":     "Unit_Value",
        "payment_terms":  "Payment_Terms",
        "date":           "Date",
        "trustnet_score": "TrustNet_Score",
        "risk_level":     "Risk_Level",
        "explanation":    "Explanation_Detail",
        "violations":     "Rule_Violations",
        "fingerprint":    "Fingerprint_Hash"
    })
    # Reconvertir les explications en listes
    df["Explanation_Detail"] = df["Explanation_Detail"].apply(
        lambda x: x.split(" | ") if isinstance(x, str) and x else []
    )
    df["Rule_Violations"] = df["Rule_Violations"].apply(
        lambda x: x.split(" | ") if isinstance(x, str) and x else []
    )
    return df
