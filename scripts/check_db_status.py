"""Inspect the configured MySQL database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def check_database():
    with engine.connect() as connection:
        print("=" * 80)
        print("DATABASE INFORMATION")
        print("=" * 80)
        row = connection.execute(text("SELECT DATABASE() AS database_name, VERSION() AS database_version")).fetchone()
        print(f"Database Name: {row[0]}")
        print(f"MySQL Version: {row[1][:50]}...")
        print()

        print("=" * 80)
        print("TABLES IN DATABASE")
        print("=" * 80)
        tables = connection.execute(
            text(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
                """
            )
        ).fetchall()
        print(f"Total tables: {len(tables)}\n")
        for table in tables:
            print(f"  - {table[0]}")
        print()

        print("=" * 80)
        print("ROLE TABLE")
        print("=" * 80)
        roles = connection.execute(text("SELECT role_id, role_name, description FROM `Role` ORDER BY role_id")).fetchall()
        print(f"Total roles: {len(roles)}\n")
        for role in roles:
            print(f"  ID: {role[0]}, Name: {role[1]}, Desc: {role[2]}")
        print()

        print("=" * 80)
        print("USER TABLE STRUCTURE")
        print("=" * 80)
        columns = connection.execute(
            text(
                """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'User'
                ORDER BY ORDINAL_POSITION
                """
            )
        ).fetchall()
        print(f"Total columns: {len(columns)}\n")
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            default = f" DEFAULT: {col[3]}" if col[3] is not None else ""
            print(f"  - {col[0]:<25} {col[1]:<20} {nullable}{default}")
        print()

        print("=" * 80)
        print("USERS IN DATABASE")
        print("=" * 80)
        users = connection.execute(
            text(
                """
                SELECT
                    u.user_id,
                    u.role_id,
                    r.role_name,
                    u.username,
                    u.email,
                    DATE_FORMAT(u.created_at, '%Y-%m-%d %H:%i:%s') AS created_at
                FROM `User` u
                LEFT JOIN `Role` r ON u.role_id = r.role_id
                ORDER BY u.user_id
                """
            )
        ).fetchall()
        print(f"Total users: {len(users)}\n")
        if users:
            print(f"{'ID':<6} {'Role ID':<8} {'Role Name':<18} {'Username':<25} {'Email':<35}")
            print("-" * 100)
            for user in users:
                print(f"{user[0]:<6} {user[1]:<8} {(user[2] or 'NULL'):<18} {user[3]:<25} {user[4]:<35}")
        else:
            print("  No users found in database")
        print()

        print("=" * 80)
        print("USER STATISTICS BY ROLE")
        print("=" * 80)
        stats = connection.execute(
            text(
                """
                SELECT r.role_name, COUNT(u.user_id) AS total_users
                FROM `Role` r
                LEFT JOIN `User` u ON r.role_id = u.role_id
                GROUP BY r.role_name
                ORDER BY COUNT(u.user_id) DESC, r.role_name
                """
            )
        ).fetchall()
        for stat in stats:
            print(f"  {stat[0]:<18}: {stat[1]} user(s)")
        print()
        print("=" * 80)


if __name__ == "__main__":
    try:
        check_database()
    except Exception as exc:
        print(f"Error: {exc}")
        raise
