"""Create deterministic, internally consistent workshop operations data."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.ml.severity import SEVERITY_RULE_TABLE, combined_severity, severity_for_fault

SEASONAL = {
    1: 0.88, 2: 0.86, 3: 0.91, 4: 1.00, 5: 1.10, 6: 1.17,
    7: 1.14, 8: 1.10, 9: 1.00, 10: 1.22, 11: 1.16, 12: 0.92,
}
SEASONAL_FAULT = {
    'Battery/Electrical': {12: 1.35, 1: 1.45, 2: 1.3, 7: 1.2, 8: 1.15},
    'Starting System': {12: 1.3, 1: 1.5, 2: 1.3},
    'Cooling System': {4: 1.15, 5: 1.5, 6: 1.6},
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
FAULT_WEIGHTS = {
    'General Maintenance': .23, 'Tyres/Wheels': .11, 'Brake System': .12,
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
    cost_ranges = {
        'Battery/Electrical': (700, 2400, 6), 'Brake System': (120, 1600, 4),
        'Cooling System': (160, 1900, 4), 'Engine': (180, 2600, 6),
        'Fuel System': (90, 1300, 5), 'General Maintenance': (120, 1100, 5),
        'Starting System': (80, 1500, 4), 'Suspension': (160, 2600, 5),
        'Transmission': (130, 3200, 5), 'Tyres/Wheels': (80, 4200, 5),
    }
    for category in CATEGORIES:
        low, high, lead = cost_ranges[category]
        for vtype in ('bike', 'car'):
            compatible = [model for brand, models in VEHICLES[vtype].items() for model in models]
            groups = [compatible]
            if category == 'Transmission' and vtype == 'bike':
                scooters = [model for model in compatible if MODEL_FACTS[model]['body'] == 'scooter']
                manual = [model for model in compatible if model not in scooters]
                groups = [manual, scooters]
            base_part_name = {
                'Battery/Electrical': 'Battery and terminal kit',
                'Brake System': 'Brake pads and service kit' if vtype == 'car' else 'Brake shoe and pad kit',
                'Cooling System': 'Radiator hose and coolant kit',
                'Engine': 'Engine sensor and gasket kit',
                'Fuel System': 'Fuel filter and hose kit',
                'General Maintenance': 'Oil and air filter service kit',
                'Starting System': 'Starter relay and plug kit',
                'Suspension': 'Shock absorber service kit',
                'Transmission': 'Clutch and drive kit',
                'Tyres/Wheels': 'Tyre and valve kit',
            }[category]
            for model_group in groups:
                if not model_group:
                    continue
                name = base_part_name
                if category == 'Transmission' and vtype == 'bike':
                    name = 'Scooter drive belt and variator kit' if MODEL_FACTS[model_group[0]]['body'] == 'scooter' else 'Clutch plate and drive chain kit'
                pid = f"P-{vtype[:1].upper()}-{len(rows)+1:02d}"
                unit_cost = int((low + high) / 2)
                unit_price = int(round(unit_cost * 1.32 / 10) * 10)
                reorder = 8 if category in ('General Maintenance', 'Brake System', 'Tyres/Wheels') else 5
                opening = 0 if len(rows) % 13 == 0 else reorder + 2
                rows.append({
                    'part_id': pid, 'part_name': name, 'fault_category': category,
                    'vehicle_type': vtype, 'compatible_models': json.dumps(model_group),
                    'opening_stock': opening, 'stock': opening, 'reorder_level': reorder,
                    'unit_cost': unit_cost, 'unit_price': unit_price,
                    'supplier_lead_time_days': lead, 'supplier': f'{category.split()[0]} Supply Co.',
                })
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
    # Cycle deliberately chosen cross-system pairs into the labels as well as
    # sampling naturally from the non-uniform annual fault mix.
    spanning_pairs = [
        ('Tyres/Wheels', 'Battery/Electrical'), ('Brake System', 'Suspension'),
        ('Engine', 'Cooling System'), ('Fuel System', 'Engine'),
        ('General Maintenance', 'Brake System'), ('Starting System', 'Battery/Electrical'),
        ('Transmission', 'Tyres/Wheels'), ('Cooling System', 'Battery/Electrical'),
        ('Suspension', 'Tyres/Wheels'), ('Fuel System', 'General Maintenance'),
    ]
    if count >= 2 and multi_number % 7 == 0:
        chosen = list(spanning_pairs[(multi_number // 7) % len(spanning_pairs)])
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
    age = int(rng.integers(1, 19))
    annual = float(rng.uniform(4000, 18000) if vtype == 'bike' else rng.uniform(6000, 20000))
    km = int(round(age * annual * rng.uniform(.85, 1.15) / 100) * 100)
    return vtype, brand, model, age, km


def phrase_for(category, day, rng):
    phrase = str(rng.choice(FAULT_PHRASES[category]))
    if day.month in (6, 7, 8, 9) and category in ('Tyres/Wheels', 'Brake System', 'Battery/Electrical'):
        phrase += ' Water spray has made the issue more noticeable.'
    if day.month in (4, 5, 6) and category == 'Cooling System':
        phrase += ' It happens most often in afternoon traffic.'
    wrapper = str(rng.choice(['Customer reports: ', 'Workshop note: ', 'Driver says: ', 'Inspection found: ', 'The owner mentions: ']))
    if rng.random() < .025:
        phrase += ' The noise comes and goes, but the listed fault is still present.'
    return wrapper + phrase


def find_part(parts_by_key, category, vehicle_type, model):
    return parts_by_key[(category, vehicle_type, model)]


def generate():
    rng = np.random.default_rng(SEED)
    dates = [START + timedelta(days=offset) for offset in range((END - START).days + 1)]
    daily_counts = {day: max(1, int(rng.poisson(day_factor(day)))) for day in dates}
    total_jobs = sum(daily_counts.values())
    n_faults = np.asarray(rng.choice([1, 2, 3], size=total_jobs, p=[.69, .27, .04]), dtype=int)
    parts = part_catalog()
    parts_by_key = {
        (row['fault_category'], row['vehicle_type'], model): row
        for row in parts for model in json.loads(row['compatible_models'])
    }
    jobs = []
    row_idx = 0
    multi_number = 0
    for day in dates:
        for _ in range(daily_counts[day]):
            count = int(n_faults[row_idx])
            if count > 1:
                multi_number += 1
            faults = make_job_faults(count, day, rng, multi_number)
            vtype, brand, model, age, km = choose_vehicle(rng)
            symptom_by_fault = {category: phrase_for(category, day, rng) for category in faults}
            symptoms = ' '.join(symptom_by_fault[category] for category in faults)
            severity_map = {category: severity_for_fault(category, symptom_by_fault[category]) for category in faults}
            combined = combined_severity(faults, severity_map)
            part_rows = [find_part(parts_by_key, category, vtype, model) for category in faults]
            base_parts = sum(part['unit_cost'] for part in part_rows)
            labor_costs = [int(rng.integers(160, 960) * (1.18 if vtype == 'car' else .78)) for _ in faults]
            labor_total = sum(labor_costs)
            invoice = sum(part['unit_price'] + labor for part, labor in zip(part_rows, labor_costs))
            warranty = rng.random() < .018
            # A limited February voucher campaign creates a few modest loss
            # jobs and one negative month without overwhelming the whole file.
            loss_month_discount = day.strftime('%Y-%m') == '2025-02' and not warranty and rng.random() < .42
            discount = invoice if warranty else (
                int(round(invoice * .50)) if loss_month_discount else
                (int(round(invoice * rng.uniform(.04, .12))) if rng.random() < .12 else 0)
            )
            charge = max(0, invoice - discount)
            # Allocate the final customer charge by each fault's invoice share.
            # This remains exact for full warranty write-offs, where an equal
            # discount split could otherwise exceed a cheap individual fault.
            line_totals = [int(part['unit_price'] + labor) for part, labor in zip(part_rows, labor_costs)]
            allocations = [int(charge * line / invoice) for line in line_totals]
            remainder = charge - sum(allocations)
            for index in range(remainder):
                allocations[index % len(allocations)] += 1
            per_fault_cost = {category: allocation for category, allocation in zip(faults, allocations)}
            jobs.append({
                'job_id': f'J{row_idx + 1:06d}', 'planned_date': day,
                'service_time': (datetime.combine(day, time(8, 0)) + timedelta(minutes=int(rng.integers(0, 600)))).strftime('%H:%M:%S'),
                'vehicle_type': vtype, 'brand': brand, 'model': model, 'age': age, 'km_driven': km,
                'primary_fault': faults[0], 'faults': faults, 'fault_count': count,
                'symptoms': symptoms, 'per_fault_severity': severity_map, 'severity': combined,
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
            job = month_jobs[int(rng.integers(0, len(month_jobs)))]
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

    # Close the reporting window with expedited supplier deliveries for the
    # rare jobs still waiting at month end; no unfulfilled job is hidden.
    receive_due(END)
    for job in list(waiting):
        for part_id in [part['part_id'] for part in job['parts']]:
            if stock[part_id] < 1:
                pending[part_id] = [order for order in pending[part_id] if order[0] <= END]
                receive_due(END)
            if stock[part_id] < 1:
                part = part_by_id[part_id]
                quantity = max(int(part['reorder_level']) * 2, 2)
                stock[part_id] += quantity
                log_event(END, 'restock', part_id, quantity, job['job_id'], 'Expedited month-end delivery')
        complete_job(job, END)
        waiting.remove(job)
    # Keep deliveries inside the snapshot boundary; future purchase orders are
    # not current stock or completed stock movements.
    ledger = [row for row in ledger if date.fromisoformat(row['event_date']) <= END]
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
    summary['profit_loss'] = summary.revenue - summary.parts_cost - summary.labour_cost
    summary = summary[['month', 'jobs', 'revenue', 'parts_cost', 'labour_cost', 'gross_profit', 'gross_loss', 'gross_margin', 'discount', 'stockout_delay_days', 'profit_loss']]
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

