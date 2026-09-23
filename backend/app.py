import os
import json
import secrets
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from backend.ml.predictor import Predictor
import backend.db as db

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.environ.get('SECRET_KEY', 'servicewise_dev_secret_key_2026')

# Initialize SQLite database tables automatically at startup (for Gunicorn & Render deployments)
db.init_db()

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

    if errors:
        return None, " | ".join(errors)

    return {
        'vehicle_type': vehicle_type,
        'vehicle_brand': vehicle_brand,
        'vehicle_model': vehicle_model,
        'vehicle_age': vehicle_age,
        'km_driven': km_driven,
        'symptoms': symptoms
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

    record_id = None
    user_id = session.get('user', {}).get('id') if session.get('user') else None
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO service_records (user_id, vehicle_type, vehicle_brand, vehicle_model, symptoms, predicted_category, urgency, actual_cost) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, cleaned['vehicle_type'], cleaned['vehicle_brand'], cleaned['vehicle_model'], cleaned['symptoms'], result['problem_category'], result['urgency'], result['estimated_cost_max'])
        )
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        print(f"Database insert error: {e}")

    result_payload = dict(result)
    result_payload['record_id'] = record_id
    return jsonify(result_payload)

@app.route('/api/records', methods=['GET'])
def get_records():
    try:
        user = session.get('user')
        conn = db.get_db()
        if user and user.get('role') == 'store_owner':
            cursor = conn.execute('SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, symptoms, predicted_category, urgency, timestamp FROM service_records ORDER BY id DESC LIMIT 50')
        elif user and user.get('role') == 'customer':
            cursor = conn.execute('SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, symptoms, predicted_category, urgency, timestamp FROM service_records WHERE user_id = ? ORDER BY id DESC LIMIT 50', (user['id'],))
        else:
            cursor = conn.execute('SELECT id, user_id, vehicle_type, vehicle_brand, vehicle_model, symptoms, predicted_category, urgency, timestamp FROM service_records ORDER BY id DESC LIMIT 20')
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Feedback Route ---
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json or {}
    record_id = data.get('record_id')
    rating = data.get('accuracy_rating')
    actual_cost = data.get('actual_cost')
    comments = str(data.get('comments', '')).strip()[:500]
    user_id = session.get('user', {}).get('id') if session.get('user') else None

    if not record_id or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "record_id and accuracy_rating (1-5) required."}), 400

    try:
        conn = db.get_db()
        conn.execute(
            'INSERT INTO feedback (record_id, user_id, accuracy_rating, actual_cost, comments) VALUES (?, ?, ?, ?, ?)',
            (record_id, user_id, rating, actual_cost, comments)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Feedback submitted successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

        conn.close()

        return jsonify({
            "total_diagnoses": total_diagnoses,
            "category_distribution": category_distribution,
            "urgency_distribution": urgency_distribution,
            "vehicle_type_split": vehicle_type_split,
            "avg_estimated_cost": avg_estimated_cost,
            "feedback_stats": feedback_stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    db.init_db()
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
