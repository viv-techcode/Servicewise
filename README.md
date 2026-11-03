# ServiceWise

ServiceWise is a Flask application for vehicle fault diagnosis, repair-cost estimates, and reviewed service feedback.

## Features

- Predicts one or more vehicle fault categories from symptoms and reports per-fault plus combined severity.
- Estimates a repair-cost range from per-fault dataset quartiles; multi-fault medians receive a 10% shared-visit discount.
- Stores diagnostic records, inventory snapshots/ledger, and monthly summaries in SQLite.
- Accepts ratings, confirmed faults, and repair costs as feedback.
- Provides model analytics plus monthly finance, inventory, and fault-by-month views for store owners.
- Retrains models with approved feedback and supports version rollback.

## Tech stack

- Python 3.11
- Flask
- SQLite
- scikit-learn, pandas, NumPy, and joblib
- HTML, CSS, and JavaScript frontend
- pytest

## Project structure

```text
backend/             Flask application, database access, and machine-learning code
backend/data/        Datasets and data-preparation utilities
backend/ml/          Training, prediction, metrics, and retraining code
backend/tests/       Automated tests
frontend/templates/  Application HTML
frontend/static/     CSS and JavaScript assets
docs/                Database documentation
scripts/             Data utility scripts
```

## Getting started

Clone the repository and enter its folder:

```powershell
git clone https://github.com/viv-techcode/Servicewise.git
Set-Location Servicewise
```

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the application:

```powershell
python -m backend.app
```

Open http://127.0.0.1:5000 in a browser.

## Workshop data

`backend/data/service_records.csv` is the app's main service dataset. The same
directory contains the inventory snapshot, inventory event ledger, and monthly
finance summary. Regenerate the four CSVs deterministically with:

```powershell
python -m backend.data.generate_workshop_data
python -m backend.data.validate_workshop_data
```

The validator checks labels and severity, vehicle mileage, parts fitment, stock
ledger reconciliation, and monthly finance totals. `build_price_reference.py`
creates a separate sourced reference CSV and does not modify service records.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Flask session signing key | Development fallback in the application |
| `SERVICEWISE_DB_PATH` | SQLite database file path | `backend/data/service_center.db` |

If these variables are not set, the application uses the defaults shown above.

## How to use

### Tear-off calendar

The vehicle-age control is implemented by `frontend/static/js/tear-calendar.js`.
It is a vanilla `TearCalendar` component driven by the existing GSAP CDN
scripts, so no frontend build step or package install is required. The current
page wires it to the vehicle age input with scroll, touch, and arrow controls.

To reuse it, instantiate `new TearCalendar(element, options)` with
`trigger: 'load'`, `'click'`, or `'scroll'`, then use `play()`, `pause()`, and
`reset()` on the returned instance. Adjust `speedUpFactor`, `daysToTear`,
`loop`, and `whipPanAtEnd` in the options. Timing and palette constants are
listed at the top of `tear-calendar.js`.

### Diagnose a vehicle

1. Open the application and provide the vehicle type, brand, model, age, kilometres driven, and symptoms. Cost ranges use per-fault costs grouped by vehicle type in the active CSV.
2. Submit the diagnosis form.
3. Review the predicted fault categories, urgency, and estimated repair-cost range.
4. The diagnosis is saved and can be viewed in the records area.

The web form uses `POST /api/predict` for diagnoses and `GET /api/records` for saved records.

### Submit feedback

1. Open a saved diagnosis and submit a rating.
2. Add the confirmed fault categories when available.
3. Optionally add the total repair cost, per-fault costs, and comments.
4. Feedback is submitted with a `pending` review status.

Feedback is sent to `POST /api/feedback`.

### Store-owner approval

1. Sign in with a store-owner account.
2. Open the analytics and feedback review area.
3. Approve or reject pending feedback.
4. Only approved feedback with valid corrected fault labels is eligible for retraining.

Approval uses `POST /api/feedback/<feedback_id>/review` with `approved` or `rejected`.

## Model results

The active classifier is v006. Evaluation artifacts are in
`backend/ml/model_metrics.json` and `backend/ml/test_set_predictions.csv`.

| Evaluation | Result |
| --- | ---: |
| Chronological test exact match | 0.9960 (747 rows) |
| Single-fault exact match | 1.0000 (510 rows) |
| Multi-fault exact match | 0.9873 (237 rows) |
| Unseen-template exact match | 0.9940 (1,168 rows) |
| Unseen-template single-fault exact match | 1.0000 |
| Unseen-template multi-fault exact match | 0.9770 |
| Challenge cases | 0.9667 severity accuracy (150 hand-authored cases) |
| Challenge Brake/Cooling/Fuel recall | 1.000 / 1.000 / 1.000 |
| Challenge red-flag under-predictions | 0 |

The regenerated jobs have combined severity shares of 26.6% low, 44.1% medium, 18.3% high, and 11.0% critical. These remain approximate targets because the shared rule table and multi-fault escalations determine final job tiers.

The chronological test uses the last three months (2026-08 through 2026-10).
The separate unseen-template test holds out `symptom_template_id` groups absent
from its training fold. The chronological test had three multilabel mismatches;
each is listed in the model metrics artifact. These metrics measure fit to the
synthetic dataset and are not estimates of real-world diagnostic performance or real-world accuracy.
Per-fault and combined severity use the shared rules in
`backend/ml/severity.py`.

## Known limitations

- The records, challenge labels, costs, inventory movements, and finance are
  synthetic demonstration data. No real-world diagnostic accuracy is claimed.
- The repair reference contains sparse bike pricing outside the brake category;
  bike cost medians in those categories use generated vehicle-specific rates.
- The bike-to-car brake job median ratio is 0.09 because the available Delhi
  bike brake reference is far below the car brake menu range; this exception
  preserves the sourced ranges rather than forcing the general 0.3-0.6 ratio.
- A low-confidence complaint returns a clarifying question and suppresses a
  firm diagnosis, severity, parts list, and price until more information is given.

## Retraining

Retrain using approved feedback:

```powershell
python -m backend.ml.retrain
```

Evaluate a candidate without saving or activating it:

```powershell
python -m backend.ml.retrain --dry-run
```

Restore a saved model version:

```powershell
python -m backend.ml.retrain --rollback v000
```

Retraining compares a candidate against the current classifier on the latest
three chronological months from `service_records.csv`. It does not use a
random split.

## Running tests

```powershell
python -m pytest
```
