
from getpass import getpass
from sqlalchemy import select

from main import SessionLocal, User, password_hash

email = input("Enter admin email: ").strip().lower()
new_password = getpass("Enter new password: ")

if len(new_password) < 8:
    raise ValueError("Password must have at least 8 characters.")

with SessionLocal() as db:
    admin = db.scalar(
        select(User).where(
            User.email == email,
            User.role == "admin"
        )
    )

    if admin is None:
        print("Admin account not found.")
    else:
        admin.password_hash = password_hash(new_password)
        db.commit()
        print("Admin password updated successfully!")
