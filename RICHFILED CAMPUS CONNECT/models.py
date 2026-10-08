"""
models.py
OOP layer for the Smart Campus Resource Booking System.

Classes here own the "business logic" -- they read/write through a
Database instance but never touch Tkinter, and the GUI never writes
raw SQL directly. That separation is what lets the GUI be swapped
out later without touching this file.
"""

import hashlib
from datetime import datetime, timedelta


# ---------------------------------------------------------------------
# Password helper
# ---------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """SHA-256 hash. Good enough for an academic project; for production
    you'd use something with a per-user salt like bcrypt."""
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# CampusPolicy -- the "rules separated from core logic" requirement
# ---------------------------------------------------------------------

class CampusPolicy:
    """
    Wraps a campus's booking rules and validates a proposed booking
    against them. Booking code calls policy.validate_booking(...)
    and never needs to know *which* campus it is -- new campuses with
    new rules just need a new row in the `campuses` table, no new code.
    """

    def __init__(self, campus_id, name, max_duration_minutes,
                 earliest_hour, latest_hour, priority_rule):
        self.campus_id = campus_id
        self.name = name
        self.max_duration_minutes = max_duration_minutes
        self.earliest_hour = earliest_hour
        self.latest_hour = latest_hour
        self.priority_rule = priority_rule

    def describe(self) -> str:
        return (f"{self.name}: max {self.max_duration_minutes} min/session, "
                f"bookable {self.earliest_hour}:00-{self.latest_hour}:00, "
                f"priority rule: {self.priority_rule}")

    def validate_booking(self, start_time_str, duration_minutes):
        """
        Returns (True, "") if a booking request is allowed by this
        campus's policy, otherwise (False, "reason").
        Does NOT check for overlaps -- that's a separate concern,
        handled with other existing bookings (see Booking.overlaps).
        """
        try:
            start_dt = datetime.strptime(start_time_str, "%H:%M")
        except ValueError:
            return False, "Start time must be in HH:MM format."

        if duration_minutes <= 0:
            return False, "Duration must be a positive number of minutes."

        if duration_minutes > self.max_duration_minutes:
            return False, (f"Duration exceeds this campus's max of "
                            f"{self.max_duration_minutes} minutes.")

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        campus_open = start_dt.replace(hour=self.earliest_hour, minute=0)
        campus_close = start_dt.replace(hour=self.latest_hour, minute=0)

        if start_dt < campus_open or end_dt > campus_close:
            return False, (f"Booking must fall between {self.earliest_hour}:00 "
                            f"and {self.latest_hour}:00 for this campus.")

        return True, ""

    @staticmethod
    def load(db, campus_id):
        """Fetch a campus's row from the DB and wrap it as a CampusPolicy."""
        row = db.fetch_one(
            "SELECT * FROM campuses WHERE campus_id = ?", (campus_id,)
        )
        if row is None:
            return None
        return CampusPolicy(
            row["campus_id"], row["name"], row["max_duration_minutes"],
            row["earliest_hour"], row["latest_hour"], row["priority_rule"]
        )


# ---------------------------------------------------------------------
# User hierarchy
# ---------------------------------------------------------------------

class User:
    """Base class. Shared login/identity data for every role."""

    role = "user"  # overridden by subclasses

    def __init__(self, db, user_id, username, campus_id=None):
        self.db = db
        self.user_id = user_id
        self.username = username
        self.campus_id = campus_id  # None for SystemOperator

    # ---- authentication ----

    @staticmethod
    def register(db, username, plain_password, role, campus_id=None):
        """Creates a new user account. Returns (User subclass instance, "")
        on success, or (None, "error message") on failure."""
        if role not in ("lecturer", "admin", "operator"):
            return None, "Invalid role."

        existing = db.fetch_one(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        )
        if existing:
            return None, "That username is already taken."

        if role in ("lecturer", "admin") and campus_id is None:
            return None, "This role requires a campus to be selected."

        cur = db.execute(
            "INSERT INTO users (username, password, role, campus_id) "
            "VALUES (?, ?, ?, ?)",
            (username, hash_password(plain_password), role, campus_id),
        )
        return User.load(db, cur.lastrowid), ""

    @staticmethod
    def login(db, username, plain_password):
        """Returns (User subclass instance, "") on success,
        or (None, "error message") on failure."""
        row = db.fetch_one(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        if row is None:
            return None, "No such user."
        if row["password"] != hash_password(plain_password):
            return None, "Incorrect password."
        return User._from_row(db, row), ""

    @staticmethod
    def load(db, user_id):
        row = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        return User._from_row(db, row)

    @staticmethod
    def list_lecturers_for_campus(db, campus_id):
        """Used by CampusAdministrator for the password-reset picker."""
        rows = db.fetch_all(
            "SELECT * FROM users WHERE campus_id = ? AND role = 'lecturer' "
            "ORDER BY username",
            (campus_id,),
        )
        return [User._from_row(db, r) for r in rows]

    @staticmethod
    def _from_row(db, row):
        """Turns a DB row into the correct subclass instance."""
        cls_map = {
            "lecturer": Lecturer,
            "admin": CampusAdministrator,
            "operator": SystemOperator,
        }
        cls = cls_map[row["role"]]
        return cls(db, row["user_id"], row["username"], row["campus_id"])


class Lecturer(User):
    role = "lecturer"

    def get_active_campus_policy(self):
        return CampusPolicy.load(self.db, self.campus_id)

    def list_available_resources(self):
        return Resource.list_for_campus(self.db, self.campus_id)

    def book_resource(self, resource_id, booking_date, start_time, duration_minutes):
        """
        Full validation pipeline for a booking:
        1. Campus policy check (duration/hours allowed)
        2. Overlap check against existing bookings on that resource
        3. Insert if both pass
        Returns (Booking or None, "error message" or "").
        """
        policy = self.get_active_campus_policy()
        if policy is None:
            return None, "No active campus policy found."

        ok, reason = policy.validate_booking(start_time, duration_minutes)
        if not ok:
            return None, reason

        conflict = Booking.find_overlap(
            self.db, resource_id, booking_date, start_time, duration_minutes
        )
        if conflict is not None:
            return None, "This resource is already booked for an overlapping time."

        booking = Booking.create(
            self.db, resource_id, self.user_id, self.campus_id,
            booking_date, start_time, duration_minutes
        )
        return booking, ""

    def get_booking_history(self):
        return Booking.list_for_lecturer(self.db, self.user_id)

    def cancel_booking(self, booking_id):
        return Booking.cancel(self.db, booking_id, owner_lecturer_id=self.user_id)


class CampusAdministrator(User):
    role = "admin"

    def add_resource(self, resource_code, name, resource_type):
        return Resource.create(self.db, resource_code, name, resource_type, self.campus_id)

    def update_resource(self, resource_id, **fields):
        return Resource.update(self.db, resource_id, self.campus_id, **fields)

    def remove_resource(self, resource_id):
        return Resource.deactivate(self.db, resource_id, self.campus_id)

    def list_campus_resources(self):
        return Resource.list_for_campus(self.db, self.campus_id)

    def list_campus_bookings(self):
        return Booking.list_for_campus(self.db, self.campus_id)

    # ---- password reset (section: forgot password, admin-managed) ----

    def list_campus_lecturers(self):
        return User.list_lecturers_for_campus(self.db, self.campus_id)

    def reset_lecturer_password(self, lecturer_user_id, new_password):
        """
        Resets a lecturer's password. Deliberately scoped to lecturers on
        THIS admin's own campus only -- an admin from Campus A can't touch
        a user on Campus B, consistent with the rest of the access-control
        design. Returns (True, "") or (False, "reason").
        """
        if not new_password or len(new_password) < 4:
            return False, "New password must be at least 4 characters."

        row = self.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ? AND campus_id = ? AND role = 'lecturer'",
            (lecturer_user_id, self.campus_id),
        )
        if row is None:
            return False, "That lecturer was not found on your campus."

        self.db.execute(
            "UPDATE users SET password = ? WHERE user_id = ?",
            (hash_password(new_password), lecturer_user_id),
        )
        return True, ""


class SystemOperator(User):
    role = "operator"

    def list_all_campuses(self):
        return self.db.fetch_all("SELECT * FROM campuses")

    def list_all_bookings(self):
        return Booking.list_all(self.db)


# ---------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------

class Resource:
    def __init__(self, resource_id, resource_code, name, resource_type,
                 campus_id, is_active):
        self.resource_id = resource_id
        self.resource_code = resource_code
        self.name = name
        self.resource_type = resource_type
        self.campus_id = campus_id
        self.is_active = is_active

    @staticmethod
    def create(db, resource_code, name, resource_type, campus_id):
        try:
            cur = db.execute(
                "INSERT INTO resources (resource_code, name, resource_type, campus_id) "
                "VALUES (?, ?, ?, ?)",
                (resource_code, name, resource_type, campus_id),
            )
        except Exception:
            # UNIQUE(campus_id, resource_code) violation
            return None, "A resource with that code already exists on this campus."
        row = db.fetch_one(
            "SELECT * FROM resources WHERE resource_id = ?", (cur.lastrowid,)
        )
        return Resource._from_row(row), ""

    @staticmethod
    def update(db, resource_id, campus_id, **fields):
        allowed = {"name", "resource_type", "is_active"}
        set_clause = ", ".join(f"{k} = ?" for k in fields if k in allowed)
        if not set_clause:
            return False
        values = [v for k, v in fields.items() if k in allowed]
        values += [resource_id, campus_id]
        db.execute(
            f"UPDATE resources SET {set_clause} "
            f"WHERE resource_id = ? AND campus_id = ?",
            values,
        )
        return True

    @staticmethod
    def deactivate(db, resource_id, campus_id):
        db.execute(
            "UPDATE resources SET is_active = 0 "
            "WHERE resource_id = ? AND campus_id = ?",
            (resource_id, campus_id),
        )
        return True

    @staticmethod
    def list_for_campus(db, campus_id):
        rows = db.fetch_all(
            "SELECT * FROM resources WHERE campus_id = ? AND is_active = 1",
            (campus_id,),
        )
        return [Resource._from_row(r) for r in rows]

    @staticmethod
    def _from_row(row):
        return Resource(row["resource_id"], row["resource_code"], row["name"],
                         row["resource_type"], row["campus_id"], row["is_active"])


# ---------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------

class Booking:
    def __init__(self, booking_id, resource_id, lecturer_id, campus_id,
                 booking_date, start_time, duration_minutes, status):
        self.booking_id = booking_id
        self.resource_id = resource_id
        self.lecturer_id = lecturer_id
        self.campus_id = campus_id
        self.booking_date = booking_date
        self.start_time = start_time
        self.duration_minutes = duration_minutes
        self.status = status

    # ---- overlap detection ----

    @staticmethod
    def _time_ranges_overlap(start_a, duration_a, start_b, duration_b):
        fmt = "%H:%M"
        a_start = datetime.strptime(start_a, fmt)
        a_end = a_start + timedelta(minutes=duration_a)
        b_start = datetime.strptime(start_b, fmt)
        b_end = b_start + timedelta(minutes=duration_b)
        # Standard interval overlap test.
        return a_start < b_end and b_start < a_end

    @staticmethod
    def find_overlap(db, resource_id, booking_date, start_time, duration_minutes):
        """Returns the first conflicting active booking row, or None."""
        rows = db.fetch_all(
            "SELECT * FROM bookings WHERE resource_id = ? AND booking_date = ? "
            "AND status = 'active'",
            (resource_id, booking_date),
        )
        for row in rows:
            if Booking._time_ranges_overlap(
                start_time, duration_minutes, row["start_time"], row["duration_minutes"]
            ):
                return row
        return None

    # ---- CRUD ----

    @staticmethod
    def create(db, resource_id, lecturer_id, campus_id, booking_date,
               start_time, duration_minutes):
        cur = db.execute(
            "INSERT INTO bookings (resource_id, lecturer_id, campus_id, "
            "booking_date, start_time, duration_minutes) VALUES (?, ?, ?, ?, ?, ?)",
            (resource_id, lecturer_id, campus_id, booking_date, start_time, duration_minutes),
        )
        row = db.fetch_one(
            "SELECT * FROM bookings WHERE booking_id = ?", (cur.lastrowid,)
        )
        return Booking._from_row(row)

    @staticmethod
    def cancel(db, booking_id, owner_lecturer_id=None):
        """If owner_lecturer_id is given, only cancels if that lecturer owns it
        (prevents one lecturer cancelling another's booking)."""
        if owner_lecturer_id is not None:
            row = db.fetch_one(
                "SELECT * FROM bookings WHERE booking_id = ? AND lecturer_id = ?",
                (booking_id, owner_lecturer_id),
            )
            if row is None:
                return False, "Booking not found or not yours to cancel."
        db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?",
            (booking_id,),
        )
        return True, ""

    @staticmethod
    def list_for_lecturer(db, lecturer_id):
        rows = db.fetch_all(
            "SELECT * FROM bookings WHERE lecturer_id = ? ORDER BY booking_date DESC",
            (lecturer_id,),
        )
        return [Booking._from_row(r) for r in rows]

    @staticmethod
    def list_for_campus(db, campus_id):
        rows = db.fetch_all(
            "SELECT * FROM bookings WHERE campus_id = ? ORDER BY booking_date DESC",
            (campus_id,),
        )
        return [Booking._from_row(r) for r in rows]

    @staticmethod
    def list_all(db):
        rows = db.fetch_all("SELECT * FROM bookings ORDER BY booking_date DESC")
        return [Booking._from_row(r) for r in rows]

    @staticmethod
    def _from_row(row):
        return Booking(row["booking_id"], row["resource_id"], row["lecturer_id"],
                        row["campus_id"], row["booking_date"], row["start_time"],
                        row["duration_minutes"], row["status"])
