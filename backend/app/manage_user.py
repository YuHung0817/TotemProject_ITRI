import argparse
from getpass import getpass

from sqlalchemy import func, select

from app.db.models import User
from app.db.session import SessionLocal
from app.services.auth_service import hash_password
from app.services.database_catalog_service import DEFAULT_USER_ID, ensure_default_data


def create_single_user() -> None:
    username = input("Username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty")
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")

    with SessionLocal() as db:
        user_count = db.scalar(select(func.count(User.id))) or 0
        user = ensure_default_data(db)
        if user_count > 1:
            raise SystemExit("More than one user exists; refusing single-user initialization")
        duplicate = db.scalar(select(User).where(User.username == username, User.id != user.id))
        if duplicate is not None:
            raise SystemExit("Username already exists")
        if user.password_hash:
            raise SystemExit("The single user is already initialized")
        user.id = DEFAULT_USER_ID
        user.username = username
        user.password_hash = hash_password(password)
        db.commit()
    print("Single-store user created successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the single Totem store account")
    parser.add_argument("command", choices=["create"])
    args = parser.parse_args()
    if args.command == "create":
        create_single_user()


if __name__ == "__main__":
    main()
