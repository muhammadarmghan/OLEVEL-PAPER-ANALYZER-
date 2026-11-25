"""Check that the schema builds and satisfies the lecturer's rubric policy.

Run from the project root:  python -m scripts.verify_schema
"""
import sys

from sqlalchemy.orm import configure_mappers

from app import create_app
from app.extensions import db

MIN_TABLES = 40


def main() -> int:
    app = create_app("testing")
    with app.app_context():
        configure_mappers()  # raises if any relationship is misconfigured
        db.create_all()
        tables = db.metadata.sorted_tables

        referenced = {fk.column.table.name for t in tables for fk in t.foreign_keys}
        standalone = [t.name for t in tables if not t.foreign_keys and t.name not in referenced]
        fk_count = sum(len(t.foreign_keys) for t in tables)

        print(f"Tables created      : {len(tables)} (minimum {MIN_TABLES})")
        print(f"Foreign keys        : {fk_count}")
        print(f"Standalone tables   : {standalone or 'none'}")
        for t in tables:
            print(f"  - {t.name}")

        ok = len(tables) >= MIN_TABLES and not standalone
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
