import json
import sys

from superset.app import create_app

config = json.load(sys.stdin)

username = config["username"]
password = config["password"]

app = create_app()

with app.app_context():
    security_manager = app.appbuilder.sm

    admin_role = security_manager.find_role("Admin")

    if admin_role is None:
        raise RuntimeError("Superset Admin role does not exist.")

    existing_user = security_manager.find_user(
        username=username
    )

    if existing_user:
        if admin_role not in existing_user.roles:
            raise RuntimeError(
                "Existing account does not have Admin role."
            )

        print("[OK] Admin account already exists.")
    else:
        user = security_manager.add_user(
            username=username,
            first_name="BI",
            last_name="Admin",
            email="admin@example.com",
            role=admin_role,
            password=password,
        )

        if not user:
            raise RuntimeError(
                "Failed to create Superset admin account."
            )

        print("[OK] Admin account created successfully.")
