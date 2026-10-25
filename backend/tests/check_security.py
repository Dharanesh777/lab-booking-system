from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import JWT_ALGORITHM, SECRET_KEY
from app.core.security import (create_access_token, decode_access_token,
                               hash_password, verify_password)


def check(label, cond):
    print(("OK   " if cond else "FAIL ") + label)


h1 = hash_password("MyPass@123")
h2 = hash_password("MyPass@123")
check("password verifies", verify_password("MyPass@123", h1))
check("wrong password rejected", not verify_password("wrong", h1))
check("same password gives different hashes (salted)", h1 != h2)
check("plain password not stored in hash", "MyPass@123" not in h1)
check("malformed stored hash returns False, no crash", not verify_password("x", "garbage"))

tok = create_access_token("abc123", "student", "23N999")
data = decode_access_token(tok)
check("token round-trip", data and data["sub"] == "abc123"
      and data["role"] == "student" and data["roll_no"] == "23N999")
check("tampered token rejected", decode_access_token(tok[:-3] + "abc") is None)
check("garbage token rejected", decode_access_token("not.a.token") is None)

old = jwt.encode({"sub": "x", "role": "admin",
                  "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                 SECRET_KEY, algorithm=JWT_ALGORITHM)
check("expired token rejected", decode_access_token(old) is None)

wrong_key = jwt.encode({"sub": "x", "role": "admin"}, "some-other-key" * 3,
                       algorithm=JWT_ALGORITHM)
check("token signed with a different key rejected", decode_access_token(wrong_key) is None)