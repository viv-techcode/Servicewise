"""Independently audit generated service, inventory, and finance CSVs."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.discount_rules import MULTI_FAULT_DISCOUNT_RATE
from backend.ml.severity import combined_severity, severity_for_fault, detect_red_flag_faults, _normalize

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
    'Battery/Electrical': ('battery', 'electrical', 'headlight', 'headlamp', 'horn', 'dashboard', 'charge'),
    'Brake System': ('brake',), 'Cooling System': ('coolant', 'radiator', 'overheating', 'temperature', 'cooling fin', 'garam', 'hotter', 'engine heat', 'hot', 'airflow'),
    'Engine': ('engine', 'engin', 'oil pressure', 'exhaust', 'misfire'), 'Fuel System': ('fuel', 'petrol', 'exhaust smoke'),
    'General Maintenance': ('oil', 'filter', 'service', 'maintenance', 'inspection', 'routine'),
    'Starting System': ('starter', 'start', 'ignition', 'crank'),
    'Suspension': ('shock', 'suspension', 'clunk', 'bounces', 'unstable', 'steering lock', 'steering has locked'),
    'Transmission': ('gear', 'clutch', 'belt', 'chain', 'transmission', 'drive system', 'variator', 'automatic', 'scooter drive'),
    'Tyres/Wheels': ('tyre', 'tire', 'wheel', 'puncture', 'pressure', 'pulls slightly'),
}
SERVICE_COLUMNS = [
    'job_id', 'service_date', 'service_time', 'vehicle_type', 'brand', 'model', 'age', 'km_driven',
    'symptoms', 'symptom_template_id', 'phrasing_family_id', 'is_ambiguous', 'ambiguity_categories',
    'primary_fault', 'faults', 'fault_count', 'per_fault_severity', 'severity', 'parts_used',
    'per_fault_cost', 'customer_charge', 'parts_cost', 'estimated_cost_min', 'estimated_cost_max', 'labour_cost', 'gross_margin', 'discount',
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


def validate(service_path=None, data_dir=None):
    root = Path(data_dir) if data_dir else ROOT
    service = pd.read_csv(service_path or root / 'service_records.csv', keep_default_na=False)
    stock = pd.read_csv(root / 'inventory_stock.csv', keep_default_na=False)
    ledger = pd.read_csv(root / 'inventory_log.csv', keep_default_na=False)
    monthly = pd.read_csv(root / 'monthly_summary.csv', keep_default_na=False)
    reference = pd.read_csv(root / 'north_india_repair_price_reference.csv', keep_default_na=False)
    price_book = pd.read_csv(root / 'part_price_table.csv', keep_default_na=False)
    assert list(service.columns) == SERVICE_COLUMNS, f'Service columns mismatch: {list(service.columns)}'
    assert len(service) == 7000, f'Unexpected job count: {len(service)} (expected 7000)'
    assert not service.job_id.duplicated().any()
    assert service.service_date.between('2025-01-01', '2026-10-31').all()
    assert service.job_id.tolist() == service.assign(_timestamp=pd.to_datetime(service.service_date + ' ' + service.service_time)).sort_values(['_timestamp','job_id']).job_id.tolist(), 'Job IDs not chronological'
    assert abs(float(service.parts_cost.sum())/max(1,float(service.customer_charge.sum())) - .55) <= .05, 'Total parts cost share must be 50%-60% of revenue'
    estimate_min = pd.to_numeric(service.estimated_cost_min)
    estimate_max = pd.to_numeric(service.estimated_cost_max)
    assert (estimate_min > 0).all() and (estimate_max >= estimate_min).all() and (estimate_max/estimate_min <= 1.5).all(), 'Invalid estimate range or max/min above 1.5x'
    ambiguity_mask = service.is_ambiguous.astype(str).str.lower().isin(['true','1','yes'])
    assert .08 <= ambiguity_mask.mean() <= .12, f'Ambiguity share outside 8%-12%: {ambiguity_mask.mean():.1%}'
    phrase_sets, family_sets = defaultdict(set), defaultdict(set)
    for row in service.itertuples(index=False):
        try:
            family_json = json.loads(row.phrasing_family_id)
            ambiguity_candidates = json.loads(row.ambiguity_categories)
        except Exception as exc:
            raise AssertionError(f'{row.job_id}: invalid phrase/ambiguity JSON') from exc
        for cat in row.faults.split(';'):
            phrase_sets[(cat,row.vehicle_type)].add(str(row.symptoms).strip().lower())
            family = family_json.get(cat, '')
            assert family, f'{row.job_id}: missing phrasing family for {cat}'
            family_sets[cat].add(family.split(':')[-2] if ':' in family else family)
        is_ambiguous = str(row.is_ambiguous).lower() in ('true','1','yes')
        if is_ambiguous:
            assert int(row.fault_count)==1 and row.primary_fault in ambiguity_candidates and len(ambiguity_candidates)>=2, f'{row.job_id}: invalid ambiguity set or true cause'
        else:
            assert not ambiguity_candidates, f'{row.job_id}: unmarked ambiguity candidates'
    for cat in CUES:
        for vtype in ('bike','car'):
            assert len(phrase_sets[(cat,vtype)])>=40, f'{cat}/{vtype}: fewer than 40 distinct symptom phrasings'
        assert len(family_sets[cat])>=4, f'{cat}: fewer than four phrasing families'
    seen_days = set(service.service_date)
    expected_days = {(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range((date(2026, 10, 31) - date(2025, 1, 1)).days + 1)}
    assert SERVICE_DATE_MIN <= min(seen_days) <= max(seen_days) <= SERVICE_DATE_MAX

    stock_by_id = stock.set_index('part_id').to_dict('index')
    assert len(stock_by_id) >= 60, f'Expected ~60 SKUs, got {len(stock_by_id)}'
    assert 55 <= len(price_book) <= 70, f'Expected approximately 60 priced SKUs, got {len(price_book)}'
    assert set(price_book.part_id) == set(stock.part_id), 'Explicit price book SKU set differs from inventory snapshot'
    assert (pd.to_numeric(price_book.unit_price) > 0).all() and (pd.to_numeric(price_book.unit_cost) > 0).all()
    assert price_book.price_basis.isin(['estimate','catalogue/official listing']).all(), 'Unmarked part price source/basis'
    for stock_row in stock.itertuples(index=False):
        priced = price_book[price_book.part_id.eq(stock_row.part_id)].iloc[0]
        assert int(priced.unit_cost) == int(stock_row.unit_cost) and int(priced.unit_price) == int(stock_row.unit_price), f'{stock_row.part_id}: price book/snapshot mismatch'
    estimate_ref = reference[reference.availability.eq('estimated') & reference.price_basis.str.startswith('typical-job estimate')]
    expected_pairs = {(cat, vtype) for cat in CUES for vtype in ('bike','car')}
    observed_pairs = set(zip(estimate_ref.fault_category, estimate_ref.vehicle_type))
    assert expected_pairs <= observed_pairs, f'Missing explicit reference bands: {sorted(expected_pairs-observed_pairs)}'
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
        ambiguous_row = str(row.is_ambiguous).lower() in ('true','1','yes')
        ambiguity_candidates = json.loads(row.ambiguity_categories)
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
            part_name = str(part['part_name']).lower()
            facts = MODEL_FACTS[row.model]
            if 'chain and sprocket' in part_name:
                assert facts['has_chain'], f'{row.job_id}: chain kit on non-chain model'
            if 'cvt' in part_name:
                assert facts['body'] == 'scooter', f'{row.job_id}: CVT part on geared vehicle'
            if any(term in part_name for term in ('radiator','coolant')):
                assert facts['has_radiator'], f'{row.job_id}: radiator/coolant part on air-cooled model'
            if row.model in ('Activa 6G', 'Jupiter 110'):
                name = str(part['part_name']).lower()
                assert 'clutch cable' not in name and 'handbrake cable' not in name
            assert (row.job_id, part_id) in sale_part_pairs, f'{row.job_id}: part issue missing from ledger'
        assert set(used_by_fault) == set(faults)
        assert all(1 <= used_by_fault[f] <= 3 for f in faults), f'{row.job_id}: expected 1-3 parts per fault: {used_by_fault}'
        for category in faults:
            if not ambiguous_row:
                normalized = _normalize(row.symptoms).lower()
                assert any(cue in normalized for cue in CUES[category]), f'{row.job_id}: {category} absent from symptoms'
            else:
                assert row.primary_fault in ambiguity_candidates and len(ambiguity_candidates)>=2
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
        assert float(row.estimated_cost_min)>0 and float(row.estimated_cost_max)>=float(row.estimated_cost_min)
        assert float(row.estimated_cost_max)/float(row.estimated_cost_min)<=1.5, f'{row.job_id}: estimate range exceeds 1.5x'
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
    expected_revenue_pct = pd.to_numeric(monthly.revenue).pct_change(fill_method=None) * 100
    expected_jobs_pct = pd.to_numeric(monthly.jobs).pct_change(fill_method=None) * 100
    for col, expected in [('mom_change_pct', expected_revenue_pct), ('revenue_mom_change_pct', expected_revenue_pct), ('jobs_mom_change_pct', expected_jobs_pct)]:
        actual = monthly[col].replace('', np.nan).astype(float)
        assert pd.isna(actual.iloc[0]), f'{col}: first month must have no change'
        assert (abs(actual.iloc[1:].to_numpy()-expected.iloc[1:].to_numpy()) < .02).all(), f'{col}: not recomputed from revenue/jobs'
    expected_trend = ['stable'] + ['growth' if x>=5 else ('dip' if x<=-5 else 'stable') for x in expected_revenue_pct.iloc[1:]]
    assert monthly.trend.tolist() == expected_trend, 'Trend label does not follow revenue +/-5% thresholds'
    assert (pd.to_numeric(monthly.gross_profit) > 0).all()
    assert (pd.to_numeric(monthly.gross_loss) < 0).all()
    assert (pd.to_numeric(monthly.profit_loss) > 0).any() and (pd.to_numeric(monthly.profit_loss) < 0).any()
    assert (pd.to_numeric(monthly.net_profit) != pd.to_numeric(monthly.gross_margin)).all()
    losses = (pd.to_numeric(monthly.net_profit) < 0).sum()
    near_zero = (pd.to_numeric(monthly.net_profit).abs() < 20000).sum()
    loss_or_near = ((pd.to_numeric(monthly.net_profit) < 0) | (pd.to_numeric(monthly.net_profit).abs() < 20000)).sum()
    assert 3 <= loss_or_near <= 4, f'Expected 3-4 loss/near-zero months, got {loss_or_near}'

    category_medians = service.groupby(['primary_fault','vehicle_type']).customer_charge.median().unstack()
    ratios = category_medians.bike / category_medians.car
    assert ratios.between(.30,.60).all(), f'Bike/car ratio out of 0.30-0.60: {ratios[~ratios.between(.30,.60)].round(3).to_dict()}'
    assert category_medians.index.tolist(), 'No category medians'
    # High and critical repairs must cost more than low repairs for the three
    # safety/thermal/fuel categories, on each vehicle class.
    per_severity_cost = []
    for row in service.itertuples(index=False):
        for cat, sev in json.loads(row.per_fault_severity).items():
            per_severity_cost.append((cat,row.vehicle_type,sev,float(json.loads(row.per_fault_cost)[cat])))
    severity_frame = pd.DataFrame(per_severity_cost,columns=['category','vehicle','severity','cost'])
    for cat in ('Brake System','Cooling System','Fuel System'):
        for vtype in ('bike','car'):
            meds=severity_frame[(severity_frame.category==cat)&(severity_frame.vehicle==vtype)].groupby('severity').cost.median()
            for sev in ('high','critical'):
                assert sev in meds and 'low' in meds and meds[sev]>meds['low'], f'{cat}/{vtype}: {sev} median must exceed low'
    headlight_jobs = service[(service.vehicle_type=='bike') & (service.fault_count==1) & service.faults.str.contains('Battery/Electrical',regex=False) & service.symptoms.str.contains(r'headlight|headlights|headlamp',case=False,regex=True) & service.symptoms.str.contains(r'dim|bulb',case=False,regex=True)]
    assert len(headlight_jobs)>0, 'No standalone bike dim-headlight/bulb sample to check'
    assert (pd.to_numeric(headlight_jobs.customer_charge)<600).all(), 'Bike dim-headlight/bulb job must be under ₹600'
    assert int((pd.to_numeric(stock.stock)<=pd.to_numeric(stock.reorder_level)).sum())>=2, 'Snapshot must include low/out-of-stock SKUs'
    assert (ledger.event_type=='stock_out').sum()>=1, 'Expected actual stock-out periods'
    for (cat,vtype), med in category_medians.stack().items():
        ref=estimate_ref[(estimate_ref.fault_category==cat)&(estimate_ref.vehicle_type==vtype)]
        assert len(ref)>=1, f'Missing reference data for {cat}/{vtype}'
        lo=pd.to_numeric(ref.price_min).median(); hi=pd.to_numeric(ref.price_max).median()
        assert .75*lo<=med<=1.25*hi, f'{cat}/{vtype}: median {med:.0f} outside reference range {lo:.0f}-{hi:.0f}'

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
    parser.add_argument('--data-dir')
    args = parser.parse_args()
    validate(args.service_csv, args.data_dir)


