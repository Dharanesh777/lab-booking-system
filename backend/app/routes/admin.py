from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_admin
from app.schemas.booking import AdminBlockIn, BlockRequest
from app.services import booking_service as bs
from app.utils.serialize import clean

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/pending")
def pending(admin: dict = Depends(require_admin)):
    """Approval page: waiting requests, oldest first."""
    return clean(bs.list_pending())


@router.get("/bookings")
def all_bookings(
    status: Optional[str] = None,
    lab_id: Optional[str] = None,
    booking_type: Optional[str] = Query(None, alias="type"),
    from_date: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    """All bookings with filters. e.g. ?status=approved&from_date=2026-11-01
    shows approved bookings the admin may need to cancel."""
    return clean(bs.list_bookings(status, lab_id, booking_type, from_date))


@router.post("/bookings/{booking_id}/approve")
def approve(booking_id: str, admin: dict = Depends(require_admin)):
    return clean(bs.approve_booking(booking_id, admin["email"]))


@router.post("/bookings/{booking_id}/reject")
def reject(booking_id: str, reason: str = "", admin: dict = Depends(require_admin)):
    return clean(bs.reject_booking(booking_id, admin["email"], reason))


@router.post("/bookings/{booking_id}/cancel")
def admin_cancel(booking_id: str, reason: str, admin: dict = Depends(require_admin)):
    """Cancel an approved booking (e.g. sudden placement), or a block."""
    return clean(bs.cancel_by_admin(booking_id, admin["email"], reason))


# ---------------- semester reservation / blocks ----------------
@router.get("/blocks")
def list_blocks(from_date: Optional[str] = None, admin: dict = Depends(require_admin)):
    return clean(bs.list_blocks(from_date))


@router.post("/blocks")
def block(req: BlockRequest, admin: dict = Depends(require_admin)):
    """Block a lab for one day up to a whole semester. Set override=true to
    cancel conflicting bookings (sudden placement). Response lists the
    affected bookings so students can be notified."""
    data = AdminBlockIn(**req.model_dump(), admin_id=admin["email"])
    return clean(bs.create_admin_block(data))