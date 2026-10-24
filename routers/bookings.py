"""routers/bookings.py - Booking CRUD and conflict detection endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Booking, Lab
from schemas import (
    BookingCreate,
    BookingUpdate,
    BookingOut,
    BookingConflictResponse,
    BookingConflictDetail,
)
from services.booking_rules import (
    DEFAULT_TODAY,
    find_conflicting_bookings,
    check_reallocatable,
    validate_time_order,
    validate_capacity,
    time_to_periods,
)

router = APIRouter(tags=["Bookings"])

PRIORITY_MAP = {
    "regular": 1,
    "semester": 2,
    "placement": 3,
}


@router.get("/bookings", response_model=List[BookingOut], summary="List and filter bookings")
def get_bookings(
    lab_id: Optional[int] = Query(None, description="Filter by lab ID"),
    date: Optional[str] = Query(None, description="Exact booking date (YYYY-MM-DD)"),
    date_from: Optional[str] = Query(None, description="Start date range (inclusive)"),
    date_to: Optional[str] = Query(None, description="End date range (inclusive)"),
    status: Optional[str] = Query(None, description="Filter by status ('confirmed', 'pending', 'cancelled', 'completed')"),
    booking_type: Optional[str] = Query(None, description="Filter by booking type ('regular', 'semester', 'placement')"),
    db: Session = Depends(get_db),
):
    """Retrieve bookings with comprehensive filtering across date ranges, labs, status, and priority types."""
    query = db.query(Booking)
    if lab_id is not None:
        query = query.filter(Booking.lab_id == lab_id)
    if date:
        query = query.filter(Booking.booking_date == date)
    if date_from:
        query = query.filter(Booking.booking_date >= date_from)
    if date_to:
        query = query.filter(Booking.booking_date <= date_to)
    if status:
        query = query.filter(Booking.status == status)
    if booking_type:
        query = query.filter(Booking.booking_type == booking_type)

    return query.order_by(Booking.booking_date, Booking.start_time, Booking.lab_id).all()


@router.post(
    "/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Validation error (capacity, maintenance)"},
        404: {"description": "Lab not found"},
        409: {"model": BookingConflictResponse, "description": "Slot clash detected"},
        422: {"description": "Invalid time ordering or payload error"},
    },
    summary="Create a new lab slot booking",
)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
):
    """Create a new booking with validation:

    1. Validates that lab exists (404).
    2. Validates that lab status is 'available' (400).
    3. Validates end_time > start_time (422).
    4. Validates student_count <= lab capacity (400).
    5. Validates half-open overlap against existing confirmed bookings:
       - On conflict returns 409 with list of conflicts and lock status.
       - If booking_type='placement' and all conflicts are non-locked, sets reallocatable=true.
    """
    # 1. Validate lab existence
    lab = db.query(Lab).filter(Lab.lab_id == booking_in.lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lab {booking_in.lab_id} not found")

    # 2. Validate lab status
    if lab.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lab {lab.name} is currently under maintenance and cannot be booked",
        )

    # 3. Validate time ordering
    if not validate_time_order(booking_in.start_time, booking_in.end_time):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end_time ({booking_in.end_time}) must be greater than start_time ({booking_in.start_time})",
        )

    # 4. Validate capacity
    if not validate_capacity(booking_in.student_count, lab.capacity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient capacity: requested {booking_in.student_count} systems, but lab {lab.name} capacity is {lab.capacity}",
        )

    # 5. Overlap check against confirmed bookings on the same lab and date
    conflicts = find_conflicting_bookings(
        db=db,
        booking_model=Booking,
        lab_id=booking_in.lab_id,
        booking_date=booking_in.booking_date,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
    )

    if conflicts:
        has_locked = any(c.is_locked == 1 for c in conflicts)
        reallocatable = check_reallocatable(conflicts, booking_in.booking_type)

        conflict_payload = [
            BookingConflictDetail.model_validate(c).model_dump()
            for c in conflicts
        ]

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "Booking conflict detected with confirmed booking(s)",
                "conflicts": conflict_payload,
                "has_locked_conflict": has_locked,
                "reallocatable": reallocatable,
            },
        )

    # Infer periods if not provided
    sp = booking_in.start_period
    ep = booking_in.end_period
    if sp is None or ep is None:
        inferred_sp, inferred_ep = time_to_periods(booking_in.start_time, booking_in.end_time)
        sp = sp or inferred_sp
        ep = ep or inferred_ep

    # Determine priority
    prio = booking_in.priority or PRIORITY_MAP.get(booking_in.booking_type, 1)

    new_booking = Booking(
        lab_id=booking_in.lab_id,
        booking_date=booking_in.booking_date,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
        start_period=sp,
        end_period=ep,
        batch=booking_in.batch,
        subject=booking_in.subject,
        faculty=booking_in.faculty,
        student_count=booking_in.student_count,
        booking_type=booking_in.booking_type,
        priority=prio,
        status=booking_in.status or "confirmed",
        recurrence=booking_in.recurrence or "none",
        semester_start=booking_in.semester_start,
        semester_end=booking_in.semester_end,
        is_locked=booking_in.is_locked or 0,
        template_id=booking_in.template_id,
        requested_by=booking_in.requested_by,
        created_at=DEFAULT_TODAY,
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking


@router.patch("/bookings/{booking_id}", response_model=BookingOut, summary="Update booking details or reassign lab/time")
def update_booking(
    booking_id: int,
    patch_in: BookingUpdate,
    db: Session = Depends(get_db),
):
    """Update booking details, status, lab, or times with full re-validation of overlaps and capacity."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking {booking_id} not found")

    update_dict = patch_in.model_dump(exclude_unset=True)

    target_lab_id = update_dict.get("lab_id", booking.lab_id)
    target_date = update_dict.get("booking_date", booking.booking_date)
    target_start = update_dict.get("start_time", booking.start_time)
    target_end = update_dict.get("end_time", booking.end_time)
    target_student_count = update_dict.get("student_count", booking.student_count)
    target_status = update_dict.get("status", booking.status)
    target_booking_type = update_dict.get("booking_type", booking.booking_type)

    if not validate_time_order(target_start, target_end):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end_time ({target_end}) must be greater than start_time ({target_start})",
        )

    lab = db.query(Lab).filter(Lab.lab_id == target_lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lab {target_lab_id} not found")

    if lab.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lab {lab.name} is currently under maintenance",
        )

    if not validate_capacity(target_student_count, lab.capacity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient capacity: requested {target_student_count} systems, but lab capacity is {lab.capacity}",
        )

    # Re-run overlap check if status is confirmed
    if target_status == "confirmed":
        conflicts = find_conflicting_bookings(
            db=db,
            booking_model=Booking,
            lab_id=target_lab_id,
            booking_date=target_date,
            start_time=target_start,
            end_time=target_end,
            exclude_booking_id=booking_id,
        )
        if conflicts:
            has_locked = any(c.is_locked == 1 for c in conflicts)
            reallocatable = check_reallocatable(conflicts, target_booking_type)
            conflict_payload = [
                BookingConflictDetail.model_validate(c).model_dump()
                for c in conflicts
            ]
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Booking conflict detected with existing confirmed booking(s)",
                    "conflicts": conflict_payload,
                    "has_locked_conflict": has_locked,
                    "reallocatable": reallocatable,
                },
            )

    for field, val in update_dict.items():
        setattr(booking, field, val)

    # Re-infer periods if times changed and periods were not explicitly provided
    if "start_time" in update_dict or "end_time" in update_dict:
        if "start_period" not in update_dict and "end_period" not in update_dict:
            sp, ep = time_to_periods(booking.start_time, booking.end_time)
            booking.start_period = sp
            booking.end_period = ep

    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/bookings/{booking_id}", response_model=BookingOut, summary="Cancel a booking")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
):
    """Cancels a booking by setting its status to 'cancelled'."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking {booking_id} not found")

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
