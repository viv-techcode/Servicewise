"""Create deterministic, internally consistent workshop operations data."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.ml.severity import SEVERITY_RULE_TABLE, combined_severity, severity_for_fault
from backend.discount_rules import MULTI_FAULT_DISCOUNT_RATE

SEASONAL = {
    1: 0.88, 2: 0.86, 3: 0.91, 4: 1.00, 5: 1.10, 6: 1.17,
    7: 1.14, 8: 1.10, 9: 1.00, 10: 1.22, 11: 1.16, 12: 0.92,
}
SEASONAL_FAULT = {
    'Battery/Electrical': {12: 2.0, 1: 2.1, 2: 1.9, 7: 1.2, 8: 1.15},
    'Starting System': {12: 3.0, 1: 3.2, 2: 2.8},
    'Cooling System': {1: .55, 2: .60, 3: .75, 4: 3.2, 5: 4.8, 6: 4.5},
    'Tyres/Wheels': {6: 1.25, 7: 1.55, 8: 1.5, 9: 1.25},
    'Brake System': {6: 1.2, 7: 1.35, 8: 1.3, 9: 1.15},
}
SHOCK_DAYS = {
    date(2025, 6, 12): 2.5, date(2026, 7, 15): 2.25,
}
QUIET_WEEKS = [(date(2025, 2, 3), date(2025, 2, 9)), (date(2026, 6, 8), date(2026, 6, 14))]
STABLE_STRETCHES = [(date(2025, 4, 1), date(2025, 5, 15)), (date(2026, 1, 10), date(2026, 2, 25))]


ROOT = Path(__file__).resolve().parent
SEED = 20261102
START = date(2025, 1, 1)
END = date(2026, 10, 31)

CATEGORIES = [
    'Battery/Electrical', 'Brake System', 'Cooling System', 'Engine', 'Fuel System',
    'General Maintenance', 'Starting System', 'Suspension', 'Transmission', 'Tyres/Wheels',
]
PRICE_FACTORS = {
    'Brake System': {'bike': .135, 'car': .73},
    'Cooling System': {'bike': .51, 'car': .42},
    'Fuel System': {'bike': .26, 'car': .24},
    'Transmission': {'bike': .275, 'car': .220},
}
FAULT_WEIGHTS = {
    'General Maintenance': .30, 'Tyres/Wheels': .13, 'Brake System': .12,
    'Battery/Electrical': .12, 'Cooling System': .07, 'Engine': .07,
    'Fuel System': .071, 'Starting System': .071, 'Suspension': .068,
    'Transmission': .068,
}
FAULT_PHRASES = {
    'Battery/Electrical': [
        'Battery warning light stays on and the charge drops overnight.',
        'Headlights dim at idle after the recent rain.',
        'Battery drains overnight and the starter cranks slowly.',
        'Electrical power cuts out while riding over bumps.',
        'The horn and dashboard lights flicker intermittently.',
        'A weak battery needs a jump start every few days.',
    ],
    'Brake System': [
        'Brakes squeal at low speed but still stop normally.',
        'Brake pedal feels soft and stopping distance is longer.',
        'Brake failure on the first press needs immediate inspection.',
        'Rear brake feels weak and pulls to one side in wet weather.',
        'Brake fluid is low and the pedal sinks toward the floor.',
        'The front brake grinds when applied firmly.',
    ],
    'Cooling System': [
        'Coolant level slowly drops between workshop visits.',
        'Engine temperature rises in traffic on warm afternoons.',
        'Engine is overheating rapidly and steam is visible.',
        'Radiator fan does not start when the temperature climbs.',
        'Coolant warning appears after a long uphill drive.',
        'A small coolant puddle forms below the radiator hose.',
    ],
    'Engine': [
        'Engine makes a light knock during a cold start.',
        'Engine stalls at signals and hesitates under acceleration.',
        'Oil pressure warning appears with a loud engine knock.',
        'Engine misfires and loses power while climbing.',
        'Exhaust smoke increased and oil use is higher than usual.',
        'Engine runs rough after sitting in heavy traffic.',
    ],
    'Fuel System': [
        'Fuel economy has dropped over the last few weeks.',
        'A strong petrol smell comes from around the fuel tank.',
        'Fuel is leaking heavily at the hose joint.',
        'Engine hesitates as if fuel delivery is restricted.',
        'Fuel line looks damp and the mileage has fallen.',
        'Black exhaust smoke appears during hard acceleration.',
    ],
    'General Maintenance': [
        'Engine oil and filter are due for their scheduled change.',
        'Air filter is dusty and routine service is overdue.',
        'Owner requests a periodic inspection before a long trip.',
        'Brake fluid and service filters need their routine check.',
        'Scheduled maintenance is due after the latest service interval.',
        'The vehicle needs a general inspection and lubrication service.',
    ],
    'Starting System': [
        'Starter cranks slowly on cold mornings.',
        'Bike does not start after several repeated attempts.',
        'Starter clicks but the engine will not turn over.',
        'Ignition switch works only after a few tries.',
        'Engine struggles to start after the vehicle has been parked.',
        'Starter relay clicks intermittently when the key is turned.',
    ],
    'Suspension': [
        'Shock absorber squeaks when crossing speed breakers.',
        'Front end clunks over potholes and rough road patches.',
        'Vehicle bounces several times after a road bump.',
        'Steering feels unstable on uneven roads.',
        'Rear suspension bottoms out with a passenger onboard.',
        'A suspension knock is heard during slow turns.',
    ],
    'Transmission': [
        'Gears feel stiff when shifting in slow traffic.',
        'Clutch slips under load while accelerating uphill.',
        'Drive belt shudders when the scooter pulls away.',
        'Gear changes grind when selecting a lower gear.',
        'Chain rattles under load and needs adjustment.',
        'Transmission vibrates when pulling away from a stop.',
    ],
    'Tyres/Wheels': [
        'Tyre pressure drops slowly between rides.',
        'Wheel vibrates at speed and the tyre tread is wearing unevenly.',
        'Tyre has a sidewall bulge after hitting a pothole.',
        'Vehicle pulls slightly to one side on a straight road.',
        'A slow puncture leaves the tyre soft by morning.',
        'Wheel bearing noise rises as road speed increases.',
    ],
}


def part_catalog():
    rows = []
    bases = {
        'Battery/Electrical': (450, 1100, 6, 'Battery, bulb and terminal kit'),
        'Brake System': (120, 900, 4, 'Brake pad and shoe kit'),
        'Cooling System': (150, 800, 4, 'Cooling hose, coolant and fin-clean kit'),
        'Engine': (300, 1800, 6, 'Engine gasket, plug and sensor kit'),
        'Fuel System': (120, 750, 5, 'Fuel filter and hose kit'),
        'General Maintenance': (180, 850, 5, 'Oil, air filter and service kit'),
        'Starting System': (150, 700, 4, 'Starter relay and spark plug kit'),
        'Suspension': (300, 1600, 5, 'Shock absorber and bush kit'),
        'Transmission': (250, 1800, 5, 'Transmission service kit'),
        'Tyres/Wheels': (250, 2200, 5, 'Tyre, tube and valve kit'),
    }
    for category in CATEGORIES:
        low, high, lead, name = bases[category]
        for vtype in ('bike', 'car'):
            models = [m for brand, ms in VEHICLES[vtype].items() for m in ms]
            groups = [models]
            if category == 'Transmission' and vtype == 'bike':
                groups = [[m for m in models if MODEL_FACTS[m]['body'] == body] for body in ('geared_bike', 'scooter')]
            for group in filter(None, groups):
                for tier, factor in (('budget', .78), ('standard', 1.0), ('premium', 1.32)):
                    vehicle_factor = 1.0 if vtype == 'bike' else 2.0
                    model_factor = sum(1.18 if MODEL_FACTS[m]['price_tier'] == 'mid' else .92 for m in group) / len(group)
                    class_price_factor = PRICE_FACTORS.get(category, {}).get(vtype, 1.0)
                    cost = int(round(((low + high) / 2) * vehicle_factor * model_factor * factor * class_price_factor / 10) * 10)
                    retail = int(round(cost * 1.28 / 10) * 10)
                    label = name
                    if category == 'Transmission' and vtype == 'bike':
                        label = 'CVT belt and variator kit' if MODEL_FACTS[group[0]]['body'] == 'scooter' else 'Clutch plate and chain kit'
                    if category == 'Cooling System' and vtype == 'bike': label = 'Cooling fin and airflow service kit'
                    reorder = 8 if tier == 'budget' else 5
                    rows.append({'part_id': f'P-{vtype[0].upper()}-{len(rows)+1:03d}', 'part_name': f'{tier.title()} {label}',
                        'fault_category': category, 'vehicle_type': vtype, 'compatible_models': json.dumps(group),
                        'opening_stock': reorder + 4, 'stock': reorder + 4, 'reorder_level': reorder,
                        'unit_cost': cost, 'unit_price': retail, 'supplier_lead_time_days': lead,
                        'supplier': f'{category.split()[0]} Supply Co.'})
    return rows


def day_factor(day: date) -> float:
    month_index = (day.year - START.year) * 12 + day.month - START.month
    weekday_factor = 1.14 if day.weekday() < 5 else .66
    if any(start <= day <= end for start, end in QUIET_WEEKS):
        quiet = .42
    else:
        quiet = 1.0
    if any(start <= day <= end for start, end in STABLE_STRETCHES):
        trend = 1 + month_index * .007
        seasonal = 1.0
    else:
        trend = 1 + month_index * .009
        seasonal = SEASONAL[day.month]
    shock = SHOCK_DAYS.get(day, 1.0)
    if day.month in (10, 11):
        seasonal *= 1.12  # festival service demand
    return 7.2 * trend * weekday_factor * seasonal * quiet * shock


def seasonal_fault_weights(day: date):
    weights = dict(FAULT_WEIGHTS)
    for category, month_multipliers in SEASONAL_FAULT.items():
        weights[category] *= month_multipliers.get(day.month, 1.0)
    total = sum(weights.values())
    return [weights[category] / total for category in CATEGORIES]


def make_job_faults(count, day, rng, multi_number):
    if count >= 2:
        all_pairs = list(combinations(CATEGORIES, 2))
        dangerous_pairs = [('Brake System','Tyres/Wheels'),('Brake System','Suspension'),('Cooling System','Engine'),('Fuel System','Engine')]
        if multi_number <= 240:
            chosen = list(dangerous_pairs[(multi_number - 1) % len(dangerous_pairs)])
        else:
            ordinary = [pair for pair in all_pairs if pair not in dangerous_pairs and tuple(reversed(pair)) not in dangerous_pairs]
            chosen = list(ordinary[(multi_number - 241) % len(ordinary)])
        if count == 3:
            remaining = [category for category in CATEGORIES if category not in chosen]
            weights = np.asarray(seasonal_fault_weights(day))
            extra_weights = np.asarray([weights[CATEGORIES.index(category)] for category in remaining])
            chosen.append(str(rng.choice(remaining, p=extra_weights / extra_weights.sum())))
        return chosen
    weights = np.asarray(seasonal_fault_weights(day), dtype=float)
    chosen = [str(rng.choice(CATEGORIES, p=weights))]
    while len(chosen) < count:
        candidates = [category for category in CATEGORIES if category not in chosen]
        probabilities = np.asarray([weights[CATEGORIES.index(category)] for category in candidates])
        probabilities /= probabilities.sum()
        chosen.append(str(rng.choice(candidates, p=probabilities)))
    return chosen


def choose_vehicle(rng):
    vtype = str(rng.choice(['car', 'bike'], p=[.55, .45]))
    choices = [(brand, model) for brand, models in VEHICLES[vtype].items() for model in models]
    brand, model = choices[int(rng.integers(0, len(choices)))]
    age_cap = 120000 if vtype == 'bike' else 250000
    age = int(rng.integers(1, min(18, 2026 - MODEL_FACTS[model]['launch_year'], age_cap // (12000 if vtype == 'bike' else 18000)) + 1))
    annual = float(rng.uniform(3000, 12000) if vtype == 'bike' else rng.uniform(5000, 18000))
    km = int(round(age * annual / 100) * 100)
    return vtype, brand, model, age, km


def phrase_for(category, day, rng, vtype, model):
    phrase_index = int(rng.integers(0, len(FAULT_PHRASES[category])))
    phrase = str(FAULT_PHRASES[category][phrase_index])
    facts = MODEL_FACTS[model]
    if vtype == 'car':
        phrase = phrase.replace('riding', 'driving').replace('Bike does not start', 'Car does not start')
    else:
        phrase = phrase.replace('driving', 'riding').replace('Brake pedal', 'Brake lever')
    if facts['body'] == 'scooter' and category == 'Transmission':
        phrase = str(rng.choice([
            'The CVT drive belt shudders as the scooter pulls away.',
            'The scooter hesitates when its automatic transmission engages.',
            'A rattling sound comes from the scooter transmission at low speed.',
            'The CVT belt slips briefly under acceleration.',
            'The scooter drive feels jerky when moving off from a stop.',
            'The variator vibrates during slow takeoff.',
            'The automatic drive belt makes a brief squeal under load.',
            'The scooter transmission feels rough on uphill starts.',
        ]))
    elif category == 'Transmission' and vtype == 'car':
        phrase = str(rng.choice([
            'Gear changes feel stiff in slow traffic.', 'The manual clutch slips under load on an uphill road.',
            'The transmission shifts roughly after the car warms up.', 'A grinding sound occurs while selecting a lower gear.',
            'The gearbox hesitates between shifts.', 'The clutch pedal feels unusually heavy.',
            'An automatic shift feels delayed when pulling away.', 'A transmission vibration appears at steady road speed.',
        ]))
    if facts['cooling'] == 'air' and category == 'Cooling System':
        phrase = str(rng.choice([
            'Engine heat rises in slow traffic and the cooling fins need inspection.',
            'The engine runs hotter than usual on a long ride.', 'Airflow around the engine feels restricted after dusty roads.',
            'The temperature warning appears during a slow uphill ride.', 'Cooling fins are clogged with dust and debris.',
            'Engine heat builds up at idle and eases while moving.', 'The engine feels unusually hot after a short trip.',
            'A fan noise is absent while the engine is hot.',
        ]))
    elif category == 'Cooling System' and vtype == 'car':
        phrase = phrase.replace('riding', 'driving')
    # Natural openings and sentence endings provide independent phrasings;
    # template IDs preserve a leakage-safe split key.
    openings = ['', 'Lately, ', 'During the last few trips, ', 'At normal road speed, ', 'After the morning start, ', 'In stop-and-go traffic, ', 'On the recent commute, ', 'Over the past week, ']
    endings = ['', ' The issue is intermittent.', ' It is more noticeable under load.', ' It happens on most trips.', ' The owner noticed it this week.', ' The symptom is getting more frequent.', ' No repair has been attempted yet.', ' It remains after restarting the vehicle.']
    opening_index = int(rng.integers(0,len(openings))); ending_index = int(rng.integers(0,len(endings)))
    if opening_index:
        phrase = phrase[0].lower() + phrase[1:]
    phrase = openings[opening_index] + phrase + endings[ending_index]
    if day.month in (6, 7, 8, 9) and category in ('Tyres/Wheels', 'Brake System', 'Battery/Electrical'):
        phrase += ' Water spray has made the issue more noticeable.'
    if day.month in (4, 5, 6) and category == 'Cooling System':
        phrase += ' It happens most often in afternoon traffic.'
    is_hinglish = rng.random() < .08
    if is_hinglish:
        phrase = {
            'Brake System': 'brake nahi lag raha, stopping feels weak.',
            'Battery/Electrical': 'headlight dim ho rahi hai.',
            'Cooling System': 'engine bahut garam ho raha hai.',
            'Engine': 'engin knocking sound aa rahi hai.', 'Fuel System': 'petrol smell aa rahi hai near the tank.',
            'General Maintenance': 'oil change due hai.', 'Starting System': 'gaadi start nahi ho rahi.',
            'Suspension': 'suspension mein awaaz aa rahi hai on bumps.', 'Transmission': 'drive system rough ho raha hai.',
            'Tyres/Wheels': 'tyre hawa slowly kam ho rahi hai.',
        }[category]
        if facts['body'] == 'scooter' and category == 'Transmission': phrase = 'automatic drive feels rough.'
    template_id = f"{category.replace('/', '_').replace(' ', '_')}:{facts['body']}:hinglish" if is_hinglish else f"{category.replace('/', '_').replace(' ', '_')}:{facts['body']}:{phrase_index}:{opening_index}:{ending_index}"
    return phrase, template_id


def find_part(parts_by_key, category, vehicle_type, model, rng):
    available = parts_by_key[(category, vehicle_type, model)]
    quantity = int(rng.integers(1, min(3, len(available)) + 1))
    return [available[int(i)] for i in rng.choice(len(available), size=quantity, replace=False)]


def generate():
    rng = np.random.default_rng(SEED)
    dates = [START + timedelta(days=offset) for offset in range((END - START).days + 1)]
    closed = {'2025-01-26','2025-03-14','2025-08-15','2025-10-02','2025-10-20','2025-10-21','2025-11-05','2026-01-26','2026-03-04','2026-08-15','2026-10-02','2026-10-20'}
    daily_counts = {day: (0 if day.weekday()==6 or day.isoformat() in closed or (day > END-timedelta(days=6) and day != END) else (1 if day == END else max(1, int(rng.poisson(day_factor(day)))))) for day in dates}
    total_jobs = sum(daily_counts.values())
    n_faults = np.asarray(rng.choice([1, 2, 3], size=total_jobs, p=[.69, .27, .04]), dtype=int)
    parts = part_catalog()
    parts_by_key = defaultdict(list)
    for part in parts:
        for model in json.loads(part['compatible_models']):
            parts_by_key[(part['fault_category'], part['vehicle_type'], model)].append(part)
    jobs = []
    row_idx = 0
    multi_number = 0
    for day in dates:
        for _ in range(daily_counts[day]):
            count = 1 if day == END else int(n_faults[row_idx])
            if count > 1:
                multi_number += 1
            vague_general = count == 1 and rng.random() < .045
            if vague_general:
                count = 1
            faults = make_job_faults(count, day, rng, multi_number)
            if vague_general or day == END: faults = ['General Maintenance']
            vtype, brand, model, age, km = choose_vehicle(rng)
            phrased = {category: phrase_for(category, day, rng, vtype, model) for category in faults}
            symptom_by_fault = {category: value[0] for category,value in phrased.items()}
            template_ids = {category: value[1] for category,value in phrased.items()}
            if vague_general:
                symptom_by_fault['General Maintenance'] = 'Routine check requested; no specific symptom described.'
                template_ids['General Maintenance'] = 'General_Maintenance:vague:unspecified'
            symptoms = ' '.join(symptom_by_fault[category] for category in faults)
            if vtype == 'bike': symptoms = symptoms.replace('driving', 'riding')
            else: symptoms = symptoms.replace('riding', 'driving')
            severity_map = {category: severity_for_fault(category, symptom_by_fault[category]) for category in faults}
            combined = combined_severity(faults, severity_map)
            parts_by_fault = [find_part(parts_by_key, category, vtype, model, rng) for category in faults]
            part_rows = [part for group in parts_by_fault for part in group]
            base_parts = sum(part['unit_cost'] for part in part_rows)
            labor_costs = [int(rng.integers(160, 960) * (1.18 if vtype == 'car' else .78) * PRICE_FACTORS.get(category, {}).get(vtype, 1.0)) for category in faults]
            labor_total = sum(labor_costs)
            invoice_by_fault = [sum(part['unit_price'] for part in group) + labor for group, labor in zip(parts_by_fault, labor_costs)]
            invoice = sum(invoice_by_fault)
            warranty = count == 1 and rng.random() < .018
            # A limited February voucher campaign creates a few modest loss
            # jobs and one negative month without overwhelming the whole file.
            loss_month_discount = day.strftime('%Y-%m') == '2025-02' and not warranty and rng.random() < .42
            if count >= 2:
                discount = int(round(invoice * MULTI_FAULT_DISCOUNT_RATE))
                warranty = False
                loss_month_discount = False
            else:
                discount = invoice if warranty else (
                    int(round(invoice * .50)) if loss_month_discount else
                    (int(round(invoice * rng.uniform(.04, .12))) if rng.random() < .12 else 0)
                )
            charge = max(0, invoice - discount)
            # Allocate the final customer charge by each fault's invoice share.
            # This remains exact for full warranty write-offs, where an equal
            # discount split could otherwise exceed a cheap individual fault.
            line_totals = invoice_by_fault
            allocations = [int(charge * line / invoice) for line in line_totals]
            remainder = charge - sum(allocations)
            for index in range(remainder):
                allocations[index % len(allocations)] += 1
            per_fault_cost = {category: allocation for category, allocation in zip(faults, allocations)}
            faults = sorted(faults, key=lambda f: (SEVERITY_RULE_TABLE['levels'].index(severity_map[f]), per_fault_cost[f]), reverse=True)
            per_fault_cost = {f: per_fault_cost[f] for f in faults}
            severity_map = {f: severity_map[f] for f in faults}
            template_ids = {f: template_ids[f] for f in faults}
            part_rows = [p for f in faults for p in parts_by_fault[[*symptom_by_fault].index(f)]]
            jobs.append({
                'job_id': f'J{row_idx + 1:06d}', 'planned_date': day,
                'service_time': (datetime.combine(day, time(8, 0)) + timedelta(minutes=int(rng.integers(0, 600)))).strftime('%H:%M:%S'),
                'vehicle_type': vtype, 'brand': brand, 'model': model, 'age': age, 'km_driven': km,
                'primary_fault': faults[0], 'faults': faults, 'fault_count': count,
                'symptoms': symptoms, 'per_fault_severity': severity_map, 'severity': combined,
                'symptom_template_id': template_ids,
                'parts': part_rows, 'per_fault_cost': per_fault_cost,
                'customer_charge': charge, 'parts_cost': base_parts, 'labour_cost': labor_total,
                'discount': discount, 'gross_margin': charge - base_parts - labor_total,
                'invoice': invoice, 'warranty': warranty,
                'stockout_delay_days': 0, 'status': 'warranty_rework' if warranty else ('discounted_loss' if loss_month_discount else 'completed'),
            })
            row_idx += 1

    # Every month has at least one no-charge rework job, while the overwhelming
    # majority of jobs still earn a positive margin.
    by_month = defaultdict(list)
    for job in jobs:
        by_month[job['planned_date'].strftime('%Y-%m')].append(job)
    for month_jobs in by_month.values():
        if not any(job['warranty'] for job in month_jobs):
            single_jobs = [job for job in month_jobs if job['fault_count'] == 1]
            if not single_jobs: continue
            job = single_jobs[int(rng.integers(0, len(single_jobs)))]
            job['warranty'] = True
            job['status'] = 'warranty_rework'
            job['discount'] = job['invoice']
            job['customer_charge'] = 0
            job['gross_margin'] = -job['parts_cost'] - job['labour_cost']
            job['per_fault_cost'] = {fault: 0 for fault in job['faults']}

    # Reconcile every physical receipt and issue. Opening balances are explicit
    # ledger entries; shortages are logged and jobs wait for supplier lead time.
    stock = {row['part_id']: int(row['opening_stock']) for row in parts}
    part_by_id = {row['part_id']: row for row in parts}
    pending = defaultdict(list)
    ledger = []
    log_seq = 0

    def log_event(event_date, event_type, part_id, delta, job_id='', note=''):
        nonlocal log_seq
        log_seq += 1
        part = part_by_id[part_id]
        ledger.append({
            'event_id': f'L{log_seq:07d}', 'event_date': event_date.isoformat(),
            'event_time': '08:00:00', 'event_type': event_type, 'job_id': job_id,
            'part_id': part_id, 'quantity_change': int(delta), 'stock_after': None,
            'unit_cost': part['unit_cost'], 'unit_price': part['unit_price'],
            'supplier': part['supplier'], 'notes': note,
        })

    for part in parts:
        if part['opening_stock']:
            log_event(START, 'opening_stock', part['part_id'], part['opening_stock'], note='Opening inventory balance')

    def receive_due(until):
        due_orders = sorted(
            (due, part_id, quantity, reference_job)
            for part_id, orders in pending.items()
            for due, quantity, reference_job in orders if due <= until
        )
        for due, part_id, quantity, job_id in due_orders:
            pending[part_id] = [order for order in pending[part_id] if not (order[0] == due and order[1] == quantity and order[2] == job_id)]
            stock[part_id] += quantity
            log_event(due, 'restock', part_id, quantity, job_id, 'Supplier delivery')

    jobs_by_day = defaultdict(list)
    for job in jobs:
        jobs_by_day[job['planned_date']].append(job)
        job['_stockout_parts'] = set()
    waiting = []

    def complete_job(job, service_day):
        for part_id in [part['part_id'] for part in job['parts']]:
            stock[part_id] -= 1
            log_event(service_day, 'sale', part_id, -1, job['job_id'], 'Part issued to completed job')
            part = part_by_id[part_id]
            if stock[part_id] <= part['reorder_level'] and not pending[part_id]:
                due = service_day + timedelta(days=int(part['supplier_lead_time_days']))
                pending[part_id].append((due, max(int(part['reorder_level']) * 2, 2), job['job_id']))
        job['service_date'] = service_day
        job['stockout_delay_days'] = max(0, (service_day - job['planned_date']).days)
        if job['stockout_delay_days'] and job['status'] == 'completed':
            job['status'] = 'delayed'

    for day in dates:
        receive_due(day)
        waiting.extend(jobs_by_day[day])
        if day.weekday() == 6 or day.isoformat() in closed:
            continue
        for job in list(waiting):
            missing = [part['part_id'] for part in job['parts'] if stock[part['part_id']] < 1]
            if missing:
                for part_id in missing:
                    if part_id not in job['_stockout_parts']:
                        log_event(day, 'stock_out', part_id, 0, job['job_id'], 'Requested part unavailable; job delayed')
                        job['_stockout_parts'].add(part_id)
                    if not pending[part_id]:
                        part = part_by_id[part_id]
                        due = day + timedelta(days=int(part['supplier_lead_time_days']))
                        pending[part_id].append((due, max(int(part['reorder_level']) * 2, 2), job['job_id']))
                continue
            complete_job(job, day)
            waiting.remove(job)

    # Finish lead-time-compliant orders inside the data window. The final
    # supplier lead-time buffer above prevents synthetic instant deliveries.
    receive_due(END)
    if waiting:
        raise AssertionError(f'Jobs still waiting beyond data window: {len(waiting)}')
    # Keep deliveries inside the snapshot boundary; future purchase orders are
    # not current stock or completed stock movements.
    ledger = [row for row in ledger if date.fromisoformat(row['event_date']) <= END]
    old_ids = {job['job_id']: job for job in jobs}
    jobs.sort(key=lambda job: (job['service_date'], job['service_time'], job['job_id']))
    id_map = {}
    for index, job in enumerate(jobs, 1):
        old_id = job['job_id']; new_id = f'J{index:06d}'
        id_map[old_id] = new_id; job['job_id'] = new_id
    for event in ledger:
        if event['job_id'] in id_map: event['job_id'] = id_map[event['job_id']]
    ledger.sort(key=lambda row: (row['event_date'], row['event_time'], row['event_id']))
    running = {row['part_id']: 0 for row in parts}
    for row in ledger:
        running[row['part_id']] += int(row['quantity_change'])
        if running[row['part_id']] < 0:
            history = [event for event in ledger if event['part_id'] == row['part_id'] and (event['event_date'], event['event_time'], event['event_id']) <= (row['event_date'], row['event_time'], row['event_id'])]
            raise AssertionError(f"Negative inventory at {row['event_id']} part={row['part_id']} history={history[-8:]}")
        row['stock_after'] = running[row['part_id']]
    for part in parts:
        part['stock'] = running[part['part_id']]
        part['snapshot_date'] = END.isoformat()

    service_rows = []
    for job in jobs:
        faults = job['faults']
        service_rows.append({
            'job_id': job['job_id'], 'service_date': job['service_date'].isoformat(),
            'service_time': job['service_time'], 'vehicle_type': job['vehicle_type'],
            'brand': job['brand'], 'model': job['model'], 'age': job['age'],
            'km_driven': job['km_driven'], 'symptoms': job['symptoms'],
            'symptom_template_id': json.dumps(job['symptom_template_id'], ensure_ascii=False, sort_keys=True),
            'primary_fault': job['primary_fault'], 'faults': ';'.join(faults),
            'fault_count': job['fault_count'],
            'per_fault_severity': json.dumps(job['per_fault_severity'], ensure_ascii=False, sort_keys=True),
            'severity': job['severity'],
            'parts_used': json.dumps([part['part_id'] for part in job['parts']]),
            'per_fault_cost': json.dumps(job['per_fault_cost'], ensure_ascii=False, sort_keys=True),
            'customer_charge': job['customer_charge'], 'parts_cost': job['parts_cost'],
            'labour_cost': job['labour_cost'], 'gross_margin': job['gross_margin'],
            'discount': job['discount'], 'stockout_delay_days': job['stockout_delay_days'],
            'status': job['status'],
        })
    services = pd.DataFrame(service_rows)
    services.sort_values(['service_date', 'service_time', 'job_id'], inplace=True, ignore_index=True)
    stock_frame = pd.DataFrame(parts)
    log_frame = pd.DataFrame(ledger)
    services['month'] = services.service_date.str.slice(0, 7)
    summary = services.groupby('month', as_index=False).agg(
        jobs=('job_id', 'count'), revenue=('customer_charge', 'sum'),
        parts_cost=('parts_cost', 'sum'), labour_cost=('labour_cost', 'sum'),
        gross_margin=('gross_margin', 'sum'), discount=('discount', 'sum'),
        stockout_delay_days=('stockout_delay_days', 'sum'),
    )
    finance_rows = services.assign(gross_profit=services.gross_margin.clip(lower=0), gross_loss=services.gross_margin.clip(upper=0))
    pnl = finance_rows.groupby('month').agg(gross_profit=('gross_profit', 'sum'), gross_loss=('gross_loss', 'sum')).reset_index()
    summary = summary.merge(pnl, on='month', how='left')
    summary['rent_overhead'] = 30000
    summary['salary_overhead'] = 45000
    summary['utilities_overhead'] = 10000
    summary['total_overheads'] = summary[['rent_overhead','salary_overhead','utilities_overhead']].sum(axis=1)
    summary['net_profit'] = summary.gross_margin - summary.total_overheads
    summary['profit_loss'] = summary.net_profit
    summary['mom_change_pct'] = summary.net_profit.pct_change() * 100
    summary['mom_change_pct'] = summary.mom_change_pct.replace([np.inf,-np.inf], np.nan).fillna(0).round(2)
    summary['trend'] = np.where(summary.mom_change_pct >= 3, 'growth', np.where(summary.mom_change_pct <= -3, 'dip', 'stable'))
    summary = summary[['month', 'jobs', 'revenue', 'parts_cost', 'labour_cost', 'gross_profit', 'gross_loss', 'gross_margin', 'rent_overhead', 'salary_overhead', 'utilities_overhead', 'total_overheads', 'net_profit', 'mom_change_pct', 'trend', 'discount', 'stockout_delay_days', 'profit_loss']]
    services.drop(columns=['month'], inplace=True)

    services.to_csv(ROOT / 'service_records.csv', index=False)
    stock_frame.to_csv(ROOT / 'inventory_stock.csv', index=False)
    log_frame.to_csv(ROOT / 'inventory_log.csv', index=False)
    summary.to_csv(ROOT / 'monthly_summary.csv', index=False)
    print(json.dumps({
        'seed': SEED, 'jobs': len(services), 'service_date_min': services.service_date.min(),
        'service_date_max': services.service_date.max(), 'fault_counts': dict(Counter(f for value in services.faults for f in value.split(';'))),
        'fault_count_distribution': {str(key): int(value) for key, value in Counter(services.fault_count).items()},
        'vehicle_counts': dict(Counter(services.vehicle_type)),
        'rows_per_month': {str(month): int(count) for month, count in zip(summary.month, summary.jobs)},
        'stockout_jobs': int((services.stockout_delay_days > 0).sum()),
        'monthly_profit_loss_min': int(summary.profit_loss.min()),
        'monthly_profit_loss_max': int(summary.profit_loss.max()),
    }, indent=2))


if __name__ == '__main__':
    generate()

