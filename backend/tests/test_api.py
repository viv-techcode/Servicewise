import pytest
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_predict_endpoint(client):
    data = {
        "vehicle_type": "bike",
        "vehicle_brand": "Honda",
        "vehicle_model": "Activa 6G",
        "vehicle_age": 2,
        "km_driven": 10000,
        "symptoms": "clicking noise when starting"
    }
    response = client.post('/api/predict', json=data)
    assert response.status_code == 200
    payload = response.get_json()
    assert 'problem_category' in payload
    assert isinstance(payload['predicted_faults'], list)
    assert payload['predicted_faults']


def test_invalid_prediction_input_stays_rejected(client):
    response = client.post('/api/predict', json={
        'vehicle_type': 'truck', 'vehicle_brand': 'Honda', 'vehicle_model': 'City',
        'vehicle_age': 2, 'km_driven': 100, 'symptoms': 'engine issue'
    })
    assert response.status_code == 400


def test_prediction_history_keeps_legacy_category_and_fault_list(client):
    response = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa 6G',
        'vehicle_age': 2, 'km_driven': 10000, 'symptoms': 'brakes squealing and wheel wobbling'
    })
    assert response.status_code == 200
    record_id = response.get_json()['record_id']
    rows = client.get('/api/records').get_json()
    row = next(item for item in rows if item['id'] == record_id)
    assert row['predicted_category']
    assert isinstance(row['predicted_faults'], list)


def test_location_is_normalized_to_global(client):
    response = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa 6G',
        'vehicle_age': 2, 'km_driven': 10000, 'symptoms': 'brake pads worn', 'state': 'Kerala'
    })
    assert response.status_code == 200
    assert response.get_json()['vehicle_details']['state'] == 'Global'

def test_records_endpoint(client):
    response = client.get('/api/records')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
