from datetime import time, timedelta

from app.core.config import PERIODS, STUDENT_ADVANCE_DAYS
from app.core.database import bookings, slots
from app.core.exceptions import ValidationFailed
from app.services.lab_service import list_labs
from app.utils.dates import now_ist, parse_date, today_ist


def _period_end(hour: int) -> time:
    hh, mm = PERIODS[hour].split(" - ")[1].strip().split(":")
    return time(int(hh), int(mm))


def _is_past(date_str: str, hour: int, now) -> bool:
    today = now.date().isoformat()
    if date_str < today:
        return True
    return date_str == today and now.time() >= _period_end(hour)


def _booking_info(b: dict) -> dict:
    """Admin only: who holds a red slot."""
    s = b.get("student") or {}
    is_block = b["type"] == "admin_block"
    return {
        "id": b["_id"], "type": b["type"],
        "name": "Blocked by admin" if is_block else s.get("name"),
        "roll_no": s.get("roll_no"), "phone": s.get("phone"), "email": s.get("email"),
        "reason": b["reason"], "faculty": b.get("faculty"),
        "start_date": b["start_date"], "end_date": b["end_date"],
        "decided_by": b.get("decided_by"),
    }


def _request_info(b: dict) -> dict:
    """Admin only: a waiting request behind an orange slot."""
    s = b["student"]
    return {"id": b["_id"], "name": s["name"], "roll_no": s["roll_no"],
            "reason": b["reason"], "faculty": b["faculty"]}


def get_dashboard(date_str: str, is_admin: bool) -> dict:
    try:
        d = parse_date(date_str)
    except ValueError:
        raise ValidationFailed("date must be in YYYY-MM-DD format")
    today = today_ist()
    if not is_admin and not (today <= d <= today + timedelta(days=STUDENT_ADVANCE_DAYS)):
        raise ValidationFailed(
            f"Students can view today up to {STUDENT_ADVANCE_DAYS} days ahead")
    date_str = d.isoformat()
    now = now_ist()

    labs = list_labs()
    lab_ids = [lab["_id"] for lab in labs]

    # red: approved bookings and admin blocks occupy slots
    taken = {(s["lab_id"], s["hour"]): s["booking_id"]
             for s in slots.find({"lab_id": {"$in": lab_ids}, "date": date_str})}

    # orange: waiting requests (they do not block the slot)
    pending = {}
    for b in bookings.find({"type": "student", "status": "pending",
                            "start_date": date_str,
                            "lab_id": {"$in": lab_ids}}).sort("created_at", 1):
        for h in b["hours"]:
            pending.setdefault((b["lab_id"], h), []).append(b)

    details = {}
    if is_admin and taken:
        ids = list(set(taken.values()))
        details = {b["_id"]: b for b in bookings.find({"_id": {"$in": ids}})}

    out = []
    for lab in labs:
        cells = []
        for hour in PERIODS:
            key = (lab["_id"], hour)
            cell = {"hour": hour, "past": _is_past(date_str, hour, now)}
            if key in taken:
                cell["status"] = "booked"
                if is_admin and taken[key] in details:
                    cell["booking"] = _booking_info(details[taken[key]])
            elif key in pending:
                cell["status"] = "pending"
                if is_admin:
                    cell["requests"] = [_request_info(b) for b in pending[key]]
            else:
                cell["status"] = "free"
            cells.append(cell)
        out.append({"id": lab["_id"], "name": lab["name"], "cells": cells})

    return {"date": date_str,
            "periods": [{"hour": h, "time": t} for h, t in PERIODS.items()],
            "labs": out}