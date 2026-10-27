import pytest
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_model_metrics_endpoint(client):
    r = client.get('/api/model/metrics')
    assert r.status_code == 200
    data = r.get_json()
    assert 'classifier' in data
    assert 'regressor' in data
    assert 'accuracy' in data['classifier']
    assert 'primary_fault_accuracy' in data['classifier']
    assert 'micro_f1' in data['classifier']
    assert 'macro_f1' in data['classifier']
    assert 'per_category' in data['classifier']
    assert 'mae' in data['regressor']
    assert 'rmse' in data['regressor']
    assert 'r2' in data['regressor']
    assert 'training_samples' in data
    assert data['evaluation']['split_group_overlap'] == 0
