from backend.ml.predictor import Predictor

def test_predictor_returns_expected_keys():
    p = Predictor()
    result = p.predict({
        'vehicle_type': 'bike',
        'vehicle_brand': 'Honda',
        'vehicle_model': 'Activa',
        'vehicle_age': 3,
        'km_driven': 20000,
        'symptoms': 'engine overheating and excessive white smoke'
    })
    assert 'problem_category' in result
    assert 'estimated_cost_min' in result
    assert 'estimated_cost_max' in result
    assert 'urgency' in result
    assert 'recommendation' in result
    assert result['estimated_cost_min'] <= result['estimated_cost_max']
