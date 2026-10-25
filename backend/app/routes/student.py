from fastapi import APIRouter

from app.schemas.booking import StudentBookingIn
from app.services import booking_service as bs
from app.utils.serialize import clean

router = APIRouter(tags=["student"])


@router.post("/bookings")
def book(data: StudentBookingIn):
    return clean(bs.create_student_booking(data))


@router.get("/students/{roll_no}/bookings")
def my_bookings(roll_no: str):
    """Orders page: returns waiting / confirmed / past."""
    return clean(bs.list_student_bookings(roll_no))


@router.post("/bookings/{booking_id}/cancel")
def student_cancel(booking_id: str, roll_no: str):
    return clean(bs.cancel_by_student(booking_id, roll_no))