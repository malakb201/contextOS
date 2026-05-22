"""
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
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
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
