from pymongo.errors import DuplicateKeyError

from app.core.database import labs, bookings
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailed
from app.schemas.lab import LabIn, LabUpdate
from app.utils.dates import today_ist


def create_lab(data: LabIn) -> dict:
    """Admin creates a new lab. Fails if the code already exists."""
    doc = data.model_dump(exclude={"code"})
    doc["_id"] = data.code
    try:
        labs.insert_one(doc)
    except DuplicateKeyError:
        raise ConflictError(f"Lab code {data.code} already exists")
    return doc


def get_lab(lab_id: str) -> dict:
    lab = labs.find_one({"_id": lab_id})
    if not lab:
        raise NotFoundError(f"Lab {lab_id} not found")
    return lab


def list_labs(active_only: bool = True) -> list:
    q = {"active": True} if active_only else {}
    return list(labs.find(q).sort("_id", 1))


def update_lab(lab_id: str, data: LabUpdate) -> dict:
    get_lab(lab_id)
    changes = data.model_dump(exclude_none=True)
    if not changes:
        raise ValidationFailed("Nothing to update")
    labs.update_one({"_id": lab_id}, {"$set": changes})
    return get_lab(lab_id)


def set_lab_active(lab_id: str, active: bool, force: bool = False) -> dict:
    """
    Enable/disable a lab (e.g. maintenance). Disabling is blocked if the lab
    has upcoming approved bookings or pending requests, unless force=True.
    """
    get_lab(lab_id)
    if not active and not force:
        upcoming = bookings.count_documents({
            "lab_id": lab_id,
            "status": {"$in": ["pending", "approved"]},
            "end_date": {"$gte": today_ist().isoformat()},
        })
        if upcoming:
            raise ConflictError(
                f"{upcoming} upcoming booking(s) exist in this lab. "
                "Cancel them first, or retry with force=True."
            )
    labs.update_one({"_id": lab_id}, {"$set": {"active": active}})
    return get_lab(lab_id)