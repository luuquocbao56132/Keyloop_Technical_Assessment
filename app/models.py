"""SQLAlchemy ORM models — mirrors the ERD in SYSTEM_DESIGN.md."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Numeric,
    Enum,
    Time,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ── Dealerships ──────────────────────────────────────────────────────────────

class Dealership(Base):
    __tablename__ = "dealerships"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    phone = Column(String(50))
    operating_hours_start = Column(Time, nullable=False)
    operating_hours_end = Column(Time, nullable=False)
    timezone = Column(String(50), default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    technicians = relationship("Technician", back_populates="dealership")
    service_bays = relationship("ServiceBay", back_populates="dealership")
    appointments = relationship("Appointment", back_populates="dealership")


# ── Customers ────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicles = relationship("Vehicle", back_populates="customer")
    appointments = relationship("Appointment", back_populates="customer")


# ── Vehicles ─────────────────────────────────────────────────────────────────

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    vin = Column(String(17), unique=True, nullable=False)
    license_plate = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="vehicles")
    appointments = relationship("Appointment", back_populates="vehicle")


# ── Service Types ────────────────────────────────────────────────────────────

class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    technician_specializations = relationship(
        "TechnicianSpecialization", back_populates="service_type"
    )
    bay_service_types = relationship("BayServiceType", back_populates="service_type")
    appointments = relationship("Appointment", back_populates="service_type")


# ── Technicians ──────────────────────────────────────────────────────────────

class Technician(Base):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealership = relationship("Dealership", back_populates="technicians")
    specializations = relationship(
        "TechnicianSpecialization", back_populates="technician"
    )
    appointments = relationship("Appointment", back_populates="technician")


class TechnicianSpecialization(Base):
    __tablename__ = "technician_specializations"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False)

    technician = relationship("Technician", back_populates="specializations")
    service_type = relationship("ServiceType", back_populates="technician_specializations")


# ── Service Bays ─────────────────────────────────────────────────────────────

class ServiceBay(Base):
    __tablename__ = "service_bays"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)
    bay_number = Column(String(20), nullable=False)
    bay_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealership = relationship("Dealership", back_populates="service_bays")
    bay_service_types = relationship("BayServiceType", back_populates="service_bay")
    appointments = relationship("Appointment", back_populates="service_bay")


class BayServiceType(Base):
    __tablename__ = "bay_service_types"

    id = Column(Integer, primary_key=True, index=True)
    service_bay_id = Column(Integer, ForeignKey("service_bays.id"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False)

    service_bay = relationship("ServiceBay", back_populates="bay_service_types")
    service_type = relationship("ServiceType", back_populates="bay_service_types")


# ── Appointments ─────────────────────────────────────────────────────────────

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("technician_id", "start_time", name="uq_technician_slot"),
        UniqueConstraint("service_bay_id", "start_time", name="uq_bay_slot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    service_bay_id = Column(Integer, ForeignKey("service_bays.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(
        Enum("pending", "confirmed", "in_progress", "completed", "cancelled",
             name="appointment_status"),
        default="confirmed",
        nullable=False,
    )
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealership = relationship("Dealership", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
    vehicle = relationship("Vehicle", back_populates="appointments")
    service_type = relationship("ServiceType", back_populates="appointments")
    technician = relationship("Technician", back_populates="appointments")
    service_bay = relationship("ServiceBay", back_populates="appointments")
