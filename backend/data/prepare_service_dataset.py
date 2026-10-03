"""Rebuild the balanced ServiceWise example table from the retained source rows."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.ml.fault_text import (
    FAULT_SYMPTOMS, INFORMAL_NOISE_NOTES, SHARED_AMBIGUOUS_SYMPTOMS,
    add_fault_symptoms,
)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'sample_service_records.csv'
OUTPUT = ROOT / 'service_records_balanced_3000.csv'
REPORT = ROOT / 'service_records_validation_report.md'
NOISE_CONFIG = ROOT / 'dataset_noise_config.json'
TARGET_PER_CATEGORY = 300
CATEGORIES = list(FAULT_SYMPTOMS)
PARTS_SHARE = {
    'Battery/Electrical': .68, 'Brake System': .55, 'Cooling System': .62,
    'Engine': .58, 'Fuel System': .52, 'General Maintenance': .40,
    'Starting System': .70, 'Suspension': .65, 'Transmission': .66,
    'Tyres/Wheels': .72,
}
STATES = ['Delhi', 'Haryana', 'Himachal Pradesh', 'Jammu and Kashmir', 'Ladakh', 'Punjab', 'Rajasthan', 'Uttar Pradesh', 'Uttarakhand']
VEHICLES = {
    'car': [('Maruti Suzuki', 'Swift'), ('Tata', 'Tiago'), ('Hyundai', 'i20'), ('Mahindra', 'XUV300'), ('Toyota', 'Innova')],
    'bike': [('Hero', 'Splendor Plus'), ('Honda', 'Shine 125'), ('Bajaj', 'Pulsar 150'), ('TVS', 'Apache RTR'), ('Suzuki', 'Access 125')],
    'cycle': [('Firefox', 'Bad Attitude'), ('Hero', 'Sprint Pro'), ('Hercules', 'Roadeo'), ('Avon', 'Element'), ('BSA', 'SLR')],
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
MISLABEL_PAIRS = [
    ('Battery/Electrical', 'Starting System'),
    ('Engine', 'Fuel System'),
    ('Suspension', 'Tyres/Wheels'),
    ('Brake System', 'Suspension'),
    ('Cooling System', 'Engine'),
]


def main():
    config = json.loads(NOISE_CONFIG.read_text(encoding='utf-8-sig'))
    rates = config['active_rates']
    ambiguous_per_category = round(TARGET_PER_CATEGORY * rates['ambiguous_shared_symptoms'])
    informal_per_category = round(TARGET_PER_CATEGORY * rates['typos_abbreviations_hinglish'])
    mislabel_rows = round(TARGET_PER_CATEGORY * len(CATEGORIES) * rates['plausible_label_misdiagnoses'])
    swaps_per_side = round(mislabel_rows / (2 * len(MISLABEL_PAIRS)))
    ambiguous_ids = {category: [] for category in CATEGORIES}
    informal_ids = []
    original = pd.read_csv(SOURCE)
    rows = original.to_dict('records')
    for row in rows:
        row.update(primary_fault=row['problem_category'], simultaneous_faults='not_recorded', fault_costs=json.dumps({row['problem_category']: float(row['actual_repair_cost'])}), state='not_recorded', parts_cost=pd.NA, labour_cost=pd.NA, total_repair_cost=row['actual_repair_cost'], reference_price_min=pd.NA, reference_price_max=pd.NA, price_reference_url='')
    next_id = int(original.record_id.max()) + 1
    category_cost = original.groupby('problem_category')['actual_repair_cost'].median().to_dict()
    for category_index, category in enumerate(CATEGORIES):
        seeds = original[original.problem_category == category].to_dict('records')
        if not seeds:
            raise ValueError(f'Missing source examples for {category}')
        for j in range(TARGET_PER_CATEGORY - len(seeds)):
            base = seeds[j % len(seeds)]
            vehicle_type = ['car', 'bike', 'cycle'][(j + category_index) % 3]
            brand, model = VEHICLES[vehicle_type][(j * 3 + category_index) % len(VEHICLES[vehicle_type])]
            if j < 10:
                options = COMBINATIONS[category]
                secondary_categories = [options[j % 3], options[(j + 1) % 3]]
            elif j < 120:
                secondary_categories = [COMBINATIONS[category][j % 3]]
            else:
                secondary_categories = []
            secondary = ';'.join(secondary_categories) if secondary_categories else 'none'
            is_ambiguous = not secondary_categories and 120 <= j < 120 + ambiguous_per_category
            if is_ambiguous:
                primary_symptom = SHARED_AMBIGUOUS_SYMPTOMS[(next_id + category_index) % len(SHARED_AMBIGUOUS_SYMPTOMS)]
                ambiguous_ids[category].append(next_id)
            else:
                primary_symptom = FAULT_SYMPTOMS[category][(j + category_index * 3) % len(FAULT_SYMPTOMS[category])]
            symptom_text = add_fault_symptoms(primary_symptom, secondary_categories, next_id)
            if j < informal_per_category:
                symptom_text += ' ' + INFORMAL_NOISE_NOTES[(next_id + category_index) % len(INFORMAL_NOISE_NOTES)] + '.'
                informal_ids.append(next_id)
            scale = [0.78, 0.90, 1.00, 1.12, 1.25][j % 5]
            segment = {'cycle': .35, 'bike': .72, 'car': 1.0}[vehicle_type]
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
                'state': STATES[(j + category_index) % len(STATES)],
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
    # Paired swaps preserve the fixed primary-class counts. Select only vague
    # single-fault examples so each alternate diagnosis remains plausible.
    used_ids = set()
    for left, right in MISLABEL_PAIRS:
        left_ids = [rid for rid in ambiguous_ids[left] if rid not in used_ids][:swaps_per_side]
        right_ids = [rid for rid in ambiguous_ids[right] if rid not in used_ids][:swaps_per_side]
        if len(left_ids) != swaps_per_side or len(right_ids) != swaps_per_side:
            raise ValueError('Not enough ambiguous single-fault examples for paired diagnosis swaps.')
        left_indices = df.index[df.record_id.isin(left_ids)].tolist()
        right_indices = df.index[df.record_id.isin(right_ids)].tolist()
        df.loc[left_indices, ['primary_fault', 'problem_category']] = right
        df.loc[right_indices, ['primary_fault', 'problem_category']] = left
        used_ids.update(left_ids + right_ids)
    columns = list(original.columns) + EXTRA_COLUMNS
    df = df.loc[:, list(dict.fromkeys(columns))]
    df.to_csv(OUTPUT, index=False)
    check = pd.read_csv(OUTPUT)
    counts = check.primary_fault.value_counts().reindex(CATEGORIES, fill_value=0)
    split = check.parts_cost.notna() & check.labour_cost.notna()
    assert len(check) == 3000 and counts.eq(300).all()
    assert ((check.loc[split, 'parts_cost'] + check.loc[split, 'labour_cost']) == check.loc[split, 'actual_repair_cost']).all()
    fault_counts = check.simultaneous_faults.fillna('none').apply(lambda value: 1 + len([x for x in str(value).split(';') if x and x not in {'none', 'not_recorded'}]))
    assert int((fault_counts > 1).sum()) == 1200
    assert int((fault_counts == 3).sum()) == 100
    assert len(ambiguous_ids) == len(CATEGORIES)
    assert sum(map(len, ambiguous_ids.values())) == int(round(len(check) * rates['ambiguous_shared_symptoms']))
    assert len(informal_ids) == int(round(len(check) * rates['typos_abbreviations_hinglish']))
    assert len(used_ids) == mislabel_rows
    lines = ['# ServiceWise prepared dataset validation report', '', f'Table rows: {len(check)}.', '', '## Primary fault counts', '', '| Primary fault | Rows |', '|---|---:|']
    lines += [f'| {category} | {int(counts[category])} |' for category in CATEGORIES]
    template_counts = check.groupby('primary_fault').symptoms.nunique().reindex(CATEGORIES, fill_value=0)
    lines += ['', '## Text ambiguity and noise checks', '', f'- Ambiguous/shared descriptions: {len(ambiguous_ids) * ambiguous_per_category} ({len(ambiguous_ids) * ambiguous_per_category / len(check):.1%}) across multiple plausible categories.', f'- Typos, abbreviations, or Hinglish notes: {len(informal_ids)} ({len(informal_ids) / len(check):.1%}).', f'- Paired plausible diagnosis swaps: {len(used_ids)} ({len(used_ids) / len(check):.1%}); primary category totals remain balanced.', '- Unique symptom descriptions per primary fault: ' + ', '.join(f'{category} {int(template_counts[category])}' for category in CATEGORIES) + '.', '', '## Checks', '', f'- Null cells: {int(check.isna().sum().sum())}.', f'- Exact duplicate rows: {int(check.duplicated().sum())}.', f'- Duplicate record IDs: {int(check.record_id.duplicated().sum())}.', f'- Multi-fault rows: {int((fault_counts > 1).sum())} ({(fault_counts > 1).mean():.1%}); two-fault rows: {int((fault_counts == 2).sum())}; three-fault rows: {int((fault_counts == 3).sum())}.', f'- Parts/labour sum mismatches against primary-fault cost where both are present: {int(((check.loc[split, "parts_cost"] + check.loc[split, "labour_cost"]) != check.loc[split, "actual_repair_cost"]).sum())}.', '- Multi-fault combined totals follow the documented shared visit rule and are distinct from per-fault model targets.', '- The first 165 rows retain the source values, with the added fault and price-reference columns populated only where those values are applicable.', '', '## Files', '', f'- `{OUTPUT.name}`', f'- `{REPORT.name}`', f'- `{Path(__file__).name}`', f'- `{NOISE_CONFIG.name}`', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'rows': len(check), 'category_counts': counts.to_dict(), 'multi_fault_rows': int((~check.simultaneous_faults.isin(['none', 'not_recorded'])).sum()), 'ambiguous_rows': len(ambiguous_ids) * ambiguous_per_category, 'informal_rows': len(informal_ids), 'mislabelled_rows': len(used_ids)}, indent=2))


if __name__ == '__main__':
    main()
