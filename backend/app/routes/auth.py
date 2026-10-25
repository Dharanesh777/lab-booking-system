from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn
from app.services import auth_service
from app.utils.serialize import clean

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterIn):
    """Student self-registration. Returns a token, so the student is logged in at once."""
    user = auth_service.register_student(data)
    return clean(auth_service.token_response(user))


@router.post("/login")
def login(data: LoginIn):
    """Student and admin login."""
    user = auth_service.authenticate(data.email, data.password)
    return clean(auth_service.token_response(user))


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return clean(auth_service.public_user(user))

@router.post("/change-password")
def change_password(data: ChangePasswordIn, user: dict = Depends(get_current_user)):
    """Works for students and admins. Returns a fresh token; all older tokens stop working."""
    updated = auth_service.change_password(user, data.current_password, data.new_password)
    return clean(auth_service.token_response(updated))