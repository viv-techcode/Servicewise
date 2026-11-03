"""Vehicle catalog shared by the API, dataset builder, and feedback training."""

VEHICLES = {
    'bike': {
        'Hero': ('Splendor Plus', 'HF Deluxe'),
        'Honda': ('Shine 125', 'Activa 6G'),
        'TVS': ('Jupiter 110',),
    },
    'car': {
        'Maruti Suzuki': ('Swift', 'WagonR', 'Alto K10'),
        'Hyundai': ('i20',),
        'Tata': ('Tiago',),
    },
}

# Physical facts used by data generation, validation, inventory compatibility,
# and the UI's mirrored catalogue. Values are intentionally conservative.
MODEL_FACTS = {
    'Splendor Plus': {'launch_year': 2004, 'body': 'geared_bike', 'drivetrain': 'manual', 'cooling': 'air', 'has_chain': True, 'has_clutch_lever': False, 'has_radiator': False, 'price_tier': 'budget'},
    'HF Deluxe': {'launch_year': 2005, 'body': 'geared_bike', 'drivetrain': 'manual', 'cooling': 'air', 'has_chain': True, 'has_clutch_lever': False, 'has_radiator': False, 'price_tier': 'budget'},
    'Shine 125': {'launch_year': 2006, 'body': 'geared_bike', 'drivetrain': 'manual', 'cooling': 'air', 'has_chain': True, 'has_clutch_lever': True, 'has_radiator': False, 'price_tier': 'budget'},
    'Activa 6G': {'launch_year': 2020, 'body': 'scooter', 'drivetrain': 'CVT', 'cooling': 'air', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': False, 'price_tier': 'mid'},
    'Jupiter 110': {'launch_year': 2013, 'body': 'scooter', 'drivetrain': 'CVT', 'cooling': 'air', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': False, 'price_tier': 'mid'},
    'Swift': {'launch_year': 2005, 'body': 'car', 'drivetrain': 'manual_or_AMT', 'cooling': 'liquid', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': True, 'price_tier': 'mid'},
    'WagonR': {'launch_year': 1999, 'body': 'car', 'drivetrain': 'manual_or_AMT', 'cooling': 'liquid', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': True, 'price_tier': 'budget'},
    'Alto K10': {'launch_year': 2010, 'body': 'car', 'drivetrain': 'manual_or_AMT', 'cooling': 'liquid', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': True, 'price_tier': 'budget'},
    'i20': {'launch_year': 2008, 'body': 'car', 'drivetrain': 'manual_or_AMT', 'cooling': 'liquid', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': True, 'price_tier': 'mid'},
    'Tiago': {'launch_year': 2016, 'body': 'car', 'drivetrain': 'manual_or_AMT', 'cooling': 'liquid', 'has_chain': False, 'has_clutch_lever': False, 'has_radiator': True, 'price_tier': 'budget'},
}

assert {model for brands in VEHICLES.values() for models in brands.values() for model in models} == set(MODEL_FACTS)


def is_supported_vehicle(vehicle_type, brand, model):
    return model in VEHICLES.get(vehicle_type, {}).get(brand, ())
