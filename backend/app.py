import os
from flask import Flask, jsonify, render_template, request
from backend import db

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'servicewise_dev_secret_key_2026'

db.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "ServiceWise API"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
