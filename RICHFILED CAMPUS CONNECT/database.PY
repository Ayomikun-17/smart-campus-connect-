"""
database.py
Handles the SQLite connection and schema creation for the
Smart Campus Resource Booking System.

All other modules talk to the database ONLY through the Database
class below -- nobody else should import sqlite3 directly.
"""

import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "campus_booking.db")


class Database:
    """Single shared connection + query helpers used by every model class."""

    def __init__(self, db_path=DB_FILE):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Rows come back as dict-like objects instead of plain tuples,
        # so code elsewhere can do row["username"] instead of row[1].
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    # ---------- generic helpers ----------

    def execute(self, query, params=()):
        """For INSERT / UPDATE / DELETE. Returns the cursor (e.g. for lastrowid)."""
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def fetch_all(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()

    def fetch_one(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur.fetchone()

    def close(self):
        self.conn.close()

    # ---------- schema ----------

    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS campuses (
                campus_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                max_duration_minutes INTEGER NOT NULL,
                earliest_hour       INTEGER NOT NULL,  -- 24h, e.g. 8
                latest_hour         INTEGER NOT NULL,  -- 24h, e.g. 18
                priority_rule       TEXT NOT NULL       -- e.g. 'lecturer_first', 'none'
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT NOT NULL UNIQUE,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL CHECK (role IN
                                ('lecturer', 'admin', 'operator')),
                campus_id   INTEGER,                   -- NULL for operators (all-campus access)
                FOREIGN KEY (campus_id) REFERENCES campuses (campus_id)
            );

            CREATE TABLE IF NOT EXISTS resources (
                resource_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_code TEXT NOT NULL,            -- e.g. 'LAB-01'
                name          TEXT NOT NULL,
                resource_type TEXT NOT NULL,             -- 'lab', 'projector', 'room', etc.
                campus_id     INTEGER NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1, -- soft-delete flag
                FOREIGN KEY (campus_id) REFERENCES campuses (campus_id),
                UNIQUE (campus_id, resource_code)
            );

            CREATE TABLE IF NOT EXISTS bookings (
                booking_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id     INTEGER NOT NULL,
                lecturer_id     INTEGER NOT NULL,
                campus_id       INTEGER NOT NULL,
                booking_date    TEXT NOT NULL,   -- 'YYYY-MM-DD'
                start_time      TEXT NOT NULL,   -- 'HH:MM'
                duration_minutes INTEGER NOT NULL,
                status          TEXT NOT NULL DEFAULT 'active'
                                    CHECK (status IN ('active', 'cancelled')),
                FOREIGN KEY (resource_id) REFERENCES resources (resource_id),
                FOREIGN KEY (lecturer_id) REFERENCES users (user_id),
                FOREIGN KEY (campus_id) REFERENCES campuses (campus_id)
            );
            """
        )
        self.conn.commit()