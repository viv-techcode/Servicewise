# Dataset audit details

Rows: 5033; stock SKUs: 63; ledger events: 14964; vague/typo/Hinglish proxy share: 10.2%.

## Median job charge vs reference range
| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |
|---|---:|---:|---:|---:|---:|
| Battery/Electrical | bike | 248 | 2703 | n/a | n/a |
| Battery/Electrical | car | 290 | 5342 | 3029.5 | 4469.5 |
| Brake System | bike | 223 | 310 | 224.0 | 299.0 |
| Brake System | car | 319 | 3322 | 600.0 | 2729.5 |
| Cooling System | bike | 182 | 984 | n/a | n/a |
| Cooling System | car | 266 | 1483 | 685.0 | 1420.0 |
| Engine | bike | 216 | 3601 | n/a | n/a |
| Engine | car | 301 | 7564 | 8500.0 | 18000.0 |
| Fuel System | bike | 126 | 612 | n/a | n/a |
| Fuel System | car | 173 | 935 | 560.0 | 810.0 |
| General Maintenance | bike | 507 | 1866 | n/a | n/a |
| General Maintenance | car | 590 | 3550 | 1599.0 | 5499.0 |
| Starting System | bike | 180 | 1859 | n/a | n/a |
| Starting System | car | 220 | 3560 | n/a | n/a |
| Suspension | bike | 162 | 3569 | n/a | n/a |
| Suspension | car | 239 | 7935 | 800.0 | n/a |
| Transmission | bike | 113 | 1105 | n/a | n/a |
| Transmission | car | 160 | 1762 | 925.0 | 1550.0 |
| Tyres/Wheels | bike | 220 | 3930 | n/a | n/a |
| Tyres/Wheels | car | 298 | 7852 | 399.5 | 10299.0 |

## Bike-to-car median job charge
| Fault | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 2703 | 5342 | 0.51 |
| Brake System | 310 | 3322 | 0.09 |
| Cooling System | 984 | 1483 | 0.66 |
| Engine | 3601 | 7564 | 0.48 |
| Fuel System | 612 | 935 | 0.66 |
| General Maintenance | 1866 | 3550 | 0.53 |
| Starting System | 1859 | 3560 | 0.52 |
| Suspension | 3569 | 7935 | 0.45 |
| Transmission | 1105 | 1762 | 0.63 |
| Tyres/Wheels | 3930 | 7852 | 0.50 |
## Combined severity distribution by primary fault
| Fault | Severity | Jobs |
|---|---|---:|
| Battery/Electrical | critical | 1 |
| Battery/Electrical | high | 23 |
| Battery/Electrical | low | 98 |
| Battery/Electrical | medium | 416 |
| Brake System | critical | 154 |
| Brake System | high | 200 |
| Brake System | low | 40 |
| Brake System | medium | 148 |
| Cooling System | critical | 63 |
| Cooling System | high | 47 |
| Cooling System | medium | 338 |
| Engine | critical | 152 |
| Engine | high | 178 |
| Engine | medium | 187 |
| Fuel System | critical | 84 |
| Fuel System | high | 65 |
| Fuel System | medium | 150 |
| General Maintenance | critical | 1 |
| General Maintenance | high | 9 |
| General Maintenance | low | 372 |
| General Maintenance | medium | 715 |
| Starting System | critical | 7 |
| Starting System | high | 76 |
| Starting System | medium | 317 |
| Suspension | critical | 9 |
| Suspension | high | 58 |
| Suspension | medium | 334 |
| Transmission | critical | 3 |
| Transmission | high | 49 |
| Transmission | medium | 221 |
| Tyres/Wheels | critical | 13 |
| Tyres/Wheels | high | 111 |
| Tyres/Wheels | low | 291 |
| Tyres/Wheels | medium | 103 |

## Per-fault severity distribution
| Fault | Severity | Fault instances |
|---|---|---:|
| Battery/Electrical | low | 166 |
| Battery/Electrical | medium | 536 |
| Brake System | critical | 110 |
| Brake System | high | 245 |
| Brake System | low | 107 |
| Brake System | medium | 254 |
| Cooling System | critical | 60 |
| Cooling System | high | 49 |
| Cooling System | medium | 560 |
| Engine | critical | 100 |
| Engine | high | 168 |
| Engine | medium | 320 |
| Fuel System | critical | 77 |
| Fuel System | high | 84 |
| Fuel System | medium | 341 |
| General Maintenance | low | 440 |
| General Maintenance | medium | 866 |
| Starting System | high | 80 |
| Starting System | medium | 488 |
| Suspension | medium | 514 |
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
