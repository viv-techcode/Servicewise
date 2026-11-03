"""Independently audit generated service, inventory, and finance CSVs."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.discount_rules import MULTI_FAULT_DISCOUNT_RATE
from backend.ml.severity import combined_severity, severity_for_fault, detect_red_flag_faults

ROOT = Path(__file__).resolve().parent
SERVICE_DATE_MIN, SERVICE_DATE_MAX = '2025-01-01', '2026-10-31'
LEVELS = ['low', 'medium', 'high', 'critical']
BASE = {
    'Battery/Electrical': 'medium', 'Brake System': 'medium', 'Cooling System': 'medium',
    'Engine': 'medium', 'Fuel System': 'medium', 'General Maintenance': 'low',
    'Starting System': 'medium', 'Suspension': 'medium', 'Transmission': 'medium', 'Tyres/Wheels': 'low',
}
CRITICAL = ['brake failure', 'fuel is leaking heavily', 'overheating rapidly', 'oil pressure warning', 'sidewall blowout']
HIGH = ['pedal sinks', 'stopping distance is longer', 'engine temperature rises', 'steam is visible', 'strong petrol smell', 'stalls at signals', 'clutch slips', 'does not start after several', 'bearing noise']
MEDIUM = ['warning light', 'drops overnight', 'flicker', 'grinds', 'misfires', 'hesitates', 'knock', 'coolant', 'slowly drops', 'vibrates', 'clunks', 'stiff when shifting']
CRITICAL_BY_FAULT = {
    'Brake System': ['brake failure'], 'Cooling System': ['overheating rapidly'],
    'Engine': ['oil pressure warning'], 'Fuel System': ['fuel is leaking heavily'],
    'Tyres/Wheels': ['sidewall blowout'],
}
HIGH_BY_FAULT = {
    'Brake System': ['pedal sinks', 'stopping distance is longer'],
    'Cooling System': ['engine temperature rises', 'steam is visible'],
    'Engine': ['stalls at signals', 'engine misfires', 'loud engine knock'],
    'Fuel System': ['strong petrol smell'], 'Transmission': ['clutch slips'],
    'Starting System': ['does not start after several'], 'Tyres/Wheels': ['bearing noise'],
}
MEDIUM_BY_FAULT = {
    'Battery/Electrical': ['warning light', 'drops overnight', 'flicker', 'battery', 'electrical'],
    'Brake System': ['grinds', 'brake'], 'Cooling System': ['coolant', 'temperature'],
    'Engine': ['knock', 'misfires', 'hesitates', 'engine'], 'Fuel System': ['fuel', 'petrol'],
    'General Maintenance': ['oil', 'filter', 'service', 'maintenance', 'inspection'],
    'Starting System': ['starter', 'start', 'ignition', 'crank'],
    'Suspension': ['shock', 'suspension', 'clunk', 'bounces'],
    'Transmission': ['gear', 'belt', 'chain', 'transmission'],
    'Tyres/Wheels': ['wheel vibrates'],
}
DANGEROUS = [
    {'Brake System', 'Tyres/Wheels'}, {'Brake System', 'Suspension'},
    {'Cooling System', 'Engine'}, {'Fuel System', 'Engine'},
]
CUES = {
    'Battery/Electrical': ('battery', 'electrical', 'headlight', 'horn', 'dashboard', 'charge'),
    'Brake System': ('brake',), 'Cooling System': ('coolant', 'radiator', 'overheating', 'temperature', 'cooling fin', 'garam', 'hotter', 'engine heat', 'hot', 'airflow'),
    'Engine': ('engine', 'engin', 'oil pressure', 'exhaust', 'misfire'), 'Fuel System': ('fuel', 'petrol', 'exhaust smoke'),
    'General Maintenance': ('oil', 'filter', 'service', 'maintenance', 'inspection', 'routine'),
    'Starting System': ('starter', 'start', 'ignition', 'crank'),
    'Suspension': ('shock', 'suspension', 'clunk', 'bounces', 'unstable'),
    'Transmission': ('gear', 'clutch', 'belt', 'chain', 'transmission', 'drive system', 'variator', 'automatic', 'scooter drive'),
    'Tyres/Wheels': ('tyre', 'wheel', 'puncture', 'pressure', 'pulls slightly'),
}
SERVICE_COLUMNS = [
    'job_id', 'service_date', 'service_time', 'vehicle_type', 'brand', 'model', 'age', 'km_driven',
    'symptoms', 'symptom_template_id', 'primary_fault', 'faults', 'fault_count', 'per_fault_severity', 'severity', 'parts_used',
    'per_fault_cost', 'customer_charge', 'parts_cost', 'labour_cost', 'gross_margin', 'discount',
    'stockout_delay_days', 'status',
]


def severity_for(category, symptoms):
    text = symptoms.lower()
    if any(term in text for term in CRITICAL_BY_FAULT.get(category, [])):
        return 'critical'
    if any(term in text for term in HIGH_BY_FAULT.get(category, [])):
        return 'high'
    if any(term in text for term in MEDIUM_BY_FAULT.get(category, [])):
        return 'medium'
    return BASE[category]


def combined_for(faults, per_fault):
    index = max(LEVELS.index(per_fault[fault]) for fault in faults)
    if any(pair <= set(faults) for pair in DANGEROUS):
        index += 1
    if len(faults) == 3:
        index += 1
    return LEVELS[min(index, 3)]


def validate(service_path=None):
    service = pd.read_csv(service_path or ROOT / 'service_records.csv', keep_default_na=False)
    stock = pd.read_csv(ROOT / 'inventory_stock.csv', keep_default_na=False)
    ledger = pd.read_csv(ROOT / 'inventory_log.csv', keep_default_na=False)
    monthly = pd.read_csv(ROOT / 'monthly_summary.csv', keep_default_na=False)
    assert list(service.columns) == SERVICE_COLUMNS, f'Service columns mismatch: {list(service.columns)}'
    assert 4000 <= len(service) <= 6000, f'Unexpected job count: {len(service)}'
    assert not service.job_id.duplicated().any()
    assert service.service_date.between('2025-01-01', '2026-10-31').all()
    assert service.job_id.tolist() == service.assign(_timestamp=pd.to_datetime(service.service_date + ' ' + service.service_time)).sort_values(['_timestamp','job_id']).job_id.tolist(), 'Job IDs not chronological'
    seen_days = set(service.service_date)
    expected_days = {(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range((date(2026, 10, 31) - date(2025, 1, 1)).days + 1)}
    assert SERVICE_DATE_MIN <= min(seen_days) <= max(seen_days) <= SERVICE_DATE_MAX

    stock_by_id = stock.set_index('part_id').to_dict('index')
    assert len(stock_by_id) >= 60, f'Expected ~60 SKUs, got {len(stock_by_id)}'
    assert (pd.to_numeric(stock.stock) >= 0).all(), 'Negative snapshot stock'
    assert (pd.to_numeric(stock.reorder_level) >= 0).all()
    assert (pd.to_numeric(stock.opening_stock) >= pd.to_numeric(stock.reorder_level)).all(), 'Opening stock below reorder level'
    assert (pd.to_numeric(stock.unit_cost) > 0).all() and (pd.to_numeric(stock.unit_price) >= pd.to_numeric(stock.unit_cost)).all()
    running = {part_id: 0 for part_id in stock_by_id}
    ledger_sorted = ledger.sort_values(['event_date', 'event_time', 'event_id'])
    sale_part_pairs = set()
    stockout_jobs = set()
    for row in ledger_sorted.itertuples(index=False):
        assert row.part_id in running, f'Unknown ledger part: {row.part_id}'
        assert row.event_type in {'opening_stock', 'restock', 'sale', 'stock_out'}
        delta = int(row.quantity_change)
        if row.event_type == 'opening_stock':
            assert delta >= 0
        elif row.event_type == 'restock':
            assert delta > 0
        elif row.event_type == 'sale':
            assert delta == -1
            sale_part_pairs.add((row.job_id, row.part_id))
        else:
            assert delta == 0
            stockout_jobs.add(row.job_id)
        running[row.part_id] += delta
        assert running[row.part_id] >= 0, f'Negative stock at ledger event {row.event_id}'
        assert int(row.stock_after) == running[row.part_id], f'Ledger running balance mismatch at {row.event_id}'
    for part_id, snapshot in stock_by_id.items():
        assert running[part_id] == int(snapshot['stock']), f'Snapshot does not reconcile for {part_id}'

    fault_counts = Counter()
    severity_counts = Counter()
    fault_count_counts = Counter()
    jobs = service.set_index('job_id')
    for row in service.itertuples(index=False):
        faults = row.faults.split(';')
        assert row.primary_fault in faults, f'{row.job_id}: primary fault is absent from fault labels'
        assert int(row.fault_count) == len(faults) and 1 <= len(faults) <= 3
        fault_count_counts[len(faults)] += 1
        assert len(set(faults)) == len(faults)
        per_severity = json.loads(row.per_fault_severity)
        per_cost = json.loads(row.per_fault_cost)
        part_ids = json.loads(row.parts_used)
        assert set(per_severity) == set(faults)
        assert set(per_cost) == set(faults)
        assert len(part_ids) >= len(faults)
        assert abs(sum(float(value) for value in per_cost.values()) - float(row.customer_charge)) < .02, f'{row.job_id}: per-fault charges do not sum to customer charge'
        used_by_fault = Counter()
        for part_id in part_ids:
            assert part_id in stock_by_id, f'{row.job_id}: unknown part {part_id}'
            part = stock_by_id[part_id]
            category = part['fault_category']
            assert category in CUES, f'Unknown fault: {category}'
            assert category in faults, f'{row.job_id}: part for unrelated fault {category}'
            used_by_fault[category] += 1
            assert part['vehicle_type'] == row.vehicle_type
            compatible = json.loads(part['compatible_models'])
            assert row.model in compatible, f'{row.job_id}: incompatible part {part_id}'
            if row.model in ('Activa 6G', 'Jupiter 110'):
                name = str(part['part_name']).lower()
                assert 'clutch cable' not in name and 'handbrake cable' not in name
            assert (row.job_id, part_id) in sale_part_pairs, f'{row.job_id}: part issue missing from ledger'
        assert set(used_by_fault) == set(faults)
        assert all(1 <= used_by_fault[f] <= 3 for f in faults), f'{row.job_id}: expected 1-3 parts per fault: {used_by_fault}'
        for category in faults:
            assert any(cue in row.symptoms.lower() for cue in CUES[category]), f'{row.job_id}: {category} absent from symptoms'
            assert per_severity[category] in LEVELS
            red_faults = detect_red_flag_faults(row.symptoms)
            if category in red_faults:
                assert LEVELS.index(per_severity[category]) >= LEVELS.index(severity_for_fault(category, row.symptoms)), f'{row.job_id}: red flag under-predicted for {category}'
            assert float(per_cost[category]) >= 0
            fault_counts[category] += 1
        assert row.severity == combined_for(faults, per_severity), f'{row.job_id}: combined severity mismatch'
        assert row.primary_fault == sorted(faults, key=lambda f: (LEVELS.index(per_severity[f]), float(per_cost[f])), reverse=True)[0]
        if len(faults) >= 2:
            required_discount = round((float(row.customer_charge) + float(row.discount)) * MULTI_FAULT_DISCOUNT_RATE)
            assert int(row.discount) == required_discount, f'{row.job_id}: multi-fault discount mismatch'
        severity_counts[row.severity] += 1
        facts = MODEL_FACTS[row.model]
        assert 1 <= int(row.age) <= 2026 - facts['launch_year'], f'{row.job_id}: model age outside launch-year range'
        annual_km = float(row.km_driven) / int(row.age)
        low, high = (3000, 12000) if row.vehicle_type == 'bike' else (5000, 18000)
        assert low <= annual_km <= high, f'{row.job_id}: implausible annual mileage {annual_km}'
        assert int(row.km_driven) <= (120000 if row.vehicle_type == 'bike' else 250000)
        assert abs(float(row.gross_margin) - (float(row.customer_charge) - float(row.parts_cost) - float(row.labour_cost))) < .02
        assert int(row.stockout_delay_days) >= 0
        if int(row.stockout_delay_days) > 0:
            assert row.job_id in stockout_jobs
    # Every offered catalogue model must be represented and no unoffered tuple may occur.
    offered = {(kind, brand, model) for kind, brands in VEHICLES.items() for brand, models in brands.items() for model in models}
    observed = set(zip(service.vehicle_type, service.brand, service.model))
    assert observed <= offered, f'Uncatalogued vehicle tuples: {sorted(observed - offered)[:3]}'
    missing = offered - observed
    assert not missing, f'Offered vehicles without service rows: {sorted(missing)[:6]}'
    # All 45 unordered fault pairs and all four declared dangerous pairs need coverage.
    from itertools import combinations
    pair_counts = Counter()
    for row in service.itertuples(index=False):
        faults = row.faults.split(';')
        for pair in combinations(sorted(faults), 2): pair_counts[pair] += 1
    expected_pairs = {tuple(sorted(pair)) for pair in combinations(CUES, 2)}
    assert expected_pairs <= set(pair_counts), f'Missing category pairs: {sorted(expected_pairs-set(pair_counts))}'
    assert all(pair_counts[pair] >= 25 for pair in expected_pairs), 'One or more category pairs below 25 rows'
    for pair in DANGEROUS:
        assert pair_counts[tuple(sorted(pair))] >= 60, f'Dangerous pair below 60 rows: {pair}'
    # Vehicle class compatibility rules catch impossible cooling and drivetrain mentions.
    incompatible = []
    for row in service.itertuples(index=False):
        text = row.symptoms.lower()
        facts = MODEL_FACTS[row.model]
        forbidden = []
        if not facts.get('has_chain', False): forbidden += ['chain', 'sprocket']
        if not facts.get('has_clutch_lever', False): forbidden += ['clutch lever']
        if not facts.get('has_radiator', False): forbidden += ['radiator', 'coolant']
        if row.vehicle_type == 'car': forbidden += ['riding']
        if row.vehicle_type == 'bike': forbidden += ['driving']
        if any(re.search(rf'\b{re.escape(term)}\b', text) for term in forbidden): incompatible.append(row.job_id)
    assert not incompatible, f'Incompatible vehicle symptom wording: {incompatible[:3]}'
    # Seasonality is measured against winter/early-year baselines.
    seasonal = service.assign(month=pd.to_datetime(service.service_date).dt.month)
    counts_by_month = seasonal.groupby('month').size()
    for category, months, baseline_months, ratio in [
        ('Cooling System', [4,5,6], [12,1], 1.4),
        ('Battery/Electrical', [12,1,2], [4,5,6], 1.1),
        ('Starting System', [12,1,2], [4,5,6], 1.1),
        ('Tyres/Wheels', [7,8,9], [1,2,3], 1.05),
    ]:
        cat = seasonal[seasonal.faults.str.contains(category, regex=False)]
        numerator = cat[cat.month.isin(months)].shape[0] / max(1, sum(counts_by_month[m] for m in months))
        denominator = cat[cat.month.isin(baseline_months)].shape[0] / max(1, sum(counts_by_month[m] for m in baseline_months))
        assert numerator >= denominator * ratio, f'{category} seasonal share too low: {numerator/denominator:.2f}x'
    assert set(fault_counts) == set(CUES)
    assert .25 <= fault_count_counts[2] / len(service) <= .30
    assert .03 <= fault_count_counts[3] / len(service) <= .05
    car_share = (service.vehicle_type == 'car').mean()
    assert .50 <= car_share <= .60, f'Car share outside target: {car_share:.3f}'
    label_total = sum(fault_counts.values())
    assert .18 <= fault_counts['General Maintenance'] / label_total <= .26
    assert .10 <= fault_counts['Tyres/Wheels'] / label_total <= .16
    assert .09 <= fault_counts['Brake System'] / label_total <= .15
    assert .09 <= fault_counts['Battery/Electrical'] / label_total <= .15
    for category in CUES:
        if category not in ('General Maintenance', 'Tyres/Wheels', 'Brake System', 'Battery/Electrical'):
            assert .04 <= fault_counts[category] / label_total <= .10, f'Fault mix outside target for {category}'

    service_monthly = service.assign(month=service.service_date.str[:7])
    service_monthly['gross_profit'] = pd.to_numeric(service_monthly.gross_margin).clip(lower=0)
    service_monthly['gross_loss'] = pd.to_numeric(service_monthly.gross_margin).clip(upper=0)
    aggregations = service_monthly.groupby('month').agg(
        jobs=('job_id', 'count'), revenue=('customer_charge', 'sum'), parts_cost=('parts_cost', 'sum'),
        labour_cost=('labour_cost', 'sum'), gross_profit=('gross_profit', 'sum'),
        gross_loss=('gross_loss', 'sum'), gross_margin=('gross_margin', 'sum'), discount=('discount', 'sum'),
        stockout_delay_days=('stockout_delay_days', 'sum'),
    ).reset_index()
    aggregations['rent_overhead'] = pd.to_numeric(monthly.rent_overhead).to_numpy()
    aggregations['salary_overhead'] = pd.to_numeric(monthly.salary_overhead).to_numpy()
    aggregations['utilities_overhead'] = pd.to_numeric(monthly.utilities_overhead).to_numpy()
    aggregations['total_overheads'] = aggregations[['rent_overhead','salary_overhead','utilities_overhead']].sum(axis=1)
    aggregations['net_profit'] = aggregations.gross_margin - aggregations.total_overheads
    aggregations['profit_loss'] = aggregations.net_profit
    assert list(monthly.month) == list(aggregations.month)
    for column in aggregations.columns:
        if column == 'month':
            continue
        left = pd.to_numeric(monthly[column]).to_numpy(dtype=float)
        right = pd.to_numeric(aggregations[column]).to_numpy(dtype=float)
        assert (abs(left - right) < .02).all(), f'Monthly totals mismatch: {column}'
    assert (pd.to_numeric(monthly.gross_profit) > 0).all()
    assert (pd.to_numeric(monthly.gross_loss) < 0).all()
    assert (pd.to_numeric(monthly.profit_loss) > 0).any() and (pd.to_numeric(monthly.profit_loss) < 0).any()
    assert (pd.to_numeric(monthly.net_profit) != pd.to_numeric(monthly.gross_margin)).all()
    losses = (pd.to_numeric(monthly.net_profit) < 0).sum()
    near_zero = (pd.to_numeric(monthly.net_profit).abs() < 10000).sum()
    loss_or_near = ((pd.to_numeric(monthly.net_profit) < 0) | (pd.to_numeric(monthly.net_profit).abs() < 10000)).sum()
    assert 3 <= loss_or_near <= 5, f'Expected 3-5 loss/near-zero months, got {loss_or_near}'

    print('PASS: service rows, dates, vehicle mileage, fault labels and severity rules')
    print('PASS: compatible parts, stock never negative, and inventory ledger reconciles to snapshot')
    print('PASS: monthly revenue, parts, labour, gross profit/loss and profit/loss reconcile')
    print(f"PASS: jobs={len(service)} stock_parts={len(stock)} ledger_events={len(ledger)} months={len(monthly)}")
    print(f'FAULT_COUNTS={dict(fault_counts)}')
    print(f'SEVERITY_COUNTS={dict(severity_counts)}')
    print(f'FAULT_COUNT_ROWS={dict(fault_count_counts)}')
    return service, stock, ledger, monthly


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--service-csv')
    validate(parser.parse_args().service_csv)


