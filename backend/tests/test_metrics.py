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
    assert 'mae' in data['regressor']
    assert 'training_samples' in data
