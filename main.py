"""
ContextOS - AI-Powered Cross-App Context Bridge
Main entry point. Run this file to start the application.

Usage:
    python main.py           # Normal start
    python main.py --debug   # Start with debug logging
    python main.py --lite    # Force lite mode (low RAM)
"""

import sys
import os
import argparse
import logging

# ── Make sure all our folders are importable ──────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils.logger import setup_logger
from utils.system_check import SystemCheck
from core.app_watcher import AppWatcher
from core.context_engine import ContextEngine
from core.conflict_detector import ConflictDetector
from core.session_manager import SessionManager
from data.database import Database
from data.config_manager import ConfigManager
from ui.tray_app import TrayApp


def parse_args():
    parser = argparse.ArgumentParser(description="ContextOS - Context Bridge for Windows")
    parser.add_argument("--debug",  action="store_true", help="Enable debug logging")
    parser.add_argument("--lite",   action="store_true", help="Force lite mode")
    parser.add_argument("--reset",  action="store_true", help="Reset all settings to default")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── 1. Set up logging first so everything after can log ───────────────────
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger(log_level)
    logger.info("=" * 50)
    logger.info("ContextOS starting up...")
    logger.info("=" * 50)

    # ── 2. Load or create config file ─────────────────────────────────────────
    config = ConfigManager()
    if args.reset:
        config.reset_to_defaults()
        logger.info("Settings reset to defaults.")

    if args.lite:
        config.set("mode", "lite")
        logger.info("Lite mode forced via command line.")

    # ── 3. Check system specs and auto-select mode ────────────────────────────
    checker = SystemCheck()
    specs = checker.get_specs()
    logger.info(f"System specs: RAM={specs['ram_gb']:.1f}GB, "
                f"CPU cores={specs['cpu_cores']}, OS={specs['os_version']}")

    if not config.get("mode"):
        mode = checker.recommend_mode()
        config.set("mode", mode)
        logger.info(f"Auto-selected mode: {mode}")
    else:
        mode = config.get("mode")
        logger.info(f"Mode from config: {mode}")

    # ── 4. Initialize the database ────────────────────────────────────────────
    db = Database()
    db.initialize()
    logger.info("Database ready.")

    # ── 5. Build the core components ──────────────────────────────────────────
    watcher   = AppWatcher(config, db)
    engine    = ContextEngine(config, db)
    detector  = ConflictDetector(config, db)
    session   = SessionManager(config, db)

    # ── 6. Start the UI (system tray) ─────────────────────────────────────────
    logger.info("Launching system tray UI...")
    app = TrayApp(
        config=config,
        watcher=watcher,
        engine=engine,
        detector=detector,
        session=session,
        db=db,
    )
    app.run()  # blocks until user quits


if __name__ == "__main__":
    main()
