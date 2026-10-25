import getpass
import sys

from app.core.database import init_indexes, users
from app.core.exceptions import BookingError
from app.services.auth_service import create_admin

init_indexes()

if users.find_one({"role": "admin"}):
    sys.exit("An admin already exists. Log in as that admin and use "
             "POST /admin/admins to add more admins.")

name = input("First admin name: ").strip()
email = input("First admin email: ").strip()
password = getpass.getpass("Password (min 8 chars, letters + digits): ")
if password != getpass.getpass("Confirm password: "):
    sys.exit("Passwords do not match")

try:
    create_admin(name, email, password, created_by="bootstrap-script")
    print(f"First admin created: {email.lower()}")
except BookingError as e:
    sys.exit(f"Failed: {e}")