"""
core/app_watcher.py  -  Watches which app is active every second.
On Windows uses win32gui. On other platforms uses simulation mode.
"""
import os, re, time, logging, threading
from typing import Callable

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    try:
        import win32gui, win32process, psutil
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("pywin32 not installed. Run: pip install pywin32 psutil")
else:
    WIN32_AVAILABLE = False

STOPWORDS = {
    "the","a","an","and","or","in","on","at","to","for","of","with",
    "is","was","are","be","by","from","as","new","tab","page","window",
    "file","untitled","microsoft","google","app","exe","com","www",
    "http","https",
}

class AppEvent:
    def __init__(self, app_name, window_title, file_name=None, keywords=None):
        self.app_name     = app_name
        self.window_title = window_title
        self.file_name    = file_name
        self.keywords     = keywords or []
    def __repr__(self):
        return f"AppEvent(app={self.app_name!r}, title={self.window_title!r})"

class AppWatcher:
    def __init__(self, config, db):
        self.config          = config
        self.db              = db
        self._running        = False
        self._thread         = None
        self._paused         = False
        self._listeners: list[Callable] = []
        self._last_title     = ""
        self._last_app       = ""
        self.events_recorded = 0

    def add_listener(self, fn):
        self._listeners.append(fn)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, name="AppWatcher", daemon=True)
        self._thread.start()
        logger.info("AppWatcher started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def get_current_app(self):
        return self._read()

    def _loop(self):
        interval = float(self.config.get("watch_interval", 1.0))
        while self._running:
            try:
                if not self._paused:
                    self._tick()
            except Exception as e:
                logger.error(f"AppWatcher tick error: {e}")
            time.sleep(interval)

    def _tick(self):
        event = self._read()
        if event is None:
            return
        if event.window_title == self._last_title and event.app_name == self._last_app:
            return
        self._last_title = event.window_title
        self._last_app   = event.app_name
        self.db.add_event(
            app_name=event.app_name, window_title=event.window_title,
            event_type="app_switch", file_name=event.file_name,
            keywords=",".join(event.keywords), raw_text=event.window_title,
        )
        self.events_recorded += 1
        for fn in self._listeners:
            try:
                fn(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def _read(self):
        if IS_WINDOWS and WIN32_AVAILABLE:
            return self._read_windows()
        return self._read_simulation()

    def _read_windows(self):
        try:
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                exe_name = psutil.Process(pid).name()
            except Exception:
                exe_name = "Unknown"
            app_name  = self._friendly(exe_name, title)
            return AppEvent(app_name, title, self._fname(title), self._kws(title))
        except Exception as e:
            logger.debug(f"win32gui error: {e}")
            return None

    def _read_simulation(self):
        import random
        samples = [
            ("VS Code", "AuthService.ts — contextOS — Visual Studio Code", "AuthService.ts"),
            ("Chrome",  "Stack Overflow — NullPointerException Python",     None),
            ("Slack",   "#dev-mobile — Ahmed: fixed the checkout bug",      None),
            ("Notion",  "Sprint 3 — Mobile App Redesign",                   None),
            ("Gmail",   "Sara: Important — auth flow must not change",      None),
            ("Figma",   "Login_v4 — Mobile App Redesign",                   None),
            ("VS Code", "main.py — contextOS — Visual Studio Code",         "main.py"),
        ]
        app, title, fname = random.choice(samples)
        return AppEvent(app, title, fname, self._kws(title))

    def _friendly(self, exe, title):
        m = {"code.exe":"VS Code","chrome.exe":"Chrome","firefox.exe":"Firefox",
             "msedge.exe":"Edge","slack.exe":"Slack","teams.exe":"Teams",
             "outlook.exe":"Outlook","notion.exe":"Notion","figma.exe":"Figma",
             "notepad.exe":"Notepad","explorer.exe":"File Explorer"}
        return m.get(exe.lower(), exe.replace(".exe","").title())

    def _fname(self, title):
        m = re.search(
            r"\b([\w\-]+\.(ts|js|py|cs|java|cpp|h|html|css|json|md|txt|yml|yaml|xml|go|rs))\b",
            title, re.IGNORECASE)
        return m.group(1) if m else None

    def _kws(self, text):
        words = re.split(r"[^a-zA-Z0-9_]+", text)
        seen, result = set(), []
        for w in words:
            w = w.lower().strip("_")
            if len(w) >= 3 and w not in STOPWORDS and w not in seen:
                seen.add(w)
                result.append(w)
        return result[:15]

    def is_watched_app(self, app_name):
        watched = self.config.get("watched_apps", [])
        return any(w.lower() in app_name.lower() for w in watched)
