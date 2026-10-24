"""routers/labs.py - Endpoints for labs and real-time slot availability."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Lab, Booking
from schemas import LabOut, LabAvailability, FreeTimeRange
from services.booking_rules import (
    find_conflicting_bookings,
    get_lab_free_periods,
    get_lab_free_ranges,
    is_overlapping,
)

router = APIRouter(tags=["Labs & Availability"])


@router.get("/labs", response_model=List[LabOut], summary="List all labs with optional filtering")
def get_labs(
    lab_type: Optional[str] = Query(None, description="Filter by lab type (e.g. 'Programming', 'AI/ML')"),
    min_capacity: Optional[int] = Query(None, description="Minimum system capacity required"),
    status: Optional[str] = Query(None, description="Filter by status ('available' or 'maintenance')"),
    db: Session = Depends(get_db),
):
    """Retrieve all labs with optional filtering by type, minimum capacity, and operational status."""
    query = db.query(Lab)
    if lab_type:
        query = query.filter(Lab.lab_type.ilike(f"%{lab_type}%"))
    if min_capacity is not None:
        query = query.filter(Lab.capacity >= min_capacity)
    if status:
        query = query.filter(Lab.status == status)

    return query.order_by(Lab.lab_id).all()


@router.get("/availability", response_model=List[LabAvailability], summary="Query lab slot availability for a date")
def get_availability(
    date: str = Query(..., description="Date to check availability for (YYYY-MM-DD)"),
    lab_type: Optional[str] = Query(None, description="Optional filter by lab type"),
    min_capacity: Optional[int] = Query(None, description="Minimum lab capacity"),
    start_time: Optional[str] = Query(None, description="Optional slot start time (HH:MM)"),
    end_time: Optional[str] = Query(None, description="Optional slot end time (HH:MM)"),
    db: Session = Depends(get_db),
):
    """Returns each matching lab with its free time ranges and periods for the requested date.

    If start_time and end_time are provided, also calculates whether the lab is
    completely free for that requested interval.
    """
    if start_time and end_time and start_time >= end_time:
        raise HTTPException(status_code=422, detail="end_time must be greater than start_time")

    query = db.query(Lab)
    if lab_type:
        query = query.filter(Lab.lab_type.ilike(f"%{lab_type}%"))
    if min_capacity is not None:
        query = query.filter(Lab.capacity >= min_capacity)

    matching_labs = query.order_by(Lab.lab_id).all()
    results: List[LabAvailability] = []

    for lab in matching_labs:
        if lab.status != "available":
            results.append(
                LabAvailability(
                    lab_id=lab.lab_id,
                    name=lab.name,
                    lab_type=lab.lab_type,
                    capacity=lab.capacity,
                    status=lab.status,
                    location=lab.location,
                    free_periods=[],
                    free_time_ranges=[],
                    is_available=False,
                )
            )
            continue

        free_periods = get_lab_free_periods(db, Booking, lab.lab_id, date)
        free_ranges_data = get_lab_free_ranges(db, Booking, lab.lab_id, date)
        free_ranges = [FreeTimeRange(**r) for r in free_ranges_data]

        is_avail = True
        if start_time and end_time:
            conflicts = find_conflicting_bookings(
                db=db,
                booking_model=Booking,
                lab_id=lab.lab_id,
                booking_date=date,
                start_time=start_time,
                end_time=end_time,
            )
            is_avail = len(conflicts) == 0
        else:
            is_avail = len(free_periods) > 0

        results.append(
            LabAvailability(
                lab_id=lab.lab_id,
                name=lab.name,
                lab_type=lab.lab_type,
                capacity=lab.capacity,
                status=lab.status,
                location=lab.location,
                free_periods=free_periods,
                free_time_ranges=free_ranges,
                is_available=is_avail,
            )
        )

    return results
