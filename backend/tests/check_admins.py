from fastapi.testclient import TestClient

from app.core.database import init_indexes, users
from app.main import app
from app.services import auth_service

client = TestClient(app)
A1, A2 = "testadmin1@example.com", "testadmin2@example.com"
ST = "teststudent9@psgtech.ac.in"
PW, PW2 = "Passw0rd123", "NewPassw0rd456"
failures = []


def check(label, cond):
    print(("OK   " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def login(email, pw):
    return client.post("/auth/login", json={"email": email, "password": pw})


def cleanup():
    users.delete_many({"email": {"$in": [A1, A2, ST]}})


init_indexes()
cleanup()

auth_service.create_admin("Admin One", A1, PW, created_by="test")
t1 = login(A1, PW).json()["access_token"]
ts = client.post("/auth/register", json={
    "name": "Stu", "roll_no": "test900", "phone": "9876543210",
    "email": ST, "password": PW}).json()["access_token"]

new = {"name": "Admin Two", "email": A2, "password": PW}
check("student cannot create an admin (403)", client.post("/admin/admins", json=new, headers=hdr(ts)).status_code == 403)
check("no token cannot create an admin (401)", client.post("/admin/admins", json=new).status_code == 401)
check("student cannot list admins (403)", client.get("/admin/admins", headers=hdr(ts)).status_code == 403)

check("weak password rejected (422)",
      client.post("/admin/admins", json={**new, "password": "short"}, headers=hdr(t1)).status_code == 422)
check("invalid email rejected (422)",
      client.post("/admin/admins", json={**new, "email": "nope"}, headers=hdr(t1)).status_code == 422)

r = client.post("/admin/admins", json=new, headers=hdr(t1))
check("admin creates another admin", r.status_code == 200 and r.json()["role"] == "admin")
check("password hash not returned", "password_hash" not in r.text)
check("created_by recorded", r.json()["created_by"] == A1)
a2_id = r.json()["_id"]
check("duplicate admin email -> 409", client.post("/admin/admins", json=new, headers=hdr(t1)).status_code == 409)

r = login(A2, PW)
check("new admin can log in as admin", r.status_code == 200 and r.json()["user"]["role"] == "admin")
t2 = r.json()["access_token"]
check("new admin can reach admin routes", client.get("/admin/pending", headers=hdr(t2)).status_code == 200)
check("admin list shows both",
      {a["email"] for a in client.get("/admin/admins", headers=hdr(t1)).json()} >= {A1, A2})

a1_id = users.find_one({"email": A1})["_id"]
check("admin cannot disable own account (400)",
      client.post(f"/admin/admins/{a1_id}/disable", headers=hdr(t1)).status_code == 400)
check("unknown admin id -> 404",
      client.post("/admin/admins/000000000000000000000000/disable", headers=hdr(t1)).status_code == 404)
check("bad admin id -> 404",
      client.post("/admin/admins/xyz/disable", headers=hdr(t1)).status_code == 404)

check("admin disables the other admin",
      client.post(f"/admin/admins/{a2_id}/disable", headers=hdr(t1)).json()["active"] is False)
check("disabled admin's token stops working (401)", client.get("/admin/pending", headers=hdr(t2)).status_code == 401)
check("disabled admin cannot log in (401)", login(A2, PW).status_code == 401)
check("admin re-enables the other admin",
      client.post(f"/admin/admins/{a2_id}/enable", headers=hdr(t1)).json()["active"] is True)
check("re-enabled admin can log in again", login(A2, PW).status_code == 200)

# ---------------- password change ----------------
t2 = login(A2, PW).json()["access_token"]
check("wrong current password -> 400",
      client.post("/auth/change-password", headers=hdr(t2),
                  json={"current_password": "Wrong1234", "new_password": PW2}).status_code == 400)
check("weak new password -> 422",
      client.post("/auth/change-password", headers=hdr(t2),
                  json={"current_password": PW, "new_password": "short"}).status_code == 422)
check("same password -> 400",
      client.post("/auth/change-password", headers=hdr(t2),
                  json={"current_password": PW, "new_password": PW}).status_code == 400)
r = client.post("/auth/change-password", headers=hdr(t2),
                json={"current_password": PW, "new_password": PW2})
check("password changed, new token returned", r.status_code == 200 and "access_token" in r.json())
t2_new = r.json()["access_token"]
check("old token stops working after password change (401)",
      client.get("/auth/me", headers=hdr(t2)).status_code == 401)
check("new token works", client.get("/auth/me", headers=hdr(t2_new)).status_code == 200)
check("old password no longer logs in", login(A2, PW).status_code == 401)
check("new password logs in", login(A2, PW2).status_code == 200)

cleanup()
print()
if failures:
    print(f"{len(failures)} check(s) FAILED")
    raise SystemExit(1)
print("All admin-management checks passed, test data cleaned up.")