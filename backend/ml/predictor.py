"""Runtime multilabel diagnosis with CSV-backed repair cost estimates."""
from __future__ import annotations

import json
import os

import joblib
import pandas as pd

from backend.ml.fault_text import prepare_classifier_text
from backend.ml.severity import (
    LEVEL_RANK, combined_severity, detect_fault_categories,
    detect_red_flag_faults, severity_for_fault,
)
from backend.discount_rules import MULTI_FAULT_DISCOUNT_RATE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'service_records.csv')


class ModelUnavailableError(RuntimeError):
    """Raised when the required fault classifier cannot be loaded."""


class Predictor:
    def __init__(self):
        self._load_model()
        self.cost_lookup = self._load_cost_lookup()

    def _load_model(self):
        model_path = os.path.join(BASE_DIR, 'multilabel_classifier.pkl')
        try:
            self.multilabel = joblib.load(model_path)
        except Exception as exc:
            self.multilabel = None
            self.model_error = f"Fault prediction model could not be loaded: {exc}"
        else:
            self.model_error = None
        version_path = os.path.join(BASE_DIR, 'active_model_version.json')
        try:
            with open(version_path, encoding='utf-8') as handle:
                self.model_version = json.load(handle).get('version', 'unknown')
        except (OSError, ValueError):
            self.model_version = 'unknown'

    @staticmethod
    def _load_cost_lookup():
        df = pd.read_csv(DATA_PATH)
        grouped = {}
        for row in df.itertuples(index=False):
            try:
                costs = json.loads(row.per_fault_cost) if isinstance(row.per_fault_cost, str) else {}
            except (TypeError, ValueError):
                costs = {}
            for category, amount in costs.items():
                try:
                    value = float(amount)
                except (TypeError, ValueError):
                    continue
                if value >= 0:
                    grouped.setdefault((category, row.vehicle_type), []).append(value)
        return {
            key: {
                'median': float(pd.Series(values).median()),
                'q25': float(pd.Series(values).quantile(.25)),
                'q75': float(pd.Series(values).quantile(.75)),
            }
            for key, values in grouped.items()
        }

    def refresh_if_model_changed(self):
        version_path = os.path.join(BASE_DIR, 'active_model_version.json')
        try:
            with open(version_path, encoding='utf-8') as handle:
                active_version = json.load(handle).get('version', 'unknown')
        except (OSError, ValueError):
            return
        if active_version != self.model_version:
            self._load_model()

    def predict(self, input_data):
        self.refresh_if_model_changed()
        if self.multilabel is None:
            raise ModelUnavailableError(self.model_error or 'Fault prediction model is unavailable.')

        pipeline = self.multilabel['pipeline']
        classes = self.multilabel['classes']
        probabilities = pipeline.predict_proba([prepare_classifier_text(input_data['symptoms'])])[0]
        thresholds = self.multilabel.get('thresholds')
        if isinstance(thresholds, dict):
            thresholds = [float(thresholds.get(category, self.multilabel.get('threshold', .35))) for category in classes]
        else:
            thresholds = float(self.multilabel.get('threshold', .35))
        probabilities_by_category = {category: float(probability) for category, probability in zip(classes, probabilities)}
        faults = [
            {'category': category, 'confidence': float(probability)}
            for index, (category, probability) in enumerate(zip(classes, probabilities))
            if probability >= (thresholds[index] if isinstance(thresholds, list) else thresholds)
        ]
        # Explicit system cues and safety red flags supplement the learned model.
        # A lexical safety flag must not disappear because a model threshold is high.
        detected = detect_fault_categories(symptoms := input_data['symptoms'])
        # When explicit system evidence exists, do not add unrelated model guesses.
        # For vague complaints the multilabel model remains the fallback.
        if detected:
            faults = [item for item in faults if item['category'] in detected]
        existing = {item['category'] for item in faults}
        for category in detected - existing:
            if category not in classes:
                continue
            confidence = probabilities_by_category.get(category, 0.0)
            floor = .95 if category in detect_red_flag_faults(symptoms) else .64
            faults.append({'category': category, 'confidence': max(confidence, floor)})
        if not faults:
            best = int(probabilities.argmax())
            faults = [{'category': classes[best], 'confidence': float(probabilities[best])}]
        faults.sort(key=lambda item: item['confidence'], reverse=True)
        per_fault_severity = {
            fault['category']: severity_for_fault(fault['category'], symptoms)
            for fault in faults
        }
        for fault in faults:
            fault['severity'] = per_fault_severity[fault['category']]
        combined = combined_severity([fault['category'] for fault in faults], per_fault_severity)
        breakdown = []
        for fault in faults:
            category = fault['category']
            stats = self.cost_lookup.get((category, input_data['vehicle_type']))
            if stats is None:
                stats = self.cost_lookup.get((category, 'car'), {'q25': 0, 'median': 0, 'q75': 0})
            breakdown.append({
                'category': category,
                'confidence': fault['confidence'],
                'estimated_cost_min': max(0, int(round(stats['q25']))),
                'estimated_cost_max': max(0, int(round(stats['q75']))),
                'estimated_cost_median': max(0, int(round(stats['median']))),
                'estimate_source': 'dataset_cost_lookup',
                'price_reference': None,
            })

        # The primary fault is the most severe; ties go to the higher median cost.
        primary = max(faults, key=lambda fault: (
            LEVEL_RANK[per_fault_severity[fault['category']]],
            self.cost_lookup.get((fault['category'], input_data['vehicle_type']), {}).get('median', 0),
        ))
        faults.sort(key=lambda item: (-LEVEL_RANK[per_fault_severity[item['category']]], -item['confidence']))

        discount_rate = MULTI_FAULT_DISCOUNT_RATE if len(breakdown) > 1 else 0.0
        raw_min = sum(item['estimated_cost_min'] for item in breakdown)
        raw_max = sum(item['estimated_cost_max'] for item in breakdown)
        median_estimate = sum(item['estimated_cost_median'] for item in breakdown)
        total_min = int(round(raw_min * (1 - discount_rate)))
        total_max = int(round(raw_max * (1 - discount_rate)))
        discount = {
            'rate': discount_rate,
            'amount_min': raw_min - total_min,
            'amount_max': raw_max - total_max,
            'rule': '10% once on combined estimate when multiple faults are serviced in one visit' if discount_rate else 'No multi-fault visit discount',
        }
        advice = {
            'Brake System': 'Avoid riding or driving until the brake system has been inspected.',
            'Cooling System': 'If temperature is rising or steam is present, stop safely and let the engine cool before inspection.',
            'Fuel System': 'If fuel is leaking or fumes are strong, switch off the engine and keep ignition sources away.',
        }
        timing = {'critical': 'Stop driving and arrange a tow and inspection now.', 'high': 'Arrange an inspection within 24 hours.', 'medium': 'Arrange an inspection this week.', 'low': 'Raise this at the next scheduled service.'}[combined]
        specific = [advice[fault['category']] for fault in faults if fault['category'] in advice]
        recommendation = ' '.join([timing, *dict.fromkeys(specific)])
        return {
            'problem_category': primary['category'],
            'model_version': self.model_version,
            'predicted_faults': faults,
            'per_fault_severity': per_fault_severity,
            'severity': combined,
            'combined_severity': combined,
            'estimated_cost_min': total_min,
            'estimated_cost_max': total_max,
            'estimated_cost': int(round(median_estimate * (1 - discount_rate))),
            'combined_estimated_cost_min': total_min,
            'combined_estimated_cost_max': total_max,
            'fault_cost_breakdown': breakdown,
            'shared_visit_discount': discount,
            'cost_estimate_basis': 'main dataset per-fault cost quartiles; median totals receive a 10% multi-fault discount',
            'price_reference': None,
            'urgency': combined,
            'recommendation': recommendation,
        }
