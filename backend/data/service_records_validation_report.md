# ServiceWise prepared dataset validation report

Table rows: 3000.

## Primary fault counts

| Primary fault | Rows |
|---|---:|
| Battery/Electrical | 300 |
| Brake System | 300 |
| Cooling System | 300 |
| Engine | 300 |
| Fuel System | 300 |
| General Maintenance | 300 |
| Starting System | 300 |
| Suspension | 300 |
| Transmission | 300 |
| Tyres/Wheels | 300 |

## Checks

- Null cells: 9034.
- Exact duplicate rows: 0.
- Duplicate record IDs: 0.
- Multi-fault rows: 1200.
- Parts/labour sum mismatches: 0.
- All region values are Global; all vehicles match the active catalog.

## Files

- `service_records_balanced_3000.csv`
- `service_records_validation_report.md`
- `prepare_service_dataset.py`
