"""Pytest fixtures — in-memory SQLite database + Redis mock for unit tests."""

import os

# Must be set before any app imports to skip top-level startup seed
os.environ["TESTING"] = "1"

import sys
from unittest.mock import MagicMock, patch
from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app import models


# ── SQLite in-memory engine for tests ────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_scheduler.db"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database and session for each test function."""
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        # Clean up the file
        if os.path.exists("./test_scheduler.db"):
            os.remove("./test_scheduler.db")


@pytest.fixture(scope="function")
def seeded_db(db_session):
    """Return a session pre-populated with seed data."""
    _seed(db_session)
    return db_session


def _seed(db):
    """Minimal seed data required by the tests."""

    dealership = models.Dealership(
        id=1,
        name="Test Dealership",
        address="1 Test Street",
        phone="+44 0000 000000",
        operating_hours_start=time(8, 0),
        operating_hours_end=time(17, 0),
        timezone="UTC",
    )
    db.add(dealership)

    customer = models.Customer(
        id=1, first_name="Jane", last_name="Tester",
        email="jane@test.com", phone="+44 0000 000001",
    )
    db.add(customer)

    vehicle = models.Vehicle(
        id=1, customer_id=1, make="BMW", model="3 Series",
        year=2023, vin="WBA3A5C51CF256789",
    )
    db.add(vehicle)

    oil_change = models.ServiceType(
        id=1, name="Oil Change", duration_minutes=60, base_price=49.99,
    )
    db.add(oil_change)

    tech = models.Technician(
        id=1, dealership_id=1, first_name="Alice", last_name="Tech",
        employee_id="T001", is_active=True,
    )
    db.add(tech)
    db.flush()

    db.add(models.TechnicianSpecialization(technician_id=1, service_type_id=1))

    bay = models.ServiceBay(
        id=1, dealership_id=1, bay_number="BAY-1",
        bay_type="General", is_active=True,
    )
    db.add(bay)
    db.flush()

    db.add(models.BayServiceType(service_bay_id=1, service_type_id=1))
    db.commit()


# ── Redis mock fixture ──────────────────────────────────────────────────────

@pytest.fixture()
def mock_redis():
    """Patch the Redis client used by services so we don't need a live Redis."""
    fake_redis = MagicMock()
    fake_redis.set.return_value = True  # lock always acquired
    fake_redis.eval.return_value = 1   # lock release OK

    with patch("app.services.get_redis_client", return_value=fake_redis):
        yield fake_redis
