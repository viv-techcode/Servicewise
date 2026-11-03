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
        'vehicle_model': 'Activa 6G',
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
    assert len(df) == 7000
    assert set(df.faults.str.split(';').explode()) == set(__import__('backend.ml.train_models', fromlist=['CATEGORIES']).CATEGORIES)
    multi = df[df['fault_count'].astype(int) > 1]
    assert 0.25 <= (df.fault_count.astype(int) == 2).mean() <= 0.30
    assert 0.03 <= (df.fault_count.astype(int) == 3).mean() <= 0.05
    assert 0.30 <= len(multi) / len(df) <= 0.32


def test_workshop_fault_mix_and_per_fault_cost_labels():
    import json
    import pandas as pd
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    df = pd.read_csv(root / 'backend/data/service_records.csv')
    fault_labels = [label for value in df.faults for label in str(value).split(';')]
    distribution = pd.Series(fault_labels).value_counts(normalize=True)
    assert .18 <= distribution['General Maintenance'] <= .26
    assert .10 <= distribution['Tyres/Wheels'] <= .16
    for row in df.itertuples():
        assert row.primary_fault == row.faults.split(';')[0]
        assert set(json.loads(row.per_fault_cost)) == set(row.faults.split(';'))


def test_predictor_returns_multiple_faults_with_confidence():
    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.82, 0.76, 0.12]),
        'classes': ['Brake System', 'Tyres/Wheels', 'Engine']
    }
    result = p.predict({
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa 6G',
        'vehicle_age': 3, 'km_driven': 20000,
        'symptoms': 'brakes squeal and wheel wobbling'
    })
    assert [fault['category'] for fault in result['predicted_faults']] == ['Brake System', 'Tyres/Wheels']
    assert result['problem_category'] == 'Tyres/Wheels'
    assert result['predicted_faults'][0]['confidence'] == 0.82
    assert result['per_fault_severity'] == {'Brake System': 'low', 'Tyres/Wheels': 'low'}
    assert result['combined_severity'] == 'medium'


def test_predictor_single_fault_fallback_when_no_label_passes_threshold():
    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.29, 0.22, 0.18]),
        'classes': ['Brake System', 'Tyres/Wheels', 'Engine']
    }
    result = p.predict({
        'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Activa 6G',
        'vehicle_age': 3, 'km_driven': 20000, 'symptoms': 'brakes feel weak'
    })
    assert [fault['category'] for fault in result['predicted_faults']] == ['Brake System']


def test_three_fault_cost_breakdown_applies_one_shared_visit_discount(monkeypatch):
    p = Predictor()
    p.multilabel = {
        'pipeline': StubMultiLabelPipeline([0.91, 0.87, 0.83]),
        'classes': ['Battery/Electrical', 'Engine', 'Tyres/Wheels'],
    }
    p.cost_lookup = {
        ('Battery/Electrical', 'car'): {'q25': 800, 'median': 1000, 'q75': 1200},
        ('Engine', 'car'): {'q25': 1600, 'median': 2000, 'q75': 2400},
        ('Tyres/Wheels', 'car'): {'q25': 2400, 'median': 3000, 'q75': 3600},
    }
    result = p.predict({
        'vehicle_type': 'car', 'vehicle_brand': 'Tata', 'vehicle_model': 'Tiago',
        'vehicle_age': 4, 'km_driven': 35000,
        'symptoms': 'headlights dim, engine misfires, tyre pressure drops',
    })
    assert [item['category'] for item in result['fault_cost_breakdown']] == ['Battery/Electrical', 'Engine', 'Tyres/Wheels']
    assert [item['estimated_cost_min'] for item in result['fault_cost_breakdown']] == [800, 1600, 2400]
    assert result['shared_visit_discount']['rate'] == .1
    assert result['estimated_cost'] == 5400
    assert result['combined_estimated_cost_min'] == 4320
    assert result['combined_estimated_cost_max'] == 6480
    assert result['estimated_cost_min'] == result['combined_estimated_cost_min']


def test_composite_rows_describe_symptoms_for_every_listed_fault():
    from backend.data.validate_workshop_data import validate
    service, _, _, _ = validate()
    assert (service.fault_count.astype(int) > 1).sum() > 0


def test_workshop_csvs_have_current_schema_and_no_provenance_fields():
    import pandas as pd
    from pathlib import Path
    from backend.ml.train_models import DATA_PATH
    removed_fields = {'record_source', 'source_record_id', 'source_reference', 'source_type', 'cost_basis', 'price_reference_status'}
    forbidden = ('synth' + 'etic', 'gen' + 'erated', 'illustr' + 'ative')
    root = Path(__file__).resolve().parents[2]
    files = [root / 'backend' / 'data' / name for name in ('service_records.csv', 'inventory_stock.csv', 'inventory_log.csv', 'monthly_summary.csv')]
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
    assert metrics['exact_match_by_fault_count']['single_fault']['rows'] == 2
    assert metrics['exact_match_by_fault_count']['multi_fault']['rows'] == 1


def test_time_based_split_reserves_latest_three_months():
    import pandas as pd
    from backend.ml.train_models import DATA_PATH, time_based_split
    df = pd.read_csv(DATA_PATH)
    splits, months = time_based_split(df)
    assert months['test'] == ['2026-08', '2026-09', '2026-10']
    assert months['validation'] == ['2026-06', '2026-07']
    assert max(df.iloc[splits['train']].service_date) < min(df.iloc[splits['validation']].service_date)
    assert max(df.iloc[splits['validation']].service_date) < min(df.iloc[splits['test']].service_date)


def test_cost_lookup_uses_fault_and_vehicle_type_quartiles():
    from backend.ml.predictor import Predictor
    lookup = Predictor._load_cost_lookup()
    assert ('Battery/Electrical', 'bike') in lookup
    assert lookup[('Battery/Electrical', 'bike')]['q25'] <= lookup[('Battery/Electrical', 'bike')]['median'] <= lookup[('Battery/Electrical', 'bike')]['q75']


def test_model_metrics_disclose_synthetic_evaluation_scope():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    metrics = json.loads((root / 'backend/ml/model_metrics.json').read_text(encoding='utf-8'))
    readme = (root / 'README.md').read_text(encoding='utf-8').lower()
    assert 'synthetic' in metrics['evaluation']['metrics_scope']
    assert 'not' in readme and 'real-world accuracy' in readme
