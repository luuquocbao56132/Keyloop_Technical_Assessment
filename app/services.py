"""Core business logic — availability check and appointment creation.

This module implements the critical booking path described in §7 of the
System Design document:

1. Validate input (Pydantic — handled in the route layer).
2. Resolve service duration.
3. Acquire distributed lock (Redis).
4. Real-time availability check (MySQL).
5. Select best resources.
6. Persist appointment (MySQL transaction).
7. Release lock.
"""

from datetime import timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app import models
from app.redis_lock import (
    get_redis_client,
    acquire_booking_lock,
    release_booking_lock,
)


class BookingError(Exception):
    """Base class for booking-related errors."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ResourceNotFoundError(BookingError):
    """Raised when a required resource does not exist."""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=404)


class ConflictError(BookingError):
    """Raised when the requested slot is already booked."""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=409)


# ── Availability Helpers ─────────────────────────────────────────────────────

def find_available_technicians(
    db: Session,
    dealership_id: int,
    service_type_id: int,
    start_time,
    end_time,
) -> list[models.Technician]:
    """Return technicians at the dealership qualified for the service type
    who have NO overlapping confirmed/in-progress appointments."""

    # Subquery: IDs of technicians who ARE busy during [start, end)
    busy_ids = (
        select(models.Appointment.technician_id)
        .where(
            models.Appointment.technician_id.isnot(None),
            models.Appointment.status.in_(["confirmed", "in_progress"]),
            models.Appointment.start_time < end_time,
            models.Appointment.end_time > start_time,
        )
        .scalar_subquery()
    )

    return (
        db.query(models.Technician)
        .join(models.TechnicianSpecialization)
        .filter(
            models.Technician.dealership_id == dealership_id,
            models.Technician.is_active.is_(True),
            models.TechnicianSpecialization.service_type_id == service_type_id,
            models.Technician.id.notin_(busy_ids),
        )
        .all()
    )


def find_available_bays(
    db: Session,
    dealership_id: int,
    service_type_id: int,
    start_time,
    end_time,
) -> list[models.ServiceBay]:
    """Return service bays at the dealership compatible with the service type
    that have NO overlapping confirmed/in-progress appointments."""

    busy_ids = (
        select(models.Appointment.service_bay_id)
        .where(
            models.Appointment.service_bay_id.isnot(None),
            models.Appointment.status.in_(["confirmed", "in_progress"]),
            models.Appointment.start_time < end_time,
            models.Appointment.end_time > start_time,
        )
        .scalar_subquery()
    )

    return (
        db.query(models.ServiceBay)
        .join(models.BayServiceType)
        .filter(
            models.ServiceBay.dealership_id == dealership_id,
            models.ServiceBay.is_active.is_(True),
            models.BayServiceType.service_type_id == service_type_id,
            models.ServiceBay.id.notin_(busy_ids),
        )
        .all()
    )


# ── Main Booking Flow ────────────────────────────────────────────────────────

def create_appointment(
    db: Session,
    dealership_id: int,
    customer_id: int,
    vehicle_id: int,
    service_type_id: int,
    desired_time,
    notes: Optional[str] = None,
) -> models.Appointment:
    """Execute the full booking flow (Steps 2–7 from the design doc).

    Raises:
        ResourceNotFoundError  – if the service type, dealership, customer,
                                  or vehicle does not exist.
        ConflictError          – if no technician or bay is available, or if
                                  the slot lock could not be acquired.
    """

    # ── Step 2: Resolve service duration ─────────────────────────────────
    service_type = (
        db.query(models.ServiceType).filter(models.ServiceType.id == service_type_id).first()
    )
    if not service_type:
        raise ResourceNotFoundError(f"Service type {service_type_id} not found")

    # Validate dealership exists
    dealership = (
        db.query(models.Dealership).filter(models.Dealership.id == dealership_id).first()
    )
    if not dealership:
        raise ResourceNotFoundError(f"Dealership {dealership_id} not found")

    # Validate customer exists
    customer = (
        db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    )
    if not customer:
        raise ResourceNotFoundError(f"Customer {customer_id} not found")

    # Validate vehicle exists
    vehicle = (
        db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    )
    if not vehicle:
        raise ResourceNotFoundError(f"Vehicle {vehicle_id} not found")

    end_time = desired_time + timedelta(minutes=service_type.duration_minutes)

    start_iso = desired_time.isoformat()
    end_iso = end_time.isoformat()

    # ── Step 3: Acquire distributed lock ─────────────────────────────────
    redis_client = get_redis_client()
    lock_id = acquire_booking_lock(
        redis_client, dealership_id, start_iso, end_iso,
    )
    if lock_id is None:
        raise ConflictError(
            "Another booking is currently being processed for this time slot. "
            "Please try again."
        )

    try:
        # ── Step 4: Real-time availability check ─────────────────────────
        available_techs = find_available_technicians(
            db, dealership_id, service_type_id, desired_time, end_time,
        )
        if not available_techs:
            raise ConflictError(
                "No qualified technician is available for the requested time slot."
            )

        available_bays = find_available_bays(
            db, dealership_id, service_type_id, desired_time, end_time,
        )
        if not available_bays:
            raise ConflictError(
                "No compatible service bay is available for the requested time slot."
            )

        # ── Step 5: Select best resources (first available) ──────────────
        technician = available_techs[0]
        service_bay = available_bays[0]

        # ── Step 6: Persist appointment (DB transaction) ─────────────────
        appointment = models.Appointment(
            dealership_id=dealership_id,
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            service_type_id=service_type_id,
            technician_id=technician.id,
            service_bay_id=service_bay.id,
            start_time=desired_time,
            end_time=end_time,
            status="confirmed",
            notes=notes,
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        return appointment

    except Exception:
        db.rollback()
        raise

    finally:
        # ── Step 7: Release lock ─────────────────────────────────────────
        release_booking_lock(redis_client, dealership_id, start_iso, end_iso, lock_id)


def list_appointments(
    db: Session,
    dealership_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[models.Appointment]:
    """List confirmed appointments with optional filters."""
    query = db.query(models.Appointment)
    if dealership_id is not None:
        query = query.filter(models.Appointment.dealership_id == dealership_id)
    if status is not None:
        query = query.filter(models.Appointment.status == status)
    else:
        # By default, exclude cancelled
        query = query.filter(models.Appointment.status != "cancelled")
    return query.order_by(models.Appointment.start_time).all()
