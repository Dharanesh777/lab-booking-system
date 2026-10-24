"""services/booking_rules.py - Core validation and scheduling logic.

Reusable service module containing:
- Period time definitions (PSG Tech 8-period schedule)
- Half-open interval overlap detection (start_a < end_b and start_b < end_a)
- Capacity validation
- Conflict detection against confirmed bookings
- Reallocation feasibility checks for placement bookings

Person 2's OR-Tools scheduler imports these rules directly.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

# 8 standard PSG Tech periods (table: periods)
PERIODS: Dict[int, Tuple[str, str]] = {
    1: ("08:30", "09:20"),
    2: ("09:20", "10:10"),
    3: ("10:30", "11:20"),
    4: ("11:20", "12:10"),
    5: ("13:40", "14:30"),
    6: ("14:30", "15:20"),
    7: ("15:30", "16:20"),
    8: ("16:20", "17:10"),
}

VALID_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
DEFAULT_TODAY = "2026-10-24"
CURRENT_SEMESTER_LABEL = "Odd 2026-27"
CURRENT_SEMESTER_START = "2026-07-20"
CURRENT_SEMESTER_END = "2026-11-28"


def is_overlapping(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """Half-open interval overlap check: a.start < b.end and b.start < a.end.

    Adjacent intervals (e.g. 08:30-09:20 and 09:20-10:10) do NOT overlap.
    """
    return start_a < end_b and start_b < end_a


def validate_time_order(start_time: str, end_time: str) -> bool:
    """Ensures end_time is strictly after start_time."""
    return start_time < end_time


def validate_capacity(student_count: Optional[int], lab_capacity: int) -> bool:
    """Validates that requested student count does not exceed lab capacity."""
    if student_count is None:
        return True
    return student_count <= lab_capacity


def periods_to_time(start_period: int, end_period: int) -> Tuple[str, str]:
    """Converts 1-based start and end period numbers to HH:MM strings."""
    if start_period not in PERIODS or end_period not in PERIODS:
        raise ValueError(f"Periods must be between 1 and 8. Got {start_period}, {end_period}")
    if start_period > end_period:
        raise ValueError(f"start_period ({start_period}) cannot exceed end_period ({end_period})")
    return PERIODS[start_period][0], PERIODS[end_period][1]


def time_to_periods(start_time: str, end_time: str) -> Tuple[Optional[int], Optional[int]]:
    """Infers start_period and end_period if start_time and end_time align with official bounds."""
    sp = None
    ep = None
    for p_no, (p_start, p_end) in PERIODS.items():
        if p_start == start_time:
            sp = p_no
        if p_end == end_time:
            ep = p_no
    return sp, ep


def find_conflicting_bookings(
    db: Session,
    booking_model: Any,
    lab_id: int,
    booking_date: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: Optional[int] = None,
) -> List[Any]:
    """Finds all confirmed bookings for the same lab and date that overlap with [start_time, end_time).

    Ignores cancelled or pending bookings. Half-open interval logic:
    existing.start_time < new_end_time AND new_start_time < existing.end_time
    """
    query = db.query(booking_model).filter(
        booking_model.lab_id == lab_id,
        booking_model.booking_date == booking_date,
        booking_model.status == "confirmed",
        booking_model.start_time < end_time,
        start_time < booking_model.end_time,
    )
    if exclude_booking_id is not None:
        query = query.filter(booking_model.booking_id != exclude_booking_id)

    return query.all()


def check_reallocatable(conflicts: List[Any], booking_type: str) -> bool:
    """Checks whether the conflict can be reallocated by the scheduler.

    Rule: If booking_type == 'placement' and ALL conflicting bookings are
    NON-locked (is_locked == 0), then reallocatable = True.
    Otherwise (or if any conflict is locked), reallocatable = False.
    """
    if booking_type != "placement":
        return False
    if not conflicts:
        return False
    return all(getattr(c, "is_locked", 0) == 0 for c in conflicts)


def get_lab_free_periods(
    db: Session,
    booking_model: Any,
    lab_id: int,
    booking_date: str,
) -> List[int]:
    """Returns list of period numbers (1..8) that are completely free of confirmed bookings."""
    confirmed = (
        db.query(booking_model)
        .filter(
            booking_model.lab_id == lab_id,
            booking_model.booking_date == booking_date,
            booking_model.status == "confirmed",
        )
        .all()
    )

    free_periods: List[int] = []
    for p_no, (p_start, p_end) in PERIODS.items():
        has_clash = any(is_overlapping(p_start, p_end, b.start_time, b.end_time) for b in confirmed)
        if not has_clash:
            free_periods.append(p_no)

    return free_periods


def get_lab_free_ranges(
    db: Session,
    booking_model: Any,
    lab_id: int,
    booking_date: str,
) -> List[Dict[str, Any]]:
    """Merges consecutive free periods into time ranges."""
    free_periods = get_lab_free_periods(db, booking_model, lab_id, booking_date)
    if not free_periods:
        return []

    ranges: List[Dict[str, Any]] = []
    start_p = free_periods[0]
    prev_p = free_periods[0]

    for p in free_periods[1:]:
        if p == prev_p + 1:
            prev_p = p
        else:
            ranges.append({
                "start_period": start_p,
                "end_period": prev_p,
                "start_time": PERIODS[start_p][0],
                "end_time": PERIODS[prev_p][1],
            })
            start_p = p
            prev_p = p

    ranges.append({
        "start_period": start_p,
        "end_period": prev_p,
        "start_time": PERIODS[start_p][0],
        "end_time": PERIODS[prev_p][1],
    })
    return ranges
