"""Seed the database with sample data for local development / demo."""

from datetime import time

from sqlalchemy.orm import Session

from app import models


def seed_database(db: Session) -> None:
    """Insert sample dealership, customer, vehicle, service types,
    technicians, and service bays so the test harness works out-of-the-box.

    This function is *idempotent*: it skips seeding when data already exists.
    """
    # Check if already seeded
    if db.query(models.Dealership).first():
        return

    # ── Dealership ───────────────────────────────────────────────────────
    dealership = models.Dealership(
        id=1,
        name="Keyloop Downtown Service Centre",
        address="123 Main Street, London, UK",
        phone="+44 20 7946 0958",
        operating_hours_start=time(8, 0),
        operating_hours_end=time(17, 0),
        timezone="UTC",
    )
    db.add(dealership)

    # ── Customer ─────────────────────────────────────────────────────────
    customer = models.Customer(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+44 7700 900000",
    )
    db.add(customer)

    # ── Vehicle ──────────────────────────────────────────────────────────
    vehicle = models.Vehicle(
        id=1,
        customer_id=1,
        make="Toyota",
        model="Corolla",
        year=2022,
        vin="1HGBH41JXMN109186",
        license_plate="AB12 CDE",
    )
    db.add(vehicle)

    # ── Service Types ────────────────────────────────────────────────────
    oil_change = models.ServiceType(
        id=1, name="Oil Change", description="Standard oil change service",
        duration_minutes=60, base_price=49.99,
    )
    full_service = models.ServiceType(
        id=2, name="Full Service", description="Comprehensive vehicle service",
        duration_minutes=180, base_price=199.99,
    )
    tyre_rotation = models.ServiceType(
        id=3, name="Tyre Rotation", description="Rotate all four tyres",
        duration_minutes=45, base_price=29.99,
    )
    db.add_all([oil_change, full_service, tyre_rotation])

    # ── Technicians ──────────────────────────────────────────────────────
    tech_alice = models.Technician(
        id=1, dealership_id=1, first_name="Alice", last_name="Smith",
        employee_id="EMP001", is_active=True,
    )
    tech_bob = models.Technician(
        id=2, dealership_id=1, first_name="Bob", last_name="Jones",
        employee_id="EMP002", is_active=True,
    )
    db.add_all([tech_alice, tech_bob])
    db.flush()

    # Specializations — Alice can do Oil Change & Full Service; Bob does all three
    db.add_all([
        models.TechnicianSpecialization(technician_id=1, service_type_id=1),
        models.TechnicianSpecialization(technician_id=1, service_type_id=2),
        models.TechnicianSpecialization(technician_id=2, service_type_id=1),
        models.TechnicianSpecialization(technician_id=2, service_type_id=2),
        models.TechnicianSpecialization(technician_id=2, service_type_id=3),
    ])

    # ── Service Bays ─────────────────────────────────────────────────────
    bay_a = models.ServiceBay(
        id=1, dealership_id=1, bay_number="BAY-A", bay_type="General",
        is_active=True,
    )
    bay_b = models.ServiceBay(
        id=2, dealership_id=1, bay_number="BAY-B", bay_type="General",
        is_active=True,
    )
    db.add_all([bay_a, bay_b])
    db.flush()

    # Bay compatibility — both bays support all three service types
    db.add_all([
        models.BayServiceType(service_bay_id=1, service_type_id=1),
        models.BayServiceType(service_bay_id=1, service_type_id=2),
        models.BayServiceType(service_bay_id=1, service_type_id=3),
        models.BayServiceType(service_bay_id=2, service_type_id=1),
        models.BayServiceType(service_bay_id=2, service_type_id=2),
        models.BayServiceType(service_bay_id=2, service_type_id=3),
    ])

    db.commit()
    print("✅  Database seeded with sample data.")
