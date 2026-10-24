"""Routers package for lab booking system."""
from routers.labs import router as labs_router
from routers.bookings import router as bookings_router
from routers.semester import router as semester_router
from routers.equipment import router as equipment_router
from routers.maintenance import router as maintenance_router

__all__ = [
    "labs_router",
    "bookings_router",
    "semester_router",
    "equipment_router",
    "maintenance_router",
]
