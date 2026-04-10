"""Insert demo users for the active MySQL roles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def insert_demo_users() -> None:
    sql = """
    INSERT INTO `User` (`role_id`, `username`, `password_hash`, `email`, `full_name`, `is_active`)
    VALUES
      (1, 'admin_demo', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', 'admin.demo@creditbank.com', 'Admin Demo', TRUE),
      (2, 'manager_demo', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', 'manager.demo@creditbank.com', 'Manager Demo', TRUE),
      (3, 'risk_analyst_demo', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', 'risk.analyst.demo@creditbank.com', 'Risk Analyst Demo', TRUE)
    """

    with engine.connect() as connection:
        check_query = text("SELECT COUNT(*) FROM `User` WHERE username IN ('admin_demo', 'manager_demo', 'risk_analyst_demo')")
        existing_count = connection.execute(check_query).scalar() or 0
        if existing_count > 0:
            print(f"{existing_count} demo users already exist. Skipping insertion.")
            return

        connection.execute(text(sql))
        connection.commit()

        rows = connection.execute(
            text(
                """
                SELECT u.user_id, r.role_name, u.username, u.email
                FROM `User` u
                INNER JOIN `Role` r ON u.role_id = r.role_id
                WHERE u.username IN ('admin_demo', 'manager_demo', 'risk_analyst_demo')
                ORDER BY u.role_id
                """
            )
        ).fetchall()

        print("Inserted demo users:")
        for row in rows:
            print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}")


if __name__ == "__main__":
    insert_demo_users()
