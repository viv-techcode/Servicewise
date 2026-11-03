"""Read-only diagnostics for the workshop CSV snapshot."""
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import pandas as pd
from backend.vehicles import MODEL_FACTS
from backend.ml.severity import SEVERITY_RULE_TABLE

ROOT = Path(__file__).resolve().parent
SERVICE = pd.read_csv(ROOT / 'service_records.csv', keep_default_na=False)
STOCK = pd.read_csv(ROOT / 'inventory_stock.csv', keep_default_na=False)
LEDGER = pd.read_csv(ROOT / 'inventory_log.csv', keep_default_na=False)
issues = defaultdict(list)
pairs = defaultdict(int)

for _, row in SERVICE.iterrows():
    facts = MODEL_FACTS.get(row.model)
    if not facts:
        issues['catalogue'].append((row.job_id, row.model))
        continue
    max_age = 2026 - facts['launch_year']
    if int(row.age) > max_age:
        issues['age'].append((row.job_id, f'{row.model}: age {row.age} > {max_age}'))
    annual = float(row.km_driven) / max(1, int(row.age))
    low, high = (3000, 12000) if row.vehicle_type == 'bike' else (5000, 18000)
    cap = 120000 if row.vehicle_type == 'bike' else 250000
    if not low <= annual <= high or int(row.km_driven) > cap:
        issues['mileage'].append((row.job_id, f'{annual:.0f} km/year; total {row.km_driven}'))
    text = row.symptoms.lower()
    impossible = []
    if facts['body'] == 'scooter' and any(x in text for x in ('chain', 'clutch', 'gear')): impossible.append('scooter chain/clutch/gear')
    if row.vehicle_type == 'car' and 'riding' in text: impossible.append('car riding')
    if row.vehicle_type == 'bike' and 'driving' in text: impossible.append('bike driving')
    if facts['cooling'] == 'air' and any(x in text for x in ('coolant', 'radiator')): impossible.append('air-cooled coolant/radiator')
    if impossible: issues['symptom_vehicle'].append((row.job_id, ', '.join(impossible)))
    faults = row.faults.split(';')
    severities = json.loads(row.per_fault_severity)
    rank = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    if faults and severities and row.primary_fault != max(faults, key=lambda f: rank.get(severities.get(f, 'low'), 0)):
        issues['primary_fault'].append((row.job_id, f'{row.primary_fault}; {severities}'))
    for pair in combinations(sorted(set(faults)), 2): pairs[pair] += 1

print(f'rows={len(SERVICE)} parts={len(STOCK)} ledger={len(LEDGER)}')
for key in ('age', 'mileage', 'symptom_vehicle', 'primary_fault'):
    rows = issues[key]
    print(f'{key}: {len(rows)} violations; examples={rows[:3]}')
faults = sorted(set(SERVICE.faults.str.split(';').explode()))
all_pairs = list(combinations(faults, 2))
print(f'pair_coverage: {sum(pairs[p] > 0 for p in all_pairs)}/{len(all_pairs)}; missing={[p for p in all_pairs if not pairs[p]]}')
print('severity_distribution:', SERVICE.severity.value_counts().to_dict())
print('distinct_symptoms_by_primary_fault:', SERVICE.groupby('primary_fault').symptoms.nunique().to_dict())
chronological = SERVICE.sort_values(['service_date', 'service_time', 'job_id']).job_id.tolist()
print('id_order_matches_time:', SERVICE.job_id.tolist() == chronological)
print('opening_below_reorder:', int((pd.to_numeric(STOCK.opening_stock) < pd.to_numeric(STOCK.reorder_level)).sum()), 'negative_snapshot:', int((pd.to_numeric(STOCK.stock) < 0).sum()))

# Remaining baseline dimensions are summarized compactly for triage.
print('severity_by_primary_fault:', SERVICE.groupby(['primary_fault', 'severity']).size().unstack(fill_value=0).to_dict('index'))
print('distinct_symptoms_by_category_severity:', SERVICE.groupby(['primary_fault', 'severity']).symptoms.nunique().to_dict())
vague = SERVICE.symptoms.str.contains(r'\b(gaadi|nahi|problem|issue|not working|noise)\b|\.{3}', case=False, regex=True)
print('vague_or_hinglish_share:', round(float(vague.mean()), 4))
same_type_price_shares = []
part_map = STOCK.set_index('part_id')
equal_parts = 0
for _, row in SERVICE.iterrows():
    ids = json.loads(row.parts_used)
    types = [part_map.loc[pid].vehicle_type for pid in ids]
    costs = [float(part_map.loc[pid].unit_price) for pid in ids]
    # Compare equivalent fault/category part prices across vehicle classes.
    for fault, cost, vtype in zip(row.faults.split(';'), costs, types):
        match = STOCK[(STOCK.fault_category == fault) & (STOCK.vehicle_type != vtype)]
        if len(match) and cost in set(pd.to_numeric(match.unit_price)):
            equal_parts += 1
print('bike_car_identical_part_price_occurrences:', equal_parts)
print('monthly_severity_fault_counts:', SERVICE.assign(month=SERVICE.service_date.str.slice(0,7)).groupby(['month','primary_fault']).size().to_dict())
print('weekend_jobs:', int(pd.to_datetime(SERVICE.service_date).dt.dayofweek.ge(5).sum()), 'sunday_jobs:', int(pd.to_datetime(SERVICE.service_date).dt.dayofweek.eq(6).sum()))
print('discount_rows_not_10pct_multi:', int((SERVICE.fault_count.gt(1) & SERVICE.discount.gt(0) & (SERVICE.discount / (SERVICE.customer_charge + SERVICE.discount) - .10).abs().gt(.015)).sum()), '(predictor rule: no shared rule found in generator contract)')
print('per_fault_severity_rule_mismatches:', sum(1 for _,r in SERVICE.iterrows() for f,s in json.loads(r.per_fault_severity).items() if s not in SEVERITY_RULE_TABLE['levels']))
ledger_running = defaultdict(int)
ledger_mismatch = 0
for row in LEDGER.sort_values(['event_date','event_time','event_id']).itertuples():
    ledger_running[row.part_id] += int(row.quantity_change)
    ledger_mismatch += int(ledger_running[row.part_id] != int(row.stock_after))
print('ledger_running_balance_mismatches:', ledger_mismatch)
