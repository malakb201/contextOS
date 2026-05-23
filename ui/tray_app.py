"""
ui/tray_app.py
Real system tray app with pystray on Windows.
Console simulation on non-Windows.
"""
import os, time, logging, threading
logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

try:
    import tkinter as tk
    from tkinter import ttk
    TK_OK = True
except ImportError:
    TK_OK = False

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    PYSTRAY_OK = True
except ImportError:
    PYSTRAY_OK = False
    logger.warning("pystray/Pillow not installed. Run: python install_deps.py")


class TrayApp:
    def __init__(self, config, watcher, engine, detector, session, db):
        self.config      = config
        self.watcher     = watcher
        self.engine      = engine
        self.detector    = detector
        self.session     = session
        self.db          = db
        self._snoozed      = 0
        self._icon         = None
        self._pending: list = []
        self._popup_queue: list = []
        self._tk_root      = None

    def run(self):
        self.engine.add_insight_listener(self._on_insight)
        self.session.set_return_listener(self._on_return)

        # Wire meeting monitor if available
        try:
            from core.meeting_monitor import MeetingMonitor
            self._meeting_mon = MeetingMonitor(
                self.config, self.db, self.watcher)
            self._meeting_mon.add_briefing_callback(self._on_meeting_briefing)
            self._meeting_mon.start()
        except Exception as e:
            logger.debug(f"Meeting monitor not started: {e}")

        self.engine.start(self.watcher, self.detector)
        self.session.start()

        # Handle startup setting
        if self.config.get("run_on_startup", True):
            try:
                from core.startup_manager import add_to_startup, is_in_startup
                if not is_in_startup():
                    add_to_startup()
            except Exception:
                pass

        if PYSTRAY_OK and IS_WINDOWS:
            # Start popup processor in background thread
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
            self._meeting_mon.stop()
        except Exception:
            pass
        if self._icon:
            self._icon.stop()

    # ── Real Windows tray ──────────────────────────────────────────────────────

    def _run_tray(self):
        icon_img = self._make_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard",   self._open_dashboard),
            pystray.MenuItem("Add Meeting",       self._add_meeting_dialog),
            pystray.MenuItem("Snooze 30 min",     self._snooze),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings",          self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit ContextOS",    self._quit),
        )
        self._icon = pystray.Icon(
            "ContextOS", icon_img,
            "ContextOS — watching your apps", menu)
        self._icon.run()

    def _make_icon(self) -> "Image":
        size  = 64
        img   = Image.new("RGBA", (size, size), (0,0,0,0))
        draw  = ImageDraw.Draw(img)
        # Dark circle background
        draw.ellipse([2,2,size-2,size-2], fill=(20,20,20,240))
        # Teal ring
        draw.ellipse([4,4,size-4,size-4], outline=(29,158,117,255), width=3)
        # White C
        draw.ellipse([18,18,46,46], fill=(29,158,117,255))
        draw.ellipse([22,22,42,42], fill=(20,20,20,255))
        draw.rectangle([30,22,46,42], fill=(20,20,20,255))
        return img

    # ── Console simulation ─────────────────────────────────────────────────────

    def _run_console(self):
        print("\n" + "═"*58)
        print("  ContextOS  —  Running")
        if not (IS_WINDOWS and PYSTRAY_OK):
            print("  Install deps for real tray: python install_deps.py")
        print("═"*58)
        print("  d = dashboard   i = insights   a = add meeting")
        print("  s = snooze 30m  q = quit\n")

        def show(ins):
            icons = {"conflict":"⚠ ","answer":"💡","auto_update":"✓ ","meeting_prep":"📅"}
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

    # ── Insight handling ───────────────────────────────────────────────────────

    def _on_insight(self, insight):
        if time.time() < self._snoozed:
            return
        self._pending.append(insight)
        # Update tray icon tooltip
        if self._icon:
            count = len(self.db.get_active_insights())
            self._icon.title = (
                f"ContextOS — {count} insight{'s' if count!=1 else ''}")
        # Queue popup for main thread
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
                print(f"     • {ev.get('app_name')}: {ev.get('window_title','')[:50]}")
            print()

    def _process_popup_queue(self):
        """Process popup queue — each popup gets its own tkinter instance."""
        while True:
            time.sleep(0.5)
            if not self._popup_queue:
                continue
            try:
                kind, data = self._popup_queue.pop(0)
                if kind == "insight":
                    self._show_insight_popup(data)
                elif kind == "resume":
                    self._show_resume_popup(data)
                elif kind == "meeting":
                    self._show_meeting_popup(data)
                time.sleep(1)  # Small gap between popups
            except Exception as e:
                logger.error(f"Popup queue error: {e}")

    # ── Tkinter popups ────────────────────────────────────────────────────────

    def _show_insight_popup(self, insight):
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#161616")

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 360, 155
        root.geometry(f"{w}x{h}+{sw-w-16}+{sh-h-52}")

        # Colour by type
        colours = {
            "conflict":    ("#BA7517","#faeeda","#633806"),
            "answer":      ("#185FA5","#e6f1fb","#0C447C"),
            "auto_update": ("#1D9E75","#e1f5ee","#085041"),
            "meeting_prep":("#534AB7","#eeedfe","#3C3489"),
        }
        accent, bg_l, fg_d = colours.get(
            insight.insight_type, ("#555","#eee","#333"))

        # Header
        hf = tk.Frame(root, bg="#1e1e1e")
        hf.pack(fill="x")
        tk.Label(hf, text="● ContextOS", font=("Segoe UI",9,"bold"),
                 bg="#1e1e1e", fg="#1D9E75",
                 padx=10, pady=6).pack(side="left")
        badge_txt = insight.insight_type.replace("_"," ").title()
        tk.Label(hf, text=badge_txt, font=("Segoe UI",8),
                 bg=bg_l, fg=fg_d,
                 padx=6, pady=2).pack(side="right", padx=8, pady=4)

        # Colour stripe
        tk.Frame(root, bg=accent, height=2).pack(fill="x")

        # Body
        bf = tk.Frame(root, bg="#161616")
        bf.pack(fill="both", expand=True, padx=12, pady=8)
        tk.Label(bf, text=insight.title, font=("Segoe UI",10,"bold"),
                 bg="#161616", fg="#f0efe8",
                 wraplength=330, justify="left", anchor="w"
                 ).pack(fill="x", pady=(0,4))
        short = insight.detail[:85] + ("…" if len(insight.detail)>85 else "")
        tk.Label(bf, text=short, font=("Segoe UI",9),
                 bg="#161616", fg="#999890",
                 wraplength=330, justify="left", anchor="w"
                 ).pack(fill="x")

        # Buttons
        btf = tk.Frame(root, bg="#161616")
        btf.pack(fill="x", padx=12, pady=(0,10))
        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI",9),
                  bg="#222", fg="#999", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [
                      self.db.dismiss_insight(insight.id) if insight.id else None,
                      root.destroy()
                  ]).pack(side="right", padx=(4,0))
        tk.Button(btf, text="Open Dashboard",
                  font=("Segoe UI",9),
                  bg=accent, fg="white", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [root.destroy(), self._open_dashboard()]
                  ).pack(side="right")

        root.after(9000, root.destroy)
        root.mainloop()

    def _show_meeting_popup(self, briefing):
        root = tk.Tk()
        root.title("ContextOS — Meeting Briefing")
        root.geometry("440x320")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0e0e0e")

        tk.Label(root,
                 text=f"📅  Meeting in {briefing['minutes_until']} minutes",
                 font=("Segoe UI",12,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=14
                 ).pack()

        tk.Label(root,
                 text=briefing["meeting_title"],
                 font=("Segoe UI",14,"bold"),
                 bg="#0e0e0e", fg="#1D9E75"
                 ).pack()

        tk.Frame(root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        tk.Label(root, text="What ContextOS found — relevant to this meeting:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#555550"
                 ).pack(anchor="w", padx=20)

        for ev in briefing.get("relevant_events", [])[:4]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=2)
            txt = f"[{ev.get('app_name','')}]  {(ev.get('window_title',''))[:52]}"
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=4)

        tk.Frame(root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        btf = tk.Frame(root, bg="#0e0e0e")
        btf.pack()
        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI",10),
                  bg="#1a1a1a", fg="#999", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=root.destroy
                  ).pack(side="left", padx=4)
        tk.Button(btf, text="Open Dashboard",
                  font=("Segoe UI",10),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=lambda: [root.destroy(), self._open_dashboard()]
                  ).pack(side="left", padx=4)
        root.mainloop()

    def _show_resume_popup(self, resume_data):
        root = tk.Tk()
        root.title("ContextOS — Welcome back")
        root.geometry("420x280")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0e0e0e")

        away = resume_data.get("away_minutes", 0)
        tk.Label(root,
                 text=f"Welcome back — away {away} minutes",
                 font=("Segoe UI",12,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=14
                 ).pack()
        tk.Label(root,
                 text="ContextOS rebuilt your context:",
                 font=("Segoe UI",9), bg="#0e0e0e", fg="#555550"
                 ).pack()

        for item in resume_data.get("restore_items", [])[:3]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=3)
            txt = f"[{item['app']}]  {item['title'][:48]}"
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=5)

        changes = resume_data.get("changes", [])
        if changes:
            tk.Label(root,
                     text=f"{len(changes)} update(s) while you were away",
                     font=("Segoe UI",9), bg="#0e0e0e", fg="#1D9E75"
                     ).pack(pady=4)

        tk.Button(root, text="Got it",
                  font=("Segoe UI",11),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=24, pady=8, cursor="hand2",
                  command=root.destroy
                  ).pack(pady=10)
        root.mainloop()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _open_dashboard(self, *_):
        try:
            from ui.dashboard import Dashboard
            threading.Thread(
                target=lambda: Dashboard(
                    self.config, self.db, self.engine).show(),
                daemon=True).start()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    def _open_settings(self, *_):
        self._open_dashboard()

    def _add_meeting_dialog(self, *_):
        if TK_OK and IS_WINDOWS:
            threading.Thread(target=self._meeting_input_window,
                             daemon=True).start()

    def _meeting_input_window(self):
        root = tk.Tk()
        root.title("Add Meeting")
        root.geometry("300x160")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#111")

        tk.Label(root, text="Meeting title:",
                 font=("Segoe UI",10), bg="#111", fg="#f0efe8"
                 ).pack(pady=(14,4))
        title_var = tk.StringVar()
        tk.Entry(root, textvariable=title_var, font=("Segoe UI",10),
                 width=28, bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5)

        tk.Label(root, text="Minutes from now:",
                 font=("Segoe UI",10), bg="#111", fg="#f0efe8"
                 ).pack(pady=(8,2))
        mins_var = tk.StringVar(value="5")
        tk.Entry(root, textvariable=mins_var, font=("Segoe UI",10),
                 width=8, bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5)

        def add():
            t = title_var.get().strip()
            m = int(mins_var.get().strip() or "5")
            if t:
                try:
                    self._meeting_mon.add_manual_meeting(t, m)
                except Exception:
                    pass
            root.destroy()

        tk.Button(root, text="Add Meeting",
                  font=("Segoe UI",10),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=add).pack(pady=10)
        root.mainloop()

    def _add_meeting_console(self):
        title = input("  Meeting title: ").strip()
        mins  = input("  Minutes from now [5]: ").strip()
        mins  = int(mins) if mins.isdigit() else 5
        if title:
            try:
                self._meeting_mon.add_manual_meeting(title, mins)
                print(f"  Meeting '{title}' added — briefing in {mins} min.")
            except Exception as e:
                print(f"  Error: {e}")

    def _snooze(self, *_):
        self._snoozed = time.time() + 1800
        logger.info("Snoozed 30 min.")

    def _quit(self, *_):
        self.stop()

    # ── Console helpers ───────────────────────────────────────────────────────

    def _print_dashboard(self):
        s = self.engine.get_stats()
        print(f"\n  ── Today's stats ──────────────────────")
        print(f"  Insights fired:   {s['insights_today']}")
        print(f"  Conflicts caught: {s['conflicts_caught']}")
        print(f"  Tasks auto-done:  {s['tasks_auto_done']}")
        print(f"  Focus time:       {s['focus_minutes']} min")
        apps = self.watcher.get_all_seen_apps()
        if apps:
            print(f"  Apps seen today:  {', '.join(apps[:6])}")
        print()

    def _print_insights(self):
        ins = self.db.get_active_insights(limit=5)
        if not ins:
            print("  No active insights.\n")
            return
        print(f"\n  ── {len(ins)} Active Insight(s) ──────────────")
        for i in ins:
            print(f"  [{i['insight_type'].upper()[:4]}] {i['title']}")
        print()