"""Tests for the core booking business logic.

Validates:
1. Successful appointment creation.
2. Overlapping time-slot rejection (double-booking prevention).
3. Missing resource errors (non-existent service type, dealership, etc.).
"""

from datetime import datetime, timedelta

import pytest

from app.services import (
    create_appointment,
    find_available_technicians,
    find_available_bays,
    ConflictError,
    ResourceNotFoundError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Successful Booking
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuccessfulBooking:
    """A booking should succeed when all resources exist and are available."""

    def test_creates_confirmed_appointment(self, seeded_db, mock_redis):
        """Happy path: create an appointment and check its attributes."""
        desired = datetime(2026, 4, 1, 10, 0)

        appt = create_appointment(
            db=seeded_db,
            dealership_id=1,
            customer_id=1,
            vehicle_id=1,
            service_type_id=1,
            desired_time=desired,
        )

        assert appt.id is not None
        assert appt.status == "confirmed"
        assert appt.technician_id == 1
        assert appt.service_bay_id == 1
        assert appt.start_time == desired
        assert appt.end_time == desired + timedelta(minutes=60)

    def test_redis_lock_acquired_and_released(self, seeded_db, mock_redis):
        """Verify that the Redis lock is acquired during booking and released after."""
        desired = datetime(2026, 4, 1, 10, 0)

        create_appointment(
            db=seeded_db,
            dealership_id=1,
            customer_id=1,
            vehicle_id=1,
            service_type_id=1,
            desired_time=desired,
        )

        # Lock was acquired (set called with nx=True)
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs[1].get("nx") is True

        # Lock was released (eval called with Lua script)
        mock_redis.eval.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Overlapping Time-Slot Rejection
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverlappingTimeRejection:
    """Double-booking the same technician or bay must be rejected."""

    def test_rejects_overlapping_technician(self, seeded_db, mock_redis):
        """If the only technician is already booked, a ConflictError is raised."""
        desired = datetime(2026, 4, 2, 10, 0)

        # First booking succeeds
        create_appointment(
            db=seeded_db,
            dealership_id=1,
            customer_id=1,
            vehicle_id=1,
            service_type_id=1,
            desired_time=desired,
        )

        # Second booking at an overlapping time must fail
        overlap_time = desired + timedelta(minutes=30)  # still within the 60-min window
        with pytest.raises(ConflictError, match="technician"):
            create_appointment(
                db=seeded_db,
                dealership_id=1,
                customer_id=1,
                vehicle_id=1,
                service_type_id=1,
                desired_time=overlap_time,
            )

    def test_allows_non_overlapping_booking(self, seeded_db, mock_redis):
        """Bookings that don't overlap should both succeed."""
        first_time = datetime(2026, 4, 3, 9, 0)
        second_time = datetime(2026, 4, 3, 11, 0)  # after the 60-min window

        appt1 = create_appointment(
            db=seeded_db,
            dealership_id=1,
            customer_id=1,
            vehicle_id=1,
            service_type_id=1,
            desired_time=first_time,
        )
        appt2 = create_appointment(
            db=seeded_db,
            dealership_id=1,
            customer_id=1,
            vehicle_id=1,
            service_type_id=1,
            desired_time=second_time,
        )

        assert appt1.id != appt2.id
        assert appt1.status == "confirmed"
        assert appt2.status == "confirmed"

    def test_redis_lock_contention(self, seeded_db, mock_redis):
        """When the Redis lock cannot be acquired, a ConflictError is raised."""
        mock_redis.set.return_value = False  # simulate lock already held

        with pytest.raises(ConflictError, match="Another booking"):
            create_appointment(
                db=seeded_db,
                dealership_id=1,
                customer_id=1,
                vehicle_id=1,
                service_type_id=1,
                desired_time=datetime(2026, 4, 4, 10, 0),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Missing Resource Errors
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissingResourceErrors:
    """Booking must fail with a clear error if a referenced resource is missing."""

    def test_missing_service_type(self, seeded_db, mock_redis):
        with pytest.raises(ResourceNotFoundError, match="Service type"):
            create_appointment(
                db=seeded_db,
                dealership_id=1,
                customer_id=1,
                vehicle_id=1,
                service_type_id=999,
                desired_time=datetime(2026, 4, 5, 10, 0),
            )

    def test_missing_dealership(self, seeded_db, mock_redis):
        with pytest.raises(ResourceNotFoundError, match="Dealership"):
            create_appointment(
                db=seeded_db,
                dealership_id=999,
                customer_id=1,
                vehicle_id=1,
                service_type_id=1,
                desired_time=datetime(2026, 4, 5, 10, 0),
            )

    def test_missing_customer(self, seeded_db, mock_redis):
        with pytest.raises(ResourceNotFoundError, match="Customer"):
            create_appointment(
                db=seeded_db,
                dealership_id=1,
                customer_id=999,
                vehicle_id=1,
                service_type_id=1,
                desired_time=datetime(2026, 4, 5, 10, 0),
            )

    def test_missing_vehicle(self, seeded_db, mock_redis):
        with pytest.raises(ResourceNotFoundError, match="Vehicle"):
            create_appointment(
                db=seeded_db,
                dealership_id=1,
                customer_id=1,
                vehicle_id=999,
                service_type_id=1,
                desired_time=datetime(2026, 4, 5, 10, 0),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Availability Helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestAvailabilityHelpers:
    """Unit tests for the availability query functions."""

    def test_finds_available_technician(self, seeded_db):
        start = datetime(2026, 5, 1, 10, 0)
        end = datetime(2026, 5, 1, 11, 0)

        techs = find_available_technicians(seeded_db, 1, 1, start, end)
        assert len(techs) == 1
        assert techs[0].id == 1

    def test_finds_available_bay(self, seeded_db):
        start = datetime(2026, 5, 1, 10, 0)
        end = datetime(2026, 5, 1, 11, 0)

        bays = find_available_bays(seeded_db, 1, 1, start, end)
        assert len(bays) == 1
        assert bays[0].id == 1

    def test_no_technician_for_wrong_service(self, seeded_db):
        """Technician is not qualified for service_type_id=99."""
        start = datetime(2026, 5, 1, 10, 0)
        end = datetime(2026, 5, 1, 11, 0)

        techs = find_available_technicians(seeded_db, 1, 99, start, end)
        assert len(techs) == 0

    def test_no_bay_for_wrong_service(self, seeded_db):
        """Bay is not compatible with service_type_id=99."""
        start = datetime(2026, 5, 1, 10, 0)
        end = datetime(2026, 5, 1, 11, 0)

        bays = find_available_bays(seeded_db, 1, 99, start, end)
        assert len(bays) == 0
