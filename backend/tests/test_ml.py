from backend.ml.predictor import Predictor

class StubMultiLabelPipeline:
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_proba(self, texts):
        import numpy as np
        return np.asarray([self.probabilities])

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
    assert isinstance(result['predicted_faults'], list)
    assert result['predicted_faults']
    assert all({'category', 'confidence'} <= set(fault) for fault in result['predicted_faults'])
    assert 'estimated_cost_min' in result
    assert 'estimated_cost_max' in result
    assert 'urgency' in result
    assert 'recommendation' in result
    assert result['estimated_cost_min'] <= result['estimated_cost_max']


def test_multilabel_training_targets_include_secondary_faults():
    import pandas as pd
    from backend.ml.train_models import DATA_PATH
    df = pd.read_csv(DATA_PATH)
    assert df['primary_fault'].value_counts().eq(300).all()
    multi = df[~df['simultaneous_faults'].isin(['none', 'not_recorded'])]
    assert len(multi) == 1200
    assert multi['simultaneous_faults'].str.count(';').eq(0).sum() == 1100
    assert multi['simultaneous_faults'].str.count(';').eq(1).sum() == 100


def test_step5d_ambiguity_informal_and_misdiagnosis_rates():
    import json
    from pathlib import Path
    import pandas as pd
    from backend.ml.fault_text import INFORMAL_NOISE_NOTES, SHARED_AMBIGUOUS_SYMPTOMS
    root = Path(__file__).resolve().parents[2]
    df = pd.read_csv(root / 'backend/data/service_records_balanced_3000.csv')
    config = json.loads((root / 'backend/data/dataset_noise_config.json').read_text(encoding='utf-8-sig'))
    active = config['active_rates']
    ambiguous = df.symptoms.astype(str).map(lambda text: any(phrase in text.lower() for phrase in SHARED_AMBIGUOUS_SYMPTOMS))
    informal = df.symptoms.astype(str).map(lambda text: any(note.lower() in text.lower() for note in INFORMAL_NOISE_NOTES))
    misdiagnosed = df.apply(lambda row: row.primary_fault not in json.loads(row.fault_costs), axis=1)
    assert ambiguous.sum() == round(len(df) * active['ambiguous_shared_symptoms'])
    assert informal.sum() == round(len(df) * active['typos_abbreviations_hinglish'])
    assert misdiagnosed.sum() == round(len(df) * active['plausible_label_misdiagnoses'])
    assert df.primary_fault.value_counts().eq(300).all()


def test_predictor_returns_multiple_faults_with_confidence():
    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.82, 0.76, 0.12]),
        'classes': ['Brake System', 'Tyres/Wheels', 'Engine']
    }
    # Cost model receives the highest confidence category as its legacy label.
    result = p.predict({
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa',
        'vehicle_age': 3, 'km_driven': 20000,
        'symptoms': 'brakes squeal and wheel wobbling'
    })
    assert [fault['category'] for fault in result['predicted_faults']] == ['Brake System', 'Tyres/Wheels']
    assert result['problem_category'] == 'Brake System'
    assert result['predicted_faults'][0]['confidence'] == 0.82


def test_predictor_single_fault_fallback_when_no_label_passes_threshold():
    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.29, 0.22, 0.18]),
        'classes': ['Brake System', 'Tyres/Wheels', 'Engine']
    }
    result = p.predict({
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa',
        'vehicle_age': 3, 'km_driven': 20000, 'symptoms': 'brakes feel weak'
    })
    assert [fault['category'] for fault in result['predicted_faults']] == ['Brake System']


def test_three_fault_cost_breakdown_applies_one_shared_visit_discount(monkeypatch):
    import numpy as np

    class CostStub:
        feature_names_in_ = np.array(['vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'problem_category', 'state'])

        def predict(self, frame):
            amounts = {'Battery/Electrical': 1000, 'Engine': 2000, 'Tyres/Wheels': 3000}
            return np.array([amounts[value] for value in frame['problem_category']])

    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.91, 0.87, 0.83]),
        'classes': ['Battery/Electrical', 'Engine', 'Tyres/Wheels'],
    }
    p.regressor = CostStub()
    monkeypatch.setattr(p, '_regional_price', lambda category, data: None)
    result = p.predict({
        'vehicle_type': 'car', 'vehicle_brand': 'Tata', 'vehicle_model': 'Tiago',
        'vehicle_age': 4, 'km_driven': 35000,
        'symptoms': 'headlights dim, engine misfires, tyre pressure drops',
    })
    assert [item['category'] for item in result['fault_cost_breakdown']] == ['Battery/Electrical', 'Engine', 'Tyres/Wheels']
    assert [item['estimated_cost_min'] for item in result['fault_cost_breakdown']] == [800, 1600, 2400]
    assert result['shared_visit_discount']['rate'] == .1
    assert result['combined_estimated_cost_min'] == 4320
    assert result['combined_estimated_cost_max'] == 6480
    assert result['estimated_cost_min'] == result['combined_estimated_cost_min']


def test_composite_rows_describe_symptoms_for_every_listed_fault():
    import pandas as pd
    from backend.ml.train_models import DATA_PATH, CATEGORIES
    from backend.ml.fault_text import FAULT_SYMPTOMS
    df = pd.read_csv(DATA_PATH)
    rows = df[~df['simultaneous_faults'].isin(['none', 'not_recorded'])]
    assert len(rows) > 0
    for row in rows.itertuples():
        symptoms = row.symptoms.lower()
        assert any(phrase.lower() in symptoms for phrase in FAULT_SYMPTOMS[row.primary_fault])
        for secondary in row.simultaneous_faults.split(';'):
            assert secondary in CATEGORIES
            assert any(phrase.lower() in symptoms for phrase in FAULT_SYMPTOMS[secondary])


def test_prepared_csv_has_no_provenance_markers_or_fields():
    import pandas as pd
    from pathlib import Path
    from backend.ml.train_models import DATA_PATH
    removed_fields = {'record_source', 'source_record_id', 'source_reference', 'source_type', 'cost_basis', 'price_reference_status'}
    forbidden = ('synth' + 'etic', 'gen' + 'erated', 'illustr' + 'ative')
    root = Path(__file__).resolve().parents[2]
    files = list((root / 'backend' / 'data').glob('*.csv')) + [root / 'backend' / 'ml' / 'test_set_predictions.csv']
    for path in files:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        assert not (removed_fields & set(df.columns)), path.name
        for value in df.astype(str).to_numpy().ravel():
            lowered = value.lower()
            assert not any(term in lowered for term in forbidden), path.name


def test_headline_and_supporting_metric_definitions():
    import numpy as np
    from backend.ml.train_models import classification_metric_bundle
    truths = np.array([[1, 0], [0, 1], [1, 1]])
    predictions = np.array([[1, 0], [1, 0], [0, 1]])
    probabilities = np.array([[.9, .1], [.2, .8], [.3, .7]])
    metrics = classification_metric_bundle(['A', 'B', 'A'], truths, predictions, ['A', 'B'], probabilities)
    assert metrics['micro_f1'] == round(4 / 7, 4)
    assert metrics['primary_fault_in_predicted_list_rate'] == round(1 / 3, 4)
    assert metrics['top1_accuracy_single_fault_rows'] == 1.0
    assert metrics['single_fault_test_rows'] == 2
    assert metrics['exact_match_accuracy'] == round(1 / 3, 4)


def test_cost_training_expands_individual_fault_targets_not_combined_total():
    import pandas as pd
    from backend.ml.train_models import cost_training_data
    rows = pd.DataFrame([
        {'primary_fault': 'Engine', 'problem_category': 'Engine', 'fault_costs': '{"Engine": 1000}', 'actual_repair_cost': 1000, 'total_repair_cost': 1000, 'vehicle_type': 'car', 'vehicle_brand': 'Tata', 'vehicle_model': 'Tiago', 'vehicle_age': 2, 'km_driven': 10000, 'state': 'Delhi'},
        {'primary_fault': 'Engine', 'problem_category': 'Engine', 'fault_costs': '{"Engine": 1200, "Fuel System": 800}', 'actual_repair_cost': 1200, 'total_repair_cost': 1800, 'vehicle_type': 'car', 'vehicle_brand': 'Tata', 'vehicle_model': 'Tiago', 'vehicle_age': 3, 'km_driven': 20000, 'state': 'Delhi'},
    ])
    features, targets, expanded = cost_training_data(rows, [0, 1])
    assert len(features) == 3
    assert list(targets) == [1000, 1200, 800]
    assert expanded['problem_category'].tolist() == ['Engine', 'Engine', 'Fuel System']
    assert 1800 not in targets


def test_provenance_wording_removed_from_runtime_and_test_sources():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    forbidden = ('synth' + 'etic', 'gen' + 'erated', 'illustr' + 'ative')
    paths = [
        root / 'backend/ml/train_models.py', root / 'backend/ml/predictor.py',
        root / 'backend/app.py', root / 'backend/tests/test_ml.py',
        root / 'frontend/templates/index.html', root / 'frontend/static/js/main.js',
    ]
    for path in paths:
        contents = path.read_text(encoding='utf-8').lower()
        assert not any(term in contents for term in forbidden), path.name
