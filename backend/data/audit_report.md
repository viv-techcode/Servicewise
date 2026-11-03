# Dataset audit details

Rows: 5033; stock SKUs: 63; ledger events: 14964; vague/typo/Hinglish proxy share: 10.2%.

## Median job charge vs reference range
| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |
|---|---:|---:|---:|---:|---:|
| Battery/Electrical | bike | 252 | 2672 | n/a | n/a |
| Battery/Electrical | car | 292 | 5342 | 3029.5 | 4469.5 |
| Brake System | bike | 218 | 303 | 224.0 | 299.0 |
| Brake System | car | 315 | 3322 | 600.0 | 2729.5 |
| Cooling System | bike | 180 | 882 | n/a | n/a |
| Cooling System | car | 278 | 1528 | 685.0 | 1420.0 |
| Engine | bike | 216 | 3572 | n/a | n/a |
| Engine | car | 294 | 7532 | 8500.0 | 18000.0 |
| Fuel System | bike | 125 | 523 | n/a | n/a |
| Fuel System | car | 173 | 935 | 560.0 | 810.0 |
| General Maintenance | bike | 507 | 1866 | n/a | n/a |
| General Maintenance | car | 587 | 3542 | 1599.0 | 5499.0 |
| Starting System | bike | 180 | 1860 | n/a | n/a |
| Starting System | car | 225 | 3606 | n/a | n/a |
| Suspension | bike | 165 | 3782 | n/a | n/a |
| Suspension | car | 239 | 7998 | 800.0 | n/a |
| Transmission | bike | 115 | 1024 | n/a | n/a |
| Transmission | car | 159 | 1761 | 925.0 | 1550.0 |
| Tyres/Wheels | bike | 219 | 3929 | n/a | n/a |
| Tyres/Wheels | car | 294 | 7830 | 399.5 | 10299.0 |

## Bike-to-car median job charge
| Fault | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 2672 | 5342 | 0.50 |
| Brake System | 303 | 3322 | 0.09 |
| Cooling System | 882 | 1528 | 0.58 |
| Engine | 3572 | 7532 | 0.47 |
| Fuel System | 523 | 935 | 0.56 |
| General Maintenance | 1866 | 3542 | 0.53 |
| Starting System | 1860 | 3606 | 0.52 |
| Suspension | 3782 | 7998 | 0.47 |
| Transmission | 1024 | 1761 | 0.58 |
| Tyres/Wheels | 3929 | 7830 | 0.50 |
## Combined severity distribution by primary fault
| Fault | Severity | Jobs |
|---|---|---:|
| Battery/Electrical | critical | 10 |
| Battery/Electrical | high | 113 |
| Battery/Electrical | low | 98 |
| Battery/Electrical | medium | 323 |
| Brake System | critical | 194 |
| Brake System | high | 103 |
| Brake System | low | 40 |
| Brake System | medium | 196 |
| Cooling System | critical | 71 |
| Cooling System | high | 80 |
| Cooling System | medium | 307 |
| Engine | critical | 147 |
| Engine | high | 176 |
| Engine | medium | 187 |
| Fuel System | critical | 84 |
| Fuel System | high | 63 |
| Fuel System | medium | 151 |
| General Maintenance | critical | 1 |
| General Maintenance | high | 9 |
| General Maintenance | low | 372 |
| General Maintenance | medium | 712 |
| Starting System | critical | 12 |
| Starting System | high | 113 |
| Starting System | medium | 280 |
| Suspension | critical | 20 |
| Suspension | high | 110 |
| Suspension | medium | 274 |
| Transmission | critical | 2 |
| Transmission | high | 48 |
| Transmission | medium | 224 |
| Tyres/Wheels | critical | 12 |
| Tyres/Wheels | high | 109 |
| Tyres/Wheels | low | 291 |
| Tyres/Wheels | medium | 101 |

## Per-fault severity distribution
| Fault | Severity | Fault instances |
|---|---|---:|
| Battery/Electrical | high | 112 |
| Battery/Electrical | low | 166 |
| Battery/Electrical | medium | 424 |
| Brake System | critical | 169 |
| Brake System | high | 125 |
| Brake System | low | 107 |
| Brake System | medium | 315 |
| Cooling System | critical | 60 |
| Cooling System | high | 105 |
| Cooling System | medium | 504 |
| Engine | critical | 100 |
| Engine | high | 168 |
| Engine | medium | 320 |
| Fuel System | critical | 77 |
| Fuel System | high | 84 |
| Fuel System | medium | 341 |
| General Maintenance | low | 440 |
| General Maintenance | medium | 866 |
| Starting System | high | 133 |
| Starting System | medium | 435 |
| Suspension | high | 82 |
| Suspension | medium | 432 |
| Transmission | high | 51 |
| Transmission | medium | 429 |
| Tyres/Wheels | high | 117 |
| Tyres/Wheels | low | 524 |
| Tyres/Wheels | medium | 123 |

## Fault category by service month
| Fault | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Battery/Electrical | 76 | 61 | 36 | 44 | 71 | 61 | 74 | 68 | 59 | 76 | 29 | 47 |
| Brake System | 71 | 59 | 60 | 82 | 51 | 66 | 71 | 58 | 67 | 73 | 32 | 26 |
| Cooling System | 31 | 34 | 36 | 85 | 121 | 99 | 57 | 42 | 57 | 51 | 27 | 29 |
| Engine | 60 | 54 | 54 | 63 | 46 | 42 | 57 | 53 | 50 | 62 | 29 | 18 |
| Fuel System | 41 | 34 | 40 | 57 | 47 | 44 | 54 | 48 | 41 | 54 | 26 | 16 |
| General Maintenance | 90 | 79 | 104 | 98 | 129 | 126 | 143 | 115 | 131 | 157 | 90 | 44 |
| Starting System | 51 | 53 | 31 | 34 | 42 | 51 | 64 | 55 | 54 | 68 | 22 | 43 |
| Suspension | 40 | 32 | 46 | 51 | 44 | 39 | 59 | 51 | 46 | 59 | 25 | 22 |
| Transmission | 27 | 28 | 35 | 30 | 39 | 44 | 69 | 54 | 50 | 51 | 29 | 24 |
| Tyres/Wheels | 59 | 56 | 54 | 69 | 54 | 65 | 110 | 92 | 74 | 69 | 39 | 23 |
