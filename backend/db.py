import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'servicewise.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS service_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vehicle_type TEXT,
        vehicle_brand TEXT,
        vehicle_model TEXT,
        symptoms TEXT,
        predicted_category TEXT,
        urgency TEXT,
        actual_cost REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
