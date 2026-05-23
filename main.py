"""
ContextOS — Main entry point.
Usage:
  python main.py            # Normal start
  python main.py --debug    # Debug logging
  python main.py --lite     # Force lite/rules mode
  python main.py --reset    # Reset all settings
"""
import sys, os, argparse, logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils.logger       import setup_logger
from utils.system_check import SystemCheck
from core.app_watcher   import AppWatcher
from core.context_engine   import ContextEngine
from core.conflict_detector import ConflictDetector
from core.session_manager  import SessionManager
from data.database         import Database
from data.config_manager   import ConfigManager
from ui.tray_app           import TrayApp


def parse_args():
    p = argparse.ArgumentParser(description="ContextOS")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--lite",  action="store_true")
    p.add_argument("--reset", action="store_true")
    return p.parse_args()


def main():
    args   = parse_args()
    level  = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger(level)

    logger.info("="*52)
    logger.info("  ContextOS starting up")
    logger.info("="*52)

    config = ConfigManager()
    if args.reset:
        config.reset_to_defaults()
        logger.info("Settings reset to defaults.")
    if args.lite:
        config.set("mode", "lite")

    checker = SystemCheck()
    specs   = checker.get_specs()
    logger.info(f"System: RAM={specs['ram_gb']:.1f}GB  "
                f"CPU={specs['cpu_cores']} cores  "
                f"OS={specs['os_version']}")

    if config.get("mode") == "auto":
        mode = checker.recommend_mode()
        config.set("mode", mode)
        logger.info(f"Auto-selected mode: {mode}")
    else:
        logger.info(f"Mode: {config.get('mode')}")

    db = Database()
    db.initialize()
    logger.info("Database ready.")

    # Check dependencies
    _check_deps(logger)

    watcher  = AppWatcher(config, db)
    engine   = ContextEngine(config, db)
    detector = ConflictDetector(config, db)
    session  = SessionManager(config, db)

    logger.info("Launching ContextOS...")
    app = TrayApp(
        config=config, watcher=watcher, engine=engine,
        detector=detector, session=session, db=db,
    )
    app.run()


def _check_deps(logger):
    missing = []
    try:
        import win32gui
    except ImportError:
        if os.name == "nt":
            missing.append("pywin32")
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
    try:
        import pystray
    except ImportError:
        missing.append("pystray")
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    if missing:
        logger.warning(
            f"Missing packages: {', '.join(missing)}. "
            f"Run: python install_deps.py")


if __name__ == "__main__":
    main()
