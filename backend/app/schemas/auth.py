import re
from pydantic import BaseModel, EmailStr, field_validator
from app.core.config import EMAIL_DOMAIN


def _check_password(v: str) -> str:
    if not 8 <= len(v) <= 128:
        raise ValueError("Password must be 8 to 128 characters")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password needs at least one letter and one digit")
    return v


def _check_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Name required")
    return v


class RegisterIn(BaseModel):
    name: str
    roll_no: str
    phone: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        return _check_name(v)

    @field_validator("roll_no")
    @classmethod
    def v_roll(cls, v):
        v = v.strip().upper()
        if not v:
            raise ValueError("Roll number required")
        return v

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise ValueError("Phone must be a 10-digit Indian mobile number")
        return v

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        v = v.lower()
        if not v.endswith("@" + EMAIL_DOMAIN):
            raise ValueError(f"Use your @{EMAIL_DOMAIN} college mail")
        return v

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        return _check_password(v)


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        return v.strip().lower()


class AdminCreateIn(BaseModel):
    """An existing admin creates another admin. Any valid email works (faculty
    addresses may not use the student domain)."""
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        return _check_name(v)

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        return v.lower()

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        return _check_password(v)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def v_new(cls, v):
        return _check_password(v)