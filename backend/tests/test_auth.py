import pytest
import sqlite3
from backend.app import app
import backend.db as db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key'
    db.init_db()
    with app.test_client() as c:
        yield c

def test_signup_customer(client):
    username = f"cust_{sqlite3.connect(':memory:').total_changes}"
    # Test valid signup with role customer
    r = client.post('/api/auth/signup', json={
        'username': 'test_customer_1',
        'password': 'password123',
        'role': 'customer'
    })
    # Accept 201 or 409 if already exists from prior test
    assert r.status_code in (201, 409)

def test_signup_store_owner(client):
    r = client.post('/api/auth/signup', json={
        'username': 'test_store_owner_1',
        'password': 'password123',
        'role': 'store_owner'
    })
    assert r.status_code in (201, 409)

def test_signup_invalid_role(client):
    r = client.post('/api/auth/signup', json={
        'username': 'invalid_role_user',
        'password': 'password123',
        'role': 'superadmin'
    })
    assert r.status_code == 400

def test_login_and_auth_me(client):
    # Ensure user exists
    client.post('/api/auth/signup', json={
        'username': 'login_test_user',
        'password': 'password123',
        'role': 'customer'
    })
    # Login
    r = client.post('/api/auth/login', json={
        'username': 'login_test_user',
        'password': 'password123'
    })
    assert r.status_code == 200
    data = r.get_json()
    assert data['user']['username'] == 'login_test_user'
    assert data['user']['role'] == 'customer'

    # Check /api/auth/me
    me_resp = client.get('/api/auth/me')
    assert me_resp.status_code == 200
    assert me_resp.get_json()['user']['username'] == 'login_test_user'

def test_logout(client):
    client.post('/api/auth/login', json={
        'username': 'login_test_user',
        'password': 'password123'
    })
    r = client.post('/api/auth/logout')
    assert r.status_code == 200
    me_resp = client.get('/api/auth/me')
    assert me_resp.get_json()['user'] is None
