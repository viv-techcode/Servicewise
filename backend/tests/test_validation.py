import pytest
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_missing_fields(client):
    r = client.post('/api/predict', json={})
    assert r.status_code == 400
    assert 'error' in r.get_json()

def test_invalid_vehicle_type(client):
    r = client.post('/api/predict', json={
        'vehicle_type': 'truck', 'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa', 'vehicle_age': 2,
        'km_driven': 10000, 'symptoms': 'engine noise'
    })
    assert r.status_code == 400
    assert 'vehicle_type' in r.get_json()['error']

def test_negative_age(client):
    r = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa', 'vehicle_age': -5,
        'km_driven': 10000, 'symptoms': 'engine noise'
    })
    assert r.status_code == 400
    assert 'vehicle_age' in r.get_json()['error']

def test_short_symptoms(client):
    r = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa', 'vehicle_age': 2,
        'km_driven': 10000, 'symptoms': 'ab'
    })
    assert r.status_code == 400
    assert 'symptoms' in r.get_json()['error']

def test_valid_input_still_works(client):
    r = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa', 'vehicle_age': 2,
        'km_driven': 10000, 'symptoms': 'clicking noise when starting'
    })
    assert r.status_code == 200
    assert 'problem_category' in r.get_json()


def test_cycle_vehicle_type(client):
    r = client.post('/api/predict', json={
        'vehicle_type': 'cycle', 'vehicle_brand': 'Hero Cycles',
        'vehicle_model': 'Hero Jet', 'vehicle_age': 2,
        'km_driven': 1500, 'symptoms': 'chain slipping off sprocket loose chain'
    })
    assert r.status_code == 200
    assert 'problem_category' in r.get_json()
