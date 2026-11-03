"""Shared fault cues and severity rules for generation and inference."""
import re

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
        'Battery/Electrical': ['battery charge will not hold', 'electrical power cuts out', 'battery repeatedly needs jump starts'],
        'Brake System': ['pedal sinks', 'stopping distance is longer', 'pedal travels farther', 'takes much longer to stop', 'takes longer to stop', 'brake pedal feels soft', 'brake lever feels soft'],
        'Cooling System': ['engine temperature rises', 'engine temperature keeps climbing', 'temperature rises in traffic', 'temperature gauge climbs', 'temperature gauge rises', 'temperature gauge still rises', 'radiator fan does not start', 'cooling fan cuts out'],
        'Engine': ['stalls at signals', 'stalls at traffic signals', 'engine misfires', 'engine misfires under load', 'misfire', 'loud engine knock', 'engine knocks', 'engine taps', 'engine taps under load', 'engine stalls', 'stalls every time'],
        'Fuel System': ['strong petrol smell'], 'Transmission': ['clutch slips', 'clutch slip is severe', 'clutch slip'],
        'Starting System': ['does not start after several', 'will not start after several', 'fails to start after repeated', 'still will not start', 'will not start after the battery was charged', 'start nahi ho rahi'],
        'Suspension': ['shock has failed', 'suspension bottoms out'],
        'Tyres/Wheels': ['bearing noise', 'wheel bearing hum'],
    },
    'category_medium_terms': {
        'Battery/Electrical': ['warning light', 'drops overnight', 'flicker', 'battery', 'electrical'],
        'Brake System': ['grinds', 'brake'], 'Cooling System': ['coolant', 'temperature'],
        'Engine': ['knock', 'knocks', 'misfire', 'misfires', 'hesitates', 'engine'], 'Fuel System': ['fuel', 'petrol'],
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
        'Battery/Electrical': ['headlamp beam is weak', 'headlamp is weak', 'headlights dim', 'headlight dim', 'dim headlight', 'dim lights', 'headlamp beam is weak', 'headlamp is weak'],
        'General Maintenance': ['oil and filter service is due', 'oil change due', 'oil change is due', 'oil and filter are due', 'oil and filter service is due', 'oil and filter service is due before', 'oil and filter service is due', 'scheduled oil change', 'no specific symptom described', 'regular service karani'],
        'Brake System': ['brake pads rub occasionally', 'soft squeak', 'squeak happens', 'squeal at low speed', 'squeaks but still stop normally', 'squeal under light pressure', 'squeak happens while parking', 'soft squeak', 'squeak', 'squeal', 'brake pads rub occasionally', 'brake pads rub while stopping'],
        'Tyres/Wheels': ['pressure drops slowly'],
    },
}

FAULT_CUES = {
    'Battery/Electrical': ('battery', 'alternator', 'electrical', 'headlight', 'headlights', 'headlamp', 'bulb', 'horn', 'dashboard', 'charge', 'voltage', 'wiring', 'fuse'),
    'Brake System': ('brake', 'brakes', 'braking', 'stopping', 'stop', 'abs', 'brake pedal', 'brake lever', 'pads', 'shoes'),
    'Cooling System': ('coolant', 'radiator', 'overheat', 'temperature', 'steam', 'cooling fan', 'cooling fin', 'cooling fins', 'engine heat', 'garam'),
    'Engine': ('engine bay', 'oil pressure', 'misfire', 'stall', 'exhaust smoke', 'burning smell', 'engine taps', 'engine knocks', 'engine misfires', 'engine knocks loudly'),
    'Fuel System': ('fuel', 'petrol', 'gasoline', 'injector', 'fuel line', 'fuel leak', 'petrol smell', 'fuel economy', 'mileage'),
    'General Maintenance': ('oil change', 'service', 'maintenance', 'filter', 'inspection', 'routine check', 'scheduled', 'check'),
    'Starting System': ('starter', 'statrer', 'crank', 'ignition', 'won\'t start', 'will not start', 'not starting', 'start nahi', 'fails to start', 'clicks when starting'),
    'Suspension': ('suspension', 'shock', 'shocks', 'shocks bounce', 'fork', 'forks', 'clunk', 'bounces', 'steering lock', 'steering locks', 'steering feels', 'vehicle leans', 'car leans', 'leans more than usual', 'handlebar', 'handlebars shake'),
    'Transmission': ('transmission', 'gear', 'clutch', 'cluch', 'chain', 'sprocket', 'drive belt', 'variator', 'gearbox', 'shifting', 'shift', 'cvt'),
    'Tyres/Wheels': ('tyre', 'tire', 'wheel', 'puncture', 'rim', 'sidewall', 'tyre burst', 'tire burst', 'pressure loss', 'wheel bearing'),
}

# Red flags are deliberately associated with one system. These patterns only
# escalate that fault and never lower the model's assigned severity.
RED_FLAG_RULES = {
    'Brake System': [(r'\bbrake failure\b', 'critical'), (r'\bno brakes?\b(?!\s+(?:failure|problem|issue|fault))', 'critical'), (r'\bbrakes? (?:are )?(?:not working|failed|fail(?:ed)?)\b', 'critical'), (r'\bbrake nahi lag\s*(?:ta|raha|rahi)\b', 'critical'), (r'\b(?:cannot|can\'t) stop\b', 'critical')],
    'Cooling System': [(r'\b(?:overheat(?:ing)?|temperature (?:is )?(?:red|critical|high)).{0,45}\bsteam\b', 'critical'), (r'\bsteam (?:is )?(?:coming|visible|pouring|pours|escapes)|\bsteam nikal\b', 'critical'), (r'\bengine (?:is )?overheat(?:ing)? rapidly\b', 'critical'), (r'\bgaadi garam ho rahi\b.{0,30}\bsteam\b', 'critical')],
    'Fuel System': [(r'\b(?:fuel|petrol|gasoline) (?:is )?(?:leaking heavily|leak(?:ing)? badly|pouring)\b', 'critical'), (r'\bpetrol (?:smell|odor)\b.{0,35}\bsmoke\b', 'critical'), (r'\bstrong petrol smell\b', 'high')],
    'Engine': [(r'\boil pressure (?:warning|light)\b.{0,40}\b(?:knock|noise|smoke)\b', 'critical'), (r'\bengine (?:is )?burning\b', 'critical'), (r'\bburning smell\b', 'high')],
    'Battery/Electrical': [(r'\b(?:electrical|wiring|battery) (?:is )?burning\b', 'critical'), (r'\bburning smell\b', 'high')],
    'Tyres/Wheels': [(r'\b(?:tyre|tire) (?:has )?(?:burst|blown|blowout|blew out)\b', 'critical'), (r'\bsidewall (?:burst|blowout|split)\b', 'critical')],
    'Suspension': [(r'\bsteering (?:has )?locked\b', 'critical'), (r'\bsteering lock(?:ed|s)?\b', 'high')],
}

LEVEL_RANK = {name: i for i, name in enumerate(SEVERITY_RULE_TABLE['levels'])}
_SPLIT_RE = re.compile(r'(?:[.!?;]+|\bbut\b|\bwhile\b|\balso\b|\band\b)', re.I)
_NEGATION_RE = re.compile(r'\b(?:no|not|never|without|isn\'t|aren\'t|wasn\'t|weren\'t|doesn\'t|didn\'t|don\'t)\b', re.I)


def split_symptom_clauses(text: str):
    return [part.strip() for part in _SPLIT_RE.split(str(text)) if part.strip()]


def _normalize(text: str) -> str:
    value = str(text).lower()
    # Common typing variants found in customer complaints.
    for wrong, right in {'brke':'brake', 'braks':'brakes', 'overheatng':'overheating', 'overheatin':'overheating', 'steem':'steam', 'petorl':'petrol', 'smel':'smell', 'tyer':'tyre', 'battrey':'battery', 'engin':'engine', 'cluch':'clutch'}.items():
        value = re.sub(rf'\b{wrong}\b', right, value)
    return value


def _term_matches(text: str, term: str):
    return re.search(rf'(?<!\w){re.escape(term)}(?!\w)', text, re.I)


def _is_negated(text: str, match, positive_no_phrase=False) -> bool:
    if positive_no_phrase:
        return False
    prefix = text[max(0, match.start() - 32):match.start()]
    # “No smoke” is a negation; “no brakes” and “brakes not working” are red flags.
    if re.search(r'\bno\s+(?:visible\s+)?$', prefix):
        return True
    if re.search(r'\b(?:no|not|never|without|isn\'t|aren\'t|doesn\'t|didn\'t|don\'t)\s+(?:\w+\s+){0,2}$', prefix):
        return True
    return False


def detect_fault_categories(text: str):
    normalized = _normalize(text)
    detected = set()
    for clause in split_symptom_clauses(normalized):
        for category, cues in FAULT_CUES.items():
            if any((m := _term_matches(clause, cue)) and not _is_negated(clause, m) for cue in cues):
                detected.add(category)
        if re.search(r'\bengine\b', clause) and re.search(r'\b(?:knock|knocks|knocking|taps|tap|misfire|misfires|misfiring|stall|stalls|stalled|oil pressure|exhaust smoke|rough idle|uneven idle|burning smell)\b', clause):
            detected.add('Engine')
    detected.update(detect_red_flag_faults(normalized))
    return detected


def detect_red_flag_faults(text: str):
    normalized = _normalize(text)
    found = set()
    for category, rules in RED_FLAG_RULES.items():
        for pattern, _ in rules:
            for match in re.finditer(pattern, normalized, re.I):
                negated = _is_negated(normalized, match, positive_no_phrase=pattern.find('no\\s') >= 0)
                if 'smoke' in match.group(0) and re.search(r'\b(?:no|not|without)\s+(?:\w+\s+){0,2}smoke\b', normalized): negated = True
                if 'steam' in match.group(0) and re.search(r'\b(?:no|not|without)\s+(?:\w+\s+){0,2}steam\b', normalized): negated = True
                if not negated: found.add(category)
    return found


def severity_for_fault(category: str, symptom: str) -> str:
    text = _normalize(symptom)
    clauses = split_symptom_clauses(text)
    cues = FAULT_CUES.get(category, ())
    relevant = [clause for clause in clauses if any(_term_matches(clause, cue) for cue in cues)]
    if not relevant:
        relevant = clauses
    result = SEVERITY_RULE_TABLE['category_baseline'][category]
    low_terms = SEVERITY_RULE_TABLE.get('category_low_terms', {}).get(category, [])
    has_low = any(_term_matches(text, _normalize(term)) for term in low_terms)
    if has_low:
        result = 'low'
    if any(_term_matches(clause, term) and not _is_negated(clause, _term_matches(clause,term))
           for clause in relevant for term in SEVERITY_RULE_TABLE.get('category_low_terms', {}).get(category, [])):
        result = 'low'
    for clause in relevant:
        low_hit = any((m := _term_matches(clause, term)) and not _is_negated(clause, m)
                      for term in SEVERITY_RULE_TABLE.get('category_low_terms', {}).get(category, []))
        clause_level = 'low' if has_low else result
        for level, table_name in (('medium','category_medium_terms'),('high','category_high_terms'),('critical','category_critical_terms')):
            if has_low and level == 'medium':
                continue
            for term in SEVERITY_RULE_TABLE.get(table_name, {}).get(category, []):
                match = _term_matches(clause, _normalize(term))
                if match and not _is_negated(clause, match):
                    if LEVEL_RANK[level] > LEVEL_RANK[clause_level]: clause_level = level
        for pattern, level in RED_FLAG_RULES.get(category, []):
            for match in re.finditer(pattern, clause, re.I):
                negated = _is_negated(clause, match, positive_no_phrase=pattern.find('no\\s') >= 0)
                # A red flag explicitly denied in the same clause is not evidence.
                if 'smoke' in match.group(0) and re.search(r'\b(?:no|not|without)\s+(?:\w+\s+){0,2}smoke\b', clause): negated = True
                if 'steam' in match.group(0) and re.search(r'\b(?:no|not|without)\s+(?:\w+\s+){0,2}steam\b', clause): negated = True
                if not negated and LEVEL_RANK[level] > LEVEL_RANK[clause_level]: clause_level = level
        if LEVEL_RANK[clause_level] > LEVEL_RANK[result]: result = clause_level
    return result


def combined_severity(faults, severity_map):
    levels = SEVERITY_RULE_TABLE['levels']
    index = max(levels.index(severity_map[fault]) for fault in faults)
    fault_set = set(faults)
    if any(set(pair).issubset(fault_set) for pair in SEVERITY_RULE_TABLE['dangerous_combinations']):
        index += SEVERITY_RULE_TABLE['dangerous_combo_increase']
    if len(faults) == 3:
        index += SEVERITY_RULE_TABLE['three_fault_increase']
    return levels[min(index, len(levels) - 1)]

