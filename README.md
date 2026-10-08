# smart-campus-connect-
application page that is built with python for school admin etc
Smart Campus Resource Booking System
A desktop app for booking campus resources (labs, projectors, rooms, equipment) across multiple campuses, built for Richfield Graduate Institute of Technology. Each campus has its own booking rules, and what you can do depends on your role.
Built with Python, Tkinter/ttk (GUI) and SQLite (storage). No third-party packages needed.
________________________________________
Features
The Three roles, each with its own dashboard: 
Lecturer: browse resources on their campus, book a resource, view booking history, cancel their own bookings.
Campus Administrator: add and remove resources, see every booking on their campus, reset a lecturer's password.
System Operator: system-wide view with a cross-campus comparison and all bookings from every campus.
•	Per-campus booking rules (max duration, opening hours, priority rule) stored in the database, so a new campus with different rules is just a new row, no code change.
•	Booking validation: duration limit, campus hours, and overlap detection on the same resource and date.
•	Soft delete for resources: removed resources are hidden, but existing bookings stay in the history.
•	Cancel, don't delete: bookings are marked cancelled, so reports and history stay intact.
•	Campus reports: total bookings, most-used resources, average booking duration, and a busiest-campus summary.
•	Login and registration with SHA-256 password hashing.
________________________________________
Thi is the Project structure
.
├── main.py             # Entry point: opens the DB, seeds campuses, launches the GUI
├── database.py         # Database class: SQLite connection, helpers, schema creation
├── models.py           # Business logic: CampusPolicy, User hierarchy, Resource, Booking
├── reports.py          # Reporting queries (campus-level and cross-campus)
├── gui.py              # Tkinter screens: login, register, and the three dashboards
├── campus_booking.db   # SQLite database (created automatically on first run)
└── assets/             # Optional: richfield_logo.png, richfield_logo_small.png
•	database.py is the only module that imports sqlite3. Everything else goes through the Database class (execute, fetch_one, fetch_all).
•	models.py holds all the rules and never touches Tkinter.
•	gui.py never writes raw SQL for actions. It calls model methods. The one exception is a few small read-only lookups, such as loading campus names.
________________________________________
Getting started
Run it
python main.py
On first run the app creates campus_booking.db and seeds the default campuses. (The file names are lowercase in the examples above. Rename the uploaded Main.py and database.PY to match, because main.py imports database and the extension case matters on Linux/macOS.)
Logo (optional)
Put richfield_logo.png and richfield_logo_small.png in an assets/ folder next to gui.py. If it goes missing, the app runs without logos.
________________________________________
Campuses and rules
Seeded on first run only (when the campuses table is empty):
Campus	Max duration	Bookable hours	Priority rule
Pretoria	120 min	08:00 – 18:00	lecturer_first
Cape Town	240 min	07:00 – 20:00	none
Durban	90 min	09:00 – 17:00	first_come_first_served
Joburg	120 min	07:00 – 20:00	none
A booking must satisfy all of these:
1.	Start time is valid HH:MM.
2.	Duration is greater than 0 and no more than the campus maximum.
3.	The whole booking (start to end) falls inside the campus's opening hours.
4.	It doesn't overlap an active booking on the same resource and date.
________________________________________
Database schema
Table	Purpose
campuses	Campus name and booking rules (max_duration_minutes, earliest_hour, latest_hour, priority_rule)
users	Username, hashed password, role (lecturer / admin / operator), campus_id (NULL for operators)
resources	Bookable items with a resource_code unique per campus and an is_active soft-delete flag
bookings	Resource, lecturer, campus, date (YYYY-MM-DD), start time (HH:MM), duration, status (active / cancelled)
Foreign keys are enabled (PRAGMA foreign_keys = ON).
________________________________________
Using the app
1.	Register: pick a username, password, role, and campus (operators don't pick a campus).
2.	Log in to land on the dashboard for your role.
3.	Lecturer: select a resource, enter date (YYYY-MM-DD), start time (HH:MM) and duration in minutes, then click Book Resource. Select a row in My Bookings and click Cancel to cancel.
4.	Campus Admin: add a resource with a code, name, and type, or remove one. Use the reset panel to give a lecturer on your campus a new password (minimum 4 characters).
5.	System Operator: compare campuses side by side and see the busiest campus. Click Refresh to update.
Forgotten password? A lecturer asks their Campus Administrator to reset it.


Tech notes
•	GUI screens are ttk.Frame subclasses swapped in and out of one container by App._swap.
•	Styling uses the clam ttk theme with Richfield navy (#123373) as the primary colour.
•	sqlite3.Row is used as the row factory, so columns are accessed by name (row["username"]).

