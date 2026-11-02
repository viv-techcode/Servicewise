"""Rebuild the balanced ServiceWise example table from the retained source rows."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))
from backend.ml.fault_text import FAULT_SYMPTOMS
from backend.vehicles import VEHICLES

SOURCE = ROOT / 'sample_service_records.csv'
OUTPUT = ROOT / 'service_records_balanced_3000.csv'
REPORT = ROOT / 'service_records_validation_report.md'
TARGET_PER_CATEGORY = 300
CATEGORIES = list(FAULT_SYMPTOMS)
PARTS_SHARE = {
    'Battery/Electrical': .68, 'Brake System': .55, 'Cooling System': .62,
    'Engine': .58, 'Fuel System': .52, 'General Maintenance': .40,
    'Starting System': .70, 'Suspension': .65, 'Transmission': .66,
    'Tyres/Wheels': .72,
}
COMMON_PROBLEMS = {
    'Battery/Electrical': ('Battery drains overnight.', 'Headlights dim or flicker.', 'Horn or electrical parts stop working.', 'Battery needs frequent jump starts.', 'Dashboard lights flicker.', 'Battery warning light stays on.', 'Electrical power is weak.', 'Lights become dim at idle.'),
    'Brake System': ('Brakes squeal when stopping.', 'Brake pedal feels soft.', 'Vehicle takes longer to stop.', 'Brakes grind during use.', 'Parking brake does not hold.', 'Vehicle pulls to one side while braking.', 'Brake pedal sinks too far.', 'Brakes feel weak.'),
    'Cooling System': ('Engine overheats in traffic.', 'Coolant leaks under the vehicle.', 'Radiator fan does not start.', 'Temperature rises quickly.', 'Steam comes from the engine bay.', 'Coolant level keeps dropping.', 'Engine runs hot after a short drive.', 'Coolant warning light comes on.'),
    'Engine': ('Engine runs rough or misfires.', 'Engine loses power while driving.', 'Engine makes a knocking noise.', 'Exhaust smoke has increased.', 'Engine stalls at stops.', 'Engine hesitates during acceleration.', 'Engine uses too much oil.', 'Engine warning light stays on.'),
    'Fuel System': ('Fuel mileage has dropped.', 'There is a strong petrol smell.', 'Engine struggles during acceleration.', 'Fuel appears to be leaking.', 'Engine uses more fuel than usual.', 'Engine loses power under load.', 'Black smoke comes from the exhaust.', 'Fuel delivery seems uneven.'),
    'General Maintenance': ('Routine service is due.', 'Engine oil and filter need changing.', 'Vehicle needs a general inspection.', 'Scheduled maintenance is overdue.', 'Air filter needs cleaning or replacement.', 'Vehicle is due for an oil change.', 'Fluids and filters need checking.', 'A routine safety check is needed.'),
    'Starting System': ('Vehicle clicks but will not start.', 'Engine cranks slowly.', 'Starter does not turn the engine.', 'Vehicle starts only after several tries.', 'Starter makes a grinding noise.', 'Engine struggles to start when cold.', 'Ignition switch works intermittently.', 'Vehicle needs repeated attempts to start.'),
    'Suspension': ('Vehicle bounces over bumps.', 'There is a clunk over potholes.', 'A shock absorber makes noise.', 'Vehicle feels unstable on rough roads.', 'Suspension bottoms out over bumps.', 'Vehicle leans to one side.', 'Front end knocks while driving.', 'Ride feels unusually rough.'),
    'Transmission': ('Gears are hard to change.', 'Gears grind while shifting.', 'Clutch slips during acceleration.', 'Vehicle vibrates when pulling away.', 'Gear changes feel rough.', 'Clutch pedal feels unusually stiff.', 'Transmission makes a rattling noise.', 'Vehicle struggles to select a gear.'),
    'Tyres/Wheels': ('Tyre pressure keeps dropping.', 'Vehicle pulls to one side.', 'Tyres are wearing unevenly.', 'Steering wheel vibrates at speed.', 'A tyre has a bulge after a pothole.', 'Wheel makes a repeated noise.', 'Vehicle shakes while driving.', 'Tyre loses air between trips.'),
}
COMBINATIONS = {
    'Battery/Electrical': ['Starting System', 'General Maintenance', 'Engine'],
    'Brake System': ['Suspension', 'Tyres/Wheels', 'General Maintenance'],
    'Cooling System': ['Engine', 'Battery/Electrical', 'General Maintenance'],
    'Engine': ['Fuel System', 'Cooling System', 'Battery/Electrical'],
    'Fuel System': ['Engine', 'Battery/Electrical', 'General Maintenance'],
    'General Maintenance': ['Tyres/Wheels', 'Brake System', 'Battery/Electrical'],
    'Starting System': ['Battery/Electrical', 'Engine', 'Fuel System'],
    'Suspension': ['Tyres/Wheels', 'Brake System', 'General Maintenance'],
    'Transmission': ['Engine', 'Tyres/Wheels', 'General Maintenance'],
    'Tyres/Wheels': ['Suspension', 'Brake System', 'General Maintenance'],
}
EXTRA_COLUMNS = ['primary_fault', 'simultaneous_faults', 'fault_costs', 'state', 'parts_cost', 'labour_cost', 'total_repair_cost', 'reference_price_min', 'reference_price_max', 'price_reference_url']
def main():
    original = pd.read_csv(SOURCE)
    allowed = {(kind, brand, model) for kind, brands in VEHICLES.items() for brand, models in brands.items() for model in models}
    original = original[original.apply(lambda row: (row.vehicle_type, row.vehicle_brand, row.vehicle_model) in allowed, axis=1)].copy()
    if original.empty:
        raise ValueError('No source records match the active vehicle catalog.')
    rows = original.to_dict('records')
    for row in rows:
        category = row['problem_category']
        row.update(symptoms=COMMON_PROBLEMS[category][int(row['record_id']) % 8], primary_fault=category, simultaneous_faults='not_recorded', fault_costs=json.dumps({category: float(row['actual_repair_cost'])}), state='Global', parts_cost=pd.NA, labour_cost=pd.NA, total_repair_cost=row['actual_repair_cost'], reference_price_min=pd.NA, reference_price_max=pd.NA, price_reference_url='')
    next_id = int(original.record_id.max()) + 1
    category_cost = original.groupby('problem_category')['actual_repair_cost'].median().to_dict()
    for category_index, category in enumerate(CATEGORIES):
        seeds = original[original.problem_category == category].to_dict('records')
        if not seeds:
            raise ValueError(f'Missing source examples for {category}')
        for j in range(TARGET_PER_CATEGORY - len(seeds)):
            base = seeds[j % len(seeds)]
            vehicle_type = ['car', 'bike'][(j + category_index) % 2]
            vehicles = [(brand, model) for brand, models in VEHICLES[vehicle_type].items() for model in models]
            brand, model = vehicles[(j * 3 + category_index) % len(vehicles)]
            if j < 10:
                options = COMBINATIONS[category]
                secondary_categories = [options[j % 3], options[(j + 1) % 3]]
            elif j < 120:
                secondary_categories = [COMBINATIONS[category][j % 3]]
            else:
                secondary_categories = []
            secondary = ';'.join(secondary_categories) if secondary_categories else 'none'
            symptom_text = COMMON_PROBLEMS[category][j % len(COMMON_PROBLEMS[category])]
            for offset, secondary_category in enumerate(secondary_categories):
                symptom_text += ' ' + COMMON_PROBLEMS[secondary_category][(j + offset + category_index) % len(COMMON_PROBLEMS[secondary_category])]
            scale = [0.78, 0.90, 1.00, 1.12, 1.25][j % 5]
            segment = {'bike': .72, 'car': 1.0}[vehicle_type]
            target_categories = [category, *secondary_categories]
            fault_cost_map = {
                fault: max(50, int(round(float(category_cost[fault]) * scale * segment / 10) * 10))
                for fault in target_categories
            }
            primary_cost = fault_cost_map[category]
            combined_total = int(round(sum(fault_cost_map.values()) * (0.9 if len(fault_cost_map) > 1 else 1.0)))
            parts = int(round(primary_cost * PARTS_SHARE[category] / 10) * 10)
            row = {
                **base,
                'record_id': next_id,
                'vehicle_type': vehicle_type,
                'vehicle_brand': brand,
                'vehicle_model': model,
                'vehicle_age': 1 + ((j * 7 + category_index) % 15),
                'km_driven': int((j * 7919 + (category_index + 1) * 2300) % (240000 if vehicle_type == 'car' else 90000 if vehicle_type == 'bike' else 9000)),
                'last_service_date': f'{1 + j % 12} months ago',
                'previous_repair_history': base['previous_repair_history'] if j % 3 else 'no related repair reported',
                'symptoms': symptom_text,
                'engine_warning_indicator': 'yes' if category in {'Engine', 'Cooling System', 'Starting System'} and j % 3 == 0 else 'no',
                'recent_maintenance': ['oil change', 'brake tune', 'none', 'filters', 'greasing'][j % 5],
                'actual_repair_cost': primary_cost,
                'service_date': f'2026-{1 + j % 9:02d}-{1 + j % 28:02d}',
                'primary_fault': category,
                'simultaneous_faults': secondary,
                'fault_costs': json.dumps(fault_cost_map, ensure_ascii=False, sort_keys=True),
                'state': 'Global',
                'parts_cost': parts,
                'labour_cost': primary_cost - parts,
                'total_repair_cost': combined_total,
                'reference_price_min': pd.NA,
                'reference_price_max': pd.NA,
                'price_reference_url': '',
            }
            rows.append(row)
            next_id += 1
    df = pd.DataFrame(rows)
    df['problem_category'] = df['primary_fault']
    columns = list(original.columns) + EXTRA_COLUMNS
    df = df.loc[:, list(dict.fromkeys(columns))]
    df.to_csv(OUTPUT, index=False)
    check = pd.read_csv(OUTPUT)
    counts = check.primary_fault.value_counts().reindex(CATEGORIES, fill_value=0)
    split = check.parts_cost.notna() & check.labour_cost.notna()
    assert len(check) == 3000 and counts.eq(300).all()
    assert set(check.state) == {'Global'}
    assert all((row.vehicle_type, row.vehicle_brand, row.vehicle_model) in allowed for row in check.itertuples())
    assert ((check.loc[split, 'parts_cost'] + check.loc[split, 'labour_cost']) == check.loc[split, 'actual_repair_cost']).all()
    fault_counts = check.simultaneous_faults.fillna('none').apply(lambda value: 1 + len([x for x in str(value).split(';') if x and x not in {'none', 'not_recorded'}]))
    lines = ['# ServiceWise prepared dataset validation report', '', f'Table rows: {len(check)}.', '', '## Primary fault counts', '', '| Primary fault | Rows |', '|---|---:|']
    lines += [f'| {category} | {int(counts[category])} |' for category in CATEGORIES]
    template_counts = check.groupby('primary_fault').symptoms.nunique().reindex(CATEGORIES, fill_value=0)
    lines += ['', '## Checks', '', f'- Null cells: {int(check.isna().sum().sum())}.', f'- Exact duplicate rows: {int(check.duplicated().sum())}.', f'- Duplicate record IDs: {int(check.record_id.duplicated().sum())}.', f'- Multi-fault rows: {int((fault_counts > 1).sum())}.', f'- Parts/labour sum mismatches: {int(((check.loc[split, "parts_cost"] + check.loc[split, "labour_cost"]) != check.loc[split, "actual_repair_cost"]).sum())}.', '- All region values are Global; all vehicles match the active catalog.', '', '## Files', '', f'- `{OUTPUT.name}`', f'- `{REPORT.name}`', f'- `{Path(__file__).name}`', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'rows': len(check), 'category_counts': counts.to_dict(), 'multi_fault_rows': int((~check.simultaneous_faults.isin(['none', 'not_recorded'])).sum())}, indent=2))


if __name__ == '__main__':
    main()
