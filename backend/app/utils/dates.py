from datetime import date, datetime, timedelta, timezone

# India has no daylight saving, so a fixed +05:30 offset is always correct.
# (Avoids needing the tzdata package, which Windows doesn't ship with.)
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    return datetime.now(IST).date()


def parse_date(s: str) -> date:
    return date.fromisoformat(s)  # "YYYY-MM-DD"


def date_range(start: date, end: date, skip_weekdays=()):
    """Yield ISO date strings from start to end inclusive, skipping given weekdays."""
    d = start
    while d <= end:
        if d.weekday() not in skip_weekdays:
            yield d.isoformat()
        d += timedelta(days=1)

def now_ist() -> datetime:
    return datetime.now(IST)