"""Train and evaluate the multilabel vehicle-fault classifier."""
from __future__ import annotations

import json
import glob
import os
from collections import Counter
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

from backend.ml.fault_text import prepare_classifier_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'service_records.csv')
METRICS_PATH = os.path.join(BASE_DIR, 'model_metrics.json')
TEST_MONTHS = 3
VALIDATION_MONTHS = 2
CATEGORIES = [
    'Battery/Electrical', 'Brake System', 'Cooling System', 'Engine',
    'Fuel System', 'General Maintenance', 'Starting System', 'Suspension',
    'Transmission', 'Tyres/Wheels',
]


def atomic_joblib_dump(obj, path):
    temporary = path + '.tmp'
    joblib.dump(obj, temporary)
    os.replace(temporary, path)


def labels_from_frame(df):
    mlb = MultiLabelBinarizer(classes=CATEGORIES)
    labels = []
    for _, row in df.iterrows():
        primary = str(row.get('primary_fault') or row['problem_category']).strip()
        found = {primary}
        serialized_faults = str(row.get('faults', '')).strip()
        secondary = str(row.get('simultaneous_faults', 'not_recorded')).strip()
        if serialized_faults and serialized_faults.lower() != 'nan':
            found.update(label.strip() for label in serialized_faults.split(';') if label.strip() in CATEGORIES)
        elif secondary not in ('', 'none', 'not_recorded', 'nan'):
            found.update(label.strip() for label in secondary.split(';') if label.strip() in CATEGORIES)
        labels.append(found)
    return mlb, mlb.fit_transform(labels)


def time_based_split(df, test_months=TEST_MONTHS, validation_months=VALIDATION_MONTHS):
    """Use the newest complete months for test and the preceding months for validation."""
    dates = pd.to_datetime(df.service_date, errors='raise')
    months = sorted(dates.dt.to_period('M').unique())
    if len(months) <= test_months + validation_months:
        raise ValueError('Not enough calendar months for chronological train/validation/test splits.')
    test_periods = set(months[-test_months:])
    validation_periods = set(months[-(test_months + validation_months):-test_months])
    row_months = dates.dt.to_period('M')
    splits = {
        'train': np.flatnonzero(~row_months.isin(test_periods | validation_periods)),
        'validation': np.flatnonzero(row_months.isin(validation_periods)),
        'test': np.flatnonzero(row_months.isin(test_periods)),
    }
    if any(len(indices) == 0 for indices in splits.values()):
        raise ValueError('Chronological split produced an empty partition.')
    month_names = {name: [str(months[index]) for index in range(len(months)) if months[index] in periods]
                   for name, periods in [('train', set(months[:-test_months-validation_months])),
                                         ('validation', validation_periods), ('test', test_periods)]}
    return splits, month_names


def classifier_candidates():
    candidates = []
    for alpha in (.5, 1.0):
        candidates.append((f'ovr_multinomial_nb_alpha_{alpha}_ngram_2', Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)),
            ('clf', OneVsRestClassifier(MultinomialNB(alpha=alpha))),
        ])))
    for c in (.5, 1.0, 2.0, 4.0, 8.0):
        candidates.append((f'balanced_logistic_C_{c}_unigram_domain_cues', Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=(1, 1), sublinear_tf=True)),
            ('clf', OneVsRestClassifier(LogisticRegression(C=c, class_weight='balanced', max_iter=2000, solver='liblinear'))),
        ])))
    for c in (1.0, 4.0):
        candidates.append((f'char_linear_C_{c}', Pipeline([
            ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=80000)),
            ('clf', OneVsRestClassifier(LogisticRegression(C=c, max_iter=2500, solver='liblinear'))),
        ])))
    for c in (2.0, 8.0):
        candidates.append((f'word_char_linear_C_{c}', Pipeline([
            ('tfidf', FeatureUnion([
                ('word', TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)),
                ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, sublinear_tf=True, max_features=80000)),
            ])),
            ('clf', OneVsRestClassifier(LogisticRegression(C=c, max_iter=2500, solver='liblinear'))),
        ])))
    return candidates


def select_thresholds(y_true, probabilities):
    thresholds = []
    for column in range(y_true.shape[1]):
        scores = []
        for threshold in np.arange(.10, .901, .05):
            pred = probabilities[:, column] >= threshold
            scores.append((f1_score(y_true[:, column], pred, zero_division=0), precision_score(y_true[:, column], pred, zero_division=0), threshold))
        thresholds.append(float(max(scores)[2]))
    return np.asarray(thresholds)


def multilabel_predictions(probabilities, thresholds):
    predictions = (probabilities >= np.asarray(thresholds)).astype(int)
    empty = predictions.sum(axis=1) == 0
    if empty.any():
        predictions[np.where(empty)[0], probabilities[empty].argmax(axis=1)] = 1
    return predictions


def classification_metric_bundle(primary_faults, y_true, y_pred, classes, probabilities):
    per_category = {}
    for index, category in enumerate(classes):
        per_category[category] = {
            'precision': round(float(precision_score(y_true[:, index], y_pred[:, index], zero_division=0)), 4),
            'recall': round(float(recall_score(y_true[:, index], y_pred[:, index], zero_division=0)), 4),
            'f1': round(float(f1_score(y_true[:, index], y_pred[:, index], zero_division=0)), 4),
            'support': int(y_true[:, index].sum()),
        }
    single = y_true.sum(axis=1) == 1
    top1 = accuracy_score(np.asarray(primary_faults)[single], np.asarray(classes)[probabilities[single].argmax(axis=1)]) if single.any() else 0
    primary_idx = np.asarray([classes.index(str(item)) for item in primary_faults])
    exact = (y_true == y_pred).all(axis=1)
    single = y_true.sum(axis=1) == 1
    multi = y_true.sum(axis=1) > 1
    return {
        'accuracy': round(float(top1), 4),
        'primary_fault_accuracy': round(float(top1), 4),
        'f1_weighted': round(float(f1_score(y_true, y_pred, average='weighted', zero_division=0)), 4),
        'micro_f1': round(float(f1_score(y_true, y_pred, average='micro', zero_division=0)), 4),
        'macro_f1': round(float(f1_score(y_true, y_pred, average='macro', zero_division=0)), 4),
        'weighted_f1': round(float(f1_score(y_true, y_pred, average='weighted', zero_division=0)), 4),
        'exact_match_accuracy': round(float(exact.mean()), 4),
        'exact_match_by_fault_count': {
            'single_fault': {'rows': int(single.sum()), 'accuracy': round(float(exact[single].mean()), 4) if single.any() else None},
            'multi_fault': {'rows': int(multi.sum()), 'accuracy': round(float(exact[multi].mean()), 4) if multi.any() else None},
        },
        'primary_fault_in_predicted_list_rate': round(float(y_pred[np.arange(len(y_pred)), primary_idx].mean()), 4),
        'top1_accuracy_single_fault_rows': round(float(top1), 4),
        'single_fault_test_rows': int(single.sum()),
        'per_category': per_category,
    }


def train_and_save(validation_only=False):
    df = pd.read_csv(DATA_PATH)
    if 'primary_fault' not in df:
        df['primary_fault'] = df['problem_category']
    mlb, y = labels_from_frame(df)
    splits, split_months = time_based_split(df)
    train, validation, test = splits['train'], splits['validation'], splits['test']
    text = df.symptoms.fillna('').map(prepare_classifier_text)
    selected = None
    trials = []
    for name, model in classifier_candidates():
        model.fit(text.iloc[train], y[train])
        probabilities = model.predict_proba(text.iloc[validation])
        thresholds = select_thresholds(y[validation], probabilities)
        predictions = multilabel_predictions(probabilities, thresholds)
        score = float(f1_score(y[validation], predictions, average='micro', zero_division=0))
        trials.append({'name': name, 'validation_micro_f1': round(score, 5)})
        if selected is None or score > selected['score']:
            selected = {'name': name, 'score': score, 'thresholds': thresholds}
    if validation_only:
        return {'validation_micro_f1': round(selected['score'], 5)}
    trainval = np.concatenate([train, validation])
    model = dict(classifier_candidates())[selected['name']]
    model.fit(text.iloc[trainval], y[trainval])
    probabilities = model.predict_proba(text.iloc[test])
    predictions = multilabel_predictions(probabilities, selected['thresholds'])
    metrics = classification_metric_bundle(df.iloc[test].primary_fault, y[test], predictions, list(mlb.classes_), probabilities)
    metrics.update({'headline_metric': 'micro_f1', 'selected_model': selected['name'], 'decision_thresholds': dict(zip(mlb.classes_, selected['thresholds'].tolist())), 'validation_micro_f1': round(selected['score'], 4)})
    atomic_joblib_dump({'pipeline': model, 'classes': list(mlb.classes_), 'thresholds': dict(zip(mlb.classes_, selected['thresholds'].tolist())), 'text_preprocessing': 'remove category annotation and append domain cue features', 'sklearn_version': sklearn.__version__}, os.path.join(BASE_DIR, 'multilabel_classifier.pkl'))
    rows = []
    for offset, source_idx in enumerate(test):
        actual = [mlb.classes_[j] for j in np.flatnonzero(y[source_idx])]
        predicted = [mlb.classes_[j] for j in np.flatnonzero(predictions[offset])]
        rows.append({'job_id': df.iloc[source_idx].get('job_id', source_idx), 'symptoms': df.iloc[source_idx].symptoms, 'actual_faults': ' | '.join(actual), 'predicted_faults': ' | '.join(predicted), 'exact_match': set(actual) == set(predicted), 'is_misclassified': set(actual) != set(predicted), 'primary_fault': df.iloc[source_idx].primary_fault})
    primary = df.iloc[test].primary_fault.to_numpy()
    guessed = np.asarray(mlb.classes_)[probabilities.argmax(axis=1)]
    confusion = Counter((str(a), str(b)) for a, b in zip(primary, guessed) if a != b)
    metrics['most_common_top1_confusions'] = [{'actual_primary': a, 'predicted_top1': b, 'count': n} for (a, b), n in confusion.most_common(10)]
    misclassified = [
        {'job_id': str(row['job_id']), 'actual_faults': row['actual_faults'],
         'predicted_faults': row['predicted_faults'], 'symptoms': row['symptoms']}
        for row in rows if row['is_misclassified']
    ]
    metrics['misclassified_test_rows'] = misclassified
    metrics['misclassified_test_row_count'] = len(misclassified)
    versions_dir = os.path.join(BASE_DIR, 'model_versions')
    existing_versions = [int(os.path.basename(path)[1:]) for path in glob.glob(os.path.join(versions_dir, 'v[0-9][0-9][0-9]'))]
    version = f"v{max(existing_versions, default=-1) + 1:03d}"
    bundle = {'pipeline': model, 'classes': list(mlb.classes_),
              'thresholds': dict(zip(mlb.classes_, selected['thresholds'].tolist())),
              'text_preprocessing': 'remove category annotation and append domain cue features',
              'severity_method': 'rule-based category and symptom severity table',
              'model_version': version, 'sklearn_version': sklearn.__version__}
    atomic_joblib_dump(bundle, os.path.join(BASE_DIR, 'multilabel_classifier.pkl'))
    version_dir = os.path.join(versions_dir, version)
    os.makedirs(version_dir, exist_ok=True)
    atomic_joblib_dump(bundle, os.path.join(version_dir, 'multilabel_classifier.pkl'))
    metadata = {'version': version, 'created_at': datetime.now(timezone.utc).isoformat(),
                'adopted': True, 'artifact': 'multilabel_classifier.pkl',
                'metrics': {'test_micro_f1': metrics['micro_f1'],
                            'test_exact_match_accuracy': metrics['exact_match_accuracy']}}
    with open(os.path.join(version_dir, 'metadata.json'), 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle, indent=2)
    with open(os.path.join(BASE_DIR, 'active_model_version.json'), 'w', encoding='utf-8') as handle:
        json.dump({'version': version}, handle, indent=2)
    data = {'training_samples': len(df), 'trained_at': datetime.now(timezone.utc).isoformat(), 'classifier': metrics,
            'evaluation': {'dataset': os.path.basename(DATA_PATH),
                           'split_method': 'chronological holdout: earliest months train, next two validate, latest three test',
                           'split_rows': {name: len(idx) for name, idx in splits.items()},
                           'split_months': split_months,
                           'validation_classifier_trials': trials,
                           'multi_label_rows': int((y.sum(axis=1) > 1).sum()),
                           'multi_fault_rows_two_labels': int((y.sum(axis=1) == 2).sum()),
                           'multi_fault_rows_three_labels': int((y.sum(axis=1) == 3).sum()),
                           'primary_only_rows': int((y.sum(axis=1) == 1).sum()),
                           'sklearn_version': sklearn.__version__,
                           'metrics_scope': 'synthetic generated dataset; not real-world accuracy'}}
    tmp = METRICS_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, METRICS_PATH)
    print(json.dumps({'classifier': metrics, 'split_rows': data['evaluation']['split_rows'],
                      'split_months': data['evaluation']['split_months'],
                      'model_version': version, 'sklearn_version': sklearn.__version__}, indent=2))
    return data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--validation-only', action='store_true')
    train_and_save(validation_only=parser.parse_args().validation_only)
