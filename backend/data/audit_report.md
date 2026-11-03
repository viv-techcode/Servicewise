# Dataset audit details

Rows: 5033; stock SKUs: 63; ledger events: 14964; vague/typo/Hinglish proxy share: 10.2%.

## Median job charge vs reference range
| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |
|---|---:|---:|---:|---:|---:|
| Battery/Electrical | bike | 256 | 2703 | n/a | n/a |
| Battery/Electrical | car | 301 | 5363 | 3029.5 | 4469.5 |
| Brake System | bike | 220 | 308 | 224.0 | 299.0 |
| Brake System | car | 325 | 3350 | 600.0 | 2729.5 |
| Cooling System | bike | 194 | 918 | n/a | n/a |
| Cooling System | car | 284 | 1566 | 685.0 | 1420.0 |
| Engine | bike | 218 | 3572 | n/a | n/a |
| Engine | car | 295 | 7564 | 8500.0 | 18000.0 |
| Fuel System | bike | 130 | 558 | n/a | n/a |
| Fuel System | car | 182 | 971 | 560.0 | 810.0 |
| General Maintenance | bike | 463 | 1783 | n/a | n/a |
| General Maintenance | car | 534 | 3437 | 1599.0 | 5499.0 |
| Starting System | bike | 185 | 1883 | n/a | n/a |
| Starting System | car | 233 | 3638 | n/a | n/a |
| Suspension | bike | 157 | 3803 | n/a | n/a |
| Suspension | car | 229 | 7998 | 800.0 | n/a |
| Transmission | bike | 125 | 1068 | n/a | n/a |
| Transmission | car | 174 | 1885 | 925.0 | 1550.0 |
| Tyres/Wheels | bike | 229 | 3929 | n/a | n/a |
| Tyres/Wheels | car | 299 | 7841 | 399.5 | 10299.0 |

## Bike-to-car median job charge
| Fault | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 2703 | 5363 | 0.50 |
| Brake System | 308 | 3350 | 0.09 |
| Cooling System | 918 | 1566 | 0.59 |
| Engine | 3572 | 7564 | 0.47 |
| Fuel System | 558 | 971 | 0.57 |
| General Maintenance | 1783 | 3437 | 0.52 |
| Starting System | 1883 | 3638 | 0.52 |
| Suspension | 3803 | 7998 | 0.48 |
| Transmission | 1068 | 1885 | 0.57 |
| Tyres/Wheels | 3929 | 7841 | 0.50 |
## Combined severity distribution by primary fault
| Fault | Severity | Jobs |
|---|---|---:|
| Battery/Electrical | critical | 10 |
| Battery/Electrical | high | 113 |
| Battery/Electrical | low | 106 |
| Battery/Electrical | medium | 328 |
| Brake System | critical | 194 |
| Brake System | high | 107 |
| Brake System | low | 40 |
| Brake System | medium | 204 |
| Cooling System | critical | 71 |
| Cooling System | high | 83 |
| Cooling System | medium | 324 |
| Engine | critical | 148 |
| Engine | high | 177 |
| Engine | medium | 188 |
| Fuel System | critical | 84 |
| Fuel System | high | 65 |
| Fuel System | medium | 163 |
| General Maintenance | high | 1 |
| General Maintenance | low | 857 |
| General Maintenance | medium | 139 |
| Starting System | critical | 12 |
| Starting System | high | 114 |
| Starting System | medium | 292 |
| Suspension | critical | 19 |
| Suspension | high | 105 |
| Suspension | low | 30 |
| Suspension | medium | 232 |
| Transmission | critical | 2 |
| Transmission | high | 49 |
| Transmission | medium | 248 |
| Tyres/Wheels | critical | 12 |
| Tyres/Wheels | high | 109 |
| Tyres/Wheels | low | 304 |
| Tyres/Wheels | medium | 103 |

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
| General Maintenance | low | 1137 |
| General Maintenance | medium | 169 |
| Starting System | high | 133 |
| Starting System | medium | 435 |
| Suspension | high | 82 |
| Suspension | low | 71 |
| Suspension | medium | 361 |
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
