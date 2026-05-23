"""
build_exe.py
ContextOS ko single .exe file mein bundle karta hai.
PyInstaller use karta hai.

Usage:  python build_exe.py
Output: dist/ContextOS_Setup/ContextOS.exe
"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(BASE, "assets", "icons", "contextOS.ico")

print("\n" + "="*55)
print("  ContextOS — EXE Builder")
print("  Developed by SAIPK@support")
print("="*55 + "\n")

# Install PyInstaller if not present
print("  Checking PyInstaller...", end=" ", flush=True)
try:
    import PyInstaller
    print("already installed.")
except ImportError:
    print("installing...")
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "pyinstaller", "--quiet"], check=True)
    print("  PyInstaller installed.")

print("\n  Building ContextOS.exe...")
print("  (This takes 1-3 minutes — please wait)\n")

# PyInstaller command
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                          # Single .exe file
    "--windowed",                         # No console window
    "--clean",                            # Clean build
    f"--icon={ICON}",                     # SAIPK icon
    "--name=ContextOS",                   # Output name
    # Add data files
    "--add-data=assets;assets",           # Include icons folder
    "--add-data=data/config_manager.py;data",
    # Hidden imports needed
    "--hidden-import=win32gui",
    "--hidden-import=win32process",
    "--hidden-import=win32con",
    "--hidden-import=pystray",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageDraw",
    "--hidden-import=PIL.ImageTk",
    "--hidden-import=psutil",
    "--hidden-import=sqlite3",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    # Version info
    "--version-file=version_info.txt"
    if os.path.exists("version_info.txt") else "--noupx",
    "main.py"                             # Entry point
]

result = subprocess.run(cmd, capture_output=False)

if result.returncode == 0:
    exe_path = os.path.join(BASE, "dist", "ContextOS.exe")
    size_mb  = os.path.getsize(exe_path) / (1024*1024) if os.path.exists(exe_path) else 0
    print(f"\n  ✓ BUILD SUCCESSFUL!")
    print(f"  File: dist/ContextOS.exe")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"\n  Share dist/ContextOS.exe with your users.")
    print("  They do NOT need Python installed.")
else:
    print("\n  ✗ Build failed. Check errors above.")
    print("  Common fix: run as Administrator")

print("\n" + "="*55 + "\n")
