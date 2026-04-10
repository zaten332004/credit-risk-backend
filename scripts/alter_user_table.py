"""Add missing MySQL columns to the User table if needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from app.db.session import engine


def execute_alter_table():
    columns_to_add = [
        ("phone", "VARCHAR(20) NULL"),
        ("user_type", "VARCHAR(20) NULL"),
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'pending'"),
        ("verification_token", "VARCHAR(255) NULL"),
        ("verification_sent_at", "DATETIME NULL"),
        ("is_email_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("approved_by", "BIGINT NULL"),
        ("approved_at", "DATETIME NULL"),
        ("rejection_reason", "VARCHAR(500) NULL"),
    ]

    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("User")}
    existing_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("User") if fk.get("name")}

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for col_name, col_def in columns_to_add:
                if col_name in existing_columns:
                    print(f"Column {col_name} already exists")
                    continue
                connection.execute(text(f"ALTER TABLE `User` ADD COLUMN `{col_name}` {col_def}"))
                print(f"Added column: {col_name}")

            if "status" in existing_columns or "status" in {name for name, _ in columns_to_add}:
                connection.execute(
                    text(
                        "ALTER TABLE `User` "
                        "MODIFY COLUMN `status` VARCHAR(20) NOT NULL DEFAULT 'pending'"
                    )
                )
                print("Ensured column definition: status")

            if "is_email_verified" in existing_columns or "is_email_verified" in {name for name, _ in columns_to_add}:
                connection.execute(
                    text(
                        "ALTER TABLE `User` "
                        "MODIFY COLUMN `is_email_verified` BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
                print("Ensured column definition: is_email_verified")

            if "approved_by" in existing_columns or "approved_by" in {name for name, _ in columns_to_add}:
                if "FK_User_ApprovedBy" not in existing_foreign_keys:
                    connection.execute(
                        text(
                            "ALTER TABLE `User` "
                            "ADD CONSTRAINT `FK_User_ApprovedBy` "
                            "FOREIGN KEY (`approved_by`) REFERENCES `User` (`user_id`)"
                        )
                    )
                    print("Added foreign key: FK_User_ApprovedBy")
                else:
                    print("Foreign key FK_User_ApprovedBy already exists")

            connection.execute(
                text(
                    "UPDATE `User` "
                    "SET `status` = 'approved' "
                    "WHERE `is_active` = TRUE "
                    "AND `role_id` IS NOT NULL "
                    "AND `verification_token` IS NULL "
                    "AND (`status` IS NULL OR TRIM(`status`) = '' OR `status` = 'pending')"
                )
            )
            print("Backfilled status for active users")

            connection.execute(
                text(
                    "UPDATE `User` "
                    "SET `is_email_verified` = TRUE "
                    "WHERE `is_active` = TRUE "
                    "AND `role_id` IS NOT NULL "
                    "AND `verification_token` IS NULL "
                    "AND (`is_email_verified` IS NULL OR `is_email_verified` = FALSE)"
                )
            )
            print("Backfilled email verification for active users")

            connection.execute(
                text(
                    "UPDATE `User` u "
                    "JOIN `Role` r ON r.`role_id` = u.`role_id` "
                    "SET u.`user_type` = 'manager' "
                    "WHERE (u.`user_type` IS NULL OR TRIM(u.`user_type`) = '') "
                    "AND LOWER(r.`role_name`) = 'manager'"
                )
            )
            connection.execute(
                text(
                    "UPDATE `User` u "
                    "JOIN `Role` r ON r.`role_id` = u.`role_id` "
                    "SET u.`user_type` = 'analyst' "
                    "WHERE (u.`user_type` IS NULL OR TRIM(u.`user_type`) = '') "
                    "AND LOWER(r.`role_name`) IN ('risk analyst', 'analyst')"
                )
            )
            connection.execute(
                text(
                    "UPDATE `User` u "
                    "JOIN `Role` r ON r.`role_id` = u.`role_id` "
                    "SET u.`user_type` = 'admin' "
                    "WHERE (u.`user_type` IS NULL OR TRIM(u.`user_type`) = '') "
                    "AND LOWER(r.`role_name`) = 'admin'"
                )
            )
            print("Backfilled user_type from role")

            connection.execute(
                text(
                    "UPDATE `User` "
                    "SET `approved_at` = COALESCE(`approved_at`, `created_at`) "
                    "WHERE `status` = 'approved'"
                )
            )
            print("Backfilled approved_at for approved users")
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise


if __name__ == "__main__":
    execute_alter_table()
