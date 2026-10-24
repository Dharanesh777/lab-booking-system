# PSG Tech CSE/AI Wing Lab Slot Booking & Management System
## Backend & Database Module (Person 1)

FastAPI + SQLite + SQLAlchemy backend for managing lab slots, recurring semester timetables, equipment inventory, fault reporting, and proactive maintenance alerts across PSG Tech's 8 CSE/AI Wing labs.

---

## 1. Quick Start

### Prerequisites
- Python 3.10+
- Dependencies: `pip install -r requirements.txt` (or `pip install fastapi uvicorn sqlalchemy pydantic pytest httpx`)

### Run the Dev Server
```bash
uvicorn main:app --reload --port 8000
```
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **CORS Allowed Origin**: `http://localhost:5173` (React/Vite Frontend)

### Run the Pytest Test Suite
```bash
python -m pytest tests/test_api.py -v
```

---

## 2. System Architecture & Code Structure

Designed with high code clarity so that every module can be explained line-by-line to hackathon judges:

```
lab-booking-system/
├── database.py              # SQLite engine, session management, and auto-seeder
├── models.py                # SQLAlchemy ORM models (exact match to schema.sql)
├── schemas.py               # Pydantic v2 schemas for request validation & OpenAPI docs
├── services/
│   ├── __init__.py
│   └── booking_rules.py     # Reusable rules: half-open interval overlap, capacity, reallocatable checks
├── routers/
│   ├── __init__.py
│   ├── labs.py              # GET /labs, GET /availability
│   ├── bookings.py          # GET /bookings, POST /bookings, PATCH /bookings/{id}, DELETE /bookings/{id}
│   ├── semester.py          # GET /semester-timetables, POST /semester-timetables
│   ├── equipment.py         # GET /equipment, GET /faults, POST /faults
│   └── maintenance.py       # GET /maintenance/alerts
├── tests/
│   ├── __init__.py
│   └── test_api.py          # Pytest suite validating all required cases from test_requests.json
├── schema.sql               # Database schema definition (single source of truth)
├── seed_db.py               # Standalone DB seeding utility
├── test_requests.json       # Challenge test cases
├── lab_booking.db           # SQLite database file (auto-restored if missing)
├── requirements.txt         # Package dependencies
└── README.md                # Documentation and API cheat sheet
```

### Key Business Logic
1. **Half-Open Interval Overlap (`services/booking_rules.py`)**:
   - Two intervals `[start_a, end_a)` and `[start_b, end_b)` overlap if and only if:
     $$\text{start}_a < \text{end}_b \quad \text{AND} \quad \text{start}_b < \text{end}_a$$
   - Adjacent periods (e.g. Period 1: `08:30-09:20` and Period 2: `09:20-10:10`) do **NOT** overlap.
   - Cancelled and pending bookings are ignored during slot collision validation.
2. **Reallocation Feasibility (`reallocatable: true`)**:
   - When a `placement` booking (priority 3) encounters a conflict with confirmed bookings, the endpoint checks if any conflicting booking has `is_locked == 1`.
   - If **all** conflicting bookings are non-locked (`is_locked == 0`), the endpoint returns `HTTP 409 Conflict` with `"reallocatable": true` so Person 2's OR-Tools scheduler can reallocate the conflicting bookings to alternative labs.
   - If any conflicting booking is locked (`is_locked == 1`), `"reallocatable": false`.
3. **Atomic Semester Timetable Expansion (`POST /semester-timetables`)**:
   - Takes a weekly recurring template (e.g., Every Monday Periods 5-8).
   - Generates all weekly occurrence dates across the semester (e.g. `2026-07-20` to `2026-11-28`).
   - Validates all dates against confirmed bookings in the target lab.
   - If any clash is found across the semester, it returns a detailed clash report and **inserts nothing** (`created: 0`).
   - If all dates are clear, it commits both the template and all expanded bookings in a **single atomic database transaction**.
4. **Automatic Startup Seeding**:
   - On application startup (`lifespan` in `main.py`), `database.init_db()` verifies if `lab_booking.db` exists and has data.
   - If missing or empty, it automatically executes `schema.sql` and populates all 6 tables from the CSV files.
5. **Proactive Maintenance Alerts (`GET /maintenance/alerts`)**:
   - Aggregates fault incidents within the last 30 days relative to today (`2026-10-24`).
   - Flags hardware with $\ge 3$ faults for immediate technician review before lab exams and placement drives.

---

## 3. Endpoints Reference Table

| Method | Endpoint | Query / Body Parameters | Success Status | Description |
|---|---|---|---|---|
| `GET` | `/` | None | `200 OK` | Health check & system simulation metadata |
| `GET` | `/periods` | None | `200 OK` | List 8 official PSG Tech periods (P1 to P8) |
| `GET` | `/labs` | `lab_type`, `min_capacity`, `status` | `200 OK` | List labs with optional filtering |
| `GET` | `/availability` | `date` (req), `lab_type`, `min_capacity`, `start_time`, `end_time` | `200 OK` | Check free periods and continuous time slots |
| `GET` | `/bookings` | `lab_id`, `date`, `date_from`, `date_to`, `status`, `booking_type` | `200 OK` | List and filter bookings |
| `POST` | `/bookings` | JSON Body (`BookingCreate`) | `201 Created` / `409 Conflict` | Create a booking with conflict & capacity checks |
| `PATCH` | `/bookings/{id}` | JSON Body (`BookingUpdate`) | `200 OK` / `409 Conflict` | Reassign lab, times, or change status |
| `DELETE` | `/bookings/{id}` | None | `200 OK` | Cancel booking (marks status as 'cancelled') |
| `GET` | `/semester-timetables` | `batch`, `day_of_week`, `lab_id` | `200 OK` | List weekly timetable templates |
| `POST` | `/semester-timetables` | JSON Body (`List[SemesterTimetableItem]`) | `200 OK` | Bulk expand weekly templates (all-or-nothing) |
| `GET` | `/equipment` | `lab_id`, `status`, `category` | `200 OK` | List equipment inventory |
| `GET` | `/faults` | `equipment_id`, `status`, `since` | `200 OK` | List equipment fault incident history |
| `POST` | `/faults` | JSON Body (`FaultReportCreate`) | `201 Created` | Report a fault; sets equipment status to `'faulty'` |
| `GET` | `/maintenance/alerts` | `as_of_date`, `min_faults` | `200 OK` | Equipment with $\ge 3$ faults in the last 30 days |

---

## 4. Example Requests & Responses

### 1. Lab Slot Availability Query
**Request**:
```http
GET /availability?date=2026-11-02&start_time=08:30&end_time=12:10 HTTP/1.1
Host: localhost:8000
```
**Response (`200 OK`)**:
```json
[
  {
    "lab_id": 1,
    "name": "Programming Lab 1",
    "lab_type": "Programming",
    "capacity": 50,
    "status": "available",
    "location": "CSE Block",
    "free_periods": [1, 2, 3, 4],
    "free_time_ranges": [
      {
        "start_period": 1,
        "end_period": 4,
        "start_time": "08:30",
        "end_time": "12:10"
      }
    ],
    "is_available": true
  },
  {
    "lab_id": 2,
    "name": "3AI Lab",
    "lab_type": "Programming",
    "capacity": 45,
    "status": "available",
    "location": "AI Wing",
    "free_periods": [],
    "free_time_ranges": [],
    "is_available": false
  }
]
```

---

### 2. Conflicting Booking Detection (HTTP 409)
**Request**:
```http
POST /bookings HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "lab_id": 2,
  "booking_date": "2026-11-02",
  "start_time": "08:30",
  "end_time": "12:10",
  "batch": "V Sem BE CSE G1",
  "student_count": 30,
  "booking_type": "regular"
}
```
**Response (`409 Conflict`)**:
```json
{
  "detail": "Booking conflict detected with confirmed booking(s)",
  "conflicts": [
    {
      "booking_id": 2183,
      "lab_id": 2,
      "booking_date": "2026-11-02",
      "start_time": "08:30",
      "end_time": "12:10",
      "batch": "I Sem BE CSE G2",
      "subject": "Python Lab",
      "booking_type": "semester",
      "priority": 2,
      "status": "confirmed",
      "is_locked": 1,
      "requested_by": "Timetable Cell"
    }
  ],
  "has_locked_conflict": true,
  "reallocatable": false
}
```

---

### 3. Urgent Placement Booking with Reallocation Flag (`reallocatable: true`)
When a placement drive clashes only with non-locked bookings (`is_locked=0`), the scheduler is instructed that the existing bookings can be shifted to alternative labs.

**Request**:
```http
POST /bookings HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "lab_id": 1,
  "booking_date": "2026-10-27",
  "start_time": "08:30",
  "end_time": "10:10",
  "batch": "Final Year Placement Group",
  "subject": "TCS Placement Drive",
  "student_count": 40,
  "booking_type": "placement"
}
```
**Response (`409 Conflict`)**:
```json
{
  "detail": "Booking conflict detected with confirmed booking(s)",
  "conflicts": [
    {
      "booking_id": 2146,
      "lab_id": 1,
      "booking_date": "2026-10-27",
      "start_time": "08:30",
      "end_time": "10:10",
      "batch": "Staff",
      "subject": "Staff reservation",
      "booking_type": "semester",
      "priority": 2,
      "status": "confirmed",
      "is_locked": 0,
      "requested_by": "Dr. K.G.S"
    }
  ],
  "has_locked_conflict": false,
  "reallocatable": true
}
```

---

### 4. Create a Valid Booking (HTTP 201)
**Request**:
```http
POST /bookings HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "lab_id": 3,
  "booking_date": "2026-10-25",
  "start_time": "08:30",
  "end_time": "10:10",
  "batch": "V Sem BE CSE G1",
  "subject": "Coding Club Hackathon Practice",
  "student_count": 30,
  "booking_type": "regular",
  "requested_by": "Dr. A. Ramesh"
}
```
**Response (`201 Created`)**:
```json
{
  "booking_id": 2380,
  "lab_id": 3,
  "booking_date": "2026-10-25",
  "start_time": "08:30",
  "end_time": "10:10",
  "start_period": 1,
  "end_period": 2,
  "batch": "V Sem BE CSE G1",
  "subject": "Coding Club Hackathon Practice",
  "faculty": null,
  "student_count": 30,
  "booking_type": "regular",
  "priority": 1,
  "status": "confirmed",
  "recurrence": "none",
  "semester_start": null,
  "semester_end": null,
  "is_locked": 0,
  "template_id": null,
  "requested_by": "Dr. A. Ramesh",
  "created_at": "2026-10-24"
}
```

---

### 5. Fault Reporting & Automated Status Transition (HTTP 201)
**Request**:
```http
POST /faults HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "equipment_id": 1,
  "fault_description": "Display flickering and keyboard unresponsive",
  "fault_date": "2026-10-24",
  "status": "open"
}
```
**Response (`201 Created`)**:
```json
{
  "fault_id": 125,
  "equipment_id": 1,
  "fault_description": "Display flickering and keyboard unresponsive",
  "fault_date": "2026-10-24",
  "status": "open",
  "resolved_date": null
}
```
*(Equipment ID 1 status is immediately set to `'faulty'` in SQLite)*

---

### 6. Preventive Maintenance Alerts ($\ge 3$ faults in 30 days)
**Request**:
```http
GET /maintenance/alerts HTTP/1.1
Host: localhost:8000
```
**Response (`200 OK`)**:
```json
[
  {
    "equipment_id": 5,
    "asset_tag": "AST-01-0005",
    "name": "PC-L01-04",
    "category": "PC",
    "lab_id": 1,
    "lab_name": "Programming Lab 1",
    "lab_location": "CSE Block",
    "current_status": "faulty",
    "fault_count_last_30_days": 4,
    "recent_faults": [
      {
        "fault_id": 118,
        "equipment_id": 5,
        "fault_description": "Keyboard not responding",
        "fault_date": "2026-10-20",
        "status": "open",
        "resolved_date": null
      }
    ]
  }
]
```

---

## 5. Postman & cURL Cheat Sheet for Teammates

### 1. Get All Available Labs
```bash
curl -X GET "http://localhost:8000/labs?status=available" -H "Accept: application/json"
```

### 2. Check Lab Availability for a Date & Time Window
```bash
curl -X GET "http://localhost:8000/availability?date=2026-11-02&start_time=08:30&end_time=12:10" -H "Accept: application/json"
```

### 3. Create a Booking
```bash
curl -X POST "http://localhost:8000/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "lab_id": 3,
    "booking_date": "2026-10-25",
    "start_time": "08:30",
    "end_time": "10:10",
    "batch": "V Sem BE CSE G1",
    "subject": "Coding Contest",
    "student_count": 30,
    "booking_type": "regular",
    "requested_by": "Dr. A. Ramesh"
  }'
```

### 4. Patch / Reassign a Booking
```bash
curl -X PATCH "http://localhost:8000/bookings/2380" \
  -H "Content-Type: application/json" \
  -d '{
    "end_time": "12:10",
    "student_count": 35
  }'
```

### 5. Cancel a Booking
```bash
curl -X DELETE "http://localhost:8000/bookings/2380" -H "Accept: application/json"
```

### 6. Submit a Weekly Semester Timetable
```bash
curl -X POST "http://localhost:8000/semester-timetables" \
  -H "Content-Type: application/json" \
  -d '[{
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
    "faculty": "Dr. T. Divya"
  }]'
```

### 7. Report Equipment Fault
```bash
curl -X POST "http://localhost:8000/faults" \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": 1,
    "fault_description": "Network card failure",
    "fault_date": "2026-10-24",
    "status": "open"
  }'
```

### 8. Get Maintenance Alerts
```bash
curl -X GET "http://localhost:8000/maintenance/alerts" -H "Accept: application/json"
```

---

## 6. Test Suite Execution Results

All 16 automated pytest tests pass deterministically:

```
$ python -m pytest tests/test_api.py -v
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.7.0 -- C:\Python314\python.exe
plugins: anyio-4.13.0
collected 16 items

tests/test_api.py::test_root_health PASSED                               [  6%]
tests/test_api.py::test_conflicting_booking PASSED                       [ 12%]
tests/test_api.py::test_insufficient_capacity PASSED                     [ 18%]
tests/test_api.py::test_end_before_start PASSED                          [ 25%]
tests/test_api.py::test_unknown_lab PASSED                               [ 31%]
tests/test_api.py::test_placement_conflict_with_demo_booking PASSED      [ 37%]
tests/test_api.py::test_placement_conflict_reallocatable PASSED          [ 43%]
tests/test_api.py::test_valid_booking PASSED                             [ 50%]
tests/test_api.py::test_get_labs_and_filtering PASSED                    [ 56%]
tests/test_api.py::test_get_availability PASSED                          [ 62%]
tests/test_api.py::test_equipment_and_fault_reporting PASSED             [ 68%]
tests/test_api.py::test_booking_patch_and_cancel PASSED                  [ 75%]
tests/test_api.py::test_semester_timetables_clash_detection PASSED       [ 81%]
tests/test_api.py::test_semester_timetables_success PASSED               [ 87%]
tests/test_api.py::test_patch_booking_conflict PASSED                    [ 93%]
tests/test_api.py::test_maintenance_alerts PASSED                        [100%]

============================= 16 passed in 0.66s ==============================
```