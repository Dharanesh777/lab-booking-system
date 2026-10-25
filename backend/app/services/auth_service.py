from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.core.database import users
from app.core.exceptions import AuthError, ConflictError, NotFoundError, ValidationFailed
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import RegisterIn

# used so a wrong email takes as long to reject as a wrong password
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _now():
    return datetime.now(timezone.utc)


def register_student(data: RegisterIn) -> dict:
    doc = {
        "role": "student", "name": data.name, "email": data.email,
        "roll_no": data.roll_no, "phone": data.phone,
        "password_hash": hash_password(data.password),
        "active": True, "created_at": _now(),
    }
    try:
        doc["_id"] = users.insert_one(doc).inserted_id
    except DuplicateKeyError:
        raise ConflictError("An account with this email or roll number already exists")
    return doc


def create_admin(name: str, email: str, password: str, created_by: Optional[str] = None) -> dict:
    """Used by scripts/create_admin.py (first admin) and POST /admin/admins."""
    name, email = name.strip(), email.strip().lower()
    if not name:
        raise ValidationFailed("Name required")
    if "@" not in email:
        raise ValidationFailed("Invalid email")
    if len(password) < 8:
        raise ValidationFailed("Password must be at least 8 characters")
    doc = {
        "role": "admin", "name": name, "email": email,
        "password_hash": hash_password(password),
        "active": True, "created_by": created_by, "created_at": _now(),
    }
    try:
        doc["_id"] = users.insert_one(doc).inserted_id
    except DuplicateKeyError:
        raise ConflictError("An account with this email already exists")
    return doc


def authenticate(email: str, password: str) -> dict:
    user = users.find_one({"email": email.strip().lower()})
    ok = verify_password(password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok:
        raise AuthError("Invalid email or password")  # same message for both cases
    if not user.get("active", True):
        raise AuthError("Account disabled")
    return user


def public_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password_hash"}


def token_response(user: dict) -> dict:
    token = create_access_token(str(user["_id"]), user["role"], user.get("roll_no"))
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}

# ---------------- admin management ----------------
def list_admins() -> list:
    return [public_user(u) for u in users.find({"role": "admin"}).sort("created_at", 1)]


def set_admin_active(user_id: str, active: bool, acting_admin: dict) -> dict:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        raise NotFoundError("Admin not found")
    target = users.find_one({"_id": oid, "role": "admin"})
    if not target:
        raise NotFoundError("Admin not found")
    if target["_id"] == acting_admin["_id"] and not active:
        raise ValidationFailed("You cannot disable your own account")
    users.update_one({"_id": oid}, {"$set": {"active": active}})
    return public_user(users.find_one({"_id": oid}))


# ---------------- password change ----------------
def change_password(user: dict, current: str, new: str) -> dict:
    if not verify_password(current, user["password_hash"]):
        raise ValidationFailed("Current password is incorrect")
    if current == new:
        raise ValidationFailed("New password must be different")
    users.update_one({"_id": user["_id"]}, {"$set": {
        "password_hash": hash_password(new), "password_changed_at": _now()}})
    return users.find_one({"_id": user["_id"]})