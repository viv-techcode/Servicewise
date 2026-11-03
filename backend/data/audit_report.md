# Dataset audit details

Rows: 7000; stock SKUs: 62; ledger events: 13300; vague/typo/Hinglish proxy share: 20.2%.

## Median job charge vs reference range
| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |
|---|---:|---:|---:|---:|---:|
| Battery/Electrical | bike | 437 | 1010 | 500.0 | 1500.0 |
| Battery/Electrical | car | 488 | 1980 | 1500.0 | 4500.0 |
| Brake System | bike | 345 | 1404 | 800.0 | 3000.0 |
| Brake System | car | 412 | 4275 | 2200.0 | 7000.0 |
| Cooling System | bike | 226 | 1220 | 500.0 | 2500.0 |
| Cooling System | car | 314 | 2560 | 1600.0 | 7000.0 |
| Engine | bike | 203 | 2367 | 1200.0 | 6500.0 |
| Engine | car | 235 | 4491 | 2800.0 | 15000.0 |
| Fuel System | bike | 259 | 960 | 500.0 | 2500.0 |
| Fuel System | car | 315 | 2820 | 1500.0 | 7000.0 |
| General Maintenance | bike | 662 | 790 | 700.0 | 3000.0 |
| General Maintenance | car | 794 | 2320 | 2200.0 | 9000.0 |
| Starting System | bike | 311 | 1360 | 500.0 | 2500.0 |
| Starting System | car | 369 | 3230 | 1500.0 | 7000.0 |
| Suspension | bike | 185 | 1892 | 1200.0 | 7000.0 |
| Suspension | car | 257 | 4986 | 3000.0 | 20000.0 |
| Transmission | bike | 249 | 2376 | 1200.0 | 7000.0 |
| Transmission | car | 235 | 6950 | 4500.0 | 26000.0 |
| Tyres/Wheels | bike | 296 | 2367 | 800.0 | 7000.0 |
| Tyres/Wheels | car | 408 | 6736 | 1800.0 | 22000.0 |

## Bike-to-car median job charge
| Fault | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 1010 | 1980 | 0.51 |
| Brake System | 1404 | 4275 | 0.33 |
| Cooling System | 1220 | 2560 | 0.48 |
| Engine | 2367 | 4491 | 0.53 |
| Fuel System | 960 | 2820 | 0.34 |
| General Maintenance | 790 | 2320 | 0.34 |
| Starting System | 1360 | 3230 | 0.42 |
| Suspension | 1892 | 4986 | 0.38 |
| Transmission | 2376 | 6950 | 0.34 |
| Tyres/Wheels | 2367 | 6736 | 0.35 |
## Combined severity distribution by primary fault
| Fault | Severity | Jobs |
|---|---|---:|
| Battery/Electrical | critical | 76 |
| Battery/Electrical | high | 140 |
| Battery/Electrical | low | 210 |
| Battery/Electrical | medium | 499 |
| Brake System | critical | 185 |
| Brake System | high | 166 |
| Brake System | low | 168 |
| Brake System | medium | 238 |
| Cooling System | critical | 63 |
| Cooling System | high | 120 |
| Cooling System | low | 90 |
| Cooling System | medium | 267 |
| Engine | critical | 59 |
| Engine | high | 137 |
| Engine | low | 55 |
| Engine | medium | 187 |
| Fuel System | critical | 44 |
| Fuel System | high | 87 |
| Fuel System | low | 60 |
| Fuel System | medium | 383 |
| General Maintenance | critical | 6 |
| General Maintenance | high | 20 |
| General Maintenance | low | 286 |
| General Maintenance | medium | 1144 |
| Starting System | critical | 40 |
| Starting System | high | 222 |
| Starting System | low | 90 |
| Starting System | medium | 328 |
| Suspension | critical | 57 |
| Suspension | high | 111 |
| Suspension | low | 75 |
| Suspension | medium | 199 |
| Transmission | critical | 48 |
| Transmission | high | 103 |
| Transmission | low | 41 |
| Transmission | medium | 292 |
| Tyres/Wheels | critical | 74 |
| Tyres/Wheels | high | 155 |
| Tyres/Wheels | low | 224 |
| Tyres/Wheels | medium | 251 |

## Per-fault severity distribution
| Fault | Severity | Fault instances |
|---|---|---:|
| Battery/Electrical | critical | 63 |
| Battery/Electrical | high | 155 |
| Battery/Electrical | low | 380 |
| Battery/Electrical | medium | 605 |
| Brake System | critical | 163 |
| Brake System | high | 178 |
| Brake System | low | 297 |
| Brake System | medium | 367 |
| Cooling System | critical | 45 |
| Cooling System | high | 132 |
| Cooling System | low | 211 |
| Cooling System | medium | 410 |
| Engine | critical | 30 |
| Engine | high | 128 |
| Engine | low | 165 |
| Engine | medium | 342 |
| Fuel System | critical | 30 |
| Fuel System | high | 97 |
| Fuel System | low | 166 |
| Fuel System | medium | 552 |
| General Maintenance | low | 350 |
| General Maintenance | medium | 1441 |
| Starting System | critical | 23 |
| Starting System | high | 261 |
| Starting System | low | 223 |
| Starting System | medium | 440 |
| Suspension | critical | 31 |
| Suspension | high | 111 |
| Suspension | low | 181 |
| Suspension | medium | 328 |
| Transmission | critical | 32 |
| Transmission | high | 97 |
| Transmission | low | 98 |
| Transmission | medium | 408 |
| Tyres/Wheels | critical | 56 |
| Tyres/Wheels | high | 152 |
| Tyres/Wheels | low | 403 |
| Tyres/Wheels | medium | 362 |

## Fault category by service month
| Fault | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Battery/Electrical | 127 | 111 | 78 | 101 | 107 | 103 | 128 | 111 | 94 | 107 | 56 | 80 |
| Brake System | 98 | 74 | 81 | 68 | 68 | 87 | 144 | 134 | 112 | 65 | 45 | 29 |
| Cooling System | 50 | 48 | 44 | 99 | 131 | 121 | 68 | 57 | 56 | 53 | 40 | 31 |
| Engine | 75 | 60 | 66 | 52 | 59 | 53 | 67 | 65 | 56 | 52 | 30 | 30 |
| Fuel System | 67 | 56 | 63 | 76 | 80 | 77 | 95 | 94 | 69 | 85 | 50 | 33 |
| General Maintenance | 132 | 89 | 138 | 153 | 177 | 180 | 192 | 171 | 173 | 200 | 99 | 87 |
| Starting System | 90 | 78 | 55 | 74 | 83 | 97 | 107 | 86 | 76 | 88 | 50 | 63 |
| Suspension | 58 | 53 | 60 | 59 | 63 | 70 | 67 | 55 | 47 | 60 | 35 | 24 |
| Transmission | 36 | 33 | 36 | 58 | 73 | 59 | 75 | 69 | 61 | 65 | 43 | 27 |
| Tyres/Wheels | 81 | 66 | 68 | 70 | 74 | 89 | 139 | 106 | 108 | 85 | 49 | 38 |

## Dataset v2 composition
| Measure | Value |
|---|---:|
| Jobs | 7000 |
| Ambiguous rows | 9.7% |
| Part-price SKUs | 62 |

## Cost medians by severity
| Category | Vehicle | Low | Medium | High | Critical |
|---|---|---:|---:|---:|---:|
| Battery/Electrical | bike | 270 | 1010 | 3312 | 4284 |
| Battery/Electrical | car | 1107 | 1320 | 6858 | 7578 |
| Brake System | bike | 954 | 999 | 4040 | 4714 |
| Brake System | car | 1817 | 1818 | 5292 | 6608 |
| Cooling System | bike | 702 | 747 | 1476 | 2286 |
| Cooling System | car | 1755 | 1856 | 4002 | 6636 |
| Engine | bike | 1242 | 1287 | 3030 | 4077 |
| Engine | car | 2655 | 2754 | 5175 | 8046 |
| Fuel System | bike | 324 | 410 | 1215 | 1647 |
| Fuel System | car | 1230 | 1420 | 3762 | 5166 |
| General Maintenance | bike | 740 | 790 | — | — |
| General Maintenance | car | 2230 | 2320 | — | — |
| Starting System | bike | 450 | 550 | 1692 | 2250 |
| Starting System | car | 1130 | 1270 | 4122 | 5762 |
| Suspension | bike | 729 | 774 | 2448 | 3285 |
| Suspension | car | 3357 | 3438 | 7002 | 10566 |
| Transmission | bike | — | 1580 | 3528 | 3798 |
| Transmission | car | 3915 | 4014 | 9855 | 15540 |
| Tyres/Wheels | bike | 1089 | 1260 | 4158 | 5355 |
| Tyres/Wheels | car | 3030 | 2808 | 8980 | 11117 |

## Bike-to-car median ratios
| Category | Bike median | Car median | Ratio |
|---|---:|---:|---:|
| Battery/Electrical | 1010 | 1980 | 0.51 |
| Brake System | 1404 | 4275 | 0.33 |
| Cooling System | 1220 | 2560 | 0.48 |
| Engine | 2367 | 4491 | 0.53 |
| Fuel System | 960 | 2820 | 0.34 |
| General Maintenance | 790 | 2320 | 0.34 |
| Starting System | 1360 | 3230 | 0.42 |
| Suspension | 1892 | 4986 | 0.38 |
| Transmission | 2376 | 6950 | 0.34 |
| Tyres/Wheels | 2367 | 6736 | 0.35 |
