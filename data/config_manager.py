"""
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
