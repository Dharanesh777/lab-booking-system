"""database.py - SQLAlchemy engine, session management, and startup database seeding."""

import os
import csv
import sqlite3
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "lab_booking.db"
DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enforce foreign key constraints in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency providing a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def find_source_dir() -> Path:
    """Finds directory containing schema.sql and CSV seed files."""
    db_subdir = BASE_DIR / "Database"
    if (db_subdir / "schema.sql").exists() and (db_subdir / "labs.csv").exists():
        return db_subdir
    if (BASE_DIR / "schema.sql").exists() and (BASE_DIR / "labs.csv").exists():
        return BASE_DIR
    return BASE_DIR



def init_db(force: bool = False) -> None:
    """Startup check: seeds lab_booking.db from schema.sql and CSVs if missing or unpopulated."""
    db_exists = DB_FILE.exists()
    needs_seed = force or not db_exists

    if db_exists and not force:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM labs")
                count = cur.fetchone()[0]
                if count == 0:
                    needs_seed = True
        except Exception:
            needs_seed = True

    if not needs_seed:
        return

    src_dir = find_source_dir()
    schema_path = src_dir / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found in {src_dir}")

    conn = sqlite3.connect(DB_FILE)
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        tables = ["periods", "labs", "equipment", "semester_timetables", "bookings", "fault_reports"]
        for tbl in tables:
            csv_path = src_dir / f"{tbl}.csv"
            if not csv_path.exists():
                continue
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if not rows:
                    continue
                cols = list(rows[0].keys())
                placeholders = ",".join(["?"] * len(cols))
                insert_sql = f"INSERT INTO {tbl} ({','.join(cols)}) VALUES ({placeholders})"
                cleaned_rows = [
                    [(val if val != "" else None) for val in row.values()]
                    for row in rows
                ]
                conn.executemany(insert_sql, cleaned_rows)
        conn.commit()
    finally:
        conn.close()
