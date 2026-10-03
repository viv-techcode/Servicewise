"""Consistent text cleanup and vehicle-system cue features."""
import re


FAULT_CUES = {
    'Battery/Electrical': ('battery', 'alternator', 'headlight', 'indicator', 'horn', 'electrical', 'dashboard', 'power window', 'remote locking', 'air conditioner', 'compressor', 'fuse', 'voltage'),
    'Brake System': ('brake', 'handbrake', 'abs', 'stopping distance', 'brake pedal'),
    'Cooling System': ('coolant', 'radiator', 'temperature', 'thermostat', 'steam', 'overheat', 'cooling fan', 'coolant hose', 'temperature gauge'),
    'Engine': ('engine', 'knock', 'misfire', 'exhaust smoke', 'stall', 'oil consumption'),
    'Fuel System': ('fuel', 'petrol', 'injector', 'fuel economy', 'mileage', 'fuel line', 'fuel delivery'),
    'General Maintenance': ('routine service', 'periodic service', 'general inspection', 'maintenance', 'tune-up', 'overdue service'),
    'Starting System': ('starter', 'crank', 'starting', 'start', 'ignition switch', 'kick lever'),
    'Suspension': ('suspension', 'shock absorber', 'fork', 'pothole', 'bounces', 'vehicle leans'),
    'Transmission': ('clutch', 'gear', 'chain', 'sprocket', 'drive belt', 'variator', 'shifting', 'transmission'),
    'Tyres/Wheels': ('tyre', 'tire', 'wheel', 'puncture', 'rim', 'alignment', 'wobble', 'pressure loss'),
}

FAULT_SYMPTOMS = {
    'Battery/Electrical': (
        'headlights fade at idle and the battery needs frequent jump starts',
        'battery charge falls overnight despite a recent start',
        'the horn cuts in and out while dashboard lights flicker',
        'power windows slow down and the alternator warning lamp stays on',
        'the lights go dim at a stop and the battery is flat by morning',
        'battery keeps dying and the dash flickers when the fan comes on',
        'the alternator seems weak; headlights brighten when revved',
        'horn sounds faint and electricals act up after parking overnight',
    ),
    'Brake System': (
        'the brake pedal feels soft and stopping distance has increased',
        'a metallic scrape is heard whenever the brakes are applied',
        'the parking brake no longer holds on a slope',
        'the vehicle pulls sideways during firm braking',
        'brakes feel spongy and it takes longer to stop than before',
        'there is a scraping sound when I press the brake pedal',
        'handbrake will not keep the car still on a hill',
        'it veers left when braking hard; pedal feels odd',
    ),
    'Cooling System': (
        'coolant level keeps dropping and a puddle forms under the radiator',
        'engine temperature climbs in traffic and the cooling fan stays off',
        'steam appears near the radiator after a short drive',
        'the temperature gauge rises quickly on uphill roads',
        'coolant is disappearing and the motor runs hot in traffic',
        'radiator fan does not kick in; temperature climbs fast',
        'there is steam under the bonnet after a short ride',
        'temp needle shoots up on climbs and coolant smells sweet',
    ),
    'Engine': (
        'the engine misfires at idle and hesitates under acceleration',
        'a metallic knock gets louder when the engine is under load',
        'exhaust smoke persists and engine oil use has increased',
        'the engine stalls at stops and restarts after a short wait',
        'motor misses and jerks when I accelerate',
        'engine makes a knocking sound under load',
        'exhaust is smoky and it is using more oil lately',
        'car cuts out at signals, then starts again after a bit',
    ),
    'Fuel System': (
        'fuel economy has fallen and a strong petrol smell follows the vehicle',
        'the engine hesitates as if fuel delivery is restricted',
        'a damp fuel line and petrol smell are noticeable near the tank',
        'black exhaust smoke appears during acceleration',
        'petrol mileage has dropped and there is a fuel smell',
        'engine bogs down like it is not getting enough fuel',
        'fuel hose looks damp and smells strongly of petrol',
        'black smoke comes out when I open the throttle',
    ),
    'General Maintenance': (
        'routine oil and filter service is due along with a general inspection',
        'fluid checks and scheduled lubrication have been overdue for months',
        'the owner requests a preventive service and safety check',
        'the air filter is dirty and the regular tune-up is overdue',
        'it is due for an oil change and a basic check-over',
        'fluids and filters have been ignored for a while',
        'the owner wants a routine service before a long trip',
        'needs the usual tune-up; air filter looks clogged',
    ),
    'Starting System': (
        'the starter clicks repeatedly but the engine does not turn over',
        'cranking is slow on cold mornings despite a charged battery',
        'the ignition switch works only after several attempts',
        'the kick lever slips under pressure and will not crank the engine',
        'starter just clicks and the engine will not turn over',
        'slow crank on cold mornings even with a charged battery',
        'ignition takes a few tries before the motor starts',
        'kick start slips under my foot and will not turn the engine',
    ),
    'Suspension': (
        'the vehicle bounces after bumps and a rear shock squeaks',
        'front fork oil is leaking and the wheel bottoms out on potholes',
        'a clunk comes from the front end over speed breakers',
        'the handlebar sits off-centre while travelling straight',
        'it keeps bouncing after bumps and the rear shock squeaks',
        'front fork oil is leaking; wheel thumps into potholes',
        'clunk from the front when going over speed breakers',
        'bike wanders a bit and the handlebar looks crooked',
    ),
    'Transmission': (
        'gear changes grind and neutral is difficult to select',
        'the clutch slips on hills and the lever feels unusually stiff',
        'the drive chain jumps under load and rattles',
        'the scooter vibrates at take-off as if its drive belt is worn',
        'gears grind and finding neutral is a pain',
        'clutch slips going uphill and the lever feels stiff',
        'chain skips under load and rattles quite a lot',
        'scooter shudders when pulling away; belt may be worn',
    ),
    'Tyres/Wheels': (
        'the steering wheel vibrates at speed and a rim may be bent',
        'tyre pressure drops repeatedly and a slow leak is suspected',
        'the vehicle pulls to one side and tyre tread is wearing unevenly',
        'a tyre sidewall has a bulge after a pothole impact',
        'steering shakes at speed and one wheel may be bent',
        'tyre keeps going soft; could be a slow puncture',
        'it pulls to one side and the tread is wearing unevenly',
        'there is a lump on the tyre after hitting a pothole',
    ),
}

SHARED_AMBIGUOUS_SYMPTOMS = (
    'a vibration and faint rattling noise show up on the road, source is unclear',
    'it makes a noise and feels rough, especially over bumps',
    'performance has been poor lately; the vehicle feels weak and sounds different',
    'it will not start every time, sometimes there is only a click or short hum',
    'a repeated shake comes through the controls, but nothing obvious is loose',
    'there is an odd sound at the front and the ride feels unsettled',
    'sometimes it stalls or shudders; hard to tell what is causing it',
    'it pulls and vibrates, with a noise that changes depending on the road',
    'something feels off at low speed; noise and vibration come and go',
    'the vehicle is sluggish and makes an unfamiliar sound under load',
    'a clunk, shake, or hesitation happens now and then without a clear source',
    'gaadi feels rough and makes awaaz while moving, samajh nahi aa raha',
)

INFORMAL_NOISE_NOTES = (
    'pls check yaar', 'sometimes happens, sometimes nahin',
    'gaadi thodi jerk kar rahi hai', 'sound aa rahi hai, pls dekh lo',
    'not happening daily, bhai', 'temp high lagti hai',
    'start hi nahi hoti kabhi kabhi', 'light blink kar rahi hai',
    'vibration aa raha, check pls', 'noize on road; mechanic pls check',
    'chk asap, it is acting weird', 'vehcle shakes now n then',
    'plz inspect when free', 'thoda issue hai, please check',
)


def strip_secondary_hint(text):
    return re.sub(r';\s*also reports a related .*? concern\s*$', '', str(text), flags=re.I).strip()


def prepare_classifier_text(text):
    clean = strip_secondary_hint(text)
    lower = clean.lower()
    tags = []
    for category, terms in FAULT_CUES.items():
        if any(term in lower for term in terms):
            tags.append('cue_' + re.sub(r'[^a-z]+', '_', category.lower()).strip('_'))
    return clean + ' ' + ' '.join(tags)


def symptom_family(text):
    normalized = strip_secondary_hint(text).lower()
    normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def add_fault_symptoms(primary_text, secondary_faults, row_id):
    primary_text = strip_secondary_hint(primary_text).rstrip(' .!?')
    styles = (
        'Workshop intake: {symptom}.', 'Customer says, “{symptom}.”',
        'During the road test, {symptom}.', 'Short complaint: {symptom}.',
        'Rider’s note — {symptom}.', 'Vehicle owner reports {symptom}.',
        'Observed: {symptom}.', 'On a phone call, the owner says {symptom}.',
        'Mechanic wrote down: {symptom}.', 'The problem shows up as {symptom}.',
        'Customer wording: “{symptom}.”', 'Inspection note: {symptom}.',
        'Driver says {symptom}.', 'Lately, {symptom}.',
        'Noticed this: {symptom}.', 'It feels like this: {symptom}.',
        'In everyday words, {symptom}.', 'Roadside note — {symptom}.',
        'Complaint on arrival: {symptom}.', 'A quick check found that {symptom}.',
    )
    contexts = (
        'mostly on cold starts', 'in stop-and-go traffic', 'after a longer highway trip',
        'more often over recent weeks', 'once the vehicle warms up', 'on rough roads',
        'during everyday commuting', 'after rain', 'on some trips, then repeatedly',
        'when carrying a load', 'after parking overnight', 'even on short town trips',
        'at low speed', 'when the engine is under load', 'after sitting for a few hours',
        'while climbing a hill', 'when the lights are switched on', 'near the end of a trip',
        'with two people on board', 'after a cold night',
    )
    row_id = int(row_id)
    primary = styles[row_id % len(styles)].format(symptom=primary_text)
    context = contexts[(row_id // len(styles)) % len(contexts)]
    parts = [primary[:-1] + f' (especially {context}).']
    connectors = (
        'The driver also notices', 'At the same time,', 'Alongside that,',
        'In addition,', 'The owner also reports that', 'Separately,',
        'Another thing: ', 'There is also', 'On top of that,', 'They also mention',
    )
    for offset, category in enumerate(secondary_faults):
        phrases = FAULT_SYMPTOMS[category]
        phrase = phrases[(int(row_id) + offset * 3) % len(phrases)]
        connector = connectors[(int(row_id) + offset) % len(connectors)]
        parts.append(f"{connector} {phrase}.")
    return ' '.join(parts)
