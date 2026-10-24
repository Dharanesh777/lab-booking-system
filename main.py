"""main.py - PSG Tech CSE/AI Wing Lab Slot Booking & Management System.

Person 1: Backend + Database (FastAPI + SQLite + SQLAlchemy).
Features:
- CORS enabled for http://localhost:5173 (React/Vite frontend)
- OpenAPI interactive documentation at /docs and /redoc
- Automatic startup database seeding from schema.sql & CSVs if lab_booking.db is missing
- Period definitions, lab inventory, equipment tracking, fault reporting
- Intelligent slot availability and booking clash detection with reallocatable flags
- Semester weekly timetable expansion with atomic all-or-nothing transactions
- Maintenance alerts for repeat equipment faults (>=3 in 30 days)
"""

from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import init_db, get_db
from models import Period
from schemas import PeriodOut
from routers import (
    labs_router,
    bookings_router,
    semester_router,
    equipment_router,
    maintenance_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup check: seeds database from schema.sql and CSVs if missing or unpopulated."""
    init_db()
    yield


app = FastAPI(
    title="PSG Tech CSE/AI Wing Lab Slot Booking & Management System",
    description="Backend API for Lab Slot Booking, Clash Detection, Equipment Tracking, and Semester Timetable Management.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(labs_router)
app.include_router(bookings_router)
app.include_router(semester_router)
app.include_router(equipment_router)
app.include_router(maintenance_router)


@app.get("/", tags=["Health"])
def root():
    """Health check and API overview."""
    return {
        "status": "healthy",
        "app": "PSG Tech CSE/AI Wing Lab Slot Booking System",
        "version": "1.0.0",
        "docs": "/docs",
        "today_simulation_date": "2026-10-24",
        "current_semester": "Odd 2026-27",
    }


@app.get("/periods", response_model=List[PeriodOut], tags=["Periods"], summary="List all 8 standard lab periods")
def get_periods(db: Session = Depends(get_db)):
    """Retrieve all 8 scheduled periods (P1 to P8) from the master periods table."""
    return db.query(Period).order_by(Period.period_no).all()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
