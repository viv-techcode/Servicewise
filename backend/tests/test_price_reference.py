import pandas as pd

from backend.ml.predictor import Predictor


def test_prepared_dataset_remains_balanced_and_price_splits_consistent():
    df = pd.read_csv('backend/data/service_records_balanced_3000.csv')
    assert len(df) == 3000
    assert df['primary_fault'].value_counts().eq(300).all()
    split = df['parts_cost'].notna() & df['labour_cost'].notna()
    assert (df.loc[split, 'parts_cost'] + df.loc[split, 'labour_cost'] == df.loc[split, 'actual_repair_cost']).all()
    parsed = df.loc[~df.simultaneous_faults.isin(['none', 'not_recorded'])].iloc[0]
    costs = __import__('json').loads(parsed.fault_costs)
    assert parsed.total_repair_cost == round(sum(costs.values()) * .9)


def test_reference_has_explicit_coverage_for_every_target_pair():
    ref = pd.read_csv('backend/data/north_india_repair_price_reference.csv')
    states = ['Uttar Pradesh', 'Delhi', 'Haryana', 'Punjab', 'Rajasthan', 'Uttarakhand', 'Himachal Pradesh', 'Jammu and Kashmir']
    categories = ['Battery/Electrical', 'Brake System', 'Cooling System', 'Engine', 'Fuel System', 'General Maintenance', 'Starting System', 'Suspension', 'Transmission', 'Tyres/Wheels']
    assert set((state, category) for state, category in zip(ref['state'], ref['fault_category']) if state in states) == set((state, category) for state in states for category in categories)
    priced = ref[ref['availability'] == 'priced']
    assert priced['source_url'].str.startswith('https://').all()
    bounded = priced['price_min'].notna() & priced['price_max'].notna()
    assert (priced.loc[bounded, 'price_min'] <= priced.loc[bounded, 'price_max']).all()


def test_predictor_uses_matching_researched_state_vehicle_range():
    predictor = Predictor()
    price = predictor._regional_price('Brake System', {
        'state': 'Delhi', 'vehicle_type': 'bike', 'vehicle_model': 'Classic 350', 'symptoms': 'brake pad squeal and weak braking'
    })
    assert price is not None
    assert price['minimum'] == 249
    assert price['maximum'] == 349
    assert price['source'].startswith('https://')


def test_predictor_respects_engine_size_qualifier():
    predictor = Predictor()
    price = predictor._regional_price('Brake System', {
        'state': 'Delhi', 'vehicle_type': 'bike', 'vehicle_model': 'Activa 125', 'symptoms': 'brake pad squeal'
    })
    assert price is None


def test_predictor_does_not_extrapolate_unavailable_state_prices():
    predictor = Predictor()
    price = predictor._regional_price('Brake System', {
        'state': 'Punjab', 'vehicle_type': 'bike', 'symptoms': 'brakes feel weak'
    })
    assert price is None
