"""
core/session_manager.py  -  Tracks work sessions and away/return state.
"""
import time, logging, threading
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
IDLE_THRESHOLD = 5 * 60   # 5 minutes in seconds
CHECK_INTERVAL = 30

class SessionManager:
    def __init__(self, config, db):
        self.config             = config
        self.db                 = db
        self._running           = False
        self._thread            = None
        self._session_id        = None
        self._last_active       = time.time()
        self._is_away           = False
        self._away_start        = None
        self._away_listeners    = []
        self._return_listeners  = []
        self._snapshot          = []

    def set_away_listener(self, fn):
        self._away_listeners.append(fn)

    def set_return_listener(self, fn):
        self._return_listeners.append(fn)

    def notify_activity(self, event=None):
        now = time.time()
        if self._is_away:
            self._handle_return(now)
        self._last_active = now

    def start(self):
        self._session_id = self.db.start_session()
        self._running    = True
        self._thread = threading.Thread(target=self._loop, name="SessionManager", daemon=True)
        self._thread.start()
        logger.info(f"Session {self._session_id} started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._session_id:
            self.db.end_session(self._session_id,
                                focus_topic=self._focus_topic(),
                                app_list=self._recent_apps())

    def get_resume_data(self):
        away_min = int((time.time() - self._away_start) / 60) if self._away_start else 0
        return {
            "away_minutes":  away_min,
            "restore_items": self._restore_items(),
            "changes":       self._changes_while_away(),
            "focus_topic":   self._focus_topic(),
        }

    def _loop(self):
        while self._running:
            time.sleep(CHECK_INTERVAL)
            if not self._running:
                break
            if not self._is_away and (time.time() - self._last_active) >= IDLE_THRESHOLD:
                self._handle_away()

    def _handle_away(self):
        self._is_away    = True
        self._away_start = time.time()
        self._snapshot   = self.db.get_recent_events(limit=10, hours=1)
        logger.info("User went away.")
        for fn in self._away_listeners:
            try: fn()
            except Exception as e: logger.error(f"Away listener: {e}")

    def _handle_return(self, now):
        self._is_away     = False
        resume            = self.get_resume_data()
        self._away_start  = None
        logger.info(f"User returned after {resume['away_minutes']} min.")
        for fn in self._return_listeners:
            try: fn(resume)
            except Exception as e: logger.error(f"Return listener: {e}")

    def _focus_topic(self):
        kws  = self.db.get_keywords_last_n_events(n=30)
        freq: dict = {}
        for k in kws:
            freq[k] = freq.get(k, 0) + 1
        best = max(freq, key=lambda k: freq[k] if len(k) >= 4 else 0, default="")
        return best.title() if best else "General work"

    def _recent_apps(self):
        evs  = self.db.get_recent_events(limit=50, hours=1)
        seen = []
        for e in evs:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return ",".join(seen[:8])

    def _restore_items(self):
        items = []
        evs   = self._snapshot or self.db.get_recent_events(limit=10, hours=2)
        seen  = set()
        for e in evs:
            t = e.get("window_title","")
            if t in seen: continue
            seen.add(t)
            items.append({"app": e.get("app_name",""), "title": t,
                          "file_name": e.get("file_name"),
                          "timestamp": e.get("timestamp","")})
            if len(items) >= 4: break
        return items

    def _changes_while_away(self):
        if not self._away_start:
            return []
        away_iso = datetime.fromtimestamp(self._away_start, tz=timezone.utc).isoformat()
        changes  = []
        for ins in self.db.get_active_insights(limit=20):
            if ins.get("timestamp","") >= away_iso:
                changes.append({"type":  ins.get("insight_type","info"),
                                "title": ins.get("title",""),
                                "source":ins.get("source_apps","")})
        return changes[:5]
