import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'service_center.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # 1. users table
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer', 'store_owner')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 2. service_records table
    conn.execute('''CREATE TABLE IF NOT EXISTS service_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vehicle_type TEXT,
        vehicle_brand TEXT,
        vehicle_model TEXT,
        vehicle_age INTEGER,
        km_driven INTEGER,
        symptoms TEXT,
        predicted_category TEXT,
        urgency TEXT,
        actual_cost REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Check if user_id column exists in existing service_records if table existed prior
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(service_records)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in columns:
        try:
            conn.execute("ALTER TABLE service_records ADD COLUMN user_id INTEGER REFERENCES users(id)")
        except Exception:
            pass

    # 3. feedback table
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        user_id INTEGER,
        accuracy_rating INTEGER CHECK(accuracy_rating BETWEEN 1 AND 5),
        actual_cost REAL,
        comments TEXT,
        submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES service_records(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def create_user(username, password, role='customer'):
    if role not in ('customer', 'store_owner'):
        return False, "Role must be 'customer' or 'store_owner'."
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                     (username, generate_password_hash(password), role))
        conn.commit()
        return True, "User created successfully."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_db()
    row = conn.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if row and check_password_hash(row['password_hash'], password):
        return {'id': row['id'], 'username': row['username'], 'role': row['role']}
    return None

if __name__ == '__main__':
    init_db()