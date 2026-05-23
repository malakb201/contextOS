"""
data/config_manager.py
Reads and writes the user's settings to settings.json.
Every setting has a safe default so the app always works,
even on first run when no settings file exists yet.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# ── Where we save the settings file ───────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "data", "user_data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

# ── Every possible setting with its default value ─────────────────────────────
DEFAULTS = {
    # Core behaviour
    "mode":               "auto",     # "lite", "full", "auto", "cloud"
    "idle_delay_seconds": 3,          # seconds of idle before analysis runs
    "watch_interval":     1.0,        # seconds between app-watcher polls
    "analysis_interval":  30,         # seconds between full context analyses

    # Which apps to watch (names must match the window title keywords)
    "watched_apps": [
        "VS Code", "Code",            # Visual Studio Code
        "Chrome", "Firefox", "Edge",  # Browsers
        "Outlook", "Gmail",           # Email
        "Slack", "Teams",             # Chat
        "Notion", "Obsidian",         # Notes
        "Figma",                      # Design
        "Jira", "Linear",             # Project management
    ],

    # Features on/off
    "auto_update_tasks":     True,    # auto-tick Notion/Jira tasks
    "meeting_briefing":      True,    # popup 5 min before calendar meetings
    "smart_pause":           True,    # pause when CPU > 80 %
    "smart_pause_threshold": 80,      # CPU % that triggers pause
    "cloud_ai":              False,   # use cloud AI (needs internet)
    "run_on_startup":        True,    # launch when Windows starts

    # UI preferences
    "theme":                 "auto",  # "light", "dark", "auto"
    "show_notifications":    True,
    "notification_sound":    False,
    "max_insights_shown":    5,       # max cards in tray popup

    # Privacy
    "local_only":            True,    # never send data to internet
    "store_history_days":    30,      # how many days of context to keep

    # Internal — do not change manually
    "first_run":             True,
    "version":               "1.0.0",
    "onboarding_complete":   False,
}


class ConfigManager:
    """
    Simple JSON-based config manager.

    Usage:
        config = ConfigManager()
        mode = config.get("mode")           # → "lite" / "full" / ...
        config.set("mode", "full")
        config.save()                       # writes to disk immediately
    """

    def __init__(self):
        self._data = {}
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, key, fallback=None):
        """Return a setting value. Falls back to DEFAULTS, then fallback."""
        return self._data.get(key, DEFAULTS.get(key, fallback))

    def set(self, key, value):
        """Update a setting and save to disk immediately."""
        self._data[key] = value
        self._save()
        logger.debug(f"Config: {key} = {value!r}")

    def get_all(self):
        """Return a merged dict of defaults + current settings."""
        merged = dict(DEFAULTS)
        merged.update(self._data)
        return merged

    def reset_to_defaults(self):
        """Wipe all settings and revert to defaults."""
        self._data = dict(DEFAULTS)
        self._save()
        logger.info("Config reset to defaults.")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load(self):
        """Load settings.json from disk. Creates it if missing."""
        os.makedirs(CONFIG_DIR, exist_ok=True)

        if not os.path.exists(CONFIG_PATH):
            logger.info("No settings.json found — creating with defaults.")
            self._data = dict(DEFAULTS)
            self._save()
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge loaded settings over defaults so new settings always exist
            self._data = dict(DEFAULTS)
            self._data.update(loaded)
            logger.info(f"Settings loaded from {CONFIG_PATH}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Could not read settings.json: {e} — using defaults.")
            self._data = dict(DEFAULTS)

    def _save(self):
        """Write current settings to disk."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Could not save settings.json: {e}")
