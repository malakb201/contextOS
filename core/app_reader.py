"""
core/app_reader.py
Deep title parser for every major app.
Window title se maximum context extract karta hai.

Har app ka title format alag hota hai — yeh module
unhe parse karke structured data deta hai.
"""
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
    r'\b([\w\-\. ]+\.(?:' + '|'.join(CODE_EXTENSIONS) + r'))\b',
    re.IGNORECASE
)


class ParsedContext:
    """Structured context extracted from one window title."""
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
        """Return all text fields joined for keyword extraction."""
        parts = [self.raw_title]
        for f in [self.file_name, self.project, self.email_subj,
                  self.sender, self.channel, self.page_title]:
            if f:
                parts.append(f)
        return " ".join(parts)


class AppReader:
    """
    Parses window titles from any app into structured ParsedContext.
    Works on ALL installed apps — not just a fixed list.
    """

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
        parts = re.split(r'\s[—–-]\s', title.replace("●","").strip())
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
                parts = re.split(r'\s[—–-]\s|\s-\s', title)
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
            m = re.match(r'^(.+?)\s*\|\s*(.+?)\s*\|', title)
            if m:
                ctx.channel  = m.group(1).strip()
                ctx.project  = m.group(2).strip()
                ctx.event_type = "slack_read"

        # GitHub
        elif "github" in low:
            ctx.url_hint = "github"
            # "contextOS/src/main.py at main · user/repo"
            m = re.search(r'([\w\-]+/[\w\.\-]+)\s+at\s+\w+', title)
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
        parts = re.split(r'\s—\s|\s-\s', title.replace("Slack","").strip())
        if parts:
            chan = parts[0].strip().lstrip("#")
            ctx.channel = chan
            ctx.event_type = "slack_read"
        if len(parts) >= 2:
            ctx.project = parts[1].strip()

    def _parse_email_client(self, ctx, title):
        # Outlook: "RE: Auth requirements - Microsoft Outlook"
        # "Inbox - malak@email.com - Outlook"
        cleaned = re.sub(r'\s*-\s*(Microsoft\s+)?Outlook\s*$','',title,flags=re.I)
        cleaned = re.sub(r'\s*-\s*Thunderbird\s*$','',cleaned,flags=re.I)
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
        ctx.page_title = re.sub(r'\s*[\|—-]\s*Notion\s*$','',title,flags=re.I).strip()
        ctx.event_type = "task_view"

    def _parse_figma(self, ctx, title):
        # "Login_v4 – Figma" or "Mobile App — Figma"
        ctx.page_title = re.sub(r'\s*[–—-]\s*Figma\s*$','',title,flags=re.I).strip()
        ctx.event_type = "design_view"

    def _parse_teams(self, ctx, title):
        # "General | My Team | Microsoft Teams"
        parts = re.split(r'\s*\|\s*', title)
        if parts:
            ctx.channel = parts[0].strip()
            if len(parts) >= 2:
                ctx.project = parts[1].strip()
        ctx.event_type = "slack_read"

    def _parse_discord(self, ctx, title):
        # "#general — Server — Discord"
        parts = re.split(r'\s—\s', title.replace("Discord","").strip())
        if parts:
            ctx.channel = parts[0].strip().lstrip("#")
        ctx.event_type = "slack_read"

    def _parse_messaging(self, ctx, title):
        # "Ahmed — WhatsApp" or "Family Group — Telegram"
        ctx.sender = re.sub(r'\s*—\s*(WhatsApp|Telegram)\s*$','',title,flags=re.I).strip()
        ctx.event_type = "slack_read"

    def _parse_zoom(self, ctx, title):
        # "Zoom Meeting" or "Sprint Review — Zoom"
        ctx.page_title = re.sub(r'\s*—?\s*Zoom\s*$','',title,flags=re.I).strip()
        ctx.event_type = "meeting"

    def _parse_explorer(self, ctx, title):
        # "contextOS — C:\Users\..." or just a folder name
        if "\\" in title or "/" in title:
            ctx.project = title.split("\\")[-1].split("/")[-1].strip()
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
        m = re.match(r'^([^\[—-]+)', title)
        if m:
            ctx.file_name = m.group(1).strip()
        m2 = re.search(r'\[([^\]]+)\]', title)
        if m2:
            path = m2.group(1)
            ctx.project = path.split("/")[-1].split("\\")[-1]
        ctx.event_type = "file_open"

    def _parse_generic(self, ctx, title):
        # For any unknown app — best-effort extraction
        file = self._extract_file(title)
        if file:
            ctx.file_name  = file
            ctx.event_type = "file_open"
        else:
            # Take the first meaningful part before any separator
            parts = re.split(r'\s[—–\-|]\s', title)
            if parts:
                ctx.page_title = parts[0].strip()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _friendly_name(self, exe: str, title: str) -> str:
        key = exe.lower().strip()
        if key in EXE_MAP:
            return EXE_MAP[key]
        # Fallback: clean up the exe name
        name = re.sub(r'\d+$', '', key.replace(".exe","")).strip()
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
