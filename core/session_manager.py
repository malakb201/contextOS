"""
core/session_manager.py
Tracks user work sessions.

Detects:
  - When a new session starts (user becomes active after idle)
  - When user goes away (idle for > 5 minutes)
  - What they were working on when they left
  - What changed while they were away

Feeds the "Resume screen" shown when the user returns.
"""

import time
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

IDLE_THRESHOLD_MINUTES = 5    # away this long = new session on return
AWAY_CHECK_INTERVAL    = 30   # check for idle every 30 seconds


class SessionManager:
    """
    Monitors active/idle state and manages session lifecycle.

    Usage:
        session = SessionManager(config, db)
        session.set_away_listener(my_callback)      # called when user goes away
        session.set_return_listener(my_callback)    # called when user comes back
        session.start()
    """

    def __init__(self, config, db):
        self.config   = config
        self.db       = db
        self._running = False
        self._thread  = None

        # Current session state
        self._session_id: int | None = None
        self._last_active_time       = time.time()
        self._is_away                = False
        self._away_start_time: float | None = None

        # Callbacks for the UI
        self._away_listeners:   list = []
        self._return_listeners: list = []

        # What the user had open when they went away
        self._snapshot_on_away: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_away_listener(self, fn):
        """fn() called when user goes idle/away."""
        self._away_listeners.append(fn)

    def set_return_listener(self, fn):
        """fn(resume_data: dict) called when user comes back."""
        self._return_listeners.append(fn)

    def notify_activity(self, event=None):
        """
        Call this whenever an AppEvent fires — proves the user is active.
        If they were away, trigger the return flow.
        """
        now = time.time()
        if self._is_away:
            self._handle_return(now)
        self._last_active_time = now

    def start(self):
        """Start monitoring in a background thread."""
        self._session_id = self.db.start_session()
        self._running    = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="SessionManager",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"SessionManager started. Session ID: {self._session_id}")

    def stop(self):
        """End the current session and stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._session_id:
            self.db.end_session(
                session_id = self._session_id,
                focus_topic = self._detect_focus_topic(),
                app_list    = self._get_recent_apps(),
            )
        logger.info("SessionManager stopped.")

    def get_resume_data(self) -> dict:
        """
        Build the data shown on the Resume screen.
        Called when the user returns from being away.
        """
        away_minutes = 0
        if self._away_start_time:
            away_minutes = int((time.time() - self._away_start_time) / 60)

        # What the user had open right before going away
        restore_items = self._build_restore_items()

        # What changed in the DB while they were gone
        changes = self._detect_changes_while_away()

        return {
            "away_minutes":  away_minutes,
            "restore_items": restore_items,
            "changes":       changes,
            "focus_topic":   self._detect_focus_topic(),
        }

    # ── Internal loop ──────────────────────────────────────────────────────────

    def _monitor_loop(self):
        while self._running:
            time.sleep(AWAY_CHECK_INTERVAL)
            if not self._running:
                break

            idle_seconds = time.time() - self._last_active_time
            idle_minutes = idle_seconds / 60

            if not self._is_away and idle_minutes >= IDLE_THRESHOLD_MINUTES:
                self._handle_away()

    # ── Away / return handlers ─────────────────────────────────────────────────

    def _handle_away(self):
        """User has gone idle."""
        self._is_away        = True
        self._away_start_time = time.time()

        # Take a snapshot of recent context before they disappear
        self._snapshot_on_away = self.db.get_recent_events(limit=10, hours=1)

        logger.info("User went away — session snapshot taken.")
        for fn in self._away_listeners:
            try:
                fn()
            except Exception as e:
                logger.error(f"Away listener error: {e}")

    def _handle_return(self, now: float):
        """User has come back."""
        self._is_away = False
        resume_data   = self.get_resume_data()
        self._away_start_time = None

        logger.info(f"User returned. Away for ~{resume_data['away_minutes']} min.")
        for fn in self._return_listeners:
            try:
                fn(resume_data)
            except Exception as e:
                logger.error(f"Return listener error: {e}")

    # ── Context helpers ────────────────────────────────────────────────────────

    def _detect_focus_topic(self) -> str:
        """
        Guess what the user was mainly working on by finding
        the most frequent keyword in the last hour of events.
        """
        keywords = self.db.get_keywords_last_n_events(n=30)
        if not keywords:
            return "Unknown project"

        freq: dict[str, int] = {}
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1

        # Return the most common non-trivial keyword
        best = max(freq, key=lambda k: freq[k] if len(k) >= 4 else 0, default="")
        return best.title() if best else "General work"

    def _get_recent_apps(self) -> str:
        """Comma-separated list of apps used in the last hour."""
        events = self.db.get_recent_events(limit=50, hours=1)
        seen   = []
        for e in events:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return ",".join(seen[:8])

    def _build_restore_items(self) -> list[dict]:
        """
        Build the list of 'restore' items for the Resume screen.
        Each item represents a file or context the user should jump back to.
        """
        items  = []
        events = self._snapshot_on_away or self.db.get_recent_events(limit=10, hours=2)

        seen_titles = set()
        for event in events:
            title = event.get("window_title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            items.append({
                "app":        event.get("app_name", ""),
                "title":      title,
                "file_name":  event.get("file_name"),
                "timestamp":  event.get("timestamp", ""),
            })
            if len(items) >= 4:
                break

        return items

    def _detect_changes_while_away(self) -> list[dict]:
        """
        Find insights that were generated while the user was away.
        These show up as "What happened while you were away" on the Resume screen.
        """
        if not self._away_start_time:
            return []

        away_start_iso = datetime.utcfromtimestamp(self._away_start_time).isoformat()
        all_insights   = self.db.get_active_insights(limit=20)

        # Filter to only those created after the user went away
        changes = []
        for ins in all_insights:
            ts = ins.get("timestamp", "")
            if ts >= away_start_iso:
                changes.append({
                    "type":   ins.get("insight_type", "info"),
                    "title":  ins.get("title", ""),
                    "source": ins.get("source_apps", ""),
                })
        return changes[:5]
