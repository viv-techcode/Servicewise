import os
import json
import secrets
import math
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from backend.ml.predictor import Predictor
from backend.ml.train_models import CATEGORIES
import backend.db as db

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.environ.get('SECRET_KEY', 'servicewise_dev_secret_key_2026')

# Initialize SQLite database tables automatically at startup (for Gunicorn & Render deployments)
db.init_db()
db.import_service_records_csv(os.path.join(os.path.dirname(__file__), 'data', 'service_records_balanced_3000.csv'))

predictor = Predictor()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                return jsonify({"error": "Authentication required."}), 401
            if user.get('role') not in allowed_roles:
                return jsonify({"error": "Forbidden: Insufficient role permissions."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_predict_input(data):
    """Return (cleaned_data, None) or (None, error_message)."""
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    errors = []
    vehicle_type = str(data.get('vehicle_type', '')).strip().lower()
    if vehicle_type not in ('bike', 'car', 'cycle'):
        errors.append("vehicle_type must be 'bike' or 'car'.")

    vehicle_brand = str(data.get('vehicle_brand', '')).strip()[:50]
    if not vehicle_brand:
        errors.append("vehicle_brand is required.")

    vehicle_model = str(data.get('vehicle_model', '')).strip()[:50]
    if not vehicle_model:
        errors.append("vehicle_model is required.")

    try:
        vehicle_age = int(data.get('vehicle_age', -1))
        if not (0 <= vehicle_age <= 30):
            errors.append("vehicle_age must be between 0 and 30.")
    except (ValueError, TypeError):
        errors.append("vehicle_age must be a valid integer.")
        vehicle_age = None

    try:
        km_driven = int(data.get('km_driven', -1))
        if not (0 <= km_driven <= 500000):
            errors.append("km_driven must be between 0 and 500,000.")
    except (ValueError, TypeError):
        errors.append("km_driven must be a valid integer.")
        km_driven = None

    symptoms = str(data.get('symptoms', '')).strip()[:1000]
    if len(symptoms) < 5:
        errors.append("symptoms must be at least 5 characters.")

    supported_states = ('Uttar Pradesh', 'Delhi', 'Haryana', 'Punjab', 'Rajasthan', 'Uttarakhand', 'Himachal Pradesh', 'Jammu and Kashmir', 'Ladakh')
    state = str(data.get('state', '')).strip()
    if state and state not in supported_states:
        errors.append("state must be a supported North Indian state or blank.")

    if errors:
        return None, " | ".join(errors)

    return {
        'vehicle_type': vehicle_type,
        'vehicle_brand': vehicle_brand,
        'vehicle_model': vehicle_model,
        'vehicle_age': vehicle_age,
        'km_driven': km_driven,
        'symptoms': symptoms,
        'state': state or None
    }, None

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found."}), 404

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

# --- Auth Routes ---
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    role = str(data.get('role', 'customer')).strip()

    if len(username) < 3 or len(username) > 30:
        return jsonify({"error": "Username must be 3-30 characters."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if role not in ('customer', 'store_owner'):
        return jsonify({"error": "Role must be 'customer' or 'store_owner'."}), 400

    success, msg = db.create_user(username, password, role)
    if not success:
        return jsonify({"error": msg}), 409

    user = db.authenticate_user(username, password)
    session['user'] = user
    return jsonify({"message": "Account created successfully.", "user": user}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    user = db.authenticate_user(username, password)
    if user:
        session['user'] = user
        return jsonify({"message": "Logged in successfully.", "user": user})
    return jsonify({"error": "Invalid username or password."}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "Logged out successfully."})

@app.route('/api/auth/me')
def auth_me():
    user = session.get('user')
    return jsonify({"user": user}), 200

# --- Predict & Record Routes ---
@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.json
    cleaned, error = validate_predict_input(data)
    if error:
        return jsonify({"error": error}), 400

    result = predictor.predict(cleaned)
    prediction_snapshot = {
        'minimum': result.get('estimated_cost_min'),
        'maximum': result.get('estimated_cost_max'),
        'fault_cost_breakdown': result.get('fault_cost_breakdown', []),
        'shared_visit_discount': result.get('shared_visit_discount'),
        'cost_estimate_basis': result.get('cost_estimate_basis'),
    }

    record_id = None
    user_id = session.get('user', {}).get('id') if session.get('user') else None
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO service_records (user_id, vehicle_type, vehicle_brand, vehicle_model, state, vehicle_age, km_driven, symptoms, predicted_category, predicted_faults_json, predicted_costs_json, predicted_cost_min, predicted_cost_max, urgency, actual_cost) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, cleaned['vehicle_type'], cleaned['vehicle_brand'], cleaned['vehicle_model'], cleaned['state'], cleaned['vehicle_age'], cleaned['km_driven'], cleaned['symptoms'], result['problem_category'], json.dumps(result['predicted_faults']), json.dumps(prediction_snapshot), result['estimated_cost_min'], result['estimated_cost_max'], result['urgency'], None)
        )
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Could not save service record: {e}"}), 500

    result_payload = dict(result)
    result_payload['record_id'] = record_id
    result_payload['vehicle_details'] = {key: cleaned.get(key) for key in ('vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'state')}
    result_payload['prediction_snapshot'] = prediction_snapshot
    return jsonify(result_payload)

@app.route('/api/records', methods=['GET'])
def get_records():
    try:
        user = session.get('user')
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=20, type=int)
        page = max(1, page)
        per_page = min(max(1, per_page), 100)
        offset = (page - 1) * per_page
        sort_order = request.args.get('sort', default='desc', type=str).lower()
        order_sql = 'ASC' if sort_order == 'asc' else 'DESC'

        conn = db.get_db()
        if user and user.get('role') == 'store_owner':
            count_cur = conn.execute('SELECT COUNT(*) as total FROM service_records')
            total = count_cur.fetchone()['total']
            cursor = conn.execute(
                f'SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, state, vehicle_age, km_driven, symptoms, predicted_category, predicted_faults_json, predicted_cost_min, predicted_cost_max, urgency, actual_cost, timestamp FROM service_records ORDER BY id {order_sql} LIMIT ? OFFSET ?',
                (per_page, offset)
            )
        elif user and user.get('role') == 'customer':
            count_cur = conn.execute('SELECT COUNT(*) as total FROM service_records WHERE user_id = ?', (user['id'],))
            total = count_cur.fetchone()['total']
            cursor = conn.execute(
                f'SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, state, vehicle_age, km_driven, symptoms, predicted_category, predicted_faults_json, predicted_cost_min, predicted_cost_max, urgency, actual_cost, timestamp FROM service_records WHERE user_id = ? ORDER BY id {order_sql} LIMIT ? OFFSET ?',
                (user['id'], per_page, offset)
            )
        else:
            count_cur = conn.execute('SELECT COUNT(*) as total FROM service_records')
            total = count_cur.fetchone()['total']
            cursor = conn.execute(
                f'SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, state, vehicle_age, km_driven, symptoms, predicted_category, predicted_faults_json, predicted_cost_min, predicted_cost_max, urgency, actual_cost, timestamp FROM service_records ORDER BY id {order_sql} LIMIT ? OFFSET ?',
                (per_page, offset)
            )
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            try:
                row['predicted_faults'] = json.loads(row.pop('predicted_faults_json')) if row.get('predicted_faults_json') else [{'category': row['predicted_category'], 'confidence': None}]
            except (TypeError, json.JSONDecodeError):
                row['predicted_faults'] = [{'category': row['predicted_category'], 'confidence': None}]
            fb = conn.execute('SELECT id, review_status, corrected_faults_json, actual_cost, actual_fault_costs_json, predicted_faults_json, predicted_costs_json FROM feedback WHERE record_id = ? ORDER BY id DESC LIMIT 1', (row['id'],)).fetchone()
            row['feedback'] = dict(fb) if fb else None
            if row['feedback']:
                try: row['feedback']['corrected_faults'] = json.loads(row['feedback'].pop('corrected_faults_json') or '[]')
                except (TypeError, json.JSONDecodeError): row['feedback']['corrected_faults'] = []
                try: row['feedback']['actual_fault_costs'] = json.loads(row['feedback'].pop('actual_fault_costs_json') or '{}')
                except (TypeError, json.JSONDecodeError): row['feedback']['actual_fault_costs'] = {}
                try: row['feedback']['predicted_faults'] = json.loads(row['feedback'].pop('predicted_faults_json') or '[]')
                except (TypeError, json.JSONDecodeError): row['feedback']['predicted_faults'] = []
                try:
                    saved_costs = json.loads(row['feedback'].pop('predicted_costs_json') or '{}')
                    row['feedback']['predicted_cost'] = saved_costs.get('maximum')
                    row['feedback']['predicted_cost_min'] = saved_costs.get('minimum')
                    row['feedback']['predicted_fault_cost_breakdown'] = saved_costs.get('fault_cost_breakdown', [])
                    row['feedback']['shared_visit_discount'] = saved_costs.get('shared_visit_discount')
                except (TypeError, json.JSONDecodeError): row['feedback']['predicted_cost'] = None
        conn.close()

        if 'page' in request.args or 'per_page' in request.args:
            return jsonify({
                "records": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page)
            })
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Feedback Route ---
def validate_feedback_input(data):
    if not isinstance(data, dict):
        return None, 'Request body must be a JSON object.'
    record_id = data.get('record_id')
    rating = data.get('accuracy_rating')
    actual_cost = data.get('actual_total_cost', data.get('actual_cost'))
    corrected = data.get('corrected_faults')
    actual_fault_costs = data.get('actual_fault_costs', {})
    state = data.get('state')
    supported_states = ('Uttar Pradesh', 'Delhi', 'Haryana', 'Punjab', 'Rajasthan', 'Uttarakhand', 'Himachal Pradesh', 'Jammu and Kashmir', 'Ladakh')
    try: record_id = int(record_id)
    except (ValueError, TypeError): return None, 'record_id must be a positive integer.'
    if record_id <= 0: return None, 'record_id must be a positive integer.'
    if rating is not None and (not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5):
        return None, 'accuracy_rating must be an integer from 1 to 5.'
    if actual_cost is not None:
        if isinstance(actual_cost, bool) or not isinstance(actual_cost, (int, float)):
            return None, 'actual_total_cost must be a numeric value.'
        try: actual_cost = float(actual_cost)
        except (ValueError, TypeError): return None, 'actual_total_cost must be a valid non-negative amount.'
        if not math.isfinite(actual_cost) or actual_cost < 0: return None, 'actual_total_cost must be a valid non-negative amount.'
    if corrected is not None:
        if not isinstance(corrected, list) or not corrected or any(not isinstance(label, str) or label not in CATEGORIES for label in corrected) or len(set(corrected)) != len(corrected):
            return None, 'corrected_faults must be a non-empty list of unique supported fault categories.'
    if not isinstance(actual_fault_costs, dict) or any(k not in CATEGORIES for k in actual_fault_costs):
        return None, 'actual_fault_costs must map supported fault categories to costs.'
    try:
        clean_fault_costs = {k: float(v) for k, v in actual_fault_costs.items()}
    except (ValueError, TypeError): return None, 'Per-fault costs must be non-negative numbers.'
    if any(not math.isfinite(v) or v < 0 for v in clean_fault_costs.values()):
        return None, 'Per-fault costs must be non-negative numbers.'
    if clean_fault_costs and corrected is not None and set(clean_fault_costs) - set(corrected):
        return None, 'Per-fault costs may only refer to corrected faults.'
    if state is not None and state != '' and state not in supported_states:
        return None, 'state must be a supported North Indian state or blank.'
    details = data.get('vehicle_details', {})
    if details is not None and not isinstance(details, dict): return None, 'vehicle_details must be an object.'
    comments = str(data.get('comments', '')).strip()[:500]
    return {'record_id': record_id, 'rating': rating, 'actual_cost': actual_cost, 'corrected_faults': corrected,
            'actual_fault_costs': clean_fault_costs, 'state': state or None, 'vehicle_details': details or {}, 'comments': comments}, None

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    cleaned, error = validate_feedback_input(request.get_json(silent=True))
    if error: return jsonify({'error': error}), 400
    record_id, rating, actual_cost = cleaned['record_id'], cleaned['rating'], cleaned['actual_cost']
    comments = cleaned['comments']
    user_id = session.get('user', {}).get('id') if session.get('user') else None
    try:
        conn = db.get_db()
        record = conn.execute('SELECT * FROM service_records WHERE id = ?', (record_id,)).fetchone()
        if not record:
            conn.close(); return jsonify({'error': 'record_id was not found.'}), 404
        predicted_faults = json.loads(record['predicted_faults_json'] or '[]') if record['predicted_faults_json'] else [{'category': record['predicted_category'], 'confidence': None}]
        details = {'vehicle_type': record['vehicle_type'], 'vehicle_brand': record['vehicle_brand'], 'vehicle_model': record['vehicle_model'], 'vehicle_age': record['vehicle_age'], 'km_driven': record['km_driven']}
        corrected_labels = cleaned['corrected_faults']
        if not details.get('vehicle_type') or not details.get('vehicle_brand') or not details.get('vehicle_model'):
            conn.close(); return jsonify({'error': 'Feedback requires vehicle details from its service record.'}), 400
        try:
            predicted_cost_snapshot = json.loads(record['predicted_costs_json'] or '{}')
        except (TypeError, json.JSONDecodeError):
            predicted_cost_snapshot = {'minimum': record['predicted_cost_min'], 'maximum': record['predicted_cost_max'], 'fault_cost_breakdown': [], 'shared_visit_discount': None}
        conn.execute(
            '''INSERT INTO feedback (record_id, user_id, accuracy_rating, actual_cost, comments,
               predicted_faults_json, predicted_costs_json, corrected_faults_json, actual_fault_costs_json,
               state, vehicle_details_json, review_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')''',
            (record_id, user_id, rating, actual_cost, comments, json.dumps(predicted_faults),
             json.dumps(predicted_cost_snapshot),
             json.dumps(cleaned['corrected_faults']) if cleaned['corrected_faults'] is not None else None,
             json.dumps(cleaned['actual_fault_costs']), cleaned['state'] or record['state'], json.dumps(details))
        )
        conn.commit()
        feedback_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        return jsonify({"message": "Feedback submitted for review.", 'feedback_id': feedback_id, 'review_status': 'pending'}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/feedback/<int:feedback_id>/review', methods=['POST'])
@role_required(['store_owner'])
def review_feedback(feedback_id):
    data = request.get_json(silent=True) or {}
    decision = data.get('decision')
    if decision not in ('approved', 'rejected'):
        return jsonify({'error': "decision must be 'approved' or 'rejected'."}), 400
    conn = db.get_db()
    feedback = conn.execute('SELECT corrected_faults_json FROM feedback WHERE id = ?', (feedback_id,)).fetchone()
    if not feedback:
        conn.close(); return jsonify({'error': 'Feedback not found.'}), 404
    if decision == 'approved':
        try: labels = json.loads(feedback['corrected_faults_json'] or 'null')
        except json.JSONDecodeError: labels = None
        if not isinstance(labels, list) or not labels or any(label not in CATEGORIES for label in labels):
            conn.close(); return jsonify({'error': 'Feedback needs valid corrected_faults before approval.'}), 400
        if len(set(labels)) != len(labels):
            conn.close(); return jsonify({'error': 'Corrected fault labels must be unique.'}), 400
    conn.execute('UPDATE feedback SET review_status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?', (decision, feedback_id))
    conn.commit(); conn.close()
    return jsonify({'feedback_id': feedback_id, 'review_status': decision})

# --- Model Metrics Route ---
@app.route('/api/model/metrics')
def model_metrics():
    metrics_path = os.path.join(os.path.dirname(__file__), 'ml', 'model_metrics.json')
    try:
        with open(metrics_path, 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "Model metrics not available."}), 404

# --- Analytics Route ---
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        conn = db.get_db()
        # 1. Total diagnoses count
        total_row = conn.execute('SELECT COUNT(*) as total FROM service_records').fetchone()
        total_diagnoses = total_row['total'] if total_row else 0

        # 2. Problem category distribution
        cat_rows = conn.execute('SELECT predicted_category, COUNT(*) as count FROM service_records GROUP BY predicted_category').fetchall()
        category_distribution = {row['predicted_category'] or 'Unknown': row['count'] for row in cat_rows}

        # 3. Urgency distribution
        urg_rows = conn.execute('SELECT urgency, COUNT(*) as count FROM service_records GROUP BY urgency').fetchall()
        urgency_distribution = {row['urgency'] or 'Unknown': row['count'] for row in urg_rows}

        # 4. Vehicle type split
        vt_rows = conn.execute('SELECT vehicle_type, COUNT(*) as count FROM service_records GROUP BY vehicle_type').fetchall()
        vehicle_type_split = {row['vehicle_type'] or 'other': row['count'] for row in vt_rows}

        # 5. Average repair cost
        cost_row = conn.execute('SELECT AVG(actual_cost) as avg_cost FROM service_records WHERE actual_cost IS NOT NULL').fetchone()
        avg_estimated_cost = round(cost_row['avg_cost'], 2) if (cost_row and cost_row['avg_cost'] is not None) else 0.0

        # 6. Feedback stats
        fb_row = conn.execute('SELECT AVG(accuracy_rating) as avg_rating, COUNT(*) as total_reviews FROM feedback').fetchone()
        feedback_stats = {
            "avg_rating": round(fb_row['avg_rating'], 2) if (fb_row and fb_row['avg_rating'] is not None) else 0.0,
            "total_reviews": fb_row['total_reviews'] if fb_row else 0
        }

        confirmed = conn.execute('''SELECT f.id, f.record_id, f.predicted_faults_json, f.corrected_faults_json,
            f.predicted_costs_json, f.actual_cost, f.actual_fault_costs_json FROM feedback f
            WHERE f.review_status = 'approved' AND f.corrected_faults_json IS NOT NULL''').fetchall()
        fault_exact = []
        cost_errors = []
        comparisons = []
        for item in confirmed:
            try:
                predicted = {x.get('category') for x in json.loads(item['predicted_faults_json'] or '[]') if isinstance(x, dict)}
                actual = set(json.loads(item['corrected_faults_json'] or '[]'))
            except (TypeError, json.JSONDecodeError):
                continue
            exact = predicted == actual
            fault_exact.append(exact)
            predicted_cost = None
            predicted_min = None
            try: per_fault_actual_costs = json.loads(item['actual_fault_costs_json'] or '{}')
            except (TypeError, json.JSONDecodeError): per_fault_actual_costs = {}
            try:
                stored_cost = json.loads(item['predicted_costs_json'] or '{}')
                predicted_cost = float(stored_cost.get('maximum')) if stored_cost.get('maximum') is not None else None
                predicted_min = float(stored_cost.get('minimum')) if stored_cost.get('minimum') is not None else None
            except (TypeError, ValueError, json.JSONDecodeError): pass
            actual_cost = item['actual_cost']
            error = abs(float(actual_cost) - predicted_cost) if actual_cost is not None and predicted_cost is not None else None
            if error is not None and predicted_min is not None and predicted_min <= float(actual_cost) <= predicted_cost:
                error = 0.0
            if error is not None: cost_errors.append(error)
            comparisons.append({'feedback_id': item['id'], 'record_id': item['record_id'],
                'predicted_faults': sorted(x for x in predicted if x), 'confirmed_faults': sorted(actual),
                'missed_faults': sorted(actual - predicted), 'extra_predicted_faults': sorted(predicted - actual),
                'fault_exact_match': exact, 'predicted_cost_min': predicted_min, 'predicted_cost': predicted_cost, 'actual_cost': actual_cost,
                'actual_fault_costs': per_fault_actual_costs,
                'cost_error': error, 'cost_error_percent': (100 * error / float(actual_cost)) if error is not None and float(actual_cost) else None})
        confirmed_analytics = {
            'reviewed_records': len(fault_exact),
            'fault_exact_match_accuracy': round(sum(fault_exact) / len(fault_exact), 4) if fault_exact else None,
            'mean_absolute_cost_error': round(sum(cost_errors) / len(cost_errors), 2) if cost_errors else None,
            'cost_records': len(cost_errors),
        }
        pending_rows = conn.execute("SELECT id, record_id, corrected_faults_json FROM feedback WHERE review_status='pending' ORDER BY submitted_at").fetchall()
        pending_feedback = []
        for item in pending_rows:
            try: labels = json.loads(item['corrected_faults_json'] or '[]')
            except (TypeError, json.JSONDecodeError): labels = []
            pending_feedback.append({'id': item['id'], 'record_id': item['record_id'], 'corrected_faults': labels})

        conn.close()

        return jsonify({
            "total_diagnoses": total_diagnoses,
            "category_distribution": category_distribution,
            "urgency_distribution": urgency_distribution,
            "vehicle_type_split": vehicle_type_split,
            "avg_estimated_cost": avg_estimated_cost,
            "feedback_stats": feedback_stats,
            "confirmed_feedback": confirmed_analytics,
            "confirmed_comparisons": comparisons,
            "pending_feedback": pending_feedback
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    db.init_db()
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
