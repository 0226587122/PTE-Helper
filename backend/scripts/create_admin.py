"""Create an admin account, or make an existing account an admin.

    python -m scripts.create_admin --email you@example.com --name "Your Name"

You'll be asked for a password. To run without a prompt, set ADMIN_PASSWORD in the environment.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.db import session_factory
from app.models import User
from app.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Admin")
    args = parser.parse_args()
    email = args.email.strip().lower()

    with session_factory()() as db:
        user = db.scalars(select(User).where(User.email == email)).first()
        if user:
            user.role = "admin"
            db.commit()
            print(f"{email} is now an admin. Their password hasn't changed.")
            return 0
        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password (at least 8 characters): ")
        if len(password) < 8:
            print("The password needs at least 8 characters.")
            return 1
        db.add(User(email=email, display_name=args.name, password_hash=hash_password(password), role="admin"))
        db.commit()
        print(f"Created admin account {email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
