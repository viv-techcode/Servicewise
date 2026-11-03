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
    if payload.get('needs_more_info'):
        assert payload['predicted_faults'] == []
        assert payload['problem_category'] is None and payload['severity'] is None
        assert payload['estimated_cost_min'] is None and payload['clarifying_question']
    else:
        assert payload['predicted_faults']
    assert 'combined_severity' in payload
    assert set(payload['per_fault_severity']) == {fault['category'] for fault in payload['predicted_faults']}
    assert all('severity' in fault for fault in payload['predicted_faults'])


def test_invalid_prediction_input_stays_rejected(client):
    response = client.post('/api/predict', json={
        'vehicle_type': 'truck', 'vehicle_brand': 'Honda', 'vehicle_model': 'City',
        'vehicle_age': 2, 'km_driven': 100, 'symptoms': 'engine issue'
    })
    assert response.status_code == 400


def test_prediction_returns_clear_error_when_classifier_is_unavailable(client, monkeypatch):
    import backend.app as app_module
    monkeypatch.setattr(app_module.predictor, 'multilabel', None, raising=False)
    monkeypatch.setattr(app_module.predictor, 'model_error', 'Fault prediction model could not be loaded.', raising=False)
    response = client.post('/api/predict', json={
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa 6G',
        'vehicle_age': 2, 'km_driven': 10000, 'symptoms': 'tyre shaking and battery warning light'
    })
    assert response.status_code == 503
    assert response.get_json()['error'] == 'Fault prediction model could not be loaded.'


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
    assert row['combined_severity']
    assert row['per_fault_severity']


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


def test_prediction_snapshot_matches_predictor_fields_for_15_inputs(client):
    cases = [
        ('car','Maruti Suzuki','Swift','tyre puncture and battery drains overnight'),
        ('car','Maruti Suzuki','Swift','brakes fail and both shocks bounce'),
        ('car','Maruti Suzuki','Swift','engine overheats and coolant temperature rises'),
        ('car','Tata','Tiago','petrol leaks and engine misfires'),
        ('bike','Honda','Activa 6G','starter clicks and battery is weak'),
        ('car','Hyundai','i20','gear grinds and brakes squeal'),
        ('car','Maruti Suzuki','Swift','brake failure on highway'),
        ('car','Maruti Suzuki','Swift','engine overheating with steam from bonnet'),
        ('bike','Honda','Shine 125','dim headlight only'),
        ('car','Maruti Suzuki','Alto K10','oil change due only'),
        ('bike','Hero','Splendor Plus','rear tyre puncture'),
        ('car','Tata','Tiago','battery will not hold charge'),
        ('car','Maruti Suzuki','Swift','brakes fail, coolant steams, petrol leaks'),
        ('bike','Honda','Activa 6G','brake nahi lag raha'),
        ('car','Maruti Suzuki','Swift','something feels unusual'),
    ]
    prediction_keys = {'problem_category','model_version','predicted_faults','per_fault_severity','severity','combined_severity','estimated_cost_min','estimated_cost_max','estimated_cost','combined_estimated_cost_min','combined_estimated_cost_max','fault_cost_breakdown','shared_visit_discount','cost_estimate_basis','price_reference','urgency','recommendation','parts_needed','needs_more_info','clarifying_question'}
    for kind, brand, model, symptoms in cases:
        response = client.post('/api/predict', json={'vehicle_type':kind,'vehicle_brand':brand,'vehicle_model':model,'vehicle_age':3,'km_driven':18000 if kind=='bike' else 40000,'symptoms':symptoms})
        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        assert payload['prediction_snapshot'] == {key:payload[key] for key in prediction_keys}
        if symptoms == 'something feels unusual':
            assert payload['needs_more_info'] is True
            assert payload['problem_category'] is None and payload['severity'] is None
            assert payload['estimated_cost_min'] is None and payload['predicted_faults'] == []
