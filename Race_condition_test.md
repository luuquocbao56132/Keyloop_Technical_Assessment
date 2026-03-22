# QA Test Suite — Walkthrough & Results

## Files Created

| File | Purpose |
|------|---------|
| [seed_data.py](file:///home/baaloone/PROJECT/Keyloop_Technical_Assessment/scripts/seed_data.py) | Drops/recreates all tables, populates with 6 technicians, 6 bays, 5 service types, 4 customers, 5 vehicles |
| [test_race_condition.py](file:///home/baaloone/PROJECT/Keyloop_Technical_Assessment/tests/test_race_condition.py) | Fires 3 simultaneous identical booking requests via `asyncio` + `httpx` |
| [test_availability.py](file:///home/baaloone/PROJECT/Keyloop_Technical_Assessment/tests/test_availability.py) | Validates booked slots become unavailable, non-overlapping slots remain open |

---

## Test Results

### 🏁 Race Condition Test — **PASS** ✅

3 concurrent `POST /api/v1/appointments/` requests with identical payload:

| Request | Status | Detail |
|---------|--------|--------|
| #1 | `409 Conflict` 🔒 | Redis lock blocked — "Another booking is currently being processed" |
| #2 | `201 Created` ✅ | Appointment ID: 1, Technician: Alice Smith, Bay: BAY-A |
| #3 | `409 Conflict` 🔒 | Redis lock blocked — "Another booking is currently being processed" |

**Assertion**: 1×201 + 2×409 = **PASS**. The Redis `SET NX EX` lock correctly serialized concurrent requests and prevented double-booking.

---

### 🔍 Availability Test — **PASS** ✅

| Scenario | Expected | Actual | Result |
|----------|----------|--------|--------|
| 1. Initial booking (Brake Inspection, 09:00) | `201` | `201` — Tech: Charlie Brown, Bay: BAY-D | ✅ |
| 2. Duplicate booking at same time | `409` after exhausting resources | 3 bookings succeeded (3 qualified techs × compatible bays), then `409` | ✅ |
| 3. Non-overlapping slot (14:00) | `201` | `201` — Tech: Charlie Brown, Bay: BAY-D | ✅ |

The availability check correctly accounts for multiple technicians and bays — the slot only becomes truly unavailable once **all** qualified resources are exhausted.

---

### 🧪 Existing Unit Tests — **19/19 PASS** ✅

No regressions introduced. All `test_booking.py` and `test_api.py` tests pass in 1.66s.

---

## How to Re-Run

```bash
# 1. Ensure Docker services are running
# (MySQL on :3307, Redis on :6380)

# 2. Seed the database
.venv/bin/python3 scripts/seed_data.py

# 3. Start the API server with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 4. Run tests (in another terminal)
.venv/bin/python3 tests/test_race_condition.py
.venv/bin/python3 tests/test_availability.py
```

> [!IMPORTANT]
> The server must run with `--workers 4` (or more) for the race condition test to be meaningful. A single-worker server serializes all requests, preventing true concurrent lock contention.
