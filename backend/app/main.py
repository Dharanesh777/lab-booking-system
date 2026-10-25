from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.core.database import init_indexes
from app.core.exceptions import BookingError, ConflictError, NotFoundError
from app.routes import admin, admin_labs, labs, student


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_indexes()
    yield


app = FastAPI(title="PSG Tech Lab Slot Booking", lifespan=lifespan)

# lets your frontend teammate call the API from the browser during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- error handling ----------------
@app.exception_handler(BookingError)
async def booking_error_handler(request: Request, exc: BookingError):
    if isinstance(exc, ConflictError):
        return JSONResponse(status_code=409, content={"error": str(exc), "conflicts": exc.conflicts})
    code = 404 if isinstance(exc, NotFoundError) else 400
    return JSONResponse(status_code=code, content={"error": str(exc)})


@app.exception_handler(PyMongoError)
async def db_error_handler(request: Request, exc: PyMongoError):
    return JSONResponse(status_code=503, content={"error": "Database unavailable"})


@app.get("/")
def health():
    return {"status": "ok"}


# ---------------- routers ----------------
app.include_router(labs.router)
app.include_router(student.router)
app.include_router(admin.router)
app.include_router(admin_labs.router)