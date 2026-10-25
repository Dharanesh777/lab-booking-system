from datetime import timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import users
from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Any logged-in user. The role is read from the database, not the token,
    so disabling or changing an account takes effect immediately."""
    if creds is None:
        raise AuthError("Not logged in")
    payload = decode_access_token(creds.credentials)
    if not payload:
        raise AuthError("Invalid or expired token")
    try:
        oid = ObjectId(payload["sub"])
    except (InvalidId, KeyError, TypeError):
        raise AuthError("Invalid token")
    user = users.find_one({"_id": oid})
    if not user or not user.get("active", True):
        raise AuthError("Account not found or disabled")

    # tokens issued before the last password change are no longer valid
    changed = user.get("password_changed_at")
    if changed:
        changed_ts = int(changed.replace(tzinfo=timezone.utc).timestamp())
        if int(payload.get("iat", 0)) < changed_ts:
            raise AuthError("Password was changed. Please log in again")
    return user


def require_student(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "student":
        raise ForbiddenError("Students only")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise ForbiddenError("Admins only")
    return user