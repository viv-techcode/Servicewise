import pytest

from backend.app import app, validate_feedback_input
import backend.db as db
from backend.ml import retrain
from backend.ml.predictor import Predictor


@pytest.fixture
def client(monkeypatch):
    import os
    from pathlib import Path
    test_db = Path('backend/data/test_step6.sqlite').resolve()
    test_db.parent.mkdir(parents=True, exist_ok=True)
    test_db.unlink(missing_ok=True)
    monkeypatch.setattr(db, 'DB_PATH', str(test_db))
    db.init_db()
    app.config['TESTING'] = True
    app.secret_key = 'step6-test'
    with app.test_client() as test_client:
        yield test_client
    test_db.unlink(missing_ok=True)


def _prediction(client):
    response = client.post('/api/predict', json={
        'vehicle_type': 'car', 'vehicle_brand': 'Hyundai', 'vehicle_model': 'i20',
        'vehicle_age': 4, 'km_driven': 35000, 'state': 'Delhi',
        'symptoms': 'brakes squeal and steering wheel vibrates'
    })
    assert response.status_code == 200
    return response.get_json()


def test_feedback_validation_multilabel_and_costs():
    valid, error = validate_feedback_input({'record_id': 3, 'corrected_faults': ['Brake System', 'Tyres/Wheels'],
        'actual_total_cost': 4500, 'actual_fault_costs': {'Brake System': 3000, 'Tyres/Wheels': 1500}})
    assert error is None and valid['actual_cost'] == 4500
    for payload in (
        {'record_id': 3, 'corrected_faults': ['unknown']},
        {'record_id': 3, 'actual_total_cost': -1},
        {'record_id': 3, 'corrected_faults': ['Brake System', 'Brake System']},
    ):
        assert validate_feedback_input(payload)[1]


def test_feedback_is_snapshotted_pending_and_requires_review(client):
    result = _prediction(client)
    response = client.post('/api/feedback', json={'record_id': result['record_id'], 'accuracy_rating': 4,
        'corrected_faults': ['Brake System'], 'actual_total_cost': 2500, 'vehicle_details': result['vehicle_details']})
    assert response.status_code == 201
    feedback_id = response.get_json()['feedback_id']
    assert response.get_json()['review_status'] == 'pending'
    assert retrain.load_approved_feedback() == []
    assert client.post(f'/api/feedback/{feedback_id}/review', json={'decision': 'approved'}).status_code == 401
    client.post('/api/auth/signup', json={'username': 'step6owner', 'password': 'password123', 'role': 'store_owner'})
    reviewed = client.post(f'/api/feedback/{feedback_id}/review', json={'decision': 'approved'})
    assert reviewed.status_code == 200
    rows = retrain.load_approved_feedback()
    assert len(rows) == 1 and rows[0]['primary_fault'] == 'Brake System'


def test_history_and_analytics_comparison_view(client):
    result = _prediction(client)
    response = client.post('/api/feedback', json={'record_id': result['record_id'], 'corrected_faults': ['Engine'],
        'actual_total_cost': 2400, 'actual_fault_costs': {'Engine': 2400}})
    feedback_id = response.get_json()['feedback_id']
    client.post('/api/auth/signup', json={'username': 'viewowner', 'password': 'password123', 'role': 'store_owner'})
    client.post(f'/api/feedback/{feedback_id}/review', json={'decision': 'approved'})
    record = next(x for x in client.get('/api/records').get_json() if x['id'] == result['record_id'])
    assert record['feedback']['predicted_faults']
    assert record['feedback']['corrected_faults'] == ['Engine']
    assert record['feedback']['predicted_cost'] == result['estimated_cost_max']
    analytics = client.get('/api/analytics').get_json()
    assert analytics['confirmed_feedback']['reviewed_records'] == 1
    assert analytics['confirmed_comparisons'][0]['record_id'] == result['record_id']


def test_candidate_gating_and_version_rollback(monkeypatch):
    assert retrain.adoption_decision(.90, .895, 100, 105)['adopt'] is True
    assert retrain.adoption_decision(.90, .894, 100, 104)['adopt'] is False
    assert retrain.adoption_decision(.90, .90, 100, 105.01)['adopt'] is False
    from pathlib import Path
    tmp_path = Path('backend/data/test_versions').resolve()
    if tmp_path.exists():
        import shutil; shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True)
    comparison = retrain.compare_models
    monkeypatch.setattr(retrain, 'compare_models', lambda *a, **kw: {
        'current': {'micro_f1': .90, 'per_fault_cost_mae': 100},
        'candidate': {'micro_f1': .894, 'per_fault_cost_mae': 104},
        'micro_f1_tolerance': .005, 'cost_mae_max_degradation_fraction': .05,
        'micro_f1_pass': False, 'cost_mae_pass': True, 'adopt': False,
    })
    assert retrain.compare_models(None, None, None, [])['micro_f1_pass'] is False
    monkeypatch.setattr(retrain, 'compare_models', comparison)

    versions = tmp_path / 'versions'; versions.mkdir()
    folder = versions / 'v001'; folder.mkdir()
    monkeypatch.setattr(retrain, 'VERSIONS_DIR', versions)
    monkeypatch.setattr(retrain, 'ML_DIR', tmp_path)
    for artifact in retrain.ARTIFACTS:
        (folder / artifact).write_bytes(b'previous')
        (tmp_path / artifact).write_bytes(b'current')
    (folder / 'metadata.json').write_text('{}')
    assert retrain.rollback('v001') == 'v001'
    assert all((tmp_path / artifact).read_bytes() == b'previous' for artifact in retrain.ARTIFACTS)
    import shutil; shutil.rmtree(tmp_path)


def test_predictor_refreshes_when_active_version_changes(monkeypatch):
    import json
    from pathlib import Path
    import backend.ml.predictor as predictor_module
    tmp_path = Path('backend/data/test_active_version').resolve()
    tmp_path.mkdir(parents=True, exist_ok=True)
    marker = tmp_path / 'active_model_version.json'
    marker.write_text(json.dumps({'version': 'v002'}))
    monkeypatch.setattr(predictor_module, 'BASE_DIR', str(tmp_path))
    predictor = Predictor.__new__(Predictor)
    predictor.model_version = 'v001'
    loaded = []
    predictor._load_models = lambda: loaded.append(True)
    # Exercise the version comparison directly without loading large artifacts.
    predictor.refresh_if_model_changed()
    assert loaded == [True]
    marker.unlink()
    tmp_path.rmdir()
