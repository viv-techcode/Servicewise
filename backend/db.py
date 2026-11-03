import os
import sqlite3
import csv
import json
import random
from werkzeug.security import generate_password_hash, check_password_hash
from backend.vehicles import VEHICLES

DB_PATH = os.environ.get('SERVICEWISE_DB_PATH', os.path.join(os.path.dirname(__file__), 'data', 'service_center.db'))

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
        state TEXT,
        vehicle_age INTEGER,
        km_driven INTEGER,
        symptoms TEXT,
        predicted_category TEXT,
        predicted_faults_json TEXT,
        predicted_costs_json TEXT,
        predicted_cost_min REAL,
        predicted_cost_max REAL,
        urgency TEXT,
        actual_cost REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        source_record_key TEXT UNIQUE,
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
    if 'predicted_faults_json' not in columns:
        conn.execute("ALTER TABLE service_records ADD COLUMN predicted_faults_json TEXT")
    if 'state' not in columns:
        conn.execute("ALTER TABLE service_records ADD COLUMN state TEXT DEFAULT 'Global'")
    for column, sql_type in {'vehicle_age': 'INTEGER', 'km_driven': 'INTEGER', 'predicted_costs_json': 'TEXT', 'predicted_cost_min': 'REAL', 'predicted_cost_max': 'REAL', 'source_record_key': 'TEXT'}.items():
        if column not in columns:
            conn.execute(f'ALTER TABLE service_records ADD COLUMN {column} {sql_type}')
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_service_records_source_key ON service_records(source_record_key)')

    # 3. feedback table
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory_stock (
        part_id TEXT PRIMARY KEY, part_name TEXT NOT NULL, fault_category TEXT NOT NULL,
        vehicle_type TEXT NOT NULL, compatible_models_json TEXT NOT NULL,
        opening_stock INTEGER NOT NULL, stock INTEGER NOT NULL, reorder_level INTEGER NOT NULL,
        unit_cost REAL NOT NULL, unit_price REAL NOT NULL, supplier_lead_time_days INTEGER NOT NULL,
        supplier TEXT, snapshot_date TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory_log (
        event_id TEXT PRIMARY KEY, event_date TEXT NOT NULL, event_time TEXT NOT NULL,
        event_type TEXT NOT NULL, job_id TEXT, part_id TEXT NOT NULL,
        quantity_change INTEGER NOT NULL, stock_after INTEGER NOT NULL,
        unit_cost REAL NOT NULL, unit_price REAL NOT NULL, supplier TEXT, notes TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS monthly_summary (
        month TEXT PRIMARY KEY, jobs INTEGER NOT NULL, revenue REAL NOT NULL,
        parts_cost REAL NOT NULL, labour_cost REAL NOT NULL, gross_profit REAL NOT NULL,
        gross_loss REAL NOT NULL, gross_margin REAL NOT NULL, discount REAL NOT NULL,
        rent_overhead REAL NOT NULL, salary_overhead REAL NOT NULL, utilities_overhead REAL NOT NULL,
        total_overheads REAL NOT NULL, net_profit REAL NOT NULL, profit_loss REAL NOT NULL,
        stockout_delay_days INTEGER NOT NULL, mom_change_pct REAL, trend TEXT
    )''')

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

    # Additive migrations keep databases created by earlier releases usable.
    cursor.execute("PRAGMA table_info(feedback)")
    feedback_columns = {row[1] for row in cursor.fetchall()}
    additions = {
        'predicted_faults_json': 'TEXT',
        'predicted_costs_json': 'TEXT',
        'corrected_faults_json': 'TEXT',
        'actual_fault_costs_json': 'TEXT',
        'state': 'TEXT',
        'vehicle_details_json': 'TEXT',
        'review_status': "TEXT NOT NULL DEFAULT 'pending'",
        'reviewed_at': 'DATETIME',
    }
    for column, sql_type in additions.items():
        if column not in feedback_columns:
            conn.execute(f'ALTER TABLE feedback ADD COLUMN {column} {sql_type}')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_review_status ON feedback(review_status)")
    conn.execute("UPDATE service_records SET state = 'Global'")
    conn.execute("UPDATE feedback SET state = 'Global'")
    active_vehicle_clauses = []
    active_vehicle_values = []
    for vehicle_type, brands in VEHICLES.items():
        for brand, models in brands.items():
            active_vehicle_clauses.append('(vehicle_type = ? AND vehicle_brand = ? AND vehicle_model IN (' + ','.join('?' for _ in models) + '))')
            active_vehicle_values.extend((vehicle_type, brand, *models))
    active_vehicle_sql = ' OR '.join(active_vehicle_clauses)
    inactive_vehicle_sql = f'(vehicle_type IS NULL OR vehicle_brand IS NULL OR vehicle_model IS NULL OR NOT ({active_vehicle_sql}))'
    conn.execute(
        f'''DELETE FROM feedback WHERE record_id IN (
            SELECT id FROM service_records WHERE {inactive_vehicle_sql}
        )''', active_vehicle_values
    )
    conn.execute(f'DELETE FROM service_records WHERE {inactive_vehicle_sql}', active_vehicle_values)
    conn.commit()
    conn.close()

def import_service_records_csv(csv_path):
    """Synchronize imported service records with the active CSV source."""
    if not os.path.exists(csv_path):
        return {'imported': 0, 'skipped': 0}

    conn = get_db()
    imported = 0
    skipped = 0
    active_keys = set()
    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as handle:
            rows = list(csv.DictReader(handle))
            for row in rows:
                job_id = row.get('job_id', '')
                source_key = f"{os.path.basename(csv_path)}:{job_id}"
                if not job_id:
                    continue
                active_keys.add(source_key)

                categories = list(dict.fromkeys(category.strip() for category in row.get('faults', '').split(';') if category.strip()))
                if not categories:
                    categories = [row.get('primary_fault', 'General Maintenance')]
                predicted_faults = [{'category': category, 'confidence': None} for category in categories]
                actual_cost = float(row['customer_charge']) if row.get('customer_charge') else 0.0
                try:
                    per_fault_cost = json.loads(row.get('per_fault_cost') or '{}')
                except (TypeError, json.JSONDecodeError):
                    per_fault_cost = {}
                prediction_snapshot = {
                    'minimum': None,
                    'maximum': None,
                    'estimate': actual_cost,
                    'fault_cost_breakdown': [{'category': category, 'customer_charge': per_fault_cost.get(category)} for category in categories],
                    'shared_visit_discount': None,
                    'cost_estimate_basis': 'historical workshop dataset row'
                }
                symptoms = row.get('symptoms', '').strip()
                urgency = {'low': 'Low', 'medium': 'Medium', 'high': 'High', 'critical': 'High'}.get(row.get('severity', '').lower(), 'Low')
                timestamp = f"{row.get('service_date', '')} {row.get('service_time', '00:00:00')}".strip()
                record_values = (
                    row.get('vehicle_type'), row.get('brand'), row.get('model'), 'Global',
                    int(row['age']) if row.get('age') else None,
                    int(row['km_driven']) if row.get('km_driven') else None,
                    symptoms, row.get('primary_fault') or categories[0],
                    json.dumps(predicted_faults), json.dumps(prediction_snapshot),
                    None, None, urgency, actual_cost, timestamp,
                )
                existing = conn.execute(
                    '''SELECT id, vehicle_type, vehicle_brand, vehicle_model, state, vehicle_age,
                       km_driven, symptoms, predicted_category, predicted_faults_json,
                       predicted_costs_json, predicted_cost_min, predicted_cost_max, urgency,
                       actual_cost, timestamp FROM service_records WHERE source_record_key = ?''',
                    (source_key,)
                ).fetchone()
                if existing:
                    old_values = tuple(existing[key] for key in (
                        'vehicle_type', 'vehicle_brand', 'vehicle_model', 'state', 'vehicle_age',
                        'km_driven', 'symptoms', 'predicted_category', 'predicted_faults_json',
                        'predicted_costs_json', 'predicted_cost_min', 'predicted_cost_max', 'urgency',
                        'actual_cost', 'timestamp'
                    ))
                    if old_values == record_values:
                        skipped += 1
                        continue
                    conn.execute('DELETE FROM feedback WHERE record_id = ?', (existing['id'],))
                    conn.execute(
                        '''UPDATE service_records SET vehicle_type=?, vehicle_brand=?, vehicle_model=?, state=?,
                           vehicle_age=?, km_driven=?, symptoms=?, predicted_category=?, predicted_faults_json=?,
                           predicted_costs_json=?, predicted_cost_min=?, predicted_cost_max=?, urgency=?, actual_cost=?,
                           timestamp=? WHERE id=?''', (*record_values, existing['id'])
                    )
                    imported += 1
                else:
                    conn.execute(
                        '''INSERT INTO service_records (
                            user_id, vehicle_type, vehicle_brand, vehicle_model, state,
                            vehicle_age, km_driven, symptoms, predicted_category,
                            predicted_faults_json, predicted_costs_json, predicted_cost_min,
                            predicted_cost_max, urgency, actual_cost, timestamp, source_record_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (None, *record_values, source_key)
                    )
                    imported += 1

        # Keep imported history synchronized with the one active CSV. Rows
        # created by app users have a NULL source key and are unaffected.
        source_prefix = f"{os.path.basename(csv_path)}:"
        for old in conn.execute(
            'SELECT id, source_record_key FROM service_records WHERE source_record_key IS NOT NULL'
        ).fetchall():
            if not old['source_record_key'].startswith(source_prefix) or old['source_record_key'] not in active_keys:
                conn.execute('DELETE FROM feedback WHERE record_id = ?', (old['id'],))
                conn.execute('DELETE FROM service_records WHERE id = ?', (old['id'],))

        # Seed demonstration feedback once for a clean demo database, never reset user feedback.
        if imported and not conn.execute('SELECT 1 FROM feedback LIMIT 1').fetchone():
            feedback_records = conn.execute(
                'SELECT id, actual_cost FROM service_records WHERE source_record_key IS NOT NULL ORDER BY id LIMIT 999'
            ).fetchall()
            ratings = [5] * 250 + [4] * 399 + [3] * 250 + [2] * 100
            random.shuffle(ratings)
            for idx, (record_id, actual_cost) in enumerate(feedback_records[:len(ratings)]):
                conn.execute(
                    '''INSERT INTO feedback (record_id, accuracy_rating, actual_cost, comments, review_status)
                       VALUES (?, ?, ?, ?, 'approved')''',
                    (record_id, ratings[idx], float(actual_cost) if actual_cost is not None else None,
                     'Demonstration feedback record; not a verified workshop bill.')
                )

        conn.commit()
        return {'imported': imported, 'skipped': skipped}
    finally:
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


def import_store_data(data_dir=None):
    """Refresh inventory snapshots, movement ledger, and monthly finance tables from source CSVs."""
    data_dir = data_dir or os.path.join(os.path.dirname(__file__), 'data')
    init_db()
    conn = get_db()
    try:
        specs = {
            'inventory_stock': ('inventory_stock.csv', 'part_id'),
            'inventory_log': ('inventory_log.csv', 'event_id'),
            'monthly_summary': ('monthly_summary.csv', 'month'),
        }
        for table, (filename, key) in specs.items():
            path = os.path.join(data_dir, filename)
            with open(path, newline='', encoding='utf-8-sig') as handle:
                rows = list(csv.DictReader(handle))
            source_columns = list(rows[0]) if rows else []
            if not source_columns: continue
            columns = ['compatible_models_json' if col == 'compatible_models' else col for col in source_columns]
            conn.execute(f'DELETE FROM {table}')
            placeholders = ','.join('?' for _ in columns)
            names = ','.join(columns)
            for row in rows:
                values = [json.dumps(json.loads(row[col]), ensure_ascii=False) if col == 'compatible_models' else row[col] for col in source_columns]
                conn.execute(f'INSERT INTO {table} ({names}) VALUES ({placeholders})', values)
        conn.commit()
        return {table: conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in specs}
    finally:
        conn.close()
