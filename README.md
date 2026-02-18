# Credit Approval System

A Django REST Framework application for credit approval based on historical loan data and customer profiles.

## Tech Stack
- **Django 4.2** + Django REST Framework
- **PostgreSQL** (database)
- **Redis** + **Celery** (background task queue for data ingestion)
- **Docker** + Docker Compose

## Project Structure

```
credit_system/                          ← root project folder
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── README.md
├── .gitignore
│
├── data/                               ← place your Excel files here
│   ├── customer_data.xlsx
│   └── loan_data.xlsx
│
├── credit_system/                      ← Django project package
│   ├── __init__.py                     ← imports celery app
│   ├── settings.py
│   ├── urls.py                         ← root URL config (includes loans.urls)
│   ├── celery.py
│   └── wsgi.py
│
└── loans/                              ← Django app
    ├── __init__.py                     ← empty file
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── serializers.py
    ├── services.py
    ├── tasks.py
    ├── tests.py
    ├── urls.py                         ← app-level URLs (register, check-eligibility, etc.)
    └── management/
        ├── __init__.py                 ← empty file
        └── commands/
            ├── __init__.py             ← empty file
            └── ingest_data.py
```

## Quick Start

### 1. Add Data Files

Place `customer_data.xlsx` and `loan_data.xlsx` in the `data/` directory.

### 2. Start the Application

```bash
docker-compose up --build
```

This will:
- Start PostgreSQL and Redis
- Run Django migrations
- Start the web server on port 8000
- Start a Celery worker
- Automatically ingest data from Excel files

### 3. Manual Data Ingestion (if needed)

```bash
# Queue via Celery (async)
docker-compose exec web python manage.py ingest_data

# Run synchronously
docker-compose exec web python manage.py ingest_data --sync
```

### 4. Run Tests

```bash
docker-compose exec web python manage.py test loans
```

---

## API Endpoints

### POST `/register`
Register a new customer.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 50000,
  "phone_number": 9876543210
}
```

**Response:**
```json
{
  "customer_id": 1,
  "name": "John Doe",
  "age": 30,
  "monthly_income": 50000,
  "approved_limit": 1800000,
  "phone_number": 9876543210
}
```

---

### POST `/check-eligibility`
Check loan eligibility based on credit score.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 100000,
  "interest_rate": 10,
  "tenure": 12
}
```

**Response:**
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 10.0,
  "corrected_interest_rate": 12.0,
  "tenure": 12,
  "monthly_installment": 8885.0
}
```

---

### POST `/create-loan`
Create a new loan if eligible.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 100000,
  "interest_rate": 12,
  "tenure": 12
}
```

**Response:**
```json
{
  "loan_id": 1,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved successfully.",
  "monthly_installment": 8885.0
}
```

---

### GET `/view-loan/<loan_id>`
View loan and customer details.

**Response:**
```json
{
  "loan_id": 1,
  "customer": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": 9876543210,
    "age": 30
  },
  "loan_amount": 100000.0,
  "interest_rate": 12.0,
  "monthly_installment": 8885.0,
  "tenure": 12
}
```

---

### GET `/view-loans/<customer_id>`
View all loans for a customer.

**Response:**
```json
[
  {
    "loan_id": 1,
    "loan_amount": 100000.0,
    "interest_rate": 12.0,
    "monthly_installment": 8885.0,
    "repayments_left": 12
  }
]
```

---

## Credit Score Logic

The credit score (0–100) is calculated from:

1. **Past loans paid on time** (up to 35 pts) — ratio of on-time EMIs
2. **Number of past loans** (up to 20 pts) — fewer loans = better
3. **Loan activity this year** (up to 20 pts) — fewer new loans = better
4. **Loan volume vs. approved limit** (up to 25 pts)
5. **Override**: If total active loan amount > approved limit → score = 0

### Approval Rules

| Credit Score | Condition |
|---|---|
| > 50 | Approve at any rate |
| 30–50 | Approve only if rate > 12% (else correct to 12%) |
| 10–30 | Approve only if rate > 16% (else correct to 16%) |
| < 10 | Reject |
| Any | Reject if total EMIs > 50% of monthly salary |

## EMI Formula (Compound Interest)

```
EMI = P × r × (1+r)^n / ((1+r)^n - 1)
```

Where:
- `P` = Principal
- `r` = Monthly interest rate = annual_rate / (12 × 100)
- `n` = Tenure in months