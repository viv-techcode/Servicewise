# ServiceWise Database Schema

## Storage & Configuration
- **Database Engine**: SQLite 3
- **File Location**: `backend/data/service_center.db`
- **Data Access Layer**: `backend/db.py`

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
| `vehicle_type` | TEXT | NOT NULL | 'bike' or 'car' |
| `vehicle_brand` | TEXT | NOT NULL | Vehicle manufacturer brand |
| `vehicle_model` | TEXT | NOT NULL | Vehicle model name |
| `vehicle_age` | INTEGER | | Age of vehicle in years |
| `km_driven` | INTEGER | | Kilometres driven |
| `symptoms` | TEXT | NOT NULL | Reported vehicle issue description |
| `predicted_category` | TEXT | | ML classified subsystem |
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
| **Model Evaluation & Health** | Standard view | Standard view | Model performance, MAE & F1 stats |
