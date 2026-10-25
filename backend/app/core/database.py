from pymongo import MongoClient, ASCENDING
from app.core.config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

labs = db["labs"]
bookings = db["bookings"]
slots = db["slots"]


def init_indexes():
    """Call once at app startup."""
    # THE conflict guard: one approved booking per lab/date/hour
    slots.create_index(
        [("lab_id", ASCENDING), ("date", ASCENDING), ("hour", ASCENDING)],
        unique=True,
    )
    slots.create_index("booking_id")
    bookings.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    bookings.create_index([("student.roll_no", ASCENDING), ("status", ASCENDING)])
    bookings.create_index([("lab_id", ASCENDING), ("start_date", ASCENDING)])