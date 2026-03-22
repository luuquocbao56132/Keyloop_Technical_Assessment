#!/usr/bin/env python3
"""Race Condition Test — Verify Redis distributed locking prevents double-booking.

Fires 3 simultaneous identical POST requests to /api/v1/appointments/.
All requests attempt to book the exact same vehicle, service type, and time.

Expected result:
  • Exactly 1 request  → 201 Created
  • Exactly 2 requests → 409 Conflict

Usage:
    # Ensure the API server is running:  uvicorn app.main:app --port 8000
    python tests/test_race_condition.py
"""

import asyncio
import sys
import os

import httpx

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ENDPOINT = f"{BASE_URL}/api/v1/appointments/"
NUM_CONCURRENT_REQUESTS = 3

# All requests send the same booking payload
BOOKING_PAYLOAD = {
    "dealership_id": 1,
    "customer_id": 1,
    "vehicle_id": 1,
    "service_type_id": 1,          # Oil Change (60 min)
    "desired_time": "2026-06-15T10:00:00",
    "notes": "Race condition test — concurrent booking attempt",
}


# ── Test Logic ───────────────────────────────────────────────────────────────


async def _post_booking(client: httpx.AsyncClient, request_id: int) -> dict:
    """Fire a single POST and return structured result."""
    try:
        resp = await client.post(ENDPOINT, json=BOOKING_PAYLOAD)
        return {
            "request_id": request_id,
            "status_code": resp.status_code,
            "body": resp.json(),
        }
    except Exception as exc:
        return {
            "request_id": request_id,
            "status_code": -1,
            "body": {"error": str(exc)},
        }


async def run_race_condition_test() -> bool:
    """Execute the concurrent booking test and return True if it passes."""

    print("=" * 70)
    print("  🏁  RACE CONDITION TEST — Concurrent Booking Attempt")
    print("=" * 70)
    print(f"\n  Target:   {ENDPOINT}")
    print(f"  Payload:  vehicle_id={BOOKING_PAYLOAD['vehicle_id']}, "
          f"service_type_id={BOOKING_PAYLOAD['service_type_id']}, "
          f"desired_time={BOOKING_PAYLOAD['desired_time']}")
    print(f"  Concurrent requests: {NUM_CONCURRENT_REQUESTS}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fire all requests simultaneously
        tasks = [
            _post_booking(client, i + 1)
            for i in range(NUM_CONCURRENT_REQUESTS)
        ]
        results = await asyncio.gather(*tasks)

    # ── Analyse results ──────────────────────────────────────────────────
    print("-" * 70)
    print("  RESULTS")
    print("-" * 70)

    for r in sorted(results, key=lambda x: x["request_id"]):
        status = r["status_code"]
        emoji = "✅" if status == 201 else ("🔒" if status == 409 else "❌")
        print(f"  Request #{r['request_id']}  →  HTTP {status}  {emoji}")
        if status == 201:
            body = r["body"]
            print(f"      Appointment ID: {body.get('id')}")
            print(f"      Technician:     {body.get('technician_name')} (id={body.get('technician_id')})")
            print(f"      Bay:            {body.get('service_bay_number')} (id={body.get('service_bay_id')})")
        elif status == 409:
            print(f"      Detail: {r['body'].get('detail', 'N/A')}")
        else:
            print(f"      Body: {r['body']}")

    # ── Assertions ───────────────────────────────────────────────────────
    status_codes = [r["status_code"] for r in results]
    count_201 = status_codes.count(201)
    count_409 = status_codes.count(409)

    print()
    print("-" * 70)
    print("  ASSERTIONS")
    print("-" * 70)
    print(f"  201 Created responses:  {count_201}  (expected: 1)")
    print(f"  409 Conflict responses: {count_409}  (expected: {NUM_CONCURRENT_REQUESTS - 1})")

    passed = (count_201 == 1) and (count_409 == NUM_CONCURRENT_REQUESTS - 1)

    print()
    if passed:
        print("  ✅  PASS — Redis distributed lock correctly prevented double-booking!")
    else:
        print("  ❌  FAIL — Race condition detected! Expected exactly 1×201 and "
              f"{NUM_CONCURRENT_REQUESTS - 1}×409, "
              f"got {count_201}×201 and {count_409}×409.")
        # Detailed failure info
        unexpected = [r for r in results if r["status_code"] not in (201, 409)]
        if unexpected:
            print(f"  ⚠️  Unexpected status codes: "
                  f"{[r['status_code'] for r in unexpected]}")

    print("=" * 70)
    return passed


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    passed = asyncio.run(run_race_condition_test())
    sys.exit(0 if passed else 1)
