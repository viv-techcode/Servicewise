# ServiceWise — Smart Vehicle Diagnostics & Cost Prediction

ServiceWise is a lightweight, machine-learning-powered decision support and diagnostic web application tailored for automobile service centers and vehicle owners.

---

## Features
- **Vehicle Problem Classification**: NLP-based identification of component/system faults from user symptoms.
- **Repair Cost Range Estimation**: Random Forest regression estimating cost bounds based on vehicle age, mileage, brand, and problem type.
- **Urgency Assessment**: Risk-level categorization (High, Medium, Low) for prioritized maintenance.
- **Service History Logging**: Persistent SQLite storage tracking diagnostic logs and historical records.
- **Interactive UI**: Responsive single-page interface with diagnostic forms, history viewing, and quick cost exploration.

---

## Project Structure
```text
.
├── backend/
│   ├── app.py                # Flask application & API routes
│   ├── db.py                 # SQLite database initialization and access
│   ├── data/
│   │   └── sample_service_records.csv  # Baseline training records
│   ├── ml/
│   │   ├── train_models.py   # Training script for NLP & regression models
│   │   ├── predictor.py      # Inference wrapper for classification & estimation
│   │   ├── problem_classifier.pkl
│   │   └── cost_regressor.pkl
│   └── tests/
│       └── test_api.py       # API test suite
├── frontend/
│   ├── templates/
│   │   └── index.html        # Main user interface template
│   └── static/
│       ├── css/
│       │   └── style.css     # Styling and responsive design
│       └── js/
│           └── main.js       # Client-side dynamic interactions and API calls
└── README.md
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10+
- `pip` or `uv` package manager

### 2. Environment Setup
Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install flask pandas scikit-learn joblib pytest
```

---

## Running the Application

1. **Start the Flask Server**:
   ```bash
   python -m backend.app
   ```
2. **Access the Web Interface**:
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

3. **Running the Tests**:
   ```bash
   pytest
   ```

---

## Prototype Status & Project Phase
> **Note:** This project is currently in an active **prototype/development phase (Phase 1 MVP)**. While all core functional workflows (ML inference, API routing, and interactive frontend) are operational, several production-level enhancements are actively in progress.

### Current Limitations & Scope
- **Dataset Scale & Diversity**: The prototype uses synthetic/sample service record data (`backend/data/sample_service_records.csv`) for demonstration and initial baseline training. Real-world accuracy and variance calibration will require a substantially larger, diverse multi-brand dataset.
- **NLP & Feature Extraction**: The current NLP pipeline relies on basic keyword and TF-IDF tokenization, which works reliably for standard technical symptom phrases but can be upgraded to transformer-based embeddings or fine-tuned LLM classification for noisy, conversational, or ambiguous user descriptions.

---

## Roadmap & Planned Enhancements

### Planned Add-ons & Future Iterations
1. **PDF Quote & Diagnostic Report Export**
   - Automated generation of downloadable and printable cost estimation sheets, repair breakdown summaries, and formal diagnostic certificates.
2. **Garage Appointment & Booking Integration**
   - Direct booking workflow enabling vehicle owners to reserve workshop time slots prioritized by diagnosed urgency level (High / Medium / Low).
3. **Parts Catalog & Inventory Synchronization**
   - Integration with local and supplier inventory systems to map diagnosed fault categories to specific OEM/aftermarket replacement parts and real-time pricing.
4. **LLM-Assisted Diagnostic Explanation**
   - Interactive diagnostic assistant offering structured, plain-language troubleshooting guidance, preventive advice, and workshop visit preparation.
5. **Multi-Language & Vernacular Input Support**
   - Cross-lingual symptom processing supporting Hindi and regional languages for broader user accessibility.
