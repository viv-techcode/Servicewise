"""Retrain the multilabel fault classifier from reviewed feedback."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from backend import db
from backend.ml import train_models as training
from backend.ml.fault_text import prepare_classifier_text
from backend.vehicles import is_supported_vehicle

ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR.parent / 'data' / 'service_records.csv'
VERSIONS_DIR = ML_DIR / 'model_versions'
ARTIFACT = 'multilabel_classifier.pkl'


def adoption_decision(current_micro_f1, candidate_micro_f1, tolerance=.005):
    passed = candidate_micro_f1 >= current_micro_f1 - tolerance
    return {'micro_f1_pass': passed, 'adopt': passed}


def load_approved_feedback(connection=None):
    owns = connection is None
    conn = connection or db.get_db()
    rows = conn.execute("""SELECT f.*, r.symptoms FROM feedback f
        JOIN service_records r ON r.id=f.record_id
        WHERE f.review_status='approved' AND f.corrected_faults_json IS NOT NULL
        ORDER BY f.id""").fetchall()
    if owns:
        conn.close()
    accepted = []
    for row in rows:
        try:
            labels = json.loads(row['corrected_faults_json'])
            details = json.loads(row['vehicle_details_json'] or '{}')
        except (TypeError, ValueError):
            continue
        if not isinstance(labels, list) or not labels or any(label not in training.CATEGORIES for label in labels):
            continue
        if not is_supported_vehicle(details.get('vehicle_type'), details.get('vehicle_brand'), details.get('vehicle_model')):
            continue
        accepted.append({**details, 'symptoms': row['symptoms'], 'primary_fault': labels[0], 'problem_category': labels[0], 'faults': ';'.join(labels)})
    return accepted


def _benchmark(df):
    return np.asarray(training.time_based_split(df)[0]['test'], dtype=int)


def compare_models(candidate, base_df):
    test_idx = _benchmark(base_df)
    mlb, labels = training.labels_from_frame(base_df)
    classes = list(mlb.classes_)
    meta = json.loads((ML_DIR / 'model_metrics.json').read_text(encoding='utf-8'))
    thresholds = np.asarray([meta['classifier']['decision_thresholds'][category] for category in classes])
    text = base_df.iloc[test_idx].symptoms.map(prepare_classifier_text)
    current = joblib.load(ML_DIR / ARTIFACT)['pipeline'].predict_proba(text)
    proposed = candidate.predict_proba(text)
    current_pred = training.multilabel_predictions(current, thresholds)
    proposed_pred = training.multilabel_predictions(proposed, thresholds)
    return {'benchmark': 'latest three chronological months from current service_records.csv', 'test_rows': len(test_idx),
            'current_micro_f1': float(f1_score(labels[test_idx], current_pred, average='micro', zero_division=0)),
            'candidate_micro_f1': float(f1_score(labels[test_idx], proposed_pred, average='micro', zero_division=0))}


def _save_version(candidate, metrics, adopt):
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    versions = [int(path.name[1:]) for path in VERSIONS_DIR.glob('v[0-9][0-9][0-9]') if path.is_dir()]
    version = f'v{max(versions, default=0) + 1:03d}'
    folder = VERSIONS_DIR / version
    folder.mkdir()
    bundle = joblib.load(ML_DIR / ARTIFACT)
    bundle['pipeline'] = candidate
    bundle['model_version'] = version
    joblib.dump(bundle, folder / ARTIFACT)
    metadata = {'version': version, 'created_at': datetime.now(timezone.utc).isoformat(), 'adopted': bool(adopt), 'artifact': ARTIFACT, 'metrics': metrics}
    (folder / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    if adopt:
        temporary = ML_DIR / (ARTIFACT + '.new')
        joblib.dump(bundle, temporary)
        os.replace(temporary, ML_DIR / ARTIFACT)
        marker = ML_DIR / 'active_model_version.json.new'
        marker.write_text(json.dumps({'version': version}, indent=2), encoding='utf-8')
        os.replace(marker, ML_DIR / 'active_model_version.json')
    return version


def rollback(version):
    folder = VERSIONS_DIR / version
    artifact = folder / ARTIFACT
    if not folder.is_dir() or not artifact.exists():
        raise ValueError(f'Unknown model version: {version}')
    temporary = ML_DIR / (ARTIFACT + '.new')
    shutil.copy2(artifact, temporary)
    os.replace(temporary, ML_DIR / ARTIFACT)
    marker = ML_DIR / 'active_model_version.json.new'
    marker.write_text(json.dumps({'version': version}, indent=2), encoding='utf-8')
    os.replace(marker, ML_DIR / 'active_model_version.json')
    return version


def retrain(dry_run=False):
    db.init_db()
    feedback = load_approved_feedback()
    df = pd.read_csv(DATA_PATH)
    test = _benchmark(df)
    training_idx = np.asarray([idx for idx in range(len(df)) if idx not in set(test.tolist())])
    training_df = pd.concat([df.iloc[training_idx], pd.DataFrame(feedback)], ignore_index=True, sort=False)
    _, labels = training.labels_from_frame(training_df)
    metrics = json.loads((ML_DIR / 'model_metrics.json').read_text(encoding='utf-8'))
    selected = metrics['classifier']['selected_model']
    model = dict(training.classifier_candidates())[selected]
    text = training_df.symptoms.fillna('').map(prepare_classifier_text)
    model.fit(text, labels)
    comparison = compare_models(model, df)
    gate = adoption_decision(comparison['current_micro_f1'], comparison['candidate_micro_f1'])
    adopt = gate['adopt']
    result = {**comparison, **gate, 'approved_feedback_count': len(feedback), 'adoption_decision': 'adopted' if adopt else 'kept_current'}
    if dry_run:
        result['dry_run'] = True
        return result
    result['version'] = _save_version(model, result, adopt)
    with (ML_DIR / 'retraining_history.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(result) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback', help='Restore a saved classifier version, such as v000.')
    parser.add_argument('--dry-run', action='store_true', help='Evaluate without saving or activating a candidate.')
    args = parser.parse_args()
    result = {'rolled_back_to': rollback(args.rollback)} if args.rollback else retrain(args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
