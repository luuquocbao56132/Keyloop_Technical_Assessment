"""Tests for the API endpoint layer (integration tests via TestClient)."""

import os
import sys
from datetime import time
from unittest.mock import MagicMock, patch

# Mark as testing BEFORE any app imports
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app import models


def _seed_api(db):
    """Minimal seed data for API tests."""
    dealership = models.Dealership(
        id=1, name="Test Dealership", address="1 Test Street",
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


@pytest.fixture(scope="function")
def client():
    """Provide a TestClient with an isolated SQLite DB and mocked Redis."""
    db_path = "./test_api_scheduler.db"
    # Clean up any leftover file
    if os.path.exists(db_path):
        os.remove(db_path)

    test_url = f"sqlite:///{db_path}"
    test_engine = create_engine(
        test_url, connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed
    session = TestingSession()
    _seed_api(session)
    session.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db

    fake_redis = MagicMock()
    fake_redis.set.return_value = True
    fake_redis.eval.return_value = 1

    with patch("app.services.get_redis_client", return_value=fake_redis):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestCreateAppointmentEndpoint:

    def test_successful_booking(self, client):
        resp = client.post("/api/v1/appointments/", json={
            "dealership_id": 1,
            "customer_id": 1,
            "vehicle_id": 1,
            "service_type_id": 1,
            "desired_time": "2026-04-10T10:00:00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["technician_id"] == 1
        assert data["service_bay_id"] == 1

    def test_missing_resource_returns_404(self, client):
        resp = client.post("/api/v1/appointments/", json={
            "dealership_id": 1,
            "customer_id": 1,
            "vehicle_id": 1,
            "service_type_id": 999,
            "desired_time": "2026-04-10T10:00:00",
        })
        assert resp.status_code == 404
        assert "Service type" in resp.json()["detail"]

    def test_validation_error_returns_422(self, client):
        resp = client.post("/api/v1/appointments/", json={
            "dealership_id": 1,
            # missing required fields
        })
        assert resp.status_code == 422


class TestListAppointmentsEndpoint:

    def test_list_returns_empty(self, client):
        resp = client.get("/api/v1/appointments/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["appointments"] == []

    def test_list_after_booking(self, client):
        # Create one
        client.post("/api/v1/appointments/", json={
            "dealership_id": 1,
            "customer_id": 1,
            "vehicle_id": 1,
            "service_type_id": 1,
            "desired_time": "2026-04-11T09:00:00",
        })
        resp = client.get("/api/v1/appointments/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestHealthEndpoint:

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
