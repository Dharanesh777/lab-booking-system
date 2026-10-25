"""
Reference for the shape of every MongoDB collection.
These are documentation only (TypedDict); validation lives in app/schemas/.
"""
from datetime import datetime
from typing import List, Literal, Optional, TypedDict

from bson import ObjectId


class LabDoc(TypedDict):
    """Collection: labs"""
    _id: str                       # lab code, e.g. "LAB1"
    name: str
    capacity: int
    department: str
    location: Optional[str]
    active: bool                   # False = disabled (maintenance)


class StudentInfo(TypedDict):
    name: str
    roll_no: str
    phone: str
    email: str


class BookingDoc(TypedDict):
    """Collection: bookings (student requests AND admin blocks)"""
    _id: ObjectId
    type: Literal["student", "admin_block"]
    status: Literal["pending", "approved", "rejected", "cancelled"]
    lab_id: str                    # -> labs._id
    start_date: str                # "YYYY-MM-DD"
    end_date: str                  # same as start_date for student bookings
    hours: List[int]               # period numbers, e.g. [1, 2]
    student: Optional[StudentInfo] # None for admin blocks
    reason: str
    faculty: Optional[str]         # None for admin blocks
    decided_by: Optional[str]      # admin id / roll no who last changed status
    note: Optional[str]            # rejection or cancellation reason
    created_at: datetime
    updated_at: datetime


class SlotDoc(TypedDict):
    """Collection: slots (one doc per approved lab/date/hour).
    Unique index on (lab_id, date, hour) is what prevents double-booking."""
    _id: ObjectId
    lab_id: str                    # -> labs._id
    date: str                      # "YYYY-MM-DD"
    hour: int
    booking_id: ObjectId           # -> bookings._id