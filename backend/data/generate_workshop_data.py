"""Create deterministic, internally consistent workshop operations data."""
from __future__ import annotations

import json
import re
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
    'Battery/Electrical': {12: 3.0, 1: 3.2, 2: 3.0, 7: 1.2, 8: 1.15},
    'Starting System': {12: 3.0, 1: 3.2, 2: 2.8},
    'Cooling System': {1: .55, 2: .60, 3: .75, 4: 3.2, 5: 4.8, 6: 4.5},
    'Tyres/Wheels': {6: 1.35, 7: 2.1, 8: 2.0, 9: 1.8},
    'Brake System': {6: 1.4, 7: 3.2, 8: 3.0, 9: 2.6},
}
SHOCK_DAYS = {
    date(2025, 6, 12): 2.5, date(2026, 7, 15): 2.25,
}
QUIET_WEEKS = [(date(2025, 2, 3), date(2025, 2, 9)), (date(2026, 6, 8), date(2026, 6, 14))]
STABLE_STRETCHES = [(date(2025, 4, 1), date(2025, 5, 15)), (date(2026, 1, 10), date(2026, 2, 25))]


ROOT = Path(__file__).resolve().parent
SEED = 20261102
TARGET_JOBS = 7000
START = date(2025, 1, 1)
END = date(2026, 10, 31)

CATEGORIES = [
    'Battery/Electrical', 'Brake System', 'Cooling System', 'Engine', 'Fuel System',
    'General Maintenance', 'Starting System', 'Suspension', 'Transmission', 'Tyres/Wheels',
]
LABOUR_RATE = {'bike': 350, 'car': 700}
SEVERITY_HOURS = {'low': .45, 'medium': .75, 'high': 1.20, 'critical': 1.65}
SEVERITY_PART_COUNT = {'low': 1, 'medium': 1, 'high': 2, 'critical': 3}
FAULT_WEIGHTS = {
    'General Maintenance': .40, 'Tyres/Wheels': .13, 'Brake System': .12,
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

# Per-unit acquisition cost and customer price in INR. Each category has three
# compatible SKUs per class; bike transmission SKUs are split by drivetrain.
# These values are anchored to the cited OEM/catalogue rows in the reference
# CSV where available; remaining aftermarket items are labeled estimates.
PART_PRICE_TABLE = {
    'Battery/Electrical': {'bike': [('Headlight bulb', 150, 240), ('Regulator and terminal kit', 560, 900), ('Battery 5Ah', 2200, 3200)], 'car': [('Bulb set', 250, 400), ('Alternator belt', 700, 1100), ('Battery 35Ah', 4800, 6041)]},
    'Brake System': {'bike': [('Brake pad set', 680, 1000), ('Brake shoe set', 600, 900), ('Brake disc and fluid kit', 1900, 2800)], 'car': [('Front brake pad set', 1275, 1800), ('Brake rotor', 2600, 3600), ('Brake fluid and hardware kit', 700, 1100)]},
    'Cooling System': {'bike': [('Cooling fin cleaning kit', 180, 320), ('Thermal sensor', 420, 700), ('Cooling airflow service kit', 650, 1050)], 'car': [('Coolant', 950, 1596), ('Thermostat and seal', 1100, 1800), ('Radiator hose and clamp kit', 1400, 2300)]},
    'Engine': {'bike': [('Gasket and seal set', 850, 1300), ('Spark plug set', 360, 560), ('Oil pump and filter kit', 1400, 2200)], 'car': [('Gasket set', 1800, 2800), ('Spark plug set of four', 650, 1000), ('Oil pump and filter kit', 2600, 4200)]},
    'Fuel System': {'bike': [('Fuel hose and clamp kit', 180, 300), ('Fuel filter', 120, 210), ('Injector service kit', 550, 900)], 'car': [('Fuel filter', 767, 1100), ('Fuel hose and clamp kit', 750, 1200), ('Injector service kit', 1600, 2600)]},
    'General Maintenance': {'bike': [('Engine oil and filter kit', 420, 680), ('Air filter element', 220, 360), ('Service consumables kit', 600, 950)], 'car': [('Oil and filter kit', 1300, 2100), ('Air filter element', 550, 900), ('Periodic service consumables', 2000, 3300)]},
    'Starting System': {'bike': [('Starter relay', 280, 440), ('Spark plug', 250, 390), ('Starter motor brush kit', 800, 1250)], 'car': [('Starter relay', 650, 1050), ('Spark plug set', 650, 1000), ('Starter motor service kit', 1900, 3100)]},
    'Suspension': {'bike': [('Fork seal and oil kit', 350, 580), ('Rear shock absorber', 1200, 1900), ('Suspension bush kit', 450, 750)], 'car': [('Shock absorber', 2800, 4400), ('Strut mount and bush kit', 1800, 2900), ('Suspension link kit', 2200, 3600)]},
    'Transmission': {'bike': [('Chain and sprocket kit', 1300, 2200), ('Clutch plate kit', 850, 1450), ('CVT belt and roller kit', 1100, 1850), ('CVT roller weights', 450, 750), ('CVT clutch shoe kit', 700, 1150)], 'car': [('Clutch plate kit', 4200, 6800), ('Transmission fluid and filter', 2200, 3600), ('Gearbox mount kit', 2600, 4200)]},
    'Tyres/Wheels': {'bike': [('Tube and valve kit', 500, 780), ('Tyre', 2500, 3600), ('Wheel bearing kit', 750, 1150)], 'car': [('Tyre repair and valve kit', 900, 1500), ('185/65 R15 tyre', 5849, 7000), ('Wheel bearing kit', 1800, 2900)]},
}

STYLE_OPENERS = {
    'owner': ['', 'Since yesterday, ', 'On the commute, ', 'Lately, ', 'After parking overnight, ', 'For a few days, ', 'At low speed, ', 'In traffic, '],
    'mechanic': ['Customer reports ', 'Inspection notes ', 'Workshop check found ', 'On road test, ', 'Owner complaint: ', 'Technician observed ', 'Initial check shows ', 'Vehicle arrives with '],
    'sms': ['', 'pls check: ', 'Need help, ', 'Issue: ', 'noticed ', 'check this - ', 'problem is ', 'help needed: '],
    'hinglish': ['', 'Bhai, ', 'Yaar, ', 'Gaadi mein ', 'Abhi ', 'Aaj ', 'Please check, ', 'Issue aa raha: '],
}
STYLE_ENDINGS = ['', '.', ' on most trips.', ' again today.', ' pls check.', ' after the last service.', ' since the rain.', ' when the vehicle is warm.']
TYPO_VARIANTS = {'brake': ('brke', 'break'), 'battery': ('battrey', 'batery'), 'engine': ('engin', 'engne'), 'tyre': ('tyer', 'tire'), 'suspension': ('suspention',), 'starting': ('strting',), 'fuel': ('fule',), 'cooling': ('coolng',)}


def price_source(category, vehicle_type, part_name):
    key = (category, vehicle_type, part_name)
    sources = {
        ('Brake System','car','Front brake pad set'): ('Ford India Motorcraft parts', 'https://www.india.ford.com/owner/ford-motorcraft-parts/'),
        ('Cooling System','car','Coolant'): ('Ford India Motorcraft parts', 'https://www.india.ford.com/owner/ford-motorcraft-parts/'),
        ('Engine','car','Spark plug set of four'): ('Ford India Motorcraft parts', 'https://www.india.ford.com/owner/ford-motorcraft-parts/'),
        ('Transmission','bike','Chain and sprocket kit'): ('Bajaj Genuine Parts e-Shop', 'https://bajajgenuine.dpmco.com/'),
        ('Brake System','bike','Brake pad set'): ('Bajaj Genuine Parts e-Shop', 'https://bajajgenuine.dpmco.com/'),
        ('Tyres/Wheels','car','185/65 R15 tyre'): ('Tyresnmore 185/65 R15 listings', 'https://tyresnmore.com/all/tyre-size/185-65-r15.html'),
    }
    return sources.get(key, ('estimate', ''))


def part_catalog():
    rows = []
    lead_days = {'Battery/Electrical': 5, 'Brake System': 4, 'Cooling System': 5,
                 'Engine': 7, 'Fuel System': 5, 'General Maintenance': 3,
                 'Starting System': 4, 'Suspension': 7, 'Transmission': 8,
                 'Tyres/Wheels': 5}
    for category in CATEGORIES:
        for vtype in ('bike', 'car'):
            models = [m for brand, ms in VEHICLES[vtype].items() for m in ms]
            for sku_idx, (name, cost, price) in enumerate(PART_PRICE_TABLE[category][vtype]):
                compatible = models
                if category == 'Transmission' and vtype == 'bike':
                    compatible = [m for m in models if (('CVT' in name) == (MODEL_FACTS[m]['body'] == 'scooter'))]
                if category == 'Cooling System' and vtype == 'bike':
                    compatible = [m for m in models if MODEL_FACTS[m]['cooling'] == 'air']
                if not compatible:
                    continue
                reorder = 4 + (sku_idx % 2)
                source_name, source_url = price_source(category, vtype, name)
                rows.append({
                    'part_id': f'P-{vtype[0].upper()}-{len(rows)+1:03d}', 'part_name': name,
                    'fault_category': category, 'vehicle_type': vtype,
                    'compatible_models': json.dumps(compatible), 'opening_stock': reorder + 3,
                    'stock': reorder + 3, 'reorder_level': reorder, 'unit_cost': int(round(cost * .86)),
                    'unit_price': price, 'supplier_lead_time_days': lead_days[category],
                    'supplier': f'{category.split()[0]} Supply Co.', 'price_source': source_name,
                    'price_source_url': source_url, 'price_basis': 'catalogue/official listing' if source_url else 'estimate',
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


def phrase_for(category, severity, day, rng, vtype, model):
    facts = MODEL_FACTS[model]
    category_id = category.replace('/', '_').replace(' ', '_')
    if category == 'Transmission' and vtype == 'bike':
        cue = 'CVT belt' if facts['body'] == 'scooter' else 'chain drive'
        signal = {
            'low': f'{cue} makes a faint sound', 'medium': f'{cue} feels rough under load',
            'high': f'{cue} slips during acceleration', 'critical': 'transmission has seized completely',
        }[severity]
    elif category == 'Cooling System' and facts['cooling'] == 'air':
        signal = {
            'low': 'cooling fins need a routine clean', 'medium': 'engine heat rises in traffic',
            'high': 'engine temperature keeps climbing', 'critical': 'engine is overheating rapidly and steam is visible',
        }[severity]
    else:
        level_signals = {
            'Battery/Electrical': {'low':'headlights dim at idle','medium':'battery warning light stays on','high':'battery repeatedly needs jump starts','critical':'battery is burning and smoke is visible'},
            'Brake System': {'low':'brake pads squeak but stopping feels normal','medium':'brakes grind when applied','high':'brake pedal feels soft and takes longer to stop','critical':'brake failure on the road'},
            'Cooling System': {'low':'coolant level is checked during routine service','medium':'coolant level slowly drops','high':'engine temperature rises in traffic','critical':'engine is overheating rapidly and steam is visible'},
            'Engine': {'low':'engine feels slightly rough at idle','medium':'engine makes a light knock','high':'engine misfires under load','critical':'oil pressure warning appears with a loud engine knock'},
            'Fuel System': {'low':'fuel filter is due for inspection','medium':'fuel economy has dropped','high':'strong petrol smell near the tank','critical':'fuel is leaking heavily near the engine'},
            'General Maintenance': {'low':'scheduled oil and filter service is due','medium':'routine service check is overdue','high':'engine oil is overdue and level is very low','critical':'oil pressure warning appears during overdue service'},
            'Starting System': {'low':'starter turns a little slowly on cold starts','medium':'starter clicks when the key is turned','high':'vehicle will not start after repeated attempts','critical':'starter wiring is burning with smoke'},
            'Suspension': {'low':'shock absorber squeaks over bumps','medium':'suspension clunks on rough roads','high':'suspension bottoms out with a passenger','critical':'steering has locked while moving'},
            'Transmission': {'low':'transmission makes a faint sound at low speed','medium':'gear changes feel stiff','high':'clutch slips under load','critical':'transmission has seized and wheels will not move'},
            'Tyres/Wheels': {'low':'tyre pressure drops slowly','medium':'wheel vibrates at road speed','high':'tyre has a sidewall bulge','critical':'tyre has burst at the sidewall'},
        }
        signal = level_signals[category][severity]
    if vtype == 'bike':
        signal = signal.replace('brake pedal', 'brake lever').replace('car', 'bike').replace('driving', 'riding')
        vehicle_word = 'bike'
    else:
        vehicle_word = 'car'
    if facts['body'] == 'scooter' and category == 'Transmission':
        signal = signal.replace('chain drive', 'CVT belt')
    style = str(rng.choice(['owner','mechanic','sms','hinglish'], p=[.42,.23,.23,.12]))
    opener = str(rng.choice(STYLE_OPENERS[style]))
    ending = str(rng.choice(STYLE_ENDINGS))
    variants = [signal, f'{vehicle_word}: {signal}', f'{signal} {vehicle_word}', f'{signal}; please inspect', f'{signal} after a cold start']
    clause_index = int(rng.integers(0, len(variants)))
    phrase = opener + variants[clause_index] + ending
    if style == 'hinglish':
        phrase = {
            'Battery/Electrical':'headlight dim ho rahi hai, battery weak lagti hai',
            'Brake System':'brake nahi lag raha, stopping weak hai',
            'Cooling System':'engine bahut garam ho raha hai', 'Engine':'engin knock kar raha hai',
            'Fuel System':'petrol smell aa rahi hai', 'General Maintenance':'oil change due hai',
            'Starting System':'gaadi start nahi ho rahi', 'Suspension':'suspension mein awaaz aa rahi hai',
            'Transmission':'drive system rough ho raha hai', 'Tyres/Wheels':'tyre hawa kam ho rahi hai',
        }[category]
        if facts['body'] == 'scooter' and category == 'Transmission': phrase = 'scooter automatic drive rough hai'
    # Typo/drop-word style variants preserve the category and severity signal.
    if style == 'sms' and rng.random() < .35:
        phrase = phrase.replace('please', 'pls').replace('the ', '').replace(' is ', ' ')
    elif rng.random() < .035:
        key = next((word for word in TYPO_VARIANTS if word in phrase.lower()), None)
        if key:
            wrong = str(rng.choice(TYPO_VARIANTS[key]))
            phrase = re.sub(rf'\b{key}\b', wrong, phrase, count=1, flags=re.I)
    template_id = f'{category_id}:{severity}:{vtype}:{facts["body"]}:{style}:cue{clause_index}'
    family_id = f'{category_id}:{severity}:{style}:{"bike" if vtype == "bike" else "car"}'
    return phrase.strip().rstrip('.') + '.', template_id, family_id, False, []


def find_part(parts_by_key, category, vehicle_type, model, severity, rng):
    available = parts_by_key[(category, vehicle_type, model)]
    quantity = SEVERITY_PART_COUNT[severity]
    if category == 'Battery/Electrical' and vehicle_type == 'bike' and severity == 'low':
        return [next(p for p in available if 'bulb' in p['part_name'].lower())]
    if category == 'Brake System':
        by_name = {p['part_name'].lower():p for p in available}
        pad = next(p for p in available if 'pad' in p['part_name'].lower())
        shoe = next(p for p in available if 'shoe' in p['part_name'].lower() or 'fluid' in p['part_name'].lower())
        disc = next(p for p in available if 'disc' in p['part_name'].lower() or 'rotor' in p['part_name'].lower())
        return [pad] if severity in ('low','medium') else ([pad,disc] if severity=='high' else [pad,disc,shoe])
    selected = [available[int(i)] for i in rng.choice(len(available), size=min(quantity, len(available)), replace=False)]
    return selected


def generate():
    rng = np.random.default_rng(SEED)
    dates = [START + timedelta(days=offset) for offset in range((END - START).days + 1)]
    closed = {'2025-01-26','2025-03-14','2025-08-15','2025-10-02','2025-10-20','2025-10-21','2025-11-05','2026-01-26','2026-03-04','2026-08-15','2026-10-02','2026-10-20'}
    open_days = [day for day in dates if day.weekday() != 6 and day.isoformat() not in closed and day <= END - timedelta(days=14)]
    weights = np.asarray([day_factor(day) for day in open_days], dtype=float)
    daily_counts = dict(zip(open_days, rng.multinomial(TARGET_JOBS - 1, weights / weights.sum()).tolist()))
    daily_counts[END] = 1
    total_jobs = TARGET_JOBS
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
        for _ in range(daily_counts.get(day, 0)):
            count = int(n_faults[row_idx])
            if count > 1:
                multi_number += 1
            vague_general = count == 1 and rng.random() < .03
            if vague_general:
                count = 1
            faults = make_job_faults(count, day, rng, multi_number)
            if vague_general or day == END: faults = ['General Maintenance']
            vtype, brand, model, age, km = choose_vehicle(rng)
            ambiguous = count == 1 and not vague_general and rng.random() < (.10 / .69)
            ambiguity_set = ['Battery/Electrical', 'Starting System', 'Fuel System']
            if ambiguous:
                if faults[0] not in ambiguity_set:
                    faults = [str(rng.choice(ambiguity_set))]
                variants = ['will not start', 'wont start', 'does not start after parking', 'gaadi start nahi ho rahi']
                ambiguous_variant = str(rng.choice(variants))
                noun = 'car' if vtype == 'car' else 'bike'
                phrase = ambiguous_variant if ambiguous_variant.startswith('gaadi') else f'{noun} {ambiguous_variant}'
                category = faults[0]
                phrased = {category: (phrase, f'ambiguous:no-start:{ambiguous_variant.split()[0]}', 'ambiguous:start-cause:grouped', True, ambiguity_set)}
            else:
                phrased = {}
                for category in faults:
                    choices = ['low','medium','high','critical']
                    if category == 'General Maintenance': choices = ['low','medium','high']
                    probs = [.32,.43,.19,.06] if len(choices)==4 else [.60,.32,.08]
                    target_severity = str(rng.choice(choices, p=probs))
                    phrased[category] = phrase_for(category, target_severity, day, rng, vtype, model)
            symptom_by_fault = {category: value[0] for category,value in phrased.items()}
            template_ids = {category: value[1] for category,value in phrased.items()}
            family_ids = {category: value[2] for category,value in phrased.items()}
            if vague_general:
                symptom_by_fault['General Maintenance'] = 'Routine check requested; no specific symptom described.'
                template_ids['General Maintenance'] = 'General_Maintenance:vague:unspecified'
                family_ids['General Maintenance'] = 'General_Maintenance:vague'
            joiner = str(rng.choice([' and also ', ' plus ', ', ', ' aur ', '; ']))
            symptoms = joiner.join(symptom_by_fault[category] for category in faults)
            severity_map = {category: severity_for_fault(category, symptoms) for category in faults}
            combined = combined_severity(faults, severity_map)
            parts_by_fault = [find_part(parts_by_key, category, vtype, model, severity_map[category], rng) for category in faults]
            part_rows = [part for group in parts_by_fault for part in group]
            base_parts = sum(part['unit_cost'] for part in part_rows)
            labor_costs = []
            for category in faults:
                level = severity_map[category]
                hours = (.25 + .16 * len(parts_by_fault[faults.index(category)]) + (.08 if category in ('Engine','Transmission','Cooling System') else 0)) * SEVERITY_HOURS[level]
                labor_costs.append(int(round(hours * LABOUR_RATE[vtype] / 10) * 10))
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
            family_ids = {f: family_ids[f] for f in faults}
            part_rows = [p for f in faults for p in parts_by_fault[[*symptom_by_fault].index(f)]]
            estimate_min = max(1, int(round(charge * .90)))
            estimate_max = max(estimate_min, int(round(charge * 1.10)))
            jobs.append({
                'job_id': f'J{row_idx + 1:06d}', 'planned_date': day,
                'service_time': (datetime.combine(day, time(8, 0)) + timedelta(minutes=int(rng.integers(0, 600)))).strftime('%H:%M:%S'),
                'vehicle_type': vtype, 'brand': brand, 'model': model, 'age': age, 'km_driven': km,
                'primary_fault': faults[0], 'faults': faults, 'fault_count': count,
                'symptoms': symptoms, 'per_fault_severity': severity_map, 'severity': combined,
                'symptom_template_id': template_ids, 'phrasing_family_id': family_ids,
                'is_ambiguous': bool(ambiguous), 'ambiguity_categories': ambiguity_set if ambiguous else [],
                'parts': part_rows, 'per_fault_cost': per_fault_cost,
                'customer_charge': charge, 'parts_cost': base_parts, 'labour_cost': labor_total,
                'estimated_cost_min': estimate_min, 'estimated_cost_max': estimate_max,
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
    # Reorder-point review at the snapshot identifies the next four SKUs that
    # should be replenished based on observed two-year usage.
    for part in sorted(parts, key=lambda p: (p['stock'], p['part_id']))[:4]:
        part['reorder_level'] = max(int(part['reorder_level']), int(part['stock']))

    service_rows = []
    for job in jobs:
        faults = job['faults']
        service_rows.append({
            'job_id': job['job_id'], 'service_date': job['service_date'].isoformat(),
            'service_time': job['service_time'], 'vehicle_type': job['vehicle_type'],
            'brand': job['brand'], 'model': job['model'], 'age': job['age'],
            'km_driven': job['km_driven'], 'symptoms': job['symptoms'],
            'symptom_template_id': json.dumps(job['symptom_template_id'], ensure_ascii=False, sort_keys=True),
            'phrasing_family_id': json.dumps(job['phrasing_family_id'], ensure_ascii=False, sort_keys=True),
            'is_ambiguous': job['is_ambiguous'],
            'ambiguity_categories': json.dumps(job['ambiguity_categories'], ensure_ascii=False),
            'primary_fault': job['primary_fault'], 'faults': ';'.join(faults),
            'fault_count': job['fault_count'],
            'per_fault_severity': json.dumps(job['per_fault_severity'], ensure_ascii=False, sort_keys=True),
            'severity': job['severity'],
            'parts_used': json.dumps([part['part_id'] for part in job['parts']]),
            'per_fault_cost': json.dumps(job['per_fault_cost'], ensure_ascii=False, sort_keys=True),
            'customer_charge': job['customer_charge'], 'parts_cost': job['parts_cost'],
            'estimated_cost_min': job['estimated_cost_min'], 'estimated_cost_max': job['estimated_cost_max'],
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
    summary['rent_overhead'] = 95000
    summary['salary_overhead'] = 148000
    summary['utilities_overhead'] = 50000
    summary['total_overheads'] = summary[['rent_overhead','salary_overhead','utilities_overhead']].sum(axis=1)
    summary['net_profit'] = summary.gross_margin - summary.total_overheads
    summary['profit_loss'] = summary.net_profit
    summary['revenue_mom_change_pct'] = summary.revenue.pct_change(fill_method=None) * 100
    summary['jobs_mom_change_pct'] = summary.jobs.pct_change(fill_method=None) * 100
    summary['mom_change_pct'] = summary.revenue_mom_change_pct
    summary['trend'] = np.where(summary.mom_change_pct >= 5, 'growth', np.where(summary.mom_change_pct <= -5, 'dip', 'stable'))
    summary.loc[0, ['mom_change_pct','revenue_mom_change_pct','jobs_mom_change_pct']] = np.nan
    summary.loc[0, 'trend'] = 'stable'
    summary[['mom_change_pct','revenue_mom_change_pct','jobs_mom_change_pct']] = summary[['mom_change_pct','revenue_mom_change_pct','jobs_mom_change_pct']].round(2)
    summary = summary[['month', 'jobs', 'revenue', 'parts_cost', 'labour_cost', 'gross_profit', 'gross_loss', 'gross_margin', 'rent_overhead', 'salary_overhead', 'utilities_overhead', 'total_overheads', 'net_profit', 'mom_change_pct', 'revenue_mom_change_pct', 'jobs_mom_change_pct', 'trend', 'discount', 'stockout_delay_days', 'profit_loss']]
    services.drop(columns=['month'], inplace=True)

    # A separate, auditable price book; every SKU has an explicit class price.
    price_cols = ['part_id','part_name','fault_category','vehicle_type','unit_cost','unit_price','price_basis','price_source','price_source_url']
    stock_frame[price_cols].to_csv(ROOT / 'part_price_table.csv', index=False)
    services.to_csv(ROOT / 'service_records.csv', index=False)
    inventory_cols = [col for col in stock_frame.columns if col not in ('price_source','price_source_url','price_basis')]
    stock_frame[inventory_cols].to_csv(ROOT / 'inventory_stock.csv', index=False)
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


