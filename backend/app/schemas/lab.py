from typing import Optional
from pydantic import BaseModel, field_validator


class LabIn(BaseModel):
    code: str                       # becomes _id, e.g. "LAB1"
    name: str
    capacity: int
    department: str = "CSE"
    location: Optional[str] = None  # e.g. "2nd floor, IT block"
    active: bool = True

    @field_validator("code")
    @classmethod
    def v_code(cls, v):
        v = v.strip().upper().replace(" ", "")
        if not v:
            raise ValueError("Lab code required")
        return v

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Lab name required")
        return v

    @field_validator("capacity")
    @classmethod
    def v_cap(cls, v):
        if v <= 0:
            raise ValueError("Capacity must be positive")
        return v


class LabUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    department: Optional[str] = None
    location: Optional[str] = None

    @field_validator("capacity")
    @classmethod
    def v_cap(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Capacity must be positive")
        return v