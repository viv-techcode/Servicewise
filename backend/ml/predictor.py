import os
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Predictor:
    def __init__(self):
        classifier_path = os.path.join(BASE_DIR, 'problem_classifier.pkl')
        regressor_path = os.path.join(BASE_DIR, 'cost_regressor.pkl')
        self.classifier = joblib.load(classifier_path)
        self.regressor = joblib.load(regressor_path)

    def predict(self, input_data):
        problem_category = self.classifier.predict([input_data['symptoms']])[0]

        features_df = pd.DataFrame([input_data])
        features_df['problem_category'] = problem_category
        features_df = features_df[['vehicle_type', 'vehicle_brand', 'vehicle_age', 'km_driven', 'problem_category']]

        cost_point = self.regressor.predict(features_df)[0]

        symptoms = input_data['symptoms'].lower()
        urgency = "Low"
        if any(word in symptoms for word in ['brake', 'overheating', 'smoke', 'failure']):
            urgency = "High"
        elif any(word in symptoms for word in ['clicking', 'noise', 'starting']):
            urgency = "Medium"

        return {
            "problem_category": problem_category,
            "estimated_cost_min": int(cost_point * 0.8),
            "estimated_cost_max": int(cost_point * 1.2),
            "urgency": urgency,
            "recommendation": "Professional mechanical inspection recommended."
        }
