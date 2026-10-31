# ServiceWise

ServiceWise is a Flask application for vehicle fault diagnosis, repair-cost estimates, and reviewed service feedback.

## Features

- Predicts one or more vehicle fault categories from vehicle details and symptoms.
- Estimates a repair-cost range and urgency.
- Stores diagnostic records in SQLite.
- Accepts ratings, confirmed faults, and repair costs as feedback.
- Provides analytics and model metrics.
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

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Flask session signing key | Development fallback in the application |
| `SERVICEWISE_DB_PATH` | SQLite database file path | `backend/data/service_center.db` |

If these variables are not set, the application uses the defaults shown above.

## How to use

### Diagnose a vehicle

1. Open the application and provide the vehicle type, brand, model, age, kilometres driven, state, and symptoms.
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

The current metrics are recorded in `backend/ml/model_metrics.json`.

| Model result | Metric | Test value |
| --- | --- | ---: |
| Fault classifier | Primary fault accuracy | 0.8204 |
| Fault classifier | Micro-F1 | 0.9379 |
| Fault classifier | Exact-match accuracy | 0.8883 |
| Cost regressor | Per-fault MAE | 80.42 |
| Cost regressor | Per-fault RMSE | 519.18 |
| Cost regressor | Per-fault R² | 0.1984 |
| Cost regressor | Combined multi-fault total MAE | 60.01 |
| Cost regressor | Combined multi-fault total R² | 0.8247 |

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

Retraining compares the candidate with the current model on the fixed benchmark. A candidate is adopted only when both the micro-F1 and cost-MAE gates pass.

## Running tests

```powershell
python -m pytest
```
