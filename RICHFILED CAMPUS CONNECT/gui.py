import os
import tkinter as tk
from tkinter import ttk, messagebox

from models import User, Lecturer, CampusAdministrator, SystemOperator, Resource, Booking
import reports


# ---------------------------------------------------------------------
# Shared styling
# ---------------------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_LARGE_PATH = os.path.join(ASSETS_DIR, "richfield_logo.png")
LOGO_SMALL_PATH = os.path.join(ASSETS_DIR, "richfield_logo_small.png")

BG_COLOR = "#f4f6f8"
PANEL_COLOR = "#ffffff"
PRIMARY = "#123373"       # Richfield brand navy
PRIMARY_DARK = "#0c2450"
TEXT_DARK = "#1c1c1c"
MUTED = "#6b7280"
SUCCESS = "#2e7d32"
DANGER = "#c62828"

FONT_BASE = ("Segoe UI", 10)
FONT_HEADER = ("Segoe UI", 16, "bold")
FONT_SUBHEADER = ("Segoe UI", 11, "bold")


def configure_styles(root):
    style = ttk.Style(root)
    # 'clam' theme takes custom colors far better than the default on Windows/Linux
    style.theme_use("clam")

    root.configure(bg=BG_COLOR)

    style.configure("TFrame", background=BG_COLOR)
    style.configure("Panel.TFrame", background=PANEL_COLOR)
    style.configure("TLabel", background=BG_COLOR, foreground=TEXT_DARK, font=FONT_BASE)
    style.configure("Panel.TLabel", background=PANEL_COLOR, foreground=TEXT_DARK, font=FONT_BASE)
    style.configure("Header.TLabel", background=BG_COLOR, foreground=PRIMARY, font=FONT_HEADER)
    style.configure("PanelHeader.TLabel", background=PANEL_COLOR, foreground=PRIMARY, font=FONT_HEADER)
    style.configure("Sub.TLabel", background=PANEL_COLOR, foreground=MUTED, font=FONT_BASE)
    style.configure("SubHeader.TLabel", background=PANEL_COLOR, foreground=TEXT_DARK, font=FONT_SUBHEADER)
    style.configure("Error.TLabel", background=PANEL_COLOR, foreground=DANGER, font=FONT_BASE)
    style.configure("Success.TLabel", background=PANEL_COLOR, foreground=SUCCESS, font=FONT_BASE)

    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=6)

    style.configure("Primary.TButton", background=PRIMARY, foreground="white",
                     font=FONT_BASE, padding=8)
    style.map("Primary.TButton", background=[("active", PRIMARY_DARK)])

    style.configure("Secondary.TButton", background="#e5e7eb", foreground=TEXT_DARK,
                     font=FONT_BASE, padding=8)

    style.configure("Danger.TButton", background=DANGER, foreground="white",
                     font=FONT_BASE, padding=6)

    style.configure("Treeview", font=FONT_BASE, rowheight=26)
    style.configure("Treeview.Heading", font=FONT_SUBHEADER)


def load_logo(path):
    """Loads a PNG logo via Tkinter's built-in PhotoImage (Tk 8.6+ reads
    PNG natively, no Pillow needed). Returns None if the file is missing
    so a moved/deleted assets folder degrades gracefully instead of
    crashing the whole app."""
    try:
        return tk.PhotoImage(file=path)
    except tk.TclError:
        return None


# ---------------------------------------------------------------------
# App shell
# ---------------------------------------------------------------------

class App(tk.Tk):
    """Root window. Holds the DB connection, the logged-in user (if any),
    and swaps ttk.Frame screens in and out of one container."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_user = None

        self.title(" Campus Resource Booking System")
        self.geometry("980x640")
        self.minsize(860, 560)

        configure_styles(self)

        # Loaded once here and kept as attributes on App -- Tkinter's
        # PhotoImage has no persistent internal reference, so if we only
        # used a local variable it would get garbage-collected and the
        # image would go blank the moment __init__ returns.
        self.logo_large = load_logo(LOGO_LARGE_PATH)
        self.logo_small = load_logo(LOGO_SMALL_PATH)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.active_frame = None
        self.show_login()

    # ---- screen switching ----

    def _swap(self, frame_cls, *args):
        if self.active_frame is not None:
            self.active_frame.destroy()
        self.active_frame = frame_cls(self.container, self, *args)
        self.active_frame.pack(fill="both", expand=True)

    def show_login(self):
        self.current_user = None
        self._swap(LoginScreen)

    def show_register(self):
        self._swap(RegisterScreen)

    def show_dashboard(self, user):
        self.current_user = user
        if isinstance(user, Lecturer):
            self._swap(LecturerDashboard)
        elif isinstance(user, CampusAdministrator):
            self._swap(AdminDashboard)
        elif isinstance(user, SystemOperator):
            self._swap(OperatorDashboard)

    def logout(self):
        self.show_login()


# ---------------------------------------------------------------------
# Login screen
# ---------------------------------------------------------------------

class LoginScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # centered panel look: outer frame just centers an inner card
        center = ttk.Frame(self)
        center.place(relx=0.5, rely=0.5, anchor="center")

        card = ttk.Frame(center, style="Panel.TFrame", padding=32)
        card.pack()

        row = 0
        if self.app.logo_large is not None:
            ttk.Label(card, image=self.app.logo_large, style="Panel.TLabel") \
                .grid(row=row, column=0, columnspan=2, pady=(0, 16))
            row += 1

        ttk.Label(card, text="Smart Campus Resource Booking System",
                  style="PanelHeader.TLabel").grid(row=row, column=0, columnspan=2, pady=(0, 4))
        row += 1
        ttk.Label(card, text="Richfield Graduate Institute of Technology", style="Sub.TLabel") \
            .grid(row=row, column=0, columnspan=2, pady=(0, 20))
        row += 1

        ttk.Label(card, text="Username", style="Panel.TLabel") \
            .grid(row=row, column=0, sticky="w", pady=4)
        row += 1
        self.username_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.username_var, width=28) \
            .grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        ttk.Label(card, text="Password", style="Panel.TLabel") \
            .grid(row=row, column=0, sticky="w", pady=4)
        row += 1
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=28) \
            .grid(row=row, column=0, columnspan=2, pady=(0, 6))
        row += 1

        self.error_label = ttk.Label(card, text="", style="Error.TLabel", wraplength=280)
        self.error_label.grid(row=row, column=0, columnspan=2, pady=(4, 10))
        row += 1

        ttk.Button(card, text="Log In", style="Primary.TButton",
                   command=self.handle_login).grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
        ttk.Button(card, text="Register a new account", style="Secondary.TButton",
                   command=self.app.show_register).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        ttk.Label(card, text="Forgot your password? Ask your Campus Administrator to reset it.",
                  style="Sub.TLabel", wraplength=280, justify="center") \
            .grid(row=row, column=0, columnspan=2, pady=(12, 0))

        card.bind("<Return>", lambda e: self.handle_login())
        self.bind_all("<Return>", lambda e: self.handle_login())

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self.error_label.config(text="Please enter both username and password.")
            return

        user, err = User.login(self.app.db, username, password)
        if user is None:
            self.error_label.config(text=err)
            return

        self.app.show_dashboard(user)


# ---------------------------------------------------------------------
# Register screen
# ---------------------------------------------------------------------

class RegisterScreen(ttk.Frame):
    ROLE_LABELS = {
        "Lecturer": "lecturer",
        "Campus Administrator": "admin",
        "System Operator": "operator",
    }

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        center = ttk.Frame(self)
        center.place(relx=0.5, rely=0.5, anchor="center")

        card = ttk.Frame(center, style="Panel.TFrame", padding=32)
        card.pack()

        if self.app.logo_small is not None:
            ttk.Label(card, image=self.app.logo_small, style="Panel.TLabel") \
                .grid(row=0, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(card, text="Create an Account", style="PanelHeader.TLabel") \
            .grid(row=1, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(card, text="Username", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.username_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.username_var, width=30) \
            .grid(row=3, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(card, text="Password", style="Panel.TLabel").grid(row=4, column=0, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=30) \
            .grid(row=5, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(card, text="Role", style="Panel.TLabel").grid(row=6, column=0, sticky="w")
        self.role_var = tk.StringVar(value="Lecturer")
        role_combo = ttk.Combobox(card, textvariable=self.role_var, state="readonly",
                                   values=list(self.ROLE_LABELS.keys()), width=27)
        role_combo.grid(row=7, column=0, columnspan=2, pady=(0, 10))
        role_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_campus_visibility())

        self.campus_label = ttk.Label(card, text="Campus", style="Panel.TLabel")
        self.campus_label.grid(row=8, column=0, sticky="w")
        self.campus_var = tk.StringVar()
        self._campus_lookup = {}  # display name -> campus_id
        self.campus_combo = ttk.Combobox(card, textvariable=self.campus_var, state="readonly", width=27)
        self.campus_combo.grid(row=9, column=0, columnspan=2, pady=(0, 6))
        self._load_campuses()

        self.error_label = ttk.Label(card, text="", style="Error.TLabel", wraplength=280)
        self.error_label.grid(row=10, column=0, columnspan=2, pady=(4, 10))

        ttk.Button(card, text="Register", style="Primary.TButton",
                   command=self.handle_register).grid(row=11, column=0, columnspan=2, sticky="ew")
        ttk.Button(card, text="Back to Login", style="Secondary.TButton",
                   command=self.app.show_login).grid(row=12, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _load_campuses(self):
        rows = self.app.db.fetch_all("SELECT campus_id, name FROM campuses ORDER BY name")
        self._campus_lookup = {row["name"]: row["campus_id"] for row in rows}
        self.campus_combo["values"] = list(self._campus_lookup.keys())
        if rows:
            self.campus_var.set(rows[0]["name"])

    def _refresh_campus_visibility(self):
        # System Operators have all-campus access, so no campus picker needed.
        if self.role_var.get() == "System Operator":
            self.campus_label.grid_remove()
            self.campus_combo.grid_remove()
        else:
            self.campus_label.grid()
            self.campus_combo.grid()

    def handle_register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        role_display = self.role_var.get()
        role = self.ROLE_LABELS.get(role_display)

        if not username or not password:
            self.error_label.config(text="Please enter both username and password.")
            return

        campus_id = None
        if role != "operator":
            campus_name = self.campus_var.get()
            campus_id = self._campus_lookup.get(campus_name)
            if campus_id is None:
                self.error_label.config(text="Please select a campus.")
                return

        user, err = User.register(self.app.db, username, password, role, campus_id)
        if user is None:
            self.error_label.config(text=err)
            return

        messagebox.showinfo("Success", "Account created. You can now log in.")
        self.app.show_login()


# ---------------------------------------------------------------------
# Shared header bar (used by all three dashboards)
# ---------------------------------------------------------------------

def build_header(parent, app, title_text, subtitle_text):
    header = tk.Frame(parent, bg=PRIMARY, height=68)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    if app.logo_small is not None:
        tk.Label(header, image=app.logo_small, bg=PRIMARY).pack(side="left", padx=(20, 0), pady=8)

    text_frame = tk.Frame(header, bg=PRIMARY)
    text_frame.pack(side="left", padx=20, pady=8)
    tk.Label(text_frame, text=title_text, bg=PRIMARY, fg="white",
              font=FONT_HEADER).pack(anchor="w")
    tk.Label(text_frame, text=subtitle_text, bg=PRIMARY, fg="#d7e2f2",
              font=FONT_BASE).pack(anchor="w")

    ttk.Button(header, text="Log Out", style="Secondary.TButton",
               command=app.logout).pack(side="right", padx=20, pady=15)
    return header


# ---------------------------------------------------------------------
# Lecturer Dashboard
# ---------------------------------------------------------------------

class LecturerDashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.lecturer = app.current_user
        self.policy = self.lecturer.get_active_campus_policy()

        build_header(self, app,
                     f"Welcome, {self.lecturer.username}",
                     f"Active campus: {self.policy.name}  |  {self.policy.describe()}")

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_booking_panel(body)
        self._build_history_panel(body)

        self.refresh()

    # ---- left panel: resources + new booking form ----

    def _build_booking_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(panel, text="Available Resources", style="PanelHeader.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        columns = ("code", "name", "type")
        self.resource_tree = ttk.Treeview(panel, columns=columns, show="headings", height=8)
        for col, label, width in (("code", "Code", 80), ("name", "Name", 160), ("type", "Type", 100)):
            self.resource_tree.heading(col, text=label)
            self.resource_tree.column(col, width=width)
        self.resource_tree.pack(fill="x", pady=(0, 12))

        ttk.Label(panel, text="Book This Resource", style="SubHeader.TLabel") \
            .pack(anchor="w", pady=(4, 8))

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.pack(fill="x")

        ttk.Label(form, text="Date (YYYY-MM-DD)", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.date_var, width=16).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(form, text="Start Time (HH:MM)", style="Panel.TLabel").grid(row=1, column=0, sticky="w")
        self.time_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.time_var, width=16).grid(row=1, column=1, padx=6, pady=4)

        ttk.Label(form, text="Duration (minutes)", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.duration_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.duration_var, width=16).grid(row=2, column=1, padx=6, pady=4)

        self.booking_msg = ttk.Label(panel, text="", style="Error.TLabel", wraplength=340)
        self.booking_msg.pack(anchor="w", pady=(8, 4))

        ttk.Button(panel, text="Book Resource", style="Primary.TButton",
                   command=self.handle_book).pack(anchor="w")

    # ---- right panel: booking history ----

    def _build_history_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(panel, text="My Bookings", style="PanelHeader.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        columns = ("date", "time", "duration", "status")
        self.history_tree = ttk.Treeview(panel, columns=columns, show="headings", height=12)
        for col, label, width in (("date", "Date", 90), ("time", "Time", 70),
                                    ("duration", "Mins", 60), ("status", "Status", 80)):
            self.history_tree.heading(col, text=label)
            self.history_tree.column(col, width=width)
        self.history_tree.pack(fill="both", expand=True, pady=(0, 12))

        ttk.Button(panel, text="Cancel Selected Booking", style="Danger.TButton",
                   command=self.handle_cancel).pack(anchor="w")

    # ---- data + actions ----

    def refresh(self):
        for row in self.resource_tree.get_children():
            self.resource_tree.delete(row)
        self._resources_by_row = {}
        for res in self.lecturer.list_available_resources():
            row_id = self.resource_tree.insert(
                "", "end", values=(res.resource_code, res.name, res.resource_type)
            )
            self._resources_by_row[row_id] = res.resource_id

        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self._bookings_by_row = {}
        for b in self.lecturer.get_booking_history():
            row_id = self.history_tree.insert(
                "", "end", values=(b.booking_date, b.start_time, b.duration_minutes, b.status)
            )
            self._bookings_by_row[row_id] = b.booking_id

    def handle_book(self):
        selected = self.resource_tree.selection()
        if not selected:
            self.booking_msg.config(text="Select a resource from the list above first.")
            return
        resource_id = self._resources_by_row[selected[0]]

        date_str = self.date_var.get().strip()
        time_str = self.time_var.get().strip()
        duration_str = self.duration_var.get().strip()

        if not date_str or not time_str or not duration_str:
            self.booking_msg.config(text="Please fill in date, time, and duration.")
            return

        try:
            duration = int(duration_str)
        except ValueError:
            self.booking_msg.config(text="Duration must be a whole number of minutes.")
            return

        booking, err = self.lecturer.book_resource(resource_id, date_str, time_str, duration)
        if booking is None:
            self.booking_msg.config(text=err, style="Error.TLabel")
            return

        self.booking_msg.config(text="Booking confirmed!", style="Success.TLabel")
        self.date_var.set("")
        self.time_var.set("")
        self.duration_var.set("")
        self.refresh()

    def handle_cancel(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a booking to cancel.")
            return
        booking_id = self._bookings_by_row[selected[0]]
        ok, err = self.lecturer.cancel_booking(booking_id)
        if not ok:
            messagebox.showerror("Cannot cancel", err)
            return
        self.refresh()


# ---------------------------------------------------------------------
# Campus Administrator Dashboard
# ---------------------------------------------------------------------

class AdminDashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.admin = app.current_user
        policy = self.admin.get_active_campus_policy() if hasattr(self.admin, "get_active_campus_policy") else None
        campus_row = app.db.fetch_one(
            "SELECT name FROM campuses WHERE campus_id = ?", (self.admin.campus_id,)
        )
        campus_name = campus_row["name"] if campus_row else "Unknown"

        build_header(self, app, f"Admin: {self.admin.username}",
                     f"Managing resources for {campus_name}")

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=3)
        body.rowconfigure(1, weight=0)

        self._build_resource_panel(body)
        self._build_bookings_panel(body)
        self._build_password_reset_panel(body)

        self.refresh()

    def _build_resource_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(panel, text="Campus Resources", style="PanelHeader.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        columns = ("code", "name", "type")
        self.resource_tree = ttk.Treeview(panel, columns=columns, show="headings", height=10)
        for col, label, width in (("code", "Code", 80), ("name", "Name", 160), ("type", "Type", 100)):
            self.resource_tree.heading(col, text=label)
            self.resource_tree.column(col, width=width)
        self.resource_tree.pack(fill="x", pady=(0, 12))

        ttk.Label(panel, text="Add a Resource", style="SubHeader.TLabel") \
            .pack(anchor="w", pady=(4, 8))

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.pack(fill="x")

        ttk.Label(form, text="Code (e.g. LAB-02)", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.code_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.code_var, width=18).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(form, text="Name", style="Panel.TLabel").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=18).grid(row=1, column=1, padx=6, pady=4)

        ttk.Label(form, text="Type", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.type_var = tk.StringVar(value="lab")
        ttk.Combobox(form, textvariable=self.type_var, state="readonly", width=16,
                     values=["lab", "projector", "room", "equipment"]).grid(row=2, column=1, padx=6, pady=4)

        self.resource_msg = ttk.Label(panel, text="", style="Error.TLabel", wraplength=340)
        self.resource_msg.pack(anchor="w", pady=(8, 4))

        btn_row = ttk.Frame(panel, style="Panel.TFrame")
        btn_row.pack(anchor="w", pady=(0, 4))
        ttk.Button(btn_row, text="Add Resource", style="Primary.TButton",
                   command=self.handle_add_resource).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Remove Selected", style="Danger.TButton",
                   command=self.handle_remove_resource).pack(side="left")

    def _build_bookings_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(panel, text="Campus Bookings", style="PanelHeader.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        columns = ("date", "time", "duration", "status")
        self.bookings_tree = ttk.Treeview(panel, columns=columns, show="headings", height=12)
        for col, label, width in (("date", "Date", 90), ("time", "Time", 70),
                                    ("duration", "Mins", 60), ("status", "Status", 80)):
            self.bookings_tree.heading(col, text=label)
            self.bookings_tree.column(col, width=width)
        self.bookings_tree.pack(fill="both", expand=True, pady=(0, 12))

        ttk.Label(panel, text="Read-only view of every booking made against this campus's resources.",
                  style="Sub.TLabel", wraplength=300).pack(anchor="w")

    def _build_password_reset_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Label(panel, text="Reset a Lecturer's Password", style="PanelHeader.TLabel") \
            .grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        ttk.Label(panel, text="For lecturers on your campus who forgot their password. "
                              "They can log in with the new password right away.",
                  style="Sub.TLabel", wraplength=600) \
            .grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ttk.Label(panel, text="Lecturer", style="Panel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 6))
        self.reset_lecturer_var = tk.StringVar()
        self.reset_lecturer_combo = ttk.Combobox(panel, textvariable=self.reset_lecturer_var,
                                                  state="readonly", width=22)
        self.reset_lecturer_combo.grid(row=2, column=1, padx=(0, 16))

        ttk.Label(panel, text="New Password", style="Panel.TLabel").grid(row=2, column=2, sticky="w", padx=(0, 6))
        self.reset_password_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.reset_password_var, show="*", width=20) \
            .grid(row=2, column=3, padx=(0, 16))

        ttk.Button(panel, text="Reset Password", style="Primary.TButton",
                   command=self.handle_reset_password).grid(row=2, column=4)

        self.reset_msg = ttk.Label(panel, text="", style="Error.TLabel", wraplength=600)
        self.reset_msg.grid(row=3, column=0, columnspan=5, sticky="w", pady=(8, 0))

    def refresh(self):
        for row in self.resource_tree.get_children():
            self.resource_tree.delete(row)
        self._resources_by_row = {}
        for res in self.admin.list_campus_resources():
            row_id = self.resource_tree.insert(
                "", "end", values=(res.resource_code, res.name, res.resource_type)
            )
            self._resources_by_row[row_id] = res.resource_id

        for row in self.bookings_tree.get_children():
            self.bookings_tree.delete(row)
        for b in self.admin.list_campus_bookings():
            self.bookings_tree.insert(
                "", "end", values=(b.booking_date, b.start_time, b.duration_minutes, b.status)
            )

        # keep the lecturer picker current in case a new lecturer registered
        # since this dashboard was opened
        lecturers = self.admin.list_campus_lecturers()
        self._lecturers_by_username = {lec.username: lec.user_id for lec in lecturers}
        self.reset_lecturer_combo["values"] = list(self._lecturers_by_username.keys())
        if lecturers and self.reset_lecturer_var.get() not in self._lecturers_by_username:
            self.reset_lecturer_var.set(lecturers[0].username)

    def handle_reset_password(self):
        username = self.reset_lecturer_var.get()
        new_password = self.reset_password_var.get()

        if not username:
            self.reset_msg.config(text="Select a lecturer first.", style="Error.TLabel")
            return

        lecturer_id = self._lecturers_by_username.get(username)
        ok, err = self.admin.reset_lecturer_password(lecturer_id, new_password)
        if not ok:
            self.reset_msg.config(text=err, style="Error.TLabel")
            return

        self.reset_msg.config(text=f"Password reset for {username}.", style="Success.TLabel")
        self.reset_password_var.set("")

    def handle_add_resource(self):
        code = self.code_var.get().strip()
        name = self.name_var.get().strip()
        rtype = self.type_var.get()

        if not code or not name:
            self.resource_msg.config(text="Please fill in both code and name.")
            return

        res, err = self.admin.add_resource(code, name, rtype)
        if res is None:
            self.resource_msg.config(text=err, style="Error.TLabel")
            return

        self.resource_msg.config(text=f"Added {code}.", style="Success.TLabel")
        self.code_var.set("")
        self.name_var.set("")
        self.refresh()

    def handle_remove_resource(self):
        selected = self.resource_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a resource to remove.")
            return
        resource_id = self._resources_by_row[selected[0]]
        if not messagebox.askyesno("Confirm", "Remove this resource? Existing bookings are kept for history."):
            return
        self.admin.remove_resource(resource_id)
        self.refresh()


# ---------------------------------------------------------------------
# System Operator Dashboard
# ---------------------------------------------------------------------

class OperatorDashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.operator = app.current_user

        build_header(self, app, f"Operator: {self.operator.username}",
                     "System-wide view across all campuses")

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_comparison_panel(body)
        self._build_all_bookings_panel(body)

        self.refresh()

    def _build_comparison_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        header_row = ttk.Frame(panel, style="Panel.TFrame")
        header_row.pack(fill="x", pady=(0, 8))
        ttk.Label(header_row, text="Cross-Campus Comparison", style="PanelHeader.TLabel") \
            .pack(side="left")
        ttk.Button(header_row, text="Refresh", style="Secondary.TButton",
                   command=self.refresh).pack(side="right")

        columns = ("campus", "total", "avg_duration", "max_dur", "hours", "priority")
        self.compare_tree = ttk.Treeview(panel, columns=columns, show="headings", height=8)
        headings = {
            "campus": ("Campus", 100), "total": ("Bookings", 70),
            "avg_duration": ("Avg Mins", 70), "max_dur": ("Max Mins", 70),
            "hours": ("Hours", 90), "priority": ("Priority Rule", 130),
        }
        for col, (label, width) in headings.items():
            self.compare_tree.heading(col, text=label)
            self.compare_tree.column(col, width=width)
        self.compare_tree.pack(fill="x", pady=(0, 12))

        self.busiest_label = ttk.Label(panel, text="", style="Sub.TLabel", wraplength=340)
        self.busiest_label.pack(anchor="w")

    def _build_all_bookings_panel(self, body):
        panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(panel, text="All Bookings (Every Campus)", style="PanelHeader.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        columns = ("campus", "date", "time", "duration", "status")
        self.all_bookings_tree = ttk.Treeview(panel, columns=columns, show="headings", height=12)
        headings = {
            "campus": ("Campus", 90), "date": ("Date", 90), "time": ("Time", 60),
            "duration": ("Mins", 50), "status": ("Status", 80),
        }
        for col, (label, width) in headings.items():
            self.all_bookings_tree.heading(col, text=label)
            self.all_bookings_tree.column(col, width=width)
        self.all_bookings_tree.pack(fill="both", expand=True)

    def refresh(self):
        db = self.app.db

        for row in self.compare_tree.get_children():
            self.compare_tree.delete(row)
        comparison = reports.compare_all_campuses(db)
        for row in comparison:
            self.compare_tree.insert(
                "", "end",
                values=(
                    row["campus_name"],
                    row["total_bookings"],
                    row["avg_duration_minutes"] if row["avg_duration_minutes"] is not None else "-",
                    row["max_duration_minutes"],
                    f"{row['earliest_hour']}:00-{row['latest_hour']}:00",
                    row["priority_rule"],
                ),
            )

        busiest = reports.busiest_campus(db)
        if busiest and busiest["total_bookings"] > 0:
            self.busiest_label.config(
                text=f"Busiest campus: {busiest['campus_name']} "
                     f"({busiest['total_bookings']} active bookings)."
            )
        else:
            self.busiest_label.config(text="No bookings recorded yet across any campus.")

        for row in self.all_bookings_tree.get_children():
            self.all_bookings_tree.delete(row)
        # Join campus name in for readability rather than showing raw campus_id.
        campus_names = {c["campus_id"]: c["name"] for c in db.fetch_all("SELECT * FROM campuses")}
        for b in self.operator.list_all_bookings():
            self.all_bookings_tree.insert(
                "", "end",
                values=(
                    campus_names.get(b.campus_id, "?"),
                    b.booking_date, b.start_time, b.duration_minutes, b.status,
                ),
            )
