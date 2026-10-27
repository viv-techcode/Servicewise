# ServiceWise — vehicle fault prediction and repair estimates

ServiceWise is a Flask application that predicts one or more vehicle fault categories, estimates repair costs, and stores diagnostic history and reviewed repair outcomes.

## Setup

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the application

```powershell
python -m backend.app
```

Open `http://127.0.0.1:5000`. Set `SECRET_KEY` for deployments. `SERVICEWISE_DB_PATH` can point to a separate SQLite file; otherwise the database is `backend/data/service_center.db`. Store-owner accounts can approve or reject feedback from the Analytics tab.

## Training and evaluation

The prepared dataset is `backend/data/service_records_balanced_3000.csv`; the preserved source file is `backend/data/sample_service_records.csv`. The prepared dataset is simulated; its labels and costs are not verified workshop records.

Train and evaluate the base models with the grouped split and fixed test benchmark:

```powershell
python -m backend.ml.train_models
```

The split seed and model settings are recorded in `backend/ml/model_metrics.json`. Evaluation details and held-out predictions are in `backend/ml/evaluation_report.md` and `backend/ml/test_set_predictions.csv`. Do not add feedback records to that benchmark.

## Submit and review feedback

After a diagnosis, submit the confirmed fault categories as a comma-separated list and the optional total bill. Optional per-fault costs use JSON, for example `{"Brake System": 2200, "Tyres/Wheels": 1500}`. Feedback is validated and stored as pending. A store owner must approve the corrected categories before they are eligible for model training; rejected and pending items are excluded. Existing rating-only submissions remain accepted for compatibility but cannot be approved for retraining without corrected fault labels.

The review endpoint is `POST /api/feedback/<feedback_id>/review` with `{"decision":"approved"}` or `{"decision":"rejected"}`. It requires a store-owner session.

## Retraining and model versions

```powershell
python -m backend.ml.retrain
```

Use `python -m backend.ml.retrain --dry-run` to fit and evaluate a candidate without saving or activating it.

Retraining adds only approved feedback to the training pool. It evaluates current and candidate artifacts on the same fixed Step 5d test record IDs. Feedback never enters the held-out benchmark. Adoption requires candidate micro-F1 to be no more than 0.005 below current and candidate per-fault cost MAE to be no more than 5% worse. Every run is saved under `backend/ml/model_versions/`; decisions and benchmark metrics are appended to `backend/ml/retraining_history.jsonl`.

Restore a saved version with:

```powershell
python -m backend.ml.retrain --rollback v000
```

`v000` is created as the original Step 5d baseline when the first retraining run is saved. Candidate artifacts and metadata remain archived even when the adoption gates fail.

## Tests

```powershell
python -m pytest
```

Tests cover API input validation, approval gating, held-out comparison logic, rollback, prediction history, and confirmed outcome analytics.

## Limitations

- The training data is controlled and simulated, so its scores do not establish real-world diagnostic accuracy or price calibration.
- Feedback quality depends on accurate mechanic-confirmed labels and bill entry; approval is a review gate, not independent verification of a workshop invoice.
- The fixed benchmark is intentionally not updated during feedback retraining. It should only be replaced through a separately reviewed evaluation-data release.
- Review authorization currently uses the existing store-owner role and local session authentication; deployments should add operational account controls and backups for the SQLite database and model archives.
