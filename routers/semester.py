"""routers/semester.py - Semester timetable templates and bulk expansion endpoints."""

from datetime import date, timedelta
from typing import List, Union, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import SemesterTimetable, Booking, Lab
from schemas import (
    SemesterTimetableItem,
    SemesterTimetableReport,
    SemesterTimetableOut,
    ClashDetail,
)
from services.booking_rules import (
    VALID_DAYS,
    DEFAULT_TODAY,
    periods_to_time,
    find_conflicting_bookings,
    is_overlapping,
)

router = APIRouter(tags=["Semester Timetables"])


@router.get("/semester-timetables", response_model=List[SemesterTimetableOut], summary="List semester timetable templates")
def get_semester_timetables(
    batch: Optional[str] = Query(None, description="Filter by batch name"),
    day_of_week: Optional[str] = Query(None, description="Filter by day ('Mon'..'Fri')"),
    lab_id: Optional[int] = Query(None, description="Filter by assigned lab ID"),
    db: Session = Depends(get_db),
):
    """Retrieve recurring weekly semester timetable templates."""
    query = db.query(SemesterTimetable)
    if batch:
        query = query.filter(SemesterTimetable.batch.ilike(f"%{batch}%"))
    if day_of_week:
        query = query.filter(SemesterTimetable.day_of_week == day_of_week)
    if lab_id is not None:
        query = query.filter(SemesterTimetable.assigned_lab_id == lab_id)

    return query.order_by(SemesterTimetable.template_id).all()


@router.post(
    "/semester-timetables",
    response_model=SemesterTimetableReport,
    status_code=status.HTTP_200_OK,
    summary="Validate and bulk-create semester weekly timetable templates",
)
def create_semester_timetables(
    templates: List[SemesterTimetableItem],
    db: Session = Depends(get_db),
):
    """Accepts a list of weekly timetable templates.

    1. Expands every template across its semester date range (e.g. 2026-07-20 to 2026-11-28) for its day_of_week.
    2. Validates all weekly occurrences against existing confirmed bookings in the target lab.
    3. Validates against intra-batch clashes.
    4. Returns a report {created, templates_created, clashes[]}.
    5. Inserts expanded bookings ONLY if there are zero clashes (all-or-nothing atomic transaction).
    """
    if not templates:
        return SemesterTimetableReport(created=0, templates_created=0, clashes=[])

    clashes: List[ClashDetail] = []
    expanded_plans = []

    # In-memory collision tracker for the batch itself: (lab_id, date_str) -> list of (start_time, end_time)
    batch_occupied = {}

    for t in templates:
        if t.day_of_week not in VALID_DAYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid day_of_week '{t.day_of_week}'. Must be one of {VALID_DAYS}",
            )

        try:
            start_time, end_time = periods_to_time(t.start_period, t.end_period)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        target_lab_id = t.assigned_lab_id
        if target_lab_id is not None:
            lab = db.query(Lab).filter(Lab.lab_id == target_lab_id).first()
            if not lab:
                clashes.append(
                    ClashDetail(
                        date=t.semester_start,
                        day_of_week=t.day_of_week,
                        lab_id=target_lab_id,
                        start_time=start_time,
                        end_time=end_time,
                        template_batch=t.batch,
                        template_subject=t.subject,
                        reason=f"Assigned lab {target_lab_id} does not exist",
                    )
                )
                continue
            if lab.status != "available":
                clashes.append(
                    ClashDetail(
                        date=t.semester_start,
                        day_of_week=t.day_of_week,
                        lab_id=target_lab_id,
                        start_time=start_time,
                        end_time=end_time,
                        template_batch=t.batch,
                        template_subject=t.subject,
                        reason=f"Assigned lab {lab.name} is in maintenance",
                    )
                )
                continue
            if t.student_count and t.student_count > lab.capacity:
                clashes.append(
                    ClashDetail(
                        date=t.semester_start,
                        day_of_week=t.day_of_week,
                        lab_id=target_lab_id,
                        start_time=start_time,
                        end_time=end_time,
                        template_batch=t.batch,
                        template_subject=t.subject,
                        reason=f"Student count {t.student_count} exceeds lab capacity {lab.capacity}",
                    )
                )
                continue
        else:
            # If no lab assigned, pick first matching available lab
            query = db.query(Lab).filter(Lab.status == "available")
            if t.lab_type:
                query = query.filter(Lab.lab_type.ilike(f"%{t.lab_type}%"))
            if t.student_count:
                query = query.filter(Lab.capacity >= t.student_count)
            first_match = query.first()
            if not first_match:
                clashes.append(
                    ClashDetail(
                        date=t.semester_start,
                        day_of_week=t.day_of_week,
                        lab_id=None,
                        start_time=start_time,
                        end_time=end_time,
                        template_batch=t.batch,
                        template_subject=t.subject,
                        reason=f"No suitable lab found for type '{t.lab_type}' and count {t.student_count}",
                    )
                )
                continue
            target_lab_id = first_match.lab_id

        # Iterate all dates in the semester matching day_of_week
        try:
            sem_start_dt = date.fromisoformat(t.semester_start)
            sem_end_dt = date.fromisoformat(t.semester_end)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid date format: {err}")

        day_idx = VALID_DAYS.index(t.day_of_week)
        curr_dt = sem_start_dt
        dates_for_template = []

        while curr_dt <= sem_end_dt:
            if curr_dt.weekday() == day_idx:
                d_str = curr_dt.isoformat()
                dates_for_template.append(d_str)

                # Check conflict against existing confirmed bookings in DB
                db_conflicts = find_conflicting_bookings(
                    db=db,
                    booking_model=Booking,
                    lab_id=target_lab_id,
                    booking_date=d_str,
                    start_time=start_time,
                    end_time=end_time,
                )
                for conf in db_conflicts:
                    clashes.append(
                        ClashDetail(
                            date=d_str,
                            day_of_week=t.day_of_week,
                            lab_id=target_lab_id,
                            start_time=start_time,
                            end_time=end_time,
                            template_batch=t.batch,
                            template_subject=t.subject,
                            conflict_booking_id=conf.booking_id,
                            conflict_subject=conf.subject,
                            is_locked=conf.is_locked,
                            reason=f"Overlaps with confirmed booking #{conf.booking_id} ('{conf.subject}')",
                        )
                    )

                # Check conflict against other templates in this exact batch
                batch_key = (target_lab_id, d_str)
                if batch_key in batch_occupied:
                    for prev_start, prev_end in batch_occupied[batch_key]:
                        if is_overlapping(start_time, end_time, prev_start, prev_end):
                            clashes.append(
                                ClashDetail(
                                    date=d_str,
                                    day_of_week=t.day_of_week,
                                    lab_id=target_lab_id,
                                    start_time=start_time,
                                    end_time=end_time,
                                    template_batch=t.batch,
                                    template_subject=t.subject,
                                    reason=f"Intra-batch overlap on {d_str} ({prev_start}-{prev_end})",
                                )
                            )
                batch_occupied.setdefault(batch_key, []).append((start_time, end_time))

            curr_dt += timedelta(days=1)

        expanded_plans.append({
            "template": t,
            "lab_id": target_lab_id,
            "start_time": start_time,
            "end_time": end_time,
            "dates": dates_for_template,
        })

    # If any clash detected, abort without saving any booking
    if clashes:
        return SemesterTimetableReport(
            created=0,
            templates_created=0,
            clashes=clashes,
        )

    # All-or-nothing atomic insertion in one transaction
    total_created = 0
    try:
        for plan in expanded_plans:
            t = plan["template"]
            lab_id = plan["lab_id"]
            start_time = plan["start_time"]
            end_time = plan["end_time"]

            db_tmpl = SemesterTimetable(
                assigned_lab_id=lab_id,
                batch=t.batch,
                subject=t.subject,
                faculty=t.faculty,
                lab_type=t.lab_type,
                student_count=t.student_count,
                day_of_week=t.day_of_week,
                start_period=t.start_period,
                end_period=t.end_period,
                start_time=start_time,
                end_time=end_time,
                semester_label=t.semester_label or "Odd 2026-27",
                semester_start=t.semester_start,
                semester_end=t.semester_end,
                is_locked=t.is_locked or 0,
                status="active",
                confidence=t.confidence or "high",
                source_note=t.source_note,
            )
            db.add(db_tmpl)
            db.flush()

            for d_str in plan["dates"]:
                new_booking = Booking(
                    lab_id=lab_id,
                    booking_date=d_str,
                    start_time=start_time,
                    end_time=end_time,
                    start_period=t.start_period,
                    end_period=t.end_period,
                    batch=t.batch,
                    subject=t.subject,
                    faculty=t.faculty,
                    student_count=t.student_count,
                    booking_type="semester",
                    priority=2,
                    status="confirmed",
                    recurrence="weekly",
                    semester_start=t.semester_start,
                    semester_end=t.semester_end,
                    is_locked=t.is_locked or 0,
                    template_id=db_tmpl.template_id,
                    requested_by=t.faculty or "Timetable Cell",
                    created_at=DEFAULT_TODAY,
                )
                db.add(new_booking)
                total_created += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction rolled back due to error: {exc}",
        )

    return SemesterTimetableReport(
        created=total_created,
        templates_created=len(expanded_plans),
        clashes=[],
    )
