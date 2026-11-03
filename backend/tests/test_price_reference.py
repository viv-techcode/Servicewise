import pandas as pd

from backend.ml.predictor import Predictor


def test_workshop_dataset_has_splits_and_per_fault_costs():
    import json
    df = pd.read_csv('backend/data/service_records.csv')
    assert 4000 <= len(df) <= 6000
    assert df.service_date.min() == '2025-01-01'
    assert df.service_date.max() == '2026-10-31'
    row = df[df.fault_count.astype(int) > 1].iloc[0]
    assert len(json.loads(row.parts_used)) == row.fault_count
    assert set(json.loads(row.per_fault_cost)) == set(row.faults.split(';'))


def test_reference_has_explicit_coverage_for_every_target_pair():
    ref = pd.read_csv('backend/data/north_india_repair_price_reference.csv')
    states = ['Uttar Pradesh', 'Delhi', 'Haryana', 'Punjab', 'Rajasthan', 'Uttarakhand', 'Himachal Pradesh', 'Jammu and Kashmir']
    categories = ['Battery/Electrical', 'Brake System', 'Cooling System', 'Engine', 'Fuel System', 'General Maintenance', 'Starting System', 'Suspension', 'Transmission', 'Tyres/Wheels']
    assert set((state, category) for state, category in zip(ref['state'], ref['fault_category']) if state in states) == set((state, category) for state in states for category in categories)
    priced = ref[ref['availability'] == 'priced']
    assert priced['source_url'].str.startswith('https://').all()
    bounded = priced['price_min'].notna() & priced['price_max'].notna()
    assert (priced.loc[bounded, 'price_min'] <= priced.loc[bounded, 'price_max']).all()


def test_predictor_uses_dataset_cost_lookup():
    predictor = Predictor()
    result = predictor.predict({
        'state': 'Global', 'vehicle_type': 'bike', 'vehicle_brand': 'Hero', 'vehicle_model': 'Splendor Plus',
        'vehicle_age': 4, 'km_driven': 24000, 'symptoms': 'Brakes squeal when stopping.'
    })
    assert 'dataset' in result['cost_estimate_basis']
    assert all(item['estimate_source'] == 'dataset_cost_lookup' for item in result['fault_cost_breakdown'])


def test_predictor_cost_does_not_change_by_location():
    predictor = Predictor()
    details = {'vehicle_type': 'bike', 'vehicle_brand': 'Honda', 'vehicle_model': 'Shine 125', 'vehicle_age': 3, 'km_driven': 18000, 'symptoms': 'Brakes feel weak.'}
    local = predictor.predict({**details, 'state': 'Delhi'})
    global_result = predictor.predict({**details, 'state': 'Global'})
    assert local['estimated_cost_min'] == global_result['estimated_cost_min']
    assert local['estimated_cost_max'] == global_result['estimated_cost_max']
