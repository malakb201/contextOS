"""
core/startup_manager.py
Windows startup management — adds/removes ContextOS from Windows Registry
so it launches automatically when the PC boots.
"""
import os, sys, logging

logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"
APP_NAME   = "ContextOS"


def add_to_startup():
    """Add ContextOS to Windows startup via Registry."""
    if not IS_WINDOWS:
        logger.info("Startup manager: not on Windows, skipping.")
        return False
    try:
        import winreg
        key  = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        # Build the startup command
        python = sys.executable
        script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py"))
        cmd = f'"{python}" "{script}"'
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        logger.info(f"Added to startup: {cmd}")
        return True
    except Exception as e:
        logger.error(f"Could not add to startup: {e}")
        return False


def remove_from_startup():
    """Remove ContextOS from Windows startup."""
    if not IS_WINDOWS:
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        logger.info("Removed from startup.")
        return True
    except FileNotFoundError:
        return True   # Already not there
    except Exception as e:
        logger.error(f"Could not remove from startup: {e}")
        return False


def is_in_startup() -> bool:
    """Check if ContextOS is currently in Windows startup."""
    if not IS_WINDOWS:
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
