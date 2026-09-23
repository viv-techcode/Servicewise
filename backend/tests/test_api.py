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
        "vehicle_model": "Activa",
        "vehicle_age": 2,
        "km_driven": 10000,
        "symptoms": "clicking noise when starting"
    }
    response = client.post('/api/predict', json=data)
    assert response.status_code == 200
    assert 'problem_category' in response.get_json()

def test_records_endpoint(client):
    response = client.get('/api/records')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
