"""
Run this inside your contextOS folder to create the full GUI dashboard.
Usage:  python build_dashboard.py
"""
import os

BASE  = os.path.dirname(os.path.abspath(__file__))
files = {}

# ── ui/dashboard.py ───────────────────────────────────────────────────────────
files["ui/dashboard.py"] = '''"""
ui/dashboard.py  -  Full 5-tab GUI dashboard for ContextOS.
Built with tkinter (built into Python - no install needed).

Tabs:
  1. Home     - today stats + context trail
  2. Insights - all active insights with action buttons
  3. Apps     - which apps are being watched
  4. Memory   - searchable context history
  5. Settings - all toggles and preferences
"""
import tkinter as tk
from tkinter import ttk, font as tkfont
import threading
import time
import os
import sys
import logging

logger = logging.getLogger(__name__)

# ── Colour palette (works in both light mode usage) ───────────────────────────
C = {
    "bg":         "#ffffff",
    "bg2":        "#f8f8f6",
    "bg3":        "#f0efeb",
    "border":     "#e5e3dc",
    "text":       "#1a1a1a",
    "text2":      "#555550",
    "text3":      "#999890",
    "teal":       "#1D9E75",
    "teal_light": "#e1f5ee",
    "blue":       "#185FA5",
    "blue_light": "#e6f1fb",
    "amber":      "#BA7517",
    "amber_light":"#faeeda",
    "red":        "#A32D2D",
    "red_light":  "#fcebeb",
    "purple":     "#534AB7",
    "purple_light":"#eeedfe",
    "sidebar":    "#f4f3ef",
    "sidebar_sel":"#ffffff",
    "accent":     "#1D9E75",
}

FONT_FAMILY = "Segoe UI"

def F(size=11, weight="normal"):
    return (FONT_FAMILY, size, weight)


class Dashboard:
    """
    Main dashboard window. Call .show() to open it.
    Pass config, db, engine so it can read live data.
    """

    def __init__(self, config, db, engine=None):
        self.config  = config
        self.db      = db
        self.engine  = engine
        self.root    = None
        self._active_tab = "home"
        self._frames = {}

    def show(self):
        """Open the dashboard window. Blocks until closed."""
        self.root = tk.Tk()
        self.root.title("ContextOS — Dashboard")
        self.root.geometry("820x580")
        self.root.minsize(700, 480)
        self.root.configure(bg=C["bg"])

        # Window icon colour (green dot in taskbar)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build_titlebar()
        self._build_body()
        self._switch_tab("home")
        self._start_auto_refresh()
        self.root.mainloop()

    # ── Title bar ─────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=C["bg2"], height=42)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Left: logo
        left = tk.Frame(bar, bg=C["bg2"])
        left.pack(side="left", padx=14, pady=8)

        dot = tk.Canvas(left, width=10, height=10, bg=C["bg2"],
                        highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=C["teal"], outline="")
        dot.pack(side="left", padx=(0, 6))

        tk.Label(left, text="ContextOS", font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(side="left")

        # Right: status pill
        right = tk.Frame(bar, bg=C["bg2"])
        right.pack(side="right", padx=14)

        self._status_lbl = tk.Label(
            right, text="● Watching",
            font=F(9), bg=C["teal_light"], fg=C["teal"],
            padx=8, pady=2
        )
        self._status_lbl.pack()

        # Separator
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

    # ── Body = sidebar + content ───────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        # Thin separator
        tk.Frame(body, bg=C["border"], width=1).pack(side="left", fill="y")

        # Content area
        self._content = tk.Frame(body, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=C["sidebar"], width=52)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tabs = [
            ("home",     "⌂",  "Home"),
            ("insights", "⚡", "Insights"),
            ("apps",     "◈",  "Apps"),
            ("memory",   "◎",  "Memory"),
            ("settings", "⚙",  "Settings"),
        ]

        self._sb_btns = {}
        for i, (key, icon, label) in enumerate(tabs):
            btn = tk.Button(
                sb, text=icon, font=("Segoe UI Emoji", 16),
                bg=C["sidebar"], fg=C["text2"],
                relief="flat", bd=0, cursor="hand2",
                width=3, height=2,
                command=lambda k=key: self._switch_tab(k),
                activebackground=C["sidebar_sel"],
                activeforeground=C["teal"],
            )
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>", lambda e, b=btn: self._sb_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._sb_hover(b, False, k))
            self._sb_btns[key] = btn
            if i == 4:   # push settings to bottom
                tk.Frame(sb, bg=C["sidebar"]).pack(expand=True)

    def _sb_hover(self, btn, on, key=None):
        if key and key == self._active_tab:
            return
        btn.configure(bg=C["sidebar_sel"] if on else C["sidebar"],
                      fg=C["teal"]        if on else C["text2"])

    def _switch_tab(self, key):
        self._active_tab = key
        # Update sidebar highlight
        for k, btn in self._sb_btns.items():
            if k == key:
                btn.configure(bg=C["sidebar_sel"], fg=C["teal"])
            else:
                btn.configure(bg=C["sidebar"], fg=C["text2"])

        # Destroy old content, build new
        for w in self._content.winfo_children():
            w.destroy()

        builders = {
            "home":     self._tab_home,
            "insights": self._tab_insights,
            "apps":     self._tab_apps,
            "memory":   self._tab_memory,
            "settings": self._tab_settings,
        }
        builders[key](self._content)

    # =========================================================================
    # TAB 1 — HOME
    # =========================================================================

    def _tab_home(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=C["bg"])

        frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        pad = {"padx": 20, "pady": 0}

        # ── Section: stats ────────────────────────────────────────────────────
        self._section_label(frame, "Today's overview", pady_top=18)

        stats_frame = tk.Frame(frame, bg=C["bg"])
        stats_frame.pack(fill="x", **pad, pady=(0, 16))

        stats = self._get_stats()
        stat_defs = [
            ("Insights fired",   str(stats["insights_today"]),  "today",           C["purple"]),
            ("Conflicts caught", str(stats["conflicts_caught"]), "saved from mistakes", C["amber"]),
            ("Tasks auto-done",  str(stats["tasks_auto_done"]),  "in Notion/Jira",  C["teal"]),
            ("Focus time",       f"{stats['focus_minutes']}m",   "deep work today", C["blue"]),
        ]

        for i, (label, value, sub, color) in enumerate(stat_defs):
            card = tk.Frame(stats_frame, bg=C["bg2"],
                            relief="flat", bd=0)
            card.grid(row=0, column=i, padx=(0,10) if i<3 else 0,
                      sticky="ew", ipady=10, ipadx=10)
            stats_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=label, font=F(9),
                     bg=C["bg2"], fg=C["text2"]).pack(anchor="w", padx=10, pady=(10,0))
            tk.Label(card, text=value, font=F(22, "bold"),
                     bg=C["bg2"], fg=color).pack(anchor="w", padx=10)
            tk.Label(card, text=sub, font=F(8),
                     bg=C["bg2"], fg=C["text3"]).pack(anchor="w", padx=10, pady=(0,8))

        # ── Section: current focus ────────────────────────────────────────────
        self._section_label(frame, "Current focus")

        focus_frame = tk.Frame(frame, bg=C["bg2"], relief="flat")
        focus_frame.pack(fill="x", **pad, pady=(0,16))

        focus_topic = self._get_focus_topic()
        tk.Label(focus_frame, text=focus_topic, font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(anchor="w", padx=14, pady=(12,4))

        # App chips
        chips_frame = tk.Frame(focus_frame, bg=C["bg2"])
        chips_frame.pack(anchor="w", padx=14, pady=(0,12))

        recent_apps = self._get_recent_apps()
        for app in recent_apps[:6]:
            chip = tk.Label(chips_frame, text=app, font=F(9),
                            bg=C["bg"], fg=C["text2"],
                            relief="flat", padx=8, pady=2)
            chip.pack(side="left", padx=(0,5))

        # ── Section: context trail ────────────────────────────────────────────
        self._section_label(frame, "Context trail")

        trail_frame = tk.Frame(frame, bg=C["bg"])
        trail_frame.pack(fill="x", **pad, pady=(0,20))

        events = self.db.get_recent_events(limit=8, hours=8)
        if not events:
            tk.Label(trail_frame, text="No activity yet — start using your apps!",
                     font=F(10), bg=C["bg"], fg=C["text3"]).pack(anchor="w", pady=8)
        else:
            for ev in events:
                self._trail_row(trail_frame, ev)

    def _trail_row(self, parent, event):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=2)

        # Time dot
        dot = tk.Canvas(row, width=8, height=8, bg=C["bg"], highlightthickness=0)
        dot.create_oval(1,1,7,7, fill=C["border"], outline=C["text3"])
        dot.pack(side="left", pady=6, padx=(4,8))

        # Vertical line (simulated with a thin frame)
        tk.Frame(row, bg=C["border"], width=1, height=20).place(x=7, y=0)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True)

        ts = event.get("timestamp","")[:19].replace("T"," ")
        tk.Label(info, text=ts[11:], font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        title = event.get("window_title","")[:70]
        app   = event.get("app_name","")
        tk.Label(info, text=f"[{app}]  {title}", font=F(10),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")

    # =========================================================================
    # TAB 2 — INSIGHTS
    # =========================================================================

    def _tab_insights(self, parent):
        # Header row
        hdr = tk.Frame(parent, bg=C["bg"])
        hdr.pack(fill="x", padx=20, pady=(18,0))

        self._section_label(hdr, "All active insights", inline=True)

        tk.Button(hdr, text="Refresh", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, cursor="hand2",
                  command=lambda: self._switch_tab("insights")
                  ).pack(side="right")

        # Scrollable list
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=C["bg"])
        frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        insights = self.db.get_active_insights(limit=20)
        if not insights:
            tk.Label(frame, text="No active insights right now.\n\nContextOS is watching your apps.",
                     font=F(11), bg=C["bg"], fg=C["text3"],
                     justify="center").pack(pady=60)
            return

        for ins in insights:
            self._insight_card(frame, ins)

    def _insight_card(self, parent, ins):
        type_colors = {
            "conflict":    (C["amber"],  C["amber_light"],  "⚠  Conflict"),
            "answer":      (C["blue"],   C["blue_light"],   "◎  Answer found"),
            "auto_update": (C["teal"],   C["teal_light"],   "✓  Auto-updated"),
            "meeting_prep":(C["purple"], C["purple_light"], "◷  Meeting prep"),
        }
        itype = ins.get("insight_type","conflict")
        color, bg_light, badge_text = type_colors.get(
            itype, (C["text2"], C["bg2"], itype))

        card = tk.Frame(parent, bg=C["bg"],
                        highlightbackground=C["border"],
                        highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0,10))

        # Left colour stripe
        stripe = tk.Frame(card, bg=color, width=4)
        stripe.pack(side="left", fill="y")

        body = tk.Frame(card, bg=C["bg"])
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        # Top row: badge + timestamp
        top = tk.Frame(body, bg=C["bg"])
        top.pack(fill="x")

        tk.Label(top, text=badge_text, font=F(9),
                 bg=bg_light, fg=color, padx=6, pady=1
                 ).pack(side="left")

        ts = ins.get("timestamp","")[:19].replace("T"," ")[11:]
        tk.Label(top, text=ts, font=F(8),
                 bg=C["bg"], fg=C["text3"]).pack(side="right")

        # Title
        tk.Label(body, text=ins.get("title",""), font=F(11,"bold"),
                 bg=C["bg"], fg=C["text"],
                 wraplength=560, justify="left",
                 anchor="w").pack(fill="x", pady=(6,2))

        # Detail
        detail = ins.get("detail","")
        if detail:
            tk.Label(body, text=detail, font=F(10),
                     bg=C["bg"], fg=C["text2"],
                     wraplength=560, justify="left",
                     anchor="w").pack(fill="x")

        # Source apps
        sources = ins.get("source_apps","")
        if sources:
            tk.Label(body, text=f"Sources: {sources}", font=F(8),
                     bg=C["bg"], fg=C["text3"]).pack(anchor="w", pady=(4,0))

        # Action buttons
        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(anchor="w", pady=(8,0))

        iid = ins.get("id")
        tk.Button(btn_row, text="Dismiss", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._dismiss(i)
                  ).pack(side="left", padx=(0,6))

        tk.Button(btn_row, text="Mark acted on", font=F(9),
                  bg=C["teal_light"], fg=C["teal"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._act_on(i)
                  ).pack(side="left")

    def _dismiss(self, insight_id):
        if insight_id:
            self.db.dismiss_insight(insight_id)
        self._switch_tab("insights")

    def _act_on(self, insight_id):
        if insight_id:
            with self.db._connect() as conn:
                conn.execute(
                    "UPDATE insights SET acted_on=1, dismissed=1 WHERE id=?",
                    (insight_id,))
        self._switch_tab("insights")

    # =========================================================================
    # TAB 3 — APPS
    # =========================================================================

    def _tab_apps(self, parent):
        self._section_label(parent, "Watched apps", pady_top=18, padx=20)

        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=C["bg"])
        frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        grid = tk.Frame(frame, bg=C["bg"])
        grid.pack(fill="x", padx=20, pady=(0,10))

        # Get recent activity per app
        events      = self.db.get_recent_events(limit=200, hours=24)
        app_counts  = {}
        app_last    = {}
        for ev in events:
            app = ev["app_name"]
            app_counts[app] = app_counts.get(app, 0) + 1
            if app not in app_last:
                app_last[app] = ev["timestamp"]

        watched = self.config.get("watched_apps", [])

        # Show all known apps with activity first
        all_apps = list(app_counts.keys())
        # Add watched apps not yet seen
        for w in watched:
            if not any(w.lower() in a.lower() for a in all_apps):
                all_apps.append(w)

        for i, app in enumerate(all_apps[:12]):
            col = i % 3
            row = i // 3
            count = app_counts.get(app, 0)
            last  = app_last.get(app, "")[:19].replace("T"," ")[11:] if app in app_last else "No activity"
            active = count > 0

            card = tk.Frame(grid, bg=C["bg2"], relief="flat")
            card.grid(row=row, column=col,
                      padx=(0,10) if col<2 else 0,
                      pady=(0,10), sticky="ew", ipadx=10, ipady=8)
            grid.columnconfigure(col, weight=1)

            # Status dot
            top = tk.Frame(card, bg=C["bg2"])
            top.pack(fill="x", padx=10, pady=(10,0))

            dot = tk.Canvas(top, width=8, height=8, bg=C["bg2"],
                            highlightthickness=0)
            dot.create_oval(1,1,7,7,
                fill=C["teal"] if active else C["border"], outline="")
            dot.pack(side="left", pady=3, padx=(0,6))

            tk.Label(top, text=app, font=F(11,"bold"),
                     bg=C["bg2"], fg=C["text"]).pack(side="left")

            tk.Label(card, text=f"{count} events today",
                     font=F(9), bg=C["bg2"], fg=C["text2"]
                     ).pack(anchor="w", padx=10)
            tk.Label(card, text=f"Last: {last}",
                     font=F(8), bg=C["bg2"], fg=C["text3"]
                     ).pack(anchor="w", padx=10, pady=(0,8))

    # =========================================================================
    # TAB 4 — MEMORY
    # =========================================================================

    def _tab_memory(self, parent):
        # Search bar
        search_frame = tk.Frame(parent, bg=C["bg"])
        search_frame.pack(fill="x", padx=20, pady=(18,10))

        self._section_label(search_frame, "Context memory", inline=True)

        search_box = tk.Frame(search_frame, bg=C["bg"])
        search_box.pack(side="right")

        self._search_var = tk.StringVar()
        entry = tk.Entry(search_box, textvariable=self._search_var,
                         font=F(10), width=22,
                         bg=C["bg2"], fg=C["text"],
                         relief="flat", bd=1,
                         highlightbackground=C["border"],
                         highlightthickness=1)
        entry.pack(side="left", ipady=5, padx=(0,6))
        entry.insert(0, "Search your work context...")
        entry.bind("<FocusIn>",  lambda e: entry.delete(0,"end")
                   if entry.get()=="Search your work context..." else None)

        tk.Button(search_box, text="Search", font=F(9),
                  bg=C["teal"], fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2",
                  command=lambda: self._do_search(results_frame,
                                                  self._search_var.get())
                  ).pack(side="left")

        entry.bind("<Return>",
            lambda e: self._do_search(results_frame, self._search_var.get()))

        # Scrollable results
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        results_frame = tk.Frame(canvas, bg=C["bg"])
        results_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=results_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Load initial results
        self._do_search(results_frame, "")

    def _do_search(self, frame, query):
        for w in frame.winfo_children():
            w.destroy()

        events = self.db.get_recent_events(limit=100, hours=24*7)
        q      = query.strip().lower()
        if q and q != "search your work context...":
            events = [e for e in events
                      if q in (e.get("window_title","") or "").lower()
                      or q in (e.get("app_name","") or "").lower()
                      or q in (e.get("keywords","") or "").lower()]

        if not events:
            tk.Label(frame, text="No results found.",
                     font=F(10), bg=C["bg"], fg=C["text3"]
                     ).pack(pady=40)
            return

        # Group by app
        by_app: dict = {}
        for ev in events:
            app = ev["app_name"]
            by_app.setdefault(app, []).append(ev)

        for app, evs in list(by_app.items())[:8]:
            group = tk.Frame(frame, bg=C["bg"])
            group.pack(fill="x", padx=20, pady=(0,12))

            tk.Label(group, text=app, font=F(10,"bold"),
                     bg=C["bg"], fg=C["text"]).pack(anchor="w")

            for ev in evs[:4]:
                row = tk.Frame(group, bg=C["bg2"])
                row.pack(fill="x", pady=1)
                title = (ev.get("window_title","") or "")[:72]
                ts    = (ev.get("timestamp","") or "")[:19].replace("T"," ")[11:]
                tk.Label(row, text=title, font=F(10),
                         bg=C["bg2"], fg=C["text"],
                         anchor="w").pack(side="left", padx=10, pady=5)
                tk.Label(row, text=ts, font=F(8),
                         bg=C["bg2"], fg=C["text3"]).pack(side="right", padx=10)

    # =========================================================================
    # TAB 5 — SETTINGS
    # =========================================================================

    def _tab_settings(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=C["bg"])
        frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        pad = {"padx":24, "pady":0}

        self._section_label(frame, "General", pady_top=18)
        self._setting_toggle(frame, "Run on Windows startup",
                             "Launch ContextOS when PC boots",
                             "run_on_startup", pad)
        self._setting_toggle(frame, "Show notifications",
                             "Popup insights when detected",
                             "show_notifications", pad)
        self._setting_toggle(frame, "Smart pause (high CPU)",
                             "Pause when CPU exceeds 80%",
                             "smart_pause", pad)

        self._divider(frame)
        self._section_label(frame, "AI & performance")
        self._setting_toggle(frame, "Auto-update tasks",
                             "Mark Notion/Jira tasks in-progress automatically",
                             "auto_update_tasks", pad)
        self._setting_toggle(frame, "Meeting briefings",
                             "Show context summary 5 min before meetings",
                             "meeting_briefing", pad)
        self._setting_toggle(frame, "Cloud AI mode",
                             "Use cloud for heavier analysis (needs internet)",
                             "cloud_ai", pad)

        self._divider(frame)
        self._section_label(frame, "Mode")
        self._setting_dropdown(frame, "Analysis mode",
                               "lite = rules only · full = local AI · auto = detect",
                               "mode", ["auto","lite","full","cloud"], pad)

        self._divider(frame)
        self._section_label(frame, "Privacy")
        self._setting_toggle(frame, "Local only",
                             "Never send any data to the internet",
                             "local_only", pad)

        # Save confirmation label
        self._save_lbl = tk.Label(frame, text="", font=F(9),
                                  bg=C["bg"], fg=C["teal"])
        self._save_lbl.pack(anchor="w", padx=24, pady=(16,20))

    def _setting_toggle(self, parent, label, sub, key, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=1, **pad)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(info, text=label, font=F(11),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        val = tk.BooleanVar(value=bool(self.config.get(key, False)))

        def toggle(k=key, v=val):
            self.config.set(k, v.get())
            self._flash_saved()

        cb = tk.Checkbutton(row, variable=val, command=toggle,
                            bg=C["bg"], activebackground=C["bg"],
                            cursor="hand2")
        cb.pack(side="right")

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)

    def _setting_dropdown(self, parent, label, sub, key, options, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=1, **pad)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(info, text=label, font=F(11),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        val = tk.StringVar(value=str(self.config.get(key, options[0])))

        def on_change(*_):
            self.config.set(key, val.get())
            self._flash_saved()

        dd = ttk.Combobox(row, textvariable=val, values=options,
                          state="readonly", width=10, font=F(10))
        dd.pack(side="right", pady=10)
        dd.bind("<<ComboboxSelected>>", on_change)

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)

    def _flash_saved(self):
        try:
            self._save_lbl.configure(text="✓ Settings saved")
            self.root.after(2000, lambda: self._save_lbl.configure(text=""))
        except Exception:
            pass

    # =========================================================================
    # Shared helpers
    # =========================================================================

    def _section_label(self, parent, text, pady_top=8, padx=20, inline=False):
        lbl = tk.Label(parent, text=text.upper(), font=F(9,"bold"),
                       bg=C["bg"], fg=C["text3"],
                       letterSpacing=2 if hasattr(tk.Label,"letterSpacing") else 0)
        if inline:
            lbl.pack(side="left", pady=pady_top)
        else:
            lbl.pack(anchor="w", padx=padx, pady=(pady_top, 6))

    def _divider(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=24, pady=12)

    def _get_stats(self):
        if self.engine:
            return self.engine.get_stats()
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    0,
        }

    def _get_focus_topic(self):
        kws  = self.db.get_keywords_last_n_events(n=30)
        freq: dict = {}
        for k in kws:
            if len(k) >= 4:
                freq[k] = freq.get(k, 0) + 1
        if not freq:
            return "No focus detected yet — start working!"
        best = max(freq, key=lambda k: freq[k])
        return best.title() + " (detected focus)"

    def _get_recent_apps(self):
        events = self.db.get_recent_events(limit=50, hours=2)
        seen   = []
        for e in events:
            app = e["app_name"]
            if app not in seen:
                seen.append(app)
        return seen

    def _start_auto_refresh(self):
        """Refresh the home tab stats every 30 seconds."""
        def refresh():
            while True:
                time.sleep(30)
                try:
                    if (self.root and
                            self.root.winfo_exists() and
                            self._active_tab == "home"):
                        self.root.after(0, lambda: self._switch_tab("home"))
                except Exception:
                    break
        t = threading.Thread(target=refresh, daemon=True)
        t.start()
'''

# ── ui/tray_app.py update — add "Open Dashboard" that works ──────────────────
files["ui/tray_app_patch.py"] = '''"""
This file patches tray_app to open the real dashboard.
It is imported by tray_app automatically — no changes needed there.
"""
# The real dashboard is in ui/dashboard.py
# TrayApp._open_dashboard() already calls Dashboard().show()
# Nothing extra needed here.
'''

# ── launcher: open_dashboard.py (standalone shortcut) ────────────────────────
files["open_dashboard.py"] = '''"""
open_dashboard.py  -  Open just the ContextOS dashboard (no tray needed).
Useful for testing the GUI on its own.

Usage:  python open_dashboard.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.config_manager import ConfigManager
from data.database import Database
from ui.dashboard import Dashboard

db = Database()
db.initialize()
config = ConfigManager()

print("Opening ContextOS Dashboard...")
dash = Dashboard(config=config, db=db, engine=None)
dash.show()
'''

# ── Write files ───────────────────────────────────────────────────────────────
created = 0
for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    created += 1
    print(f"  OK  {rel_path}")

print(f"\nDone! {created} files written.")
print("\nTo open the dashboard:")
print("  python open_dashboard.py")
print("\nOr run the full app (tray + dashboard):")
print("  python main.py")
print("  then type 'd' and press Enter")
