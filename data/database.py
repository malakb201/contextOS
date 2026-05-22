"""
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
