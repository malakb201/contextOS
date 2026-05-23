"""
ui/tray_app.py
Real system tray app — SAIPK@support branding
Real pystray icon using SAIPK logo.
"""
import os, time, logging, threading, queue
logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH  = os.path.join(BASE_DIR, "assets", "icons", "contextOS.ico")
LOGO_PATH  = os.path.join(BASE_DIR, "assets", "icons", "logo_64.png")

try:
    import tkinter as tk
    from tkinter import ttk
    TK_OK = True
except ImportError:
    TK_OK = False

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_OK = True
except ImportError:
    PYSTRAY_OK = False
    logger.warning("pystray/Pillow not installed. Run: python install_deps.py")


def load_icon_image():
    """Load SAIPK logo for tray — fallback to generated icon."""
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).convert("RGBA")
            img = img.resize((64, 64), Image.LANCZOS)
            return img
    except Exception:
        pass
    # Fallback: generate teal C icon
    size = 64
    img  = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2,2,size-2,size-2], fill=(20,20,20,240))
    draw.ellipse([4,4,size-4,size-4], outline=(29,158,117,255), width=3)
    draw.ellipse([18,18,46,46], fill=(29,158,117,255))
    draw.ellipse([22,22,42,42], fill=(20,20,20,255))
    draw.rectangle([30,22,46,42], fill=(20,20,20,255))
    return img


class TrayApp:
    def __init__(self, config, watcher, engine, detector, session, db):
        self.config        = config
        self.watcher       = watcher
        self.engine        = engine
        self.detector      = detector
        self.session       = session
        self.db            = db
        self._snoozed      = 0
        self._icon         = None
        self._pending: list = []
        self._popup_queue: list = []
        self._tk_root      = None
        self._meeting_mon  = None

    def run(self):
        self.engine.add_insight_listener(self._on_insight)
        self.session.set_return_listener(self._on_return)

        # Meeting monitor
        try:
            from core.meeting_monitor import MeetingMonitor
            self._meeting_mon = MeetingMonitor(
                self.config, self.db, self.watcher)
            self._meeting_mon.add_briefing_callback(self._on_meeting_briefing)
            self._meeting_mon.start()
        except Exception as e:
            logger.debug(f"Meeting monitor: {e}")

        self.engine.start(self.watcher, self.detector)
        self.session.start()

        # Startup registry
        if self.config.get("run_on_startup", True):
            try:
                from core.startup_manager import add_to_startup, is_in_startup
                if not is_in_startup():
                    add_to_startup()
            except Exception:
                pass

        if PYSTRAY_OK and IS_WINDOWS:
            threading.Thread(
                target=self._process_popup_queue,
                name="PopupProcessor", daemon=True).start()
            self._run_tray()
        else:
            self._run_console()

    def stop(self):
        self.engine.stop()
        self.session.stop()
        try:
            if self._meeting_mon:
                self._meeting_mon.stop()
        except Exception:
            pass
        if self._icon:
            self._icon.stop()

    # ── Real Windows tray ──────────────────────────────────────────────────────

    def _run_tray(self):
        icon_img = load_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard",    self._open_dashboard),
            pystray.MenuItem("Add Meeting",        self._add_meeting_dialog),
            pystray.MenuItem("Snooze 30 min",      self._snooze),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings",           self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Developed by SAIPK@support", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit ContextOS",     self._quit),
        )
        self._icon = pystray.Icon(
            "ContextOS", icon_img,
            "ContextOS — SAIPK@support", menu)
        self._icon.run()

    # ── Console simulation ─────────────────────────────────────────────────────

    def _run_console(self):
        print("\n" + "═"*58)
        print("  ContextOS  —  AI-Powered Context Bridge")
        print("  Developed by SAIPK@support")
        if not (IS_WINDOWS and PYSTRAY_OK):
            print("  Run: python install_deps.py  for real tray icon")
        print("═"*58)
        print("  d=dashboard  i=insights  a=add meeting  s=snooze  q=quit\n")

        def show(ins):
            icons = {
                "conflict":    "⚠ ",
                "answer":      "💡",
                "auto_update": "✓ ",
                "meeting_prep":"📅"
            }
            ic = icons.get(ins.insight_type, "• ")
            print(f"\n  {ic} [{ins.insight_type.upper()}]")
            print(f"     {ins.title}")
            print(f"     {ins.detail[:80]}")
            print(f"     Apps: {ins.source_apps}\n")

        self.engine.add_insight_listener(show)
        try:
            while True:
                cmd = input("ContextOS> ").strip().lower()
                if   cmd == "q": break
                elif cmd == "d": self._print_dashboard()
                elif cmd == "i": self._print_insights()
                elif cmd == "s": self._snooze(); print("  Snoozed 30 min.")
                elif cmd == "a": self._add_meeting_console()
                else: print("  Commands: d / i / a / s / q")
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.stop()

    # ── Insight / event handlers ───────────────────────────────────────────────

    def _on_insight(self, insight):
        if time.time() < self._snoozed:
            return
        self._pending.append(insight)
        if self._icon:
            count = len(self.db.get_active_insights())
            self._icon.title = (
                f"ContextOS — {count} insight{'s' if count!=1 else ''}")
        if TK_OK and IS_WINDOWS:
            self._popup_queue.append(("insight", insight))

    def _on_return(self, resume_data):
        away = resume_data.get("away_minutes", 0)
        if TK_OK and IS_WINDOWS:
            self._popup_queue.append(("resume", resume_data))
        else:
            print(f"\n  Welcome back! Away {away} min.")
            for c in resume_data.get("changes", []):
                print(f"  • {c['type'].upper()}: {c['title']}")
            print()

    def _on_meeting_briefing(self, briefing):
        title = briefing.get("meeting_title", "Meeting")
        mins  = briefing.get("minutes_until", 5)
        if TK_OK and IS_WINDOWS:
            self._popup_queue.append(("meeting", briefing))
        else:
            print(f"\n  MEETING IN {mins} MIN: {title}")
            for ev in briefing.get("relevant_events", [])[:3]:
                print(f"     • {ev.get('app_name')}: "
                      f"{ev.get('window_title','')[:50]}")
            print()

    # ── Popup queue processor ──────────────────────────────────────────────────

    def _process_popup_queue(self):
        """Process popups one at a time — no threading conflicts."""
        while True:
            time.sleep(0.5)
            if not self._popup_queue:
                continue
            try:
                kind, data = self._popup_queue.pop(0)
                if   kind == "insight": self._show_insight_popup(data)
                elif kind == "resume":  self._show_resume_popup(data)
                elif kind == "meeting": self._show_meeting_popup(data)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Popup error: {e}")

    # ── Tkinter popup windows ─────────────────────────────────────────────────

    def _make_root(self, title, w, h, topmost=True):
        """Create a styled tkinter window."""
        root = tk.Tk()
        root.title(title)
        root.resizable(False, False)
        root.configure(bg="#0e0e0e")
        root.attributes("-topmost", topmost)
        # Set SAIPK icon
        try:
            if os.path.exists(ICON_PATH):
                root.iconbitmap(ICON_PATH)
        except Exception:
            pass
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - w - 16
        y  = sh - h - 52
        root.geometry(f"{w}x{h}+{x}+{y}")
        return root

    def _show_insight_popup(self, insight):
        colours = {
            "conflict":    ("#BA7517", "#2a1a00", "#f0a832"),
            "answer":      ("#185FA5", "#00102a", "#6aabf7"),
            "auto_update": ("#1D9E75", "#001a12", "#0dcfaa"),
            "meeting_prep":("#534AB7", "#0d0b2a", "#9b95e8"),
        }
        accent, bg_dark, fg_bright = colours.get(
            insight.insight_type, ("#555","#111","#ccc"))

        root = self._make_root("ContextOS", 370, 170)

        # Top stripe
        tk.Frame(root, bg=accent, height=3).pack(fill="x")

        # Header
        hf = tk.Frame(root, bg="#151515")
        hf.pack(fill="x")

        # SAIPK logo in header
        try:
            logo_img = Image.open(LOGO_PATH).resize((22,22), Image.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(logo_img)
            lbl = tk.Label(hf, image=logo_tk, bg="#151515")
            lbl.image = logo_tk
            lbl.pack(side="left", padx=(10,4), pady=5)
        except Exception:
            tk.Label(hf, text="●", font=("Segoe UI",10),
                     bg="#151515", fg="#1D9E75",
                     padx=10, pady=5).pack(side="left")

        tk.Label(hf, text="ContextOS",
                 font=("Segoe UI", 9, "bold"),
                 bg="#151515", fg="#f0efe8").pack(side="left")

        badge = insight.insight_type.replace("_"," ").title()
        tk.Label(hf, text=badge, font=("Segoe UI", 8),
                 bg=bg_dark, fg=fg_bright,
                 padx=6, pady=2).pack(side="right", padx=8, pady=4)

        # Body
        bf = tk.Frame(root, bg="#0e0e0e")
        bf.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(bf, text=insight.title,
                 font=("Segoe UI", 10, "bold"),
                 bg="#0e0e0e", fg="#f0efe8",
                 wraplength=340, justify="left", anchor="w"
                 ).pack(fill="x", pady=(0,4))

        short = insight.detail[:90] + ("…" if len(insight.detail)>90 else "")
        tk.Label(bf, text=short,
                 font=("Segoe UI", 9),
                 bg="#0e0e0e", fg="#999890",
                 wraplength=340, justify="left", anchor="w"
                 ).pack(fill="x")

        # Buttons
        btf = tk.Frame(root, bg="#0e0e0e")
        btf.pack(fill="x", padx=12, pady=(0,8))

        tk.Label(btf, text="SAIPK@support",
                 font=("Segoe UI", 7),
                 bg="#0e0e0e", fg="#333330").pack(side="left")

        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI", 9),
                  bg="#1e1e1e", fg="#999890", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [
                      self.db.dismiss_insight(insight.id) if insight.id else None,
                      root.destroy()
                  ]).pack(side="right", padx=(4,0))

        tk.Button(btf, text="Dashboard",
                  font=("Segoe UI", 9),
                  bg=accent, fg="white", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [root.destroy(),
                                   self._open_dashboard()]
                  ).pack(side="right")

        root.after(9000, root.destroy)
        root.mainloop()

    def _show_meeting_popup(self, briefing):
        root = self._make_root("ContextOS — Meeting Briefing", 440, 300)

        tk.Frame(root, bg="#534AB7", height=3).pack(fill="x")

        # Header with logo
        hf = tk.Frame(root, bg="#111")
        hf.pack(fill="x", pady=0)
        try:
            logo_img = Image.open(LOGO_PATH).resize((28,28), Image.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(logo_img)
            lbl = tk.Label(hf, image=logo_tk, bg="#111")
            lbl.image = logo_tk
            lbl.pack(side="left", padx=10, pady=8)
        except Exception:
            pass
        tk.Label(hf, text="ContextOS — Meeting Briefing",
                 font=("Segoe UI",10,"bold"),
                 bg="#111", fg="#f0efe8").pack(side="left")

        mins  = briefing.get("minutes_until", 5)
        title = briefing.get("meeting_title","Meeting")

        tk.Label(root, text=f"📅  Meeting in {mins} minutes",
                 font=("Segoe UI",11,"bold"),
                 bg="#0e0e0e", fg="#9b95e8", pady=8).pack()

        tk.Label(root, text=title,
                 font=("Segoe UI",13,"bold"),
                 bg="#0e0e0e", fg="#f0efe8").pack()

        tk.Frame(root, bg="#222", height=1).pack(fill="x", padx=20, pady=10)

        tk.Label(root,
                 text="Relevant context from your apps:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#55544f").pack(anchor="w", padx=20)

        for ev in briefing.get("relevant_events",[])[:3]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=2)
            txt = (f"[{ev.get('app_name','')}]  "
                   f"{ev.get('window_title','')[:50]}")
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=4)

        btf = tk.Frame(root, bg="#0e0e0e")
        btf.pack(pady=10)
        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI",10),
                  bg="#1a1a1a", fg="#999", relief="flat",
                  padx=14, pady=6, cursor="hand2",
                  command=root.destroy).pack(side="left", padx=4)
        tk.Button(btf, text="Open Dashboard",
                  font=("Segoe UI",10),
                  bg="#534AB7", fg="white", relief="flat",
                  padx=14, pady=6, cursor="hand2",
                  command=lambda: [root.destroy(),
                                   self._open_dashboard()]
                  ).pack(side="left", padx=4)

        tk.Label(root, text="Developed by SAIPK@support",
                 font=("Segoe UI",7),
                 bg="#0e0e0e", fg="#2a2a2a").pack(pady=(0,4))
        root.mainloop()

    def _show_resume_popup(self, resume_data):
        root = self._make_root("ContextOS — Welcome back", 420, 260)

        tk.Frame(root, bg="#1D9E75", height=3).pack(fill="x")

        hf = tk.Frame(root, bg="#111")
        hf.pack(fill="x")
        try:
            logo_img = Image.open(LOGO_PATH).resize((28,28), Image.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(logo_img)
            lbl = tk.Label(hf, image=logo_tk, bg="#111")
            lbl.image = logo_tk
            lbl.pack(side="left", padx=10, pady=8)
        except Exception:
            pass
        tk.Label(hf, text="ContextOS",
                 font=("Segoe UI",10,"bold"),
                 bg="#111", fg="#f0efe8").pack(side="left")

        away = resume_data.get("away_minutes", 0)
        tk.Label(root,
                 text=f"Welcome back — away {away} minutes",
                 font=("Segoe UI",12,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=10).pack()

        tk.Label(root, text="Your context has been restored:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#55544f").pack()

        for item in resume_data.get("restore_items",[])[:3]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=2)
            txt = f"[{item['app']}]  {item['title'][:46]}"
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=4)

        changes = resume_data.get("changes",[])
        if changes:
            tk.Label(root,
                     text=f"{len(changes)} update(s) while you were away",
                     font=("Segoe UI",9),
                     bg="#0e0e0e", fg="#0dcfaa").pack(pady=4)

        tk.Button(root, text="Got it",
                  font=("Segoe UI",11),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=24, pady=8, cursor="hand2",
                  command=root.destroy).pack(pady=6)

        tk.Label(root, text="Developed by SAIPK@support",
                 font=("Segoe UI",7),
                 bg="#0e0e0e", fg="#2a2a2a").pack()
        root.mainloop()

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _open_dashboard(self, *_):
        try:
            from ui.dashboard import Dashboard
            threading.Thread(
                target=lambda: Dashboard(
                    self.config, self.db, self.engine).show(),
                name="Dashboard", daemon=True).start()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    def _open_settings(self, *_):
        self._open_dashboard()

    # ── Meeting input ──────────────────────────────────────────────────────────

    def _add_meeting_dialog(self, *_):
        if TK_OK and IS_WINDOWS:
            threading.Thread(
                target=self._meeting_input_window, daemon=True).start()

    def _meeting_input_window(self):
        root = tk.Tk()
        root.title("Add Meeting — ContextOS")
        root.geometry("320x180")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0e0e0e")
        try:
            if os.path.exists(ICON_PATH):
                root.iconbitmap(ICON_PATH)
        except Exception:
            pass

        tk.Frame(root, bg="#1D9E75", height=3).pack(fill="x")
        tk.Label(root, text="Add Meeting",
                 font=("Segoe UI",11,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=10).pack()

        tk.Label(root, text="Meeting title:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#999890").pack()
        title_var = tk.StringVar()
        tk.Entry(root, textvariable=title_var,
                 font=("Segoe UI",10), width=28,
                 bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5, pady=2)

        tk.Label(root, text="Minutes from now:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#999890").pack()
        mins_var = tk.StringVar(value="5")
        tk.Entry(root, textvariable=mins_var,
                 font=("Segoe UI",10), width=8,
                 bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5, pady=2)

        def add():
            t = title_var.get().strip()
            m = int(mins_var.get().strip() or "5")
            if t and self._meeting_mon:
                try:
                    self._meeting_mon.add_manual_meeting(t, m)
                except Exception:
                    pass
            root.destroy()

        tk.Button(root, text="Add Meeting",
                  font=("Segoe UI",10),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=add).pack(pady=8)
        root.mainloop()

    def _add_meeting_console(self):
        title = input("  Meeting title: ").strip()
        mins  = input("  Minutes from now [5]: ").strip()
        mins  = int(mins) if mins.isdigit() else 5
        if title and self._meeting_mon:
            try:
                self._meeting_mon.add_manual_meeting(title, mins)
                print(f"  Meeting '{title}' added — briefing in {mins} min.")
            except Exception as e:
                print(f"  Error: {e}")

    # ── Snooze / Quit ──────────────────────────────────────────────────────────

    def _snooze(self, *_):
        self._snoozed = time.time() + 1800
        logger.info("Snoozed 30 min.")

    def _quit(self, *_):
        logger.info("User quit.")
        self.stop()

    # ── Console helpers ────────────────────────────────────────────────────────

    def _print_dashboard(self):
        s = self.engine.get_stats()
        print(f"\n  ── Today ──────────────────────────────")
        print(f"  Insights:  {s['insights_today']}")
        print(f"  Conflicts: {s['conflicts_caught']}")
        print(f"  Auto-done: {s['tasks_auto_done']}")
        print(f"  Focus:     {s['focus_minutes']} min")
        apps = self.watcher.get_all_seen_apps()
        if apps:
            print(f"  Apps:      {', '.join(apps[:6])}")
        print()

    def _print_insights(self):
        ins = self.db.get_active_insights(limit=5)
        if not ins:
            print("  No active insights.\n")
            return
        print(f"\n  ── {len(ins)} Insight(s) ──────────────────")
        for i in ins:
            print(f"  [{i['insight_type'].upper()[:4]}] {i['title']}")
        print()
