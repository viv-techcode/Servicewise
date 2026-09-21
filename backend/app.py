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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
