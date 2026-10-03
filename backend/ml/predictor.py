import os
import joblib
import pandas as pd
import re
from backend.ml.fault_text import prepare_classifier_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Predictor:
    def __init__(self):
        self._load_models()

    def _load_models(self):
        classifier_path = os.path.join(BASE_DIR, 'problem_classifier.pkl')
        multilabel_path = os.path.join(BASE_DIR, 'multilabel_classifier.pkl')
        regressor_path = os.path.join(BASE_DIR, 'cost_regressor.pkl')
        self.classifier = joblib.load(classifier_path)
        self.multilabel = joblib.load(multilabel_path) if os.path.exists(multilabel_path) else None
        self.regressor = joblib.load(regressor_path)
        version_path = os.path.join(BASE_DIR, 'active_model_version.json')
        if os.path.exists(version_path):
            try:
                import json
                with open(version_path, encoding='utf-8') as handle:
                    self.model_version = json.load(handle).get('version', 'baseline-step5d')
            except (OSError, ValueError):
                self.model_version = 'baseline-step5d'
        else:
            self.model_version = (self.multilabel or {}).get('model_version', 'baseline-step5d')
        reference_path = os.path.join(BASE_DIR, '..', 'data', 'north_india_repair_price_reference.csv')
        self.price_reference = pd.read_csv(reference_path) if os.path.exists(reference_path) else pd.DataFrame()

    def refresh_if_model_changed(self):
        version_path = os.path.join(BASE_DIR, 'active_model_version.json')
        if not os.path.exists(version_path):
            return
        try:
            import json
            with open(version_path, encoding='utf-8') as handle:
                active_version = json.load(handle).get('version', 'baseline-step5d')
        except (OSError, ValueError):
            return
        if active_version != self.model_version:
            self._load_models()

    def _regional_price(self, category, input_data):
        state = input_data.get('state')
        symptoms = str(input_data.get('symptoms', '')).lower()
        if not state or self.price_reference.empty:
            return None
        # Match only published complete ranges with an explicit state and
        # vehicle class. Starting prices and national/unlocated evidence are
        # excluded because they cannot support a defensible bounded estimate.
        rows = self.price_reference[
            (self.price_reference['fault_category'] == category) &
            (self.price_reference['state'] == state) &
            (self.price_reference['vehicle_type'] == input_data.get('vehicle_type')) &
            (self.price_reference['availability'] == 'priced') &
            self.price_reference['price_min'].notna() &
            self.price_reference['price_max'].notna()
        ]
        for _, ref in rows.iterrows():
            job = str(ref['repair_or_part']).lower()
            details = str(ref.get('vehicle_details', '')).lower()
            if 'above-180cc' in details and input_data.get('vehicle_type') == 'bike':
                cc = re.search(r'\b(\d{3,4})\b', str(input_data.get('vehicle_model', '')))
                if not cc or int(cc.group(1)) <= 180:
                    continue
            terms = [term for term in ('brake', 'battery', 'service') if term in job]
            if terms and not any(term in symptoms for term in terms):
                continue
            if not terms:
                continue
            return {
                'minimum': int(ref['price_min']),
                'maximum': int(ref['price_max']),
                'source': str(ref['source_url']),
                'basis': str(ref['price_basis']),
                'location': str(ref['state_or_city']),
            }
        return None

    def predict(self, input_data):
        self.refresh_if_model_changed()
        if self.multilabel:
            pipeline = self.multilabel['pipeline']
            classes = self.multilabel['classes']
            probabilities = pipeline.predict_proba([prepare_classifier_text(input_data['symptoms'])])[0]
            thresholds = self.multilabel.get('thresholds')
            if isinstance(thresholds, dict):
                thresholds = [float(thresholds.get(category, self.multilabel.get('threshold', 0.35))) for category in classes]
            else:
                thresholds = float(self.multilabel.get('threshold', 0.35))
            faults = [
                {'category': category, 'confidence': float(probability)}
                for index, (category, probability) in enumerate(zip(classes, probabilities))
                if probability >= (thresholds[index] if isinstance(thresholds, list) else thresholds)
            ]
            if not faults:
                best = int(probabilities.argmax())
                faults = [{'category': classes[best], 'confidence': float(probabilities[best])}]
            faults.sort(key=lambda item: item['confidence'], reverse=True)
            problem_category = faults[0]['category']
        else:
            model_text = prepare_classifier_text(input_data['symptoms'])
            problem_category = self.classifier.predict([model_text])[0]
            probs = self.classifier.predict_proba([model_text])[0] if hasattr(self.classifier, 'predict_proba') else [1.0]
            confidence = float(max(probs))
            faults = [{'category': problem_category, 'confidence': confidence}]

        fault_costs = []
        for fault in faults:
            category = fault['category']
            features_df = pd.DataFrame([input_data])
            features_df['problem_category'] = category
            features_df['state'] = features_df.get('state', pd.Series([None])).fillna('not_recorded').replace('', 'not_recorded')
            expected_features = list(getattr(self.regressor, 'feature_names_in_', ['vehicle_type', 'vehicle_brand', 'vehicle_age', 'km_driven', 'problem_category']))
            features_df = features_df.reindex(columns=expected_features)
            regional_price = self._regional_price(category, input_data)
            if regional_price:
                minimum, maximum = regional_price['minimum'], regional_price['maximum']
            else:
                cost_point = float(self.regressor.predict(features_df)[0])
                minimum = max(0, int(cost_point * 0.8))
                maximum = max(minimum, int(cost_point * 1.2))
            fault_costs.append({
                'category': category,
                'confidence': fault['confidence'],
                'estimated_cost_min': minimum,
                'estimated_cost_max': maximum,
                'estimate_source': 'regional_reference' if regional_price else 'cost_model',
                'price_reference': regional_price,
            })

        base_minimum = sum(item['estimated_cost_min'] for item in fault_costs)
        base_maximum = sum(item['estimated_cost_max'] for item in fault_costs)
        discount_rate = 0.10 if len(fault_costs) > 1 else 0.0
        total_minimum = int(round(base_minimum * (1 - discount_rate)))
        total_maximum = int(round(base_maximum * (1 - discount_rate)))
        shared_visit_discount = {
            'rate': discount_rate,
            'amount_min': base_minimum - total_minimum,
            'amount_max': base_maximum - total_maximum,
            'rule': '10% once on combined estimate when multiple faults are serviced in one visit' if discount_rate else 'No multi-fault visit discount',
        }
        primary_reference = fault_costs[0]['price_reference'] if fault_costs else None

        symptoms = input_data['symptoms'].lower()
        urgency = "Low"
        if any(word in symptoms for word in ['brake', 'overheating', 'smoke', 'failure']):
            urgency = "High"
        elif any(word in symptoms for word in ['clicking', 'noise', 'starting']):
            urgency = "Medium"

        return {
            "problem_category": problem_category,
            "model_version": self.model_version,
            "predicted_faults": faults,
            "estimated_cost_min": total_minimum,
            "estimated_cost_max": total_maximum,
            "combined_estimated_cost_min": total_minimum,
            "combined_estimated_cost_max": total_maximum,
            "fault_cost_breakdown": fault_costs,
            "shared_visit_discount": shared_visit_discount,
            "cost_estimate_basis": "per-fault regional references where matched, otherwise cost model",
            "price_reference": primary_reference,
            "urgency": urgency,
            "recommendation": "Professional mechanical inspection recommended."
        }
