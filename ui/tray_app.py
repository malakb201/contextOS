"""
ui/tray_app.py  -  System tray + popup windows.
On Windows: real tray icon with pystray.
On other platforms: console simulation mode for testing.
"""
import os, time, logging, threading
logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

try:
    import tkinter as tk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

class TrayApp:
    def __init__(self, config, watcher, engine, detector, session, db):
        self.config   = config
        self.watcher  = watcher
        self.engine   = engine
        self.detector = detector
        self.session  = session
        self.db       = db
        self._snoozed_until = 0
        self._tray_icon     = None

    def run(self):
        self.engine.add_insight_listener(self._on_insight)
        self.session.set_return_listener(self._on_return)
        self.engine.start(self.watcher, self.detector)
        self.session.start()
        if PYSTRAY_AVAILABLE and IS_WINDOWS:
            self._run_tray()
        else:
            self._run_console()

    def stop(self):
        self.engine.stop()
        self.session.stop()
        if self._tray_icon:
            self._tray_icon.stop()

    def _run_tray(self):
        img  = self._make_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._open_dashboard),
            pystray.MenuItem("Snooze 30 min",  self._snooze),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",           self._quit),
        )
        self._tray_icon = pystray.Icon("ContextOS", img,
                                       "ContextOS — watching your apps", menu)
        self._tray_icon.run()

    def _make_icon(self):
        size  = 64
        img   = Image.new("RGBA", (size, size), (0,0,0,0))
        draw  = ImageDraw.Draw(img)
        draw.ellipse([2,2,size-2,size-2], fill=(29,158,117))
        draw.text((20,18), "C", fill=(255,255,255))
        return img

    def _run_console(self):
        print("\n" + "="*55)
        print("  ContextOS  —  Console Mode")
        print("  (On Windows install pystray+pillow for real tray icon)")
        print("="*55)
        print("  Commands:  d=dashboard  i=insights  s=snooze  q=quit\n")

        def print_ins(ins):
            icon = {"conflict":"[!]","answer":"[?]","auto_update":"[v]"}.get(ins.insight_type,"[ ]")
            print(f"\n  {icon} {ins.insight_type.upper()}: {ins.title}")
            print(f"      {ins.detail[:80]}")
            print(f"      Apps: {ins.source_apps}\n")

        self.engine.add_insight_listener(print_ins)
        try:
            while True:
                cmd = input("ContextOS> ").strip().lower()
                if   cmd == "q": break
                elif cmd == "d": self._print_stats()
                elif cmd == "i": self._print_insights()
                elif cmd == "s": self._snooze(); print("  Snoozed 30 min.")
                else:            print("  Use: d / i / s / q")
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.stop()

    def _on_insight(self, insight):
        if time.time() < self._snoozed_until:
            return
        if TK_AVAILABLE and IS_WINDOWS:
            threading.Thread(target=self._popup, args=(insight,), daemon=True).start()

    def _on_return(self, resume_data):
        away = resume_data.get("away_minutes", 0)
        print(f"\n  Welcome back! Away for {away} minutes.")
        for c in resume_data.get("changes", []):
            print(f"  * {c['type'].upper()}: {c['title']}")
        print()

    def _popup(self, insight):
        root = tk.Tk()
        root.title("ContextOS")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#ffffff")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"360x140+{sw-380}+{sh-180}")
        hf = tk.Frame(root, bg="#f8f8f6", pady=6, padx=12)
        hf.pack(fill="x")
        tk.Label(hf, text="* ContextOS", font=("Segoe UI",10,"bold"),
                 bg="#f8f8f6", fg="#1D9E75").pack(side="left")
        tk.Label(root, text=insight.title, font=("Segoe UI",10,"bold"),
                 bg="#ffffff", fg="#1a1a1a", wraplength=320,
                 justify="left", padx=12, pady=6).pack(fill="x")
        tk.Label(root, text=insight.detail[:90], font=("Segoe UI",9),
                 bg="#ffffff", fg="#555", wraplength=320,
                 justify="left", padx=12).pack(fill="x")
        bf = tk.Frame(root, bg="#ffffff", pady=8, padx=12)
        bf.pack(fill="x")
        tk.Button(bf, text="Dismiss", font=("Segoe UI",9), command=root.destroy,
                  relief="flat", bg="#f0f0f0", fg="#333", padx=10).pack(side="right", padx=4)
        root.after(8000, root.destroy)
        root.mainloop()

    def _open_dashboard(self, *a):
        logger.info("Dashboard requested.")

    def _print_stats(self):
        s = self.engine.get_stats()
        print(f"\n  Insights today:   {s['insights_today']}")
        print(f"  Conflicts caught: {s['conflicts_caught']}")
        print(f"  Tasks auto-done:  {s['tasks_auto_done']}")
        print(f"  Focus time:       {s['focus_minutes']} min\n")

    def _print_insights(self):
        ins = self.db.get_active_insights(limit=5)
        if not ins:
            print("  No active insights.")
            return
        for i in ins:
            print(f"  [{i['insight_type'].upper()}] {i['title']}")
        print()

    def _snooze(self, *a):
        self._snoozed_until = time.time() + 1800

    def _quit(self, *a):
        self.stop()
