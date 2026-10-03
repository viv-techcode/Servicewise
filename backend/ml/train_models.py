"""Group-aware model selection and final holdout evaluation for ServiceWise."""
from __future__ import annotations

import json
import os
import argparse
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error, mean_squared_error,
    precision_score, recall_score, r2_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder
import sklearn
from backend.ml.fault_text import prepare_classifier_text, symptom_family

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'service_records_balanced_3000.csv')
LEGACY_DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'sample_service_records.csv')
REPORT_PATH = os.path.join(BASE_DIR, 'evaluation_report.md')
PREDICTIONS_PATH = os.path.join(BASE_DIR, 'test_set_predictions.csv')
METRICS_PATH = os.path.join(BASE_DIR, 'model_metrics.json')
STEP5C_BASELINE_METRICS_PATH = os.path.join(BASE_DIR, 'step5c_baseline_metrics.json')
NOISE_CONFIG_PATH = os.path.join(BASE_DIR, '..', 'data', 'dataset_noise_config.json')
TEXT_AUDIT_PATH = os.path.join(BASE_DIR, '..', 'data', 'step5d_prechange_text_audit.json')
SPLIT_SEED = 104729
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
    rows = []
    for _, row in df.iterrows():
        primary = str(row.get('primary_fault') or row['problem_category']).strip()
        labels = {primary}
        secondary = str(row.get('simultaneous_faults', 'not_recorded')).strip()
        if secondary not in ('', 'none', 'not_recorded', 'nan'):
            labels.update(x.strip() for x in secondary.split(';') if x.strip() in CATEGORIES)
        rows.append(labels)
    return mlb, mlb.fit_transform(rows)


def group_aware_split(df, labels=None, seed=SPLIT_SEED):
    # Group on normalized symptom content and primary class. The same broad
    # phrase can describe distinct systems (e.g. a vehicle pulling sideways),
    # while repeated templates for the same class must remain together.
    groups = (df['primary_fault'].astype(str) + '::' + df['symptoms'].map(symptom_family)).to_numpy()
    first = GroupShuffleSplit(n_splits=1, test_size=.20, random_state=seed)
    remaining_idx, test_idx = next(first.split(df, groups=groups))
    target_ratios = {'train': .65, 'validation': .15, 'test': .20}
    best = None
    for random_state in range(seed, seed + 300):
        second = GroupShuffleSplit(n_splits=1, test_size=.1875, random_state=random_state)
        tr_rel, val_rel = next(second.split(df.iloc[remaining_idx], groups=groups[remaining_idx]))
        train_idx = remaining_idx[tr_rel]
        val_idx = remaining_idx[val_rel]
        partitions = {'train': train_idx, 'validation': val_idx, 'test': test_idx}
        if any(set(df.iloc[idx]['primary_fault']) != set(CATEGORIES) for idx in (train_idx, val_idx)):
            continue
        sizes = {name: len(idx) / len(df) for name, idx in partitions.items()}
        # Prefer the requested proportions and balanced primary-label support.
        cost = sum(abs(sizes[k] - target_ratios[k]) for k in target_ratios)
        for name, idx in (('train', train_idx), ('validation', val_idx)):
            counts = df.iloc[idx]['primary_fault'].value_counts(normalize=True)
            cost += .08 * sum(abs(float(counts.get(c, 0)) - .1) for c in CATEGORIES)
        if best is None or cost < best[0]:
            best = (cost, partitions, groups)
    if best is None:
        raise RuntimeError('Could not create group-aware splits containing all primary categories.')
    _, splits, groups = best
    group_sets = {name: set(groups[idx]) for name, idx in splits.items()}
    assert not (group_sets['train'] & group_sets['validation'])
    assert not (group_sets['train'] & group_sets['test'])
    assert not (group_sets['validation'] & group_sets['test'])
    return splits, groups


def classifier_candidates():
    candidates = []
    for alpha, ngram in [(.5, (1, 2)), (1.0, (1, 2))]:
        candidates.append((
            f"ovr_multinomial_nb_alpha_{alpha}_ngram_{ngram[1]}",
            Pipeline([
                ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=ngram, min_df=1, sublinear_tf=True)),
                ('clf', OneVsRestClassifier(MultinomialNB(alpha=alpha))),
            ]),
        ))
    for ngram, strengths in [((1, 1), [.5, 1.0, 2.0]), ((1, 2), [1.0, 2.0])]:
        for c in strengths:
            candidates.append((
                f"ovr_logistic_C_{c}_ngram_{ngram[1]}",
                Pipeline([
                    ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=ngram, min_df=1, sublinear_tf=True)),
                    ('clf', OneVsRestClassifier(LogisticRegression(C=c, max_iter=1500, solver='liblinear'))),
                ]),
            ))
    # Domain cue tokens are derived by the same fixed text transform used
    # at prediction time. Balanced logistic candidates help rare fault cues.
    for c in [1.0, 4.0, 8.0]:
        candidates.append((
            f"balanced_logistic_C_{c}_unigram_domain_cues",
            Pipeline([
                ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=(1, 1), min_df=1, sublinear_tf=True)),
                ('clf', OneVsRestClassifier(LogisticRegression(C=c, class_weight='balanced', max_iter=2000, solver='liblinear'))),
            ]),
        ))
    for c in [1.0, 4.0]:
        candidates.append((
            f"char_linear_C_{c}",
            Pipeline([
                ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=80000)),
                ('clf', OneVsRestClassifier(LogisticRegression(C=c, max_iter=2500, solver='liblinear'))),
            ]),
        ))
    for c in [2.0, 8.0]:
        candidates.append((
            f"word_char_linear_C_{c}",
            Pipeline([
                ('tfidf', FeatureUnion([
                    ('word', TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
                    ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, sublinear_tf=True, max_features=80000)),
                ])),
                ('clf', OneVsRestClassifier(LogisticRegression(C=c, max_iter=2500, solver='liblinear'))),
            ]),
        ))
    return candidates


def select_threshold(y_true, probabilities):
    best = None
    for threshold in np.arange(.15, .801, .025):
        pred = multilabel_predictions(probabilities, threshold)
        score = f1_score(y_true, pred, average='micro', zero_division=0)
        exact = accuracy_score(y_true, pred)
        candidate = (score, exact, float(threshold))
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2], best[0], best[1]


def select_thresholds_per_label(y_true, probabilities):
    thresholds = []
    per_label_scores = []
    for column in range(y_true.shape[1]):
        best = None
        for threshold in np.arange(.10, .901, .05):
            pred = (probabilities[:, column] >= threshold).astype(int)
            score = f1_score(y_true[:, column], pred, zero_division=0)
            precision = precision_score(y_true[:, column], pred, zero_division=0)
            candidate = (float(score), float(precision), float(threshold))
            if best is None or candidate > best:
                best = candidate
        thresholds.append(best[2])
        per_label_scores.append(best[0])
    return np.asarray(thresholds, dtype=float), per_label_scores


def multilabel_predictions(probabilities, threshold):
    thresholds = np.asarray(threshold, dtype=float)
    predictions = (probabilities >= thresholds).astype(int)
    empty = np.sum(predictions, axis=1) == 0
    if empty.any():
        predictions[np.where(empty)[0], np.argmax(probabilities[empty], axis=1)] = 1
    return predictions


def cost_features(df):
    result = df[['vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'problem_category', 'state']].copy()
    result['state'] = result['state'].fillna('not_recorded').replace('', 'not_recorded')
    return result


def cost_training_data(df, row_indices):
    """Expand each row into individual fault-cost targets, never visit totals."""
    records = []
    targets = []
    for index in row_indices:
        row = df.iloc[int(index)]
        primary = str(row['primary_fault'])
        fault_costs = parse_fault_costs(row)
        if not isinstance(fault_costs, dict) or not fault_costs:
            fault_costs = {primary: row.get('actual_repair_cost')}
        for category, amount in fault_costs.items():
            cost = pd.to_numeric(amount, errors='coerce')
            if category not in CATEGORIES or pd.isna(cost):
                continue
            item = row.copy()
            item['problem_category'] = category
            records.append(item)
            targets.append(float(cost))
    if not records:
        raise ValueError('No individual fault-cost targets are available.')
    expanded = pd.DataFrame(records)
    return cost_features(expanded), np.asarray(targets, dtype=float), expanded


def parse_fault_costs(row):
    try:
        result = json.loads(str(row.get('fault_costs', '{}')))
    except (TypeError, json.JSONDecodeError):
        result = {}
    return result if isinstance(result, dict) else {}


def classification_metric_bundle(primary_faults, y_true, y_pred, classes, probabilities):
    primary_indices = np.asarray([classes.index(str(value)) for value in primary_faults], dtype=int)
    primary_in_list = y_pred[np.arange(len(y_pred)), primary_indices]
    single_rows = y_true.sum(axis=1) == 1
    top1_single = None
    if single_rows.any():
        top1_single = float(accuracy_score(np.asarray(primary_faults)[single_rows], np.asarray(classes)[probabilities[single_rows].argmax(axis=1)]))
    per_category = {}
    for i, category in enumerate(classes):
        per_category[category] = {
            'precision': round(float(precision_score(y_true[:, i], y_pred[:, i], zero_division=0)), 4),
            'recall': round(float(recall_score(y_true[:, i], y_pred[:, i], zero_division=0)), 4),
            'f1': round(float(f1_score(y_true[:, i], y_pred[:, i], zero_division=0)), 4),
            'support': int(y_true[:, i].sum()),
        }
    macro_f1 = round(float(f1_score(y_true, y_pred, average='macro', zero_division=0)), 4)
    weighted_f1 = round(float(f1_score(y_true, y_pred, average='weighted', zero_division=0)), 4)
    return {
        'micro_f1': round(float(f1_score(y_true, y_pred, average='micro', zero_division=0)), 4),
        'macro_f1': macro_f1,
        'weighted_f1': weighted_f1,
        'exact_match_accuracy': round(float(accuracy_score(y_true, y_pred)), 4),
        'primary_fault_in_predicted_list_rate': round(float(np.mean(primary_in_list)), 4),
        'top1_accuracy_single_fault_rows': round(top1_single, 4) if top1_single is not None else None,
        'primary_fault_accuracy': round(top1_single, 4) if top1_single is not None else None,
        'single_fault_test_rows': int(single_rows.sum()),
        'per_category': per_category,
    }


def per_fault_combined_estimates(model, df, row_indices, y_matrix, classes):
    estimates = []
    actual_totals = []
    for index in row_indices:
        fault_costs = parse_fault_costs(df.iloc[int(index)])
        categories = [category for category in fault_costs if category in CATEGORIES]
        if not categories:
            categories = [classes[j] for j in np.flatnonzero(y_matrix[index])]
        rows = []
        for category in categories:
            item = df.iloc[int(index)].copy()
            item['problem_category'] = category
            rows.append(item)
        predicted_parts = np.maximum(0.0, model.predict(cost_features(pd.DataFrame(rows))))
        estimates.append(float(predicted_parts.sum() * (0.9 if len(categories) > 1 else 1.0)))
        actual_totals.append(float(df.iloc[int(index)]['total_repair_cost']))
    return np.asarray(actual_totals), np.asarray(estimates)


def top1_confusion_summary(primary_faults, probabilities, classes, limit=10):
    predicted = np.asarray(classes)[probabilities.argmax(axis=1)]
    counts = Counter((str(actual), str(guess)) for actual, guess in zip(primary_faults, predicted) if actual != guess)
    return [
        {'actual_primary': actual, 'predicted_top1': guess, 'count': int(count)}
        for (actual, guess), count in counts.most_common(limit)
    ]


def make_cost_pipeline(model):
    categorical = ['vehicle_type', 'vehicle_brand', 'vehicle_model', 'problem_category', 'state']
    prep = ColumnTransformer([
        ('categorical', OneHotEncoder(handle_unknown='ignore'), categorical),
        ('numeric', 'passthrough', ['vehicle_age', 'km_driven']),
    ])
    return Pipeline([('preprocessor', prep), ('regressor', model)])


def cost_candidates():
    return [
        ('random_forest_leaf1', RandomForestRegressor(n_estimators=250, min_samples_leaf=1, max_features=1.0, random_state=42, n_jobs=-1)),
        ('random_forest_leaf3', RandomForestRegressor(n_estimators=250, min_samples_leaf=3, max_features=1.0, random_state=42, n_jobs=-1)),
        ('random_forest_sqrt', RandomForestRegressor(n_estimators=250, min_samples_leaf=2, max_features=.8, random_state=42, n_jobs=-1)),
        ('extra_trees_leaf1', ExtraTreesRegressor(n_estimators=250, min_samples_leaf=1, max_features=1.0, random_state=42, n_jobs=-1)),
        ('extra_trees_leaf3', ExtraTreesRegressor(n_estimators=250, min_samples_leaf=3, max_features=1.0, random_state=42, n_jobs=-1)),
    ]


def evaluate_regression(y_true, y_pred):
    return {
        'mae': round(float(mean_absolute_error(y_true, y_pred)), 2),
        'rmse': round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        'r2': round(float(r2_score(y_true, y_pred)), 4),
    }


def train_and_save(validation_only=False):
    os.makedirs(BASE_DIR, exist_ok=True)
    data_path = DATA_PATH if os.path.exists(DATA_PATH) else LEGACY_DATA_PATH
    df = pd.read_csv(data_path)
    if 'primary_fault' not in df:
        df['primary_fault'] = df['problem_category']
    if 'state' not in df:
        df['state'] = 'not_recorded'
    if 'vehicle_model' not in df:
        df['vehicle_model'] = 'not_recorded'
    df['problem_category'] = df['primary_fault'].fillna(df['problem_category'])
    df['actual_repair_cost'] = pd.to_numeric(df['actual_repair_cost'], errors='coerce')
    df['total_repair_cost'] = pd.to_numeric(df.get('total_repair_cost', df['actual_repair_cost']), errors='coerce')
    df = df[df['actual_repair_cost'].notna() & df['total_repair_cost'].notna() & df['symptoms'].notna()].reset_index(drop=True)
    mlb, y = labels_from_frame(df)
    splits, group_ids = group_aware_split(df, y)
    idx_train, idx_val, idx_test = splits['train'], splits['validation'], splits['test']
    text = df['symptoms'].map(prepare_classifier_text)

    # Select model and per-label thresholds using validation predictions only.
    selected = None
    validation_trials = []
    for name, pipeline in classifier_candidates():
        pipeline.fit(text.iloc[idx_train], y[idx_train])
        proba = pipeline.predict_proba(text.iloc[idx_val])
        thresholds, per_label_f1 = select_thresholds_per_label(y[idx_val], proba)
        val_pred = multilabel_predictions(proba, thresholds)
        micro = float(f1_score(y[idx_val], val_pred, average='micro', zero_division=0))
        trial = {'name': name, 'thresholds': {category: round(float(value), 3) for category, value in zip(CATEGORIES, thresholds)}, 'validation_micro_f1': round(micro, 5)}
        validation_trials.append(trial)
        if selected is None or micro > selected['micro']:
            selected = {'name': name, 'pipeline': pipeline, 'thresholds': thresholds, 'micro': micro}

    if validation_only:
        result = {'validation_micro_f1': round(float(selected['micro']), 5)}
        print(json.dumps(result))
        return result

    baseline = json.loads(Path(STEP5C_BASELINE_METRICS_PATH).read_text(encoding='utf-8'))
    noise_config = json.loads(Path(NOISE_CONFIG_PATH).read_text(encoding='utf-8-sig'))

    # Refit selected hyperparameters on train + validation. Test remains unseen.
    selected_config = next(p for n, p in classifier_candidates() if n == selected['name'])
    idx_trainval = np.concatenate([idx_train, idx_val])
    selected_config.fit(text.iloc[idx_trainval], y[idx_trainval])
    test_proba = selected_config.predict_proba(text.iloc[idx_test])
    y_test_pred = multilabel_predictions(test_proba, selected['thresholds'])
    classes = list(mlb.classes_)
    classification_metrics = classification_metric_bundle(df.iloc[idx_test]['primary_fault'].to_numpy(), y[idx_test], y_test_pred, classes, test_proba)
    classification_metrics.update({
        'headline_metric': 'micro_f1',
        'selected_model': selected['name'],
        'decision_thresholds': {category: round(float(value), 4) for category, value in zip(classes, selected['thresholds'])},
        'validation_micro_f1': round(float(selected['micro']), 4),
    })

    # Build one cost-training row per known fault label, with an individual
    # target from fault_costs. Never train against the combined visit total.
    x_train_cost, y_train_cost, train_cost_rows = cost_training_data(df, idx_train)
    x_val_cost, y_val_cost, val_cost_rows = cost_training_data(df, idx_val)
    x_test_cost, y_test_cost, test_cost_rows = cost_training_data(df, idx_test)
    selected_cost = None
    cost_trials = []
    for name, model in cost_candidates():
        pipeline = make_cost_pipeline(model)
        pipeline.fit(x_train_cost, y_train_cost)
        val_pred = pipeline.predict(x_val_cost)
        mae = float(mean_absolute_error(y_val_cost, val_pred))
        trial = {'name': name, 'validation_per_fault_mae': round(mae, 2)}
        cost_trials.append(trial)
        if selected_cost is None or mae < selected_cost['mae']:
            selected_cost = {'name': name, 'model': model, 'mae': mae}
    cost_pipeline = make_cost_pipeline(selected_cost['model'])
    x_trainval_cost, y_trainval_cost, _ = cost_training_data(df, idx_trainval)
    cost_pipeline.fit(x_trainval_cost, y_trainval_cost)
    cost_test_pred = cost_pipeline.predict(x_test_cost)
    regression_metrics = evaluate_regression(y_test_cost, cost_test_pred)
    regression_metrics['selected_model'] = selected_cost['name']
    regression_metrics['validation_per_fault_mae'] = round(selected_cost['mae'], 2)
    regression_metrics['test_fault_targets'] = int(len(y_test_cost))
    multi_test_idx = np.asarray([index for index in idx_test if len(parse_fault_costs(df.iloc[int(index)])) > 1], dtype=int)
    if len(multi_test_idx):
        multi_actual, multi_predicted = per_fault_combined_estimates(cost_pipeline, df, multi_test_idx, y, classes)
        combined_metrics = evaluate_regression(multi_actual, multi_predicted)
        combined_metrics['test_rows'] = int(len(multi_test_idx))
        regression_metrics['combined_multi_fault_totals'] = combined_metrics
    else:
        regression_metrics['combined_multi_fault_totals'] = {'mae': None, 'rmse': None, 'r2': None, 'test_rows': 0}

    # Test predictions provide auditable examples and allow independent review.
    prediction_rows = []
    for local_i, source_idx in enumerate(idx_test):
        actual = [classes[j] for j in np.where(y[idx_test[local_i]] == 1)[0]]
        predicted = [classes[j] for j in np.where(y_test_pred[local_i] == 1)[0]]
        is_correct = set(actual) == set(predicted)
        row = {
            'record_id': df.iloc[source_idx].get('record_id', source_idx),
            'input': json.dumps({key: df.iloc[source_idx].get(key) for key in ('vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'state', 'symptoms')}, ensure_ascii=False, default=lambda value: value.item() if hasattr(value, 'item') else str(value)),
            'symptoms': df.iloc[source_idx]['symptoms'],
            'actual_faults': ' | '.join(actual),
            'predicted_faults': ' | '.join(predicted),
            'exact_match': is_correct,
            'is_misclassified': not is_correct,
            'primary_fault': df.iloc[source_idx]['primary_fault'],
        }
        actual_total = float(df.iloc[source_idx]['total_repair_cost'])
        predicted_costs = []
        for category in predicted:
            input_row = df.iloc[source_idx].copy()
            input_row['problem_category'] = category
            predicted_costs.append(max(0.0, float(cost_pipeline.predict(cost_features(pd.DataFrame([input_row])))[0])))
        predicted_total = sum(predicted_costs) * (0.9 if len(predicted_costs) > 1 else 1.0)
        row['actual_cost'] = actual_total
        row['predicted_cost'] = round(predicted_total, 2)
        row['cost_absolute_error'] = round(abs(row['actual_cost'] - row['predicted_cost']), 2)
        prediction_rows.append(row)
    examples = []
    for kind, desired in [('correct', True), ('incorrect', False)]:
        seen_families = set()
        for row in prediction_rows:
            if bool(row['exact_match']) != desired:
                continue
            family = symptom_family(row['symptoms'])
            if family in seen_families:
                continue
            seen_families.add(family)
            examples.append((kind, row.copy()))
            if len(seen_families) >= 5:
                break
    pd.DataFrame(prediction_rows).to_csv(PREDICTIONS_PATH, index=False)
    classification_metrics['most_common_top1_confusions'] = top1_confusion_summary(
        df.iloc[idx_test]['primary_fault'].to_numpy(), test_proba, classes
    )
    classification_metrics['misclassified_test_rows_saved'] = int(sum(row['is_misclassified'] for row in prediction_rows))

    # Fit the backward-compatible single-label classifier on train+validation only.
    legacy = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', LogisticRegression(C=1.0, max_iter=1500, solver='lbfgs')),
    ])
    legacy.fit(text.iloc[idx_trainval], df.iloc[idx_trainval]['primary_fault'])
    atomic_joblib_dump(legacy, os.path.join(BASE_DIR, 'problem_classifier.pkl'))
    atomic_joblib_dump({'pipeline': selected_config, 'classes': classes, 'thresholds': {category: float(value) for category, value in zip(classes, selected['thresholds'])}, 'text_preprocessing': 'remove category annotation and append domain cue features', 'sklearn_version': sklearn.__version__}, os.path.join(BASE_DIR, 'multilabel_classifier.pkl'))
    atomic_joblib_dump(cost_pipeline, os.path.join(BASE_DIR, 'cost_regressor.pkl'))

    multi_count = int(np.sum(y.sum(axis=1) > 1))
    family_group_counts = {name: int(len(set(group_ids[idx]))) for name, idx in splits.items()}
    family_sets = {name: set(group_ids[idx]) for name, idx in splits.items()}
    split_overlap = sum(len(family_sets[a] & family_sets[b]) for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')])
    metrics = {
        'training_samples': int(len(df)),
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'classifier': {
            'accuracy': classification_metrics['primary_fault_accuracy'],
            'f1_weighted': classification_metrics['weighted_f1'],
            **classification_metrics,
        },
        'regressor': regression_metrics,
        'evaluation': {
            'dataset': os.path.basename(data_path),
            'split_method': 'Two-stage GroupShuffleSplit by normalized symptom family and primary class; test split drawn once with a fresh fixed seed.',
            'split_rows': {name: int(len(idx)) for name, idx in splits.items()},
            'split_family_groups': family_group_counts,
            'split_group_overlap': int(split_overlap),
            'split_seed': SPLIT_SEED,
            'validation_classifier_trials': validation_trials,
            'validation_cost_trials': cost_trials,
            'multi_label_rows': multi_count,
            'multi_fault_rows_two_labels': int(np.sum(y.sum(axis=1) == 2)),
            'multi_fault_rows_three_labels': int(np.sum(y.sum(axis=1) == 3)),
            'primary_only_rows': int(np.sum(y.sum(axis=1) == 1)),
            'sklearn_version': sklearn.__version__,
            'noise_config': noise_config,
            'prechange_text_audit': json.loads(Path(TEXT_AUDIT_PATH).read_text(encoding='utf-8')),
            'unique_symptom_descriptions_by_primary': {str(k): int(v) for k, v in df.groupby('primary_fault').symptoms.nunique().items()},
            'noise_row_counts': {
                'ambiguous_shared_symptoms': int(round(len(df) * noise_config['active_rates']['ambiguous_shared_symptoms'])),
                'typos_abbreviations_hinglish': int(round(len(df) * noise_config['active_rates']['typos_abbreviations_hinglish'])),
                'plausible_label_misdiagnoses': int(round(len(df) * noise_config['active_rates']['plausible_label_misdiagnoses'])),
            },
            'cost_target_definition': 'individual fault costs parsed from fault_costs; combined visit totals excluded from model training',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
        },
    }
    metrics['comparison_to_step5c'] = {
        'classifier': {
            key: {'step5c': float(baseline['classifier'][key]), 'step5d': float(classification_metrics[key]), 'change': round(float(classification_metrics[key]) - float(baseline['classifier'][key]), 4)}
            for key in ('micro_f1', 'macro_f1', 'exact_match_accuracy')
        },
        'regressor': {
            key: {'step5c': float(baseline['regressor'][key]), 'step5d': float(regression_metrics[key]), 'change': round(float(regression_metrics[key]) - float(baseline['regressor'][key]), 2 if key != 'r2' else 4)}
            for key in ('mae', 'rmse', 'r2')
        },
    }
    metrics_tmp = METRICS_PATH + '.tmp'
    with open(metrics_tmp, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    os.replace(metrics_tmp, METRICS_PATH)
    write_report(metrics, df, examples)
    print(json.dumps({'classifier': classification_metrics, 'regressor': regression_metrics, 'split_rows': metrics['evaluation']['split_rows'], 'split_seed': SPLIT_SEED, 'sklearn_version': sklearn.__version__, 'report': REPORT_PATH}, indent=2))
    return metrics


def write_report(metrics, df, examples):
    c = metrics['classifier']; r = metrics['regressor']; e = metrics['evaluation']
    comparison = metrics['comparison_to_step5c']
    noise = e['noise_config']
    audit = e['prechange_text_audit']
    common = audit['maximum_base_template_vocabulary_overlap']
    combined = r['combined_multi_fault_totals']
    lines = [
        '# ServiceWise Step 5d evaluation report', '',
        f"Evaluated: {e['created_at_utc']}",
        f"Dataset: `{e['dataset']}` ({len(df)} rows); scikit-learn {e['sklearn_version']}.", '',
        '## Pre-change symptom separability audit', '',
        f"- Before this regeneration, the dataset had {audit['unique_symptom_descriptions_overall']} unique symptom descriptions; per-primary counts ranged from {min(audit['unique_symptom_descriptions_by_primary'].values())} to {max(audit['unique_symptom_descriptions_by_primary'].values())}.",
        f"- The base phrase bank had {min(audit['base_fault_phrasing_templates_by_primary'].values())} to {max(audit['base_fault_phrasing_templates_by_primary'].values())} phrases per fault. Its largest vocabulary Jaccard overlap was {common['jaccard']:.4f} ({common['shared_terms']} shared terms) between {common['left']} and {common['right']}.",
        '- Despite many surface strings, the earlier set mostly repeated a small number of fault-specific symptom descriptions, which made the targets easy to separate. Step 5d adds shared complaints, informal wording, and paired diagnosis noise.',
        f"- Current unique symptom descriptions by primary fault: {json.dumps(e['unique_symptom_descriptions_by_primary'], ensure_ascii=False, sort_keys=True)}.", '',
        '## Noise settings', '',
        f"- Initial configured rates before training: ambiguous/shared {noise['initial_rates']['ambiguous_shared_symptoms']:.1%}, informal/typo {noise['initial_rates']['typos_abbreviations_hinglish']:.1%}, plausible misdiagnosis {noise['initial_rates']['plausible_label_misdiagnoses']:.1%}.",
        f"- Final active rates: ambiguous/shared {noise['active_rates']['ambiguous_shared_symptoms']:.1%}, informal/typo {noise['active_rates']['typos_abbreviations_hinglish']:.1%}, plausible misdiagnosis {noise['active_rates']['plausible_label_misdiagnoses']:.1%}; row counts {json.dumps(e['noise_row_counts'], sort_keys=True)}.",
        f"- Validation-only rate adjustments: {json.dumps(noise['rate_adjustments'], ensure_ascii=False)}.", '',
        '## Split and model selection', '',
        '- Split unit: normalized symptom family paired with primary fault; related wording within a primary class stays together.',
        f"- Fresh grouped split: {json.dumps(e['split_rows'], sort_keys=True)} rows; seed {e['split_seed']}; {e['split_group_overlap']} group overlaps.",
        f"- Validation selected among {len(e['validation_classifier_trials'])} classifier configurations by micro-F1 only; per-label thresholds were tuned on validation. The first final-run attempt computed test metrics but stopped during JSON serialization; the unchanged deterministic run was repeated to persist artifacts. No test result was used to adjust records, rates, or model settings.",
        f"- Validation micro-F1: {c['validation_micro_f1']:.4f}. Test headline micro-F1: **{c['micro_f1']:.4f}** ({'above' if c['micro_f1'] > .83 else 'below'} 0.83).", '',
        '## Fault classifier test metrics', '',
        f"- Primary fault included in predicted list: {c['primary_fault_in_predicted_list_rate']:.4f}.",
        f"- Macro-F1: {c['macro_f1']:.4f}; exact-match accuracy: {c['exact_match_accuracy']:.4f}.",
        f"- Single-fault top-1 accuracy: {c['top1_accuracy_single_fault_rows']:.4f} on {c['single_fault_test_rows']} test rows.",
        f"- Exact multi-label errors saved in `test_set_predictions.csv`: {c['misclassified_test_rows_saved']} of {len(pd.read_csv(PREDICTIONS_PATH))} test predictions.", '',
        '| Fault category | Precision | Recall | F1 | Support |', '|---|---:|---:|---:|---:|',
    ]
    for category, value in c['per_category'].items():
        lines.append(f"| {category} | {value['precision']:.4f} | {value['recall']:.4f} | {value['f1']:.4f} | {value['support']} |")
    lines += ['', '### Most common primary top-1 confusions', '', '| Actual primary | Predicted top-1 | Count |', '|---|---|---:|']
    for row in c['most_common_top1_confusions']:
        lines.append(f"| {row['actual_primary']} | {row['predicted_top1']} | {row['count']} |")
    lines += ['', '## Comparison with Step 5c', '',
        'Step 5c used a different noise profile and grouped test split; values are project-level comparisons, not paired examples.',
        '', '| Metric | Step 5c | Step 5d | Change |', '|---|---:|---:|---:|']
    for key, label in [('micro_f1', 'Micro-F1'), ('macro_f1', 'Macro-F1'), ('exact_match_accuracy', 'Exact-match accuracy')]:
        item = comparison['classifier'][key]
        lines.append(f"| {label} | {item['step5c']:.4f} | {item['step5d']:.4f} | {item['change']:+.4f} |")
    for key, label in [('mae', 'Per-fault cost MAE (₹)'), ('rmse', 'Per-fault cost RMSE (₹)'), ('r2', 'Per-fault cost R²')]:
        item = comparison['regressor'][key]
        lines.append(f"| {label} | {item['step5c']:.4f} | {item['step5d']:.4f} | {item['change']:+.4f} |")
    lines += ['', '## Cost test metrics', '',
        f"- Selected on validation by individual-fault MAE: `{r['selected_model']}`. Per-fault MAE ₹{r['mae']:.2f}; RMSE ₹{r['rmse']:.2f}; R² {r['r2']:.4f} across {r['test_fault_targets']} fault targets.",
        f"- Combined multi-fault totals ({combined['test_rows']} rows): MAE ₹{combined['mae']:.2f}; RMSE ₹{combined['rmse']:.2f}; R² {combined['r2']:.4f}.",
        '- Cost training expands each record into individual targets from `fault_costs`; combined visit totals are excluded from fitting. Combined estimates sum fault-level predictions and apply the shared-visit rule.', '',
        '## Dataset balance and limits', '',
        f"- Primary labels: 300 per category; multi-fault rows: {e['multi_label_rows']} ({e['multi_label_rows']/len(df):.1%}), including {e['multi_fault_rows_two_labels']} two-fault and {e['multi_fault_rows_three_labels']} three-fault rows.",
        '- Ambiguous descriptions, typos/Hinglish, and label swaps are configured rates, not verified workshop annotations. High scores can still reflect the controlled phrase bank and do not establish real-world diagnostic performance.',
        '- Combined cost results use stored combined totals and the shared-visit discount; regional price overrides are not applied in these model metrics.', '',
        '## Artifacts', '',
        '- `multilabel_classifier.pkl` — selected classifier and per-category thresholds.',
        '- `problem_classifier.pkl` — backward-compatible classifier.',
        '- `cost_regressor.pkl` — per-fault cost model.',
        '- `model_metrics.json` — measured results, selected noise rates, and split details.',
        '- `test_set_predictions.csv` — all final test rows, including every actual misclassification, with input and costs.',
        '',
        'Note: The prepared dataset is simulated; its fault labels and repair costs are not verified workshop records.',
    ]
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validation-only', action='store_true', help='select on training/validation without scoring or saving test predictions')
    args = parser.parse_args()
    train_and_save(validation_only=args.validation_only)
