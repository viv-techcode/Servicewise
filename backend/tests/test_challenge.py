"""Hand-authored safety and phrasing challenge suite for the classifier."""
import json
from pathlib import Path

from backend.ml.predictor import Predictor
from backend.ml.severity import LEVEL_RANK

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = Path(__file__).with_name('challenge_cases.json')
METRICS_PATH = ROOT / 'backend' / 'ml' / 'challenge_metrics.json'
SAFETY = ('Brake System', 'Cooling System', 'Fuel System')


def evaluate_challenge_cases():
    cases = json.loads(CASES_PATH.read_text(encoding='utf-8'))
    assert len(cases) >= 150
    predictor = Predictor()
    misses = []
    total_severity_correct = 0
    safety_actual = {category: 0 for category in SAFETY}
    safety_found = {category: 0 for category in SAFETY}
    red_flag_count = red_flag_underpredicted = 0
    for case in cases:
        result = predictor.predict({
            'vehicle_type': 'car', 'vehicle_brand': 'Maruti Suzuki',
            'vehicle_model': 'Swift', 'vehicle_age': 4, 'km_driven': 42000,
            'symptoms': case['input'],
        })
        predicted = {fault['category'] for fault in result['predicted_faults']}
        expected = set(case['expected_faults'])
        severity_correct = result['combined_severity'] == case['expected_severity']
        total_severity_correct += int(severity_correct)
        for category in SAFETY & expected:
            safety_actual[category] += 1
            safety_found[category] += int(category in predicted)
        red_under = case.get('red_flag', False) and LEVEL_RANK[result['combined_severity']] < LEVEL_RANK[case['expected_severity']]
        if case.get('red_flag', False):
            red_flag_count += 1
            red_flag_underpredicted += int(red_under)
        if not expected.issubset(predicted) or not severity_correct or red_under:
            misses.append({
                'id': case['id'], 'input': case['input'],
                'expected_faults': sorted(expected), 'predicted_faults': sorted(predicted),
                'expected_severity': case['expected_severity'],
                'predicted_severity': result['combined_severity'],
                'red_flag_underpredicted': red_under,
            })
    recall = {key: round(safety_found[key] / safety_actual[key], 4) if safety_actual[key] else None for key in SAFETY}
    metrics = {
        'cases': len(cases), 'severity_accuracy': round(total_severity_correct / len(cases), 4),
        'safety_fault_recall': recall, 'red_flag_cases': red_flag_count,
        'red_flag_underpredicted': red_flag_underpredicted, 'misses': misses,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return metrics


def test_challenge_set_targets_and_reports_every_miss():
    metrics = evaluate_challenge_cases()
    print(json.dumps({key: value for key, value in metrics.items() if key != 'misses'}, indent=2))
    if metrics['misses']:
        print('CHALLENGE MISSES:', json.dumps(metrics['misses'], ensure_ascii=False))
    assert metrics['red_flag_underpredicted'] == 0, json.dumps(metrics['misses'], ensure_ascii=False)
    assert all(metrics['safety_fault_recall'][category] >= .98 for category in SAFETY), json.dumps(metrics['misses'], ensure_ascii=False)
    assert metrics['severity_accuracy'] >= .90, json.dumps(metrics['misses'], ensure_ascii=False)

