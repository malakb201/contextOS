"""
core/meeting_monitor.py
Detects upcoming meetings and triggers briefing 5 min before.
Checks: Outlook calendar, Google Calendar (browser title), Zoom, Teams.
"""
import re, time, logging, threading
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt" if __import__("os").name == "nt" else False


class Meeting:
    def __init__(self, title: str, start_time: datetime,
                 source: str = "detected"):
        self.title      = title
        self.start_time = start_time
        self.source     = source
        self.briefed    = False

    def minutes_until(self) -> float:
        now = datetime.now(timezone.utc)
        st  = self.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        return (st - now).total_seconds() / 60


class MeetingMonitor:
    """
    Checks for upcoming meetings every 60 seconds.
    When a meeting is 5 minutes away, calls the briefing callback.

    Sources:
      1. Outlook COM object (Windows, needs pywin32)
      2. Window title detection (Zoom, Teams, Google Meet in browser)
      3. Manual meetings added by user
    """

    def __init__(self, config, db, watcher=None):
        self.config   = config
        self.db       = db
        self.watcher  = watcher
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._meetings: list[Meeting] = []
        self._briefing_callbacks: list[Callable] = []
        self._checked: set = set()

    def add_briefing_callback(self, fn: Callable):
        self._briefing_callbacks.append(fn)

    def start(self):
        if not self.config.get("meeting_briefing", True):
            logger.info("Meeting briefing disabled in settings.")
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="MeetingMonitor", daemon=True)
        self._thread.start()
        logger.info("MeetingMonitor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def add_manual_meeting(self, title: str, minutes_from_now: int):
        """Add a meeting manually (for testing or user input)."""
        from datetime import timedelta
        start = datetime.now(timezone.utc).replace(
            second=0, microsecond=0)
        start += timedelta(minutes=minutes_from_now)
        m = Meeting(title, start, "manual")
        self._meetings.append(m)
        logger.info(f"Manual meeting added: {title} in {minutes_from_now} min")

    def _loop(self):
        while self._running:
            try:
                self._refresh_meetings()
                self._check_upcoming()
            except Exception as e:
                logger.error(f"MeetingMonitor error: {e}")
            time.sleep(60)

    def _refresh_meetings(self):
        """Try to read real calendar data."""
        # Method 1: Outlook via COM (Windows only)
        self._try_outlook()
        # Method 2: Detect from window titles (Zoom joining, Teams)
        self._detect_from_titles()

    def _try_outlook(self):
        if not IS_WINDOWS:
            return
        try:
            import win32com.client
            outlook  = win32com.client.Dispatch("Outlook.Application")
            ns       = outlook.GetNamespace("MAPI")
            calendar = ns.GetDefaultFolder(9)  # 9 = olFolderCalendar
            items    = calendar.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]")

            from datetime import timedelta
            now      = datetime.now()
            end_time = now + timedelta(hours=2)
            items.Restrict(
                f"[Start] >= '{now.strftime('%m/%d/%Y %H:%M')}' "
                f"AND [Start] <= '{end_time.strftime('%m/%d/%Y %H:%M')}'"
            )

            existing_titles = {m.title for m in self._meetings}
            for item in items:
                try:
                    title = item.Subject
                    start = item.Start
                    if title not in existing_titles:
                        # Convert COM datetime to Python datetime
                        from pywintypes import Time
                        import pythoncom
                        dt = datetime(start.year, start.month, start.day,
                                     start.hour, start.minute,
                                     tzinfo=timezone.utc)
                        self._meetings.append(Meeting(title, dt, "outlook"))
                        logger.info(f"Outlook meeting found: {title}")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Outlook COM not available: {e}")

    def _detect_from_titles(self):
        """Detect meetings from Zoom/Teams window titles."""
        if not self.watcher:
            return
        event = self.watcher.get_current()
        if not event:
            return

        title = event.window_title.lower()
        app   = event.app_name.lower()

        meeting_signals = [
            "zoom meeting", "zoom call",
            "microsoft teams meeting", "teams call",
            "google meet", "meet.google",
            "whereby", "webex",
        ]
        if any(sig in title or sig in app for sig in meeting_signals):
            meeting_title = event.window_title.split("—")[0].strip()
            key = f"window_{meeting_title}"
            if key not in self._checked:
                self._checked.add(key)
                now = datetime.now(timezone.utc)
                self._meetings.append(Meeting(meeting_title, now, "window"))
                logger.info(f"Meeting detected from window: {meeting_title}")

    def _check_upcoming(self):
        """Check if any meeting is ~5 minutes away."""
        now = datetime.now(timezone.utc)
        for meeting in self._meetings[:]:
            if meeting.briefed:
                continue
            mins = meeting.minutes_until()
            if 0 <= mins <= 6:   # 0–6 minutes window
                meeting.briefed = True
                logger.info(f"Meeting briefing triggered: {meeting.title}")
                briefing = self._build_briefing(meeting)
                for fn in self._briefing_callbacks:
                    try:
                        fn(briefing)
                    except Exception as e:
                        logger.error(f"Briefing callback error: {e}")
            # Remove past meetings
            if mins < -30:
                self._meetings.remove(meeting)

    def _build_briefing(self, meeting: Meeting) -> dict:
        """Build the context briefing for a meeting."""
        recent  = self.db.get_recent_events(limit=30, hours=4)
        insights= self.db.get_active_insights(limit=10)

        # Find relevant events (keyword match with meeting title)
        meeting_kws = set(
            w.lower() for w in re.split(r'\W+', meeting.title)
            if len(w) >= 3
        )

        relevant_events = []
        for ev in recent:
            ev_kws = set((ev.get("keywords") or "").lower().split(","))
            if ev_kws & meeting_kws:
                relevant_events.append(ev)

        # Recent files opened
        files = []
        for ev in recent:
            f = ev.get("file_name")
            if f and f not in files:
                files.append(f)

        return {
            "meeting_title":    meeting.title,
            "minutes_until":    int(meeting.minutes_until()),
            "relevant_events":  relevant_events[:5],
            "active_insights":  insights[:3],
            "recent_files":     files[:4],
            "source":           meeting.source,
        }
