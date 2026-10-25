from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.database import bookings, init_indexes, labs, slots, users
from app.main import app
from app.schemas.lab import LabIn
from app.services import auth_service, lab_service
from app.utils.dates import today_ist

client = TestClient(app)
LAB = "TESTLAB"
S1, S2, S3 = ("teststudent1@psgtech.ac.in", "teststudent2@psgtech.ac.in",
              "teststudent3@psgtech.ac.in")
ADMIN = "testadmin@example.com"
PW = "Passw0rd123"
failures = []


def check(label, cond):
    print(("OK   " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def cleanup():
    users.delete_many({"email": {"$in": [S1, S2, S3, ADMIN]}})
    slots.delete_many({"lab_id": LAB})
    bookings.delete_many({"lab_id": LAB})
    labs.delete_many({"_id": LAB})


def reg(email, roll, name="Test Student", pw=PW):
    return client.post("/auth/register", json={
        "name": name, "roll_no": roll, "phone": "9876543210",
        "email": email, "password": pw})


init_indexes()
cleanup()

today = today_ist()
day = next(today + timedelta(days=i) for i in range(1, 7)
           if (today + timedelta(days=i)).weekday() != 6)
dstr = day.isoformat()

lab_service.create_lab(LabIn(code=LAB, name="Test Lab", capacity=30))
auth_service.create_admin("Test Admin", ADMIN, PW)

# ---------------- registration ----------------
r = reg(S1, "test001")
check("register student", r.status_code == 200 and r.json()["user"]["role"] == "student")
check("roll number normalised to upper case", r.json()["user"]["roll_no"] == "TEST001")
check("password hash never returned", "password_hash" not in r.text)
t1 = r.json()["access_token"]
check("duplicate email rejected (409)", reg(S1, "test099").status_code == 409)
check("duplicate roll number rejected (409)", reg(S3, "TEST001").status_code == 409)
check("non-college email rejected (422)", reg("a@gmail.com", "test050").status_code == 422)
check("weak password rejected (422)", reg(S3, "test051", pw="short1").status_code == 422)
check("password without digit rejected (422)", reg(S3, "test052", pw="onlyletters").status_code == 422)

# ---------------- login ----------------
check("wrong password -> 401",
      client.post("/auth/login", json={"email": S1, "password": "Wrong1234"}).status_code == 401)
check("unknown email -> 401",
      client.post("/auth/login", json={"email": "nobody@psgtech.ac.in", "password": PW}).status_code == 401)
r = client.post("/auth/login", json={"email": S1.upper(), "password": PW})
check("login works (email case-insensitive)", r.status_code == 200)
me = client.get("/auth/me", headers=hdr(t1))
check("/auth/me returns own account", me.status_code == 200 and me.json()["email"] == S1)
check("no token -> 401", client.get("/auth/me").status_code == 401)
check("garbage token -> 401", client.get("/auth/me", headers=hdr("abc.def.ghi")).status_code == 401)

t2 = reg(S2, "test002").json()["access_token"]

# ---------------- student booking uses the account, not the request ----------------
check("labs list needs login", client.get("/labs").status_code == 401)
check("labs list works when logged in", client.get("/labs", headers=hdr(t1)).status_code == 200)

body = {"lab_id": LAB, "date": dstr, "hours": [1, 2], "name": "Test One",
        "phone": "9876543210", "reason": "Project work", "faculty": "Dr. X",
        "roll_no": "HACKER99", "email": "hacker@psgtech.ac.in"}   # these two must be ignored
r = client.post("/bookings", json=body, headers=hdr(t1))
check("student booking created as pending", r.status_code == 200 and r.json()["status"] == "pending")
bid = r.json()["_id"]
check("roll_no and email taken from account, not request",
      r.json()["student"]["roll_no"] == "TEST001" and r.json()["student"]["email"] == S1)
check("same student, same slot again -> 409",
      client.post("/bookings", json=body, headers=hdr(t1)).status_code == 409)

# ---------------- ownership ----------------
check("other student cannot cancel it (400)",
      client.post(f"/bookings/{bid}/cancel", headers=hdr(t2)).status_code == 400)
check("other student's orders page is empty",
      client.get("/students/me/bookings", headers=hdr(t2)).json()["waiting"] == [])
check("own orders page shows it as waiting",
      len(client.get("/students/me/bookings", headers=hdr(t1)).json()["waiting"]) == 1)

# ---------------- role separation ----------------
check("student on /admin/pending -> 403", client.get("/admin/pending", headers=hdr(t1)).status_code == 403)
check("student on /admin/labs -> 403", client.get("/admin/labs", headers=hdr(t1)).status_code == 403)
check("student on POST /admin/blocks -> 403",
      client.post("/admin/blocks", headers=hdr(t1), json={
          "lab_id": LAB, "start_date": dstr, "end_date": dstr,
          "hours": [1], "reason": "x"}).status_code == 403)
check("no token on /admin/pending -> 401", client.get("/admin/pending").status_code == 401)

ta = client.post("/auth/login", json={"email": ADMIN, "password": PW}).json()["access_token"]
check("admin on POST /bookings -> 403 (students only)",
      client.post("/bookings", json=body, headers=hdr(ta)).status_code == 403)
check("admin on student orders page -> 403",
      client.get("/students/me/bookings", headers=hdr(ta)).status_code == 403)

# ---------------- admin approval ----------------
pend = client.get("/admin/pending", headers=hdr(ta)).json()
check("admin sees the pending request", any(p["_id"] == bid for p in pend))
r = client.post(f"/admin/bookings/{bid}/approve", headers=hdr(ta))
check("admin approves", r.status_code == 200 and r.json()["status"] == "approved")
check("approval records the admin from the token", r.json()["decided_by"] == ADMIN)
av = {h["hour"]: h["available"]
      for h in client.get(f"/labs/{LAB}/availability", params={"date": dstr}, headers=hdr(t2)).json()}
check("hours 1,2 now taken, hour 3 free", av[1] is False and av[2] is False and av[3] is True)

# ---------------- semester block + sudden placement ----------------
blk = {"lab_id": LAB, "start_date": dstr, "end_date": (day + timedelta(days=2)).isoformat(),
       "hours": [1, 2, 3], "reason": "Placement drive"}
check("block without override while booking exists -> 409",
      client.post("/admin/blocks", json=blk, headers=hdr(ta)).status_code == 409)
r = client.post("/admin/blocks", json={**blk, "override": True}, headers=hdr(ta))
check("block with override works", r.status_code == 200)
check("affected student booking reported as cancelled",
      len(r.json()["affected"]) == 1 and r.json()["affected"][0]["status"] == "cancelled")
check("block records the admin from the token", r.json()["block"]["decided_by"] == ADMIN)
blk_id = r.json()["block"]["_id"]
check("student sees the cancelled booking under past",
      len(client.get("/students/me/bookings", headers=hdr(t1)).json()["past"]) == 1)
check("admin lists active blocks",
      any(b["_id"] == blk_id for b in client.get("/admin/blocks", headers=hdr(ta)).json()))

r = client.post(f"/admin/bookings/{blk_id}/cancel", params={"reason": "Drive postponed"}, headers=hdr(ta))
check("admin cancels the block", r.status_code == 200 and r.json()["status"] == "cancelled")
av = {h["hour"]: h["available"]
      for h in client.get(f"/labs/{LAB}/availability", params={"date": dstr}, headers=hdr(t1)).json()}
check("hours free again after the block is cancelled", all(av[h] for h in (1, 2, 3)))

r = client.get("/admin/bookings", params={"status": "cancelled", "lab_id": LAB}, headers=hdr(ta))
check("admin filter: cancelled bookings in lab", r.status_code == 200 and len(r.json()) >= 2)
check("admin filter: bad status -> 400",
      client.get("/admin/bookings", params={"status": "nonsense"}, headers=hdr(ta)).status_code == 400)

# ---------------- disabled account ----------------
users.update_one({"email": S1}, {"$set": {"active": False}})
check("disabled account: existing token stops working",
      client.get("/auth/me", headers=hdr(t1)).status_code == 401)
check("disabled account: cannot log in again",
      client.post("/auth/login", json={"email": S1, "password": PW}).status_code == 401)

cleanup()
print()
if failures:
    print(f"{len(failures)} check(s) FAILED")
    raise SystemExit(1)
print("All auth checks passed, test data cleaned up.")