from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import BulkWriteError

from app.core.config import PERIODS, SKIP_WEEKDAYS, STUDENT_ADVANCE_DAYS
from app.core.database import bookings, slots
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailed
from app.schemas.booking import AdminBlockIn, StudentBookingIn
from app.services.lab_service import get_lab
from app.utils.dates import date_range, parse_date, today_ist


# ---------------- helpers ----------------
def _now():
    return datetime.now(timezone.utc)


def _oid(booking_id: str) -> ObjectId:
    try:
        return ObjectId(booking_id)
    except (InvalidId, TypeError):
        raise NotFoundError("Invalid booking id")


def _get(booking_id: str) -> dict:
    b = bookings.find_one({"_id": _oid(booking_id)})
    if not b:
        raise NotFoundError("Booking not found")
    return b


def _get_active_lab(lab_id: str) -> dict:
    lab = get_lab(lab_id)
    if not lab.get("active", True):
        raise ValidationFailed(f"Lab {lab_id} is currently unavailable")
    return lab


def _dates_of(b: dict) -> list:
    skip = SKIP_WEEKDAYS if b["type"] == "admin_block" else ()
    return list(date_range(parse_date(b["start_date"]), parse_date(b["end_date"]), skip))


def _find_conflicts(lab_id, dates, hours) -> list:
    """Occupied slots for this lab on these dates/hours."""
    return list(slots.find({"lab_id": lab_id, "date": {"$in": dates}, "hour": {"$in": hours}}))


def _conflict_list(conflicts) -> list:
    return [{"date": c["date"], "hour": c["hour"]} for c in conflicts]


def _occupy(booking_id: ObjectId, lab_id, dates, hours):
    """Insert one slot per (date, hour). The unique index rejects double-booking."""
    docs = [{"lab_id": lab_id, "date": d, "hour": h, "booking_id": booking_id}
            for d in dates for h in hours]
    try:
        slots.insert_many(docs, ordered=False)
    except BulkWriteError:
        slots.delete_many({"booking_id": booking_id})  # rollback our partial inserts
        conflicts = _find_conflicts(lab_id, dates, hours)
        raise ConflictError("Slot(s) already booked", _conflict_list(conflicts))


def _release(booking_id: ObjectId):
    slots.delete_many({"booking_id": booking_id})


def _set_status(booking_id: ObjectId, status: str, by: str, note: str = None):
    bookings.update_one({"_id": booking_id}, {"$set": {
        "status": status, "decided_by": by, "note": note, "updated_at": _now()}})


# ---------------- student ----------------
def create_student_booking(data: StudentBookingIn) -> dict:
    _get_active_lab(data.lab_id)
    today = today_ist()
    if data.date < today:
        raise ValidationFailed("Cannot book a past date")
    if data.date > today + timedelta(days=STUDENT_ADVANCE_DAYS):
        raise ValidationFailed(f"Bookings open only {STUDENT_ADVANCE_DAYS} days ahead")

    d = data.date.isoformat()
    conflicts = _find_conflicts(data.lab_id, [d], data.hours)
    if conflicts:
        raise ConflictError("Slot not available", _conflict_list(conflicts))

    dup = bookings.find_one({
        "type": "student", "status": "pending", "lab_id": data.lab_id,
        "start_date": d, "hours": {"$in": data.hours},
        "student.roll_no": data.roll_no,
    })
    if dup:
        raise ConflictError("You already have a pending request for this slot")

    doc = {
        "type": "student", "status": "pending", "lab_id": data.lab_id,
        "start_date": d, "end_date": d, "hours": data.hours,
        "student": {"name": data.name, "roll_no": data.roll_no,
                    "phone": data.phone, "email": data.email},
        "reason": data.reason, "faculty": data.faculty,
        "decided_by": None, "note": None,
        "created_at": _now(), "updated_at": _now(),
    }
    doc["_id"] = bookings.insert_one(doc).inserted_id
    return doc


def cancel_by_student(booking_id: str, roll_no: str) -> dict:
    b = _get(booking_id)
    if b["type"] != "student" or b["student"]["roll_no"] != roll_no:
        raise ValidationFailed("Not your booking")
    if b["status"] not in ("pending", "approved"):
        raise ValidationFailed(f"Cannot cancel a {b['status']} booking")
    if b["start_date"] < today_ist().isoformat():
        raise ValidationFailed("Cannot cancel a past booking")
    _release(b["_id"])
    _set_status(b["_id"], "cancelled", roll_no, "Cancelled by student")
    return _get(booking_id)


def list_student_bookings(roll_no: str) -> dict:
    """Powers the 'orders page': waiting / confirmed / past."""
    today = today_ist().isoformat()
    all_b = list(bookings.find({"type": "student", "student.roll_no": roll_no})
                 .sort("created_at", -1))
    waiting = [b for b in all_b if b["status"] == "pending" and b["start_date"] >= today]
    confirmed = [b for b in all_b if b["status"] == "approved" and b["end_date"] >= today]
    ids_in_use = {b["_id"] for b in waiting + confirmed}
    past = [b for b in all_b if b["_id"] not in ids_in_use]
    return {"waiting": waiting, "confirmed": confirmed, "past": past}


# ---------------- admin ----------------
def list_pending() -> list:
    return list(bookings.find({"status": "pending", "type": "student"}).sort("created_at", 1))


def approve_booking(booking_id: str, admin_id: str) -> dict:
    b = _get(booking_id)
    if b["status"] != "pending":
        raise ValidationFailed(f"Booking is already {b['status']}")
    if b["start_date"] < today_ist().isoformat():
        raise ValidationFailed("Date already passed")
    _occupy(b["_id"], b["lab_id"], _dates_of(b), b["hours"])  # may raise ConflictError
    _set_status(b["_id"], "approved", admin_id)
    return _get(booking_id)


def reject_booking(booking_id: str, admin_id: str, reason: str = "") -> dict:
    b = _get(booking_id)
    if b["status"] != "pending":
        raise ValidationFailed(f"Booking is already {b['status']}")
    _set_status(b["_id"], "rejected", admin_id, reason)
    return _get(booking_id)


def cancel_by_admin(booking_id: str, admin_id: str, reason: str) -> dict:
    b = _get(booking_id)
    if b["status"] not in ("approved", "pending"):
        raise ValidationFailed(f"Cannot cancel a {b['status']} booking")
    _release(b["_id"])
    _set_status(b["_id"], "cancelled", admin_id, reason)
    return _get(booking_id)


def create_admin_block(data: AdminBlockIn) -> dict:
    """
    Block a lab for a date range (one day up to a whole semester).
    Returns {"block": ..., "affected": [bookings cancelled/rejected]} so the
    notification module can message those students.
    """
    _get_active_lab(data.lab_id)
    if data.end_date < today_ist():
        raise ValidationFailed("Cannot block past dates")

    dates = list(date_range(data.start_date, data.end_date, SKIP_WEEKDAYS))
    if not dates:
        raise ValidationFailed("No working days in that range")

    conflicts = _find_conflicts(data.lab_id, dates, data.hours)
    if conflicts and not data.override:
        raise ConflictError(
            "Existing bookings overlap this block. Retry with override=True to cancel them.",
            _conflict_list(conflicts),
        )

    doc = {
        "type": "admin_block", "status": "approved", "lab_id": data.lab_id,
        "start_date": data.start_date.isoformat(), "end_date": data.end_date.isoformat(),
        "hours": data.hours, "reason": data.reason, "student": None,
        "faculty": None, "decided_by": data.admin_id, "note": None,
        "created_at": _now(), "updated_at": _now(),
    }
    doc["_id"] = bookings.insert_one(doc).inserted_id

    affected = []
    # override: cancel approved bookings that are in the way
    for bid in {c["booking_id"] for c in conflicts}:
        _release(bid)
        _set_status(bid, "cancelled", data.admin_id, f"Lab blocked: {data.reason}")
        affected.append(bookings.find_one({"_id": bid}))

    # reject overlapping pending requests
    pending = bookings.find({
        "type": "student", "status": "pending", "lab_id": data.lab_id,
        "start_date": {"$gte": data.start_date.isoformat(), "$lte": data.end_date.isoformat()},
        "hours": {"$in": data.hours},
    })
    for p in list(pending):
        _set_status(p["_id"], "rejected", data.admin_id, f"Lab blocked: {data.reason}")
        affected.append(bookings.find_one({"_id": p["_id"]}))

    try:
        _occupy(doc["_id"], data.lab_id, dates, data.hours)
    except ConflictError:
        bookings.delete_one({"_id": doc["_id"]})
        raise

    return {"block": doc, "affected": affected}


# ---------------- availability ----------------
def get_availability(lab_id: str, date_str: str) -> list:
    """Hour-by-hour status, for the 'select hour' step of the student form."""
    get_lab(lab_id)
    taken = {s["hour"] for s in slots.find({"lab_id": lab_id, "date": date_str})}
    return [{"hour": h, "time": label, "available": h not in taken}
            for h, label in PERIODS.items()]