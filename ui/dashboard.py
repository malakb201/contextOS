"""
ui/dashboard.py - ContextOS Dashboard
Developed by SAIPK@support
WHITE professional theme, stable tooltips, working scroll
"""
import tkinter as tk
from tkinter import ttk
import threading, time, os, logging

logger   = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_ICO = os.path.join(BASE_DIR, "assets", "icons", "contextOS.ico")
LOGO_48  = os.path.join(BASE_DIR, "assets", "icons", "logo_48.png")
LOGO_32  = os.path.join(BASE_DIR, "assets", "icons", "logo_32.png")

# ── WHITE PROFESSIONAL THEME ──────────────────────────────────────────────────
BG      = "#ffffff"   # pure white main background
BG2     = "#f8f9fa"   # light gray panels
BG3     = "#f1f3f4"   # slightly darker cards
BG4     = "#e8eaed"   # hover / border-ish
BORDER  = "#e0e0e0"
BORDER2 = "#d0d0d0"
TEXT    = "#1a1a1a"   # near black text
TEXT2   = "#5f6368"   # secondary gray
TEXT3   = "#9aa0a6"   # muted hints

TEAL    = "#0d7a4e"   # primary green
TEALL   = "#0d9e62"   # lighter green
TEAL_BG = "#e6f4ee"
AMBER   = "#b45309"
AMBERL  = "#d97706"
AMBER_BG= "#fef3c7"
BLUE    = "#1a56db"
BLUEL   = "#3b82f6"
BLUE_BG = "#eff6ff"
PURPLE  = "#6d28d9"
PURPL   = "#8b5cf6"
PURP_BG = "#f5f3ff"

SAIPK   = "#0d7a4e"
SB_BG   = "#1e293b"   # dark sidebar
SB_ICON = "#94a3b8"   # sidebar icon inactive
SB_ACT  = "#ffffff"   # sidebar icon active
SB_HOVB = "#334155"   # sidebar hover bg

FF = "Segoe UI"
def F(sz=11, w="normal"): return (FF, sz, w)
def FB(sz=11):             return (FF, sz, "bold")


class Dashboard:
    def __init__(self, config, db, engine=None):
        self.config       = config
        self.db           = db
        self.engine       = engine
        self.root         = None
        self._active      = "home"
        self._imgs        = {}
        self._save_lbl    = None
        self._search_var  = None
        self._blink_state = True
        # tooltip state
        self._tip_label   = None   # Label widget inside sidebar
        self._tip_after   = None   # scheduled hide job

    # ─────────────────────────────────────────────────────────────────────────
    # STABLE TOOLTIP — inline label in sidebar, never a Toplevel
    # ─────────────────────────────────────────────────────────────────────────
    def _show_tip(self, text):
        """Show tooltip text in the sidebar tip label."""
        if self._tip_label:
            self._tip_label.configure(text=text)
        if self._tip_after:
            self.root.after_cancel(self._tip_after)
            self._tip_after = None

    def _hide_tip(self):
        """Hide tooltip after a short delay so it doesn't flash."""
        if self._tip_after:
            self.root.after_cancel(self._tip_after)
        self._tip_after = self.root.after(400, self._do_hide)

    def _do_hide(self):
        self._tip_after = None
        if self._tip_label:
            self._tip_label.configure(text="")

    # ─────────────────────────────────────────────────────────────────────────
    # SHOW
    # ─────────────────────────────────────────────────────────────────────────
    def show(self):
        self.root = tk.Tk()
        self.root.title("ContextOS — Dashboard")
        self.root.configure(bg=BG)
        self.root.minsize(900, 580)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = min(1140, int(sw * 0.85))
        h  = min(720,  int(sh * 0.84))
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        try:
            if os.path.exists(ICON_ICO):
                self.root.iconbitmap(ICON_ICO)
        except Exception:
            pass

        self._load_imgs()
        self._apply_style()
        self._build_titlebar()
        self._build_main()
        self._switch("home")
        self._auto_refresh()
        self.root.mainloop()

    def _load_imgs(self):
        try:
            from PIL import Image, ImageTk
            for key, path, sz in [("32", LOGO_32, 32), ("48", LOGO_48, 48)]:
                if os.path.exists(path):
                    img = Image.open(path).convert("RGBA").resize(
                        (sz, sz), Image.LANCZOS)
                    self._imgs[key] = ImageTk.PhotoImage(img)
        except Exception as e:
            logger.debug(f"Logo: {e}")

    def _apply_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        # Slim scrollbar matching white theme
        s.configure("Slim.Vertical.TScrollbar",
                    background=BG4,
                    troughcolor=BG2,
                    arrowcolor=BG4,
                    borderwidth=0,
                    relief="flat",
                    width=6)
        s.map("Slim.Vertical.TScrollbar",
              background=[("active", BORDER2)])
        s.configure("TCombobox",
                    fieldbackground=BG,
                    background=BG,
                    foreground=TEXT,
                    selectbackground=BG3,
                    arrowcolor=TEXT2,
                    borderwidth=1)

    # ─────────────────────────────────────────────────────────────────────────
    # TITLE BAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=BG, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Left
        left = tk.Frame(bar, bg=BG)
        left.place(x=16, rely=0.5, anchor="w")

        if "32" in self._imgs:
            tk.Label(left, image=self._imgs["32"],
                     bg=BG).pack(side="left", padx=(0, 10))

        tk.Label(left, text="ContextOS",
                 font=FB(14), bg=BG, fg=TEXT).pack(side="left")

        tk.Label(left, text="  —  ",
                 font=F(12), bg=BG, fg=BORDER2).pack(side="left")

        tk.Label(left, text="by SAIPK@support",
                 font=F(9), bg=BG, fg=SAIPK).pack(side="left")

        # Right — blinking dot + Running
        right = tk.Frame(bar, bg=BG)
        right.place(relx=1.0, x=-20, rely=0.5, anchor="e")

        self._blink_dot = tk.Canvas(right, width=10, height=10,
                                    bg=BG, highlightthickness=0)
        self._blink_dot.create_oval(1, 1, 9, 9, fill=TEAL, tags="dot")
        self._blink_dot.pack(side="left", padx=(0, 6))

        tk.Label(right, text="Running",
                 font=F(10), bg=BG, fg=TEXT2).pack(side="left")

        self._start_blink()
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    def _start_blink(self):
        def blink():
            if not self.root or not self.root.winfo_exists():
                return
            self._blink_state = not self._blink_state
            col = TEAL if self._blink_state else BG
            try:
                self._blink_dot.itemconfig("dot", fill=col)
                self.root.after(1000, blink)
            except Exception:
                pass
        self.root.after(1000, blink)

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR + CONTENT
    # ─────────────────────────────────────────────────────────────────────────
    def _build_main(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True)
        self._build_sidebar(wrap)
        tk.Frame(wrap, bg=BORDER, width=1).pack(side="left", fill="y")
        self._content = tk.Frame(wrap, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self, parent):
        # Dark sidebar contrasts with white content
        sb = tk.Frame(parent, bg=SB_BG, width=64)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        self._sb = {}
        tabs = [
            ("home",     "⌂",  "Home"),
            ("insights", "⚡", "Insights"),
            ("apps",     "◈",  "Apps"),
            ("memory",   "◎",  "Memory"),
            ("settings", "⚙",  "Settings"),
        ]

        for key, icon, label in tabs:
            frame = tk.Frame(sb, bg=SB_BG, cursor="hand2")
            frame.pack(fill="x")

            lbl = tk.Label(frame, text=icon,
                           font=("Segoe UI Emoji", 18),
                           bg=SB_BG, fg=SB_ICON,
                           width=4, pady=12)
            lbl.pack(fill="x")

            def on_enter(e, k=key, ic=lbl, fr=frame, ln=label):
                if self._active != k:
                    fr.configure(bg=SB_HOVB)
                    ic.configure(bg=SB_HOVB, fg=SB_ACT)
                self._show_tip(ln)

            def on_leave(e, k=key, ic=lbl, fr=frame):
                if self._active != k:
                    fr.configure(bg=SB_BG)
                    ic.configure(bg=SB_BG, fg=SB_ICON)
                self._hide_tip()

            def on_click(e, k=key):
                self._do_hide()
                self._switch(k)

            for w in (frame, lbl):
                w.bind("<Enter>",    on_enter)
                w.bind("<Leave>",    on_leave)
                w.bind("<Button-1>", on_click)

            self._sb[key] = (frame, lbl)

        # Tooltip label at bottom of sidebar
        tk.Frame(sb, bg=SB_BG).pack(expand=True, fill="y")

        self._tip_label = tk.Label(sb, text="",
                                   font=F(9), bg=SB_BG, fg=SB_ACT,
                                   wraplength=60, justify="center")
        self._tip_label.pack(pady=4)

        if "32" in self._imgs:
            tk.Label(sb, image=self._imgs["32"],
                     bg=SB_BG).pack(pady=10)

    def _switch(self, key):
        self._active = key
        for k, (fr, lbl) in self._sb.items():
            if k == key:
                fr.configure(bg=SB_HOVB)
                lbl.configure(bg=SB_HOVB, fg=SB_ACT)
            else:
                fr.configure(bg=SB_BG)
                lbl.configure(bg=SB_BG, fg=SB_ICON)

        for w in self._content.winfo_children():
            w.destroy()

        {
            "home":     self._home,
            "insights": self._insights,
            "apps":     self._apps,
            "memory":   self._memory,
            "settings": self._settings,
        }[key](self._content)

    # ─────────────────────────────────────────────────────────────────────────
    # SCROLLABLE FRAME — mouse wheel working on all children
    # ─────────────────────────────────────────────────────────────────────────
    def _scroll_frame(self, parent):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG,
                           highlightthickness=0, borderwidth=0)
        sb = ttk.Scrollbar(outer, orient="vertical",
                           command=canvas.yview,
                           style="Slim.Vertical.TScrollbar")
        frame = tk.Frame(canvas, bg=BG)

        frame.bind("<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))

        win_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width))

        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Bind scroll to canvas AND frame AND all children recursively
        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        def _bind_wheel(widget):
            widget.bind("<MouseWheel>", _wheel)
            for child in widget.winfo_children():
                _bind_wheel(child)

        canvas.bind("<MouseWheel>", _wheel)
        frame.bind("<MouseWheel>", _wheel)

        # Re-bind after frame children are added
        frame.bind("<Configure>",
            lambda e: [canvas.configure(
                scrollregion=canvas.bbox("all")),
                _bind_wheel(frame)])

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    # SHARED WIDGETS
    # ─────────────────────────────────────────────────────────────────────────
    def _section(self, parent, text, top=20, left=24):
        tk.Label(parent, text=text.upper(),
                 font=FB(8), bg=BG, fg=TEXT3, anchor="w"
                 ).pack(anchor="w", padx=left, pady=(top, 6))

    def _divider(self, parent):
        tk.Frame(parent, bg=BORDER, height=1
                 ).pack(fill="x", padx=24, pady=12)

    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=BG2,
                        highlightbackground=BORDER,
                        highlightthickness=1, **kw)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — HOME
    # ─────────────────────────────────────────────────────────────────────────
    def _home(self, parent):
        frame = self._scroll_frame(parent)
        stats = self._get_stats()

        # Stat cards
        self._section(frame, "Today's overview")
        sg = tk.Frame(frame, bg=BG)
        sg.pack(fill="x", padx=24, pady=(0, 22))
        sg.columnconfigure((0, 1, 2, 3), weight=1, uniform="sc")

        defs = [
            ("Insights fired",   str(stats["insights_today"]),  "today",               PURPL,  PURP_BG, PURPLE),
            ("Conflicts caught", str(stats["conflicts_caught"]), "saved from mistakes", AMBERL, AMBER_BG, AMBER),
            ("Tasks auto-done",  str(stats["tasks_auto_done"]),  "in Notion / Jira",   TEALL,  TEAL_BG, TEAL),
            ("Focus time",       f"{stats['focus_minutes']}m",   "deep work today",    BLUEL,  BLUE_BG, BLUE),
        ]

        for i, (lbl, val, sub, fg_c, bg_c, bdr) in enumerate(defs):
            card = tk.Frame(sg, bg=bg_c,
                            highlightbackground=bdr,
                            highlightthickness=1)
            card.grid(row=0, column=i,
                      padx=(0, 10) if i < 3 else 0,
                      sticky="ew", ipadx=14, ipady=8)
            tk.Label(card, text=lbl, font=F(9),
                     bg=bg_c, fg=TEXT2, anchor="w"
                     ).pack(anchor="w", padx=14, pady=(12, 0))
            tk.Label(card, text=val, font=FB(28),
                     bg=bg_c, fg=bdr, anchor="w"
                     ).pack(anchor="w", padx=14)
            tk.Label(card, text=sub, font=F(8),
                     bg=bg_c, fg=TEXT3, anchor="w"
                     ).pack(anchor="w", padx=14, pady=(0, 12))

        # Current focus
        self._section(frame, "Current focus")
        fc = tk.Frame(frame, bg=BG2,
                      highlightbackground=TEAL,
                      highlightthickness=1)
        fc.pack(fill="x", padx=24, pady=(0, 22))
        tk.Frame(fc, bg=TEAL, height=3).pack(fill="x")
        inner = tk.Frame(fc, bg=BG2)
        inner.pack(fill="x", padx=16, pady=14)
        tk.Label(inner, text=self._focus_topic(),
                 font=FB(13), bg=BG2, fg=TEXT, anchor="w"
                 ).pack(anchor="w", pady=(0, 10))
        chips = tk.Frame(inner, bg=BG2)
        chips.pack(anchor="w")
        for app in self._recent_apps()[:8]:
            tk.Label(chips, text=app, font=F(9),
                     bg=BG4, fg=TEXT2, padx=10, pady=4,
                     relief="flat"
                     ).pack(side="left", padx=(0, 6))

        # Active insights
        active = self.db.get_active_insights(limit=3)
        if active:
            self._section(frame, "Active insights")
            for ins in active:
                self._ins_row(frame, ins, compact=True)

        # Context trail
        self._section(frame, "Context trail")
        evs = self.db.get_recent_events(limit=12, hours=8)
        if not evs:
            tk.Label(frame,
                     text="No activity yet — start using your apps",
                     font=F(10), bg=BG, fg=TEXT3
                     ).pack(anchor="w", padx=24, pady=8)
        else:
            trail = tk.Frame(frame, bg=BG)
            trail.pack(fill="x", padx=24, pady=(0, 8))
            for ev in evs:
                self._trail_row(trail, ev)

        # Footer
        foot = tk.Frame(frame, bg=BG3,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        foot.pack(fill="x", padx=24, pady=(16, 24))
        if "32" in self._imgs:
            tk.Label(foot, image=self._imgs["32"],
                     bg=BG3).pack(side="left", padx=12, pady=8)
        tk.Label(foot, text="ContextOS — AI-Powered Context Bridge",
                 font=F(9), bg=BG3, fg=TEXT3
                 ).pack(side="left", pady=8)
        tk.Label(foot, text="SAIPK@support",
                 font=FB(9), bg=BG3, fg=SAIPK
                 ).pack(side="right", padx=14, pady=8)

    def _trail_row(self, parent, ev):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=2)
        dot = tk.Canvas(row, width=8, height=8,
                        bg=BG, highlightthickness=0)
        dot.create_oval(1, 1, 7, 7, fill=BORDER2)
        dot.pack(side="left", pady=8, padx=(2, 10))
        info = tk.Frame(row, bg=BG)
        info.pack(side="left", fill="x", expand=True)
        ts    = (ev.get("timestamp") or "")[:19].replace("T", " ")
        app   = ev.get("app_name", "")
        title = (ev.get("window_title") or "")[:75]
        top   = tk.Frame(info, bg=BG)
        top.pack(anchor="w")
        tk.Label(top, text=ts[11:], font=F(8),
                 bg=BG, fg=TEXT3).pack(side="left")
        tk.Label(top, text=f"   {app}", font=FB(9),
                 bg=BG, fg=TEAL).pack(side="left")
        tk.Label(info, text=title, font=F(10),
                 bg=BG, fg=TEXT2, anchor="w").pack(anchor="w")
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 1))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — INSIGHTS
    # ─────────────────────────────────────────────────────────────────────────
    def _insights(self, parent):
        hbar = tk.Frame(parent, bg=BG,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        hbar.pack(fill="x")
        tk.Label(hbar, text="ALL ACTIVE INSIGHTS",
                 font=FB(8), bg=BG, fg=TEXT3
                 ).pack(side="left", padx=24, pady=13)
        tk.Button(hbar, text="↻  Refresh",
                  font=F(9), bg=BG3, fg=TEXT2,
                  relief="flat", padx=12, pady=4,
                  cursor="hand2",
                  command=lambda: self._switch("insights")
                  ).pack(side="right", padx=16, pady=9)

        frame = self._scroll_frame(parent)
        ins   = self.db.get_active_insights(limit=30)

        if not ins:
            tk.Label(frame,
                     text="✓   No active insights right now",
                     font=FB(13), bg=BG, fg=TEXT3
                     ).pack(pady=80)
            tk.Label(frame,
                     text="ContextOS is silently watching your apps",
                     font=F(11), bg=BG, fg=TEXT3).pack()
            return

        for i in ins:
            self._ins_row(frame, i)

    def _ins_row(self, parent, ins, compact=False):
        cfg = {
            "conflict":    (AMBER,  AMBER_BG, AMBERL, "⚠  Conflict"),
            "answer":      (BLUE,   BLUE_BG,  BLUEL,  "💡  Answer found"),
            "auto_update": (TEAL,   TEAL_BG,  TEALL,  "✓   Auto-updated"),
            "meeting_prep":(PURPLE, PURP_BG,  PURPL,  "📅  Meeting prep"),
        }
        itype                   = ins.get("insight_type", "conflict")
        accent, bg_c, fg, badge = cfg.get(itype, (BORDER2, BG2, TEXT, itype))

        card = tk.Frame(parent, bg=bg_c,
                        highlightbackground=accent,
                        highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(0, 8))
        tk.Frame(card, bg=accent, width=4).pack(side="left", fill="y")
        body = tk.Frame(card, bg=bg_c)
        body.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        top = tk.Frame(body, bg=bg_c)
        top.pack(fill="x")
        tk.Label(top, text=badge, font=FB(9),
                 bg=bg_c, fg=accent).pack(side="left")
        ts = (ins.get("timestamp") or "")[:19].replace("T", " ")[11:]
        tk.Label(top, text=ts, font=F(8),
                 bg=bg_c, fg=TEXT3).pack(side="right")

        tk.Label(body, text=ins.get("title", ""),
                 font=FB(11), bg=bg_c, fg=TEXT,
                 wraplength=640, justify="left", anchor="w"
                 ).pack(fill="x", pady=(5, 3))

        if not compact:
            detail = ins.get("detail", "")
            if detail:
                tk.Label(body, text=detail, font=F(10),
                         bg=bg_c, fg=TEXT2,
                         wraplength=640, justify="left",
                         anchor="w").pack(fill="x")
            src = ins.get("source_apps", "")
            if src:
                tk.Label(body, text="Sources: " + src,
                         font=F(8), bg=bg_c,
                         fg=TEXT3).pack(anchor="w", pady=(4, 0))
            btf = tk.Frame(body, bg=bg_c)
            btf.pack(anchor="w", pady=(8, 0))
            iid = ins.get("id")
            tk.Button(btf, text="Dismiss",
                      font=F(9), bg=BG4, fg=TEXT2,
                      relief="flat", padx=10, pady=4,
                      cursor="hand2",
                      command=lambda i=iid: self._dismiss(i)
                      ).pack(side="left", padx=(0, 6))
            tk.Button(btf, text="Mark done",
                      font=F(9), bg=TEAL_BG, fg=TEAL,
                      relief="flat", padx=10, pady=4,
                      cursor="hand2",
                      command=lambda i=iid: self._act_on(i)
                      ).pack(side="left")

    def _dismiss(self, iid):
        if iid:
            self.db.dismiss_insight(iid)
        self._switch("insights")

    def _act_on(self, iid):
        if iid:
            with self.db._connect() as conn:
                conn.execute(
                    "UPDATE insights SET acted_on=1,dismissed=1 WHERE id=?",
                    (iid,))
        self._switch("insights")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — APPS
    # ─────────────────────────────────────────────────────────────────────────
    def _apps(self, parent):
        hbar = tk.Frame(parent, bg=BG,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        hbar.pack(fill="x")
        tk.Label(hbar, text="WATCHED APPS",
                 font=FB(8), bg=BG, fg=TEXT3
                 ).pack(side="left", padx=24, pady=13)
        tk.Button(hbar, text="↻  Refresh",
                  font=F(9), bg=BG3, fg=TEXT2,
                  relief="flat", padx=12, pady=4,
                  cursor="hand2",
                  command=lambda: self._switch("apps")
                  ).pack(side="right", padx=16, pady=9)

        frame = self._scroll_frame(parent)
        grid  = tk.Frame(frame, bg=BG)
        grid.pack(fill="x", padx=24, pady=(8, 24))
        grid.columnconfigure((0, 1, 2), weight=1, uniform="ac")

        evs       = self.db.get_recent_events(limit=400, hours=24)
        app_count = {}
        app_last  = {}
        for ev in evs:
            a = ev["app_name"]
            app_count[a] = app_count.get(a, 0) + 1
            if a not in app_last:
                app_last[a] = ev["timestamp"]

        all_apps = list(app_count.keys())
        for w in self.config.get("watched_apps", []):
            if not any(w.lower() in a.lower() for a in all_apps):
                all_apps.append(w)

        for i, app in enumerate(all_apps[:12]):
            col = i % 3
            row = i // 3
            cnt = app_count.get(app, 0)
            lt  = app_last.get(app, "")
            ls  = lt[:19].replace("T", " ")[11:] if lt else "No activity"
            act = cnt > 0

            card = tk.Frame(grid, bg=BG2,
                            highlightbackground=TEAL if act else BORDER,
                            highlightthickness=1)
            card.grid(row=row, column=col,
                      padx=(0, 10) if col < 2 else 0,
                      pady=(0, 10), sticky="ew",
                      ipadx=12, ipady=6)

            top = tk.Frame(card, bg=BG2)
            top.pack(fill="x", padx=12, pady=(10, 4))
            dot = tk.Canvas(top, width=8, height=8,
                            bg=BG2, highlightthickness=0)
            dot.create_oval(1, 1, 7, 7, fill=TEAL if act else BORDER2)
            dot.pack(side="left", pady=2, padx=(0, 7))
            tk.Label(top, text=app, font=FB(11),
                     bg=BG2, fg=TEXT).pack(side="left")
            tk.Label(card,
                     text=f"{cnt} events today" if cnt else "Not seen today",
                     font=F(9), bg=BG2,
                     fg=TEAL if act else TEXT3
                     ).pack(anchor="w", padx=12)
            tk.Label(card, text="Last:  " + ls,
                     font=F(8), bg=BG2, fg=TEXT3
                     ).pack(anchor="w", padx=12, pady=(0, 8))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4 — MEMORY
    # ─────────────────────────────────────────────────────────────────────────
    def _memory(self, parent):
        hbar = tk.Frame(parent, bg=BG,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        hbar.pack(fill="x")
        tk.Label(hbar, text="CONTEXT MEMORY",
                 font=FB(8), bg=BG, fg=TEXT3
                 ).pack(side="left", padx=24, pady=13)

        sbox = tk.Frame(hbar, bg=BG)
        sbox.pack(side="right", padx=16, pady=9)

        self._search_var = tk.StringVar()
        ph  = "Search your context..."
        ent = tk.Entry(sbox, textvariable=self._search_var,
                       font=F(10), width=22,
                       bg=BG2, fg=TEXT,
                       insertbackground=TEXT,
                       relief="flat",
                       highlightbackground=BORDER2,
                       highlightthickness=1)
        ent.insert(0, ph)
        ent.pack(side="left", ipady=6, padx=(0, 8))
        ent.bind("<FocusIn>",
                 lambda e: ent.delete(0, "end")
                 if ent.get() == ph else None)
        ent.bind("<FocusOut>",
                 lambda e: ent.insert(0, ph)
                 if not ent.get() else None)

        frame = self._scroll_frame(parent)

        tk.Button(sbox, text="Search",
                  font=F(9), bg=TEAL, fg="white",
                  relief="flat", padx=12, pady=6,
                  cursor="hand2",
                  command=lambda: self._do_search(
                      frame, self._search_var.get())
                  ).pack(side="left")

        ent.bind("<Return>",
                 lambda e: self._do_search(
                     frame, self._search_var.get()))

        self._do_search(frame, "")

    def _do_search(self, frame, q):
        for w in frame.winfo_children():
            w.destroy()
        evs  = self.db.get_recent_events(limit=200, hours=24 * 7)
        qc   = q.strip().lower()
        skip = ("", "search your context...")
        if qc and qc not in skip:
            evs = [e for e in evs
                   if qc in (e.get("window_title") or "").lower()
                   or qc in (e.get("app_name") or "").lower()
                   or qc in (e.get("keywords") or "").lower()]
        if not evs:
            tk.Label(frame, text="No results found.",
                     font=F(11), bg=BG, fg=TEXT3
                     ).pack(pady=60)
            return
        by_app: dict = {}
        for ev in evs:
            by_app.setdefault(ev["app_name"], []).append(ev)
        for app, items in list(by_app.items())[:10]:
            grp = tk.Frame(frame, bg=BG)
            grp.pack(fill="x", padx=24, pady=(0, 14))
            hl  = tk.Frame(grp, bg=BG)
            hl.pack(fill="x", pady=(0, 4))
            tk.Label(hl, text=app, font=FB(10),
                     bg=BG, fg=TEAL).pack(side="left")
            tk.Label(hl, text=f"  {len(items)} events",
                     font=F(9), bg=BG, fg=TEXT3).pack(side="left")
            for ev in items[:5]:
                row = tk.Frame(grp, bg=BG2,
                               highlightbackground=BORDER,
                               highlightthickness=1)
                row.pack(fill="x", pady=1)
                t  = (ev.get("window_title") or "")[:74]
                ts = (ev.get("timestamp") or "")[:19].replace("T", " ")[11:]
                tk.Label(row, text=t, font=F(10),
                         bg=BG2, fg=TEXT, anchor="w"
                         ).pack(side="left", padx=12, pady=6)
                tk.Label(row, text=ts, font=F(8),
                         bg=BG2, fg=TEXT3
                         ).pack(side="right", padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 5 — SETTINGS
    # ─────────────────────────────────────────────────────────────────────────
    def _settings(self, parent):
        hbar = tk.Frame(parent, bg=BG,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        hbar.pack(fill="x")
        tk.Label(hbar, text="SETTINGS",
                 font=FB(8), bg=BG, fg=TEXT3
                 ).pack(side="left", padx=24, pady=13)

        frame = self._scroll_frame(parent)

        self._section(frame, "General")
        self._tog(frame, "Run on Windows startup",
                  "Launch ContextOS automatically when PC boots",
                  "run_on_startup")
        self._tog(frame, "Show notifications",
                  "Popup insight cards when conflicts are detected",
                  "show_notifications")
        self._tog(frame, "Smart pause — high CPU",
                  "Pause analysis when CPU exceeds 80%",
                  "smart_pause")

        self._divider(frame)
        self._section(frame, "Features", top=4)
        self._tog(frame, "Auto-update tasks",
                  "Mark Notion/Jira tasks in-progress from file activity",
                  "auto_update_tasks")
        self._tog(frame, "Meeting briefings",
                  "Context summary 5 minutes before meetings",
                  "meeting_briefing")
        self._tog(frame, "Cloud AI mode",
                  "Deeper analysis via cloud — requires internet",
                  "cloud_ai")
        self._tog(frame, "Local only — privacy",
                  "Never send any data outside your PC",
                  "local_only")

        self._divider(frame)
        self._section(frame, "Mode", top=4)
        self._drop(frame, "Analysis mode",
                   "auto = detect automatically    "
                   "lite = rules only    full = local AI",
                   "mode", ["auto", "lite", "full"])

        self._divider(frame)
        self._section(frame, "About", top=4)

        about = tk.Frame(frame, bg=BG2,
                         highlightbackground=BORDER,
                         highlightthickness=1)
        about.pack(fill="x", padx=24, pady=(0, 8))
        ab = tk.Frame(about, bg=BG2)
        ab.pack(fill="x", padx=18, pady=16)

        if "48" in self._imgs:
            tk.Label(ab, image=self._imgs["48"],
                     bg=BG2).pack(side="left", padx=(0, 16))

        abt = tk.Frame(ab, bg=BG2)
        abt.pack(side="left")
        tk.Label(abt, text="ContextOS  v1.0",
                 font=FB(14), bg=BG2, fg=TEXT).pack(anchor="w")
        tk.Label(abt,
                 text="AI-Powered Cross-App Context Bridge for Windows",
                 font=F(10), bg=BG2, fg=TEXT2
                 ).pack(anchor="w", pady=(2, 0))
        tk.Label(abt, text="Developed by SAIPK@support",
                 font=FB(11), bg=BG2, fg=SAIPK
                 ).pack(anchor="w", pady=(6, 2))
        tk.Label(abt,
                 text="IT Tools  •  Web Solutions  •  Support",
                 font=F(9), bg=BG2, fg=TEXT3).pack(anchor="w")
        tk.Label(abt,
                 text="Building Tools. Solving Problems.",
                 font=F(9, "italic"), bg=BG2,
                 fg=TEXT3).pack(anchor="w")

        self._save_lbl = tk.Label(frame, text="",
                                  font=F(9), bg=BG, fg=TEAL)
        self._save_lbl.pack(anchor="w", padx=24, pady=(10, 24))

    def _tog(self, parent, label, sub, key):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=1)
        info = tk.Frame(row, bg=BG)
        info.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(info, text=label, font=F(11),
                 bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=BG, fg=TEXT3).pack(anchor="w")
        var = tk.BooleanVar(value=bool(self.config.get(key, False)))

        def on_change(k=key, v=var):
            self.config.set(k, v.get())
            self._flash()

        tk.Checkbutton(row, variable=var, command=on_change,
                       bg=BG, activebackground=BG,
                       selectcolor=TEAL_BG,
                       fg=TEAL, activeforeground=TEAL,
                       cursor="hand2").pack(side="right", pady=12)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=24)

    def _drop(self, parent, label, sub, key, opts):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=1)
        info = tk.Frame(row, bg=BG)
        info.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(info, text=label, font=F(11),
                 bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=BG, fg=TEXT3).pack(anchor="w")
        var = tk.StringVar(value=str(self.config.get(key, opts[0])))

        def on_change(*_):
            self.config.set(key, var.get())
            self._flash()

        dd = ttk.Combobox(row, textvariable=var,
                          values=opts, state="readonly",
                          width=10, font=F(10))
        dd.pack(side="right", pady=12)
        dd.bind("<<ComboboxSelected>>", on_change)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=24)

    def _flash(self):
        try:
            self._save_lbl.configure(text="✓   Settings saved")
            self.root.after(2200,
                            lambda: self._save_lbl.configure(text=""))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # DATA HELPERS
    # ─────────────────────────────────────────────────────────────────────────
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

    def _focus_topic(self):
        kws  = self.db.get_keywords_last_n_events(n=40)
        freq: dict = {}
        for k in kws:
            if len(k) >= 4:
                freq[k] = freq.get(k, 0) + 1
        if not freq:
            return "No focus detected yet — start working!"
        return max(freq, key=lambda k: freq[k]).title() + " — detected focus"

    def _recent_apps(self):
        evs  = self.db.get_recent_events(limit=60, hours=3)
        seen: list = []
        for e in evs:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return seen

    def _auto_refresh(self):
        def loop():
            while True:
                time.sleep(30)
                try:
                    if (self.root and
                            self.root.winfo_exists() and
                            self._active == "home"):
                        self.root.after(0, lambda: self._switch("home"))
                except Exception:
                    break
        threading.Thread(target=loop, daemon=True).start()
