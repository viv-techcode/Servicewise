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

def test_submit_valid_feedback(client):
    # First create a prediction to get a valid record_id
    pred_resp = client.post('/api/predict', json={
        'vehicle_type': 'car', 'vehicle_brand': 'Hyundai',
        'vehicle_model': 'i20', 'vehicle_age': 4,
        'km_driven': 35000, 'symptoms': 'brakes squeaking loudly'
    })
    assert pred_resp.status_code == 200
    record_id = pred_resp.get_json().get('record_id')
    assert record_id is not None

    # Submit feedback
    fb_resp = client.post('/api/feedback', json={
        'record_id': record_id,
        'accuracy_rating': 5,
        'actual_cost': 2500.0,
        'comments': 'Estimate was very close to workshop charge.'
    })
    assert fb_resp.status_code == 201
    assert 'message' in fb_resp.get_json()

def test_submit_feedback_invalid_rating(client):
    fb_resp = client.post('/api/feedback', json={
        'record_id': 1,
        'accuracy_rating': 6 # Invalid rating (must be 1-5)
    })
    assert fb_resp.status_code == 400

def test_submit_feedback_missing_record(client):
    fb_resp = client.post('/api/feedback', json={
        'accuracy_rating': 4
    })
    assert fb_resp.status_code == 400
