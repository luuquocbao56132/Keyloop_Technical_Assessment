#!/usr/bin/env python3
"""Availability Check Test — Verify that booked slots become unavailable.

Scenarios:
  1. Book a time slot successfully (201).
  2. Attempt the exact same booking again → must be 409 (slot occupied).
  3. Book a NON-overlapping time slot → must succeed (201).

Usage:
    # Ensure the API server is running and DB is freshly seeded:
    #   python scripts/seed_data.py
    #   uvicorn app.main:app --port 8000
    python tests/test_availability.py
"""

import asyncio
import sys
import os

import httpx

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ENDPOINT = f"{BASE_URL}/api/v1/appointments/"


# ── Test Scenarios ───────────────────────────────────────────────────────────


async def run_availability_tests() -> bool:
    """Run all availability test scenarios and return True if all pass."""

    print("=" * 70)
    print("  🔍  AVAILABILITY CHECK TEST — Post-Booking Slot Verification")
    print("=" * 70)
    print(f"\n  Target: {ENDPOINT}\n")

    all_passed = True
    async with httpx.AsyncClient(timeout=30.0) as client:

        # ── Scenario 1: Initial booking should succeed ───────────────────
        print("-" * 70)
        print("  SCENARIO 1: Initial booking (should succeed with 201)")
        print("-" * 70)

        first_booking = {
            "dealership_id": 1,
            "customer_id": 2,
            "vehicle_id": 2,
            "service_type_id": 4,          # Brake Inspection (90 min)
            "desired_time": "2026-07-10T09:00:00",
            "notes": "Availability test — first booking",
        }
        resp1 = await client.post(ENDPOINT, json=first_booking)
        print(f"  Status: {resp1.status_code}")

        if resp1.status_code == 201:
            data1 = resp1.json()
            tech_id = data1["technician_id"]
            bay_id = data1["service_bay_id"]
            print(f"  ✅  Booking created — ID: {data1['id']}")
            print(f"      Technician: {data1.get('technician_name')} (id={tech_id})")
            print(f"      Bay:        {data1.get('service_bay_number')} (id={bay_id})")
            print(f"      Time:       {data1['start_time']} → {data1['end_time']}")
        else:
            print(f"  ❌  FAIL — Expected 201, got {resp1.status_code}")
            print(f"      Detail: {resp1.json().get('detail', resp1.text)}")
            all_passed = False

        # ── Scenario 2: Duplicate booking should fail (409) ──────────────
        print()
        print("-" * 70)
        print("  SCENARIO 2: Duplicate booking at same time (should fail with 409)")
        print("-" * 70)

        duplicate_booking = {
            "dealership_id": 1,
            "customer_id": 3,           # different customer but same slot
            "vehicle_id": 3,
            "service_type_id": 4,       # same service type (Brake Inspection)
            "desired_time": "2026-07-10T09:00:00",  # exact same time
            "notes": "Availability test — duplicate attempt",
        }
        resp2 = await client.post(ENDPOINT, json=duplicate_booking)
        print(f"  Status: {resp2.status_code}")

        if resp2.status_code == 409:
            print(f"  ✅  Correctly rejected — {resp2.json().get('detail', 'N/A')}")
        elif resp2.status_code == 201:
            data2 = resp2.json()
            # It might succeed if there are other available technicians/bays.
            # That's valid! Let's keep booking until we exhaust resources.
            print(f"  ℹ️   Booking succeeded (other resources available).")
            print(f"      Technician: {data2.get('technician_name')} (id={data2['technician_id']})")
            print(f"      Bay:        {data2.get('service_bay_number')} (id={data2['service_bay_id']})")
            # We need to exhaust all resources to test a true 409
            print("\n  → Exhausting all available technicians and bays for this slot…")
            booked_count = 2
            while True:
                extra_booking = {
                    "dealership_id": 1,
                    "customer_id": 3,
                    "vehicle_id": 3,
                    "service_type_id": 4,
                    "desired_time": "2026-07-10T09:00:00",
                    "notes": f"Availability test — exhaust attempt #{booked_count + 1}",
                }
                resp_extra = await client.post(ENDPOINT, json=extra_booking)
                booked_count += 1
                if resp_extra.status_code == 409:
                    print(f"  ✅  After {booked_count - 1} bookings, "
                          f"slot is now FULL — 409: {resp_extra.json().get('detail', 'N/A')}")
                    break
                elif resp_extra.status_code == 201:
                    d = resp_extra.json()
                    print(f"      Booking #{booked_count - 1} succeeded — "
                          f"Tech: {d.get('technician_name')}, Bay: {d.get('service_bay_number')}")
                    if booked_count > 20:
                        print("  ❌  FAIL — Over 20 bookings succeeded; resources seem unlimited.")
                        all_passed = False
                        break
                else:
                    print(f"  ❌  FAIL — Unexpected status {resp_extra.status_code}")
                    all_passed = False
                    break
        else:
            print(f"  ❌  FAIL — Expected 409, got {resp2.status_code}")
            print(f"      Body: {resp2.text}")
            all_passed = False

        # ── Scenario 3: Non-overlapping booking should succeed ───────────
        print()
        print("-" * 70)
        print("  SCENARIO 3: Non-overlapping time slot (should succeed with 201)")
        print("-" * 70)

        non_overlap_booking = {
            "dealership_id": 1,
            "customer_id": 4,
            "vehicle_id": 4,
            "service_type_id": 4,          # same service type
            "desired_time": "2026-07-10T14:00:00",  # well after the 90-min window
            "notes": "Availability test — non-overlapping slot",
        }
        resp3 = await client.post(ENDPOINT, json=non_overlap_booking)
        print(f"  Status: {resp3.status_code}")

        if resp3.status_code == 201:
            data3 = resp3.json()
            print(f"  ✅  Non-overlapping booking succeeded — ID: {data3['id']}")
            print(f"      Technician: {data3.get('technician_name')} (id={data3['technician_id']})")
            print(f"      Bay:        {data3.get('service_bay_number')} (id={data3['service_bay_id']})")
            print(f"      Time:       {data3['start_time']} → {data3['end_time']}")
        else:
            print(f"  ❌  FAIL — Expected 201, got {resp3.status_code}")
            print(f"      Detail: {resp3.json().get('detail', resp3.text)}")
            all_passed = False

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    if all_passed:
        print("  ✅  ALL AVAILABILITY TESTS PASSED")
    else:
        print("  ❌  SOME AVAILABILITY TESTS FAILED")
    print("=" * 70)

    return all_passed


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    passed = asyncio.run(run_availability_tests())
    sys.exit(0 if passed else 1)
