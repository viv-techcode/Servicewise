# ServiceWise Database Schema

## Storage & Configuration
- **Database Engine**: SQLite 3
- **File Location**: `backend/data/service_center.db`
- **Data Access Layer**: `backend/db.py`
- **Active workshop CSVs**: `backend/data/service_records.csv`, `inventory_stock.csv`, `inventory_log.csv`, and `monthly_summary.csv`
- **Dataset generation and checks**: `backend/data/generate_workshop_data.py` and `backend/data/validate_workshop_data.py`

---

## Entity Relationship (ER) Diagram

```text
       +-----------------------+
       |         users         |
       +-----------------------+
       | id (PK)               |
       | username (UNIQUE)     |
       | password_hash         |
       | role (customer/store) |
       | created_at            |
       +-----------+-----------+
                   | 1
                   |
                   | 0..*
       +-----------v-----------+               +-----------------------+
       |    service_records    | 1        0..* |       feedback        |
       +-----------------------+---------------+-----------------------+
       | id (PK)               |               | id (PK)               |
       | user_id (FK -> users) |               | record_id (FK)        |
       | vehicle_type          |               | user_id (FK -> users) |
       | vehicle_brand         |               | accuracy_rating (1-5) |
       | vehicle_model         |               | actual_cost           |
       | vehicle_age           |               | comments              |
       | km_driven             |               | submitted_at          |
       | symptoms              |               +-----------------------+
       | predicted_category    |
       | urgency               |
       | actual_cost           |
       | timestamp             |
       +-----------------------+
```

---

## Tables Definition

### 1. `users`
Stores registered account credentials and role assignments.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique user identifier |
| `username` | TEXT | UNIQUE, NOT NULL | Account login username |
| `password_hash` | TEXT | NOT NULL | Werkzeug hashed password |
| `role` | TEXT | NOT NULL CHECK(role IN ('customer', 'store_owner')) | Account role permissions |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

### 2. `service_records`
Stores diagnostic queries submitted by customers or guests, along with ML prediction outputs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record ID |
| `user_id` | INTEGER | FOREIGN KEY REFERENCES users(id) | Associated user (NULL for guests) |
| `vehicle_type` | TEXT | NOT NULL | 'bike' or 'car'; active supported makes/models are in `backend/vehicles.py` |
| `vehicle_brand` | TEXT | NOT NULL | Vehicle manufacturer brand |
| `vehicle_model` | TEXT | NOT NULL | Vehicle model name |
| `state` | TEXT | | Always `Global`; location is not collected or used for estimates |
| `vehicle_age` | INTEGER | | Age of vehicle in years |
| `km_driven` | INTEGER | | Kilometres driven |
| `symptoms` | TEXT | NOT NULL | Reported vehicle issue description |
| `predicted_category` | TEXT | | ML classified subsystem |
| `predicted_faults_json` | TEXT | | Multilabel fault categories and confidence values |
| `predicted_costs_json` | TEXT | | Cached cost range and per-fault estimate snapshot |
| `predicted_cost_min` | REAL | | Lower end of the dataset-backed cost range (INR) |
| `predicted_cost_max` | REAL | | Upper end of the dataset-backed cost range (INR) |
| `urgency` | TEXT | | 'Low', 'Medium', or 'High' |
| `actual_cost` | REAL | | Upper estimated repair budget in INR |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Diagnosis creation time |

### 3. `feedback`
Stores user-submitted verification ratings and actual workshop costs to audit ML performance.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique feedback ID |
| `record_id` | INTEGER | NOT NULL, FK REFERENCES service_records(id) | Target diagnostic record |
| `user_id` | INTEGER | FK REFERENCES users(id) | Reviewer user ID (optional) |
| `accuracy_rating` | INTEGER | NOT NULL CHECK(accuracy_rating BETWEEN 1 AND 5) | Star rating 1 to 5 |
| `actual_cost` | REAL | | Final repair bill paid (INR) |
| `comments` | TEXT | | Freeform review text |
| `submitted_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Submission timestamp |

---

## Role Access Matrix

| Feature / Resource | Guest | Customer | Store Owner / Workshop |
|---|---|---|---|
| **Vehicle Diagnosis** | Yes | Yes (recorded to user profile) | Yes |
| **View Service History** | Public records (last 20) | User's own service records only | All customer workshop records |
| **Submit Feedback & Rating** | Yes | Yes | Yes |
| **Workshop Business Analytics** | Summary | Summary | Full metrics & distribution charts |
| **Model Evaluation & Health** | Standard view | Standard view | Multilabel fault-classification metrics |


## Imported store data

`inventory_stock` stores the current part snapshot and compatible model list imported from `backend/data/inventory_stock.csv`. `inventory_log` stores stock openings, sales, restocks, and stock-out events from `inventory_log.csv`. `monthly_summary` stores job counts, revenue, margins, fixed overheads, net profit, month-over-month change, and trend from `monthly_summary.csv`. Startup refreshes these operational tables from their CSV sources. Store owners can read them through `GET /api/store-data`; the response includes stock-level status and per-month fault counts.
