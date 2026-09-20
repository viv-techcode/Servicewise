import random, datetime, json
import pandas as pd
import sqlite3

# Define authentic North India repair price benchmarks & standard realistic diagnostic templates
# (Cycles, 2-wheelers / Bikes / Scooters, 4-wheelers / Cars)

cycle_brands = ['Hero Cycles', 'Atlas', 'Avon', 'Hercules', 'BSA', 'Firefox', 'Leader']
cycle_models = {
    'Hero Cycles': ['Hero Jet', 'Hero Sprint', 'Hero Ranger', 'Hero Kyoto', 'Hero Impact'],
    'Atlas': ['Atlas Goldline', 'Atlas Ultimate', 'Atlas Motion'],
    'Avon': ['Avon Prime', 'Avon Element', 'Avon Star', 'Avon Colt'],
    'Hercules': ['Hercules Roadeo', 'Hercules Streetcat', 'Hercules Captain'],
    'BSA': ['BSA SLR', 'BSA Mach', 'BSA Champ'],
    'Firefox': ['Firefox Target', 'Firefox Grunge', 'Firefox Cyclone'],
    'Leader': ['Leader Scout', 'Leader Beast', 'Leader Gladiator']
}

bike_brands = ['Hero', 'Honda', 'Bajaj', 'TVS', 'Royal Enfield', 'Yamaha', 'Suzuki']
bike_models = {
    'Hero': ['Splendor Plus', 'HF Deluxe', 'Passion Pro', 'Glamour', 'Xtreme 160R'],
    'Honda': ['Activa 6G', 'Shine 125', 'SP 125', 'Dio', 'Unicorn'],
    'Bajaj': ['Pulsar 150', 'Pulsar NS200', 'Platina 100', 'CT 100', 'Avenger 220'],
    'TVS': ['Jupiter 110', 'Apache RTR 160', 'Raider 125', 'XL 100 Heavy Duty', 'NTorq 125'],
    'Royal Enfield': ['Classic 350', 'Bullet 350', 'Hunter 350', 'Meteor 350', 'Himalayan'],
    'Yamaha': ['FZ-S V3', 'MT-15 V2', 'R15 V4', 'RayZR 125'],
    'Suzuki': ['Access 125', 'Burgman Street', 'Gixxer 150']
}

car_brands = ['Maruti Suzuki', 'Hyundai', 'Tata', 'Mahindra', 'Kia', 'Toyota', 'Renault']
car_models = {
    'Maruti Suzuki': ['WagonR', 'Swift', 'Dzire', 'Baleno', 'Brezza', 'Ertiga', 'Alto K10'],
    'Hyundai': ['i20', 'Creta', 'Venue', 'Grand i10 Nios', 'Verna'],
    'Tata': ['Nexon', 'Punch', 'Altroz', 'Tiago', 'Harrier'],
    'Mahindra': ['Bolero', 'Scorpio-N', 'XUV700', 'Thar', 'XUV300'],
    'Kia': ['Seltos', 'Sonet', 'Carens'],
    'Toyota': ['Innova Crysta', 'Fortuner', 'Urban Cruiser Hyryder', 'Glanza'],
    'Renault': ['Kwid', 'Triber', 'Kiger']
}

symptom_catalog = [
    # Tyres & Wheels
    ('Tyres/Wheels', 'Tyre puncture with visible nail and rapid loss of air pressure', 'tyre tube/puncture strip', 'Low',
     (50, 150), (80, 200), (150, 350)),
    ('Tyres/Wheels', 'Low tyre pressure losing air frequently every 2 days valve leaking', 'valve pin/air valve', 'Low',
     (40, 100), (60, 150), (100, 250)),
    ('Tyres/Wheels', 'Vehicle pulling to left uneven tyre tread wear wheel alignment needed', 'alignment balancing weight', 'Medium',
     (60, 150), (250, 600), (450, 1200)),
    ('Tyres/Wheels', 'Steering wheel and handlebar vibrating heavily at high speed bent rim', 'rim trueing / wheel balancing', 'Medium',
     (100, 250), (350, 800), (700, 1800)),
    ('Tyres/Wheels', 'Tyre sidewall bulge after hitting pothole tyre replacement needed', 'new tyre/tube', 'High',
     (250, 650), (1200, 2400), (2800, 5500)),
     
    # Lights & Electrical
    ('Battery/Electrical', 'Headlight beam very dim and indicator flasher blinking too fast', 'headlight bulb/relay', 'Low',
     (40, 120), (150, 450), (350, 950)),
    ('Battery/Electrical', 'Vehicle horn completely dead or making weak croaking sound', 'horn/horn switch', 'Low',
     (60, 150), (180, 450), (400, 1100)),
    ('Battery/Electrical', 'Car AC not cooling vents throwing warm air AC gas low compressor cut off', 'AC gas topup / cabin filter', 'Medium',
     (0, 0), (0, 0), (1500, 3800)),
    ('Battery/Electrical', 'Battery warning light glowing alternator charging issue cluster flickering', 'alternator relay/fuse', 'High',
     (0, 0), (450, 1400), (1200, 3500)),
    ('Battery/Electrical', 'Power window not rolling up central locking key remote unresponsive', 'window motor/key battery', 'Low',
     (0, 0), (0, 0), (500, 1800)),

    # Starting & Battery
    ('Starting System', 'Self starter clicking sound but engine will not crank battery drained', 'battery jump/relay', 'High',
     (0, 0), (800, 2400), (1800, 4500)),
    ('Starting System', 'Engine cranking very slowly for 10 seconds before starting cold start issue', 'spark plug/starter carbon', 'Medium',
     (0, 0), (350, 950), (750, 2200)),
    ('Starting System', 'Kick starter slipping or jammed no compression on bike', 'kick ratchet gear', 'Medium',
     (80, 200), (250, 600), (0, 0)),
    ('Starting System', 'Electric e-bike cycle throttle not engaging battery cut off', 'throttle switch/bldc fuse', 'Medium',
     (250, 700), (450, 1500), (0, 0)),

    # Brake System
    ('Brake System', 'Brakes screeching loud metallic grinding noise brake pads worn down', 'brake pads/brake shoes', 'High',
     (60, 180), (350, 950), (1100, 2800)),
    ('Brake System', 'Brake pedal going deep down spongy feel without stopping power air in lines', 'brake fluid flush/bleeding', 'High',
     (50, 120), (250, 650), (600, 1600)),
    ('Brake System', 'Disc brake lever vibrating violently disc rotor warped or glazed', 'disc rotor machining/pads', 'Medium',
     (100, 250), (600, 1800), (1500, 3800)),
    ('Brake System', 'Handbrake parking brake not holding vehicle on slope loose brake cable', 'handbrake cable adjustment', 'Medium',
     (40, 100), (150, 350), (350, 900)),

    # Engine
    ('Engine', 'Engine overheating rapidly temperature gauge in red steam from bonnet', 'thermostat / head gasket check', 'High',
     (0, 0), (1500, 4500), (2800, 7500)),
    ('Engine', 'Engine knocking and metallic pinging sound under load tappet clearance loose', 'tappet adjustment / oil flush', 'High',
     (0, 0), (600, 1800), (1800, 5200)),
    ('Engine', 'Engine misfiring jerking severely during acceleration fouled spark plugs', 'spark plugs / ignition coil', 'Medium',
     (0, 0), (350, 1100), (850, 2600)),
    ('Engine', 'Heavy white or bluish smoke coming continuously from exhaust burning engine oil', 'piston rings / valve seals', 'High',
     (0, 0), (3000, 7500), (6500, 16000)),
    ('Engine', 'Check engine light glowing loss of pickup and engine stuttering at idle', 'sensor cleaning / OBD scan', 'Medium',
     (0, 0), (400, 1200), (800, 2500)),

    # Fuel System
    ('Fuel System', 'Drop in fuel mileage running very rich with strong petrol smell from exhaust', 'carburettor/injector clean', 'Medium',
     (0, 0), (350, 950), (900, 2400)),
    ('Fuel System', 'Fuel pipe leaking petrol near fuel pump filter cracked', 'fuel pipe / fuel filter', 'High',
     (0, 0), (180, 550), (450, 1200)),
    ('Fuel System', 'Black soot smoke during sudden acceleration clogged air filter', 'air filter / choke clean', 'Low',
     (0, 0), (200, 500), (450, 1100)),

    # Transmission
    ('Transmission', 'Gears slipping hard to shift into gear grinding gear noise', 'clutch plates / gear oil', 'High',
     (0, 0), (1200, 3200), (3500, 9500)),
    ('Transmission', 'Bicycle or motorcycle chain loose slipping off teeth dry squeaking', 'chain adjustment / sprocket kit', 'Medium',
     (60, 180), (350, 1200), (0, 0)),
    ('Transmission', 'Clutch lever extremely tight and hard to press stiff clutch cable', 'clutch cable replacement', 'Low',
     (40, 120), (150, 450), (350, 950)),
    ('Transmission', 'Scooter drive belt and variator rollers worn vibrating on acceleration', 'drive belt / variator rollers', 'Medium',
     (0, 0), (750, 1950), (0, 0)),

    # Suspension
    ('Suspension', 'Front suspension fork leaking oil bottoming out over potholes', 'fork oil seals / fork oil', 'Medium',
     (80, 220), (650, 1800), (1400, 3600)),
    ('Suspension', 'Rear shock absorber squeaking and vehicle bouncing excessively', 'shock absorber replacement', 'Medium',
     (100, 300), (950, 2800), (2200, 5800)),
    ('Suspension', 'Handlebars misaligned handlebar turned sideways while going straight', 'fork alignment / T-stem adjustment', 'Low',
     (50, 150), (200, 550), (450, 1200)),

    # Cooling System
    ('Cooling System', 'Radiator coolant leaking green fluid pooling under engine bay', 'radiator hose / coolant topup', 'High',
     (0, 0), (450, 1400), (950, 2800)),
    ('Cooling System', 'Radiator cooling fan not spinning when engine heats up fan motor jammed', 'fan motor / relay fuse', 'High',
     (0, 0), (650, 1800), (1400, 3600)),

    # General Maintenance
    ('General Maintenance', 'Periodic periodic general servicing engine oil filter chain and brake tune', 'engine oil / filters', 'Low',
     (100, 250), (450, 1400), (1800, 4200)),
    ('General Maintenance', 'Cycle bottom bracket pedal crank creaking on rotation loose bearings', 'ball bearings & greasing', 'Low',
     (80, 220), (0, 0), (0, 0)),
    ('General Maintenance', 'Vehicle horn switch and pass light switch stuck with dust grime', 'switch cleaning / WD40 service', 'Low',
     (30, 80), (100, 250), (250, 600))
]

# Generate 165 coherent, realistic records spanning 2026-09-17 08:30:00 to 2026-09-24 18:00:00
start_date = datetime.datetime(2026, 9, 17, 8, 30, 0)
end_date = datetime.datetime(2026, 9, 24, 18, 0, 0)
total_seconds = int((end_date - start_date).total_seconds())

random.seed(42)
records = []
total_records = 165

for i in range(total_records):
    # Determine vehicle type (20% cycles, 45% bikes, 35% cars)
    rnd_type = random.random()
    if rnd_type < 0.20:
        v_type = 'cycle'
        v_brand = random.choice(cycle_brands)
        v_model = random.choice(cycle_models[v_brand])
        v_age = random.randint(1, 6)
        km = random.randint(300, 4500)
    elif rnd_type < 0.65:
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
        cat, sym, part, urgency, c_p, b_p, car_p = s
        if v_type == 'cycle' and c_p != (0, 0):
            applicable_symptoms.append((cat, sym, part, urgency, c_p))
        elif v_type == 'bike' and b_p != (0, 0):
            applicable_symptoms.append((cat, sym, part, urgency, b_p))
        elif v_type == 'car' and car_p != (0, 0):
            applicable_symptoms.append((cat, sym, part, urgency, car_p))

    chosen = random.choice(applicable_symptoms)
    cat, sym, part, urgency, price_range = chosen
    
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
        'last_service_date': f'{random.randint(1, 12)} months ago',
        'previous_repair_history': random.choice(['none', 'general service', 'brake pads', 'oil change', 'battery replacement']),
        'symptoms': sym,
        'engine_warning_indicator': 'yes' if (cat in ['Engine', 'Cooling System', 'Starting System'] and v_type != 'cycle' and random.random() > 0.4) else 'no',
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
csv_cols = ['record_id', 'vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_age', 'km_driven', 'last_service_date', 'previous_repair_history', 'symptoms', 'engine_warning_indicator', 'recent_maintenance', 'parts_replaced', 'problem_category', 'actual_repair_cost', 'service_date']
df[csv_cols].to_csv('backend/data/sample_service_records.csv', index=False)
print(f'Successfully generated {len(df)} records in sample_service_records.csv')

# Rewrite SQLite service_center.db
conn = sqlite3.connect('backend/data/service_center.db')
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
