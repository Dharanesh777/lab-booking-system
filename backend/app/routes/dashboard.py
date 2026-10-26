from typing import Optional

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.services.dashboard_service import get_dashboard
from app.utils.dates import today_ist
from app.utils.serialize import clean

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(date: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Timetable of every active lab for one day. Defaults to today.
    Students get colours only; admins also get who booked and the waiting requests."""
    return clean(get_dashboard(date or today_ist().isoformat(), user["role"] == "admin"))