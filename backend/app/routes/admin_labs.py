from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.schemas.lab import LabIn, LabUpdate
from app.services import lab_service as ls
from app.utils.serialize import clean

router = APIRouter(prefix="/admin/labs", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("")
def admin_list_labs():
    """All labs, including disabled ones."""
    return clean(ls.list_labs(active_only=False))


@router.post("")
def create_lab(data: LabIn):
    return clean(ls.create_lab(data))


@router.put("/{lab_id}")
def update_lab(lab_id: str, data: LabUpdate):
    return clean(ls.update_lab(lab_id, data))


@router.post("/{lab_id}/disable")
def disable_lab(lab_id: str, force: bool = False):
    return clean(ls.set_lab_active(lab_id, False, force))


@router.post("/{lab_id}/enable")
def enable_lab(lab_id: str):
    return clean(ls.set_lab_active(lab_id, True))