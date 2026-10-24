"""tests/test_api.py - Pytest test suite for PSG Tech Lab Slot Booking Backend.

Validates:
1. Conflicting booking -> 409 with conflict details
2. Insufficient capacity -> 400/422
3. End before start -> 422
4. Unknown lab -> 404
5. Placement request with demo booking IDs / unlocked conflicts -> 409 with reallocatable info
6. Valid booking -> 201 Created
7. Lab filtering and availability queries
8. Equipment & fault reporting (equipment becomes 'faulty')
9. Booking patch & delete/cancellation
10. Semester timetable expansion & clash detection
11. Maintenance alerts (>=3 faults in 30 days)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from database import init_db

client = TestClient(app)

# Load test requests JSON
def load_test_requests():
    for p in [Path("test_requests.json"), Path("Database/test_requests.json")]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("test_requests.json not found")

TEST_DATA = load_test_requests()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure DB is freshly initialized before and after test session."""
    init_db(force=True)
    yield
    init_db(force=True)



def test_root_health():
    """Verify health endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["today_simulation_date"] == "2026-10-24"


def test_conflicting_booking():
    """Test 1: Conflicting booking should return HTTP 409 with conflict details."""
    payload = TEST_DATA["conflicting_booking"]
    response = client.post("/bookings", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "conflicts" in data
    assert len(data["conflicts"]) > 0
    assert "has_locked_conflict" in data
    # Verify conflicting booking details are included
    conf = data["conflicts"][0]
    assert conf["lab_id"] == payload["lab_id"]
    assert conf["booking_date"] == payload["booking_date"]


def test_insufficient_capacity():
    """Test 2: Student count exceeding lab capacity should return HTTP 400 or 422."""
    payload = TEST_DATA["insufficient_capacity"]
    response = client.post("/bookings", json=payload)

    assert response.status_code in (400, 422)
    data = response.json()
    assert "detail" in data
    assert "capacity" in data["detail"].lower()


def test_end_before_start():
    """Test 3: end_time earlier than start_time should return HTTP 422 Unprocessable Entity."""
    payload = TEST_DATA["end_before_start"]
    response = client.post("/bookings", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_unknown_lab():
    """Test 4: Booking on non-existent lab should return HTTP 404 Not Found."""
    payload = TEST_DATA["unknown_lab"]
    response = client.post("/bookings", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_placement_conflict_with_demo_booking():
    """Test 5a: Placement booking matching demo booking clashing with a locked semester slot.

    Should return 409 with has_locked_conflict=True and reallocatable=False.
    """
    demo_ids = TEST_DATA["placement_conflict_demo_booking_ids"]
    assert len(demo_ids) > 0

    # Demo 2295 is on Lab 2 on 2026-11-17 from 13:40 to 17:10
    payload = {
        "lab_id": 2,
        "booking_date": "2026-11-17",
        "start_time": "13:40",
        "end_time": "17:10",
        "batch": "Final Year Placement Group",
        "subject": "Zoho Online Test (URGENT)",
        "student_count": 45,
        "booking_type": "placement",
    }
    response = client.post("/bookings", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "conflicts" in data
    assert data["has_locked_conflict"] is True
    assert data["reallocatable"] is False


def test_placement_conflict_reallocatable():
    """Test 5b: Placement booking conflicting ONLY with non-locked bookings.

    Booking 2146 is on Lab 1 on 2026-10-27 from 08:30 to 10:10 (is_locked=0).
    Should return 409 with reallocatable=True.
    """
    payload = {
        "lab_id": 1,
        "booking_date": "2026-10-27",
        "start_time": "08:30",
        "end_time": "10:10",
        "batch": "Final Year Placement Group",
        "subject": "TCS Placement Drive",
        "student_count": 40,
        "booking_type": "placement",
    }
    response = client.post("/bookings", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "conflicts" in data
    assert data["has_locked_conflict"] is False
    assert data["reallocatable"] is True


def test_valid_booking():
    """Test 6: Valid booking without conflict should return HTTP 201 Created."""
    payload = {
        "lab_id": 3,
        "booking_date": "2026-10-25",  # Sunday (free day in academic timetable)
        "start_time": "08:30",
        "end_time": "10:10",
        "batch": "V Sem BE CSE G1",
        "subject": "Coding Club Hackathon Practice",
        "student_count": 30,
        "booking_type": "regular",
        "requested_by": "Dr. A. Ramesh",
    }
    response = client.post("/bookings", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["booking_id"] is not None
    assert data["lab_id"] == 3
    assert data["status"] == "confirmed"
    assert data["priority"] == 1
    assert data["start_period"] == 1
    assert data["end_period"] == 2


def test_get_labs_and_filtering():
    """Test GET /labs with filters."""
    # All labs
    res = client.get("/labs")
    assert res.status_code == 200
    labs = res.json()
    assert len(labs) == 8

    # Filter by lab_type
    res_prog = client.get("/labs?lab_type=Programming")
    assert res_prog.status_code == 200
    for lab in res_prog.json():
        assert "Programming" in lab["lab_type"]

    # Filter by min_capacity
    res_cap = client.get("/labs?min_capacity=50")
    assert res_cap.status_code == 200
    for lab in res_cap.json():
        assert lab["capacity"] >= 50


def test_get_availability():
    """Test GET /availability for a specific date and time slot."""
    res = client.get("/availability?date=2026-11-02&start_time=08:30&end_time=12:10")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 8

    # Lab 2 has confirmed booking 2183 at 08:30-12:10, so is_available should be False
    lab2 = next(l for l in data if l["lab_id"] == 2)
    assert lab2["is_available"] is False
    assert 1 not in lab2["free_periods"]
    assert 2 not in lab2["free_periods"]


def test_equipment_and_fault_reporting():
    """Test GET /equipment, POST /faults (marking equipment 'faulty'), and GET /faults."""
    # 1. Fetch working equipment
    eq_res = client.get("/equipment?status=working")
    assert eq_res.status_code == 200
    working_items = eq_res.json()
    assert len(working_items) > 0
    target_eq = working_items[0]
    target_id = target_eq["equipment_id"]

    # 2. Report fault on this equipment
    fault_payload = {
        "equipment_id": target_id,
        "fault_description": "Keyboard not responding and monitor flickering",
        "fault_date": "2026-10-24",
        "status": "open",
    }
    fault_res = client.post("/faults", json=fault_payload)
    assert fault_res.status_code == 201
    created_fault = fault_res.json()
    assert created_fault["equipment_id"] == target_id
    assert created_fault["status"] == "open"

    # 3. Verify target equipment status is now 'faulty'
    updated_eq = client.get(f"/equipment?lab_id={target_eq['lab_id']}").json()
    matched = next(e for e in updated_eq if e["equipment_id"] == target_id)
    assert matched["status"] == "faulty"

    # 4. Verify fault appears in GET /faults
    f_res = client.get(f"/faults?equipment_id={target_id}")
    assert f_res.status_code == 200
    assert any(f["fault_id"] == created_fault["fault_id"] for f in f_res.json())


def test_booking_patch_and_cancel():
    """Test PATCH /bookings/{id} and DELETE /bookings/{id}."""
    # 1. Create a booking to test with
    create_res = client.post(
        "/bookings",
        json={
            "lab_id": 5,
            "booking_date": "2026-10-25",
            "start_time": "13:40",
            "end_time": "15:20",
            "batch": "Patch Test Batch",
            "student_count": 25,
            "booking_type": "regular",
        },
    )
    assert create_res.status_code == 201
    booking_id = create_res.json()["booking_id"]

    # 2. PATCH booking times
    patch_res = client.patch(
        f"/bookings/{booking_id}",
        json={"start_time": "13:40", "end_time": "17:10", "student_count": 35},
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["end_time"] == "17:10"
    assert patched["student_count"] == 35

    # 3. DELETE / cancel booking
    del_res = client.delete(f"/bookings/{booking_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "cancelled"

    # 4. Verify booking is now ignored in conflict checking
    re_create_res = client.post(
        "/bookings",
        json={
            "lab_id": 5,
            "booking_date": "2026-10-25",
            "start_time": "13:40",
            "end_time": "17:10",
            "batch": "Replacement Batch",
            "student_count": 25,
            "booking_type": "regular",
        },
    )
    assert re_create_res.status_code == 201


def test_semester_timetables_clash_detection():
    """Test POST /semester-timetables returns clashes and creates 0 bookings when conflicts exist."""
    clashing_template = {
        "batch": "Test Clashing Batch",
        "subject": "Clash Lab Test",
        "lab_type": "Programming",
        "student_count": 35,
        "day_of_week": "Mon",
        "start_period": 5,
        "end_period": 8,
        "semester_start": "2026-07-20",
        "semester_end": "2026-11-28",
        "is_locked": 1,
        "assigned_lab_id": 1,
    }

    res = client.post("/semester-timetables", json=[clashing_template])
    assert res.status_code == 200
    report = res.json()
    assert report["created"] == 0
    assert len(report["clashes"]) > 0
    assert any("Overlaps with confirmed booking" in c["reason"] for c in report["clashes"])


def test_semester_timetables_success():
    """Test POST /semester-timetables successfully creates recurring bookings when no clash exists."""
    free_template = {
        "batch": "Special Elective AI Batch",
        "subject": "Deep Reinforcement Learning Lab",
        "lab_type": "Programming",
        "student_count": 35,
        "day_of_week": "Mon",
        "start_period": 1,
        "end_period": 2,
        "semester_start": "2026-11-02",
        "semester_end": "2026-11-23",
        "is_locked": 1,
        "assigned_lab_id": 7,
        "faculty": "Dr. T. Divya",
    }

    res = client.post("/semester-timetables", json=[free_template])
    assert res.status_code == 200
    report = res.json()
    assert report["clashes"] == []
    assert report["created"] == 4  # 4 Mondays in November
    assert report["templates_created"] == 1


def test_patch_booking_conflict():
    """Test PATCH /bookings/{id} returns 409 if changed to a conflicting slot."""
    # Create booking on a free slot
    create_res = client.post(
        "/bookings",
        json={
            "lab_id": 3,
            "booking_date": "2026-10-25",
            "start_time": "10:30",
            "end_time": "12:10",
            "batch": "Movable Batch",
            "student_count": 25,
            "booking_type": "regular",
        },
    )
    assert create_res.status_code == 201
    booking_id = create_res.json()["booking_id"]

    # Try to move it to Lab 2 on 2026-11-02 08:30-12:10 (which is booked by confirmed booking 2183)
    patch_res = client.patch(
        f"/bookings/{booking_id}",
        json={
            "lab_id": 2,
            "booking_date": "2026-11-02",
            "start_time": "08:30",
            "end_time": "12:10",
        },
    )
    assert patch_res.status_code == 409
    data = patch_res.json()
    assert "conflicts" in data
    assert len(data["conflicts"]) > 0


def test_maintenance_alerts():
    """Test GET /maintenance/alerts returns equipment with >=3 faults in 30 days."""
    res = client.get("/maintenance/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0
    for a in alerts:
        assert a["fault_count_last_30_days"] >= 3
        assert len(a["recent_faults"]) >= 3
        assert a["lab_name"] is not None

