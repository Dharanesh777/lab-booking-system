"""routers/maintenance.py - Preventive maintenance alerts based on fault thresholds."""

from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Equipment, FaultReport, Lab
from schemas import MaintenanceAlertOut, FaultReportOut
from services.booking_rules import DEFAULT_TODAY

router = APIRouter(tags=["Maintenance"])


@router.get(
    "/maintenance/alerts",
    response_model=List[MaintenanceAlertOut],
    summary="List equipment with >=3 faults in the last 30 days",
)
def get_maintenance_alerts(
    as_of_date: Optional[str] = Query(
        DEFAULT_TODAY,
        description="Reference date to calculate 30-day window (defaults to today: 2026-10-24)",
    ),
    min_faults: int = Query(3, description="Minimum fault incidents threshold"),
    db: Session = Depends(get_db),
):
    """Detects recurring equipment issues: returns all equipment with >=3 faults in the last 30 days.

    Calculated relative to today (2026-10-24) to guide proactive maintenance before exams and drives.
    """
    ref_date = date.fromisoformat(as_of_date) if as_of_date else date.fromisoformat(DEFAULT_TODAY)
    cutoff_date = (ref_date - timedelta(days=30)).isoformat()
    ref_date_str = ref_date.isoformat()

    # Query equipment IDs with >= min_faults within the 30-day window
    fault_counts = (
        db.query(
            FaultReport.equipment_id,
            func.count(FaultReport.fault_id).label("fault_count"),
        )
        .filter(
            FaultReport.fault_date >= cutoff_date,
            FaultReport.fault_date <= ref_date_str,
        )
        .group_by(FaultReport.equipment_id)
        .having(func.count(FaultReport.fault_id) >= min_faults)
        .all()
    )

    if not fault_counts:
        return []

    alerts: List[MaintenanceAlertOut] = []

    for eq_id, count in fault_counts:
        equipment = db.query(Equipment).filter(Equipment.equipment_id == eq_id).first()
        if not equipment:
            continue

        lab = db.query(Lab).filter(Lab.lab_id == equipment.lab_id).first()
        recent_faults_query = (
            db.query(FaultReport)
            .filter(
                FaultReport.equipment_id == eq_id,
                FaultReport.fault_date >= cutoff_date,
                FaultReport.fault_date <= ref_date_str,
            )
            .order_by(FaultReport.fault_date.desc(), FaultReport.fault_id.desc())
            .all()
        )

        alerts.append(
            MaintenanceAlertOut(
                equipment_id=equipment.equipment_id,
                asset_tag=equipment.asset_tag,
                name=equipment.name,
                category=equipment.category,
                lab_id=equipment.lab_id,
                lab_name=lab.name if lab else "Unknown Lab",
                lab_location=lab.location if lab else None,
                current_status=equipment.status,
                fault_count_last_30_days=count,
                recent_faults=[FaultReportOut.model_validate(f) for f in recent_faults_query],
            )
        )

    # Sort alerts by highest fault count first
    alerts.sort(key=lambda a: a.fault_count_last_30_days, reverse=True)
    return alerts
