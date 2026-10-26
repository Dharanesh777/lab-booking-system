from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.database import bookings, init_indexes, labs, slots, users
from app.main import app
from app.schemas.lab import LabIn
from app.services import auth_service, lab_service
from app.utils.dates import today_ist

client = TestClient(app)
LAB = "TESTLAB"
S1, S2 = "dashstudent1@psgtech.ac.in", "dashstudent2@psgtech.ac.in"
ADMIN = "dashadmin@example.com"
PW = "Passw0rd123"
failures = []


def check(label, cond):
    print(("OK   " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


def cleanup():
    users.delete_many({"email": {"$in": [S1, S2, ADMIN]}})
    slots.delete_many({"lab_id": LAB})
    bookings.delete_many({"lab_id": LAB})
    labs.delete_many({"_id": LAB})


def cells(resp):
    lab = next(l for l in resp.json()["labs"] if l["id"] == LAB)
    return {c["hour"]: c for c in lab["cells"]}


init_indexes()
cleanup()
today = today_ist()
day = next(today + timedelta(days=i) for i in range(1, 7)
           if (today + timedelta(days=i)).weekday() != 6)
dstr = day.isoformat()

lab_service.create_lab(LabIn(code=LAB, name="Test Lab", capacity=30))
auth_service.create_admin("Dash Admin", ADMIN, PW)
ta = client.post("/auth/login", json={"email": ADMIN, "password": PW}).json()["access_token"]


def reg(email, roll, name):
    return client.post("/auth/register", json={
        "name": name, "roll_no": roll, "phone": "9876543210",
        "email": email, "password": PW}).json()["access_token"]


t1, t2 = reg(S1, "dash001", "Dash One"), reg(S2, "dash002", "Dash Two")


def book(tok, hours, name="Dash Student"):
    return client.post("/bookings", headers=hdr(tok), json={
        "lab_id": LAB, "date": dstr, "hours": hours, "name": name, "phone": "9876543210",
        "reason": "Project work", "faculty": "Dr. X"}).json()


b1 = book(t1, [1, 2], "Dash One")
client.post(f"/admin/bookings/{b1['_id']}/approve", headers=hdr(ta))   # red
book(t2, [4])                                                          # orange

check("no token -> 401", client.get("/dashboard").status_code == 401)

# ---------------- admin view ----------------
r = client.get("/dashboard", params={"date": dstr}, headers=hdr(ta))
check("admin gets the dashboard", r.status_code == 200 and r.json()["date"] == dstr)
check("all 8 periods returned", len(r.json()["periods"]) == 8 and len(cells(r)) == 8)
a = cells(r)
check("approved hours are booked", a[1]["status"] == "booked" and a[2]["status"] == "booked")
check("admin sees who booked",
      a[1]["booking"]["name"] == "Dash One" and a[1]["booking"]["roll_no"] == "DASH001"
      and a[1]["booking"]["id"] == b1["_id"])
check("waiting request is orange", a[4]["status"] == "pending")
check("admin sees the waiting request", a[4]["requests"][0]["roll_no"] == "DASH002")
check("untouched hour is free", a[3]["status"] == "free" and "booking" not in a[3])
check("future day has no past hours", not any(c["past"] for c in a.values()))

# ---------------- student view ----------------
r = client.get("/dashboard", params={"date": dstr}, headers=hdr(t2))
s = cells(r)
check("student sees red, orange and green",
      s[1]["status"] == "booked" and s[4]["status"] == "pending" and s[3]["status"] == "free")
check("student gets no booking or request details",
      "booking" not in s[1] and "requests" not in s[4])
check("no names or roll numbers leak to the student",
      "Dash One" not in r.text and "DASH001" not in r.text and "DASH002" not in r.text)

# ---------------- admin block shows as red ----------------
client.post("/admin/blocks", headers=hdr(ta), json={
    "lab_id": LAB, "start_date": dstr, "end_date": dstr, "hours": [6], "reason": "Placement drive"})
a = cells(client.get("/dashboard", params={"date": dstr}, headers=hdr(ta)))
check("admin block is red and labelled", a[6]["status"] == "booked"
      and a[6]["booking"]["type"] == "admin_block" and a[6]["booking"]["name"] == "Blocked by admin")
check("block reason visible to admin", a[6]["booking"]["reason"] == "Placement drive")
s = cells(client.get("/dashboard", params={"date": dstr}, headers=hdr(t2)))
check("block is just red for students", s[6]["status"] == "booked" and "booking" not in s[6])

# ---------------- dates ----------------
r = client.get("/dashboard", headers=hdr(t1))
check("default date is today", r.status_code == 200 and r.json()["date"] == today.isoformat())
check("student: date beyond 7 days -> 400",
      client.get("/dashboard", params={"date": (today + timedelta(days=9)).isoformat()},
                 headers=hdr(t1)).status_code == 400)
check("student: past date -> 400",
      client.get("/dashboard", params={"date": (today - timedelta(days=1)).isoformat()},
                 headers=hdr(t1)).status_code == 400)
r = client.get("/dashboard", params={"date": (today - timedelta(days=1)).isoformat()}, headers=hdr(ta))
check("admin can view a past date, all hours past",
      r.status_code == 200 and all(c["past"] for c in cells(r).values()))
check("bad date format -> 400",
      client.get("/dashboard", params={"date": "28-10-2026"}, headers=hdr(ta)).status_code == 400)

# ---------------- disabled lab disappears ----------------
lab_service.set_lab_active(LAB, False, force=True)
r = client.get("/dashboard", params={"date": dstr}, headers=hdr(ta))
check("disabled lab is not on the dashboard", all(l["id"] != LAB for l in r.json()["labs"]))

cleanup()
print()
if failures:
    print(f"{len(failures)} check(s) FAILED")
    raise SystemExit(1)
print("All dashboard checks passed, test data cleaned up.")