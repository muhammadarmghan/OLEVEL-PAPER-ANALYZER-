import sqlite3

from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

# Naming convention keeps constraint names stable, which makes Alembic
# migrations (especially on SQLite) predictable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))
migrate = Migrate()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite ignores foreign keys (and ON DELETE CASCADE) unless told otherwise."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
