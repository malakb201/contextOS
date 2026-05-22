"""
Run this once inside your contextOS folder to create every file correctly.
Usage:  python fix_setup.py
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

files = {}

# ── __init__.py files ──────────────────────────────────────────────────────────
files["__init__.py"]        = "# ContextOS\n"
files["core/__init__.py"]   = "# core package\n"
files["data/__init__.py"]   = "# data package\n"
files["ui/__init__.py"]     = "# ui package\n"
files["utils/__init__.py"]  = "# utils package\n"
files["tests/__init__.py"]  = "# tests package\n"
files["ai/__init__.py"]     = "# ai package\n"

# ── utils/logger.py ───────────────────────────────────────────────────────────
files["utils/logger.py"] = '''"""
utils/logger.py  -  Sets up logging for the whole application.
Logs go to both the console and a rotating log file.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, "data", "user_data")
LOG_PATH = os.path.join(LOG_DIR, "contextos.log")

_FMT = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)

def setup_logger(level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(_FMT)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2*1024*1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FMT)
    if not root.handlers:
        root.addHandler(ch)
        root.addHandler(fh)
    return root
'''

# ── utils/system_check.py ─────────────────────────────────────────────────────
files["utils/system_check.py"] = '''"""
utils/system_check.py  -  Reads hardware specs and recommends a mode.
"""
import os, platform, logging
logger = logging.getLogger(__name__)

class SystemCheck:
    def get_specs(self):
        return {
            "ram_gb":     self._ram(),
            "cpu_cores":  self._cores(),
            "os_version": platform.platform(),
            "is_windows": os.name == "nt",
        }

    def recommend_mode(self):
        ram = self._ram()
        mode = "lite" if ram < 3.0 else "full"
        logger.info(f"RAM={ram:.1f}GB -> {mode} mode")
        return mode

    def _ram(self):
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            pass
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        return int(line.split()[1]) / (1024**2)
        except Exception:
            pass
        return 4.0

    def _cores(self):
        return os.cpu_count() or 2
'''

# ── data/config_manager.py ────────────────────────────────────────────────────
files["data/config_manager.py"] = '''"""
data/config_manager.py  -  Reads and writes settings.json
"""
import json, os, logging
logger = logging.getLogger(__name__)

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR  = os.path.join(BASE_DIR, "data", "user_data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "mode":               "auto",
    "idle_delay_seconds": 3,
    "watch_interval":     1.0,
    "analysis_interval":  30,
    "watched_apps": [
        "VS Code", "Code", "Chrome", "Firefox", "Edge",
        "Outlook", "Gmail", "Slack", "Teams",
        "Notion", "Obsidian", "Figma", "Jira", "Linear",
    ],
    "auto_update_tasks":     True,
    "meeting_briefing":      True,
    "smart_pause":           True,
    "smart_pause_threshold": 80,
    "cloud_ai":              False,
    "run_on_startup":        True,
    "theme":                 "auto",
    "show_notifications":    True,
    "notification_sound":    False,
    "max_insights_shown":    5,
    "local_only":            True,
    "store_history_days":    30,
    "first_run":             True,
    "version":               "1.0.0",
    "onboarding_complete":   False,
}

class ConfigManager:
    def __init__(self):
        self._data = {}
        self._load()

    def get(self, key, fallback=None):
        return self._data.get(key, DEFAULTS.get(key, fallback))

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def get_all(self):
        merged = dict(DEFAULTS)
        merged.update(self._data)
        return merged

    def reset_to_defaults(self):
        self._data = dict(DEFAULTS)
        self._save()

    def _load(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            self._data = dict(DEFAULTS)
            self._save()
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._data = dict(DEFAULTS)
            self._data.update(loaded)
        except Exception as e:
            logger.error(f"Could not read settings.json: {e}")
            self._data = dict(DEFAULTS)

    def _save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Could not save settings.json: {e}")
'''

# ── data/database.py ──────────────────────────────────────────────────────────
files["data/database.py"] = '''"""
data/database.py  -  SQLite database that stores all of ContextOS memory.
"""
import sqlite3, os, logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR   = os.path.join(BASE_DIR, "data", "user_data")
DB_PATH  = os.path.join(DB_DIR, "context.db")

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        os.makedirs(DB_DIR, exist_ok=True)

    def initialize(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS context_events (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT NOT NULL,
                    app_name     TEXT NOT NULL,
                    window_title TEXT NOT NULL,
                    file_name    TEXT,
                    event_type   TEXT NOT NULL,
                    keywords     TEXT,
                    raw_text     TEXT
                );
                CREATE TABLE IF NOT EXISTS insights (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    title        TEXT NOT NULL,
                    detail       TEXT,
                    source_apps  TEXT,
                    dismissed    INTEGER DEFAULT 0,
                    acted_on     INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time       TEXT NOT NULL,
                    end_time         TEXT,
                    focus_topic      TEXT,
                    app_list         TEXT,
                    tasks_done       INTEGER DEFAULT 0,
                    conflicts_caught INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS kv_store (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
        logger.info(f"Database ready at {self.db_path}")

    def add_event(self, app_name, window_title, event_type,
                  file_name=None, keywords=None, raw_text=None):
        sql = """INSERT INTO context_events
                 (timestamp,app_name,window_title,file_name,event_type,keywords,raw_text)
                 VALUES (?,?,?,?,?,?,?)"""
        with self._connect() as conn:
            conn.execute(sql, (self._now(), app_name, window_title,
                               file_name, event_type, keywords, raw_text))

    def get_recent_events(self, limit=20, hours=24):
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        sql = """SELECT * FROM context_events
                 WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (since, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_keywords_last_n_events(self, n=30):
        sql = "SELECT keywords FROM context_events ORDER BY timestamp DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(sql, (n,)).fetchall()
        keywords = []
        for row in rows:
            if row[0]:
                keywords.extend(row[0].split(","))
        return [k.strip().lower() for k in keywords if k.strip()]

    def add_insight(self, insight_type, title, detail=None, source_apps=None):
        sql = """INSERT INTO insights (timestamp,insight_type,title,detail,source_apps)
                 VALUES (?,?,?,?,?)"""
        with self._connect() as conn:
            cur = conn.execute(sql, (self._now(), insight_type, title, detail, source_apps))
            return cur.lastrowid

    def get_active_insights(self, limit=10):
        sql = """SELECT * FROM insights WHERE dismissed=0
                 ORDER BY timestamp DESC LIMIT ?"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def dismiss_insight(self, insight_id):
        with self._connect() as conn:
            conn.execute("UPDATE insights SET dismissed=1 WHERE id=?", (insight_id,))

    def get_insight_count_today(self):
        today = datetime.now(timezone.utc).date().isoformat()
        sql = """SELECT insight_type, COUNT(*) FROM insights
                 WHERE timestamp >= ? GROUP BY insight_type"""
        with self._connect() as conn:
            rows = conn.execute(sql, (today,)).fetchall()
        return {row[0]: row[1] for row in rows}

    def start_session(self):
        sql = "INSERT INTO sessions (start_time) VALUES (?)"
        with self._connect() as conn:
            cur = conn.execute(sql, (self._now(),))
            return cur.lastrowid

    def end_session(self, session_id, focus_topic=None, app_list=None,
                    tasks_done=0, conflicts_caught=0):
        sql = """UPDATE sessions SET end_time=?,focus_topic=?,app_list=?,
                 tasks_done=?,conflicts_caught=? WHERE id=?"""
        with self._connect() as conn:
            conn.execute(sql, (self._now(), focus_topic, app_list,
                               tasks_done, conflicts_caught, session_id))

    def kv_set(self, key, value):
        with self._connect() as conn:
            conn.execute("INSERT OR REPLACE INTO kv_store (key,value) VALUES (?,?)",
                         (key, value))

    def kv_get(self, key, default=None):
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM kv_store WHERE key=?",
                               (key,)).fetchone()
        return row[0] if row else default

    def purge_old_events(self, keep_days=30):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM context_events WHERE timestamp < ?", (cutoff,))

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
'''

# ── core/app_watcher.py ───────────────────────────────────────────────────────
files["core/app_watcher.py"] = '''"""
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
            r"\\b([\\w\\-]+\\.(ts|js|py|cs|java|cpp|h|html|css|json|md|txt|yml|yaml|xml|go|rs))\\b",
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
'''

# ── core/conflict_detector.py ─────────────────────────────────────────────────
files["core/conflict_detector.py"] = '''"""
core/conflict_detector.py  -  Finds conflicts and answers across apps.
No AI needed — pure keyword matching. Fast and works offline.
"""
import logging, time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Insight:
    insight_type: str
    title:        str
    detail:       str
    source_apps:  list
    confidence:   float = 1.0
    id:           Optional[int] = None
    def __repr__(self):
        return f"Insight({self.insight_type!r}: {self.title!r})"

CONFLICT_RULES = [
    {
        "name":          "code_vs_email",
        "trigger_apps":  {"VS Code","Gmail","Outlook"},
        "insight_type":  "conflict",
        "title_template":  "Possible conflict: \\"{kw}\\" in email and your code",
        "detail_template": "You have an email mentioning \\"{kw}\\" and you are editing a related file. Check if the email has instructions about this code.",
    },
    {
        "name":          "slack_answer",
        "trigger_apps":  {"Slack","Teams","VS Code","Chrome"},
        "insight_type":  "answer",
        "title_template":  "Slack may have the answer for \\"{kw}\\"",
        "detail_template": "A recent Slack message mentions \\"{kw}\\" which matches what you are working on. The fix may already be there.",
    },
    {
        "name":          "notion_task_match",
        "trigger_apps":  {"Notion","Obsidian","VS Code","Figma"},
        "insight_type":  "auto_update",
        "title_template":  "Task \\"{kw}\\" may be ready to mark in-progress",
        "detail_template": "You have been working on \\"{kw}\\" for a while. Your Notion board may have a matching task to update.",
    },
    {
        "name":          "figma_code_mismatch",
        "trigger_apps":  {"Figma","VS Code"},
        "insight_type":  "conflict",
        "title_template":  "Design and code both mention \\"{kw}\\"",
        "detail_template": "Your Figma design and current code file both reference \\"{kw}\\". Make sure they are in sync.",
    },
    {
        "name":          "browser_research",
        "trigger_apps":  {"Chrome","Firefox","Edge","VS Code"},
        "insight_type":  "answer",
        "title_template":  "Your browser research relates to \\"{kw}\\"",
        "detail_template": "You searched for \\"{kw}\\" in your browser and are currently working on something related.",
    },
]

class ConflictDetector:
    def __init__(self, config, db):
        self.config  = config
        self.db      = db
        self._fired: dict = {}
        self._cooldown    = 300

    def analyse(self):
        recent = self.db.get_recent_events(limit=50, hours=2)
        if len(recent) < 2:
            return []
        app_kws: dict = {}
        for e in recent:
            app = e["app_name"]
            kws = e.get("keywords","") or ""
            if app not in app_kws:
                app_kws[app] = set()
            app_kws[app].update(k.strip().lower() for k in kws.split(",") if k.strip())
        results = []
        for rule in CONFLICT_RULES:
            ins = self._apply(rule, app_kws)
            if ins:
                ins.id = self.db.add_insight(ins.insight_type, ins.title,
                                              ins.detail, ",".join(ins.source_apps))
                results.append(ins)
        return results

    def analyse_single_event(self, event):
        if not event or not event.keywords:
            return []
        recent   = self.db.get_recent_events(limit=30, hours=1)
        insights = []
        for ev in recent:
            if ev["app_name"] == event.app_name:
                continue
            db_kws  = set((ev.get("keywords") or "").split(","))
            new_kws = set(event.keywords)
            shared  = {k for k in db_kws & new_kws if len(k) >= 4}
            if not shared:
                continue
            kw  = max(shared, key=len)
            key = f"quick_{event.app_name}_{ev[\'app_name\']}_{kw}"
            if self._on_cd(key):
                continue
            itype  = "answer" if any(c in ev["app_name"].lower()
                                     for c in ["slack","teams","gmail","outlook"]) else "conflict"
            title  = f\'"{kw}" seen in both {event.app_name} and {ev["app_name"]}\'
            detail = (f\'Your {event.app_name} window and a recent {ev["app_name"]} \'
                      f\'event both mention "{kw}". This might be relevant.\')
            ins = Insight(itype, title, detail, [event.app_name, ev["app_name"]],
                          min(1.0, len(shared)*0.3))
            ins.id = self.db.add_insight(ins.insight_type, ins.title,
                                          ins.detail, ",".join(ins.source_apps))
            self._mark(key)
            insights.append(ins)
            if len(insights) >= 2:
                break
        return insights

    def _apply(self, rule, app_kws):
        trigger  = rule["trigger_apps"]
        active   = list(app_kws.keys())
        matched  = [a for a in active if any(t.lower() in a.lower() for t in trigger)]
        if len(matched) < 2:
            return None
        kw_per   = {a: app_kws[a] for a in matched}
        all_kws  = set()
        for kws in kw_per.values():
            all_kws |= kws
        shared = set()
        for kw in all_kws:
            if len(kw) < 4:
                continue
            if sum(1 for kws in kw_per.values() if kw in kws) >= 2:
                shared.add(kw)
        if not shared:
            return None
        kw  = max(shared, key=len)
        key = f"{rule[\'name\']}_{kw}"
        if self._on_cd(key):
            return None
        self._mark(key)
        return Insight(
            rule["insight_type"],
            rule["title_template"].format(kw=kw),
            rule["detail_template"].format(kw=kw),
            matched[:3],
            min(1.0, len(shared)*0.25+0.25),
        )

    def _on_cd(self, key):
        return (time.time() - self._fired.get(key, 0)) < self._cooldown

    def _mark(self, key):
        self._fired[key] = time.time()
'''

# ── core/context_engine.py ────────────────────────────────────────────────────
files["core/context_engine.py"] = '''"""
core/context_engine.py  -  Orchestrates watcher + detector + CPU guard.
"""
import time, logging, threading, os
from typing import Callable
from core.conflict_detector import ConflictDetector, Insight

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

class ContextEngine:
    def __init__(self, config, db):
        self.config   = config
        self.db       = db
        self._running = False
        self._paused  = False
        self._thread  = None
        self._listeners: list[Callable] = []
        self.stats    = {"insights_today":0,"conflicts_caught":0,
                         "tasks_auto_done":0,"focus_minutes":0}
        self._watcher  = None
        self._detector = None

    def add_insight_listener(self, fn):
        self._listeners.append(fn)

    def start(self, watcher, detector):
        self._watcher  = watcher
        self._detector = detector
        watcher.add_listener(self._on_event)
        watcher.start()
        self._running = True
        self._thread  = threading.Thread(target=self._loop, name="ContextEngine", daemon=True)
        self._thread.start()
        logger.info("ContextEngine started.")

    def stop(self):
        self._running = False
        if self._watcher:
            self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)

    def get_stats(self):
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    self.stats["focus_minutes"],
        }

    def _on_event(self, event):
        if self._paused:
            return
        try:
            for ins in self._detector.analyse_single_event(event):
                self._dispatch(ins)
        except Exception as e:
            logger.error(f"Quick analysis error: {e}")

    def _loop(self):
        interval = int(self.config.get("analysis_interval", 30))
        while self._running:
            time.sleep(interval)
            if not self._running:
                break
            if self._paused:
                continue
            if self.config.get("smart_pause", True):
                cpu = self._cpu()
                thr = int(self.config.get("smart_pause_threshold", 80))
                if cpu > thr:
                    logger.info(f"CPU {cpu:.0f}% — pausing.")
                    self._paused = True
                    if self._watcher:
                        self._watcher.pause()
                    continue
                elif self._paused and cpu < thr - 10:
                    logger.info(f"CPU {cpu:.0f}% — resuming.")
                    self._paused = False
                    if self._watcher:
                        self._watcher.resume()
            try:
                for ins in self._detector.analyse():
                    self._dispatch(ins)
                self.stats["focus_minutes"] += interval // 60
            except Exception as e:
                logger.error(f"Analysis error: {e}")

    def _dispatch(self, insight):
        for fn in self._listeners:
            try:
                fn(insight)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def _cpu(self):
        if IS_WINDOWS:
            try:
                import psutil
                return psutil.cpu_percent(interval=1)
            except Exception:
                return 0.0
        try:
            with open("/proc/stat") as f:
                parts = list(map(int, f.readline().split()[1:]))
            idle  = parts[3]
            total = sum(parts)
            return max(0.0, 100.0 - idle/total*100.0)
        except Exception:
            return 0.0
'''

# ── core/session_manager.py ───────────────────────────────────────────────────
files["core/session_manager.py"] = '''"""
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
        logger.info(f"User returned after {resume[\'away_minutes\']} min.")
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
'''

# ── ui/tray_app.py ────────────────────────────────────────────────────────────
files["ui/tray_app.py"] = '''"""
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
        print("\\n" + "="*55)
        print("  ContextOS  —  Console Mode")
        print("  (On Windows install pystray+pillow for real tray icon)")
        print("="*55)
        print("  Commands:  d=dashboard  i=insights  s=snooze  q=quit\\n")

        def print_ins(ins):
            icon = {"conflict":"[!]","answer":"[?]","auto_update":"[v]"}.get(ins.insight_type,"[ ]")
            print(f"\\n  {icon} {ins.insight_type.upper()}: {ins.title}")
            print(f"      {ins.detail[:80]}")
            print(f"      Apps: {ins.source_apps}\\n")

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
        print(f"\\n  Welcome back! Away for {away} minutes.")
        for c in resume_data.get("changes", []):
            print(f"  * {c[\'type\'].upper()}: {c[\'title\']}")
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
        print(f"\\n  Insights today:   {s[\'insights_today\']}")
        print(f"  Conflicts caught: {s[\'conflicts_caught\']}")
        print(f"  Tasks auto-done:  {s[\'tasks_auto_done\']}")
        print(f"  Focus time:       {s[\'focus_minutes\']} min\\n")

    def _print_insights(self):
        ins = self.db.get_active_insights(limit=5)
        if not ins:
            print("  No active insights.")
            return
        for i in ins:
            print(f"  [{i[\'insight_type\'].upper()}] {i[\'title\']}")
        print()

    def _snooze(self, *a):
        self._snoozed_until = time.time() + 1800

    def _quit(self, *a):
        self.stop()
'''

# ── tests/test_core.py ────────────────────────────────────────────────────────
files["tests/test_core.py"] = '''"""
tests/test_core.py  -  Automated tests. Run with: pytest tests/
All tests work without Windows — no GUI, no win32 needed.
"""
import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabase:
    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        import data.database as m
        monkeypatch.setattr(m, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(m, "DB_PATH", str(tmp_path / "test.db"))
        from data.database import Database
        d = Database(); d.initialize(); return d

    def test_tables_created(self, db):
        with db._connect() as conn:
            names = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type=\'table\'").fetchall()}
        assert {"context_events","insights","sessions","kv_store"} <= names

    def test_add_get_event(self, db):
        db.add_event("VS Code","AuthService.ts — VS Code","app_switch",keywords="auth,service")
        evs = db.get_recent_events(limit=5)
        assert len(evs) == 1 and evs[0]["app_name"] == "VS Code"

    def test_add_get_insight(self, db):
        iid = db.add_insight("conflict","Auth conflict","detail","VS Code,Gmail")
        assert isinstance(iid, int)
        assert db.get_active_insights()[0]["title"] == "Auth conflict"

    def test_dismiss_insight(self, db):
        iid = db.add_insight("conflict","Test","detail","VS Code")
        db.dismiss_insight(iid)
        assert db.get_active_insights() == []

    def test_kv_store(self, db):
        db.kv_set("k","v"); assert db.kv_get("k") == "v"

    def test_kv_missing_returns_default(self, db):
        assert db.kv_get("nope", default="fallback") == "fallback"

    def test_keywords_last_n(self, db):
        db.add_event("VS Code","f.py","app_switch",keywords="auth,service")
        db.add_event("Slack","msg","app_switch",keywords="checkout,fixed")
        kws = db.get_keywords_last_n_events(n=10)
        assert "auth" in kws and "checkout" in kws

    def test_session_start_end(self, db):
        sid = db.start_session()
        assert isinstance(sid, int)
        db.end_session(sid, focus_topic="Auth", app_list="VS Code")


class TestConfigManager:
    @pytest.fixture
    def config(self, tmp_path, monkeypatch):
        import data.config_manager as m
        monkeypatch.setattr(m, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(m, "CONFIG_PATH", str(tmp_path / "settings.json"))
        from data.config_manager import ConfigManager
        return ConfigManager()

    def test_defaults_loaded(self, config):
        assert config.get("mode") in ("auto","lite","full")

    def test_set_get(self, config):
        config.set("mode","lite"); assert config.get("mode") == "lite"

    def test_reset(self, config):
        config.set("mode","cloud"); config.reset_to_defaults()
        assert config.get("mode") == "auto"

    def test_missing_fallback(self, config):
        assert config.get("xyz_missing", fallback="DEF") == "DEF"

    def test_persists_across_reload(self, tmp_path, monkeypatch):
        import data.config_manager as m
        monkeypatch.setattr(m, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(m, "CONFIG_PATH", str(tmp_path / "s.json"))
        from data.config_manager import ConfigManager
        ConfigManager().set("theme","dark")
        assert ConfigManager().get("theme") == "dark"


class TestAppWatcherHelpers:
    @pytest.fixture
    def watcher(self, tmp_path, monkeypatch):
        import data.config_manager as cm; import data.database as dm
        monkeypatch.setattr(cm, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm, "CONFIG_PATH", str(tmp_path/"s.json"))
        monkeypatch.setattr(dm, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(dm, "DB_PATH", str(tmp_path/"db.db"))
        from data.config_manager import ConfigManager
        from data.database import Database
        from core.app_watcher import AppWatcher
        db = Database(); db.initialize()
        return AppWatcher(ConfigManager(), db)

    def test_keywords_basic(self, watcher):
        kws = watcher._kws("AuthService.ts — contextOS — VS Code")
        assert any("auth" in k for k in kws)

    def test_keywords_no_stopwords(self, watcher):
        assert watcher._kws("the and or in on at") == []

    def test_keywords_dedup(self, watcher):
        kws = watcher._kws("auth auth auth service")
        assert kws.count("auth") <= 1

    def test_fname_typescript(self, watcher):
        assert watcher._fname("AuthService.ts — VS Code") == "AuthService.ts"

    def test_fname_python(self, watcher):
        assert watcher._fname("main.py — VS Code") == "main.py"

    def test_fname_none(self, watcher):
        assert watcher._fname("Stack Overflow — no file") is None

    def test_friendly_name(self, watcher):
        assert watcher._friendly("Code.exe","")   == "VS Code"
        assert watcher._friendly("chrome.exe","") == "Chrome"
        assert watcher._friendly("slack.exe","")  == "Slack"


class TestConflictDetector:
    @pytest.fixture
    def setup(self, tmp_path, monkeypatch):
        import data.config_manager as cm; import data.database as dm
        monkeypatch.setattr(cm, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm, "CONFIG_PATH", str(tmp_path/"s.json"))
        monkeypatch.setattr(dm, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(dm, "DB_PATH", str(tmp_path/"db.db"))
        from data.config_manager import ConfigManager
        from data.database import Database
        from core.conflict_detector import ConflictDetector
        db = Database(); db.initialize()
        return db, ConfigManager(), ConflictDetector(ConfigManager(), db)

    def test_empty_db_no_insights(self, setup):
        _, _, det = setup; assert det.analyse() == []

    def test_detects_code_email_conflict(self, setup):
        db, _, det = setup
        db.add_event("Gmail","Sara: authentication flow must not change",
                     "app_switch",keywords="authentication,flow,change")
        db.add_event("VS Code","authentication_service.py — VS Code",
                     "app_switch",keywords="authentication,service,python")
        ins = det.analyse()
        assert len(ins) >= 1

    def test_cooldown_blocks_duplicate(self, setup):
        db, _, det = setup
        db.add_event("Gmail","Subject: checkout problem","app_switch",keywords="checkout,problem")
        db.add_event("VS Code","checkout.py","app_switch",keywords="checkout,python")
        det.analyse()
        assert det.analyse() == []

    def test_insight_saved_to_db(self, setup):
        db, _, det = setup
        db.add_event("Slack","Ahmed: fixed checkout bug","app_switch",keywords="checkout,fixed,bug")
        db.add_event("VS Code","checkout_handler.py","app_switch",keywords="checkout,handler,python")
        det.analyse()
        assert len(db.get_active_insights()) >= 1


class TestSystemCheck:
    def test_get_specs(self):
        from utils.system_check import SystemCheck
        s = SystemCheck().get_specs()
        assert s["ram_gb"] > 0 and s["cpu_cores"] >= 1

    def test_recommend_mode(self):
        from utils.system_check import SystemCheck
        assert SystemCheck().recommend_mode() in ("lite","full","cloud")
'''

# ── Write every file ───────────────────────────────────────────────────────────
created = 0
for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    created += 1
    print(f"  OK  {rel_path}")

print(f"\nDone! {created} files written.")
print("Now run:  python -m pytest tests/")