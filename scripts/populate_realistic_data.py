import random, datetime, json
import os, sys
import pandas as pd
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.data.prepare_service_dataset import COMMON_PROBLEMS

# Define authentic North India repair price benchmarks & standard realistic diagnostic templates
# (2-wheelers / Bikes / Scooters, 4-wheelers / Cars)

bike_models = {
    'Hero': ['Splendor Plus', 'HF Deluxe'],
    'Honda': ['Shine 125', 'Activa 6G'],
    'TVS': ['Jupiter 110']
}

car_models = {
    'Maruti Suzuki': ['Swift', 'WagonR', 'Alto K10'],
    'Hyundai': ['i20'],
    'Tata': ['Tiago']
}
car_brands = list(car_models)
bike_brands = list(bike_models)

symptom_catalog = [
    ('Tyres/Wheels', 'Tyre puncture with visible nail and rapid loss of air pressure', 'tyre tube/puncture strip', 'Low', (80, 200), (150, 350)),
    ('Tyres/Wheels', 'Low tyre pressure losing air frequently every 2 days valve leaking', 'valve pin/air valve', 'Low', (60, 150), (100, 250)),
    ('Tyres/Wheels', 'Vehicle pulling to left uneven tyre tread wear wheel alignment needed', 'alignment balancing weight', 'Medium', (250, 600), (450, 1200)),
    ('Tyres/Wheels', 'Steering wheel and handlebar vibrating heavily at high speed bent rim', 'rim trueing / wheel balancing', 'Medium', (350, 800), (700, 1800)),
    ('Tyres/Wheels', 'Tyre sidewall bulge after hitting pothole tyre replacement needed', 'new tyre/tube', 'High', (1200, 2400), (2800, 5500)),
    ('Battery/Electrical', 'Headlight beam very dim and indicator flasher blinking too fast', 'headlight bulb/relay', 'Low', (150, 450), (350, 950)),
    ('Battery/Electrical', 'Vehicle horn completely dead or making weak croaking sound', 'horn/horn switch', 'Low', (180, 450), (400, 1100)),
    ('Battery/Electrical', 'Car AC not cooling vents throwing warm air AC gas low compressor cut off', 'AC gas topup / cabin filter', 'Medium', (0, 0), (1500, 3800)),
    ('Battery/Electrical', 'Battery warning light glowing alternator charging issue cluster flickering', 'alternator relay/fuse', 'High', (450, 1400), (1200, 3500)),
    ('Battery/Electrical', 'Power window not rolling up central locking key remote unresponsive', 'window motor/key battery', 'Low', (0, 0), (500, 1800)),
    ('Starting System', 'Self starter clicking sound but engine will not crank battery drained', 'battery jump/relay', 'High', (800, 2400), (1800, 4500)),
    ('Starting System', 'Engine cranking very slowly for 10 seconds before starting cold start issue', 'spark plug/starter carbon', 'Medium', (350, 950), (750, 2200)),
    ('Starting System', 'Kick starter slipping or jammed no compression on bike', 'kick ratchet gear', 'Medium', (250, 600), (0, 0)),
    ('Brake System', 'Brakes screeching loud metallic grinding noise brake pads worn down', 'brake pads/brake shoes', 'High', (350, 950), (1100, 2800)),
    ('Brake System', 'Brake pedal going deep down spongy feel without stopping power air in lines', 'brake fluid flush/bleeding', 'High', (250, 650), (600, 1600)),
    ('Brake System', 'Disc brake lever vibrating violently disc rotor warped or glazed', 'disc rotor machining/pads', 'Medium', (600, 1800), (1500, 3800)),
    ('Brake System', 'Handbrake parking brake not holding vehicle on slope loose brake cable', 'handbrake cable adjustment', 'Medium', (150, 350), (350, 900)),
    ('Engine', 'Engine overheating rapidly temperature gauge in red steam from bonnet', 'thermostat / head gasket check', 'High', (1500, 4500), (2800, 7500)),
    ('Engine', 'Engine knocking and metallic pinging sound under load tappet clearance loose', 'tappet adjustment / oil flush', 'High', (600, 1800), (1800, 5200)),
    ('Engine', 'Engine misfiring jerking severely during acceleration fouled spark plugs', 'spark plugs / ignition coil', 'Medium', (350, 1100), (850, 2600)),
    ('Engine', 'Heavy white or bluish smoke coming continuously from exhaust burning engine oil', 'piston rings / valve seals', 'High', (3000, 7500), (6500, 16000)),
    ('Engine', 'Check engine light glowing loss of pickup and engine stuttering at idle', 'sensor cleaning / OBD scan', 'Medium', (400, 1200), (800, 2500)),
    ('Fuel System', 'Drop in fuel mileage running very rich with strong petrol smell from exhaust', 'carburettor/injector clean', 'Medium', (350, 950), (900, 2400)),
    ('Fuel System', 'Fuel pipe leaking petrol near fuel pump filter cracked', 'fuel pipe / fuel filter', 'High', (180, 550), (450, 1200)),
    ('Fuel System', 'Black soot smoke during sudden acceleration clogged air filter', 'air filter / choke clean', 'Low', (200, 500), (450, 1100)),
    ('Transmission', 'Gears slipping hard to shift into gear grinding gear noise', 'clutch plates / gear oil', 'High', (1200, 3200), (3500, 9500)),
    ('Transmission', 'Clutch lever extremely tight and hard to press stiff clutch cable', 'clutch cable replacement', 'Low', (150, 450), (350, 950)),
    ('Transmission', 'Scooter drive belt and variator rollers worn vibrating on acceleration', 'drive belt / variator rollers', 'Medium', (750, 1950), (0, 0)),
    ('Suspension', 'Front suspension fork leaking oil bottoming out over potholes', 'fork oil seals / fork oil', 'Medium', (650, 1800), (1400, 3600)),
    ('Suspension', 'Rear shock absorber squeaking and vehicle bouncing excessively', 'shock absorber replacement', 'Medium', (950, 2800), (2200, 5800)),
    ('Suspension', 'Handlebars misaligned handlebar turned sideways while going straight', 'fork alignment / T-stem adjustment', 'Low', (200, 550), (450, 1200)),
    ('Cooling System', 'Radiator coolant leaking green fluid pooling under engine bay', 'radiator hose / coolant topup', 'High', (450, 1400), (950, 2800)),
    ('Cooling System', 'Radiator cooling fan not spinning when engine heats up fan motor jammed', 'fan motor / relay fuse', 'High', (650, 1800), (1400, 3600)),
    ('General Maintenance', 'Periodic periodic general servicing engine oil filter chain and brake tune', 'engine oil / filters', 'Low', (450, 1400), (1800, 4200)),
    ('General Maintenance', 'Vehicle horn switch and pass light switch stuck with dust grime', 'switch cleaning / WD40 service', 'Low', (100, 250), (250, 600)),
]

# Generate 165 coherent, realistic records spanning 2026-09-17 08:30:00 to 2026-09-24 18:00:00
start_date = datetime.datetime(2026, 9, 17, 8, 30, 0)
end_date = datetime.datetime(2026, 9, 24, 18, 0, 0)
total_seconds = int((end_date - start_date).total_seconds())

random.seed(42)
records = []
total_records = 165

for i in range(total_records):
    # Determine vehicle type (56% bikes, 44% cars)
    rnd_type = random.random()
    if rnd_type < 0.56:
        v_type = 'bike'
        v_brand = random.choice(bike_brands)
        v_model = random.choice(bike_models[v_brand])
        v_age = random.randint(1, 10)
        km = random.randint(3000, 85000)
    else:
        v_type = 'car'
        v_brand = random.choice(car_brands)
        v_model = random.choice(car_models[v_brand])
        v_age = random.randint(1, 12)
        km = random.randint(8000, 140000)

    # Filter applicable symptoms
    applicable_symptoms = []
    for s in symptom_catalog:
        cat, sym, part, urgency, b_p, car_p = s
        if v_type == 'bike' and b_p != (0, 0):
            applicable_symptoms.append((cat, sym, part, urgency, b_p))
        elif v_type == 'car' and car_p != (0, 0):
            applicable_symptoms.append((cat, sym, part, urgency, car_p))

    chosen = random.choice(applicable_symptoms)
    cat, sym, part, urgency, price_range = chosen
    sym = COMMON_PROBLEMS[cat][i % len(COMMON_PROBLEMS[cat])]
    
    min_p, max_p = price_range
    # Calculate authentic North Indian market cost (with realistic small variance rounded to ₹50)
    actual_cost = round(random.uniform(min_p, max_p) / 50.0) * 50
    if actual_cost < min_p: actual_cost = min_p
    
    # Calculate timestamp evenly across 17-09-2026 to 24-09-2026
    offset_sec = int((i / (total_records - 1)) * total_seconds) + random.randint(-600, 600)
    offset_sec = max(0, min(total_seconds, offset_sec))
    ts = start_date + datetime.timedelta(seconds=offset_sec)
    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
    service_d_str = ts.strftime('%Y-%m-%d')

    records.append({
        'record_id': i + 1,
        'vehicle_type': v_type,
        'vehicle_brand': v_brand,
        'vehicle_model': v_model,
        'vehicle_age': v_age,
        'km_driven': km,
        'state': 'Global',
        'last_service_date': f'{random.randint(1, 12)} months ago',
        'previous_repair_history': random.choice(['none', 'general service', 'brake pads', 'oil change', 'battery replacement']),
        'symptoms': sym,
        'engine_warning_indicator': 'yes' if (cat in ['Engine', 'Cooling System', 'Starting System'] and random.random() > 0.4) else 'no',
        'recent_maintenance': random.choice(['oil change', 'brake tune', 'filters', 'none', 'greasing']),
        'parts_replaced': part,
        'problem_category': cat,
        'actual_repair_cost': actual_cost,
        'service_date': service_d_str,
        'timestamp': ts_str,
        'urgency': urgency
    })

# Write updated sample_service_records.csv
df = pd.DataFrame(records)
csv_cols = ['record_id', 'vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'state', 'last_service_date', 'previous_repair_history', 'symptoms', 'engine_warning_indicator', 'recent_maintenance', 'parts_replaced', 'problem_category', 'actual_repair_cost', 'service_date']
df[csv_cols].to_csv('backend/data/sample_service_records.csv', index=False)
print(f'Successfully generated {len(df)} records in sample_service_records.csv')

# Ensure database tables exist before updating SQLite service_center.db
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import db

db.init_db()

conn = db.get_db()
cursor = conn.cursor()

cursor.execute('DELETE FROM service_records')
for r in records:
    cursor.execute('''
        INSERT INTO service_records 
        (id, user_id, vehicle_type, vehicle_brand, vehicle_model, symptoms, predicted_category, urgency, actual_cost, timestamp)
        VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        r['record_id'],
        r['vehicle_type'],
        r['vehicle_brand'],
        r['vehicle_model'],
        r['symptoms'],
        r['problem_category'],
        r['urgency'],
        r['actual_repair_cost'],
        r['timestamp']
    ))
conn.commit()
print('SQLite database updated with all 165 records.')
conn.close()
