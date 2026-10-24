"""schemas.py - Pydantic models for request validation and response serialization.

Uses schema.sql column names as the single source of truth.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


# -------------------------------------------------------------
# Period Schemas
# -------------------------------------------------------------
class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_no: int
    start_time: str
    end_time: str


# -------------------------------------------------------------
# Lab Schemas
# -------------------------------------------------------------
class LabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lab_id: int
    name: str
    lab_type: str
    capacity: int
    status: str
    location: Optional[str] = None
    software_tags: Optional[str] = None


# -------------------------------------------------------------
# Equipment Schemas
# -------------------------------------------------------------
class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    lab_id: int
    asset_tag: Optional[str] = None
    name: str
    category: Optional[str] = None
    specs: Optional[str] = None
    status: str
    purchase_date: Optional[str] = None


# -------------------------------------------------------------
# Fault Report Schemas
# -------------------------------------------------------------
class FaultReportCreate(BaseModel):
    equipment_id: int
    fault_description: str
    fault_date: Optional[str] = Field(default="2026-10-24", description="Date fault was reported (YYYY-MM-DD)")
    status: Optional[str] = Field(default="open", description="'open', 'under_repair', or 'resolved'")


class FaultReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fault_id: int
    equipment_id: int
    fault_description: Optional[str] = None
    fault_date: str
    status: str
    resolved_date: Optional[str] = None


# -------------------------------------------------------------
# Booking Schemas
# -------------------------------------------------------------
class BookingCreate(BaseModel):
    lab_id: int
    booking_date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    batch: Optional[str] = None
    subject: Optional[str] = None
    faculty: Optional[str] = None
    student_count: Optional[int] = None
    booking_type: Optional[str] = Field(default="regular", description="'regular', 'semester', or 'placement'")
    priority: Optional[int] = None
    status: Optional[str] = Field(default="confirmed", description="'confirmed', 'pending', 'cancelled', 'completed'")
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    recurrence: Optional[str] = "none"
    semester_start: Optional[str] = None
    semester_end: Optional[str] = None
    is_locked: Optional[int] = 0
    template_id: Optional[int] = None
    requested_by: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> "BookingCreate":
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError(f"end_time ({self.end_time}) must be greater than start_time ({self.start_time})")
        return self


class BookingUpdate(BaseModel):
    lab_id: Optional[int] = None
    booking_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    batch: Optional[str] = None
    subject: Optional[str] = None
    faculty: Optional[str] = None
    student_count: Optional[int] = None
    booking_type: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    recurrence: Optional[str] = None
    semester_start: Optional[str] = None
    semester_end: Optional[str] = None
    is_locked: Optional[int] = None
    template_id: Optional[int] = None
    requested_by: Optional[str] = None

    @model_validator(mode="after")
    def validate_times_if_present(self) -> "BookingUpdate":
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError(f"end_time ({self.end_time}) must be greater than start_time ({self.start_time})")
        return self


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_id: int
    lab_id: int
    booking_date: str
    start_time: str
    end_time: str
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    batch: Optional[str] = None
    subject: Optional[str] = None
    faculty: Optional[str] = None
    student_count: Optional[int] = None
    booking_type: str
    priority: int
    status: str
    recurrence: Optional[str] = "none"
    semester_start: Optional[str] = None
    semester_end: Optional[str] = None
    is_locked: int = 0
    template_id: Optional[int] = None
    requested_by: Optional[str] = None
    created_at: Optional[str] = None


class BookingConflictDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_id: int
    lab_id: int
    booking_date: str
    start_time: str
    end_time: str
    batch: Optional[str] = None
    subject: Optional[str] = None
    booking_type: str
    priority: int
    status: str
    is_locked: int
    requested_by: Optional[str] = None


class BookingConflictResponse(BaseModel):
    detail: str
    conflicts: List[BookingConflictDetail]
    has_locked_conflict: bool
    reallocatable: bool


# -------------------------------------------------------------
# Semester Timetable Schemas
# -------------------------------------------------------------
class SemesterTimetableItem(BaseModel):
    batch: str
    subject: str
    day_of_week: str  # 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'
    start_period: int
    end_period: int
    semester_start: str  # YYYY-MM-DD
    semester_end: str  # YYYY-MM-DD
    lab_type: Optional[str] = None
    student_count: Optional[int] = None
    is_locked: Optional[int] = 0
    assigned_lab_id: Optional[int] = None
    faculty: Optional[str] = None
    semester_label: Optional[str] = None
    confidence: Optional[str] = "high"
    source_note: Optional[str] = None


class ClashDetail(BaseModel):
    date: str
    day_of_week: str
    lab_id: Optional[int] = None
    start_time: str
    end_time: str
    template_batch: str
    template_subject: str
    conflict_booking_id: Optional[int] = None
    conflict_subject: Optional[str] = None
    is_locked: Optional[int] = None
    reason: str


class SemesterTimetableReport(BaseModel):
    created: int
    templates_created: int = 0
    clashes: List[ClashDetail] = []


class SemesterTimetableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: int
    assigned_lab_id: Optional[int] = None
    batch: str
    subject: str
    faculty: Optional[str] = None
    lab_type: Optional[str] = None
    student_count: Optional[int] = None
    day_of_week: str
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    start_time: str
    end_time: str
    semester_label: Optional[str] = None
    semester_start: str
    semester_end: str
    is_locked: int
    status: Optional[str] = None
    confidence: Optional[str] = None
    source_note: Optional[str] = None


# -------------------------------------------------------------
# Availability Schemas
# -------------------------------------------------------------
class FreeTimeRange(BaseModel):
    start_period: int
    end_period: int
    start_time: str
    end_time: str


class LabAvailability(BaseModel):
    lab_id: int
    name: str
    lab_type: str
    capacity: int
    status: str
    location: Optional[str] = None
    free_periods: List[int]
    free_time_ranges: List[FreeTimeRange]
    is_available: bool = True


# -------------------------------------------------------------
# Maintenance Alert Schemas
# -------------------------------------------------------------
class MaintenanceAlertOut(BaseModel):
    equipment_id: int
    asset_tag: Optional[str] = None
    name: str
    category: Optional[str] = None
    lab_id: int
    lab_name: str
    lab_location: Optional[str] = None
    current_status: str
    fault_count_last_30_days: int
    recent_faults: List[FaultReportOut]
