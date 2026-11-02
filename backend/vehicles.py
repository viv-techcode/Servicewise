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


def is_supported_vehicle(vehicle_type, brand, model):
    return model in VEHICLES.get(vehicle_type, {}).get(brand, ())
