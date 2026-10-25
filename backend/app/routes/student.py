from fastapi import APIRouter, Depends

from app.core.deps import require_student
from app.schemas.booking import BookingRequest, StudentBookingIn
from app.services import booking_service as bs
from app.utils.serialize import clean

router = APIRouter(tags=["student"])


@router.post("/bookings")
def book(req: BookingRequest, user: dict = Depends(require_student)):
    """roll_no and email are taken from the logged-in account, never from the request."""
    data = StudentBookingIn(**req.model_dump(), roll_no=user["roll_no"], email=user["email"])
    return clean(bs.create_student_booking(data))


@router.get("/students/me/bookings")
def my_bookings(user: dict = Depends(require_student)):
    """Orders page: returns waiting / confirmed / past."""
    return clean(bs.list_student_bookings(user["roll_no"]))


@router.post("/bookings/{booking_id}/cancel")
def student_cancel(booking_id: str, user: dict = Depends(require_student)):
    return clean(bs.cancel_by_student(booking_id, user["roll_no"]))