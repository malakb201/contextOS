"""
tests/test_core.py
Automated tests for the core ContextOS modules.
Run with:   pytest tests/
All tests work without Windows — no GUI, no win32 needed.
"""

import sys
import os
import pytest
import tempfile

# Make sure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════════
#  Database tests
# ══════════════════════════════════════════════════════════════════

class TestDatabase:
    """Test the Database class with a temporary in-memory database."""

    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        """Create a fresh Database using a temp directory."""
        import data.database as db_module
        monkeypatch.setattr(db_module, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
        from data.database import Database
        database = Database()
        database.initialize()
        return database

    def test_initialize_creates_tables(self, db):
        """Database should create all 4 tables on init."""
        with db._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        table_names = {t[0] for t in tables}
        assert "context_events" in table_names
        assert "insights"       in table_names
        assert "sessions"       in table_names
        assert "kv_store"       in table_names

    def test_add_and_get_event(self, db):
        """Should save an event and retrieve it."""
        db.add_event(
            app_name     = "VS Code",
            window_title = "AuthService.ts — VS Code",
            event_type   = "app_switch",
            keywords     = "auth,service,token",
        )
        events = db.get_recent_events(limit=5)
        assert len(events) == 1
        assert events[0]["app_name"] == "VS Code"
        assert "auth" in events[0]["keywords"]

    def test_add_and_get_insight(self, db):
        """Should save an insight and retrieve it as active."""
        insight_id = db.add_insight(
            insight_type = "conflict",
            title        = "Auth conflict detected",
            detail       = "Email vs code conflict",
            source_apps  = "VS Code,Gmail",
        )
        assert isinstance(insight_id, int)
        active = db.get_active_insights()
        assert len(active) == 1
        assert active[0]["title"] == "Auth conflict detected"

    def test_dismiss_insight(self, db):
        """Dismissed insights should not appear in active list."""
        iid = db.add_insight("conflict", "Test insight", "detail", "VS Code")
        db.dismiss_insight(iid)
        active = db.get_active_insights()
        assert len(active) == 0

    def test_kv_store(self, db):
        """kv_store should save and retrieve arbitrary strings."""
        db.kv_set("test_key", "hello world")
        val = db.kv_get("test_key")
        assert val == "hello world"

    def test_kv_get_missing_returns_default(self, db):
        val = db.kv_get("does_not_exist", default="fallback")
        assert val == "fallback"

    def test_get_keywords_last_n(self, db):
        """Should collect all keywords from recent events."""
        db.add_event("VS Code", "AuthService.ts", "app_switch",
                     keywords="auth,service")
        db.add_event("Slack",   "Ahmed: fixed checkout", "app_switch",
                     keywords="checkout,fixed")
        kws = db.get_keywords_last_n_events(n=10)
        assert "auth" in kws
        assert "checkout" in kws

    def test_session_start_and_end(self, db):
        """Should record a session start and end."""
        sid = db.start_session()
        assert isinstance(sid, int)
        db.end_session(sid, focus_topic="AuthService", app_list="VS Code,Slack")
        # If no exception, the session was recorded correctly


# ══════════════════════════════════════════════════════════════════
#  Config manager tests
# ══════════════════════════════════════════════════════════════════

class TestConfigManager:

    @pytest.fixture
    def config(self, tmp_path, monkeypatch):
        import data.config_manager as cm_module
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", str(tmp_path / "settings.json"))
        from data.config_manager import ConfigManager
        return ConfigManager()

    def test_defaults_loaded(self, config):
        assert config.get("mode") in ("auto", "lite", "full")
        assert isinstance(config.get("idle_delay_seconds"), int)

    def test_set_and_get(self, config):
        config.set("mode", "lite")
        assert config.get("mode") == "lite"

    def test_reset_to_defaults(self, config):
        config.set("mode", "cloud")
        config.reset_to_defaults()
        assert config.get("mode") == "auto"

    def test_missing_key_returns_fallback(self, config):
        val = config.get("nonexistent_key_xyz", fallback="DEFAULT")
        assert val == "DEFAULT"

    def test_settings_persist_across_reload(self, tmp_path, monkeypatch):
        """Settings written in one instance should be readable by a new instance."""
        import data.config_manager as cm_module
        path = str(tmp_path / "settings.json")
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", path)
        from data.config_manager import ConfigManager
        c1 = ConfigManager()
        c1.set("theme", "dark")
        c2 = ConfigManager()
        assert c2.get("theme") == "dark"


# ══════════════════════════════════════════════════════════════════
#  AppWatcher keyword extraction tests
# ══════════════════════════════════════════════════════════════════

class TestAppWatcherHelpers:
    """Test parsing via AppReader — no Windows API needed."""

    @pytest.fixture
    def reader(self):
        from core.app_reader import AppReader
        return AppReader()

    def test_extract_keywords_basic(self, reader):
        kws = reader._extract_keywords("AuthService.ts — contextOS — VS Code")
        assert any("auth" in k for k in kws)

    def test_extract_keywords_filters_stopwords(self, reader):
        kws = reader._extract_keywords("the and or in on at")
        assert len(kws) == 0

    def test_extract_keywords_deduplicates(self, reader):
        kws = reader._extract_keywords("auth auth auth service")
        assert kws.count("auth") <= 1

    def test_extract_filename_typescript(self, reader):
        assert reader._extract_file("AuthService.ts — VS Code") == "AuthService.ts"

    def test_extract_filename_python(self, reader):
        assert reader._extract_file("main.py — contextOS — VS Code") == "main.py"

    def test_extract_filename_none_when_missing(self, reader):
        assert reader._extract_file("Stack Overflow — no file here") is None

    def test_friendly_app_name(self, reader):
        assert reader._friendly_name("Code.exe","")   == "VS Code"
        assert reader._friendly_name("chrome.exe","") == "Chrome"
        assert reader._friendly_name("slack.exe","")  == "Slack"

    def test_parse_vscode_title(self, reader):
        ctx = reader.parse("code.exe", "AuthService.ts — contextOS — Visual Studio Code")
        assert ctx.app_name  == "VS Code"
        assert ctx.file_name == "AuthService.ts"
        assert ctx.project   == "contextOS"

    def test_parse_gmail_in_browser(self, reader):
        ctx = reader.parse("chrome.exe", "Re: auth flow must not change — Sara Khan — Gmail")
        assert ctx.app_name   == "Chrome"
        assert ctx.email_subj is not None
        assert "auth" in ctx.email_subj.lower()

    def test_parse_slack_desktop(self, reader):
        ctx = reader.parse("slack.exe", "#dev-mobile — MyWorkspace — Slack")
        assert ctx.app_name == "Slack"
        assert ctx.channel  == "dev-mobile"

    def test_parse_figma(self, reader):
        ctx = reader.parse("figma.exe", "Login_v4 — Figma")
        assert ctx.app_name   == "Figma"
        assert ctx.page_title == "Login_v4"

    def test_parse_unknown_app(self, reader):
        ctx = reader.parse("myapp.exe", "Customer Invoice 2024 — MyApp")
        assert ctx.app_name is not None


# ══════════════════════════════════════════════════════════════════
#  ConflictDetector tests
# ══════════════════════════════════════════════════════════════════

class TestConflictDetector:

    @pytest.fixture
    def setup(self, tmp_path, monkeypatch):
        import data.config_manager as cm_module
        import data.database as db_module
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", str(tmp_path / "settings.json"))
        monkeypatch.setattr(db_module, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
        from data.config_manager import ConfigManager
        from data.database import Database
        from core.conflict_detector import ConflictDetector
        db  = Database()
        db.initialize()
        cfg = ConfigManager()
        det = ConflictDetector(cfg, db)
        return db, cfg, det

    def test_no_insights_with_empty_db(self, setup):
        _, _, det = setup
        insights = det.analyse()
        assert insights == []

    def test_detects_conflict_between_code_and_email(self, setup):
        db, _, det = setup
        # Simulate: user read email about 'authentication'
        db.add_event("Gmail", "Sara: authentication flow must not change",
                     "app_switch", keywords="authentication,flow,change")
        # Simulate: user then opened auth file in VS Code
        db.add_event("VS Code", "authentication_service.py — VS Code",
                     "app_switch", keywords="authentication,service,python")
        insights = det.analyse()
        # Should detect the shared keyword 'authentication'
        assert len(insights) >= 1
        assert any("authentication" in i.title.lower() or
                   "conflict" in i.insight_type for i in insights)

    def test_cooldown_prevents_duplicate_insights(self, setup):
        db, _, det = setup
        db.add_event("Gmail",   "Subject: checkout problem", "app_switch",
                     keywords="checkout,problem")
        db.add_event("VS Code", "checkout.py — VS Code",    "app_switch",
                     keywords="checkout,python")
        # Fire once
        first  = det.analyse()
        # Fire again immediately — should be suppressed by cooldown
        second = det.analyse()
        assert len(second) == 0   # cooldown should block it

    def test_insight_saved_to_database(self, setup):
        db, _, det = setup
        db.add_event("Slack",   "Ahmed: fixed the checkout bug", "app_switch",
                     keywords="checkout,fixed,bug")
        db.add_event("VS Code", "checkout_handler.py — VS Code", "app_switch",
                     keywords="checkout,handler,python")
        det.analyse()
        saved = db.get_active_insights()
        assert len(saved) >= 1


# ══════════════════════════════════════════════════════════════════
#  SystemCheck tests
# ══════════════════════════════════════════════════════════════════

class TestSystemCheck:

    def test_get_specs_returns_dict(self):
        from utils.system_check import SystemCheck
        specs = SystemCheck().get_specs()
        assert "ram_gb"    in specs
        assert "cpu_cores" in specs
        assert specs["ram_gb"] > 0
        assert specs["cpu_cores"] >= 1

    def test_recommend_mode_returns_valid_string(self):
        from utils.system_check import SystemCheck
        mode = SystemCheck().recommend_mode()
        assert mode in ("lite", "full", "cloud")
