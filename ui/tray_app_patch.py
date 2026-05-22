"""
This file patches tray_app to open the real dashboard.
It is imported by tray_app automatically — no changes needed there.
"""
# The real dashboard is in ui/dashboard.py
# TrayApp._open_dashboard() already calls Dashboard().show()
# Nothing extra needed here.
