# ContextOS

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
