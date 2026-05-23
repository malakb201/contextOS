"""
install_deps.py
One-click installer for all ContextOS dependencies.
Run this ONCE before starting ContextOS.

Usage:  python install_deps.py
"""
import sys, subprocess, os

IS_WINDOWS = os.name == "nt"

print("\n" + "="*55)
print("  ContextOS — Dependency Installer")
print("="*55 + "\n")

PACKAGES = [
    ("psutil",    "CPU/RAM monitoring and process names"),
    ("pillow",    "Tray icon image generation"),
    ("pystray",   "System tray icon (Windows)"),
]
if IS_WINDOWS:
    PACKAGES.insert(0, ("pywin32", "Read active Windows app titles (REQUIRED on Windows)"))

OPTIONAL = [
    ("pytest", "Run automated tests (optional)"),
]

def install(pkg_name):
    print(f"  Installing {pkg_name}...", end=" ", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg_name,
         "--quiet", "--disable-pip-version-check"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✓ Done")
        return True
    else:
        print("✗ FAILED")
        print(f"    Error: {result.stderr.strip()[:120]}")
        return False

print("  Required packages:")
failed = []
for pkg, desc in PACKAGES:
    print(f"  • {pkg:<12} — {desc}")
print()

for pkg, desc in PACKAGES:
    ok = install(pkg)
    if not ok:
        failed.append(pkg)

print("\n  Optional packages:")
for pkg, desc in OPTIONAL:
    install(pkg)

print()
if failed:
    print(f"  ⚠  Some packages failed: {', '.join(failed)}")
    print("  Try running as Administrator or check your internet connection.\n")
else:
    print("  ✓  All packages installed successfully!")
    print("\n  You can now run:  python main.py")

if IS_WINDOWS and "pywin32" not in failed:
    print("\n  Running post-install script for pywin32...")
    try:
        scripts = os.path.join(os.path.dirname(sys.executable), "Scripts")
        post    = os.path.join(scripts, "pywin32_postinstall.py")
        if os.path.exists(post):
            subprocess.run([sys.executable, post, "-install"],
                          capture_output=True)
            print("  ✓  pywin32 post-install done.")
    except Exception as e:
        print(f"  Note: post-install skipped ({e})")

print()
