import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "pharma_algo.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            name TEXT,
            cik TEXT,
            market_cap REAL,
            cash REAL,
            burn_rate REAL,
            float_shares INTEGER,
            short_interest REAL,
            short_percent_float REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS catalysts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER REFERENCES companies(id),
            drug_name TEXT,
            indication TEXT,
            catalyst_type TEXT,
            catalyst_date TEXT,
            date_reliability TEXT,
            date_source TEXT,
            fda_designations TEXT,
            crl_precedente INTEGER DEFAULT 0,
            nct_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalyst_id INTEGER REFERENCES catalysts(id),
            score_date TEXT,
            score_scientifico INTEGER,
            score_movimento INTEGER,
            ev_stimato REAL,
            timing TEXT,
            llm_output TEXT,
            segnali_positivi TEXT,
            rischi TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalyst_id INTEGER REFERENCES catalysts(id),
            status TEXT DEFAULT 'WATCHLIST',
            entry_price REAL,
            entry_date TEXT,
            stop_price REAL,
            target_parziale REAL,
            target_finale REAL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS daily_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalyst_id INTEGER REFERENCES catalysts(id),
            update_date TEXT,
            trigger_type TEXT,
            descrizione TEXT,
            azione_suggerita TEXT,
            ev_precedente REAL,
            ev_aggiornato REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
