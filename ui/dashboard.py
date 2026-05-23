"""
ui/dashboard.py  -  Full 5-tab GUI dashboard for ContextOS.
Built with tkinter (built into Python — no install needed).

Tabs:  Home · Insights · Apps · Memory · Settings
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
import logging

logger = logging.getLogger(__name__)

C = {
    "bg":           "#ffffff",
    "bg2":          "#f8f8f6",
    "bg3":          "#f0efeb",
    "border":       "#e5e3dc",
    "text":         "#1a1a1a",
    "text2":        "#555550",
    "text3":        "#999890",
    "teal":         "#1D9E75",
    "teal_light":   "#e1f5ee",
    "blue":         "#185FA5",
    "blue_light":   "#e6f1fb",
    "amber":        "#BA7517",
    "amber_light":  "#faeeda",
    "red":          "#A32D2D",
    "red_light":    "#fcebeb",
    "purple":       "#534AB7",
    "purple_light": "#eeedfe",
    "sidebar":      "#f4f3ef",
    "sidebar_sel":  "#ffffff",
}

FF = "Segoe UI"

def F(size=11, weight="normal"):
    return (FF, size, weight)


class Dashboard:

    def __init__(self, config, db, engine=None):
        self.config      = config
        self.db          = db
        self.engine      = engine
        self.root        = None
        self._active_tab = "home"
        self._save_lbl   = None
        self._search_var = None

    def show(self):
        self.root = tk.Tk()
        self.root.title("ContextOS — Dashboard")
        self.root.geometry("820x580")
        self.root.minsize(700, 480)
        self.root.configure(bg=C["bg"])
        self._build_titlebar()
        self._build_body()
        self._switch_tab("home")
        self._start_auto_refresh()
        self.root.mainloop()

    # ── Title bar ──────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=C["bg2"], height=42)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C["bg2"])
        left.pack(side="left", padx=14, pady=8)

        dot = tk.Canvas(left, width=10, height=10,
                        bg=C["bg2"], highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=C["teal"], outline="")
        dot.pack(side="left", padx=(0, 6))

        tk.Label(left, text="ContextOS", font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(side="left")

        right = tk.Frame(bar, bg=C["bg2"])
        right.pack(side="right", padx=14)

        self._status_lbl = tk.Label(
            right, text="● Watching",
            font=F(9), bg=C["teal_light"], fg=C["teal"],
            padx=8, pady=2)
        self._status_lbl.pack()

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

    # ── Body ───────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        tk.Frame(body, bg=C["border"], width=1).pack(side="left", fill="y")
        self._content = tk.Frame(body, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=C["sidebar"], width=52)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tabs = [
            ("home",     "\u2302", "Home"),
            ("insights", "\u26a1", "Insights"),
            ("apps",     "\u25c8", "Apps"),
            ("memory",   "\u25ce", "Memory"),
            ("settings", "\u2699", "Settings"),
        ]

        self._sb_btns = {}
        spacer_added  = False

        for i, (key, icon, label) in enumerate(tabs):
            if i == 4 and not spacer_added:
                tk.Frame(sb, bg=C["sidebar"]).pack(expand=True)
                spacer_added = True

            btn = tk.Button(
                sb, text=icon, font=("Segoe UI Emoji", 16),
                bg=C["sidebar"], fg=C["text2"],
                relief="flat", bd=0, cursor="hand2",
                width=3, height=2,
                activebackground=C["sidebar_sel"],
                activeforeground=C["teal"],
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>",
                lambda e, b=btn: b.configure(
                    bg=C["sidebar_sel"], fg=C["teal"]))
            btn.bind("<Leave>",
                lambda e, b=btn, k=key: b.configure(
                    bg=C["sidebar_sel"] if k == self._active_tab else C["sidebar"],
                    fg=C["teal"] if k == self._active_tab else C["text2"]))
            self._sb_btns[key] = btn

    def _switch_tab(self, key):
        self._active_tab = key
        for k, btn in self._sb_btns.items():
            if k == key:
                btn.configure(bg=C["sidebar_sel"], fg=C["teal"])
            else:
                btn.configure(bg=C["sidebar"], fg=C["text2"])
        for w in self._content.winfo_children():
            w.destroy()
        {
            "home":     self._tab_home,
            "insights": self._tab_insights,
            "apps":     self._tab_apps,
            "memory":   self._tab_memory,
            "settings": self._tab_settings,
        }[key](self._content)

    # ── Scrollable canvas helper ───────────────────────────────────────────────

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=C["bg"])
        frame.bind("<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return frame

    # =========================================================================
    # TAB 1 — HOME
    # =========================================================================

    def _tab_home(self, parent):
        frame = self._scrollable(parent)
        pad   = {"padx": 20, "pady": 0}

        self._section_label(frame, "Today's overview", pady_top=18)

        # Stat cards
        stats      = self._get_stats()
        stats_wrap = tk.Frame(frame, bg=C["bg"])
        stats_wrap.pack(fill="x", padx=20, pady=(0, 16))

        defs = [
            ("Insights fired",   str(stats["insights_today"]),   "today",              C["purple"]),
            ("Conflicts caught", str(stats["conflicts_caught"]),  "saved from mistakes",C["amber"]),
            ("Tasks auto-done",  str(stats["tasks_auto_done"]),   "in Notion / Jira",  C["teal"]),
            ("Focus time",       str(stats["focus_minutes"]) + "m","deep work today",  C["blue"]),
        ]

        for i, (label, value, sub, color) in enumerate(defs):
            card = tk.Frame(stats_wrap, bg=C["bg2"])
            card.grid(row=0, column=i,
                      padx=(0, 10) if i < 3 else 0,
                      sticky="ew", ipady=10, ipadx=10)
            stats_wrap.columnconfigure(i, weight=1)

            tk.Label(card, text=label, font=F(9),
                     bg=C["bg2"], fg=C["text2"]).pack(anchor="w", padx=10, pady=(10, 0))
            tk.Label(card, text=value, font=F(22, "bold"),
                     bg=C["bg2"], fg=color).pack(anchor="w", padx=10)
            tk.Label(card, text=sub, font=F(8),
                     bg=C["bg2"], fg=C["text3"]).pack(anchor="w", padx=10, pady=(0, 8))

        # Current focus
        self._section_label(frame, "Current focus")

        focus_wrap = tk.Frame(frame, bg=C["bg2"])
        focus_wrap.pack(fill="x", padx=20, pady=(0, 16))

        topic = self._get_focus_topic()
        tk.Label(focus_wrap, text=topic, font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(anchor="w", padx=14, pady=(12, 4))

        chips_row = tk.Frame(focus_wrap, bg=C["bg2"])
        chips_row.pack(anchor="w", padx=14, pady=(0, 12))

        for app in self._get_recent_apps()[:6]:
            tk.Label(chips_row, text=app, font=F(9),
                     bg=C["bg"], fg=C["text2"],
                     relief="flat", padx=8, pady=2
                     ).pack(side="left", padx=(0, 5))

        # Context trail
        self._section_label(frame, "Context trail")

        trail_wrap = tk.Frame(frame, bg=C["bg"])
        trail_wrap.pack(fill="x", padx=20, pady=(0, 20))

        events = self.db.get_recent_events(limit=10, hours=8)
        if not events:
            tk.Label(trail_wrap,
                     text="No activity yet — start using your apps!",
                     font=F(10), bg=C["bg"], fg=C["text3"]
                     ).pack(anchor="w", pady=8)
        else:
            for ev in events:
                self._trail_row(trail_wrap, ev)

    def _trail_row(self, parent, event):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=2)

        dot = tk.Canvas(row, width=8, height=8,
                        bg=C["bg"], highlightthickness=0)
        dot.create_oval(1, 1, 7, 7, fill=C["border"], outline=C["text3"])
        dot.pack(side="left", pady=6, padx=(4, 8))

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True)

        ts = (event.get("timestamp") or "")[:19].replace("T", " ")
        tk.Label(info, text=ts[11:], font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        title = (event.get("window_title") or "")[:68]
        app   = event.get("app_name", "")
        tk.Label(info, text=f"[{app}]  {title}", font=F(10),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")

    # =========================================================================
    # TAB 2 — INSIGHTS
    # =========================================================================

    def _tab_insights(self, parent):
        hdr = tk.Frame(parent, bg=C["bg"])
        hdr.pack(fill="x", padx=20, pady=(18, 0))
        self._section_label(hdr, "All active insights", inline=True)
        tk.Button(hdr, text="Refresh", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, cursor="hand2",
                  command=lambda: self._switch_tab("insights")
                  ).pack(side="right")

        frame    = self._scrollable(parent)
        insights = self.db.get_active_insights(limit=20)

        if not insights:
            msg = "No active insights right now.\n\nContextOS is watching your apps."
            tk.Label(frame, text=msg,
                     font=F(11), bg=C["bg"], fg=C["text3"],
                     justify="center").pack(pady=60)
            return

        for ins in insights:
            self._insight_card(frame, ins)

    def _insight_card(self, parent, ins):
        type_map = {
            "conflict":    (C["amber"],  C["amber_light"],  "Conflict"),
            "answer":      (C["blue"],   C["blue_light"],   "Answer found"),
            "auto_update": (C["teal"],   C["teal_light"],   "Auto-updated"),
            "meeting_prep":(C["purple"], C["purple_light"], "Meeting prep"),
        }
        itype              = ins.get("insight_type", "conflict")
        color, bg_l, badge = type_map.get(itype, (C["text2"], C["bg2"], itype))

        card = tk.Frame(parent, bg=C["bg"],
                        highlightbackground=C["border"],
                        highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 10))

        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")

        body = tk.Frame(card, bg=C["bg"])
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        top = tk.Frame(body, bg=C["bg"])
        top.pack(fill="x")

        tk.Label(top, text=badge, font=F(9),
                 bg=bg_l, fg=color, padx=6, pady=1).pack(side="left")

        ts = (ins.get("timestamp") or "")[:19].replace("T", " ")[11:]
        tk.Label(top, text=ts, font=F(8),
                 bg=C["bg"], fg=C["text3"]).pack(side="right")

        tk.Label(body, text=ins.get("title", ""), font=F(11, "bold"),
                 bg=C["bg"], fg=C["text"],
                 wraplength=560, justify="left", anchor="w"
                 ).pack(fill="x", pady=(6, 2))

        detail = ins.get("detail", "")
        if detail:
            tk.Label(body, text=detail, font=F(10),
                     bg=C["bg"], fg=C["text2"],
                     wraplength=560, justify="left", anchor="w"
                     ).pack(fill="x")

        sources = ins.get("source_apps", "")
        if sources:
            tk.Label(body, text="Sources: " + sources, font=F(8),
                     bg=C["bg"], fg=C["text3"]).pack(anchor="w", pady=(4, 0))

        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(anchor="w", pady=(8, 0))

        iid = ins.get("id")
        tk.Button(btn_row, text="Dismiss", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._dismiss(i)
                  ).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Mark acted on", font=F(9),
                  bg=C["teal_light"], fg=C["teal"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._act_on(i)
                  ).pack(side="left")

    def _dismiss(self, iid):
        if iid:
            self.db.dismiss_insight(iid)
        self._switch_tab("insights")

    def _act_on(self, iid):
        if iid:
            with self.db._connect() as conn:
                conn.execute(
                    "UPDATE insights SET acted_on=1, dismissed=1 WHERE id=?",
                    (iid,))
        self._switch_tab("insights")

    # =========================================================================
    # TAB 3 — APPS
    # =========================================================================

    def _tab_apps(self, parent):
        self._section_label(parent, "Watched apps", pady_top=18, padx=20)
        frame = self._scrollable(parent)
        grid  = tk.Frame(frame, bg=C["bg"])
        grid.pack(fill="x", padx=20, pady=(0, 10))

        events     = self.db.get_recent_events(limit=200, hours=24)
        app_counts: dict = {}
        app_last:   dict = {}

        for ev in events:
            app = ev["app_name"]
            app_counts[app] = app_counts.get(app, 0) + 1
            if app not in app_last:
                app_last[app] = ev["timestamp"]

        watched  = self.config.get("watched_apps", [])
        all_apps = list(app_counts.keys())
        for w in watched:
            if not any(w.lower() in a.lower() for a in all_apps):
                all_apps.append(w)

        for i, app in enumerate(all_apps[:12]):
            col    = i % 3
            row    = i // 3
            count  = app_counts.get(app, 0)
            last_t = app_last.get(app, "")
            last_s = last_t[:19].replace("T", " ")[11:] if last_t else "No activity"
            active = count > 0

            card = tk.Frame(grid, bg=C["bg2"])
            card.grid(row=row, column=col,
                      padx=(0, 10) if col < 2 else 0,
                      pady=(0, 10), sticky="ew",
                      ipadx=10, ipady=8)
            grid.columnconfigure(col, weight=1)

            top = tk.Frame(card, bg=C["bg2"])
            top.pack(fill="x", padx=10, pady=(10, 0))

            dot = tk.Canvas(top, width=8, height=8,
                            bg=C["bg2"], highlightthickness=0)
            dot.create_oval(1, 1, 7, 7,
                fill=C["teal"] if active else C["border"], outline="")
            dot.pack(side="left", pady=3, padx=(0, 6))

            tk.Label(top, text=app, font=F(11, "bold"),
                     bg=C["bg2"], fg=C["text"]).pack(side="left")

            tk.Label(card, text=str(count) + " events today",
                     font=F(9), bg=C["bg2"], fg=C["text2"]
                     ).pack(anchor="w", padx=10)
            tk.Label(card, text="Last: " + last_s,
                     font=F(8), bg=C["bg2"], fg=C["text3"]
                     ).pack(anchor="w", padx=10, pady=(0, 8))

    # =========================================================================
    # TAB 4 — MEMORY
    # =========================================================================

    def _tab_memory(self, parent):
        search_wrap = tk.Frame(parent, bg=C["bg"])
        search_wrap.pack(fill="x", padx=20, pady=(18, 10))
        self._section_label(search_wrap, "Context memory", inline=True)

        search_box = tk.Frame(search_wrap, bg=C["bg"])
        search_box.pack(side="right")

        self._search_var = tk.StringVar()
        entry = tk.Entry(search_box, textvariable=self._search_var,
                         font=F(10), width=22,
                         bg=C["bg2"], fg=C["text"],
                         relief="flat", bd=1,
                         highlightbackground=C["border"],
                         highlightthickness=1)
        entry.pack(side="left", ipady=5, padx=(0, 6))
        placeholder = "Search your work context..."
        entry.insert(0, placeholder)
        entry.bind("<FocusIn>",
            lambda e: entry.delete(0, "end")
            if entry.get() == placeholder else None)

        frame = self._scrollable(parent)

        tk.Button(search_box, text="Search", font=F(9),
                  bg=C["teal"], fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2",
                  command=lambda: self._do_search(frame, self._search_var.get())
                  ).pack(side="left")

        entry.bind("<Return>",
            lambda e: self._do_search(frame, self._search_var.get()))

        self._do_search(frame, "")

    def _do_search(self, frame, query):
        for w in frame.winfo_children():
            w.destroy()

        events = self.db.get_recent_events(limit=100, hours=24 * 7)
        q      = query.strip().lower()
        skip   = ("", "search your work context...")
        if q and q not in skip:
            events = [
                e for e in events
                if q in (e.get("window_title") or "").lower()
                or q in (e.get("app_name") or "").lower()
                or q in (e.get("keywords") or "").lower()
            ]

        if not events:
            tk.Label(frame, text="No results found.",
                     font=F(10), bg=C["bg"], fg=C["text3"]
                     ).pack(pady=40)
            return

        by_app: dict = {}
        for ev in events:
            by_app.setdefault(ev["app_name"], []).append(ev)

        for app, evs in list(by_app.items())[:8]:
            group = tk.Frame(frame, bg=C["bg"])
            group.pack(fill="x", padx=20, pady=(0, 12))

            tk.Label(group, text=app, font=F(10, "bold"),
                     bg=C["bg"], fg=C["text"]).pack(anchor="w")

            for ev in evs[:4]:
                row = tk.Frame(group, bg=C["bg2"])
                row.pack(fill="x", pady=1)
                title = (ev.get("window_title") or "")[:70]
                ts    = (ev.get("timestamp") or "")[:19].replace("T", " ")[11:]
                tk.Label(row, text=title, font=F(10),
                         bg=C["bg2"], fg=C["text"], anchor="w"
                         ).pack(side="left", padx=10, pady=5)
                tk.Label(row, text=ts, font=F(8),
                         bg=C["bg2"], fg=C["text3"]
                         ).pack(side="right", padx=10)

    # =========================================================================
    # TAB 5 — SETTINGS
    # =========================================================================

    def _tab_settings(self, parent):
        frame = self._scrollable(parent)
        pad   = {"padx": 24}

        self._section_label(frame, "General", pady_top=18)
        self._toggle(frame, "Run on Windows startup",
                     "Launch ContextOS when PC boots",
                     "run_on_startup", pad)
        self._toggle(frame, "Show notifications",
                     "Popup insights when detected",
                     "show_notifications", pad)
        self._toggle(frame, "Smart pause (high CPU)",
                     "Pause analysis when CPU exceeds 80%",
                     "smart_pause", pad)

        self._divider(frame)
        self._section_label(frame, "Features")
        self._toggle(frame, "Auto-update tasks",
                     "Mark Notion / Jira tasks in-progress automatically",
                     "auto_update_tasks", pad)
        self._toggle(frame, "Meeting briefings",
                     "Show context summary 5 min before meetings",
                     "meeting_briefing", pad)
        self._toggle(frame, "Cloud AI mode",
                     "Use cloud for heavier analysis (needs internet)",
                     "cloud_ai", pad)

        self._divider(frame)
        self._section_label(frame, "Mode")
        self._dropdown(frame, "Analysis mode",
                       "lite = rules only    full = local AI    auto = detect",
                       "mode", ["auto", "lite", "full", "cloud"], pad)

        self._divider(frame)
        self._section_label(frame, "Privacy")
        self._toggle(frame, "Local only",
                     "Never send any data to the internet",
                     "local_only", pad)

        self._save_lbl = tk.Label(frame, text="", font=F(9),
                                  bg=C["bg"], fg=C["teal"])
        self._save_lbl.pack(anchor="w", padx=24, pady=(16, 20))

    def _toggle(self, parent, label, sub, key, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=pad.get("padx", 24), pady=1)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(info, text=label, font=F(11),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        val = tk.BooleanVar(value=bool(self.config.get(key, False)))

        def on_toggle(k=key, v=val):
            self.config.set(k, v.get())
            self._flash_saved()

        tk.Checkbutton(row, variable=val, command=on_toggle,
                       bg=C["bg"], activebackground=C["bg"],
                       cursor="hand2").pack(side="right")

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)

    def _dropdown(self, parent, label, sub, key, options, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=pad.get("padx", 24), pady=1)

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
            self._save_lbl.configure(text="\u2713 Settings saved")
            self.root.after(
                2000, lambda: self._save_lbl.configure(text=""))
        except Exception:
            pass

    # =========================================================================
    # Shared helpers
    # =========================================================================

    def _section_label(self, parent, text, pady_top=8, padx=20, inline=False):
        lbl = tk.Label(parent, text=text.upper(), font=F(9, "bold"),
                       bg=C["bg"], fg=C["text3"])
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
            return "No focus detected yet — start using your apps!"
        best = max(freq, key=lambda k: freq[k])
        return best.title() + " — detected focus"

    def _get_recent_apps(self):
        events = self.db.get_recent_events(limit=50, hours=2)
        seen: list = []
        for e in events:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return seen

    def _start_auto_refresh(self):
        def loop():
            while True:
                time.sleep(30)
                try:
                    if (self.root and
                            self.root.winfo_exists() and
                            self._active_tab == "home"):
                        self.root.after(
                            0, lambda: self._switch_tab("home"))
                except Exception:
                    break
        threading.Thread(target=loop, daemon=True).start()
