# Walkthrough — The Unified Service Scheduler

## Overview

Implemented the complete backend service for **Keyloop Technical Assessment — Scenario A** across 7 steps, covering infrastructure, database, business logic, API, test harness, tests, and documentation.

## Project Structure

```
├── app/
│   ├── config.py          # Env-var configuration
│   ├── database.py        # SQLAlchemy engine & session
│   ├── models.py          # 9 ORM models (ERD from SYSTEM_DESIGN.md)
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── redis_lock.py      # SET NX EX + Lua safe release
│   ├── services.py        # Core booking logic (7-step critical path)
│   ├── routes.py          # POST & GET /api/v1/appointments/
│   ├── seed.py            # Sample data seeder
│   └── main.py            # FastAPI entry point
├── templates/index.html   # Dark-themed HTML/JS test harness
├── tests/
│   ├── conftest.py        # SQLite + mocked Redis fixtures
│   ├── test_booking.py    # 13 business logic tests
│   └── test_api.py        # 6 API integration tests
├── docker-compose.yml     # MySQL 8 + Redis 7
├── requirements.txt
└── README.md
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Redis `SET NX EX` lock | Prevents race conditions between concurrent booking requests for the same slot |
| Lua compare-and-delete | Ensures only the lock owner can release (avoids accidental release by different requests) |
| `UniqueConstraint` on `(technician_id, start_time)` and `(service_bay_id, start_time)` | Defence-in-depth: DB-level guard against double-booking if Redis fails |
| SQLite + mocked Redis for tests | Tests run without Docker containers, making CI simple |
| `TESTING=1` env guard | Prevents `app/main.py` startup event from connecting to MySQL during tests |

## Test Results

**19/19 passed** ✅

| Suite | Tests | What's validated |
|-------|-------|-----------------|
| `test_booking.py` | 13 | Successful booking, overlapping technician/bay rejection, Redis lock contention, missing resource errors (4 types), availability helpers |
| `test_api.py` | 6 | POST 201/404/422, GET empty/populated list, health check |

## Browser Testing Proof

A browser subagent was used to end-to-end test the running server:
1. It successfully submitted the form and created **Appointment #2**.
2. It clicked **Refresh List**, verifying the full stack works and it popped up in the list.
3. It attempted to book a 3rd appointment at the same slot, triggering a **409 Conflict** as both bays were now occupied.

## Backend Changes
Added 4 new GET endpoints to app/routes.py:

    GET /api/v1/dealerships/

    GET /api/v1/customers/

    GET /api/v1/vehicles/

    GET /api/v1/service-types/

## Frontend Changes (templates/index.html)
1. Dynamic Dropdowns — All ID fields are now **select** dropdowns populated via fetch() on page load:

        Dealership: "Dealership #1 — Keyloop Downtown Service Centre"

        Vehicle: "Vehicle #1 — 2022 Toyota Corolla (AB12 CDE)"

        Customer: Auto-linked from vehicle selection — "Customer #1 — John Doe" (disabled, read-only)

        Service Type: "Oil Change (60 min — £49.99)"
2. Notification Banner — A dismissible alert appears above the form:

        🟢 Green for success: "Appointment #1 Confirmed! Technician: Alice Smith · Bay: BAY-A…"

        🔴 Red for 409 conflicts: "Booking Failed — Resource Conflict: No qualified technician is available…"

        🟡 Yellow for 422 validation errors

3. Loading State — Button shows spinner + "Booking…" text while the POST is in flight, then re-enables.

## Multi-bay resource assignment logic

When booking the second appointment, the system correctly noticed that `BAY-A` (used by Appointment #1) was occupied and dynamically assigned `BAY-B` to the new appointment. When a third was attempted, it rejected it because no bays were left.

## How to Run

```bash
# 1. Start DBs
docker compose up -d

# 2. Install deps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Run server
uvicorn app.main:app --reload --port 8000

# 4. Run tests
pytest tests/ -v
```

Test harness at [http://localhost:8000](http://localhost:8000), Swagger at [http://localhost:8000/docs](http://localhost:8000/docs).
