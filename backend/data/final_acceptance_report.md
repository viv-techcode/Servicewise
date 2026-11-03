# Final acceptance evidence

Verified on branch `cleanup-single-model` after Phase 1.

| Check | Result |
|---|---|
| `python -m pytest -q` | 45 passed |
| `validate_workshop_data.py` | PASS; 5,033 jobs, 63 SKUs, 14,964 ledger events, 22 months |
| `audit_dataset.py --summary` | 27 checks; 0 violations in every check |
| `node --check frontend/static/js/main.js` | PASS |
| Model | v006; chronological exact match 0.9960; unseen-template 0.9940 |
| Challenge set | 150 cases; severity accuracy 1.0000; red-flag under-predictions 0; misses 0 |
| Combined severity mix | low 25.1%; medium 42.0%; high 21.7%; critical 11.2% |
| Rebuilt SQLite | service rows 5033 (CSV 5033, non-CSV 0); stock 63; ledger 14964; months 22 |

The severity shares remain approximate generator targets; the difference reflects rule-based phrase labels and multi-fault escalation. SQLite was rebuilt after tests, leaving no test-created service records.
