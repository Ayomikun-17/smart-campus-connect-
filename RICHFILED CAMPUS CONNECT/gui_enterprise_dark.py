"""
gui.py  --  Smart Campus Resource Booking System  (v3 "Aurora" UI)

Pure Tkinter / ttk -- no extra packages needed. models.py / reports.py are untouched.

What's new:
  * Light / Dark theme switch (top-right, rebuilds the current screen instantly)
  * Top navigation bar with underline tabs instead of a sidebar
  * Aurora login: gradient backdrop with a floating glass-style card
  * Booking page = resource TILES + a visual day TIMELINE:
        - pick a resource tile
        - pick a day from the 7-day strip
        - see taken slots (red), past time (hatched) and your selection (blue)
        - click the timeline to choose a start time, pick a duration, confirm
  * Live clash warning before you even press the button
  * Toasts, stat tiles, bar charts, zebra tables

The timeline reads existing bookings with one read-only query on the `bookings`
table. If your table/columns are named differently it quietly shows an empty
timeline and everything else still works (the real clash check stays in models.py).
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from datetime import datetime, date, timedelta

from models import User, Lecturer, CampusAdministrator, SystemOperator
import reports


# ---------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_LARGE_PATH = os.path.join(ASSETS_DIR, "richfield_logo.png")
LOGO_SMALL_PATH = os.path.join(ASSETS_DIR, "richfield_logo_small.png")
LOGIN_ART_PATH = os.path.join(ASSETS_DIR, "login_art.png")

THEMES = {
    "dark": dict(
        bg="#0a0f1c", grad="#16224a", surface="#121a2b", surface2="#1a2540", topbar="#0d1424",
        border="#243049", shadow="#060a14", text="#eaf0fb", muted="#8b9ab3", input="#0d1526",
        accent="#6c8cff", accent_dark="#4d6fea", accent2="#a77bff", accent_soft="#1d2a4d",
        success="#35c991", danger="#ff6685", warn="#f0b85b",
        blob1="#1b2c66", blob2="#33246b", on_accent="#ffffff",
    ),
    "light": dict(
        bg="#f3f5fb", grad="#dde5ff", surface="#ffffff", surface2="#eef1f9", topbar="#ffffff",
        border="#dde3f0", shadow="#d9deec", text="#141b2d", muted="#66728a", input="#f6f8fd",
        accent="#4f6ef7", accent_dark="#3a56d8", accent2="#8b5cf6", accent_soft="#e6ebff",
        success="#12a574", danger="#e5365a", warn="#c98a12",
        blob1="#c9d6ff", blob2="#e0d3ff", on_accent="#ffffff",
    ),
    # warm cream palette, used only by the login / register screens
    "cream": dict(
        bg="#fdf6ec", grad="#fbe9d2", surface="#fffdf9", surface2="#f8efe2", topbar="#fffdf9",
        border="#eadcc8", shadow="#ecdfcb", text="#2a1c10", muted="#8a7560", input="#fbf5ea",
        accent="#f26a1b", accent_dark="#d9560c", accent2="#ff9a3c", accent_soft="#ffe8d6",
        success="#12a574", danger="#e5365a", warn="#c98a12",
        blob1="#fbe3c4", blob2="#fdd9b0", on_accent="#ffffff",
    ),
}

C = {}   # active palette, filled by apply_theme()
F = {}   # fonts, filled by init_fonts()


def apply_theme(name):
    C.clear()
    C.update(THEMES[name])
    C["name"] = name


def mix(a, b, t):
    """Blend colour a towards b by t (0..1). Both '#rrggbb'."""
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def pal(key):
    """(foreground, tinted background) pair for stat tiles."""
    fg = C[key]
    return fg, mix(fg, C["surface"], 0.86)


def chart_colors():
    return [C["accent"], C["accent2"], C["success"], C["warn"], C["danger"]]


def init_fonts(root):
    families = set(tkfont.families(root))
    family = next(
        (f for f in ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue",
                     "Inter", "Roboto", "Ubuntu", "DejaVu Sans") if f in families),
        "TkDefaultFont",
    )

    def mk(size, weight="normal"):
        return tkfont.Font(root=root, family=family, size=size, weight=weight)

    F.update(
        family=family,
        tiny=mk(9, "bold"), small=mk(10), small_b=mk(10, "bold"),
        base=mk(11), bold=mk(11, "bold"), btn=mk(11, "bold"),
        h3=mk(13, "bold"), h2=mk(19, "bold"), h1=mk(24, "bold"),
        hero=mk(30, "bold"), icon=mk(16, "bold"),
    )


def configure_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=C["bg"])
    odd = mix(C["surface"], C["surface2"], 0.6)

    style.configure("Modern.Treeview", background=C["surface"], fieldbackground=C["surface"],
                    foreground=C["text"], font=F["base"], rowheight=38, borderwidth=0,
                    relief="flat")
    style.configure("Modern.Treeview.Heading", background=C["surface2"], foreground=C["muted"],
                    font=F["tiny"], relief="flat", borderwidth=0, padding=(10, 10))
    style.map("Modern.Treeview.Heading", background=[("active", C["surface2"])])
    style.map("Modern.Treeview", background=[("selected", C["accent_soft"])],
              foreground=[("selected", C["accent"])])
    style.layout("Modern.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    C["odd"] = odd

    thumb = mix(C["muted"], C["surface"], 0.55)
    style.configure("Modern.Vertical.TScrollbar", background=thumb, troughcolor=C["surface"],
                    bordercolor=C["surface"], lightcolor=thumb, darkcolor=thumb,
                    arrowcolor=C["surface"], relief="flat", gripcount=0, width=8)
    style.map("Modern.Vertical.TScrollbar", background=[("active", C["muted"])])

    style.configure("Modern.TCombobox", fieldbackground=C["input"], background=C["input"],
                    foreground=C["text"], bordercolor=C["border"], lightcolor=C["input"],
                    darkcolor=C["input"], arrowcolor=C["muted"], padding=9, relief="flat",
                    selectbackground=C["input"], selectforeground=C["text"])
    style.map("Modern.TCombobox", fieldbackground=[("readonly", C["input"])],
              bordercolor=[("focus", C["accent"])],
              selectbackground=[("readonly", C["input"])],
              selectforeground=[("readonly", C["text"])])
    root.option_add("*TCombobox*Listbox.font", F["base"])
    root.option_add("*TCombobox*Listbox.background", C["surface"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "white")


def load_logo(path):
    try:
        return tk.PhotoImage(file=path)
    except tk.TclError:
        return None


def short(text, n):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def pretty_rule(rule):
    return {
        "lecturer_first": "Lecturer first",
        "first_come_first_served": "First come",
        "none": "None",
    }.get(rule, str(rule).replace("_", " ").title())


def status_text(status):
    return "● Active" if status == "active" else "○ Cancelled"


def fmt_hours(minutes):
    return f"{minutes / 60:.1f} h"


def hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def to_minutes(text):
    h, m = str(text).split(":")[:2]
    return int(h) * 60 + int(m)


TYPE_ICONS = {"lab": "◈", "projector": "▶", "room": "▣", "equipment": "✦"}


# ---------------------------------------------------------------------
# Drawing helpers + reusable widgets
# ---------------------------------------------------------------------

def rounded_rect(c, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Card(tk.Canvas):
    """Rounded panel with a soft shadow. Put children in `.body`.
    fit=True  -> wraps its content;  fit=False -> fills the space it is given."""

    def __init__(self, parent, fit=False, pad=20, radius=18, **kw):
        super().__init__(parent, bg=C["bg"], highlightthickness=0, bd=0,
                         height=kw.pop("height", 60), **kw)
        self._pad, self._r, self._fit = pad, radius, fit
        self.body = tk.Frame(self, bg=C["surface"])
        self._win = self.create_window(pad, pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw)
        if fit:
            self.body.bind("<Configure>", self._fit_height)

    def _fit_height(self, _e=None):
        h = self.body.winfo_reqheight() + 2 * self._pad + 5
        if int(self.cget("height")) != h:
            self.configure(height=h)

    def _redraw(self, e):
        self.delete("bg")
        rounded_rect(self, 1, 4, e.width - 1, e.height - 1, self._r, fill=C["shadow"],
                     outline="", tags="bg")
        rounded_rect(self, 1, 1, e.width - 2, e.height - 4, self._r, fill=C["surface"],
                     outline=C["border"], tags="bg")
        self.tag_lower("bg")
        w = max(10, e.width - 2 * self._pad - 2)
        if self._fit:
            self.itemconfigure(self._win, width=w)
        else:
            self.itemconfigure(self._win, width=w, height=max(10, e.height - 2 * self._pad - 5))


class RoundButton(tk.Canvas):
    """Rounded button with hover. Stretches with fill='x'."""

    def __init__(self, parent, text, command=None, kind="primary", height=42, radius=12,
                 width=None, bg=None, font=None):
        self.text, self.command, self.kind, self.radius = text, command, kind, radius
        self._font = font or F["btn"]
        w = width or (self._font.measure(text) + 40)
        super().__init__(parent, width=w, height=height, highlightthickness=0, bd=0,
                         bg=bg or parent.cget("bg"), cursor="hand2")
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)

    def _colors(self):
        k = self.kind
        if k == "primary":
            return C["accent"], C["accent_dark"], C["on_accent"], None
        if k == "soft":
            return C["accent_soft"], mix(C["accent_soft"], C["accent"], 0.18), C["accent"], None
        if k == "ghost":
            return C["surface"], C["surface2"], C["text"], C["border"]
        if k == "danger":
            return C["danger"], mix(C["danger"], "#000000", 0.2), "#ffffff", None
        if k == "danger_soft":
            return (mix(C["danger"], C["surface"], 0.86), mix(C["danger"], C["surface"], 0.74),
                    C["danger"], None)
        if k == "chip":
            return C["surface2"], C["accent_soft"], C["text"], None
        return C["surface2"], C["accent_soft"], C["text"], None

    def _set_hover(self, state):
        self._hover = state
        self._draw()

    def _click(self, e):
        if self.command and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        base, hov, fg, border = self._colors()
        rounded_rect(self, 1, 1, w - 1, h - 1, self.radius, fill=hov if self._hover else base,
                     outline=border or "")
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=self._font)

    def set_text(self, text):
        self.text = text
        self._draw()


class Field(tk.Frame):
    """Label + flat input with focus ring. `.entry` is the real tk.Entry."""

    def __init__(self, parent, label, variable, password=False, bg=None, width=None):
        bg = bg or C["surface"]
        super().__init__(parent, bg=bg)
        tk.Label(self, text=label, bg=bg, fg=C["muted"], font=F["small_b"]).pack(anchor="w")
        self.box = tk.Frame(self, bg=C["input"], highlightthickness=1,
                            highlightbackground=C["border"])
        self.box.pack(fill="x", pady=(5, 0))
        self.entry = tk.Entry(self.box, textvariable=variable, relief="flat", bd=0,
                              bg=C["input"], fg=C["text"], insertbackground=C["text"],
                              font=F["base"], show="•" if password else "", width=width or 24)
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=10)
        if password:
            self.toggle = tk.Label(self.box, text="SHOW", bg=C["input"], fg=C["muted"],
                                   font=F["tiny"], cursor="hand2")
            self.toggle.pack(side="right", padx=(0, 12))
            self.toggle.bind("<Button-1>", self._toggle)
        self.entry.bind("<FocusIn>", lambda e: self.box.configure(highlightbackground=C["accent"]))
        self.entry.bind("<FocusOut>", lambda e: self.box.configure(highlightbackground=C["border"]))

    def _toggle(self, _e):
        hidden = self.entry.cget("show") != ""
        self.entry.configure(show="" if hidden else "•")
        self.toggle.configure(text="HIDE" if hidden else "SHOW")


class ComboField(tk.Frame):
    def __init__(self, parent, label, variable, values, state="readonly", bg=None):
        bg = bg or C["surface"]
        super().__init__(parent, bg=bg)
        tk.Label(self, text=label, bg=bg, fg=C["muted"], font=F["small_b"]).pack(anchor="w")
        self.combo = ttk.Combobox(self, textvariable=variable, values=values, state=state,
                                  style="Modern.TCombobox", font=F["base"])
        self.combo.pack(fill="x", pady=(5, 0))


class Segmented(tk.Frame):
    """Pill-style segmented control bound to a StringVar."""

    def __init__(self, parent, options, variable, command=None, padx=14):
        super().__init__(parent, bg=C["surface2"], padx=3, pady=3)
        self.variable, self.command = variable, command
        self.buttons = {}
        for opt in options:
            lbl = tk.Label(self, text=opt, font=F["small_b"], padx=padx, pady=6, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, o=opt: self._pick(o))
            self.buttons[opt] = lbl
        self._paint()

    def _pick(self, opt):
        self.variable.set(opt)
        self._paint()
        if self.command:
            self.command(opt)

    def _paint(self):
        for opt, lbl in self.buttons.items():
            on = opt == self.variable.get()
            lbl.configure(bg=C["accent"] if on else C["surface2"],
                          fg=C["on_accent"] if on else C["muted"])


class Pill(tk.Label):
    def __init__(self, parent, text, fg=None, bg=None):
        super().__init__(parent, text=text, fg=fg or C["accent"], bg=bg or C["accent_soft"],
                         font=F["small_b"], padx=10, pady=3)


class Avatar(tk.Canvas):
    COLORS = ["#4f6ef7", "#8b5cf6", "#12a36b", "#d98a0b", "#e0365a", "#0aa5c0"]

    def __init__(self, parent, name, size=36, bg=None):
        super().__init__(parent, width=size, height=size, bg=bg or parent.cget("bg"),
                         highlightthickness=0)
        color = self.COLORS[sum(ord(c) for c in name) % len(self.COLORS)]
        self.create_oval(1, 1, size - 1, size - 1, fill=color, outline="")
        self.create_text(size / 2, size / 2, text=(name[:1] or "?").upper(), fill="white",
                         font=F["bold"])


class LogoTile(tk.Canvas):
    """Rounded tile holding the logo, or an 'S' monogram if there is no logo file."""

    def __init__(self, parent, app, size=42, bg=None):
        super().__init__(parent, width=size, height=size, bg=bg or parent.cget("bg"),
                         highlightthickness=0)
        rounded_rect(self, 0, 0, size, size, 12, fill="white", outline=C["border"])
        img = app.logo_small
        if img is not None and img.width() > 0:
            factor = max(1, -(-max(img.width(), img.height()) // (size - 10)))
            self._img = img.subsample(factor, factor)
            self.create_image(size / 2, size / 2, image=self._img)
        else:
            self.create_text(size / 2, size / 2, text="S", fill="#4f6ef7",
                             font=tkfont.Font(family=F["family"], size=17, weight="bold"))


class ScrollFrame(tk.Frame):
    """Vertically scrollable frame. Put children in `.inner`."""

    def __init__(self, parent, bg=None):
        bg = bg or C["surface"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                style="Modern.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y", padx=(4, 0))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.bind_all("<MouseWheel>", self._wheel, add="+")
        self.bind_all("<Button-4>", lambda e: self._wheel(e, -1), add="+")
        self.bind_all("<Button-5>", lambda e: self._wheel(e, 1), add="+")

    def _wheel(self, e, step=None):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
            while w is not None and w is not self:
                w = w.master
            if w is None:
                return
            if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
                return
            if step is None:
                step = -1 if e.delta > 0 else 1
            self.canvas.yview_scroll(step, "units")
        except tk.TclError:
            pass


class ResourceGrid(tk.Frame):
    """Scrollable grid of selectable resource tiles."""

    def __init__(self, parent, on_select, cols=2):
        super().__init__(parent, bg=C["surface"])
        self.on_select, self.cols = on_select, cols
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.tiles = {}
        self.selected_id = None

    def set_items(self, items):
        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        self.tiles = {}
        for c in range(self.cols):
            inner.columnconfigure(c, weight=1, uniform="tile")
        if not items:
            tk.Label(inner, text="No resources match.", bg=C["surface"], fg=C["muted"],
                     font=F["base"]).grid(row=0, column=0, columnspan=self.cols, pady=40)
            return
        for i, r in enumerate(items):
            tile = self._make_tile(inner, r)
            tile.grid(row=i // self.cols, column=i % self.cols, sticky="nsew", padx=5, pady=5)
            self.tiles[r.resource_id] = tile
        self._paint()

    def _make_tile(self, parent, r):
        t = tk.Frame(parent, bg=C["surface2"], highlightthickness=2,
                     highlightbackground=C["border"], cursor="hand2")
        top = tk.Frame(t, bg=C["surface2"])
        top.pack(fill="x", padx=14, pady=(12, 0))
        tk.Label(top, text=TYPE_ICONS.get(r.resource_type, "◆"), bg=C["surface2"],
                 fg=C["accent"], font=F["icon"]).pack(side="left")
        tk.Label(top, text=r.resource_type.upper(), bg=C["surface2"], fg=C["muted"],
                 font=F["tiny"]).pack(side="right")
        tk.Label(t, text=r.resource_code, bg=C["surface2"], fg=C["text"], font=F["h3"],
                 anchor="w").pack(fill="x", padx=14, pady=(8, 0))
        tk.Label(t, text=short(r.name, 28), bg=C["surface2"], fg=C["muted"], font=F["small"],
                 anchor="w").pack(fill="x", padx=14, pady=(0, 12))
        self._bind_all(t, lambda e, res=r: self._pick(res))
        return t

    def _bind_all(self, widget, fn):
        widget.bind("<Button-1>", fn)
        for ch in widget.winfo_children():
            self._bind_all(ch, fn)

    def _pick(self, res):
        self.selected_id = res.resource_id
        self._paint()
        self.on_select(res)

    def _recolor(self, widget, bg):
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass
        for ch in widget.winfo_children():
            self._recolor(ch, bg)

    def _paint(self):
        for rid, tile in self.tiles.items():
            on = rid == self.selected_id
            bg = C["accent_soft"] if on else C["surface2"]
            self._recolor(tile, bg)
            tile.configure(highlightbackground=C["accent"] if on else C["border"])


class Timeline(tk.Canvas):
    """Day timeline: taken slots, past time, and the chosen slot. Click to pick a start."""

    def __init__(self, parent, start_hour, end_hour, on_pick):
        super().__init__(parent, bg=C["surface"], highlightthickness=0, height=86)
        self.s, self.e, self.on_pick = start_hour * 60, end_hour * 60, on_pick
        self.busy, self.past, self.sel, self.dur, self.hover = [], None, None, 60, None
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.configure(cursor="hand2")

    PAD = 6

    def set_state(self, busy, past, sel, dur):
        self.busy, self.past, self.sel, self.dur = busy, past, sel, dur
        self.draw()

    def _x(self, minute):
        w = max(1, self.winfo_width() - 2 * self.PAD)
        return self.PAD + (minute - self.s) / (self.e - self.s) * w

    def _minute_at(self, x):
        w = max(1, self.winfo_width() - 2 * self.PAD)
        m = self.s + (x - self.PAD) / w * (self.e - self.s)
        m = int(m // 30) * 30
        return max(self.s, min(self.e - 30, m))

    def _click(self, ev):
        self.on_pick(self._minute_at(ev.x))

    def _motion(self, ev):
        self._set_hover(self._minute_at(ev.x))

    def _set_hover(self, m):
        self.hover = m
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 20:
            return
        top, bot = 30, 66
        rounded_rect(self, self.PAD, top, w - self.PAD, bot, 8, fill=C["surface2"], outline="")
        # hour ticks + labels
        span_h = (self.e - self.s) // 60
        every = 1 if span_h <= 10 else 2
        for i, m in enumerate(range(self.s, self.e + 1, 60)):
            x = self._x(m)
            self.create_line(x, top, x, bot, fill=C["border"])
            if i % every == 0:
                self.create_text(min(max(x, 14), w - 14), 16, text=f"{m // 60:02d}",
                                 fill=C["muted"], font=F["tiny"])
        # past time
        if self.past is not None and self.past > self.s:
            x2 = self._x(min(self.past, self.e))
            self.create_rectangle(self.PAD, top, x2, bot, fill=C["border"], outline="",
                                  stipple="gray50")
        # busy blocks
        for bs, bd in self.busy:
            x1, x2 = self._x(max(bs, self.s)), self._x(min(bs + bd, self.e))
            if x2 > x1:
                rounded_rect(self, x1, top + 3, x2, bot - 3, 6, fill=C["danger"], outline="")
        # hover marker
        if self.hover is not None:
            hx = self._x(self.hover)
            self.create_line(hx, top - 4, hx, bot + 4, fill=C["muted"], dash=(3, 3))
            self.create_text(hx, bot + 14, text=hhmm(self.hover), fill=C["muted"], font=F["tiny"])
        # selection
        if self.sel is not None:
            x1, x2 = self._x(self.sel), self._x(min(self.sel + self.dur, self.e))
            clash = any(self.sel < bs + bd and bs < self.sel + self.dur for bs, bd in self.busy)
            col = C["warn"] if clash else C["accent"]
            rounded_rect(self, x1, top - 2, max(x2, x1 + 6), bot + 2, 8, fill=col,
                         outline=C["surface"], width=2)
            self.create_text((x1 + max(x2, x1 + 6)) / 2, (top + bot) / 2, text=hhmm(self.sel),
                             fill="white", font=F["tiny"])


class DataTable(tk.Frame):
    """Styled Treeview with zebra rows, scrollbar and an empty-state message."""

    def __init__(self, parent, columns, status_col=None, empty_text="Nothing here yet", height=10):
        super().__init__(parent, bg=C["surface"])
        self.status_col = status_col
        self.keys = {}
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show="headings",
                                 height=height, style="Modern.Treeview", selectmode="browse")
        for key, label, width in columns:
            self.tree.heading(key, text=label.upper(), anchor="w")
            self.tree.column(key, width=width, minwidth=40, anchor="w", stretch=True)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                           style="Modern.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.tree.tag_configure("even", background=C["surface"])
        self.tree.tag_configure("odd", background=C["odd"])
        self.tree.tag_configure("cancelled", foreground=C["muted"])
        self.empty = tk.Label(self, text=empty_text, bg=C["surface"], fg=C["muted"], font=F["base"])

    def set_rows(self, rows, keys=None):
        self.tree.delete(*self.tree.get_children())
        self.keys = {}
        for i, row in enumerate(rows):
            tags = ["odd" if i % 2 else "even"]
            if self.status_col is not None and "cancel" in str(row[self.status_col]).lower():
                tags.append("cancelled")
            iid = self.tree.insert("", "end", values=row, tags=tags)
            self.keys[iid] = keys[i] if keys else None
        if rows:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def selected_key(self):
        sel = self.tree.selection()
        return self.keys.get(sel[0]) if sel else None


class BarChart(tk.Canvas):
    """Horizontal bar chart with rounded bars."""

    ROW_H = 44

    def __init__(self, parent, empty_text="No data yet"):
        super().__init__(parent, bg=C["surface"], highlightthickness=0, height=self.ROW_H)
        self.data, self.empty_text = [], empty_text
        self.bind("<Configure>", lambda e: self.draw())

    def set_data(self, data):
        self.data = data
        self.configure(height=max(1, len(data)) * self.ROW_H + 8)
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if not self.data or all(v == 0 for _, v in self.data):
            self.create_text(w / 2, 40, text=self.empty_text, fill=C["muted"], font=F["base"])
            return
        label_w, right_pad = 120, 44
        mx = max(v for _, v in self.data) or 1
        colors = chart_colors()
        for i, (label, val) in enumerate(self.data):
            y = 6 + i * self.ROW_H
            self.create_text(0, y + 16, text=short(label, 16), anchor="w", fill=C["text"],
                             font=F["base"])
            x1, x2 = label_w, max(label_w + 40, w - right_pad)
            rounded_rect(self, x1, y + 8, x2, y + 24, 8, fill=C["surface2"], outline="")
            if val > 0:
                bw = max(16, (x2 - x1) * val / mx)
                rounded_rect(self, x1, y + 8, x1 + bw, y + 24, 8, fill=colors[i % len(colors)],
                             outline="")
            self.create_text(w, y + 16, text=str(val), anchor="e", fill=C["text"], font=F["bold"])


class StatCard(Card):
    def __init__(self, parent, label, value, icon, palette):
        super().__init__(parent, fit=True, pad=16)
        fg, tint = palette
        row = tk.Frame(self.body, bg=C["surface"])
        row.pack(fill="x")
        ic = tk.Canvas(row, width=44, height=44, bg=C["surface"], highlightthickness=0)
        rounded_rect(ic, 0, 0, 44, 44, 13, fill=tint, outline="")
        ic.create_text(22, 22, text=icon, fill=fg, font=F["h3"])
        ic.pack(side="left")
        txt = tk.Frame(row, bg=C["surface"])
        txt.pack(side="left", padx=(14, 0))
        tk.Label(txt, text=label.upper(), bg=C["surface"], fg=C["muted"], font=F["tiny"]).pack(anchor="w")
        tk.Label(txt, text=str(value), bg=C["surface"], fg=C["text"], font=F["h2"]).pack(anchor="w")


def card_title(parent, text, right=None):
    row = tk.Frame(parent, bg=C["surface"])
    row.pack(fill="x", pady=(0, 12))
    tk.Label(row, text=text, bg=C["surface"], fg=C["text"], font=F["h3"]).pack(side="left")
    if right is not None:
        right.pack(in_=row, side="right")
    return row


# ---------------------------------------------------------------------
# App shell
# ---------------------------------------------------------------------

class App(tk.Tk):
    """Root window: holds the DB, the logged-in user and the active screen."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_user = None
        self.theme = "dark"
        apply_theme(self.theme)

        self.title("Smart Campus Resource Booking System")
        self.minsize(1120, 720)

        init_fonts(self)
        configure_styles(self)

        self.logo_large = load_logo(LOGO_LARGE_PATH)
        self.logo_small = load_logo(LOGO_SMALL_PATH)
        # embedded copy first: works even if assets/login_art.png was never copied over
        try:
            self.login_art = tk.PhotoImage(data=LOGIN_ART_B64)
        except Exception:
            self.login_art = load_logo(LOGIN_ART_PATH)

        self.container = tk.Frame(self, bg=C["bg"])
        self.container.pack(fill="both", expand=True)
        self.active_frame = None
        self._last = None
        self._toast = None

        self._center()
        self.show_login()

    def _center(self):
        self.update_idletasks()
        w, h = 1360, 860
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ---- screen switching ----

    def _swap(self, frame_cls, *args):
        if self.active_frame is not None:
            self.active_frame.destroy()
        self._last = (frame_cls, args)
        # login / register always use the warm cream palette; dashboards use the chosen theme
        apply_theme("cream" if frame_cls in (LoginScreen, RegisterScreen) else self.theme)
        configure_styles(self)
        self.container.configure(bg=C["bg"])
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

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        apply_theme(self.theme)
        configure_styles(self)
        self.container.configure(bg=C["bg"])
        key = getattr(self.active_frame, "current", None)
        cls, args = self._last
        self._swap(cls, *args)
        if key and hasattr(self.active_frame, "show"):
            self.active_frame.show(key)

    # ---- toasts ----

    def toast(self, text, kind="success"):
        base = {"success": (C["success"], "✓"), "error": (C["danger"], "✕"),
                "warn": (C["warn"], "!"), "info": (C["accent"], "i")}
        fg, icon = base[kind]
        bg = mix(fg, C["surface"], 0.88)
        if self._toast is not None:
            self._toast.destroy()
        t = tk.Label(self, text=f"{icon}   {text}", bg=bg, fg=fg, font=F["bold"], padx=18,
                     pady=12, highlightthickness=1, highlightbackground=fg, wraplength=380,
                     justify="left")
        t.place(relx=1.0, x=-28, y=84, anchor="ne")
        t.lift()
        self._toast = t
        self.after(3800, lambda: self._kill_toast(t))

    def _kill_toast(self, t):
        try:
            t.destroy()
        except tk.TclError:
            pass
        if self._toast is t:
            self._toast = None


def theme_button(parent, app, bg):
    label = "☀  Light" if app.theme == "dark" else "☾  Dark"
    return RoundButton(parent, label, app.toggle_theme, kind="ghost", height=34, radius=17,
                       font=F["small_b"], bg=bg)


# ---------------------------------------------------------------------
# Login / Register (aurora backdrop + floating card)
# ---------------------------------------------------------------------

class Backdrop(tk.Canvas):
    """Gradient + soft blobs, with a centred floating card (`.form`) on top."""

    PAD = 32

    def __init__(self, parent, app, card_w=450):
        super().__init__(parent, bg=C["bg"], highlightthickness=0)
        self.app, self.card_w = app, card_w
        self.form = tk.Frame(self, bg=C["surface"])
        self.win = self.create_window(0, 0, window=self.form, anchor="center",
                                      width=card_w - 2 * self.PAD)
        self.logo = LogoTile(self, app, size=44, bg=C["bg"])
        self.create_window(40, 34, window=self.logo, anchor="nw")
        self.cream = C.get("name") == "cream"
        self.theme_win = None
        if not self.cream:
            self.theme_win = self.create_window(0, 36, window=theme_button(self, app, C["bg"]),
                                                anchor="ne")
        self.bind("<Configure>", lambda e: self.draw())
        self.form.bind("<Configure>", lambda e: self.draw())

    def draw_cream(self, w, h):
        """Cream layout: artwork bottom-left, headline above it, card on the right."""
        art = getattr(self.app, "login_art", None)
        if art is not None:
            self.create_image(0, h, image=art, anchor="sw", tags="deco")
        self.create_text(98, 46, text="Smart Campus", anchor="w", fill=C["text"], font=F["h3"], tags="deco")
        self.create_text(98, 66, text="Resource Booking", anchor="w", fill=C["muted"], font=F["small"], tags="deco")
        self.create_text(48, 130, anchor="nw", fill=C["text"], font=F["hero"], tags="deco",
                         text="Book campus resources\nin seconds.")
        self.create_text(48, 226, anchor="nw", fill=C["muted"], font=F["base"], width=460, tags="deco",
                         text="Labs, rooms and projectors across every campus, "
                              "with each campus's own rules built in.")
        cx = max(w - self.card_w / 2 - 90, w / 2)
        cy = h / 2
        ch = self.form.winfo_reqheight() + 2 * self.PAD
        x1, x2 = cx - self.card_w / 2, cx + self.card_w / 2
        y1, y2 = cy - ch / 2, cy + ch / 2
        rounded_rect(self, x1, y1 + 8, x2, y2 + 8, 26, fill=C["shadow"], outline="", tags="deco")
        rounded_rect(self, x1, y1, x2, y2, 26, fill=C["surface"], outline=C["border"], tags="deco")
        self.create_text(cx, y2 + 34, text="Richfield Graduate Institute of Technology",
                         fill=C["muted"], font=F["small"], tags="deco")
        self.coords(self.win, cx, cy)
        self.tag_lower("deco")

    def draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        self.delete("deco")
        if self.cream:
            self.draw_cream(w, h)
            return
        n = 48
        for i in range(n):
            self.create_rectangle(0, h * i / n, w, h * (i + 1) / n + 1,
                                  fill=mix(C["bg"], C["grad"], i / (n - 1)), outline="", tags="deco")
        self.create_oval(-160, h - 320, 360, h + 180, fill=C["blob1"], outline="", tags="deco")
        self.create_oval(w - 420, -200, w + 140, 340, fill=C["blob2"], outline="", tags="deco")
        self.create_oval(w - 220, h - 240, w - 60, h - 80, fill=C["accent"], outline="", tags="deco")
        self.create_oval(w - 120, h - 150, w - 60, h - 90, fill=C["accent2"], outline="", tags="deco")

        self.create_text(98, 46, text="Smart Campus", anchor="w", fill=C["text"], font=F["h3"], tags="deco")
        self.create_text(98, 66, text="Resource Booking", anchor="w", fill=C["muted"], font=F["small"], tags="deco")

        cx, cy = w / 2, h / 2
        ch = self.form.winfo_reqheight() + 2 * self.PAD
        x1, x2 = cx - self.card_w / 2, cx + self.card_w / 2
        y1, y2 = cy - ch / 2, cy + ch / 2
        rounded_rect(self, x1, y1 + 8, x2, y2 + 8, 26, fill=C["shadow"], outline="", tags="deco")
        rounded_rect(self, x1, y1, x2, y2, 26, fill=C["surface"], outline=C["border"], tags="deco")
        self.create_text(cx, h - 30, text="Richfield Graduate Institute of Technology",
                         fill=C["muted"], font=F["small"], tags="deco")
        self.coords(self.win, cx, cy)
        self.coords(self.theme_win, w - 40, 36)
        self.tag_lower("deco")


class AuthScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.backdrop = Backdrop(self, app)
        self.backdrop.pack(fill="both", expand=True)
        self.form = self.backdrop.form

    def heading(self, title, subtitle):
        tk.Label(self.form, text=title, bg=C["surface"], fg=C["text"], font=F["h1"]).pack(anchor="w")
        tk.Label(self.form, text=subtitle, bg=C["surface"], fg=C["muted"],
                 font=F["base"]).pack(anchor="w", pady=(4, 22))

    def error_label(self):
        lbl = tk.Label(self.form, text="", bg=C["surface"], fg=C["danger"], font=F["small_b"],
                       wraplength=340, justify="left", anchor="w")
        lbl.pack(fill="x", pady=(10, 6))
        return lbl


class LoginScreen(AuthScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.heading("Welcome back", "Sign in to manage your campus bookings.")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        user_f = Field(self.form, "USERNAME", self.username_var, width=34)
        user_f.pack(fill="x", pady=(0, 14))
        pass_f = Field(self.form, "PASSWORD", self.password_var, password=True, width=34)
        pass_f.pack(fill="x")

        self.error = self.error_label()
        RoundButton(self.form, "Sign in", self.handle_login, height=46).pack(fill="x")

        sep = tk.Frame(self.form, bg=C["surface"])
        sep.pack(fill="x", pady=14)
        tk.Frame(sep, bg=C["border"], height=1).pack(side="left", fill="x", expand=True, pady=8)
        tk.Label(sep, text="  NEW HERE?  ", bg=C["surface"], fg=C["muted"], font=F["tiny"]).pack(side="left")
        tk.Frame(sep, bg=C["border"], height=1).pack(side="left", fill="x", expand=True, pady=8)

        RoundButton(self.form, "Create an account", app.show_register, kind="ghost",
                    height=46).pack(fill="x")
        tk.Label(self.form, text="Forgot your password? Ask your Campus Administrator to reset it.",
                 bg=C["surface"], fg=C["muted"], font=F["small"], wraplength=340,
                 justify="left").pack(anchor="w", pady=(16, 0))

        for entry in (user_f.entry, pass_f.entry):
            entry.bind("<Return>", lambda e: self.handle_login())
        user_f.entry.focus_set()

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            self.error.config(text="Please enter both username and password.")
            return
        user, err = User.login(self.app.db, username, password)
        if user is None:
            self.error.config(text=err)
            return
        self.app.show_dashboard(user)


class RegisterScreen(AuthScreen):
    ROLE_LABELS = {"Lecturer": "lecturer", "Campus Admin": "admin", "System Operator": "operator"}

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.heading("Create your account", "Pick your role and campus to get started.")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.role_var = tk.StringVar(value="Lecturer")
        self.campus_var = tk.StringVar()

        user_f = Field(self.form, "USERNAME", self.username_var, width=34)
        user_f.pack(fill="x", pady=(0, 14))
        pass_f = Field(self.form, "PASSWORD", self.password_var, password=True, width=34)
        pass_f.pack(fill="x", pady=(0, 14))

        tk.Label(self.form, text="ROLE", bg=C["surface"], fg=C["muted"], font=F["small_b"]).pack(anchor="w")
        Segmented(self.form, list(self.ROLE_LABELS.keys()), self.role_var,
                  command=lambda _o: self._refresh_campus_visibility()).pack(anchor="w", pady=(5, 14))

        self._campus_lookup = {}
        self.campus_field = ComboField(self.form, "CAMPUS", self.campus_var, [])
        self.campus_field.pack(fill="x")
        self._load_campuses()

        self.error = self.error_label()
        RoundButton(self.form, "Create account", self.handle_register, height=46).pack(fill="x")
        RoundButton(self.form, "Back to sign in", app.show_login, kind="ghost",
                    height=46).pack(fill="x", pady=(10, 0))

        for entry in (user_f.entry, pass_f.entry):
            entry.bind("<Return>", lambda e: self.handle_register())
        user_f.entry.focus_set()

    def _load_campuses(self):
        rows = self.app.db.fetch_all("SELECT campus_id, name FROM campuses ORDER BY name")
        self._campus_lookup = {r["name"]: r["campus_id"] for r in rows}
        self.campus_field.combo["values"] = list(self._campus_lookup.keys())
        if rows:
            self.campus_var.set(rows[0]["name"])

    def _refresh_campus_visibility(self):
        if self.role_var.get() == "System Operator":
            self.campus_field.pack_forget()
        else:
            self.campus_field.pack(fill="x", before=self.error)

    def handle_register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        role = self.ROLE_LABELS.get(self.role_var.get())

        if not username or not password:
            self.error.config(text="Please enter both username and password.")
            return

        campus_id = None
        if role != "operator":
            campus_id = self._campus_lookup.get(self.campus_var.get())
            if campus_id is None:
                self.error.config(text="Please select a campus.")
                return

        user, err = User.register(self.app.db, username, password, role, campus_id)
        if user is None:
            self.error.config(text=err)
            return

        self.app.show_login()
        self.app.toast("Account created. You can sign in now.")


# ---------------------------------------------------------------------
# Dashboard shell: top bar + header + swappable page
# ---------------------------------------------------------------------

class TabItem(tk.Frame):
    def __init__(self, parent, icon, text, command):
        bg = C["topbar"]
        super().__init__(parent, bg=bg, cursor="hand2")
        self.active = False
        self.bar = tk.Frame(self, bg=bg, height=3)
        self.bar.pack(side="bottom", fill="x", padx=10)
        self.lbl = tk.Label(self, text=f"{icon}  {text}", bg=bg, fg=C["muted"], font=F["bold"],
                            padx=14, pady=16, cursor="hand2")
        self.lbl.pack(side="top")
        for w in (self, self.lbl, self.bar):
            w.bind("<Enter>", lambda e: self._paint(True))
            w.bind("<Leave>", lambda e: self._paint(False))
            w.bind("<Button-1>", lambda e: command())

    def set_active(self, on):
        self.active = on
        self._paint(False)

    def _paint(self, hover):
        self.lbl.configure(fg=C["text"] if (self.active or hover) else C["muted"])
        self.bar.configure(bg=C["accent"] if self.active else C["topbar"])


class Shell(tk.Frame):
    """Base for the three role dashboards. Subclasses define NAV, TITLES and
    a `view_<key>(parent)` method per nav entry."""

    NAV = []         # [(key, icon, label)]
    TITLES = {}      # key -> (title, subtitle)
    ROLE_LABEL = ""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app, self.db, self.user = app, app.db, app.current_user
        self.current = None
        self.page = None
        self.nav_items = {}

        row = None
        if self.user.campus_id is not None:
            row = self.db.fetch_one("SELECT name FROM campuses WHERE campus_id = ?",
                                    (self.user.campus_id,))
        self.campus_name = row["name"] if row else "All campuses"

        self._build_topbar()
        self._build_main()
        self.show(self.NAV[0][0])

    def _build_topbar(self):
        top = tk.Frame(self, bg=C["topbar"])
        top.pack(fill="x")
        inner = tk.Frame(top, bg=C["topbar"])
        inner.pack(fill="x", padx=28)

        brand = tk.Frame(inner, bg=C["topbar"])
        brand.pack(side="left", pady=10)
        LogoTile(brand, self.app, size=38, bg=C["topbar"]).pack(side="left")
        tk.Label(brand, text="Smart Campus", bg=C["topbar"], fg=C["text"],
                 font=F["h3"]).pack(side="left", padx=(10, 28))

        for key, icon, label in self.NAV:
            item = TabItem(inner, icon, label, lambda k=key: self.show(k))
            item.pack(side="left", padx=2)
            self.nav_items[key] = item

        right = tk.Frame(inner, bg=C["topbar"])
        right.pack(side="right", pady=9)
        theme_button(right, self.app, C["topbar"]).pack(side="left", padx=(0, 14))
        Avatar(right, self.user.username, size=34, bg=C["topbar"]).pack(side="left")
        who = tk.Frame(right, bg=C["topbar"])
        who.pack(side="left", padx=(8, 14))
        tk.Label(who, text=short(self.user.username, 18), bg=C["topbar"], fg=C["text"],
                 font=F["small_b"]).pack(anchor="w")
        tk.Label(who, text=f"{self.ROLE_LABEL} · {self.campus_name}", bg=C["topbar"],
                 fg=C["muted"], font=F["small"]).pack(anchor="w")
        RoundButton(right, "Log out", self.app.logout, kind="ghost", height=34, radius=17,
                    font=F["small_b"], bg=C["topbar"]).pack(side="left")
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

    def _build_main(self):
        head = tk.Frame(self, bg=C["bg"])
        head.pack(fill="x", padx=32, pady=(24, 16))
        left = tk.Frame(head, bg=C["bg"])
        left.pack(side="left")
        hour = datetime.now().hour
        greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        tk.Label(left, text=f"{greet}, {short(self.user.username, 20)}", bg=C["bg"],
                 fg=C["accent"], font=F["small_b"]).pack(anchor="w")
        self.title_lbl = tk.Label(left, bg=C["bg"], fg=C["text"], font=F["h1"])
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = tk.Label(left, bg=C["bg"], fg=C["muted"], font=F["base"])
        self.sub_lbl.pack(anchor="w", pady=(2, 0))
        tk.Label(head, text=datetime.now().strftime("%a, %d %b %Y"), bg=C["surface"],
                 fg=C["muted"], font=F["small_b"], padx=14, pady=8, highlightthickness=1,
                 highlightbackground=C["border"]).pack(side="right")

        self.content = tk.Frame(self, bg=C["bg"])
        self.content.pack(fill="both", expand=True, padx=32, pady=(0, 24))

    def show(self, key):
        self.current = key
        for k, item in self.nav_items.items():
            item.set_active(k == key)
        title, subtitle = self.TITLES[key]
        self.title_lbl.config(text=title)
        self.sub_lbl.config(text=subtitle)
        if self.page is not None:
            self.page.destroy()
        self.page = tk.Frame(self.content, bg=C["bg"])
        self.page.pack(fill="both", expand=True)
        getattr(self, "view_" + key)(self.page)

    def reload(self):
        self.show(self.current)

    def resource_names(self):
        rows = self.db.fetch_all("SELECT resource_id, resource_code, name FROM resources")
        return {r["resource_id"]: f'{r["resource_code"]} · {r["name"]}' for r in rows}

    def usernames(self):
        rows = self.db.fetch_all("SELECT user_id, username FROM users")
        return {r["user_id"]: r["username"] for r in rows}

    def stat_row(self, parent, specs, row=0):
        """specs: [(label, value, icon, palette)] -> one StatCard per column."""
        cards = []
        for i, (label, value, icon, palette) in enumerate(specs):
            parent.columnconfigure(i, weight=1, uniform="stat")
            card = StatCard(parent, label, value, icon, palette)
            card.grid(row=row, column=i, sticky="ew",
                      padx=(0 if i == 0 else 8, 0 if i == len(specs) - 1 else 8), pady=(0, 16))
            cards.append(card)
        return cards


# ---------------------------------------------------------------------
# Lecturer
# ---------------------------------------------------------------------

class LecturerDashboard(Shell):
    ROLE_LABEL = "Lecturer"
    NAV = [("book", "＋", "New booking"), ("history", "☰", "My bookings")]
    TITLES = {
        "book": ("Book a resource", "Pick a tile, pick a day, click a free slot."),
        "history": ("My bookings", "Your upcoming and past reservations."),
    }

    def __init__(self, parent, app):
        self.policy = app.current_user.get_active_campus_policy()
        super().__init__(parent, app)

    # ---- page: new booking ----

    def view_book(self, p):
        p.columnconfigure(0, weight=11, uniform="cols")
        p.columnconfigure(1, weight=9, uniform="cols")
        p.rowconfigure(0, weight=1)

        self._resources = self.user.list_available_resources()
        self.sel_res = None
        self.sel_date = date.today()
        self.start_min = None
        self._busy = []
        self.duration = min(60, self.policy.max_duration_minutes)

        # ---- left: resource tiles ----
        left = Card(p)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 6))
        self.count_pill = Pill(left.body, "")
        card_title(left.body, "Available resources", right=self.count_pill)

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        Field(left.body, "SEARCH", self.filter_var, width=20).pack(fill="x", pady=(0, 10))

        types = sorted({r.resource_type.title() for r in self._resources})
        self.type_var = tk.StringVar(value="All")
        Segmented(left.body, ["All"] + types, self.type_var, padx=12,
                  command=lambda _o: self._apply_filter()).pack(anchor="w", pady=(0, 10))

        self.grid_view = ResourceGrid(left.body, self._on_pick, cols=2)
        self.grid_view.pack(fill="both", expand=True)

        # ---- right: slot picker ----
        right = Card(p)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 6))
        b = right.body
        tk.Label(b, text="Choose your slot", bg=C["surface"], fg=C["text"],
                 font=F["h3"]).pack(anchor="w")

        pick = tk.Frame(b, bg=C["accent_soft"])
        pick.pack(fill="x", pady=(10, 12))
        tk.Label(pick, text="SELECTED RESOURCE", bg=C["accent_soft"], fg=C["accent"],
                 font=F["tiny"]).pack(anchor="w", padx=14, pady=(8, 0))
        self.pick_lbl = tk.Label(pick, text="Choose a tile on the left", bg=C["accent_soft"],
                                 fg=C["text"], font=F["bold"], anchor="w")
        self.pick_lbl.pack(fill="x", padx=14, pady=(2, 8))

        tk.Label(b, text="DAY", bg=C["surface"], fg=C["muted"], font=F["small_b"]).pack(anchor="w")
        self.date_row = tk.Frame(b, bg=C["surface"])
        self.date_row.pack(fill="x", pady=(5, 12))
        self._build_dates()

        tk.Label(b, text="AVAILABILITY  ·  click to set a start time", bg=C["surface"],
                 fg=C["muted"], font=F["small_b"]).pack(anchor="w")
        self.timeline = Timeline(b, self.policy.earliest_hour, self.policy.latest_hour,
                                 on_pick=self._pick_start)
        self.timeline.pack(fill="x", pady=(4, 0))
        legend = tk.Frame(b, bg=C["surface"])
        legend.pack(anchor="w", pady=(0, 10))
        for col, text in ((C["danger"], "Taken"), (C["accent"], "Your slot"),
                          (C["border"], "Past")):
            tk.Label(legend, text="●", bg=C["surface"], fg=col, font=F["small"]).pack(side="left")
            tk.Label(legend, text=text + "   ", bg=C["surface"], fg=C["muted"],
                     font=F["small"]).pack(side="left")

        tk.Label(b, text="DURATION (MINUTES)", bg=C["surface"], fg=C["muted"],
                 font=F["small_b"]).pack(anchor="w")
        self.duration_var = tk.StringVar(value=str(self.duration))
        Segmented(b, self._duration_options(), self.duration_var, padx=12,
                  command=self._set_duration).pack(anchor="w", pady=(5, 12))

        box = tk.Frame(b, bg=C["surface2"], highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="x", pady=(0, 12))
        self.summary_lbl = tk.Label(box, text="", bg=C["surface2"], fg=C["text"], font=F["bold"],
                                    anchor="w", justify="left", wraplength=380)
        self.summary_lbl.pack(fill="x", padx=12, pady=(10, 2))
        self.rules_lbl = tk.Label(
            box, bg=C["surface2"], fg=C["muted"], font=F["small"], anchor="w", justify="left",
            wraplength=380,
            text=f"{self.policy.name} rules · max {self.policy.max_duration_minutes} min · "
                 f"open {self.policy.earliest_hour:02d}:00–{self.policy.latest_hour:02d}:00 · "
                 f"priority: {pretty_rule(self.policy.priority_rule)}")
        self.rules_lbl.pack(fill="x", padx=12, pady=(0, 10))

        RoundButton(b, "Confirm booking", self.handle_book, height=46).pack(fill="x")

        self._apply_filter()
        self._refresh_timeline()

    def _duration_options(self):
        mx = self.policy.max_duration_minutes
        vals = list(range(30, mx + 1, 30))
        if mx not in vals:
            vals.append(mx)
        return [str(v) for v in vals] or [str(mx)]

    def _apply_filter(self):
        q = self.filter_var.get().strip().lower()
        t = self.type_var.get().lower()
        shown = [r for r in self._resources
                 if (t == "all" or r.resource_type.lower() == t)
                 and q in f"{r.resource_code} {r.name} {r.resource_type}".lower()]
        self.grid_view.set_items(shown)
        self.count_pill.config(text=f"{len(shown)} available")

    def _on_pick(self, res):
        self.sel_res = res
        self.pick_lbl.config(text=f"{res.resource_code} · {res.name}")
        self._refresh_timeline()

    def _build_dates(self):
        for w in self.date_row.winfo_children():
            w.destroy()
        for i in range(7):
            d = date.today() + timedelta(days=i)
            on = d == self.sel_date
            lbl = tk.Label(self.date_row, text=f"{d.strftime('%a').upper()}\n{d.day}",
                           font=F["small_b"], padx=10, pady=7, cursor="hand2",
                           bg=C["accent"] if on else C["surface2"],
                           fg=C["on_accent"] if on else C["text"])
            lbl.grid(row=0, column=i, padx=(0 if i == 0 else 3, 0), sticky="ew")
            self.date_row.columnconfigure(i, weight=1, uniform="day")
            lbl.bind("<Button-1>", lambda e, dd=d: self._set_date(dd))

    def _set_date(self, d):
        self.sel_date = d
        self._build_dates()
        self._refresh_timeline()

    def _set_duration(self, opt):
        self.duration = int(opt)
        self._refresh_timeline()

    def _pick_start(self, minute):
        if self.sel_res is None:
            self.app.toast("Pick a resource tile first.", "warn")
            return
        self.start_min = minute
        self._refresh_timeline()

    def _load_busy(self):
        if self.sel_res is None:
            return []
        try:
            rows = self.db.fetch_all(
                "SELECT start_time, duration_minutes FROM bookings "
                "WHERE resource_id = ? AND booking_date = ? AND status = 'active'",
                (self.sel_res.resource_id, self.sel_date.isoformat()))
            return [(to_minutes(r["start_time"]), int(r["duration_minutes"])) for r in rows]
        except Exception:
            return []

    def _refresh_timeline(self):
        self._busy = self._load_busy()
        now = datetime.now()
        past = now.hour * 60 + now.minute if self.sel_date == date.today() else None
        self.timeline.set_state(self._busy, past, self.start_min, self.duration)
        self._update_summary()

    def _clash(self):
        if self.start_min is None:
            return False
        s, e = self.start_min, self.start_min + self.duration
        return any(s < bs + bd and bs < e for bs, bd in self._busy)

    def _update_summary(self):
        if self.sel_res is None:
            self.summary_lbl.config(text="Pick a resource to begin.", fg=C["muted"])
            return
        if self.start_min is None:
            self.summary_lbl.config(text=f"{self.sel_res.resource_code} · "
                                         f"{self.sel_date.strftime('%a %d %b')} — choose a start time",
                                    fg=C["muted"])
            return
        end = self.start_min + self.duration
        text = (f"{self.sel_res.resource_code} · {self.sel_date.strftime('%a %d %b')} · "
                f"{hhmm(self.start_min)}–{hhmm(end)}  ({self.duration} min)")
        fg = C["text"]
        if self._clash():
            text += "\n⚠ This overlaps an existing booking."
            fg = C["warn"]
        elif end > self.policy.latest_hour * 60:
            text += f"\n⚠ Ends after closing time ({self.policy.latest_hour:02d}:00)."
            fg = C["warn"]
        self.summary_lbl.config(text=text, fg=fg)

    def handle_book(self):
        res = self.sel_res
        if res is None:
            self.app.toast("Select a resource tile first.", "warn")
            return
        if self.start_min is None:
            self.app.toast("Click the timeline to choose a start time.", "warn")
            return
        time_str = hhmm(self.start_min)
        iso = self.sel_date.isoformat()
        booking, err = self.user.book_resource(res.resource_id, iso, time_str, self.duration)
        if booking is None:
            self.app.toast(err, "error")
            self._refresh_timeline()
            return
        self.app.toast(f"Booked {res.resource_code} on {iso} at {time_str}.")
        self.show("history")

    # ---- page: my bookings ----

    def view_history(self, p):
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)

        self._history = self.user.get_booking_history()
        active = [b for b in self._history if b.status == "active"]
        stats = tk.Frame(p, bg=C["bg"])
        stats.grid(row=0, column=0, sticky="ew")
        self.stat_row(stats, [
            ("Active bookings", len(active), "◉", pal("accent")),
            ("Hours booked", fmt_hours(sum(b.duration_minutes for b in active)), "◷", pal("success")),
            ("Cancelled", len(self._history) - len(active), "✕", pal("danger")),
        ])

        card = Card(p)
        card.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self.filter_mode = tk.StringVar(value="All")
        seg = Segmented(card.body, ["All", "Upcoming", "Past", "Cancelled"], self.filter_mode,
                        command=lambda _o: self._fill_history())
        card_title(card.body, "Booking history", right=seg)

        self.hist_table = DataTable(card.body, [
            ("resource", "Resource", 230), ("date", "Date", 110), ("time", "Start", 80),
            ("duration", "Mins", 70), ("status", "Status", 110)],
            status_col=4, empty_text="No bookings here yet.")
        self.hist_table.pack(fill="both", expand=True)

        foot = tk.Frame(card.body, bg=C["surface"])
        foot.pack(fill="x", pady=(14, 0))
        RoundButton(foot, "Cancel selected booking", self.handle_cancel, kind="danger_soft",
                    height=40).pack(side="left")
        self._fill_history()

    def _fill_history(self):
        names = self.resource_names()
        mode = self.filter_mode.get()
        today = date.today().isoformat()

        def keep(b):
            if mode == "All":
                return True
            if mode == "Cancelled":
                return b.status != "active"
            if mode == "Upcoming":
                return b.status == "active" and str(b.booking_date) >= today
            return b.status == "active" and str(b.booking_date) < today   # Past

        rows = [b for b in self._history if keep(b)]
        self.hist_table.set_rows(
            [(names.get(b.resource_id, "?"), b.booking_date, b.start_time, b.duration_minutes,
              status_text(b.status)) for b in rows],
            keys=[b.booking_id for b in rows])

    def handle_cancel(self):
        booking_id = self.hist_table.selected_key()
        if booking_id is None:
            self.app.toast("Select a booking to cancel.", "warn")
            return
        if not messagebox.askyesno("Cancel booking", "Cancel this booking?"):
            return
        ok, err = self.user.cancel_booking(booking_id)
        if not ok:
            self.app.toast(err, "error")
            return
        self.app.toast("Booking cancelled.", "info")
        self.reload()


# ---------------------------------------------------------------------
# Campus Administrator
# ---------------------------------------------------------------------

class AdminDashboard(Shell):
    ROLE_LABEL = "Admin"
    NAV = [("overview", "▣", "Overview"), ("resources", "⚙", "Resources"),
           ("lecturers", "☺", "Lecturers")]
    TITLES = {
        "overview": ("Campus overview", "How your campus is using its resources."),
        "resources": ("Resources", "Add or remove what lecturers can book."),
        "lecturers": ("Lecturers", "Reset passwords for lecturers on your campus."),
    }

    def view_overview(self, p):
        p.columnconfigure(0, weight=2, uniform="cols")
        p.columnconfigure(1, weight=3, uniform="cols")
        p.rowconfigure(1, weight=1)

        summary = reports.campus_summary(self.db, self.user.campus_id)
        resources = self.user.list_campus_resources()
        lecturers = self.user.list_campus_lecturers()
        bookings = self.user.list_campus_bookings()

        stats = tk.Frame(p, bg=C["bg"])
        stats.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.stat_row(stats, [
            ("Resources", len(resources), "▣", pal("accent")),
            ("Active bookings", summary["total_bookings"], "◉", pal("success")),
            ("Lecturers", len(lecturers), "☺", pal("accent2")),
            ("Avg duration", f'{summary["average_duration_minutes"]:g} min', "◷", pal("warn")),
        ])

        left = Card(p)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 6))
        card_title(left.body, "Most used resources")
        chart = BarChart(left.body, empty_text="No bookings yet")
        chart.pack(fill="x")
        chart.set_data([(f'{r["resource_code"]}', r["booking_count"])
                        for r in summary["most_used_resources"]])

        right = Card(p)
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 6))
        card_title(right.body, "Recent bookings")
        names, users = self.resource_names(), self.usernames()
        table = DataTable(right.body, [
            ("res", "Resource", 160), ("who", "Lecturer", 150), ("date", "Date", 95),
            ("time", "Start", 65), ("status", "Status", 95)],
            status_col=4, empty_text="No bookings on this campus yet.")
        table.pack(fill="both", expand=True)
        table.set_rows([(names.get(b.resource_id, "?"), short(users.get(b.lecturer_id, "?"), 22),
                         b.booking_date, b.start_time, status_text(b.status))
                        for b in bookings[:12]])

    # ---- resources ----

    def view_resources(self, p):
        p.columnconfigure(0, weight=3, uniform="cols")
        p.columnconfigure(1, weight=2, uniform="cols")
        p.rowconfigure(0, weight=1)

        left = Card(p)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 6))
        resources = self.user.list_campus_resources()
        card_title(left.body, "Campus resources", right=Pill(left.body, f"{len(resources)} active"))
        self.res_table = DataTable(left.body, [("code", "Code", 90), ("name", "Name", 200),
                                               ("type", "Type", 110)],
                                   empty_text="No resources yet. Add your first one →")
        self.res_table.pack(fill="both", expand=True)
        self.res_table.set_rows([(r.resource_code, r.name, r.resource_type.title()) for r in resources],
                                keys=[r.resource_id for r in resources])
        RoundButton(left.body, "Remove selected", self.handle_remove_resource,
                    kind="danger_soft", height=40).pack(anchor="w", pady=(14, 0))

        right = Card(p, fit=True)
        right.grid(row=0, column=1, sticky="new", padx=(10, 0), pady=(0, 6))
        b = right.body
        tk.Label(b, text="Add a resource", bg=C["surface"], fg=C["text"],
                 font=F["h3"]).pack(anchor="w", pady=(0, 14))
        self.code_var, self.name_var = tk.StringVar(), tk.StringVar()
        self.type_var = tk.StringVar(value="lab")
        Field(b, "CODE  (e.g. LAB-02)", self.code_var, width=20).pack(fill="x", pady=(0, 12))
        Field(b, "NAME", self.name_var, width=20).pack(fill="x", pady=(0, 12))
        ComboField(b, "TYPE", self.type_var, ["lab", "projector", "room", "equipment"]).pack(fill="x", pady=(0, 18))
        RoundButton(b, "Add resource", self.handle_add_resource, height=46).pack(fill="x")

    def handle_add_resource(self):
        code, name = self.code_var.get().strip(), self.name_var.get().strip()
        if not code or not name:
            self.app.toast("Please fill in both code and name.", "warn")
            return
        res, err = self.user.add_resource(code, name, self.type_var.get())
        if res is None:
            self.app.toast(err, "error")
            return
        self.app.toast(f"Added {code}.")
        self.reload()

    def handle_remove_resource(self):
        resource_id = self.res_table.selected_key()
        if resource_id is None:
            self.app.toast("Select a resource to remove.", "warn")
            return
        if not messagebox.askyesno("Remove resource",
                                   "Remove this resource? Existing bookings are kept for history."):
            return
        self.user.remove_resource(resource_id)
        self.app.toast("Resource removed.", "info")
        self.reload()

    # ---- lecturers / password reset ----

    def view_lecturers(self, p):
        p.columnconfigure(0, weight=3, uniform="cols")
        p.columnconfigure(1, weight=2, uniform="cols")
        p.rowconfigure(0, weight=1)

        lecturers = self.user.list_campus_lecturers()
        left = Card(p)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 6))
        card_title(left.body, "Lecturers on your campus", right=Pill(left.body, f"{len(lecturers)} total"))
        self.lec_table = DataTable(left.body, [("name", "Username", 320), ("id", "ID", 60)],
                                   empty_text="No lecturers have registered here yet.")
        self.lec_table.pack(fill="both", expand=True)
        self.lec_table.set_rows([(l.username, l.user_id) for l in lecturers],
                                keys=[(l.user_id, l.username) for l in lecturers])
        self.lec_table.tree.bind("<<TreeviewSelect>>", lambda e: self._on_pick_lecturer())

        right = Card(p, fit=True)
        right.grid(row=0, column=1, sticky="new", padx=(10, 0), pady=(0, 6))
        b = right.body
        tk.Label(b, text="Reset password", bg=C["surface"], fg=C["text"], font=F["h3"]).pack(anchor="w")
        tk.Label(b, text="Select a lecturer on the left, then set a new password. "
                         "They can sign in with it straight away.",
                 bg=C["surface"], fg=C["muted"], font=F["small"], wraplength=300,
                 justify="left").pack(anchor="w", pady=(4, 14))
        box = tk.Frame(b, bg=C["accent_soft"])
        box.pack(fill="x", pady=(0, 14))
        tk.Label(box, text="LECTURER", bg=C["accent_soft"], fg=C["accent"],
                 font=F["tiny"]).pack(anchor="w", padx=14, pady=(10, 0))
        self.target_lbl = tk.Label(box, text="None selected", bg=C["accent_soft"], fg=C["text"],
                                   font=F["bold"], anchor="w")
        self.target_lbl.pack(fill="x", padx=14, pady=(2, 10))
        self.new_pw_var = tk.StringVar()
        Field(b, "NEW PASSWORD", self.new_pw_var, password=True, width=20).pack(fill="x", pady=(0, 16))
        RoundButton(b, "Reset password", self.handle_reset_password, height=46).pack(fill="x")

    def _on_pick_lecturer(self):
        key = self.lec_table.selected_key()
        self.target_lbl.config(text=short(key[1], 30) if key else "None selected")

    def handle_reset_password(self):
        key = self.lec_table.selected_key()
        if key is None:
            self.app.toast("Select a lecturer first.", "warn")
            return
        ok, err = self.user.reset_lecturer_password(key[0], self.new_pw_var.get())
        if not ok:
            self.app.toast(err, "error")
            return
        self.new_pw_var.set("")
        self.app.toast(f"Password reset for {key[1]}.")


# ---------------------------------------------------------------------
# System Operator
# ---------------------------------------------------------------------

class OperatorDashboard(Shell):
    ROLE_LABEL = "Operator"
    NAV = [("overview", "▣", "Overview"), ("bookings", "☰", "All bookings")]
    TITLES = {
        "overview": ("System overview", "Every campus side by side."),
        "bookings": ("All bookings", "Every reservation across every campus."),
    }

    def view_overview(self, p):
        p.columnconfigure(0, weight=2, uniform="cols")
        p.columnconfigure(1, weight=3, uniform="cols")
        p.rowconfigure(1, weight=1)

        rows = reports.compare_all_campuses(self.db)
        total = sum(r["total_bookings"] for r in rows)
        weighted = sum(r["total_bookings"] * (r["avg_duration_minutes"] or 0) for r in rows)
        avg = round(weighted / total, 1) if total else 0
        busiest = reports.busiest_campus(self.db)
        busiest_name = busiest["campus_name"] if busiest and busiest["total_bookings"] > 0 else "—"

        stats = tk.Frame(p, bg=C["bg"])
        stats.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.stat_row(stats, [
            ("Campuses", len(rows), "▣", pal("accent")),
            ("Active bookings", total, "◉", pal("success")),
            ("Busiest campus", busiest_name, "★", pal("warn")),
            ("Avg duration", f"{avg:g} min", "◷", pal("accent2")),
        ])

        left = Card(p)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 6))
        card_title(left.body, "Bookings by campus")
        chart = BarChart(left.body, empty_text="No bookings recorded yet")
        chart.pack(fill="x")
        chart.set_data([(r["campus_name"], r["total_bookings"]) for r in rows])

        right = Card(p)
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 6))
        card_title(right.body, "Campus rules compared",
                   right=RoundButton(right.body, "Refresh", self.reload, kind="soft", height=32,
                                     radius=10, font=F["small_b"]))
        table = DataTable(right.body, [
            ("campus", "Campus", 100), ("total", "Active", 60), ("avg", "Avg min", 70),
            ("max", "Max min", 70), ("hours", "Hours", 100), ("rule", "Priority", 100)])
        table.pack(fill="both", expand=True)
        table.set_rows([(
            r["campus_name"], r["total_bookings"],
            r["avg_duration_minutes"] if r["avg_duration_minutes"] is not None else "–",
            r["max_duration_minutes"], f'{r["earliest_hour"]:02d}:00–{r["latest_hour"]:02d}:00',
            pretty_rule(r["priority_rule"])) for r in rows])

    def view_bookings(self, p):
        p.columnconfigure(0, weight=1)
        p.rowconfigure(0, weight=1)
        card = Card(p)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        campuses = {c["campus_id"]: c["name"] for c in self.db.fetch_all("SELECT * FROM campuses")}
        self._all = self.user.list_all_bookings()
        self.campus_filter = tk.StringVar(value="All campuses")
        combo = ttk.Combobox(card.body, textvariable=self.campus_filter, state="readonly",
                             style="Modern.TCombobox", font=F["base"], width=18,
                             values=["All campuses"] + sorted(campuses.values()))
        combo.bind("<<ComboboxSelected>>", lambda e: self._fill_all(campuses))
        card_title(card.body, f"{len(self._all)} bookings", right=combo)

        self.all_table = DataTable(card.body, [
            ("campus", "Campus", 110), ("res", "Resource", 190), ("who", "Lecturer", 190),
            ("date", "Date", 100), ("time", "Start", 70), ("dur", "Mins", 60),
            ("status", "Status", 100)], status_col=6, empty_text="No bookings recorded yet.")
        self.all_table.pack(fill="both", expand=True)
        self._fill_all(campuses)

    def _fill_all(self, campuses):
        names, users = self.resource_names(), self.usernames()
        pick = self.campus_filter.get()
        rows = [b for b in self._all if pick == "All campuses" or campuses.get(b.campus_id) == pick]
        self.all_table.set_rows([(
            campuses.get(b.campus_id, "?"), names.get(b.resource_id, "?"),
            short(users.get(b.lecturer_id, "?"), 24), b.booking_date, b.start_time,
            b.duration_minutes, status_text(b.status)) for b in rows])


# ---------------------------------------------------------------------
# Embedded login artwork (so no extra file is needed)
# ---------------------------------------------------------------------

LOGIN_ART_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAArwAAAINCAMAAADr8lyhAAABIFBMVEX+9+3+9u399u399uz99ez79ez99un99ej89uf89en69un89uX89eT89e"
    "H89tj98+T98+D98t/989v98t398d/98dz98Nn979f89Of79N/589/88dz879n58N398dP979P87tP68NP87dL67NL87s377M7868357c387cn9"
    "7cD47cX96cz96cf96cb96cP96b7957/56cj56L785sH85bz85bn847r45Lz85bP847P84bL84qr84Kn836n83Kf83aD83Jj45LH3363436H425"
    "782Z382ZL81ZD62Zj61ZD315Xv1pj71YP70n/70X37znz7zW75z3n0z3z7yWv7w2X6wVf6vFD4wl7xwmb6tUn6qT7yrUX6li7ukizwcRnoPAkW"
    "JHVVAAEAAElEQVR42uydCUNaWba2qxLjEEbBCAiiCAo4gwMoToDzEBVNQmJZ/f//xfe8a58DJibVqe7bt6q/6+6uSsqoMeZlnbXXeodfQv0TjU"
    "ZHR+PJN69fvx50ZyiQDAaDoWg6k8lMpkO5Vms+9CaZHBwZGBgZCoRSwUAoFs4V5+dDExPByERyMDg5OTkxMRGJ8GGBwPDg4Ovh5HBAnyOU5IyM"
    "uM87MsJ/DAeGh4f5TAP8fgMjAd5r2J3A4KvXL+fl/NPzy1fgHQW8kTcDbwa/Bm9c4E2/i8bmqwIvIB0cGhJ4A8Oh6LjAC2YBbyQy4U4y6YN3cD"
    "CZBJepiRfwvpz/HHijVnhHxyIjAtBT8MbiMYE3Fg+Fs+HgAKXXIM0JDEYi6UxutpgKhYKh4PBIcCIYpOyODAZCPfBORIZT1OPkyAt4X85/DLxx"
    "6m48HQ2qag4/BW8sNp7IjI+nJ1KpUGBoeDjI+3JoMQDv2GRmOqFPMDExPDQMZHkPuoWvwDuRz0++gPfl/KfAa3CMp9PpeCoUjQSH6Gxf98ELfA"
    "XeCNCkiEbj6fFwOJaOA8hIdCw9npmcTIVSqcDEJIgVZJ+ANzIZGZ58Ae/L+U+DN60Ti8ejoUgkOeSDNx6Lp1L6xcnJ5GAgl5+cyCRy2WwiPRbh"
    "jI2NvRubnEiB5kBy4jvgfam8L+c/Bl56AYE3JuDS2o5nx2Px0Wgk0gPv2JjeYXQsM5+fHArmchPxXLZQKGQzYxMTapNH49HBULhYK6ZeD9L7Br"
    "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"
)