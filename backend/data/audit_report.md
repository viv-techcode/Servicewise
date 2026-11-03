# Dataset audit details

Rows: 5033; stock SKUs: 63; ledger events: 14174; vague/typo/Hinglish proxy share: 10.2%.

## Median job charge vs reference range
| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |
|---|---:|---:|---:|---:|---:|
| Battery/Electrical | bike | 260 | 2718 | n/a | n/a |
| Battery/Electrical | car | 309 | 5360 | 3029.5 | 4469.5 |
| Brake System | bike | 220 | 345 | 224.0 | 299.0 |
| Brake System | car | 299 | 1146 | 600.0 | 2729.5 |
| Cooling System | bike | 191 | 917 | n/a | n/a |
| Cooling System | car | 282 | 1544 | 685.0 | 1420.0 |
| Engine | bike | 214 | 3554 | n/a | n/a |
| Engine | car | 290 | 7456 | 8500.0 | 18000.0 |
| Fuel System | bike | 127 | 559 | n/a | n/a |
| Fuel System | car | 181 | 970 | 560.0 | 810.0 |
| General Maintenance | bike | 461 | 1779 | n/a | n/a |
| General Maintenance | car | 535 | 3436 | 1599.0 | 5499.0 |
| Starting System | bike | 181 | 1863 | n/a | n/a |
| Starting System | car | 230 | 3544 | n/a | n/a |
| Suspension | bike | 156 | 3841 | n/a | n/a |
| Suspension | car | 220 | 7691 | 800.0 | n/a |
| Transmission | bike | 124 | 1078 | n/a | n/a |
| Transmission | car | 178 | 1885 | 925.0 | 1550.0 |
| Tyres/Wheels | bike | 243 | 3931 | n/a | n/a |
| Tyres/Wheels | car | 332 | 8044 | 399.5 | 10299.0 |

## Bike-to-car median job charge
| Fault | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 2718 | 5360 | 0.51 |
| Brake System | 345 | 1146 | 0.30 |
| Cooling System | 917 | 1544 | 0.59 |
| Engine | 3554 | 7456 | 0.48 |
| Fuel System | 559 | 970 | 0.58 |
| General Maintenance | 1779 | 3436 | 0.52 |
| Starting System | 1863 | 3544 | 0.53 |
| Suspension | 3841 | 7691 | 0.50 |
| Transmission | 1078 | 1885 | 0.57 |
| Tyres/Wheels | 3931 | 8044 | 0.49 |
## Combined severity distribution by primary fault
| Fault | Severity | Jobs |
|---|---|---:|
| Battery/Electrical | critical | 19 |
| Battery/Electrical | high | 192 |
| Battery/Electrical | low | 106 |
| Battery/Electrical | medium | 252 |
| Brake System | critical | 187 |
| Brake System | high | 105 |
| Brake System | low | 40 |
| Brake System | medium | 187 |
| Cooling System | critical | 70 |
| Cooling System | high | 80 |
| Cooling System | medium | 323 |
| Engine | critical | 147 |
| Engine | high | 175 |
| Engine | medium | 182 |
| Fuel System | critical | 83 |
| Fuel System | high | 65 |
| Fuel System | medium | 160 |
| General Maintenance | high | 1 |
| General Maintenance | low | 857 |
| General Maintenance | medium | 138 |
| Starting System | critical | 11 |
| Starting System | high | 110 |
| Starting System | medium | 290 |
| Suspension | critical | 18 |
| Suspension | high | 104 |
| Suspension | low | 29 |
| Suspension | medium | 225 |
| Transmission | critical | 2 |
| Transmission | high | 48 |
| Transmission | medium | 252 |
| Tyres/Wheels | critical | 28 |
| Tyres/Wheels | high | 211 |
| Tyres/Wheels | low | 233 |
| Tyres/Wheels | medium | 103 |

## Per-fault severity distribution
| Fault | Severity | Fault instances |
|---|---|---:|
| Battery/Electrical | high | 214 |
| Battery/Electrical | low | 166 |
| Battery/Electrical | medium | 322 |
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
| Tyres/Wheels | high | 245 |
| Tyres/Wheels | low | 396 |
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
