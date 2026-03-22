#!/usr/bin/env python3
"""Robust Seed Script — Drop/recreate all tables and populate with rich mock data.

Usage:
    python scripts/seed_data.py

Requires: MySQL (docker-compose) running on port 3307.
"""

import sys
import os
from datetime import time

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app import models


def seed() -> None:
    """Drop all tables, recreate, and populate with realistic mock data."""

    print("🗑️  Dropping all tables…")
    Base.metadata.drop_all(bind=engine)

    print("🔨  Recreating all tables…")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _populate(db)
        db.commit()
        print("\n✅  Database seeded successfully!")
        _print_summary(db)
    except Exception as exc:
        db.rollback()
        print(f"\n❌  Seeding failed: {exc}")
        raise
    finally:
        db.close()


# ── Data Population ──────────────────────────────────────────────────────────


def _populate(db) -> None:

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
    print("   • Dealership created")

    # ── Service Types (5) ────────────────────────────────────────────────
    service_types = [
        models.ServiceType(
            id=1, name="Oil Change",
            description="Standard oil and filter change",
            duration_minutes=60, base_price=49.99,
        ),
        models.ServiceType(
            id=2, name="Full Service",
            description="Comprehensive vehicle inspection and service",
            duration_minutes=180, base_price=199.99,
        ),
        models.ServiceType(
            id=3, name="Tyre Rotation",
            description="Rotate and balance all four tyres",
            duration_minutes=45, base_price=29.99,
        ),
        models.ServiceType(
            id=4, name="Brake Inspection",
            description="Full brake system check and pad measurement",
            duration_minutes=90, base_price=79.99,
        ),
        models.ServiceType(
            id=5, name="Diagnostics",
            description="OBD-II scan and electronic diagnostics",
            duration_minutes=120, base_price=119.99,
        ),
    ]
    db.add_all(service_types)
    print(f"   • {len(service_types)} Service Types created")

    # ── Customers (4) ────────────────────────────────────────────────────
    customers = [
        models.Customer(
            id=1, first_name="John", last_name="Doe",
            email="john.doe@example.com", phone="+44 7700 900001",
        ),
        models.Customer(
            id=2, first_name="Sarah", last_name="Connor",
            email="sarah.connor@example.com", phone="+44 7700 900002",
        ),
        models.Customer(
            id=3, first_name="James", last_name="Wilson",
            email="james.wilson@example.com", phone="+44 7700 900003",
        ),
        models.Customer(
            id=4, first_name="Emily", last_name="Zhang",
            email="emily.zhang@example.com", phone="+44 7700 900004",
        ),
    ]
    db.add_all(customers)
    print(f"   • {len(customers)} Customers created")

    # ── Vehicles (5) ─────────────────────────────────────────────────────
    vehicles = [
        models.Vehicle(
            id=1, customer_id=1, make="Toyota", model="Corolla",
            year=2022, vin="1HGBH41JXMN109186", license_plate="AB12 CDE",
        ),
        models.Vehicle(
            id=2, customer_id=2, make="BMW", model="3 Series",
            year=2023, vin="WBA3A5C51CF256789", license_plate="CD34 FGH",
        ),
        models.Vehicle(
            id=3, customer_id=3, make="Ford", model="Focus",
            year=2021, vin="3FADP4BJ2EM123456", license_plate="EF56 IJK",
        ),
        models.Vehicle(
            id=4, customer_id=4, make="Mercedes-Benz", model="C-Class",
            year=2024, vin="WDDGF8AB7CA654321", license_plate="GH78 LMN",
        ),
        models.Vehicle(
            id=5, customer_id=1, make="Honda", model="Civic",
            year=2020, vin="2HGFC2F59LH567890", license_plate="IJ90 OPQ",
        ),
    ]
    db.add_all(vehicles)
    print(f"   • {len(vehicles)} Vehicles created")

    # ── Technicians (6) ──────────────────────────────────────────────────
    technicians = [
        models.Technician(
            id=1, dealership_id=1, first_name="Alice", last_name="Smith",
            employee_id="EMP001", is_active=True,
        ),
        models.Technician(
            id=2, dealership_id=1, first_name="Bob", last_name="Jones",
            employee_id="EMP002", is_active=True,
        ),
        models.Technician(
            id=3, dealership_id=1, first_name="Charlie", last_name="Brown",
            employee_id="EMP003", is_active=True,
        ),
        models.Technician(
            id=4, dealership_id=1, first_name="Diana", last_name="Prince",
            employee_id="EMP004", is_active=True,
        ),
        models.Technician(
            id=5, dealership_id=1, first_name="Edward", last_name="Norton",
            employee_id="EMP005", is_active=True,
        ),
        models.Technician(
            id=6, dealership_id=1, first_name="Fiona", last_name="Green",
            employee_id="EMP006", is_active=True,
        ),
    ]
    db.add_all(technicians)
    db.flush()
    print(f"   • {len(technicians)} Technicians created")

    # Specializations — varied coverage to test different availability scenarios
    # Alice:   Oil Change, Full Service
    # Bob:     Oil Change, Full Service, Tyre Rotation
    # Charlie: Tyre Rotation, Brake Inspection
    # Diana:   Brake Inspection, Diagnostics, Full Service
    # Edward:  Diagnostics, Oil Change
    # Fiona:   Oil Change, Tyre Rotation, Brake Inspection, Diagnostics
    specializations = [
        # Alice (1)
        models.TechnicianSpecialization(technician_id=1, service_type_id=1),
        models.TechnicianSpecialization(technician_id=1, service_type_id=2),
        # Bob (2)
        models.TechnicianSpecialization(technician_id=2, service_type_id=1),
        models.TechnicianSpecialization(technician_id=2, service_type_id=2),
        models.TechnicianSpecialization(technician_id=2, service_type_id=3),
        # Charlie (3)
        models.TechnicianSpecialization(technician_id=3, service_type_id=3),
        models.TechnicianSpecialization(technician_id=3, service_type_id=4),
        # Diana (4)
        models.TechnicianSpecialization(technician_id=4, service_type_id=4),
        models.TechnicianSpecialization(technician_id=4, service_type_id=5),
        models.TechnicianSpecialization(technician_id=4, service_type_id=2),
        # Edward (5)
        models.TechnicianSpecialization(technician_id=5, service_type_id=5),
        models.TechnicianSpecialization(technician_id=5, service_type_id=1),
        # Fiona (6)
        models.TechnicianSpecialization(technician_id=6, service_type_id=1),
        models.TechnicianSpecialization(technician_id=6, service_type_id=3),
        models.TechnicianSpecialization(technician_id=6, service_type_id=4),
        models.TechnicianSpecialization(technician_id=6, service_type_id=5),
    ]
    db.add_all(specializations)
    print(f"   • {len(specializations)} Technician Specializations created")

    # ── Service Bays (6) ─────────────────────────────────────────────────
    bays = [
        models.ServiceBay(
            id=1, dealership_id=1, bay_number="BAY-A",
            bay_type="General", is_active=True,
        ),
        models.ServiceBay(
            id=2, dealership_id=1, bay_number="BAY-B",
            bay_type="General", is_active=True,
        ),
        models.ServiceBay(
            id=3, dealership_id=1, bay_number="BAY-C",
            bay_type="Quick-Service", is_active=True,
        ),
        models.ServiceBay(
            id=4, dealership_id=1, bay_number="BAY-D",
            bay_type="Heavy-Duty", is_active=True,
        ),
        models.ServiceBay(
            id=5, dealership_id=1, bay_number="BAY-E",
            bay_type="Diagnostics", is_active=True,
        ),
        models.ServiceBay(
            id=6, dealership_id=1, bay_number="BAY-F",
            bay_type="General", is_active=True,
        ),
    ]
    db.add_all(bays)
    db.flush()
    print(f"   • {len(bays)} Service Bays created")

    # Bay compatibility — varied to create realistic constraints
    # BAY-A (General):       Oil Change, Full Service, Tyre Rotation
    # BAY-B (General):       Oil Change, Full Service, Tyre Rotation
    # BAY-C (Quick-Service): Oil Change, Tyre Rotation
    # BAY-D (Heavy-Duty):    Full Service, Brake Inspection
    # BAY-E (Diagnostics):   Diagnostics, Brake Inspection
    # BAY-F (General):       Oil Change, Full Service, Brake Inspection, Diagnostics
    bay_services = [
        # BAY-A (1)
        models.BayServiceType(service_bay_id=1, service_type_id=1),
        models.BayServiceType(service_bay_id=1, service_type_id=2),
        models.BayServiceType(service_bay_id=1, service_type_id=3),
        # BAY-B (2)
        models.BayServiceType(service_bay_id=2, service_type_id=1),
        models.BayServiceType(service_bay_id=2, service_type_id=2),
        models.BayServiceType(service_bay_id=2, service_type_id=3),
        # BAY-C (3)
        models.BayServiceType(service_bay_id=3, service_type_id=1),
        models.BayServiceType(service_bay_id=3, service_type_id=3),
        # BAY-D (4)
        models.BayServiceType(service_bay_id=4, service_type_id=2),
        models.BayServiceType(service_bay_id=4, service_type_id=4),
        # BAY-E (5)
        models.BayServiceType(service_bay_id=5, service_type_id=5),
        models.BayServiceType(service_bay_id=5, service_type_id=4),
        # BAY-F (6)
        models.BayServiceType(service_bay_id=6, service_type_id=1),
        models.BayServiceType(service_bay_id=6, service_type_id=2),
        models.BayServiceType(service_bay_id=6, service_type_id=4),
        models.BayServiceType(service_bay_id=6, service_type_id=5),
    ]
    db.add_all(bay_services)
    print(f"   • {len(bay_services)} Bay-Service Type mappings created")


# ── Summary ──────────────────────────────────────────────────────────────────


def _print_summary(db) -> None:
    """Print a summary of all seeded data."""

    print("\n" + "=" * 65)
    print("  SEED DATA SUMMARY")
    print("=" * 65)

    # Technicians and their specializations
    print("\n📋 Technicians & Specializations:")
    print("-" * 50)
    techs = db.query(models.Technician).order_by(models.Technician.id).all()
    for t in techs:
        specs = [s.service_type.name for s in t.specializations]
        print(f"  {t.employee_id} | {t.first_name:8s} {t.last_name:8s} | {', '.join(specs)}")

    # Service Bays and compatible services
    print("\n🔧 Service Bays & Compatible Services:")
    print("-" * 50)
    bays = db.query(models.ServiceBay).order_by(models.ServiceBay.id).all()
    for b in bays:
        svcs = [bs.service_type.name for bs in b.bay_service_types]
        print(f"  {b.bay_number:6s} ({b.bay_type:13s}) | {', '.join(svcs)}")

    # Customers & Vehicles
    print("\n👤 Customers & Vehicles:")
    print("-" * 50)
    customers = db.query(models.Customer).order_by(models.Customer.id).all()
    for c in customers:
        vehs = [f"{v.year} {v.make} {v.model} ({v.license_plate})" for v in c.vehicles]
        vehs_str = "; ".join(vehs) if vehs else "(no vehicles)"
        print(f"  {c.first_name:8s} {c.last_name:8s} | {vehs_str}")

    # Service Types
    print("\n🛠️  Service Types:")
    print("-" * 50)
    stypes = db.query(models.ServiceType).order_by(models.ServiceType.id).all()
    for s in stypes:
        print(f"  ID {s.id} | {s.name:20s} | {s.duration_minutes:3d} min | £{float(s.base_price):7.2f}")

    print("\n" + "=" * 65)


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed()
