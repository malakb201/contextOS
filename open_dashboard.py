"""
open_dashboard.py
Open the ContextOS dashboard directly (without starting the tray icon).
Useful for testing the UI on its own.

Usage:  python open_dashboard.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.config_manager import ConfigManager
from data.database       import Database
from ui.dashboard        import Dashboard

db = Database()
db.initialize()
config = ConfigManager()

print("Opening ContextOS Dashboard...")
dash = Dashboard(config=config, db=db, engine=None)
dash.show()
