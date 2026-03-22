"""Pydantic schemas for request validation and response serialization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Appointment Schemas ──────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    """Request body for POST /appointments/."""

    dealership_id: int = Field(..., description="ID of the dealership")
    customer_id: int = Field(..., description="ID of the customer")
    vehicle_id: int = Field(..., description="ID of the vehicle to be serviced")
    service_type_id: int = Field(..., description="ID of the service type")
    desired_time: datetime = Field(
        ..., description="Desired appointment start time (ISO 8601 UTC)"
    )
    notes: Optional[str] = Field(None, description="Optional booking notes")


class AppointmentResponse(BaseModel):
    """Response body for appointment endpoints."""

    id: int
    dealership_id: int
    customer_id: int
    vehicle_id: int
    service_type_id: int
    technician_id: int
    service_bay_id: int
    start_time: datetime
    end_time: datetime
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Extra detail fields (populated from relationships)
    technician_name: Optional[str] = None
    service_bay_number: Optional[str] = None
    service_type_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    """Paginated list of appointments."""

    total: int
    appointments: list[AppointmentResponse]


# ── Seed-Data Helper Schemas ─────────────────────────────────────────────────

class DealershipCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    operating_hours_start: str = "08:00"
    operating_hours_end: str = "17:00"
    timezone: str = "UTC"


class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None


class VehicleCreate(BaseModel):
    customer_id: int
    make: str
    model: str
    year: int
    vin: str
    license_plate: Optional[str] = None


class ServiceTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    base_price: float


class TechnicianCreate(BaseModel):
    dealership_id: int
    first_name: str
    last_name: str
    employee_id: str
    service_type_ids: list[int] = Field(
        default_factory=list,
        description="IDs of service types this technician is qualified for",
    )


class ServiceBayCreate(BaseModel):
    dealership_id: int
    bay_number: str
    bay_type: Optional[str] = None
    service_type_ids: list[int] = Field(
        default_factory=list,
        description="IDs of service types this bay supports",
    )


# ── Generic message ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    detail: str
