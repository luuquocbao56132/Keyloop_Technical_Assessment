"""API routes for the Unified Service Scheduler."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentListResponse,
)
from app.services import (
    create_appointment,
    list_appointments,
    BookingError,
)
from app import models

router = APIRouter(prefix="/api/v1", tags=["Appointments"])


def _appointment_to_response(appt: models.Appointment) -> AppointmentResponse:
    """Map an ORM Appointment to the response schema, including extras."""
    tech_name = None
    if appt.technician:
        tech_name = f"{appt.technician.first_name} {appt.technician.last_name}"

    bay_number = appt.service_bay.bay_number if appt.service_bay else None
    svc_name = appt.service_type.name if appt.service_type else None

    return AppointmentResponse(
        id=appt.id,
        dealership_id=appt.dealership_id,
        customer_id=appt.customer_id,
        vehicle_id=appt.vehicle_id,
        service_type_id=appt.service_type_id,
        technician_id=appt.technician_id,
        service_bay_id=appt.service_bay_id,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        notes=appt.notes,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
        technician_name=tech_name,
        service_bay_number=bay_number,
        service_type_name=svc_name,
    )


# ── POST /appointments/ ─────────────────────────────────────────────────────

@router.post("/appointments/", response_model=AppointmentResponse, status_code=201)
def create_booking(payload: AppointmentCreate, db: Session = Depends(get_db)):
    """Create a new service appointment (Resource Constrained Booking).

    Acquires a Redis distributed lock, checks real-time availability of
    both a qualified Technician and a compatible ServiceBay, then persists
    the confirmed appointment.
    """
    try:
        appointment = create_appointment(
            db=db,
            dealership_id=payload.dealership_id,
            customer_id=payload.customer_id,
            vehicle_id=payload.vehicle_id,
            service_type_id=payload.service_type_id,
            desired_time=payload.desired_time,
            notes=payload.notes,
        )
        return _appointment_to_response(appointment)

    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ── GET /appointments/ ───────────────────────────────────────────────────────

@router.get("/appointments/", response_model=AppointmentListResponse)
def get_appointments(
    dealership_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List confirmed appointments with optional dealership / status filters."""
    appointments = list_appointments(db, dealership_id=dealership_id, status=status)
    return AppointmentListResponse(
        total=len(appointments),
        appointments=[_appointment_to_response(a) for a in appointments],
    )


# ── Resource listing endpoints (for frontend dropdowns) ──────────────────────

@router.get("/dealerships/", tags=["Resources"])
def get_dealerships(db: Session = Depends(get_db)):
    """List all dealerships."""
    rows = db.query(models.Dealership).all()
    return [
        {"id": d.id, "name": d.name, "address": d.address}
        for d in rows
    ]


@router.get("/customers/", tags=["Resources"])
def get_customers(db: Session = Depends(get_db)):
    """List all customers."""
    rows = db.query(models.Customer).all()
    return [
        {"id": c.id, "first_name": c.first_name, "last_name": c.last_name, "email": c.email}
        for c in rows
    ]


@router.get("/vehicles/", tags=["Resources"])
def get_vehicles(db: Session = Depends(get_db)):
    """List all vehicles with owner info."""
    rows = db.query(models.Vehicle).all()
    return [
        {
            "id": v.id,
            "customer_id": v.customer_id,
            "make": v.make,
            "model": v.model,
            "year": v.year,
            "vin": v.vin,
            "license_plate": v.license_plate,
        }
        for v in rows
    ]


@router.get("/service-types/", tags=["Resources"])
def get_service_types(db: Session = Depends(get_db)):
    """List all service types."""
    rows = db.query(models.ServiceType).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "duration_minutes": s.duration_minutes,
            "base_price": float(s.base_price),
        }
        for s in rows
    ]
