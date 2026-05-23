"""
core/app_watcher.py
Watches the active Windows window every second using win32gui.
Works on ALL installed apps — not just a fixed list.
On non-Windows (dev), runs simulation mode.
"""
import os, re, time, logging, threading
from typing import Callable, Optional
from core.app_reader import AppReader, ParsedContext

logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    try:
        import win32gui, win32process, psutil
        WIN32_OK = True
    except ImportError:
        WIN32_OK = False
        logger.warning("pywin32/psutil not installed. Run: python install_deps.py")
else:
    WIN32_OK = False


class AppEvent:
    """One context snapshot — active window at a point in time."""
    def __init__(self, ctx: ParsedContext):
        self.app_name    = ctx.app_name
        self.window_title= ctx.raw_title
        self.file_name   = ctx.file_name
        self.keywords    = ctx.keywords
        self.event_type  = ctx.event_type
        self.email_subj  = ctx.email_subj
        self.sender      = ctx.sender
        self.channel     = ctx.channel
        self.page_title  = ctx.page_title
        self.project     = ctx.project

    def __repr__(self):
        return f"AppEvent(app={self.app_name!r}, title={self.window_title[:40]!r})"


class AppWatcher:
    """
    Polls the active window every `interval` seconds.
    Fires registered listeners whenever the window changes.
    Works with ALL apps installed on the PC.
    """

    def __init__(self, config, db):
        self.config          = config
        self.db              = db
        self._reader         = AppReader()
        self._running        = False
        self._paused         = False
        self._thread: Optional[threading.Thread] = None
        self._listeners: list[Callable] = []
        self._last_title     = ""
        self._last_app       = ""
        self.events_recorded = 0
        # Track active apps seen this session
        self.seen_apps: dict[str, int] = {}

    def add_listener(self, fn: Callable):
        self._listeners.append(fn)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="AppWatcher", daemon=True)
        self._thread.start()
        mode = "REAL (win32gui)" if (IS_WINDOWS and WIN32_OK) else "SIMULATION"
        logger.info(f"AppWatcher started — mode: {mode}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info(f"AppWatcher stopped. Events: {self.events_recorded}")

    def pause(self):
        self._paused = True
        logger.info("AppWatcher paused.")

    def resume(self):
        self._paused = False
        logger.info("AppWatcher resumed.")

    def get_current(self) -> Optional[AppEvent]:
        ctx = self._read()
        return AppEvent(ctx) if ctx else None

    def get_all_seen_apps(self) -> list[str]:
        return sorted(self.seen_apps.keys(),
                      key=lambda a: self.seen_apps[a], reverse=True)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self):
        interval = float(self.config.get("watch_interval", 1.0))
        while self._running:
            try:
                if not self._paused:
                    self._tick()
            except Exception as e:
                logger.error(f"Watcher tick error: {e}")
            time.sleep(interval)

    def _tick(self):
        ctx = self._read()
        if not ctx:
            return

        # Only act on window change
        if (ctx.raw_title   == self._last_title and
                ctx.app_name == self._last_app):
            return

        self._last_title = ctx.raw_title
        self._last_app   = ctx.app_name

        # Track seen apps
        self.seen_apps[ctx.app_name] = \
            self.seen_apps.get(ctx.app_name, 0) + 1

        # Save to DB
        extra = []
        if ctx.email_subj: extra.append(f"email:{ctx.email_subj}")
        if ctx.channel:    extra.append(f"channel:{ctx.channel}")
        if ctx.project:    extra.append(f"project:{ctx.project}")
        if ctx.page_title: extra.append(f"page:{ctx.page_title}")

        self.db.add_event(
            app_name     = ctx.app_name,
            window_title = ctx.raw_title,
            event_type   = ctx.event_type,
            file_name    = ctx.file_name,
            keywords     = ",".join(ctx.keywords),
            raw_text     = " | ".join(extra) if extra else ctx.raw_title,
        )
        self.events_recorded += 1
        logger.debug(f"Window: {ctx.app_name} | {ctx.raw_title[:60]}")

        event = AppEvent(ctx)
        for fn in self._listeners:
            try:
                fn(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def _read(self) -> Optional[ParsedContext]:
        if IS_WINDOWS and WIN32_OK:
            return self._read_windows()
        return self._read_simulation()

    def _read_windows(self) -> Optional[ParsedContext]:
        try:
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title or len(title.strip()) < 2:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                exe = psutil.Process(pid).name()
            except Exception:
                exe = "unknown.exe"
            return self._reader.parse(exe, title)
        except Exception as e:
            logger.debug(f"win32 read error: {e}")
            return None

    def _read_simulation(self) -> Optional[ParsedContext]:
        import random
        samples = [
            ("code.exe",    "AuthService.ts — contextOS — Visual Studio Code"),
            ("chrome.exe",  "Re: auth flow must not change — Sara Khan — Gmail"),
            ("slack.exe",   "#dev-mobile — MyWorkspace — Slack"),
            ("chrome.exe",  "Sprint 3 | Notion"),
            ("figma.exe",   "Login_v4 — Figma"),
            ("code.exe",    "main.py — contextOS — Visual Studio Code"),
            ("chrome.exe",  "Stack Overflow — NullPointerException Python"),
            ("chrome.exe",  "contextOS/core/app_watcher.py at main · user/contextOS — GitHub"),
            ("outlook.exe", "RE: Auth requirements - Microsoft Outlook"),
            ("teams.exe",   "General | Dev Team | Microsoft Teams"),
            ("chrome.exe",  "COS-123 Fix login bug — MyProject — Jira"),
            ("whatsapp.exe","Ahmed Khan — WhatsApp"),
        ]
        exe, title = random.choice(samples)
        return self._reader.parse(exe, title)

    def is_watched(self, app_name: str) -> bool:
        watched = self.config.get("watched_apps", [])
        return any(w.lower() in app_name.lower() for w in watched)
