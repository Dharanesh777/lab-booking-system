"""models.py - SQLAlchemy ORM models matching schema.sql exactly.

Tables:
- periods
- labs
- equipment
- semester_timetables
- bookings
- fault_reports
"""

from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base


class Period(Base):
    __tablename__ = "periods"

    period_no = Column(Integer, primary_key=True, index=True)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)


class Lab(Base):
    __tablename__ = "labs"

    lab_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lab_type = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # 'available' or 'maintenance'
    location = Column(String, nullable=True)
    software_tags = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_lab_capacity_positive"),
        CheckConstraint("status IN ('available', 'maintenance')", name="chk_lab_status"),
    )

    equipment_items = relationship("Equipment", back_populates="lab", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="lab", cascade="all, delete-orphan")


class Equipment(Base):
    __tablename__ = "equipment"

    equipment_id = Column(Integer, primary_key=True, index=True)
    lab_id = Column(Integer, ForeignKey("labs.lab_id"), nullable=False)
    asset_tag = Column(String, nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    specs = Column(String, nullable=True)
    status = Column(String, nullable=False)  # 'working', 'faulty', 'under_repair'
    purchase_date = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('working', 'faulty', 'under_repair')", name="chk_equipment_status"),
    )

    lab = relationship("Lab", back_populates="equipment_items")
    fault_reports = relationship("FaultReport", back_populates="equipment", cascade="all, delete-orphan")


class SemesterTimetable(Base):
    __tablename__ = "semester_timetables"

    template_id = Column(Integer, primary_key=True, index=True)
    assigned_lab_id = Column(Integer, ForeignKey("labs.lab_id"), nullable=True)
    batch = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    faculty = Column(String, nullable=True)
    lab_type = Column(String, nullable=True)
    student_count = Column(Integer, nullable=True)
    day_of_week = Column(String, nullable=False)  # 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'
    start_period = Column(Integer, ForeignKey("periods.period_no"), nullable=True)
    end_period = Column(Integer, ForeignKey("periods.period_no"), nullable=True)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    semester_label = Column(String, nullable=True)
    semester_start = Column(String, nullable=False)
    semester_end = Column(String, nullable=False)
    is_locked = Column(Integer, default=0)
    status = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    source_note = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("day_of_week IN ('Mon', 'Tue', 'Wed', 'Thu', 'Fri')", name="chk_day_of_week"),
    )

    assigned_lab = relationship("Lab")
    bookings = relationship("Booking", back_populates="timetable_template")


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lab_id = Column(Integer, ForeignKey("labs.lab_id"), nullable=False)
    booking_date = Column(String, nullable=False)  # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)  # HH:MM
    start_period = Column(Integer, nullable=True)
    end_period = Column(Integer, nullable=True)
    batch = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    faculty = Column(String, nullable=True)
    student_count = Column(Integer, nullable=True)
    booking_type = Column(String, nullable=False)  # 'regular', 'semester', 'placement'
    priority = Column(Integer, nullable=False, default=1)  # 1=regular, 2=semester, 3=placement
    status = Column(String, nullable=False)  # 'confirmed', 'pending', 'cancelled', 'completed'
    recurrence = Column(String, default="none")
    semester_start = Column(String, nullable=True)
    semester_end = Column(String, nullable=True)
    is_locked = Column(Integer, default=0)
    template_id = Column(Integer, ForeignKey("semester_timetables.template_id"), nullable=True)
    requested_by = Column(String, nullable=True)
    created_at = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("booking_type IN ('regular', 'semester', 'placement')", name="chk_booking_type"),
        CheckConstraint("status IN ('confirmed', 'pending', 'cancelled', 'completed')", name="chk_booking_status"),
    )

    lab = relationship("Lab", back_populates="bookings")
    timetable_template = relationship("SemesterTimetable", back_populates="bookings")


class FaultReport(Base):
    __tablename__ = "fault_reports"

    fault_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey("equipment.equipment_id"), nullable=False)
    fault_description = Column(String, nullable=True)
    fault_date = Column(String, nullable=False)  # YYYY-MM-DD
    status = Column(String, nullable=False)  # 'open', 'under_repair', 'resolved'
    resolved_date = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('open', 'under_repair', 'resolved')", name="chk_fault_status"),
    )

    equipment = relationship("Equipment", back_populates="fault_reports")
