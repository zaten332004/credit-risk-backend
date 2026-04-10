"""Refresh MySQL risk group seed data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine

RISK_GROUP_ROWS = [
    {
        "group_id": 1,
        "group_name": "No tieu chuan",
        "group_name_en": "Standard Loans",
        "description": "Within due date or overdue less than 10 days",
        "description_vn": "Trong han hoac qua han duoi 10 ngay",
        "days_from": 0,
        "days_to": 9,
        "risk_level": "Rat thap",
        "provision_rate": 0.00,
        "color": "green",
        "icon": "check_circle",
    },
    {
        "group_id": 2,
        "group_name": "No can chu y",
        "group_name_en": "Loans Requiring Attention",
        "description": "Overdue from 10 to less than 90 days",
        "description_vn": "Qua han tu 10 ngay den duoi 90 ngay",
        "days_from": 10,
        "days_to": 89,
        "risk_level": "Thap",
        "provision_rate": 0.01,
        "color": "yellow",
        "icon": "warning",
    },
    {
        "group_id": 3,
        "group_name": "No duoi tieu chuan",
        "group_name_en": "Substandard Loans",
        "description": "Overdue from 91 to 180 days (Beginning of bad debt)",
        "description_vn": "Qua han tu 91 den 180 ngay",
        "days_from": 91,
        "days_to": 180,
        "risk_level": "Trung binh cao",
        "provision_rate": 0.25,
        "color": "orange",
        "icon": "info",
    },
    {
        "group_id": 4,
        "group_name": "No nghi ngo",
        "group_name_en": "Doubtful Loans",
        "description": "Overdue from 181 to 360 days",
        "description_vn": "Qua han tu 181 den 360 ngay",
        "days_from": 181,
        "days_to": 360,
        "risk_level": "Cao",
        "provision_rate": 0.50,
        "color": "red",
        "icon": "error_outline",
    },
    {
        "group_id": 5,
        "group_name": "No co kha nang mat von",
        "group_name_en": "Loss Loans",
        "description": "Overdue over 360 days or unrecoverable",
        "description_vn": "Qua han tren 360 ngay hoac mat kha nang thu hoi",
        "days_from": 361,
        "days_to": 999999,
        "risk_level": "Rat cao",
        "provision_rate": 1.00,
        "color": "dark_red",
        "icon": "cancel",
    },
]


def create_risk_tables() -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("DELETE FROM `Risk_Group`"))
            insert_sql = text(
                """
                INSERT INTO `Risk_Group`
                (`group_id`, `group_name`, `group_name_en`, `description`, `description_vn`, `days_from`, `days_to`, `risk_level`, `provision_rate`, `color`, `icon`)
                VALUES
                (:group_id, :group_name, :group_name_en, :description, :description_vn, :days_from, :days_to, :risk_level, :provision_rate, :color, :icon)
                """
            )
            for row in RISK_GROUP_ROWS:
                connection.execute(insert_sql, row)
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise

        rows = connection.execute(
            text(
                """
                SELECT group_id, group_name, group_name_en, days_from, days_to, risk_level, provision_rate
                FROM `Risk_Group`
                ORDER BY group_id
                """
            )
        ).fetchall()

    print("Risk groups refreshed:")
    for row in rows:
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}-{row[4]} | {row[5]} | {row[6]}")


if __name__ == "__main__":
    create_risk_tables()
