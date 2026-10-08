from database import Database
from gui import App


# Each tuple: (name, max_duration_minutes, earliest_hour, latest_hour, priority_rule)
# These satisfy section 5.1: at least 3 campuses, each with different constraints.
DEFAULT_CAMPUSES = [
    ("Pretoria",  120, 8, 18, "lecturer_first"),      # short bookings, standard hours, lecturers prioritised
    ("Cape Town", 240, 7, 20, "none"),                 # longer bookings allowed, extended hours, no priority rule
    ("Durban",     90, 9, 17, "first_come_first_served"),
    ("Joburg",      120, 7, 20,  "none"), # shortest bookings, restricted hours
]


def seed_campuses(db):
    """Insert the default campuses only if the campuses table is empty,
    so restarting the app never creates duplicates."""
    existing = db.fetch_one("SELECT COUNT(*) AS total FROM campuses")
    if existing["total"] > 0:
        return  # already seeded

    for name, max_dur, earliest, latest, priority in DEFAULT_CAMPUSES:
        db.execute(
            "INSERT INTO campuses (name, max_duration_minutes, earliest_hour, "
            "latest_hour, priority_rule) VALUES (?, ?, ?, ?, ?)",
            (name, max_dur, earliest, latest, priority),
        )
    print(f"Seeded {len(DEFAULT_CAMPUSES)} default campuses.")


def main():
    db = Database()
    seed_campuses(db)

    app = App(db)
    app.mainloop()

    db.close()


if __name__ == "__main__":
    main()