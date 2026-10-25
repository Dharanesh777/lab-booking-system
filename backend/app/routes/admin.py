from fastapi import APIRouter

from app.schemas.booking import AdminBlockIn
from app.services import booking_service as bs
from app.utils.serialize import clean

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/pending")
def pending():
    return clean(bs.list_pending())


@router.post("/bookings/{booking_id}/approve")
def approve(booking_id: str, admin_id: str):
    return clean(bs.approve_booking(booking_id, admin_id))


@router.post("/bookings/{booking_id}/reject")
def reject(booking_id: str, admin_id: str, reason: str = ""):
    return clean(bs.reject_booking(booking_id, admin_id, reason))


@router.post("/bookings/{booking_id}/cancel")
def admin_cancel(booking_id: str, admin_id: str, reason: str):
    return clean(bs.cancel_by_admin(booking_id, admin_id, reason))


@router.post("/blocks")
def block(data: AdminBlockIn):
    """Block a lab for one day up to a whole semester. Set override=true to
    cancel conflicting bookings (sudden placement)."""
    return clean(bs.create_admin_block(data))