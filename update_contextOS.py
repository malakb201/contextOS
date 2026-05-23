"""
update_contextOS.py
Run this inside your contextOS folder to update all files.
Usage:  python update_contextOS.py
"""
import os
BASE = os.path.dirname(os.path.abspath(__file__))
files = {}

files['main.py'] = """\"\"\"
ContextOS — Main entry point.
Usage:
  python main.py            # Normal start
  python main.py --debug    # Debug logging
  python main.py --lite     # Force lite/rules mode
  python main.py --reset    # Reset all settings
\"\"\"
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
"""

files['install_deps.py'] = """\"\"\"
install_deps.py
One-click installer for all ContextOS dependencies.
Run this ONCE before starting ContextOS.

Usage:  python install_deps.py
\"\"\"
import sys, subprocess, os

IS_WINDOWS = os.name == "nt"

print("\\n" + "="*55)
print("  ContextOS — Dependency Installer")
print("="*55 + "\\n")

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

print("\\n  Optional packages:")
for pkg, desc in OPTIONAL:
    install(pkg)

print()
if failed:
    print(f"  ⚠  Some packages failed: {', '.join(failed)}")
    print("  Try running as Administrator or check your internet connection.\\n")
else:
    print("  ✓  All packages installed successfully!")
    print("\\n  You can now run:  python main.py")

if IS_WINDOWS and "pywin32" not in failed:
    print("\\n  Running post-install script for pywin32...")
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
"""

files['requirements.txt'] = """# ContextOS — Python dependencies
# Install everything with:   pip install -r requirements.txt
#
# CORE (required — works on all platforms)
# ─────────────────────────────────────────
# No extra packages needed for the core engine!
# Python's built-in sqlite3, threading, logging, json are all used.

# WINDOWS GUI (install on Windows only)
# ──────────────────────────────────────
pystray==0.19.5          # system tray icon
Pillow==10.4.0           # draw the tray icon image
pywin32==306             # read active window titles (Windows only)
psutil==6.0.0            # CPU/RAM monitoring, process names

# AI (optional — only needed for full AI mode)
# ─────────────────────────────────────────────
# llama-cpp-python==0.2.90  # local AI model runner
#   → uncomment when you are ready to add AI features (Stage 5 in your guide)
#   → install command:  pip install llama-cpp-python

# DEVELOPMENT TOOLS (install on all platforms for testing)
# ─────────────────────────────────────────────────────────
pytest==8.3.3            # run tests with:  pytest tests/
"""

files['README.md'] = """# ContextOS

**AI-Powered Cross-App Context Bridge for Windows**

ContextOS runs silently in the background and watches what you are doing
across all your apps — VS Code, Gmail, Slack, Notion, Figma — then alerts
you when something in one app conflicts with or answers something in another.

---

## What it does

- **Conflict detection** — Email says "don't change auth" while you edit `AuthService.ts`? ContextOS warns you.
- **Answer surfacing** — Slack has the fix for the bug you are looking at right now? ContextOS tells you.
- **Auto task updates** — Working on a file for 10+ minutes? ContextOS marks the matching Notion task in-progress.
- **Meeting prep** — 5 minutes before a meeting, get a briefing of everything relevant to it.
- **Resume screen** — Come back after a break and see exactly where you left off.

## System requirements

| Mode      | RAM     | CPU             | OS            |
|-----------|---------|-----------------|---------------|
| Lite      | 2 GB+   | Any dual-core   | Windows 7+    |
| Full (AI) | 4 GB+   | i5 6th gen+     | Windows 10+   |

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/contextOS.git
cd contextOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run ContextOS
python main.py

# 4. Run tests
pytest tests/
```

## Project structure

```
contextOS/
├── main.py                  ← Start here. Entry point.
├── requirements.txt         ← Python dependencies
│
├── core/                    ← The brain
│   ├── app_watcher.py       ← Reads the active Windows window every second
│   ├── context_engine.py    ← Orchestrates watcher + detector + session
│   ├── conflict_detector.py ← Finds conflicts and answers across apps
│   └── session_manager.py   ← Tracks work sessions, detects away time
│
├── ui/                      ← The face
│   └── tray_app.py          ← System tray icon + popup windows
│
├── ai/                      ← AI upgrade (Stage 5 — not yet)
│   └── (local AI model integration goes here)
│
├── data/                    ← Storage
│   ├── config_manager.py    ← Reads/writes settings.json
│   ├── database.py          ← SQLite database (context memory)
│   └── user_data/           ← Created automatically on first run
│       ├── settings.json
│       ├── context.db
│       └── contextos.log
│
├── utils/                   ← Helpers
│   ├── logger.py            ← Logging setup
│   └── system_check.py      ← Detects RAM/CPU, picks lite vs full mode
│
├── tests/                   ← Automated tests
│   └── test_core.py         ← Run with: pytest tests/
│
├── assets/
│   └── icons/               ← App icons go here
│
└── docs/                    ← Documentation
```

## Development

This project is being built by a complete beginner learning Python and C#.
Every file is heavily commented so you can understand exactly what each line does.

**Running on Linux/Mac for development:**
The app watcher runs in simulation mode — it generates fake app events
so you can test the full pipeline without being on Windows.

**Running on Windows:**
Install `pywin32` and `psutil` to enable real window detection.

## Built with

- Python 3.12 (core engine)
- SQLite (context memory — built into Python, no install needed)
- tkinter (popup windows — built into Python)
- pystray (system tray icon)
- Pillow (tray icon image)
- pywin32 (Windows window reader)

## Roadmap

- [x] Core engine (watcher + detector + session + database)
- [x] System tray UI with popup insights
- [ ] Full dashboard window (5 tabs)
- [ ] Meeting prep from calendar
- [ ] Local AI model integration (Phi-3 Mini)
- [ ] Windows installer (.exe setup)
- [ ] Auto-update system

## License

MIT — free to use, modify, and distribute.

---

*Built in Pakistan. Learning in public.*
"""

files['__init__.py'] = """# ContextOS package
"""

files['core/__init__.py'] = """# core package
"""

files['core/app_reader.py'] = """\"\"\"
core/app_reader.py
Deep title parser for every major app.
Window title se maximum context extract karta hai.

Har app ka title format alag hota hai — yeh module
unhe parse karke structured data deta hai.
\"\"\"
import re
import logging

logger = logging.getLogger(__name__)

# ── App name mapping from exe names ───────────────────────────────────────────
EXE_MAP = {
    "code.exe":            "VS Code",
    "code - insiders.exe": "VS Code",
    "chrome.exe":          "Chrome",
    "firefox.exe":         "Firefox",
    "msedge.exe":          "Edge",
    "opera.exe":           "Opera",
    "brave.exe":           "Brave",
    "slack.exe":           "Slack",
    "teams.exe":           "Teams",
    "msteams.exe":         "Teams",
    "outlook.exe":         "Outlook",
    "thunderbird.exe":     "Thunderbird",
    "notion.exe":          "Notion",
    "obsidian.exe":        "Obsidian",
    "figma.exe":           "Figma",
    "discord.exe":         "Discord",
    "whatsapp.exe":        "WhatsApp",
    "telegram.exe":        "Telegram",
    "zoom.exe":            "Zoom",
    "postman.exe":         "Postman",
    "insomnia.exe":        "Insomnia",
    "datagrip64.exe":      "DataGrip",
    "pycharm64.exe":       "PyCharm",
    "idea64.exe":          "IntelliJ",
    "webstorm64.exe":      "WebStorm",
    "devenv.exe":          "Visual Studio",
    "notepad.exe":         "Notepad",
    "notepad++.exe":       "Notepad++",
    "winword.exe":         "Word",
    "excel.exe":           "Excel",
    "powerpnt.exe":        "PowerPoint",
    "acrobat.exe":         "Acrobat",
    "explorer.exe":        "File Explorer",
    "wt.exe":              "Windows Terminal",
    "windowsterminal.exe": "Windows Terminal",
    "powershell.exe":      "PowerShell",
    "cmd.exe":             "Command Prompt",
    "python.exe":          "Python",
    "pythonw.exe":         "Python",
    "git-bash.exe":        "Git Bash",
    "vmware.exe":          "VMware",
    "virtualboxvm.exe":    "VirtualBox",
    "spotify.exe":         "Spotify",
    "vlc.exe":             "VLC",
    "mspaint.exe":         "Paint",
    "photoshop.exe":       "Photoshop",
    "xd.exe":              "Adobe XD",
    "illustrator.exe":     "Illustrator",
    "trello.exe":          "Trello",
    "asana.exe":           "Asana",
    "linear.exe":          "Linear",
    "warp.exe":            "Warp Terminal",
}

# ── File extensions ContextOS tracks ─────────────────────────────────────────
CODE_EXTENSIONS = (
    "py","js","ts","jsx","tsx","cs","java","cpp","c","h","go",
    "rs","kt","swift","php","rb","r","html","css","scss","json",
    "yaml","yml","xml","sql","sh","bat","ps1","md","txt","env",
    "dockerfile","toml","ini","cfg","conf"
)

FILE_PATTERN = re.compile(
    r'\\b([\\w\\-\\. ]+\\.(?:' + '|'.join(CODE_EXTENSIONS) + r'))\\b',
    re.IGNORECASE
)


class ParsedContext:
    \"\"\"Structured context extracted from one window title.\"\"\"
    def __init__(self):
        self.app_name    = ""
        self.raw_title   = ""
        self.file_name   = None
        self.project     = None
        self.email_subj  = None
        self.sender      = None
        self.channel     = None
        self.page_title  = None
        self.url_hint    = None
        self.keywords    = []
        self.event_type  = "app_switch"

    def all_text(self):
        \"\"\"Return all text fields joined for keyword extraction.\"\"\"
        parts = [self.raw_title]
        for f in [self.file_name, self.project, self.email_subj,
                  self.sender, self.channel, self.page_title]:
            if f:
                parts.append(f)
        return " ".join(parts)


class AppReader:
    \"\"\"
    Parses window titles from any app into structured ParsedContext.
    Works on ALL installed apps — not just a fixed list.
    \"\"\"

    def parse(self, exe_name: str, title: str) -> ParsedContext:
        ctx = ParsedContext()
        ctx.raw_title = title
        ctx.app_name  = self._friendly_name(exe_name, title)

        # Route to app-specific parser if we know the app
        app = ctx.app_name.lower()

        if "vs code" in app or "visual studio code" in app:
            self._parse_vscode(ctx, title)
        elif "chrome" in app or "firefox" in app or "edge" in app or "opera" in app or "brave" in app:
            self._parse_browser(ctx, title)
        elif "slack" in app:
            self._parse_slack(ctx, title)
        elif "outlook" in app or "thunderbird" in app:
            self._parse_email_client(ctx, title)
        elif "notion" in app:
            self._parse_notion(ctx, title)
        elif "figma" in app:
            self._parse_figma(ctx, title)
        elif "teams" in app:
            self._parse_teams(ctx, title)
        elif "discord" in app:
            self._parse_discord(ctx, title)
        elif "whatsapp" in app or "telegram" in app:
            self._parse_messaging(ctx, title)
        elif "zoom" in app:
            self._parse_zoom(ctx, title)
        elif "explorer" in app:
            self._parse_explorer(ctx, title)
        elif "word" in app or "excel" in app or "powerpoint" in app:
            self._parse_office(ctx, title)
        elif any(ide in app for ide in ["pycharm","intellij","webstorm","datagrip"]):
            self._parse_jetbrains(ctx, title)
        else:
            # Generic parser — works for ANY unknown app
            self._parse_generic(ctx, title)

        # Always extract file names and keywords
        if not ctx.file_name:
            ctx.file_name = self._extract_file(title)
        ctx.keywords = self._extract_keywords(ctx.all_text())

        return ctx

    # ── App-specific parsers ──────────────────────────────────────────────────

    def _parse_vscode(self, ctx, title):
        # "AuthService.ts — contextOS — Visual Studio Code"
        # "● main.py — myproject — Visual Studio Code"
        parts = re.split(r'\\s[—–-]\\s', title.replace("●","").strip())
        if len(parts) >= 2:
            ctx.file_name = parts[0].strip()
            if len(parts) >= 3:
                ctx.project = parts[1].strip()
        ctx.event_type = "file_open"

    def _parse_browser(self, ctx, title):
        # Gmail: "Inbox (12) — malak@gmail.com — Gmail"
        # Gmail email: "Re: auth flow — Sara Khan — Gmail"
        # Slack web: "general | MyWorkspace | Slack"
        # GitHub: "contextOS/main.py at main · user/contextOS"
        # Jira: "COS-123 Fix auth bug — My Project — Jira"
        # Stack Overflow: "How to fix null pointer — Stack Overflow"
        # YouTube: "ContextOS Demo — YouTube"

        low = title.lower()

        # Gmail
        if "gmail" in low:
            ctx.url_hint = "gmail"
            if " — gmail" in low or "- gmail" in low:
                parts = re.split(r'\\s[—–-]\\s|\\s-\\s', title)
                if len(parts) >= 2:
                    subj = parts[0].strip()
                    # Strip "Inbox (12)" type strings
                    if not re.match(r'inbox|sent|drafts|spam|trash', subj, re.I):
                        ctx.email_subj = subj
                        ctx.event_type = "email_read"
                    if len(parts) >= 3:
                        ctx.sender = parts[1].strip()

        # Slack web
        elif "slack" in low:
            ctx.url_hint = "slack"
            m = re.match(r'^(.+?)\\s*\\|\\s*(.+?)\\s*\\|', title)
            if m:
                ctx.channel  = m.group(1).strip()
                ctx.project  = m.group(2).strip()
                ctx.event_type = "slack_read"

        # GitHub
        elif "github" in low:
            ctx.url_hint = "github"
            # "contextOS/src/main.py at main · user/repo"
            m = re.search(r'([\\w\\-]+/[\\w\\.\\-]+)\\s+at\\s+\\w+', title)
            if m:
                ctx.file_name = m.group(1)
                ctx.event_type = "file_open"

        # Jira / Linear / Trello
        elif any(x in low for x in ["jira","linear","trello","asana"]):
            ctx.url_hint = "project_tool"
            ctx.page_title = title.split("—")[0].strip()
            ctx.event_type = "task_view"

        # Notion web
        elif "notion" in low:
            ctx.url_hint = "notion"
            ctx.page_title = title.replace("| Notion","").replace("- Notion","").strip()

        # YouTube / video
        elif "youtube" in low:
            ctx.url_hint = "youtube"
            ctx.page_title = title.replace("— YouTube","").replace("- YouTube","").strip()

        # Stack Overflow / docs
        elif "stack overflow" in low or "mdn" in low or "docs" in low:
            ctx.url_hint = "docs"
            ctx.page_title = title.split("—")[0].split("-")[0].strip()
            ctx.event_type = "search"

        # Generic web page
        else:
            ctx.page_title = title.split("—")[0].split("-")[0].strip()

    def _parse_slack(self, ctx, title):
        # Desktop: "#general — Workspace — Slack" or "Ahmed — Slack"
        parts = re.split(r'\\s—\\s|\\s-\\s', title.replace("Slack","").strip())
        if parts:
            chan = parts[0].strip().lstrip("#")
            ctx.channel = chan
            ctx.event_type = "slack_read"
        if len(parts) >= 2:
            ctx.project = parts[1].strip()

    def _parse_email_client(self, ctx, title):
        # Outlook: "RE: Auth requirements - Microsoft Outlook"
        # "Inbox - malak@email.com - Outlook"
        cleaned = re.sub(r'\\s*-\\s*(Microsoft\\s+)?Outlook\\s*$','',title,flags=re.I)
        cleaned = re.sub(r'\\s*-\\s*Thunderbird\\s*$','',cleaned,flags=re.I)
        if " - " in cleaned:
            parts = cleaned.split(" - ")
            subj  = parts[0].strip()
            if not re.match(r'inbox|sent|drafts|calendar', subj, re.I):
                ctx.email_subj = subj
                ctx.event_type = "email_read"
                if len(parts) >= 2:
                    ctx.sender = parts[1].strip()
        else:
            ctx.page_title = cleaned.strip()

    def _parse_notion(self, ctx, title):
        # "Sprint 3 | Notion" or "Sprint 3 — Notion"
        ctx.page_title = re.sub(r'\\s*[\\|—-]\\s*Notion\\s*$','',title,flags=re.I).strip()
        ctx.event_type = "task_view"

    def _parse_figma(self, ctx, title):
        # "Login_v4 – Figma" or "Mobile App — Figma"
        ctx.page_title = re.sub(r'\\s*[–—-]\\s*Figma\\s*$','',title,flags=re.I).strip()
        ctx.event_type = "design_view"

    def _parse_teams(self, ctx, title):
        # "General | My Team | Microsoft Teams"
        parts = re.split(r'\\s*\\|\\s*', title)
        if parts:
            ctx.channel = parts[0].strip()
            if len(parts) >= 2:
                ctx.project = parts[1].strip()
        ctx.event_type = "slack_read"

    def _parse_discord(self, ctx, title):
        # "#general — Server — Discord"
        parts = re.split(r'\\s—\\s', title.replace("Discord","").strip())
        if parts:
            ctx.channel = parts[0].strip().lstrip("#")
        ctx.event_type = "slack_read"

    def _parse_messaging(self, ctx, title):
        # "Ahmed — WhatsApp" or "Family Group — Telegram"
        ctx.sender = re.sub(r'\\s*—\\s*(WhatsApp|Telegram)\\s*$','',title,flags=re.I).strip()
        ctx.event_type = "slack_read"

    def _parse_zoom(self, ctx, title):
        # "Zoom Meeting" or "Sprint Review — Zoom"
        ctx.page_title = re.sub(r'\\s*—?\\s*Zoom\\s*$','',title,flags=re.I).strip()
        ctx.event_type = "meeting"

    def _parse_explorer(self, ctx, title):
        # "contextOS — C:\\Users\\..." or just a folder name
        if "\\\\" in title or "/" in title:
            ctx.project = title.split("\\\\")[-1].split("/")[-1].strip()
        else:
            ctx.project = title.strip()

    def _parse_office(self, ctx, title):
        # "Report.docx - Word" or "Budget.xlsx - Excel"
        app_names = ["Microsoft Word","Word","Microsoft Excel","Excel",
                     "Microsoft PowerPoint","PowerPoint"]
        cleaned = title
        for name in app_names:
            cleaned = cleaned.replace(" - " + name,"").replace(" — " + name,"")
        ctx.file_name  = cleaned.strip()
        ctx.event_type = "file_open"

    def _parse_jetbrains(self, ctx, title):
        # "main.py — myproject [~/projects/myproject]"
        m = re.match(r'^([^\\[—-]+)', title)
        if m:
            ctx.file_name = m.group(1).strip()
        m2 = re.search(r'\\[([^\\]]+)\\]', title)
        if m2:
            path = m2.group(1)
            ctx.project = path.split("/")[-1].split("\\\\")[-1]
        ctx.event_type = "file_open"

    def _parse_generic(self, ctx, title):
        # For any unknown app — best-effort extraction
        file = self._extract_file(title)
        if file:
            ctx.file_name  = file
            ctx.event_type = "file_open"
        else:
            # Take the first meaningful part before any separator
            parts = re.split(r'\\s[—–\\-|]\\s', title)
            if parts:
                ctx.page_title = parts[0].strip()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _friendly_name(self, exe: str, title: str) -> str:
        key = exe.lower().strip()
        if key in EXE_MAP:
            return EXE_MAP[key]
        # Fallback: clean up the exe name
        name = re.sub(r'\\d+$', '', key.replace(".exe","")).strip()
        return name.title() if name else "Unknown"

    def _extract_file(self, text: str):
        m = FILE_PATTERN.search(text)
        if m:
            fname = m.group(1).strip()
            # Filter out obvious non-filenames
            if len(fname) > 2 and not fname.startswith("."):
                return fname
        return None

    def _extract_keywords(self, text: str) -> list:
        STOP = {
            "the","a","an","and","or","in","on","at","to","for","of",
            "with","is","was","are","be","by","from","as","new","tab",
            "page","window","file","microsoft","google","app","com","www",
            "http","https","inbox","sent","draft","gmail","outlook","slack",
            "notion","figma","chrome","firefox","edge","code","visual",
            "studio","untitled","undefined","null","true","false","nan",
        }
        words = re.split(r'[^a-zA-Z0-9_]+', text)
        seen, result = set(), []
        for w in words:
            w = w.lower().strip("_")
            if len(w) >= 3 and w not in STOP and w not in seen:
                seen.add(w)
                result.append(w)
        return result[:20]
"""

files['core/app_watcher.py'] = """\"\"\"
core/app_watcher.py
Watches the active Windows window every second using win32gui.
Works on ALL installed apps — not just a fixed list.
On non-Windows (dev), runs simulation mode.
\"\"\"
import os, re, time, logging, threading
from typing import Callable, Optional
from core.app_reader import AppReader, ParsedContext

logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    try:
        import win32gui, win32process, psutil
        WIN32_OK = True
    except ImportError:
        WIN32_OK = False
        logger.warning("pywin32/psutil not installed. Run: python install_deps.py")
else:
    WIN32_OK = False


class AppEvent:
    \"\"\"One context snapshot — active window at a point in time.\"\"\"
    def __init__(self, ctx: ParsedContext):
        self.app_name    = ctx.app_name
        self.window_title= ctx.raw_title
        self.file_name   = ctx.file_name
        self.keywords    = ctx.keywords
        self.event_type  = ctx.event_type
        self.email_subj  = ctx.email_subj
        self.sender      = ctx.sender
        self.channel     = ctx.channel
        self.page_title  = ctx.page_title
        self.project     = ctx.project

    def __repr__(self):
        return f"AppEvent(app={self.app_name!r}, title={self.window_title[:40]!r})"


class AppWatcher:
    \"\"\"
    Polls the active window every `interval` seconds.
    Fires registered listeners whenever the window changes.
    Works with ALL apps installed on the PC.
    \"\"\"

    def __init__(self, config, db):
        self.config          = config
        self.db              = db
        self._reader         = AppReader()
        self._running        = False
        self._paused         = False
        self._thread: Optional[threading.Thread] = None
        self._listeners: list[Callable] = []
        self._last_title     = ""
        self._last_app       = ""
        self.events_recorded = 0
        # Track active apps seen this session
        self.seen_apps: dict[str, int] = {}

    def add_listener(self, fn: Callable):
        self._listeners.append(fn)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="AppWatcher", daemon=True)
        self._thread.start()
        mode = "REAL (win32gui)" if (IS_WINDOWS and WIN32_OK) else "SIMULATION"
        logger.info(f"AppWatcher started — mode: {mode}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info(f"AppWatcher stopped. Events: {self.events_recorded}")

    def pause(self):
        self._paused = True
        logger.info("AppWatcher paused.")

    def resume(self):
        self._paused = False
        logger.info("AppWatcher resumed.")

    def get_current(self) -> Optional[AppEvent]:
        ctx = self._read()
        return AppEvent(ctx) if ctx else None

    def get_all_seen_apps(self) -> list[str]:
        return sorted(self.seen_apps.keys(),
                      key=lambda a: self.seen_apps[a], reverse=True)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self):
        interval = float(self.config.get("watch_interval", 1.0))
        while self._running:
            try:
                if not self._paused:
                    self._tick()
            except Exception as e:
                logger.error(f"Watcher tick error: {e}")
            time.sleep(interval)

    def _tick(self):
        ctx = self._read()
        if not ctx:
            return

        # Only act on window change
        if (ctx.raw_title   == self._last_title and
                ctx.app_name == self._last_app):
            return

        self._last_title = ctx.raw_title
        self._last_app   = ctx.app_name

        # Track seen apps
        self.seen_apps[ctx.app_name] = \\
            self.seen_apps.get(ctx.app_name, 0) + 1

        # Save to DB
        extra = []
        if ctx.email_subj: extra.append(f"email:{ctx.email_subj}")
        if ctx.channel:    extra.append(f"channel:{ctx.channel}")
        if ctx.project:    extra.append(f"project:{ctx.project}")
        if ctx.page_title: extra.append(f"page:{ctx.page_title}")

        self.db.add_event(
            app_name     = ctx.app_name,
            window_title = ctx.raw_title,
            event_type   = ctx.event_type,
            file_name    = ctx.file_name,
            keywords     = ",".join(ctx.keywords),
            raw_text     = " | ".join(extra) if extra else ctx.raw_title,
        )
        self.events_recorded += 1
        logger.debug(f"Window: {ctx.app_name} | {ctx.raw_title[:60]}")

        event = AppEvent(ctx)
        for fn in self._listeners:
            try:
                fn(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def _read(self) -> Optional[ParsedContext]:
        if IS_WINDOWS and WIN32_OK:
            return self._read_windows()
        return self._read_simulation()

    def _read_windows(self) -> Optional[ParsedContext]:
        try:
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title or len(title.strip()) < 2:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                exe = psutil.Process(pid).name()
            except Exception:
                exe = "unknown.exe"
            return self._reader.parse(exe, title)
        except Exception as e:
            logger.debug(f"win32 read error: {e}")
            return None

    def _read_simulation(self) -> Optional[ParsedContext]:
        import random
        samples = [
            ("code.exe",    "AuthService.ts — contextOS — Visual Studio Code"),
            ("chrome.exe",  "Re: auth flow must not change — Sara Khan — Gmail"),
            ("slack.exe",   "#dev-mobile — MyWorkspace — Slack"),
            ("chrome.exe",  "Sprint 3 | Notion"),
            ("figma.exe",   "Login_v4 — Figma"),
            ("code.exe",    "main.py — contextOS — Visual Studio Code"),
            ("chrome.exe",  "Stack Overflow — NullPointerException Python"),
            ("chrome.exe",  "contextOS/core/app_watcher.py at main · user/contextOS — GitHub"),
            ("outlook.exe", "RE: Auth requirements - Microsoft Outlook"),
            ("teams.exe",   "General | Dev Team | Microsoft Teams"),
            ("chrome.exe",  "COS-123 Fix login bug — MyProject — Jira"),
            ("whatsapp.exe","Ahmed Khan — WhatsApp"),
        ]
        exe, title = random.choice(samples)
        return self._reader.parse(exe, title)

    def is_watched(self, app_name: str) -> bool:
        watched = self.config.get("watched_apps", [])
        return any(w.lower() in app_name.lower() for w in watched)
"""

files['core/conflict_detector.py'] = """\"\"\"
core/conflict_detector.py
15 real conflict rules — covers all major app combinations.
Works purely on keyword matching. No AI needed.
\"\"\"
import logging, time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Insight:
    insight_type: str
    title:        str
    detail:       str
    source_apps:  list
    confidence:   float = 1.0
    id:           Optional[int] = None
    def __repr__(self):
        return f"Insight({self.insight_type!r}: {self.title!r})"


RULES = [
    # ── Code vs Communication ──────────────────────────────────────────────────
    {
        "name":     "code_vs_email",
        "apps_a":   {"VS Code","PyCharm","IntelliJ","WebStorm","Visual Studio"},
        "apps_b":   {"Gmail","Outlook","Thunderbird"},
        "type":     "conflict",
        "title":    'Conflict: "{kw}" in email and in your code',
        "detail":   'You have an email mentioning "{kw}" and are currently editing a file with the same name. Check if the email contains instructions about this code before continuing.',
    },
    {
        "name":     "code_vs_slack",
        "apps_a":   {"VS Code","PyCharm","IntelliJ","WebStorm","Visual Studio"},
        "apps_b":   {"Slack","Teams","Discord"},
        "type":     "answer",
        "title":    'Slack may have the answer for "{kw}"',
        "detail":   'A recent Slack or Teams message mentions "{kw}" which matches what you are working on right now. The fix or answer may already be there.',
    },
    {
        "name":     "code_vs_jira",
        "apps_a":   {"VS Code","PyCharm","IntelliJ"},
        "apps_b":   {"Chrome","Edge","Firefox"},
        "type":     "auto_update",
        "title":    'Task "{kw}" may need updating in your project tool',
        "detail":   'You have been working on "{kw}" in your editor and a Jira or Linear task with that name is open in your browser. Consider marking it in-progress.',
    },
    # ── Design vs Code ────────────────────────────────────────────────────────
    {
        "name":     "figma_vs_code",
        "apps_a":   {"Figma","Adobe XD","Illustrator"},
        "apps_b":   {"VS Code","PyCharm","IntelliJ","Chrome"},
        "type":     "conflict",
        "title":    'Design and code both mention "{kw}" — are they in sync?',
        "detail":   'Your Figma design and your code file both reference "{kw}". Make sure the implementation matches the latest design — design changes may not be reflected in code yet.',
    },
    # ── Email conflicts ────────────────────────────────────────────────────────
    {
        "name":     "email_vs_notion",
        "apps_a":   {"Gmail","Outlook","Thunderbird"},
        "apps_b":   {"Notion","Obsidian","Chrome"},
        "type":     "conflict",
        "title":    'Email and your notes both mention "{kw}"',
        "detail":   'An email and your Notion notes both discuss "{kw}". There may be new information in the email that should update your notes or task list.',
    },
    {
        "name":     "email_vs_slack",
        "apps_a":   {"Gmail","Outlook"},
        "apps_b":   {"Slack","Teams"},
        "type":     "answer",
        "title":    'Email and Slack both discuss "{kw}"',
        "detail":   'Both your email and a Slack message mention "{kw}". Check both — there may be conflicting information or a decision you need to align on.',
    },
    # ── Browser research ──────────────────────────────────────────────────────
    {
        "name":     "browser_vs_code",
        "apps_a":   {"Chrome","Firefox","Edge","Brave","Opera"},
        "apps_b":   {"VS Code","PyCharm","IntelliJ"},
        "type":     "answer",
        "title":    'Your browser research on "{kw}" matches your current code',
        "detail":   'You searched for "{kw}" in your browser and are now editing a file with the same topic. The solution you found may apply directly to your current task.',
    },
    # ── Meeting context ────────────────────────────────────────────────────────
    {
        "name":     "zoom_vs_code",
        "apps_a":   {"Zoom","Teams"},
        "apps_b":   {"VS Code","Notion","Chrome"},
        "type":     "meeting_prep",
        "title":    'Active meeting — "{kw}" also appears in your work',
        "detail":   'You are in a meeting and your other apps show recent activity on "{kw}". This topic may come up — your context trail has relevant information ready.',
    },
    # ── Slack answers ─────────────────────────────────────────────────────────
    {
        "name":     "slack_vs_notion",
        "apps_a":   {"Slack","Teams","Discord"},
        "apps_b":   {"Notion","Obsidian"},
        "type":     "auto_update",
        "title":    'Slack discussion on "{kw}" — update your notes?',
        "detail":   'A Slack conversation about "{kw}" may contain decisions or information that should be added to your Notion notes. Check the thread.',
    },
    # ── File conflicts ─────────────────────────────────────────────────────────
    {
        "name":     "github_vs_code",
        "apps_a":   {"Chrome","Firefox","Edge"},
        "apps_b":   {"VS Code","PyCharm"},
        "type":     "conflict",
        "title":    'GitHub and local code both show "{kw}"',
        "detail":   'You are viewing "{kw}" on GitHub and also editing it locally. Make sure you have pulled the latest changes — your local version may be behind the remote.',
    },
    # ── WhatsApp / Telegram ───────────────────────────────────────────────────
    {
        "name":     "whatsapp_vs_code",
        "apps_a":   {"WhatsApp","Telegram"},
        "apps_b":   {"VS Code","PyCharm","Notion","Chrome"},
        "type":     "answer",
        "title":    'Message about "{kw}" — relevant to your current work',
        "detail":   'A WhatsApp or Telegram message mentions "{kw}" which is also your current focus. The message may contain useful information for what you are working on.',
    },
    # ── Excel/Office ──────────────────────────────────────────────────────────
    {
        "name":     "excel_vs_code",
        "apps_a":   {"Excel","Word","PowerPoint"},
        "apps_b":   {"VS Code","Chrome","Notion"},
        "type":     "answer",
        "title":    'Office document and your work both mention "{kw}"',
        "detail":   'An Office document and your current task share the topic "{kw}". The document may contain specifications, data, or requirements relevant to what you are doing.',
    },
    # ── Terminal / deployment ─────────────────────────────────────────────────
    {
        "name":     "terminal_vs_code",
        "apps_a":   {"Windows Terminal","PowerShell","Command Prompt","Git Bash","Warp Terminal"},
        "apps_b":   {"VS Code","Chrome"},
        "type":     "auto_update",
        "title":    'Terminal activity on "{kw}" while editing it in your editor',
        "detail":   'You are running commands related to "{kw}" in your terminal and also editing files with that name. This may be a deployment, test, or build run — check the output.',
    },
    # ── Postman / API ─────────────────────────────────────────────────────────
    {
        "name":     "postman_vs_code",
        "apps_a":   {"Postman","Insomnia"},
        "apps_b":   {"VS Code","Chrome"},
        "type":     "answer",
        "title":    'API test on "{kw}" — matches your current code',
        "detail":   'You are testing an API endpoint related to "{kw}" in Postman while editing the same in your code editor. Results from your API test may be directly relevant.',
    },
    # ── Spotify / distraction alert ───────────────────────────────────────────
    {
        "name":     "deep_focus",
        "apps_a":   {"VS Code","PyCharm"},
        "apps_b":   {"VS Code","PyCharm"},
        "type":     "auto_update",
        "title":    'Deep focus on "{kw}" detected — 15+ minutes',
        "detail":   'You have been actively working on "{kw}" for a significant time. Consider marking the related task as in-progress if you have not already.',
    },
]


class ConflictDetector:
    def __init__(self, config, db):
        self.config    = config
        self.db        = db
        self._fired: dict[str, float] = {}
        self._cooldown = 300   # 5 min between same insight

    def analyse(self) -> list[Insight]:
        recent = self.db.get_recent_events(limit=60, hours=2)
        if len(recent) < 2:
            return []

        # Build app→keywords map
        app_kws: dict[str, set] = {}
        app_meta: dict[str, dict] = {}   # extra structured data

        for ev in recent:
            app = ev["app_name"]
            kws = set(k.strip().lower()
                      for k in (ev.get("keywords") or "").split(",")
                      if k.strip())
            if app not in app_kws:
                app_kws[app]  = set()
                app_meta[app] = {}
            app_kws[app] |= kws

            # Grab structured fields from raw_text
            raw = ev.get("raw_text") or ""
            for part in raw.split(" | "):
                if ":" in part:
                    k, v = part.split(":", 1)
                    app_meta[app][k.strip()] = v.strip()

        results = []
        for rule in RULES:
            ins = self._check_rule(rule, app_kws)
            if ins:
                ins.id = self.db.add_insight(
                    ins.insight_type, ins.title,
                    ins.detail, ",".join(ins.source_apps))
                results.append(ins)
        return results

    def analyse_single_event(self, event) -> list[Insight]:
        if not event or not event.keywords:
            return []

        recent = self.db.get_recent_events(limit=40, hours=1)
        results = []

        for ev in recent:
            if ev["app_name"] == event.app_name:
                continue
            db_kws  = set(k.strip().lower()
                          for k in (ev.get("keywords") or "").split(",")
                          if k.strip())
            new_kws = set(k.lower() for k in event.keywords)
            shared  = {k for k in db_kws & new_kws if len(k) >= 4}
            if not shared:
                continue

            kw  = max(shared, key=len)
            key = f"quick_{event.app_name}_{ev['app_name']}_{kw}"
            if self._on_cd(key):
                continue

            itype = self._guess_type(event.app_name, ev["app_name"])
            title = f'"{kw}" — seen in {event.app_name} and {ev["app_name"]}'
            detail= (f'Your {event.app_name} window and a recent {ev["app_name"]} '
                     f'event both mention "{kw}". This may be directly relevant '
                     f'to what you are working on right now.')
            ins = Insight(itype, title, detail,
                          [event.app_name, ev["app_name"]],
                          min(1.0, len(shared) * 0.3))
            ins.id = self.db.add_insight(
                ins.insight_type, ins.title,
                ins.detail, ",".join(ins.source_apps))
            self._mark(key)
            results.append(ins)
            if len(results) >= 2:
                break

        return results

    def _check_rule(self, rule, app_kws) -> Optional[Insight]:
        active = set(app_kws.keys())

        # Find which apps from set_a and set_b are currently active
        matched_a = [a for a in active
                     if any(t.lower() in a.lower() for t in rule["apps_a"])]
        matched_b = [a for a in active
                     if any(t.lower() in a.lower() for t in rule["apps_b"])]

        # Need at least one from each group (or both from same group)
        if rule["apps_a"] == rule["apps_b"]:
            if len(matched_a) < 1:
                return None
            matches = matched_a
        else:
            if not matched_a or not matched_b:
                return None
            matches = matched_a + matched_b

        # Find shared keywords across matched apps
        all_kws: set = set()
        for a in matches:
            all_kws |= app_kws[a]

        shared = {kw for kw in all_kws
                  if len(kw) >= 4 and
                  sum(1 for a in matches if kw in app_kws[a]) >= 2}

        if not shared:
            return None

        kw  = max(shared, key=len)
        key = f"{rule['name']}_{kw}"
        if self._on_cd(key):
            return None
        self._mark(key)

        return Insight(
            insight_type = rule["type"],
            title        = rule["title"].format(kw=kw),
            detail       = rule["detail"].format(kw=kw),
            source_apps  = matches[:3],
            confidence   = min(1.0, len(shared) * 0.2 + 0.4),
        )

    def _on_cd(self, key):
        return (time.time() - self._fired.get(key, 0)) < self._cooldown

    def _mark(self, key):
        self._fired[key] = time.time()

    def _guess_type(self, app1, app2):
        comms = {"slack","teams","gmail","outlook","discord",
                 "whatsapp","telegram"}
        if any(c in app1.lower() or c in app2.lower() for c in comms):
            return "answer"
        return "conflict"
"""

files['core/context_engine.py'] = """\"\"\"
core/context_engine.py
The orchestrator. Connects the AppWatcher to the ConflictDetector
and runs the periodic full-analysis loop.

Responsibilities:
  - Receive AppEvents from AppWatcher in real-time
  - Run quick conflict checks on each new event
  - Every N seconds, run a full analysis of all recent events
  - Monitor CPU and trigger pause/resume on AppWatcher
  - Notify the UI layer when new insights are ready
\"\"\"

import time
import logging
import threading
import os
from typing import Callable

from core.conflict_detector import ConflictDetector, Insight

logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"


class ContextEngine:
    \"\"\"
    Sits between the watcher (input) and the UI (output).

    Usage:
        engine = ContextEngine(config, db)
        engine.add_insight_listener(my_ui_callback)
        engine.start(watcher, detector)
        ...
        engine.stop()
    \"\"\"

    def __init__(self, config, db):
        self.config   = config
        self.db       = db
        self._running = False
        self._paused  = False
        self._thread  = None

        # Callbacks to call when a new insight is ready
        self._insight_listeners: list[Callable[[Insight], None]] = []

        # Stats for the dashboard
        self.stats = {
            "insights_today":   0,
            "conflicts_caught": 0,
            "tasks_auto_done":  0,
            "focus_minutes":    0,
        }

        self._watcher  = None
        self._detector = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_insight_listener(self, fn: Callable[[Insight], None]):
        \"\"\"Register a callback called whenever a new insight is created.\"\"\"
        self._insight_listeners.append(fn)

    def start(self, watcher, detector: ConflictDetector):
        \"\"\"Start the engine. Wires up the watcher listener and analysis loop.\"\"\"
        self._watcher  = watcher
        self._detector = detector

        # Wire: every new AppEvent from the watcher comes here first
        watcher.add_listener(self._on_app_event)
        watcher.start()

        # Start the periodic full-analysis loop in a background thread
        self._running = True
        self._thread = threading.Thread(
            target=self._analysis_loop,
            name="ContextEngine",
            daemon=True,
        )
        self._thread.start()
        logger.info("ContextEngine started.")

    def stop(self):
        \"\"\"Gracefully stop everything.\"\"\"
        self._running = False
        if self._watcher:
            self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ContextEngine stopped.")

    def get_stats(self) -> dict:
        \"\"\"Return today's stats for the dashboard Home tab.\"\"\"
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    self.stats["focus_minutes"],
        }

    # ── Real-time event handler ────────────────────────────────────────────────

    def _on_app_event(self, event):
        \"\"\"Called by AppWatcher every time the active window changes.\"\"\"
        if self._paused:
            return

        # Run a quick check comparing the new event against recent history
        try:
            quick_insights = self._detector.analyse_single_event(event)
            for insight in quick_insights:
                self._dispatch_insight(insight)
        except Exception as e:
            logger.error(f"Quick analysis error: {e}")

    # ── Periodic full-analysis loop ────────────────────────────────────────────

    def _analysis_loop(self):
        \"\"\"Every N seconds, run a full analysis of all recent events.\"\"\"
        interval = int(self.config.get("analysis_interval", 30))
        while self._running:
            time.sleep(interval)
            if not self._running:
                break
            if self._paused:
                continue

            # CPU guard — pause analysis if system is under load
            if self.config.get("smart_pause", True):
                cpu = self._get_cpu_percent()
                threshold = int(self.config.get("smart_pause_threshold", 80))
                if cpu > threshold:
                    logger.info(f"CPU at {cpu:.0f}% — pausing analysis.")
                    self._paused = True
                    if self._watcher:
                        self._watcher.pause()
                    continue
                elif self._paused and cpu < threshold - 10:
                    logger.info(f"CPU at {cpu:.0f}% — resuming analysis.")
                    self._paused = False
                    if self._watcher:
                        self._watcher.resume()

            try:
                insights = self._detector.analyse()
                for insight in insights:
                    self._dispatch_insight(insight)

                # Update focus time counter
                self.stats["focus_minutes"] += interval // 60

            except Exception as e:
                logger.error(f"Full analysis error: {e}")

    # ── Dispatch ───────────────────────────────────────────────────────────────

    def _dispatch_insight(self, insight: Insight):
        \"\"\"Send a new insight to all registered UI listeners.\"\"\"
        logger.info(f"Dispatching insight: {insight}")
        for fn in self._insight_listeners:
            try:
                fn(insight)
            except Exception as e:
                logger.error(f"Insight listener error: {e}")

    # ── CPU monitoring ─────────────────────────────────────────────────────────

    def _get_cpu_percent(self) -> float:
        \"\"\"Return current overall CPU usage as a percentage (0–100).\"\"\"
        if IS_WINDOWS:
            try:
                import psutil
                return psutil.cpu_percent(interval=1)
            except Exception:
                return 0.0
        else:
            # Linux development: read from /proc/stat
            try:
                with open("/proc/stat") as f:
                    line = f.readline()
                fields = list(map(int, line.split()[1:]))
                idle  = fields[3]
                total = sum(fields)
                # Simple non-blocking approximation
                return max(0.0, 100.0 - (idle / total * 100.0))
            except Exception:
                return 0.0
"""

files['core/session_manager.py'] = """\"\"\"
core/session_manager.py
Tracks user work sessions.

Detects:
  - When a new session starts (user becomes active after idle)
  - When user goes away (idle for > 5 minutes)
  - What they were working on when they left
  - What changed while they were away

Feeds the "Resume screen" shown when the user returns.
\"\"\"

import time
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

IDLE_THRESHOLD_MINUTES = 5    # away this long = new session on return
AWAY_CHECK_INTERVAL    = 30   # check for idle every 30 seconds


class SessionManager:
    \"\"\"
    Monitors active/idle state and manages session lifecycle.

    Usage:
        session = SessionManager(config, db)
        session.set_away_listener(my_callback)      # called when user goes away
        session.set_return_listener(my_callback)    # called when user comes back
        session.start()
    \"\"\"

    def __init__(self, config, db):
        self.config   = config
        self.db       = db
        self._running = False
        self._thread  = None

        # Current session state
        self._session_id: int | None = None
        self._last_active_time       = time.time()
        self._is_away                = False
        self._away_start_time: float | None = None

        # Callbacks for the UI
        self._away_listeners:   list = []
        self._return_listeners: list = []

        # What the user had open when they went away
        self._snapshot_on_away: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_away_listener(self, fn):
        \"\"\"fn() called when user goes idle/away.\"\"\"
        self._away_listeners.append(fn)

    def set_return_listener(self, fn):
        \"\"\"fn(resume_data: dict) called when user comes back.\"\"\"
        self._return_listeners.append(fn)

    def notify_activity(self, event=None):
        \"\"\"
        Call this whenever an AppEvent fires — proves the user is active.
        If they were away, trigger the return flow.
        \"\"\"
        now = time.time()
        if self._is_away:
            self._handle_return(now)
        self._last_active_time = now

    def start(self):
        \"\"\"Start monitoring in a background thread.\"\"\"
        self._session_id = self.db.start_session()
        self._running    = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="SessionManager",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"SessionManager started. Session ID: {self._session_id}")

    def stop(self):
        \"\"\"End the current session and stop monitoring.\"\"\"
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._session_id:
            self.db.end_session(
                session_id = self._session_id,
                focus_topic = self._detect_focus_topic(),
                app_list    = self._get_recent_apps(),
            )
        logger.info("SessionManager stopped.")

    def get_resume_data(self) -> dict:
        \"\"\"
        Build the data shown on the Resume screen.
        Called when the user returns from being away.
        \"\"\"
        away_minutes = 0
        if self._away_start_time:
            away_minutes = int((time.time() - self._away_start_time) / 60)

        # What the user had open right before going away
        restore_items = self._build_restore_items()

        # What changed in the DB while they were gone
        changes = self._detect_changes_while_away()

        return {
            "away_minutes":  away_minutes,
            "restore_items": restore_items,
            "changes":       changes,
            "focus_topic":   self._detect_focus_topic(),
        }

    # ── Internal loop ──────────────────────────────────────────────────────────

    def _monitor_loop(self):
        while self._running:
            time.sleep(AWAY_CHECK_INTERVAL)
            if not self._running:
                break

            idle_seconds = time.time() - self._last_active_time
            idle_minutes = idle_seconds / 60

            if not self._is_away and idle_minutes >= IDLE_THRESHOLD_MINUTES:
                self._handle_away()

    # ── Away / return handlers ─────────────────────────────────────────────────

    def _handle_away(self):
        \"\"\"User has gone idle.\"\"\"
        self._is_away        = True
        self._away_start_time = time.time()

        # Take a snapshot of recent context before they disappear
        self._snapshot_on_away = self.db.get_recent_events(limit=10, hours=1)

        logger.info("User went away — session snapshot taken.")
        for fn in self._away_listeners:
            try:
                fn()
            except Exception as e:
                logger.error(f"Away listener error: {e}")

    def _handle_return(self, now: float):
        \"\"\"User has come back.\"\"\"
        self._is_away = False
        resume_data   = self.get_resume_data()
        self._away_start_time = None

        logger.info(f"User returned. Away for ~{resume_data['away_minutes']} min.")
        for fn in self._return_listeners:
            try:
                fn(resume_data)
            except Exception as e:
                logger.error(f"Return listener error: {e}")

    # ── Context helpers ────────────────────────────────────────────────────────

    def _detect_focus_topic(self) -> str:
        \"\"\"
        Guess what the user was mainly working on by finding
        the most frequent keyword in the last hour of events.
        \"\"\"
        keywords = self.db.get_keywords_last_n_events(n=30)
        if not keywords:
            return "Unknown project"

        freq: dict[str, int] = {}
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1

        # Return the most common non-trivial keyword
        best = max(freq, key=lambda k: freq[k] if len(k) >= 4 else 0, default="")
        return best.title() if best else "General work"

    def _get_recent_apps(self) -> str:
        \"\"\"Comma-separated list of apps used in the last hour.\"\"\"
        events = self.db.get_recent_events(limit=50, hours=1)
        seen   = []
        for e in events:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return ",".join(seen[:8])

    def _build_restore_items(self) -> list[dict]:
        \"\"\"
        Build the list of 'restore' items for the Resume screen.
        Each item represents a file or context the user should jump back to.
        \"\"\"
        items  = []
        events = self._snapshot_on_away or self.db.get_recent_events(limit=10, hours=2)

        seen_titles = set()
        for event in events:
            title = event.get("window_title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            items.append({
                "app":        event.get("app_name", ""),
                "title":      title,
                "file_name":  event.get("file_name"),
                "timestamp":  event.get("timestamp", ""),
            })
            if len(items) >= 4:
                break

        return items

    def _detect_changes_while_away(self) -> list[dict]:
        \"\"\"
        Find insights that were generated while the user was away.
        These show up as "What happened while you were away" on the Resume screen.
        \"\"\"
        if not self._away_start_time:
            return []

        away_start_iso = datetime.utcfromtimestamp(self._away_start_time).isoformat()
        all_insights   = self.db.get_active_insights(limit=20)

        # Filter to only those created after the user went away
        changes = []
        for ins in all_insights:
            ts = ins.get("timestamp", "")
            if ts >= away_start_iso:
                changes.append({
                    "type":   ins.get("insight_type", "info"),
                    "title":  ins.get("title", ""),
                    "source": ins.get("source_apps", ""),
                })
        return changes[:5]
"""

files['core/meeting_monitor.py'] = """\"\"\"
core/meeting_monitor.py
Detects upcoming meetings and triggers briefing 5 min before.
Checks: Outlook calendar, Google Calendar (browser title), Zoom, Teams.
\"\"\"
import re, time, logging, threading
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt" if __import__("os").name == "nt" else False


class Meeting:
    def __init__(self, title: str, start_time: datetime,
                 source: str = "detected"):
        self.title      = title
        self.start_time = start_time
        self.source     = source
        self.briefed    = False

    def minutes_until(self) -> float:
        now = datetime.now(timezone.utc)
        st  = self.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        return (st - now).total_seconds() / 60


class MeetingMonitor:
    \"\"\"
    Checks for upcoming meetings every 60 seconds.
    When a meeting is 5 minutes away, calls the briefing callback.

    Sources:
      1. Outlook COM object (Windows, needs pywin32)
      2. Window title detection (Zoom, Teams, Google Meet in browser)
      3. Manual meetings added by user
    \"\"\"

    def __init__(self, config, db, watcher=None):
        self.config   = config
        self.db       = db
        self.watcher  = watcher
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._meetings: list[Meeting] = []
        self._briefing_callbacks: list[Callable] = []
        self._checked: set = set()

    def add_briefing_callback(self, fn: Callable):
        self._briefing_callbacks.append(fn)

    def start(self):
        if not self.config.get("meeting_briefing", True):
            logger.info("Meeting briefing disabled in settings.")
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="MeetingMonitor", daemon=True)
        self._thread.start()
        logger.info("MeetingMonitor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def add_manual_meeting(self, title: str, minutes_from_now: int):
        \"\"\"Add a meeting manually (for testing or user input).\"\"\"
        from datetime import timedelta
        start = datetime.now(timezone.utc).replace(
            second=0, microsecond=0)
        start += timedelta(minutes=minutes_from_now)
        m = Meeting(title, start, "manual")
        self._meetings.append(m)
        logger.info(f"Manual meeting added: {title} in {minutes_from_now} min")

    def _loop(self):
        while self._running:
            try:
                self._refresh_meetings()
                self._check_upcoming()
            except Exception as e:
                logger.error(f"MeetingMonitor error: {e}")
            time.sleep(60)

    def _refresh_meetings(self):
        \"\"\"Try to read real calendar data.\"\"\"
        # Method 1: Outlook via COM (Windows only)
        self._try_outlook()
        # Method 2: Detect from window titles (Zoom joining, Teams)
        self._detect_from_titles()

    def _try_outlook(self):
        if not IS_WINDOWS:
            return
        try:
            import win32com.client
            outlook  = win32com.client.Dispatch("Outlook.Application")
            ns       = outlook.GetNamespace("MAPI")
            calendar = ns.GetDefaultFolder(9)  # 9 = olFolderCalendar
            items    = calendar.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]")

            from datetime import timedelta
            now      = datetime.now()
            end_time = now + timedelta(hours=2)
            items.Restrict(
                f"[Start] >= '{now.strftime('%m/%d/%Y %H:%M')}' "
                f"AND [Start] <= '{end_time.strftime('%m/%d/%Y %H:%M')}'"
            )

            existing_titles = {m.title for m in self._meetings}
            for item in items:
                try:
                    title = item.Subject
                    start = item.Start
                    if title not in existing_titles:
                        # Convert COM datetime to Python datetime
                        from pywintypes import Time
                        import pythoncom
                        dt = datetime(start.year, start.month, start.day,
                                     start.hour, start.minute,
                                     tzinfo=timezone.utc)
                        self._meetings.append(Meeting(title, dt, "outlook"))
                        logger.info(f"Outlook meeting found: {title}")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Outlook COM not available: {e}")

    def _detect_from_titles(self):
        \"\"\"Detect meetings from Zoom/Teams window titles.\"\"\"
        if not self.watcher:
            return
        event = self.watcher.get_current()
        if not event:
            return

        title = event.window_title.lower()
        app   = event.app_name.lower()

        meeting_signals = [
            "zoom meeting", "zoom call",
            "microsoft teams meeting", "teams call",
            "google meet", "meet.google",
            "whereby", "webex",
        ]
        if any(sig in title or sig in app for sig in meeting_signals):
            meeting_title = event.window_title.split("—")[0].strip()
            key = f"window_{meeting_title}"
            if key not in self._checked:
                self._checked.add(key)
                now = datetime.now(timezone.utc)
                self._meetings.append(Meeting(meeting_title, now, "window"))
                logger.info(f"Meeting detected from window: {meeting_title}")

    def _check_upcoming(self):
        \"\"\"Check if any meeting is ~5 minutes away.\"\"\"
        now = datetime.now(timezone.utc)
        for meeting in self._meetings[:]:
            if meeting.briefed:
                continue
            mins = meeting.minutes_until()
            if 0 <= mins <= 6:   # 0–6 minutes window
                meeting.briefed = True
                logger.info(f"Meeting briefing triggered: {meeting.title}")
                briefing = self._build_briefing(meeting)
                for fn in self._briefing_callbacks:
                    try:
                        fn(briefing)
                    except Exception as e:
                        logger.error(f"Briefing callback error: {e}")
            # Remove past meetings
            if mins < -30:
                self._meetings.remove(meeting)

    def _build_briefing(self, meeting: Meeting) -> dict:
        \"\"\"Build the context briefing for a meeting.\"\"\"
        recent  = self.db.get_recent_events(limit=30, hours=4)
        insights= self.db.get_active_insights(limit=10)

        # Find relevant events (keyword match with meeting title)
        meeting_kws = set(
            w.lower() for w in re.split(r'\\W+', meeting.title)
            if len(w) >= 3
        )

        relevant_events = []
        for ev in recent:
            ev_kws = set((ev.get("keywords") or "").lower().split(","))
            if ev_kws & meeting_kws:
                relevant_events.append(ev)

        # Recent files opened
        files = []
        for ev in recent:
            f = ev.get("file_name")
            if f and f not in files:
                files.append(f)

        return {
            "meeting_title":    meeting.title,
            "minutes_until":    int(meeting.minutes_until()),
            "relevant_events":  relevant_events[:5],
            "active_insights":  insights[:3],
            "recent_files":     files[:4],
            "source":           meeting.source,
        }
"""

files['core/startup_manager.py'] = """\"\"\"
core/startup_manager.py
Windows startup management — adds/removes ContextOS from Windows Registry
so it launches automatically when the PC boots.
\"\"\"
import os, sys, logging

logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"
APP_NAME   = "ContextOS"


def add_to_startup():
    \"\"\"Add ContextOS to Windows startup via Registry.\"\"\"
    if not IS_WINDOWS:
        logger.info("Startup manager: not on Windows, skipping.")
        return False
    try:
        import winreg
        key  = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
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
    \"\"\"Remove ContextOS from Windows startup.\"\"\"
    if not IS_WINDOWS:
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
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
    \"\"\"Check if ContextOS is currently in Windows startup.\"\"\"
    if not IS_WINDOWS:
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
"""

files['data/__init__.py'] = """# data package
"""

files['data/config_manager.py'] = """\"\"\"
data/config_manager.py
Reads and writes the user's settings to settings.json.
Every setting has a safe default so the app always works,
even on first run when no settings file exists yet.
\"\"\"

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
    \"\"\"
    Simple JSON-based config manager.

    Usage:
        config = ConfigManager()
        mode = config.get("mode")           # → "lite" / "full" / ...
        config.set("mode", "full")
        config.save()                       # writes to disk immediately
    \"\"\"

    def __init__(self):
        self._data = {}
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, key, fallback=None):
        \"\"\"Return a setting value. Falls back to DEFAULTS, then fallback.\"\"\"
        return self._data.get(key, DEFAULTS.get(key, fallback))

    def set(self, key, value):
        \"\"\"Update a setting and save to disk immediately.\"\"\"
        self._data[key] = value
        self._save()
        logger.debug(f"Config: {key} = {value!r}")

    def get_all(self):
        \"\"\"Return a merged dict of defaults + current settings.\"\"\"
        merged = dict(DEFAULTS)
        merged.update(self._data)
        return merged

    def reset_to_defaults(self):
        \"\"\"Wipe all settings and revert to defaults.\"\"\"
        self._data = dict(DEFAULTS)
        self._save()
        logger.info("Config reset to defaults.")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load(self):
        \"\"\"Load settings.json from disk. Creates it if missing.\"\"\"
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
        \"\"\"Write current settings to disk.\"\"\"
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Could not save settings.json: {e}")
"""

files['data/database.py'] = """\"\"\"
data/database.py
SQLite database that stores all of ContextOS's memory:
  - context_events  : every app switch, file open, email read
  - insights        : every conflict/answer/auto-update detected
  - sessions        : work session start/end records

SQLite is built into Python — no install needed.
The database file lives at:  data/user_data/context.db
\"\"\"

import sqlite3
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR   = os.path.join(BASE_DIR, "data", "user_data")
DB_PATH  = os.path.join(DB_DIR, "context.db")


class Database:
    \"\"\"
    Thin wrapper around SQLite.
    Every public method opens its own connection so this is safe
    to call from background threads.
    \"\"\"

    def __init__(self):
        self.db_path = DB_PATH
        os.makedirs(DB_DIR, exist_ok=True)

    # ── Schema setup ───────────────────────────────────────────────────────────

    def initialize(self):
        \"\"\"Create tables if they don't exist yet. Safe to call on every start.\"\"\"
        with self._connect() as conn:
            conn.executescript(\"\"\"
                -- Every time the active app or file changes
                CREATE TABLE IF NOT EXISTS context_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    app_name    TEXT    NOT NULL,
                    window_title TEXT   NOT NULL,
                    file_name   TEXT,
                    event_type  TEXT    NOT NULL,  -- 'app_switch','file_open','search','email_read'
                    keywords    TEXT,              -- comma-separated keywords extracted from title
                    raw_text    TEXT               -- full window title / content snippet
                );

                -- Every insight ContextOS generates
                CREATE TABLE IF NOT EXISTS insights (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT    NOT NULL,
                    insight_type TEXT    NOT NULL,  -- 'conflict','answer','auto_update','meeting_prep'
                    title        TEXT    NOT NULL,
                    detail       TEXT,
                    source_apps  TEXT,              -- comma-separated: "VS Code,Gmail"
                    dismissed    INTEGER DEFAULT 0,
                    acted_on     INTEGER DEFAULT 0
                );

                -- Work sessions
                CREATE TABLE IF NOT EXISTS sessions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time   TEXT    NOT NULL,
                    end_time     TEXT,
                    focus_topic  TEXT,              -- detected main topic of the session
                    app_list     TEXT,              -- comma-separated apps used
                    tasks_done   INTEGER DEFAULT 0,
                    conflicts_caught INTEGER DEFAULT 0
                );

                -- Simple key-value store for anything else
                CREATE TABLE IF NOT EXISTS kv_store (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            \"\"\")
        logger.info(f"Database ready at {self.db_path}")

    # ── context_events ─────────────────────────────────────────────────────────

    def add_event(self, app_name: str, window_title: str,
                  event_type: str, file_name: str = None,
                  keywords: str = None, raw_text: str = None):
        \"\"\"Record a new context event (app switch, file open, etc.).\"\"\"
        sql = \"\"\"
            INSERT INTO context_events
                (timestamp, app_name, window_title, file_name,
                 event_type, keywords, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        \"\"\"
        with self._connect() as conn:
            conn.execute(sql, (
                self._now(), app_name, window_title, file_name,
                event_type, keywords, raw_text
            ))
        logger.debug(f"Event recorded: [{event_type}] {app_name} — {window_title}")

    def get_recent_events(self, limit: int = 20, hours: int = 24) -> list[dict]:
        \"\"\"Return the most recent context events as a list of dicts.\"\"\"
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        sql = \"\"\"
            SELECT * FROM context_events
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        \"\"\"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (since, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_keywords_last_n_events(self, n: int = 30) -> list[str]:
        \"\"\"Return a flat list of all keywords from the last N events.\"\"\"
        sql = "SELECT keywords FROM context_events ORDER BY timestamp DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(sql, (n,)).fetchall()
        keywords = []
        for row in rows:
            if row[0]:
                keywords.extend(row[0].split(","))
        return [k.strip().lower() for k in keywords if k.strip()]

    # ── insights ───────────────────────────────────────────────────────────────

    def add_insight(self, insight_type: str, title: str,
                    detail: str = None, source_apps: str = None) -> int:
        \"\"\"Save a new insight. Returns its new ID.\"\"\"
        sql = \"\"\"
            INSERT INTO insights (timestamp, insight_type, title, detail, source_apps)
            VALUES (?, ?, ?, ?, ?)
        \"\"\"
        with self._connect() as conn:
            cur = conn.execute(sql, (
                self._now(), insight_type, title, detail, source_apps
            ))
            return cur.lastrowid

    def get_active_insights(self, limit: int = 10) -> list[dict]:
        \"\"\"Return insights that have not been dismissed.\"\"\"
        sql = \"\"\"
            SELECT * FROM insights
            WHERE dismissed = 0
            ORDER BY timestamp DESC
            LIMIT ?
        \"\"\"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def dismiss_insight(self, insight_id: int):
        \"\"\"Mark an insight as dismissed.\"\"\"
        with self._connect() as conn:
            conn.execute(
                "UPDATE insights SET dismissed = 1 WHERE id = ?",
                (insight_id,)
            )

    def get_insight_count_today(self) -> dict:
        \"\"\"Return today's insight counts by type.\"\"\"
        today = datetime.utcnow().date().isoformat()
        sql = \"\"\"
            SELECT insight_type, COUNT(*) as cnt
            FROM insights
            WHERE timestamp >= ?
            GROUP BY insight_type
        \"\"\"
        with self._connect() as conn:
            rows = conn.execute(sql, (today,)).fetchall()
        return {row[0]: row[1] for row in rows}

    # ── sessions ───────────────────────────────────────────────────────────────

    def start_session(self) -> int:
        \"\"\"Record a new work session start. Returns session ID.\"\"\"
        sql = "INSERT INTO sessions (start_time) VALUES (?)"
        with self._connect() as conn:
            cur = conn.execute(sql, (self._now(),))
            return cur.lastrowid

    def end_session(self, session_id: int, focus_topic: str = None,
                    app_list: str = None, tasks_done: int = 0,
                    conflicts_caught: int = 0):
        \"\"\"Mark a session as ended and record summary stats.\"\"\"
        sql = \"\"\"
            UPDATE sessions SET
                end_time         = ?,
                focus_topic      = ?,
                app_list         = ?,
                tasks_done       = ?,
                conflicts_caught = ?
            WHERE id = ?
        \"\"\"
        with self._connect() as conn:
            conn.execute(sql, (
                self._now(), focus_topic, app_list,
                tasks_done, conflicts_caught, session_id
            ))

    # ── kv_store ───────────────────────────────────────────────────────────────

    def kv_set(self, key: str, value: str):
        \"\"\"Store an arbitrary key-value pair.\"\"\"
        sql = "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)"
        with self._connect() as conn:
            conn.execute(sql, (key, value))

    def kv_get(self, key: str, default: str = None) -> str:
        \"\"\"Retrieve a value from the kv store.\"\"\"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM kv_store WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else default

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def purge_old_events(self, keep_days: int = 30):
        \"\"\"Delete events older than keep_days to control database size.\"\"\"
        cutoff = (datetime.utcnow() - timedelta(days=keep_days)).isoformat()
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM context_events WHERE timestamp < ?", (cutoff,)
            )
        logger.info(f"Old events purged (keeping last {keep_days} days).")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")   # safe for multi-thread
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()
"""

files['ui/__init__.py'] = """# ui package
"""

files['ui/tray_app.py'] = """\"\"\"
ui/tray_app.py
Real system tray app with pystray on Windows.
Console simulation on non-Windows.
\"\"\"
import os, time, logging, threading
logger     = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

try:
    import tkinter as tk
    from tkinter import ttk
    TK_OK = True
except ImportError:
    TK_OK = False

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    PYSTRAY_OK = True
except ImportError:
    PYSTRAY_OK = False
    logger.warning("pystray/Pillow not installed. Run: python install_deps.py")


class TrayApp:
    def __init__(self, config, watcher, engine, detector, session, db):
        self.config      = config
        self.watcher     = watcher
        self.engine      = engine
        self.detector    = detector
        self.session     = session
        self.db          = db
        self._snoozed    = 0
        self._icon       = None
        self._pending: list = []

    def run(self):
        self.engine.add_insight_listener(self._on_insight)
        self.session.set_return_listener(self._on_return)

        # Wire meeting monitor if available
        try:
            from core.meeting_monitor import MeetingMonitor
            self._meeting_mon = MeetingMonitor(
                self.config, self.db, self.watcher)
            self._meeting_mon.add_briefing_callback(self._on_meeting_briefing)
            self._meeting_mon.start()
        except Exception as e:
            logger.debug(f"Meeting monitor not started: {e}")

        self.engine.start(self.watcher, self.detector)
        self.session.start()

        # Handle startup setting
        if self.config.get("run_on_startup", True):
            try:
                from core.startup_manager import add_to_startup, is_in_startup
                if not is_in_startup():
                    add_to_startup()
            except Exception:
                pass

        if PYSTRAY_OK and IS_WINDOWS:
            self._run_tray()
        else:
            self._run_console()

    def stop(self):
        self.engine.stop()
        self.session.stop()
        try:
            self._meeting_mon.stop()
        except Exception:
            pass
        if self._icon:
            self._icon.stop()

    # ── Real Windows tray ──────────────────────────────────────────────────────

    def _run_tray(self):
        icon_img = self._make_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard",   self._open_dashboard),
            pystray.MenuItem("Add Meeting",       self._add_meeting_dialog),
            pystray.MenuItem("Snooze 30 min",     self._snooze),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings",          self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit ContextOS",    self._quit),
        )
        self._icon = pystray.Icon(
            "ContextOS", icon_img,
            "ContextOS — watching your apps", menu)
        self._icon.run()

    def _make_icon(self) -> "Image":
        size  = 64
        img   = Image.new("RGBA", (size, size), (0,0,0,0))
        draw  = ImageDraw.Draw(img)
        # Dark circle background
        draw.ellipse([2,2,size-2,size-2], fill=(20,20,20,240))
        # Teal ring
        draw.ellipse([4,4,size-4,size-4], outline=(29,158,117,255), width=3)
        # White C
        draw.ellipse([18,18,46,46], fill=(29,158,117,255))
        draw.ellipse([22,22,42,42], fill=(20,20,20,255))
        draw.rectangle([30,22,46,42], fill=(20,20,20,255))
        return img

    # ── Console simulation ─────────────────────────────────────────────────────

    def _run_console(self):
        print("\\n" + "═"*58)
        print("  ContextOS  —  Running")
        if not (IS_WINDOWS and PYSTRAY_OK):
            print("  Install deps for real tray: python install_deps.py")
        print("═"*58)
        print("  d = dashboard   i = insights   a = add meeting")
        print("  s = snooze 30m  q = quit\\n")

        def show(ins):
            icons = {"conflict":"⚠ ","answer":"💡","auto_update":"✓ ","meeting_prep":"📅"}
            ic = icons.get(ins.insight_type, "• ")
            print(f"\\n  {ic} [{ins.insight_type.upper()}]")
            print(f"     {ins.title}")
            print(f"     {ins.detail[:80]}")
            print(f"     Apps: {ins.source_apps}\\n")

        self.engine.add_insight_listener(show)
        try:
            while True:
                cmd = input("ContextOS> ").strip().lower()
                if   cmd == "q": break
                elif cmd == "d": self._print_dashboard()
                elif cmd == "i": self._print_insights()
                elif cmd == "s": self._snooze(); print("  Snoozed 30 min.")
                elif cmd == "a": self._add_meeting_console()
                else: print("  Commands: d / i / a / s / q")
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.stop()

    # ── Insight handling ───────────────────────────────────────────────────────

    def _on_insight(self, insight):
        if time.time() < self._snoozed:
            return
        self._pending.append(insight)
        # Update tray icon tooltip
        if self._icon:
            count = len(self.db.get_active_insights())
            self._icon.title = (
                f"ContextOS — {count} insight{'s' if count!=1 else ''}")
        # Show popup on Windows
        if TK_OK and IS_WINDOWS:
            threading.Thread(
                target=self._show_insight_popup,
                args=(insight,), daemon=True).start()

    def _on_return(self, resume_data):
        away = resume_data.get("away_minutes", 0)
        if TK_OK and IS_WINDOWS:
            threading.Thread(
                target=self._show_resume_popup,
                args=(resume_data,), daemon=True).start()
        else:
            print(f"\\n  Welcome back! Away {away} min.")
            for c in resume_data.get("changes", []):
                print(f"  • {c['type'].upper()}: {c['title']}")
            print()

    def _on_meeting_briefing(self, briefing):
        title = briefing.get("meeting_title", "Meeting")
        mins  = briefing.get("minutes_until", 5)
        if TK_OK and IS_WINDOWS:
            threading.Thread(
                target=self._show_meeting_popup,
                args=(briefing,), daemon=True).start()
        else:
            print(f"\\n  📅 MEETING IN {mins} MIN: {title}")
            for ev in briefing.get("relevant_events", [])[:3]:
                print(f"     • {ev.get('app_name')}: {ev.get('window_title','')[:50]}")
            print()

    # ── Tkinter popups ────────────────────────────────────────────────────────

    def _show_insight_popup(self, insight):
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#161616")

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 360, 155
        root.geometry(f"{w}x{h}+{sw-w-16}+{sh-h-52}")

        # Colour by type
        colours = {
            "conflict":    ("#BA7517","#faeeda","#633806"),
            "answer":      ("#185FA5","#e6f1fb","#0C447C"),
            "auto_update": ("#1D9E75","#e1f5ee","#085041"),
            "meeting_prep":("#534AB7","#eeedfe","#3C3489"),
        }
        accent, bg_l, fg_d = colours.get(
            insight.insight_type, ("#555","#eee","#333"))

        # Header
        hf = tk.Frame(root, bg="#1e1e1e")
        hf.pack(fill="x")
        tk.Label(hf, text="● ContextOS", font=("Segoe UI",9,"bold"),
                 bg="#1e1e1e", fg="#1D9E75",
                 padx=10, pady=6).pack(side="left")
        badge_txt = insight.insight_type.replace("_"," ").title()
        tk.Label(hf, text=badge_txt, font=("Segoe UI",8),
                 bg=bg_l, fg=fg_d,
                 padx=6, pady=2).pack(side="right", padx=8, pady=4)

        # Colour stripe
        tk.Frame(root, bg=accent, height=2).pack(fill="x")

        # Body
        bf = tk.Frame(root, bg="#161616")
        bf.pack(fill="both", expand=True, padx=12, pady=8)
        tk.Label(bf, text=insight.title, font=("Segoe UI",10,"bold"),
                 bg="#161616", fg="#f0efe8",
                 wraplength=330, justify="left", anchor="w"
                 ).pack(fill="x", pady=(0,4))
        short = insight.detail[:85] + ("…" if len(insight.detail)>85 else "")
        tk.Label(bf, text=short, font=("Segoe UI",9),
                 bg="#161616", fg="#999890",
                 wraplength=330, justify="left", anchor="w"
                 ).pack(fill="x")

        # Buttons
        btf = tk.Frame(root, bg="#161616")
        btf.pack(fill="x", padx=12, pady=(0,10))
        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI",9),
                  bg="#222", fg="#999", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [
                      self.db.dismiss_insight(insight.id) if insight.id else None,
                      root.destroy()
                  ]).pack(side="right", padx=(4,0))
        tk.Button(btf, text="Open Dashboard",
                  font=("Segoe UI",9),
                  bg=accent, fg="white", relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda: [root.destroy(), self._open_dashboard()]
                  ).pack(side="right")

        root.after(9000, root.destroy)
        root.mainloop()

    def _show_meeting_popup(self, briefing):
        root = tk.Tk()
        root.title("ContextOS — Meeting Briefing")
        root.geometry("440x320")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0e0e0e")

        tk.Label(root,
                 text=f"📅  Meeting in {briefing['minutes_until']} minutes",
                 font=("Segoe UI",12,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=14
                 ).pack()

        tk.Label(root,
                 text=briefing["meeting_title"],
                 font=("Segoe UI",14,"bold"),
                 bg="#0e0e0e", fg="#1D9E75"
                 ).pack()

        tk.Frame(root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        tk.Label(root, text="What ContextOS found — relevant to this meeting:",
                 font=("Segoe UI",9),
                 bg="#0e0e0e", fg="#555550"
                 ).pack(anchor="w", padx=20)

        for ev in briefing.get("relevant_events", [])[:4]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=2)
            txt = f"[{ev.get('app_name','')}]  {(ev.get('window_title',''))[:52]}"
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=4)

        tk.Frame(root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        btf = tk.Frame(root, bg="#0e0e0e")
        btf.pack()
        tk.Button(btf, text="Dismiss",
                  font=("Segoe UI",10),
                  bg="#1a1a1a", fg="#999", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=root.destroy
                  ).pack(side="left", padx=4)
        tk.Button(btf, text="Open Dashboard",
                  font=("Segoe UI",10),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=lambda: [root.destroy(), self._open_dashboard()]
                  ).pack(side="left", padx=4)
        root.mainloop()

    def _show_resume_popup(self, resume_data):
        root = tk.Tk()
        root.title("ContextOS — Welcome back")
        root.geometry("420x280")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0e0e0e")

        away = resume_data.get("away_minutes", 0)
        tk.Label(root,
                 text=f"Welcome back — away {away} minutes",
                 font=("Segoe UI",12,"bold"),
                 bg="#0e0e0e", fg="#f0efe8", pady=14
                 ).pack()
        tk.Label(root,
                 text="ContextOS rebuilt your context:",
                 font=("Segoe UI",9), bg="#0e0e0e", fg="#555550"
                 ).pack()

        for item in resume_data.get("restore_items", [])[:3]:
            row = tk.Frame(root, bg="#141414")
            row.pack(fill="x", padx=20, pady=3)
            txt = f"[{item['app']}]  {item['title'][:48]}"
            tk.Label(row, text=txt, font=("Segoe UI",9),
                     bg="#141414", fg="#f0efe8",
                     anchor="w").pack(side="left", padx=8, pady=5)

        changes = resume_data.get("changes", [])
        if changes:
            tk.Label(root,
                     text=f"{len(changes)} update(s) while you were away",
                     font=("Segoe UI",9), bg="#0e0e0e", fg="#1D9E75"
                     ).pack(pady=4)

        tk.Button(root, text="Got it",
                  font=("Segoe UI",11),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=24, pady=8, cursor="hand2",
                  command=root.destroy
                  ).pack(pady=10)
        root.mainloop()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _open_dashboard(self, *_):
        try:
            from ui.dashboard import Dashboard
            threading.Thread(
                target=lambda: Dashboard(
                    self.config, self.db, self.engine).show(),
                daemon=True).start()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    def _open_settings(self, *_):
        self._open_dashboard()

    def _add_meeting_dialog(self, *_):
        if TK_OK and IS_WINDOWS:
            threading.Thread(target=self._meeting_input_window,
                             daemon=True).start()

    def _meeting_input_window(self):
        root = tk.Tk()
        root.title("Add Meeting")
        root.geometry("300x160")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#111")

        tk.Label(root, text="Meeting title:",
                 font=("Segoe UI",10), bg="#111", fg="#f0efe8"
                 ).pack(pady=(14,4))
        title_var = tk.StringVar()
        tk.Entry(root, textvariable=title_var, font=("Segoe UI",10),
                 width=28, bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5)

        tk.Label(root, text="Minutes from now:",
                 font=("Segoe UI",10), bg="#111", fg="#f0efe8"
                 ).pack(pady=(8,2))
        mins_var = tk.StringVar(value="5")
        tk.Entry(root, textvariable=mins_var, font=("Segoe UI",10),
                 width=8, bg="#1e1e1e", fg="#f0efe8",
                 insertbackground="white", relief="flat"
                 ).pack(ipady=5)

        def add():
            t = title_var.get().strip()
            m = int(mins_var.get().strip() or "5")
            if t:
                try:
                    self._meeting_mon.add_manual_meeting(t, m)
                except Exception:
                    pass
            root.destroy()

        tk.Button(root, text="Add Meeting",
                  font=("Segoe UI",10),
                  bg="#1D9E75", fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  command=add).pack(pady=10)
        root.mainloop()

    def _add_meeting_console(self):
        title = input("  Meeting title: ").strip()
        mins  = input("  Minutes from now [5]: ").strip()
        mins  = int(mins) if mins.isdigit() else 5
        if title:
            try:
                self._meeting_mon.add_manual_meeting(title, mins)
                print(f"  Meeting '{title}' added — briefing in {mins} min.")
            except Exception as e:
                print(f"  Error: {e}")

    def _snooze(self, *_):
        self._snoozed = time.time() + 1800
        logger.info("Snoozed 30 min.")

    def _quit(self, *_):
        self.stop()

    # ── Console helpers ───────────────────────────────────────────────────────

    def _print_dashboard(self):
        s = self.engine.get_stats()
        print(f"\\n  ── Today's stats ──────────────────────")
        print(f"  Insights fired:   {s['insights_today']}")
        print(f"  Conflicts caught: {s['conflicts_caught']}")
        print(f"  Tasks auto-done:  {s['tasks_auto_done']}")
        print(f"  Focus time:       {s['focus_minutes']} min")
        apps = self.watcher.get_all_seen_apps()
        if apps:
            print(f"  Apps seen today:  {', '.join(apps[:6])}")
        print()

    def _print_insights(self):
        ins = self.db.get_active_insights(limit=5)
        if not ins:
            print("  No active insights.\\n")
            return
        print(f"\\n  ── {len(ins)} Active Insight(s) ──────────────")
        for i in ins:
            print(f"  [{i['insight_type'].upper()[:4]}] {i['title']}")
        print()
"""

files['ui/dashboard.py'] = """\"\"\"
ui/dashboard.py  -  Full 5-tab GUI dashboard for ContextOS.
Built with tkinter (built into Python — no install needed).

Tabs:  Home · Insights · Apps · Memory · Settings
\"\"\"
import tkinter as tk
from tkinter import ttk
import threading
import time
import logging

logger = logging.getLogger(__name__)

C = {
    "bg":           "#ffffff",
    "bg2":          "#f8f8f6",
    "bg3":          "#f0efeb",
    "border":       "#e5e3dc",
    "text":         "#1a1a1a",
    "text2":        "#555550",
    "text3":        "#999890",
    "teal":         "#1D9E75",
    "teal_light":   "#e1f5ee",
    "blue":         "#185FA5",
    "blue_light":   "#e6f1fb",
    "amber":        "#BA7517",
    "amber_light":  "#faeeda",
    "red":          "#A32D2D",
    "red_light":    "#fcebeb",
    "purple":       "#534AB7",
    "purple_light": "#eeedfe",
    "sidebar":      "#f4f3ef",
    "sidebar_sel":  "#ffffff",
}

FF = "Segoe UI"

def F(size=11, weight="normal"):
    return (FF, size, weight)


class Dashboard:

    def __init__(self, config, db, engine=None):
        self.config      = config
        self.db          = db
        self.engine      = engine
        self.root        = None
        self._active_tab = "home"
        self._save_lbl   = None
        self._search_var = None

    def show(self):
        self.root = tk.Tk()
        self.root.title("ContextOS — Dashboard")
        self.root.geometry("820x580")
        self.root.minsize(700, 480)
        self.root.configure(bg=C["bg"])
        self._build_titlebar()
        self._build_body()
        self._switch_tab("home")
        self._start_auto_refresh()
        self.root.mainloop()

    # ── Title bar ──────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=C["bg2"], height=42)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C["bg2"])
        left.pack(side="left", padx=14, pady=8)

        dot = tk.Canvas(left, width=10, height=10,
                        bg=C["bg2"], highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=C["teal"], outline="")
        dot.pack(side="left", padx=(0, 6))

        tk.Label(left, text="ContextOS", font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(side="left")

        right = tk.Frame(bar, bg=C["bg2"])
        right.pack(side="right", padx=14)

        self._status_lbl = tk.Label(
            right, text="● Watching",
            font=F(9), bg=C["teal_light"], fg=C["teal"],
            padx=8, pady=2)
        self._status_lbl.pack()

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

    # ── Body ───────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        tk.Frame(body, bg=C["border"], width=1).pack(side="left", fill="y")
        self._content = tk.Frame(body, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=C["sidebar"], width=52)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tabs = [
            ("home",     "\\u2302", "Home"),
            ("insights", "\\u26a1", "Insights"),
            ("apps",     "\\u25c8", "Apps"),
            ("memory",   "\\u25ce", "Memory"),
            ("settings", "\\u2699", "Settings"),
        ]

        self._sb_btns = {}
        spacer_added  = False

        for i, (key, icon, label) in enumerate(tabs):
            if i == 4 and not spacer_added:
                tk.Frame(sb, bg=C["sidebar"]).pack(expand=True)
                spacer_added = True

            btn = tk.Button(
                sb, text=icon, font=("Segoe UI Emoji", 16),
                bg=C["sidebar"], fg=C["text2"],
                relief="flat", bd=0, cursor="hand2",
                width=3, height=2,
                activebackground=C["sidebar_sel"],
                activeforeground=C["teal"],
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>",
                lambda e, b=btn: b.configure(
                    bg=C["sidebar_sel"], fg=C["teal"]))
            btn.bind("<Leave>",
                lambda e, b=btn, k=key: b.configure(
                    bg=C["sidebar_sel"] if k == self._active_tab else C["sidebar"],
                    fg=C["teal"] if k == self._active_tab else C["text2"]))
            self._sb_btns[key] = btn

    def _switch_tab(self, key):
        self._active_tab = key
        for k, btn in self._sb_btns.items():
            if k == key:
                btn.configure(bg=C["sidebar_sel"], fg=C["teal"])
            else:
                btn.configure(bg=C["sidebar"], fg=C["text2"])
        for w in self._content.winfo_children():
            w.destroy()
        {
            "home":     self._tab_home,
            "insights": self._tab_insights,
            "apps":     self._tab_apps,
            "memory":   self._tab_memory,
            "settings": self._tab_settings,
        }[key](self._content)

    # ── Scrollable canvas helper ───────────────────────────────────────────────

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=C["bg"])
        frame.bind("<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return frame

    # =========================================================================
    # TAB 1 — HOME
    # =========================================================================

    def _tab_home(self, parent):
        frame = self._scrollable(parent)
        pad   = {"padx": 20, "pady": 0}

        self._section_label(frame, "Today's overview", pady_top=18)

        # Stat cards
        stats      = self._get_stats()
        stats_wrap = tk.Frame(frame, bg=C["bg"])
        stats_wrap.pack(fill="x", padx=20, pady=(0, 16))

        defs = [
            ("Insights fired",   str(stats["insights_today"]),   "today",              C["purple"]),
            ("Conflicts caught", str(stats["conflicts_caught"]),  "saved from mistakes",C["amber"]),
            ("Tasks auto-done",  str(stats["tasks_auto_done"]),   "in Notion / Jira",  C["teal"]),
            ("Focus time",       str(stats["focus_minutes"]) + "m","deep work today",  C["blue"]),
        ]

        for i, (label, value, sub, color) in enumerate(defs):
            card = tk.Frame(stats_wrap, bg=C["bg2"])
            card.grid(row=0, column=i,
                      padx=(0, 10) if i < 3 else 0,
                      sticky="ew", ipady=10, ipadx=10)
            stats_wrap.columnconfigure(i, weight=1)

            tk.Label(card, text=label, font=F(9),
                     bg=C["bg2"], fg=C["text2"]).pack(anchor="w", padx=10, pady=(10, 0))
            tk.Label(card, text=value, font=F(22, "bold"),
                     bg=C["bg2"], fg=color).pack(anchor="w", padx=10)
            tk.Label(card, text=sub, font=F(8),
                     bg=C["bg2"], fg=C["text3"]).pack(anchor="w", padx=10, pady=(0, 8))

        # Current focus
        self._section_label(frame, "Current focus")

        focus_wrap = tk.Frame(frame, bg=C["bg2"])
        focus_wrap.pack(fill="x", padx=20, pady=(0, 16))

        topic = self._get_focus_topic()
        tk.Label(focus_wrap, text=topic, font=F(12, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(anchor="w", padx=14, pady=(12, 4))

        chips_row = tk.Frame(focus_wrap, bg=C["bg2"])
        chips_row.pack(anchor="w", padx=14, pady=(0, 12))

        for app in self._get_recent_apps()[:6]:
            tk.Label(chips_row, text=app, font=F(9),
                     bg=C["bg"], fg=C["text2"],
                     relief="flat", padx=8, pady=2
                     ).pack(side="left", padx=(0, 5))

        # Context trail
        self._section_label(frame, "Context trail")

        trail_wrap = tk.Frame(frame, bg=C["bg"])
        trail_wrap.pack(fill="x", padx=20, pady=(0, 20))

        events = self.db.get_recent_events(limit=10, hours=8)
        if not events:
            tk.Label(trail_wrap,
                     text="No activity yet — start using your apps!",
                     font=F(10), bg=C["bg"], fg=C["text3"]
                     ).pack(anchor="w", pady=8)
        else:
            for ev in events:
                self._trail_row(trail_wrap, ev)

    def _trail_row(self, parent, event):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=2)

        dot = tk.Canvas(row, width=8, height=8,
                        bg=C["bg"], highlightthickness=0)
        dot.create_oval(1, 1, 7, 7, fill=C["border"], outline=C["text3"])
        dot.pack(side="left", pady=6, padx=(4, 8))

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True)

        ts = (event.get("timestamp") or "")[:19].replace("T", " ")
        tk.Label(info, text=ts[11:], font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        title = (event.get("window_title") or "")[:68]
        app   = event.get("app_name", "")
        tk.Label(info, text=f"[{app}]  {title}", font=F(10),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")

    # =========================================================================
    # TAB 2 — INSIGHTS
    # =========================================================================

    def _tab_insights(self, parent):
        hdr = tk.Frame(parent, bg=C["bg"])
        hdr.pack(fill="x", padx=20, pady=(18, 0))
        self._section_label(hdr, "All active insights", inline=True)
        tk.Button(hdr, text="Refresh", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, cursor="hand2",
                  command=lambda: self._switch_tab("insights")
                  ).pack(side="right")

        frame    = self._scrollable(parent)
        insights = self.db.get_active_insights(limit=20)

        if not insights:
            msg = "No active insights right now.\\n\\nContextOS is watching your apps."
            tk.Label(frame, text=msg,
                     font=F(11), bg=C["bg"], fg=C["text3"],
                     justify="center").pack(pady=60)
            return

        for ins in insights:
            self._insight_card(frame, ins)

    def _insight_card(self, parent, ins):
        type_map = {
            "conflict":    (C["amber"],  C["amber_light"],  "Conflict"),
            "answer":      (C["blue"],   C["blue_light"],   "Answer found"),
            "auto_update": (C["teal"],   C["teal_light"],   "Auto-updated"),
            "meeting_prep":(C["purple"], C["purple_light"], "Meeting prep"),
        }
        itype              = ins.get("insight_type", "conflict")
        color, bg_l, badge = type_map.get(itype, (C["text2"], C["bg2"], itype))

        card = tk.Frame(parent, bg=C["bg"],
                        highlightbackground=C["border"],
                        highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 10))

        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")

        body = tk.Frame(card, bg=C["bg"])
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        top = tk.Frame(body, bg=C["bg"])
        top.pack(fill="x")

        tk.Label(top, text=badge, font=F(9),
                 bg=bg_l, fg=color, padx=6, pady=1).pack(side="left")

        ts = (ins.get("timestamp") or "")[:19].replace("T", " ")[11:]
        tk.Label(top, text=ts, font=F(8),
                 bg=C["bg"], fg=C["text3"]).pack(side="right")

        tk.Label(body, text=ins.get("title", ""), font=F(11, "bold"),
                 bg=C["bg"], fg=C["text"],
                 wraplength=560, justify="left", anchor="w"
                 ).pack(fill="x", pady=(6, 2))

        detail = ins.get("detail", "")
        if detail:
            tk.Label(body, text=detail, font=F(10),
                     bg=C["bg"], fg=C["text2"],
                     wraplength=560, justify="left", anchor="w"
                     ).pack(fill="x")

        sources = ins.get("source_apps", "")
        if sources:
            tk.Label(body, text="Sources: " + sources, font=F(8),
                     bg=C["bg"], fg=C["text3"]).pack(anchor="w", pady=(4, 0))

        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(anchor="w", pady=(8, 0))

        iid = ins.get("id")
        tk.Button(btn_row, text="Dismiss", font=F(9),
                  bg=C["bg2"], fg=C["text2"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._dismiss(i)
                  ).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Mark acted on", font=F(9),
                  bg=C["teal_light"], fg=C["teal"], relief="flat",
                  padx=10, pady=3, cursor="hand2",
                  command=lambda i=iid: self._act_on(i)
                  ).pack(side="left")

    def _dismiss(self, iid):
        if iid:
            self.db.dismiss_insight(iid)
        self._switch_tab("insights")

    def _act_on(self, iid):
        if iid:
            with self.db._connect() as conn:
                conn.execute(
                    "UPDATE insights SET acted_on=1, dismissed=1 WHERE id=?",
                    (iid,))
        self._switch_tab("insights")

    # =========================================================================
    # TAB 3 — APPS
    # =========================================================================

    def _tab_apps(self, parent):
        self._section_label(parent, "Watched apps", pady_top=18, padx=20)
        frame = self._scrollable(parent)
        grid  = tk.Frame(frame, bg=C["bg"])
        grid.pack(fill="x", padx=20, pady=(0, 10))

        events     = self.db.get_recent_events(limit=200, hours=24)
        app_counts: dict = {}
        app_last:   dict = {}

        for ev in events:
            app = ev["app_name"]
            app_counts[app] = app_counts.get(app, 0) + 1
            if app not in app_last:
                app_last[app] = ev["timestamp"]

        watched  = self.config.get("watched_apps", [])
        all_apps = list(app_counts.keys())
        for w in watched:
            if not any(w.lower() in a.lower() for a in all_apps):
                all_apps.append(w)

        for i, app in enumerate(all_apps[:12]):
            col    = i % 3
            row    = i // 3
            count  = app_counts.get(app, 0)
            last_t = app_last.get(app, "")
            last_s = last_t[:19].replace("T", " ")[11:] if last_t else "No activity"
            active = count > 0

            card = tk.Frame(grid, bg=C["bg2"])
            card.grid(row=row, column=col,
                      padx=(0, 10) if col < 2 else 0,
                      pady=(0, 10), sticky="ew",
                      ipadx=10, ipady=8)
            grid.columnconfigure(col, weight=1)

            top = tk.Frame(card, bg=C["bg2"])
            top.pack(fill="x", padx=10, pady=(10, 0))

            dot = tk.Canvas(top, width=8, height=8,
                            bg=C["bg2"], highlightthickness=0)
            dot.create_oval(1, 1, 7, 7,
                fill=C["teal"] if active else C["border"], outline="")
            dot.pack(side="left", pady=3, padx=(0, 6))

            tk.Label(top, text=app, font=F(11, "bold"),
                     bg=C["bg2"], fg=C["text"]).pack(side="left")

            tk.Label(card, text=str(count) + " events today",
                     font=F(9), bg=C["bg2"], fg=C["text2"]
                     ).pack(anchor="w", padx=10)
            tk.Label(card, text="Last: " + last_s,
                     font=F(8), bg=C["bg2"], fg=C["text3"]
                     ).pack(anchor="w", padx=10, pady=(0, 8))

    # =========================================================================
    # TAB 4 — MEMORY
    # =========================================================================

    def _tab_memory(self, parent):
        search_wrap = tk.Frame(parent, bg=C["bg"])
        search_wrap.pack(fill="x", padx=20, pady=(18, 10))
        self._section_label(search_wrap, "Context memory", inline=True)

        search_box = tk.Frame(search_wrap, bg=C["bg"])
        search_box.pack(side="right")

        self._search_var = tk.StringVar()
        entry = tk.Entry(search_box, textvariable=self._search_var,
                         font=F(10), width=22,
                         bg=C["bg2"], fg=C["text"],
                         relief="flat", bd=1,
                         highlightbackground=C["border"],
                         highlightthickness=1)
        entry.pack(side="left", ipady=5, padx=(0, 6))
        placeholder = "Search your work context..."
        entry.insert(0, placeholder)
        entry.bind("<FocusIn>",
            lambda e: entry.delete(0, "end")
            if entry.get() == placeholder else None)

        frame = self._scrollable(parent)

        tk.Button(search_box, text="Search", font=F(9),
                  bg=C["teal"], fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2",
                  command=lambda: self._do_search(frame, self._search_var.get())
                  ).pack(side="left")

        entry.bind("<Return>",
            lambda e: self._do_search(frame, self._search_var.get()))

        self._do_search(frame, "")

    def _do_search(self, frame, query):
        for w in frame.winfo_children():
            w.destroy()

        events = self.db.get_recent_events(limit=100, hours=24 * 7)
        q      = query.strip().lower()
        skip   = ("", "search your work context...")
        if q and q not in skip:
            events = [
                e for e in events
                if q in (e.get("window_title") or "").lower()
                or q in (e.get("app_name") or "").lower()
                or q in (e.get("keywords") or "").lower()
            ]

        if not events:
            tk.Label(frame, text="No results found.",
                     font=F(10), bg=C["bg"], fg=C["text3"]
                     ).pack(pady=40)
            return

        by_app: dict = {}
        for ev in events:
            by_app.setdefault(ev["app_name"], []).append(ev)

        for app, evs in list(by_app.items())[:8]:
            group = tk.Frame(frame, bg=C["bg"])
            group.pack(fill="x", padx=20, pady=(0, 12))

            tk.Label(group, text=app, font=F(10, "bold"),
                     bg=C["bg"], fg=C["text"]).pack(anchor="w")

            for ev in evs[:4]:
                row = tk.Frame(group, bg=C["bg2"])
                row.pack(fill="x", pady=1)
                title = (ev.get("window_title") or "")[:70]
                ts    = (ev.get("timestamp") or "")[:19].replace("T", " ")[11:]
                tk.Label(row, text=title, font=F(10),
                         bg=C["bg2"], fg=C["text"], anchor="w"
                         ).pack(side="left", padx=10, pady=5)
                tk.Label(row, text=ts, font=F(8),
                         bg=C["bg2"], fg=C["text3"]
                         ).pack(side="right", padx=10)

    # =========================================================================
    # TAB 5 — SETTINGS
    # =========================================================================

    def _tab_settings(self, parent):
        frame = self._scrollable(parent)
        pad   = {"padx": 24, "pady": 0}

        self._section_label(frame, "General", pady_top=18)
        self._toggle(frame, "Run on Windows startup",
                     "Launch ContextOS when PC boots",
                     "run_on_startup", pad)
        self._toggle(frame, "Show notifications",
                     "Popup insights when detected",
                     "show_notifications", pad)
        self._toggle(frame, "Smart pause (high CPU)",
                     "Pause analysis when CPU exceeds 80%",
                     "smart_pause", pad)

        self._divider(frame)
        self._section_label(frame, "Features")
        self._toggle(frame, "Auto-update tasks",
                     "Mark Notion / Jira tasks in-progress automatically",
                     "auto_update_tasks", pad)
        self._toggle(frame, "Meeting briefings",
                     "Show context summary 5 min before meetings",
                     "meeting_briefing", pad)
        self._toggle(frame, "Cloud AI mode",
                     "Use cloud for heavier analysis (needs internet)",
                     "cloud_ai", pad)

        self._divider(frame)
        self._section_label(frame, "Mode")
        self._dropdown(frame, "Analysis mode",
                       "lite = rules only    full = local AI    auto = detect",
                       "mode", ["auto", "lite", "full", "cloud"], pad)

        self._divider(frame)
        self._section_label(frame, "Privacy")
        self._toggle(frame, "Local only",
                     "Never send any data to the internet",
                     "local_only", pad)

        self._save_lbl = tk.Label(frame, text="", font=F(9),
                                  bg=C["bg"], fg=C["teal"])
        self._save_lbl.pack(anchor="w", padx=24, pady=(16, 20))

    def _toggle(self, parent, label, sub, key, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=1, **pad)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(info, text=label, font=F(11),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        val = tk.BooleanVar(value=bool(self.config.get(key, False)))

        def on_toggle(k=key, v=val):
            self.config.set(k, v.get())
            self._flash_saved()

        tk.Checkbutton(row, variable=val, command=on_toggle,
                       bg=C["bg"], activebackground=C["bg"],
                       cursor="hand2").pack(side="right")

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)

    def _dropdown(self, parent, label, sub, key, options, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=1, **pad)

        info = tk.Frame(row, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(info, text=label, font=F(11),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(info, text=sub, font=F(9),
                 bg=C["bg"], fg=C["text3"]).pack(anchor="w")

        val = tk.StringVar(value=str(self.config.get(key, options[0])))

        def on_change(*_):
            self.config.set(key, val.get())
            self._flash_saved()

        dd = ttk.Combobox(row, textvariable=val, values=options,
                          state="readonly", width=10, font=F(10))
        dd.pack(side="right", pady=10)
        dd.bind("<<ComboboxSelected>>", on_change)
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)

    def _flash_saved(self):
        try:
            self._save_lbl.configure(text="\\u2713 Settings saved")
            self.root.after(
                2000, lambda: self._save_lbl.configure(text=""))
        except Exception:
            pass

    # =========================================================================
    # Shared helpers
    # =========================================================================

    def _section_label(self, parent, text, pady_top=8, padx=20, inline=False):
        lbl = tk.Label(parent, text=text.upper(), font=F(9, "bold"),
                       bg=C["bg"], fg=C["text3"])
        if inline:
            lbl.pack(side="left", pady=pady_top)
        else:
            lbl.pack(anchor="w", padx=padx, pady=(pady_top, 6))

    def _divider(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=24, pady=12)

    def _get_stats(self):
        if self.engine:
            return self.engine.get_stats()
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    0,
        }

    def _get_focus_topic(self):
        kws  = self.db.get_keywords_last_n_events(n=30)
        freq: dict = {}
        for k in kws:
            if len(k) >= 4:
                freq[k] = freq.get(k, 0) + 1
        if not freq:
            return "No focus detected yet — start using your apps!"
        best = max(freq, key=lambda k: freq[k])
        return best.title() + " — detected focus"

    def _get_recent_apps(self):
        events = self.db.get_recent_events(limit=50, hours=2)
        seen: list = []
        for e in events:
            if e["app_name"] not in seen:
                seen.append(e["app_name"])
        return seen

    def _start_auto_refresh(self):
        def loop():
            while True:
                time.sleep(30)
                try:
                    if (self.root and
                            self.root.winfo_exists() and
                            self._active_tab == "home"):
                        self.root.after(
                            0, lambda: self._switch_tab("home"))
                except Exception:
                    break
        threading.Thread(target=loop, daemon=True).start()
"""

files['utils/__init__.py'] = """# utils package
"""

files['utils/logger.py'] = """\"\"\"
utils/logger.py
Sets up logging for the whole application.
Logs go to both the console and a rotating log file.
\"\"\"

import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, "data", "user_data")
LOG_PATH = os.path.join(LOG_DIR, "contextos.log")

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)


def setup_logger(level=logging.INFO) -> logging.Logger:
    \"\"\"
    Configure root logger with console + rotating file handler.
    Call once at startup. Returns the root logger.
    \"\"\"
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler — clean output
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(_FORMATTER)

    # File handler — keeps last 2 MB, 3 backup files
    fh = RotatingFileHandler(
        LOG_PATH,
        maxBytes  = 2 * 1024 * 1024,   # 2 MB
        backupCount = 3,
        encoding  = "utf-8",
    )
    fh.setLevel(logging.DEBUG)   # always log everything to file
    fh.setFormatter(_FORMATTER)

    # Avoid duplicate handlers if called twice
    if not root.handlers:
        root.addHandler(ch)
        root.addHandler(fh)

    return root
"""

files['utils/system_check.py'] = """\"\"\"
utils/system_check.py
Reads the hardware specs of the current machine and recommends
whether to run ContextOS in lite, full, or cloud mode.
Works on Windows, Linux, and Mac.
\"\"\"

import os
import platform
import logging

logger = logging.getLogger(__name__)


class SystemCheck:

    def get_specs(self) -> dict:
        \"\"\"Return a dict of key hardware specs.\"\"\"
        return {
            "ram_gb":    self._get_ram_gb(),
            "cpu_cores": self._get_cpu_cores(),
            "os_version": platform.platform(),
            "is_windows": os.name == "nt",
        }

    def recommend_mode(self) -> str:
        \"\"\"
        Choose the right mode based on available RAM:
          < 3 GB  → lite   (keyword rules only, no AI)
          3–6 GB  → full   (local small AI model)
          > 6 GB  → full   (full local AI + faster analysis)
        \"\"\"
        ram = self._get_ram_gb()
        if ram < 3.0:
            logger.info(f"RAM={ram:.1f}GB → recommending lite mode")
            return "lite"
        elif ram < 6.0:
            logger.info(f"RAM={ram:.1f}GB → recommending full mode")
            return "full"
        else:
            logger.info(f"RAM={ram:.1f}GB → recommending full mode (high RAM)")
            return "full"

    def _get_ram_gb(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            pass

        # Fallback: read /proc/meminfo on Linux
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        except Exception:
            pass

        return 4.0   # safe default if we can not detect

    def _get_cpu_cores(self) -> int:
        try:
            return os.cpu_count() or 2
        except Exception:
            return 2
"""

files['tests/__init__.py'] = """# tests package
"""

files['tests/test_core.py'] = """\"\"\"
tests/test_core.py
Automated tests for the core ContextOS modules.
Run with:   pytest tests/
All tests work without Windows — no GUI, no win32 needed.
\"\"\"

import sys
import os
import pytest
import tempfile

# Make sure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════════
#  Database tests
# ══════════════════════════════════════════════════════════════════

class TestDatabase:
    \"\"\"Test the Database class with a temporary in-memory database.\"\"\"

    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        \"\"\"Create a fresh Database using a temp directory.\"\"\"
        import data.database as db_module
        monkeypatch.setattr(db_module, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
        from data.database import Database
        database = Database()
        database.initialize()
        return database

    def test_initialize_creates_tables(self, db):
        \"\"\"Database should create all 4 tables on init.\"\"\"
        with db._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        table_names = {t[0] for t in tables}
        assert "context_events" in table_names
        assert "insights"       in table_names
        assert "sessions"       in table_names
        assert "kv_store"       in table_names

    def test_add_and_get_event(self, db):
        \"\"\"Should save an event and retrieve it.\"\"\"
        db.add_event(
            app_name     = "VS Code",
            window_title = "AuthService.ts — VS Code",
            event_type   = "app_switch",
            keywords     = "auth,service,token",
        )
        events = db.get_recent_events(limit=5)
        assert len(events) == 1
        assert events[0]["app_name"] == "VS Code"
        assert "auth" in events[0]["keywords"]

    def test_add_and_get_insight(self, db):
        \"\"\"Should save an insight and retrieve it as active.\"\"\"
        insight_id = db.add_insight(
            insight_type = "conflict",
            title        = "Auth conflict detected",
            detail       = "Email vs code conflict",
            source_apps  = "VS Code,Gmail",
        )
        assert isinstance(insight_id, int)
        active = db.get_active_insights()
        assert len(active) == 1
        assert active[0]["title"] == "Auth conflict detected"

    def test_dismiss_insight(self, db):
        \"\"\"Dismissed insights should not appear in active list.\"\"\"
        iid = db.add_insight("conflict", "Test insight", "detail", "VS Code")
        db.dismiss_insight(iid)
        active = db.get_active_insights()
        assert len(active) == 0

    def test_kv_store(self, db):
        \"\"\"kv_store should save and retrieve arbitrary strings.\"\"\"
        db.kv_set("test_key", "hello world")
        val = db.kv_get("test_key")
        assert val == "hello world"

    def test_kv_get_missing_returns_default(self, db):
        val = db.kv_get("does_not_exist", default="fallback")
        assert val == "fallback"

    def test_get_keywords_last_n(self, db):
        \"\"\"Should collect all keywords from recent events.\"\"\"
        db.add_event("VS Code", "AuthService.ts", "app_switch",
                     keywords="auth,service")
        db.add_event("Slack",   "Ahmed: fixed checkout", "app_switch",
                     keywords="checkout,fixed")
        kws = db.get_keywords_last_n_events(n=10)
        assert "auth" in kws
        assert "checkout" in kws

    def test_session_start_and_end(self, db):
        \"\"\"Should record a session start and end.\"\"\"
        sid = db.start_session()
        assert isinstance(sid, int)
        db.end_session(sid, focus_topic="AuthService", app_list="VS Code,Slack")
        # If no exception, the session was recorded correctly


# ══════════════════════════════════════════════════════════════════
#  Config manager tests
# ══════════════════════════════════════════════════════════════════

class TestConfigManager:

    @pytest.fixture
    def config(self, tmp_path, monkeypatch):
        import data.config_manager as cm_module
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", str(tmp_path / "settings.json"))
        from data.config_manager import ConfigManager
        return ConfigManager()

    def test_defaults_loaded(self, config):
        assert config.get("mode") in ("auto", "lite", "full")
        assert isinstance(config.get("idle_delay_seconds"), int)

    def test_set_and_get(self, config):
        config.set("mode", "lite")
        assert config.get("mode") == "lite"

    def test_reset_to_defaults(self, config):
        config.set("mode", "cloud")
        config.reset_to_defaults()
        assert config.get("mode") == "auto"

    def test_missing_key_returns_fallback(self, config):
        val = config.get("nonexistent_key_xyz", fallback="DEFAULT")
        assert val == "DEFAULT"

    def test_settings_persist_across_reload(self, tmp_path, monkeypatch):
        \"\"\"Settings written in one instance should be readable by a new instance.\"\"\"
        import data.config_manager as cm_module
        path = str(tmp_path / "settings.json")
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", path)
        from data.config_manager import ConfigManager
        c1 = ConfigManager()
        c1.set("theme", "dark")
        c2 = ConfigManager()
        assert c2.get("theme") == "dark"


# ══════════════════════════════════════════════════════════════════
#  AppWatcher keyword extraction tests
# ══════════════════════════════════════════════════════════════════

class TestAppWatcherHelpers:
    \"\"\"Test parsing via AppReader — no Windows API needed.\"\"\"

    @pytest.fixture
    def reader(self):
        from core.app_reader import AppReader
        return AppReader()

    def test_extract_keywords_basic(self, reader):
        kws = reader._extract_keywords("AuthService.ts — contextOS — VS Code")
        assert any("auth" in k for k in kws)

    def test_extract_keywords_filters_stopwords(self, reader):
        kws = reader._extract_keywords("the and or in on at")
        assert len(kws) == 0

    def test_extract_keywords_deduplicates(self, reader):
        kws = reader._extract_keywords("auth auth auth service")
        assert kws.count("auth") <= 1

    def test_extract_filename_typescript(self, reader):
        assert reader._extract_file("AuthService.ts — VS Code") == "AuthService.ts"

    def test_extract_filename_python(self, reader):
        assert reader._extract_file("main.py — contextOS — VS Code") == "main.py"

    def test_extract_filename_none_when_missing(self, reader):
        assert reader._extract_file("Stack Overflow — no file here") is None

    def test_friendly_app_name(self, reader):
        assert reader._friendly_name("Code.exe","")   == "VS Code"
        assert reader._friendly_name("chrome.exe","") == "Chrome"
        assert reader._friendly_name("slack.exe","")  == "Slack"

    def test_parse_vscode_title(self, reader):
        ctx = reader.parse("code.exe", "AuthService.ts — contextOS — Visual Studio Code")
        assert ctx.app_name  == "VS Code"
        assert ctx.file_name == "AuthService.ts"
        assert ctx.project   == "contextOS"

    def test_parse_gmail_in_browser(self, reader):
        ctx = reader.parse("chrome.exe", "Re: auth flow must not change — Sara Khan — Gmail")
        assert ctx.app_name   == "Chrome"
        assert ctx.email_subj is not None
        assert "auth" in ctx.email_subj.lower()

    def test_parse_slack_desktop(self, reader):
        ctx = reader.parse("slack.exe", "#dev-mobile — MyWorkspace — Slack")
        assert ctx.app_name == "Slack"
        assert ctx.channel  == "dev-mobile"

    def test_parse_figma(self, reader):
        ctx = reader.parse("figma.exe", "Login_v4 — Figma")
        assert ctx.app_name   == "Figma"
        assert ctx.page_title == "Login_v4"

    def test_parse_unknown_app(self, reader):
        ctx = reader.parse("myapp.exe", "Customer Invoice 2024 — MyApp")
        assert ctx.app_name is not None


# ══════════════════════════════════════════════════════════════════
#  ConflictDetector tests
# ══════════════════════════════════════════════════════════════════

class TestConflictDetector:

    @pytest.fixture
    def setup(self, tmp_path, monkeypatch):
        import data.config_manager as cm_module
        import data.database as db_module
        monkeypatch.setattr(cm_module, "CONFIG_DIR",  str(tmp_path))
        monkeypatch.setattr(cm_module, "CONFIG_PATH", str(tmp_path / "settings.json"))
        monkeypatch.setattr(db_module, "DB_DIR",  str(tmp_path))
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
        from data.config_manager import ConfigManager
        from data.database import Database
        from core.conflict_detector import ConflictDetector
        db  = Database()
        db.initialize()
        cfg = ConfigManager()
        det = ConflictDetector(cfg, db)
        return db, cfg, det

    def test_no_insights_with_empty_db(self, setup):
        _, _, det = setup
        insights = det.analyse()
        assert insights == []

    def test_detects_conflict_between_code_and_email(self, setup):
        db, _, det = setup
        # Simulate: user read email about 'authentication'
        db.add_event("Gmail", "Sara: authentication flow must not change",
                     "app_switch", keywords="authentication,flow,change")
        # Simulate: user then opened auth file in VS Code
        db.add_event("VS Code", "authentication_service.py — VS Code",
                     "app_switch", keywords="authentication,service,python")
        insights = det.analyse()
        # Should detect the shared keyword 'authentication'
        assert len(insights) >= 1
        assert any("authentication" in i.title.lower() or
                   "conflict" in i.insight_type for i in insights)

    def test_cooldown_prevents_duplicate_insights(self, setup):
        db, _, det = setup
        db.add_event("Gmail",   "Subject: checkout problem", "app_switch",
                     keywords="checkout,problem")
        db.add_event("VS Code", "checkout.py — VS Code",    "app_switch",
                     keywords="checkout,python")
        # Fire once
        first  = det.analyse()
        # Fire again immediately — should be suppressed by cooldown
        second = det.analyse()
        assert len(second) == 0   # cooldown should block it

    def test_insight_saved_to_database(self, setup):
        db, _, det = setup
        db.add_event("Slack",   "Ahmed: fixed the checkout bug", "app_switch",
                     keywords="checkout,fixed,bug")
        db.add_event("VS Code", "checkout_handler.py — VS Code", "app_switch",
                     keywords="checkout,handler,python")
        det.analyse()
        saved = db.get_active_insights()
        assert len(saved) >= 1


# ══════════════════════════════════════════════════════════════════
#  SystemCheck tests
# ══════════════════════════════════════════════════════════════════

class TestSystemCheck:

    def test_get_specs_returns_dict(self):
        from utils.system_check import SystemCheck
        specs = SystemCheck().get_specs()
        assert "ram_gb"    in specs
        assert "cpu_cores" in specs
        assert specs["ram_gb"] > 0
        assert specs["cpu_cores"] >= 1

    def test_recommend_mode_returns_valid_string(self):
        from utils.system_check import SystemCheck
        mode = SystemCheck().recommend_mode()
        assert mode in ("lite", "full", "cloud")
"""

files['ai/__init__.py'] = """# ai package
"""

created = 0
for rel, content in files.items():
    full = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(full) if os.path.dirname(full) else BASE, exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    created += 1
    print(f"  OK  {rel}")
print(f"\nDone! {created} files updated.")
print("Run:  python install_deps.py")
print("Then: python -m pytest tests/")
print("Then: python main.py")