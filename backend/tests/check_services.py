from datetime import timedelta

from app.core.database import bookings, init_indexes, labs, slots
from app.core.exceptions import ConflictError, ValidationFailed
from app.schemas.booking import AdminBlockIn, StudentBookingIn
from app.schemas.lab import LabIn, LabUpdate
from app.services import booking_service as bs
from app.services import lab_service as ls
from app.utils.dates import today_ist

LAB = "TESTLAB"


def cleanup():
    slots.delete_many({"lab_id": LAB})
    bookings.delete_many({"lab_id": LAB})
    labs.delete_many({"_id": LAB})


def ok(msg):
    print("OK  ", msg)


def expect(exc, label, fn):
    try:
        fn()
        print("FAIL (no error raised):", label)
    except exc:
        ok(f"rejected: {label}")


def student(day, hours, roll="23N001", name="Test Student"):
    return StudentBookingIn(
        lab_id=LAB, date=day, hours=hours, name=name, roll_no=roll,
        phone="9876543210", email=f"{roll.lower()}@psgtech.ac.in",
        reason="Project work", faculty="Dr. X")


init_indexes()
cleanup()

# pick a working day (not Sunday) within the next week
today = today_ist()
day = next(today + timedelta(days=i) for i in range(1, 7)
           if (today + timedelta(days=i)).weekday() != 6)
dstr = day.isoformat()

# ---- labs ----
ls.create_lab(LabIn(code=LAB, name="Test Lab", capacity=30))
ok("lab created")
expect(ConflictError, "duplicate lab code", lambda: ls.create_lab(LabIn(code=LAB, name="X", capacity=1)))
ls.update_lab(LAB, LabUpdate(capacity=45))
assert ls.get_lab(LAB)["capacity"] == 45
ok("lab updated (capacity 45)")

# ---- availability + student booking ----
assert all(h["available"] for h in bs.get_availability(LAB, dstr))
ok("all hours free before any booking")

a = bs.create_student_booking(student(day, [1, 2]))
assert a["status"] == "pending"
ok("student booking A created as pending")
expect(ConflictError, "same student, same pending slot",
       lambda: bs.create_student_booking(student(day, [2])))
expect(ValidationFailed, "date more than 7 days ahead",
       lambda: bs.create_student_booking(student(today + timedelta(days=8), [1])))
expect(ValidationFailed, "past date",
       lambda: bs.create_student_booking(student(today - timedelta(days=1), [1])))

b = bs.create_student_booking(student(day, [2, 3], roll="23N002"))
ok("pending requests don't block each other (B created)")

# ---- approval + conflict ----
bs.approve_booking(str(a["_id"]), "admin1")
av = {h["hour"]: h["available"] for h in bs.get_availability(LAB, dstr)}
assert av[1] is False and av[2] is False and av[3] is True
ok("A approved -> hours 1,2 taken, 3 free")
expect(ConflictError, "approving B (hour 2 already taken)",
       lambda: bs.approve_booking(str(b["_id"]), "admin1"))
assert not slots.find_one({"booking_id": b["_id"]}), "partial slots were not rolled back"
ok("failed approval left no partial slots behind")
bs.reject_booking(str(b["_id"]), "admin1", "Slot taken")
ok("B rejected")

# ---- student cancel ----
expect(ValidationFailed, "cancelling someone else's booking",
       lambda: bs.cancel_by_student(str(a["_id"]), "23N999"))
bs.cancel_by_student(str(a["_id"]), "23N001")
assert all(h["available"] for h in bs.get_availability(LAB, dstr))
ok("student cancelled A -> slots freed")

# ---- admin block with override (sudden placement) ----
c = bs.create_student_booking(student(day, [1], roll="23N003"))
bs.approve_booking(str(c["_id"]), "admin1")
d = bs.create_student_booking(student(day, [3], roll="23N004"))   # stays pending
block_in = dict(lab_id=LAB, start_date=day, end_date=day + timedelta(days=7),
                hours=[1, 2, 3], reason="Placement drive", admin_id="admin1")
expect(ConflictError, "block without override while C is approved",
       lambda: bs.create_admin_block(AdminBlockIn(**block_in)))
res = bs.create_admin_block(AdminBlockIn(**block_in, override=True))
statuses = sorted(x["status"] for x in res["affected"])
assert statuses == ["cancelled", "rejected"], statuses
ok("block with override -> C cancelled, D rejected (2 students to notify)")
assert not any(h["available"] for h in bs.get_availability(LAB, dstr)[:3])
ok("hours 1-3 now blocked")

# ---- orders page ----
lists = bs.list_student_bookings("23N003")
assert len(lists["past"]) == 1 and not lists["waiting"] and not lists["confirmed"]
ok("orders page: cancelled booking shows under 'past'")

# ---- disabling lab ----
expect(ConflictError, "disable lab that has an upcoming block",
       lambda: ls.set_lab_active(LAB, False))
ls.set_lab_active(LAB, False, force=True)
expect(ValidationFailed, "booking in a disabled lab",
       lambda: bs.create_student_booking(student(day, [5], roll="23N005")))
ls.set_lab_active(LAB, True)
ok("lab re-enabled")

cleanup()
print("\nAll service checks done, test data cleaned up.")