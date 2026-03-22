# The Unified Service Scheduler

> **Keyloop Technical Assessment — Scenario A**
> A resource-constrained appointment booking system with real-time availability checks and Redis distributed locking.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python 3.11+) |
| Database | MySQL 8.0 (InnoDB) |
| Cache / Locks | Redis 7 |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic 2.0 |
| Testing | Pytest + HTTPX |
| Containerisation | Docker Compose |

---

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── config.py          # Environment-based configuration
│   ├── database.py        # SQLAlchemy engine & session
│   ├── models.py          # ORM models (Dealership, Technician, ServiceBay, Appointment…)
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── redis_lock.py      # Distributed lock (SET NX EX + Lua safe release)
│   ├── services.py        # Core booking logic (availability check + create)
│   ├── routes.py          # API endpoints (POST & GET /appointments/)
│   ├── seed.py            # Sample data seeder
│   └── main.py            # FastAPI application entry point
├── templates/
│   └── index.html         # Client-side test harness (HTML/JS)
├── tests/
│   ├── conftest.py        # Pytest fixtures (SQLite + Redis mock)
│   ├── test_booking.py    # Business logic tests
│   └── test_api.py        # API integration tests
├── docker-compose.yml     # MySQL + Redis containers
├── requirements.txt       # Python dependencies
├── SYSTEM_DESIGN.md       # System design document
└── README.md              # ← You are here
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**

### 1️⃣ Start the Databases

```bash
docker compose up -d
```

This starts:
- **MySQL** on `localhost:3306` (user: `scheduler_user`, password: `scheduler_pass`, database: `scheduler_db`)
- **Redis** on `localhost:6379`

Verify the containers are healthy:

```bash
docker compose ps
```

### 2️⃣ Install Python Dependencies

```bash
# (Recommended) Create a virtual environment first
python -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 3️⃣ Run the FastAPI Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
1. **Auto-create** all database tables on first run.
2. **Seed** sample data (1 dealership, 1 customer, 1 vehicle, 3 service types, 2 technicians, 2 service bays).

### 4️⃣ Open the Application

| URL | Description |
|-----|-------------|
| [http://localhost:8000](http://localhost:8000) | **Test Harness** — HTML/JS booking form |
| [http://localhost:8000/docs](http://localhost:8000/docs) | **Swagger UI** — Interactive API documentation |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | **ReDoc** — Alternative API docs |
| [http://localhost:8000/health](http://localhost:8000/health) | **Health check** |

---

## API Endpoints

### `POST /api/v1/appointments/`

Create a new service appointment (resource-constrained booking).

**Request body:**
```json
{
  "dealership_id": 1,
  "customer_id": 1,
  "vehicle_id": 1,
  "service_type_id": 1,
  "desired_time": "2026-04-01T10:00:00",
  "notes": "Please check brakes too"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "dealership_id": 1,
  "customer_id": 1,
  "vehicle_id": 1,
  "service_type_id": 1,
  "technician_id": 1,
  "service_bay_id": 1,
  "start_time": "2026-04-01T10:00:00",
  "end_time": "2026-04-01T11:00:00",
  "status": "confirmed",
  "technician_name": "Alice Smith",
  "service_bay_number": "BAY-A",
  "service_type_name": "Oil Change",
  "notes": "Please check brakes too",
  "created_at": "...",
  "updated_at": "..."
}
```

**Error responses:**
- `404` — Resource not found (dealership, customer, vehicle, or service type)
- `409` — Conflict (no available technician/bay, or lock contention)
- `422` — Validation error

### `GET /api/v1/appointments/`

List confirmed appointments. Optional query parameters: `dealership_id`, `status`.

---

## Running Tests

Tests use an **in-memory SQLite database** and a **mocked Redis client**, so no Docker containers are required.

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run only the business logic tests
pytest tests/test_booking.py -v

# Run only the API integration tests
pytest tests/test_api.py -v
```

### What the Tests Validate

| Test Suite | Validates |
|-----------|-----------|
| `test_booking.py` | Successful booking, overlapping time rejection, Redis lock contention, missing resource errors, availability helpers |
| `test_api.py` | POST endpoint (201, 404, 422), GET endpoint (empty + populated), health check |

---

## How the Booking Flow Works

1. **Input validation** — Pydantic schemas validate the request.
2. **Resolve duration** — Fetch `duration_minutes` for the service type from MySQL.
3. **Acquire distributed lock** — Redis `SET NX EX` on `lock:dealership:{id}:slot:{start}:{end}`.
4. **Availability check** — Query MySQL for qualified, non-busy technicians AND compatible, non-busy service bays.
5. **Select resources** — Pick the first available technician and bay.
6. **Persist appointment** — Insert with `status = "confirmed"` in a DB transaction.
7. **Release lock** — Lua compare-and-delete ensures only the owner releases.

> See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full architectural documentation including ERD, sequence diagrams, and concurrency control details.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://scheduler_user:scheduler_pass@localhost:3306/scheduler_db` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `LOCK_TTL_SECONDS` | `10` | Distributed lock TTL |
| `LOCK_RETRY_DELAY` | `0.2` | Seconds between lock retry attempts |
| `LOCK_MAX_RETRIES` | `3` | Maximum lock acquisition retries |

---

## Stopping the Services

```bash
docker compose down          # Stop containers
docker compose down -v       # Stop and remove volumes (wipes data)
```
