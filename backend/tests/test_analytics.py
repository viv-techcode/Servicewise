import pytest
from backend.app import app
import backend.db as db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key'
    db.init_db()
    with app.test_client() as c:
        yield c

def test_analytics_endpoint(client):
    # Ensure there are some records
    client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa', 'vehicle_age': 2,
        'km_driven': 10000, 'symptoms': 'engine overheating and smoking'
    })
    
    r = client.get('/api/analytics')
    assert r.status_code == 200
    data = r.get_json()
    assert 'total_diagnoses' in data
    assert 'category_distribution' in data
    assert 'urgency_distribution' in data
    assert 'vehicle_type_split' in data
    assert 'avg_estimated_cost' in data
    assert 'feedback_stats' in data
