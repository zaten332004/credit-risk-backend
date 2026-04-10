"""Execute the canonical MySQL schema file statement by statement."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def _split_mysql_statements(sql_content: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).rstrip().rstrip(";"))
            current = []
    if current:
        statements.append("\n".join(current).strip())
    return [stmt for stmt in statements if stmt.strip()]


def execute_sql_file(filepath: Path) -> None:
    sql_content = filepath.read_text(encoding="utf-8")
    statements = _split_mysql_statements(sql_content)

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in statements:
                print(f"Executing: {statement[:80]}...")
                connection.execute(text(statement))
            transaction.commit()
            print("All statements executed successfully.")
        except Exception:
            transaction.rollback()
            raise


if __name__ == "__main__":
    filepath = Path(__file__).resolve().parents[1] / "docs" / "database" / "Database_MySQL_V1.sql"
    print(f"Executing SQL script: {filepath}")
    execute_sql_file(filepath)
    print("Script execution completed.")
