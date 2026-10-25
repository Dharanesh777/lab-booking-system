from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.schemas.auth import AdminCreateIn
from app.services import auth_service
from app.utils.serialize import clean

router = APIRouter(prefix="/admin/admins", tags=["admin"])


@router.get("")
def list_admins(admin: dict = Depends(require_admin)):
    return clean(auth_service.list_admins())


@router.post("")
def add_admin(data: AdminCreateIn, admin: dict = Depends(require_admin)):
    """Only an existing admin can create another admin."""
    new = auth_service.create_admin(data.name, data.email, data.password,
                                    created_by=admin["email"])
    return clean(auth_service.public_user(new))


@router.post("/{user_id}/disable")
def disable_admin(user_id: str, admin: dict = Depends(require_admin)):
    return clean(auth_service.set_admin_active(user_id, False, admin))


@router.post("/{user_id}/enable")
def enable_admin(user_id: str, admin: dict = Depends(require_admin)):
    return clean(auth_service.set_admin_active(user_id, True, admin))