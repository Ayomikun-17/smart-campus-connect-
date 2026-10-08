# ---------------------------------------------------------------------
# 7.1 Campus-level reports
# ---------------------------------------------------------------------

def total_bookings(db, campus_id, include_cancelled=False):
    """Total number of bookings made at a campus."""
    if include_cancelled:
        row = db.fetch_one(
            "SELECT COUNT(*) AS total FROM bookings WHERE campus_id = ?",
            (campus_id,),
        )
    else:
        row = db.fetch_one(
            "SELECT COUNT(*) AS total FROM bookings "
            "WHERE campus_id = ? AND status = 'active'",
            (campus_id,),
        )
    return row["total"]


def most_used_resources(db, campus_id, limit=5):
    """Resources at a campus ranked by number of active bookings, most first."""
    rows = db.fetch_all(
        """
        SELECT r.resource_code, r.name, COUNT(b.booking_id) AS booking_count
        FROM resources r
        LEFT JOIN bookings b
            ON b.resource_id = r.resource_id AND b.status = 'active'
        WHERE r.campus_id = ?
        GROUP BY r.resource_id
        ORDER BY booking_count DESC
        LIMIT ?
        """,
        (campus_id, limit),
    )
    return rows


def average_booking_duration(db, campus_id):
    """Average duration (minutes) of active bookings at a campus."""
    row = db.fetch_one(
        "SELECT AVG(duration_minutes) AS avg_duration FROM bookings "
        "WHERE campus_id = ? AND status = 'active'",
        (campus_id,),
    )
    avg = row["avg_duration"]
    return round(avg, 1) if avg is not None else 0.0


def campus_summary(db, campus_id):
    """Bundles the three campus-level stats into one dict -- convenient
    for both the GUI report screen and quick debugging/printing."""
    campus = db.fetch_one(
        "SELECT * FROM campuses WHERE campus_id = ?", (campus_id,)
    )
    return {
        "campus_name": campus["name"] if campus else "Unknown",
        "total_bookings": total_bookings(db, campus_id),
        "most_used_resources": most_used_resources(db, campus_id),
        "average_duration_minutes": average_booking_duration(db, campus_id),
    }


# ---------------------------------------------------------------------
# 7.2 Cross-campus comparison (System Operator only)
# ---------------------------------------------------------------------

def compare_all_campuses(db):
    """
    One row per campus with booking totals and average duration side by
    side -- what a SystemOperator's comparison screen would show.
    """
    rows = db.fetch_all(
        """
        SELECT c.campus_id,
               c.name AS campus_name,
               c.max_duration_minutes,
               c.earliest_hour,
               c.latest_hour,
               c.priority_rule,
               COUNT(CASE WHEN b.status = 'active' THEN 1 END) AS total_bookings,
               ROUND(AVG(CASE WHEN b.status = 'active'
                         THEN b.duration_minutes END), 1) AS avg_duration_minutes
        FROM campuses c
        LEFT JOIN bookings b ON b.campus_id = c.campus_id
        GROUP BY c.campus_id
        ORDER BY total_bookings DESC
        """
    )
    return rows


def busiest_campus(db):
    """Convenience wrapper: which campus has the most active bookings."""
    rows = compare_all_campuses(db)
    return rows[0] if rows else None