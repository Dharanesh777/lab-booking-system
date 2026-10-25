import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lab_booking")

STUDENT_ADVANCE_DAYS = 7          # students can book today .. today+7
EMAIL_DOMAIN = "psgtech.ac.in"    # verify your college mail domain

# Hour number -> label. Edit to match your real timetable.
PERIODS = {
    1: "08:30 - 09:20",
    2: "09:20 - 10:10",
    3: "10:30 - 11:20",
    4: "11:20 - 12:10",
    5: "13:40 - 14:30",
    6: "14:30 - 15:20",
    7: "15:30 - 16:20",
    8: "16:20 - 17:10",
}

# Weekdays skipped in semester blocks (Mon=0 ... Sun=6)
SKIP_WEEKDAYS = (6,)