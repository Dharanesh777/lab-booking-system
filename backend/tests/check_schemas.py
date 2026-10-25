from pydantic import ValidationError
from app.schemas.lab import LabIn, LabUpdate
from app.schemas.booking import StudentBookingIn, AdminBlockIn

good = dict(lab_id="LAB1", date="2026-10-28", hours=[3, 1], name="Dharanesh",
            roll_no="23N999", phone="9876543210", email="Test@PSGTECH.ac.in",
            reason="Project work", faculty="Dr. X")


def expect_fail(label, fn):
    try:
        fn()
        print(f"FAIL (should have been rejected): {label}")
    except ValidationError:
        print(f"OK   rejected: {label}")


# --- should pass ---
b = StudentBookingIn(**good)
print("OK   valid booking -> hours sorted:", b.hours, "| email:", b.email)
print("OK   lab code normalised:", LabIn(code=" lab 1 ", name="CSE Lab 1", capacity=60).code)

# --- should be rejected ---
expect_fail("bad phone", lambda: StudentBookingIn(**{**good, "phone": "12345"}))
expect_fail("non-college email", lambda: StudentBookingIn(**{**good, "email": "a@gmail.com"}))
expect_fail("hour 99", lambda: StudentBookingIn(**{**good, "hours": [99]}))
expect_fail("duplicate hours", lambda: StudentBookingIn(**{**good, "hours": [1, 1]}))
expect_fail("empty hours", lambda: StudentBookingIn(**{**good, "hours": []}))
expect_fail("blank reason", lambda: StudentBookingIn(**{**good, "reason": "  "}))
expect_fail("capacity 0", lambda: LabIn(code="X", name="X", capacity=0))
expect_fail("end before start", lambda: AdminBlockIn(
    lab_id="LAB1", start_date="2026-11-10", end_date="2026-11-01",
    hours=[1], reason="Placement", admin_id="admin1"))