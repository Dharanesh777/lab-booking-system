from fastapi import APIRouter

from app.core.exceptions import ValidationFailed
from app.services import booking_service as bs
from app.services import lab_service as ls
from app.utils.dates import parse_date
from app.utils.serialize import clean

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get("")
def get_labs():
    """Active labs only: for the student's lab dropdown."""
    return clean(ls.list_labs())


@router.get("/{lab_id}/availability")
def availability(lab_id: str, date: str):
    """Hour-by-hour availability. date format: YYYY-MM-DD"""
    try:
        parse_date(date)
    except ValueError:
        raise ValidationFailed("date must be in YYYY-MM-DD format")
    return bs.get_availability(lab_id, date)