import re
from datetime import date as Date
from typing import List
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.core.config import PERIODS, EMAIL_DOMAIN


def _check_hours(v: List[int]) -> List[int]:
    if not v:
        raise ValueError("Select at least one hour")
    if len(set(v)) != len(v):
        raise ValueError("Duplicate hours")
    bad = [h for h in v if h not in PERIODS]
    if bad:
        raise ValueError(f"Invalid hours: {bad}")
    return sorted(v)


# ---------------- student booking ----------------
class BookingRequest(BaseModel):
    """What the student's form sends. roll_no and email come from the login."""
    lab_id: str
    date: Date
    hours: List[int]
    name: str
    phone: str
    reason: str
    faculty: str

    @field_validator("hours")
    @classmethod
    def v_hours(cls, v):
        return _check_hours(v)

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise ValueError("Phone must be a 10-digit Indian mobile number")
        return v

    @field_validator("lab_id", "name", "reason", "faculty")
    @classmethod
    def v_nonempty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class StudentBookingIn(BookingRequest):
    """Full booking data used by the service layer."""
    roll_no: str
    email: EmailStr

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        if not v.lower().endswith("@" + EMAIL_DOMAIN):
            raise ValueError(f"Use your @{EMAIL_DOMAIN} college mail")
        return v.lower()

    @field_validator("roll_no")
    @classmethod
    def v_roll(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


# ---------------- admin block / semester reservation ----------------
class BlockRequest(BaseModel):
    """What the admin's form sends. admin_id comes from the login."""
    lab_id: str
    start_date: Date
    end_date: Date
    hours: List[int]
    reason: str
    override: bool = False  # True = cancel conflicting bookings (sudden placement)

    @field_validator("hours")
    @classmethod
    def v_hours(cls, v):
        return _check_hours(v)

    @field_validator("lab_id", "reason")
    @classmethod
    def v_nonempty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v

    @model_validator(mode="after")
    def v_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class AdminBlockIn(BlockRequest):
    admin_id: str