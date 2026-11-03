"""Rule-based per-fault and combined severity shared by generation and API."""

# Escalation rules are part of the generated data contract.
SEVERITY_RULE_TABLE = {
    'levels': ['low', 'medium', 'high', 'critical'],
    'category_baseline': {
        'Battery/Electrical': 'medium', 'Brake System': 'medium', 'Cooling System': 'medium',
        'Engine': 'medium', 'Fuel System': 'medium', 'General Maintenance': 'low',
        'Starting System': 'medium', 'Suspension': 'medium', 'Transmission': 'medium',
        'Tyres/Wheels': 'low',
    },
    'critical_terms': ['brake failure', 'fuel is leaking heavily', 'overheating rapidly', 'oil pressure warning', 'sidewall blowout'],
    'high_terms': ['pedal sinks', 'stopping distance is longer', 'engine temperature rises', 'steam is visible', 'strong petrol smell', 'stalls at signals', 'clutch slips', 'does not start after several', 'bearing noise'],
    'medium_terms': ['warning light', 'drops overnight', 'flicker', 'grinds', 'misfires', 'hesitates', 'knock', 'coolant', 'slowly drops', 'vibrates', 'clunks', 'stiff when shifting'],
    'category_critical_terms': {
        'Brake System': ['brake failure'], 'Cooling System': ['overheating rapidly'],
        'Engine': ['oil pressure warning'], 'Fuel System': ['fuel is leaking heavily'],
        'Tyres/Wheels': ['sidewall blowout'],
    },
    'category_high_terms': {
        'Brake System': ['pedal sinks', 'stopping distance is longer'],
        'Cooling System': ['engine temperature rises', 'steam is visible'],
        'Engine': ['stalls at signals', 'engine misfires', 'loud engine knock'],
        'Fuel System': ['strong petrol smell'], 'Transmission': ['clutch slips'],
        'Starting System': ['does not start after several'], 'Tyres/Wheels': ['bearing noise'],
    },
    'category_medium_terms': {
        'Battery/Electrical': ['warning light', 'drops overnight', 'flicker', 'battery', 'electrical'],
        'Brake System': ['grinds', 'brake'], 'Cooling System': ['coolant', 'temperature'],
        'Engine': ['knock', 'misfires', 'hesitates', 'engine'], 'Fuel System': ['fuel', 'petrol'],
        'General Maintenance': ['oil', 'filter', 'service', 'maintenance', 'inspection'],
        'Starting System': ['starter', 'start', 'ignition', 'crank'],
        'Suspension': ['shock', 'suspension', 'clunk', 'bounces'],
        'Transmission': ['gear', 'belt', 'chain', 'transmission'],
        'Tyres/Wheels': ['wheel vibrates'],
    },
    'dangerous_combinations': [
        ['Brake System', 'Tyres/Wheels'], ['Brake System', 'Suspension'],
        ['Cooling System', 'Engine'], ['Fuel System', 'Engine'],
    ],
    'dangerous_combo_increase': 1,
    'three_fault_increase': 1,
    'category_low_terms': {
        'Battery/Electrical': ['headlights dim', 'headlight dim', 'dim headlight', 'dim lights'],
        'General Maintenance': ['oil change due', 'oil and filter are due', 'scheduled oil change', 'no specific symptom described'],
        'Brake System': ['squeal at low speed', 'squeaks but still stop normally'],
        'Tyres/Wheels': ['pressure drops slowly'],
    },
}


def severity_for_fault(category: str, symptom: str) -> str:
    text = symptom.lower()
    if any(term in text for term in SEVERITY_RULE_TABLE.get('category_low_terms', {}).get(category, [])):
        return 'low'
    if any(term in text for term in SEVERITY_RULE_TABLE['category_critical_terms'].get(category, [])):
        return 'critical'
    if any(term in text for term in SEVERITY_RULE_TABLE['category_high_terms'].get(category, [])):
        return 'high'
    if any(term in text for term in SEVERITY_RULE_TABLE['category_medium_terms'].get(category, [])):
        return 'medium'
    return SEVERITY_RULE_TABLE['category_baseline'][category]


def combined_severity(faults, severity_map):
    levels = SEVERITY_RULE_TABLE['levels']
    index = max(levels.index(severity_map[fault]) for fault in faults)
    fault_set = set(faults)
    if any(set(pair).issubset(fault_set) for pair in SEVERITY_RULE_TABLE['dangerous_combinations']):
        index += SEVERITY_RULE_TABLE['dangerous_combo_increase']
    if len(faults) == 3:
        index += SEVERITY_RULE_TABLE['three_fault_increase']
    return levels[min(index, len(levels) - 1)]

