"""Legacy SQL Server migration helper replaced by MySQL schema import."""

from pathlib import Path


if __name__ == "__main__":
    schema = Path(__file__).resolve().parents[1] / "docs" / "database" / "Database_MySQL_V1.sql"
    print("This project now uses MySQL.")
    print(f"Import the canonical schema instead: {schema}")
