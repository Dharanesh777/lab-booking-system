"""routers/equipment.py - Equipment inventory and fault reporting endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import Equipment, FaultReport
from schemas import EquipmentOut, FaultReportCreate, FaultReportOut
from services.booking_rules import DEFAULT_TODAY

router = APIRouter(tags=["Equipment & Faults"])


@router.get("/equipment", response_model=List[EquipmentOut], summary="List equipment inventory with filters")
def get_equipment(
    lab_id: Optional[int] = Query(None, description="Filter by lab ID"),
    status: Optional[str] = Query(None, description="Filter by status ('working', 'faulty', 'under_repair')"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. 'PC', 'Projector', 'Air Conditioner')"),
    db: Session = Depends(get_db),
):
    """Retrieve equipment inventory with filters for lab, operational status, and category."""
    query = db.query(Equipment)
    if lab_id is not None:
        query = query.filter(Equipment.lab_id == lab_id)
    if status:
        query = query.filter(Equipment.status == status)
    if category:
        query = query.filter(Equipment.category.ilike(f"%{category}%"))

    return query.order_by(Equipment.equipment_id).all()


@router.get("/faults", response_model=List[FaultReportOut], summary="List fault reports with filters")
def get_faults(
    equipment_id: Optional[int] = Query(None, description="Filter by equipment ID"),
    status: Optional[str] = Query(None, description="Filter by status ('open', 'under_repair', 'resolved')"),
    since: Optional[str] = Query(None, description="Filter faults reported on or after date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Retrieve fault incident reports filtered by equipment, resolution status, or date."""
    query = db.query(FaultReport)
    if equipment_id is not None:
        query = query.filter(FaultReport.equipment_id == equipment_id)
    if status:
        query = query.filter(FaultReport.status == status)
    if since:
        query = query.filter(FaultReport.fault_date >= since)

    return query.order_by(FaultReport.fault_date.desc(), FaultReport.fault_id.desc()).all()


@router.post(
    "/faults",
    response_model=FaultReportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Report an equipment fault and mark equipment as faulty",
)
def report_fault(
    fault_in: FaultReportCreate,
    db: Session = Depends(get_db),
):
    """Submit a new fault report.

    1. Validates that target equipment exists.
    2. Records the fault report.
    3. Automatically updates equipment status to 'faulty' in the same transaction.
    """
    equipment = db.query(Equipment).filter(Equipment.equipment_id == fault_in.equipment_id).first()
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {fault_in.equipment_id} not found",
        )

    # Record fault
    new_fault = FaultReport(
        equipment_id=fault_in.equipment_id,
        fault_description=fault_in.fault_description,
        fault_date=fault_in.fault_date or DEFAULT_TODAY,
        status=fault_in.status or "open",
        resolved_date=None,
    )
    db.add(new_fault)

    # Update equipment status to faulty
    equipment.status = "faulty"

    db.commit()
    db.refresh(new_fault)
    return new_fault
