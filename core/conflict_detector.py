"""
core/conflict_detector.py
Smart conflict detector — noise filtered, meaningful insights only.
"""
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


# ── Words too generic to be useful insights ───────────────────────────────────
NOISE_WORDS = {
    # OS / system words
    "windows","system32","program","programs","appdata","local",
    "users","desktop","onedrive","documents","downloads","roaming",
    "microsoft","python","pythonw","scripts","install","installer",
    "cmd","powershell","terminal","windowsterminal","windowstermina",
    "explorer","taskbar","taskmanager","control","panel",
    # Common path fragments
    "clone","repos","projects","github","gitbash","git",
    "lib","site","packages","bin","src","dist","build","venv",
    # App names themselves
    "chrome","firefox","edge","brave","slack","notion","figma",
    "outlook","gmail","teams","discord","zoom","whatsapp","telegram",
    "vscode","code","notepad","word","excel","postman",
    # Too short or too generic
    "new","file","open","save","close","window","page","tab",
    "main","test","debug","run","start","stop","true","false",
    "null","none","error","warning","info","log","data","base",
    "http","https","www","com","net","org","html","css","js",
    # Project-specific (contextOS itself)
    "contextos","contextOS","dashboard","settings","config","utils",
    "core","session","manager","watcher","detector","engine",
    "insight","insights","database","sqlite","context","trail",
}

# Minimum keyword length for a meaningful insight
MIN_KW_LEN = 5

# ── Conflict rules ────────────────────────────────────────────────────────────
RULES = [
    {
        "name":   "code_vs_email",
        "apps_a": {"VS Code","PyCharm","IntelliJ","WebStorm","Visual Studio"},
        "apps_b": {"Gmail","Outlook","Thunderbird"},
        "type":   "conflict",
        "title":  'Email and code both mention "{kw}" — possible conflict',
        "detail": 'You have an email mentioning "{kw}" and are editing a related file. Check the email for instructions before making changes.',
    },
    {
        "name":   "code_vs_slack",
        "apps_a": {"VS Code","PyCharm","IntelliJ","WebStorm","Visual Studio"},
        "apps_b": {"Slack","Teams","Discord"},
        "type":   "answer",
        "title":  'Slack may have the answer for "{kw}"',
        "detail": 'A recent Slack message mentions "{kw}" which matches your current code. The fix or discussion may already be there.',
    },
    {
        "name":   "figma_vs_code",
        "apps_a": {"Figma","Adobe XD"},
        "apps_b": {"VS Code","PyCharm","IntelliJ","Chrome"},
        "type":   "conflict",
        "title":  'Design and code both mention "{kw}" — are they in sync?',
        "detail": 'Your Figma design and code both reference "{kw}". Make sure the implementation matches the latest design.',
    },
    {
        "name":   "email_vs_notion",
        "apps_a": {"Gmail","Outlook","Thunderbird"},
        "apps_b": {"Notion","Obsidian"},
        "type":   "conflict",
        "title":  'Email and notes both discuss "{kw}"',
        "detail": 'An email and your Notion notes mention "{kw}". There may be new information in the email that should update your notes.',
    },
    {
        "name":   "browser_vs_code",
        "apps_a": {"Chrome","Firefox","Edge","Brave"},
        "apps_b": {"VS Code","PyCharm","IntelliJ"},
        "type":   "answer",
        "title":  'Your browser research on "{kw}" matches your current code',
        "detail": 'You searched for "{kw}" in your browser and are editing a related file. The solution you found may apply directly.',
    },
    {
        "name":   "github_vs_code",
        "apps_a": {"Chrome","Firefox","Edge"},
        "apps_b": {"VS Code","PyCharm"},
        "type":   "conflict",
        "title":  'GitHub and local editor both show "{kw}"',
        "detail": 'You are viewing "{kw}" on GitHub and editing it locally. Make sure you have pulled the latest changes.',
    },
    {
        "name":   "slack_vs_notion",
        "apps_a": {"Slack","Teams"},
        "apps_b": {"Notion","Obsidian"},
        "type":   "auto_update",
        "title":  'Slack discussion on "{kw}" — update your notes?',
        "detail": 'A Slack conversation about "{kw}" may contain decisions that should be added to your Notion notes.',
    },
    {
        "name":   "email_vs_slack",
        "apps_a": {"Gmail","Outlook"},
        "apps_b": {"Slack","Teams"},
        "type":   "answer",
        "title":  'Email and Slack both discuss "{kw}"',
        "detail": 'Both your email and a Slack message mention "{kw}". Check both for conflicting information or decisions.',
    },
    {
        "name":   "postman_vs_code",
        "apps_a": {"Postman","Insomnia"},
        "apps_b": {"VS Code","Chrome"},
        "type":   "answer",
        "title":  'API test on "{kw}" matches your current code',
        "detail": 'You are testing an endpoint related to "{kw}" in Postman while editing the same in your editor.',
    },
    {
        "name":   "office_vs_code",
        "apps_a": {"Excel","Word","PowerPoint"},
        "apps_b": {"VS Code","Chrome","Notion"},
        "type":   "answer",
        "title":  'Office document and your work both mention "{kw}"',
        "detail": 'A document and your current task share "{kw}". The document may contain specs or requirements for what you are doing.',
    },
    {
        "name":   "whatsapp_vs_work",
        "apps_a": {"WhatsApp","Telegram"},
        "apps_b": {"VS Code","Notion","Chrome","Gmail"},
        "type":   "answer",
        "title":  'Message about "{kw}" — relevant to your current work',
        "detail": 'A WhatsApp message mentions "{kw}" which is your current focus. It may contain useful information.',
    },
    {
        "name":   "zoom_vs_work",
        "apps_a": {"Zoom","Teams"},
        "apps_b": {"VS Code","Notion","Chrome"},
        "type":   "meeting_prep",
        "title":  'Active meeting — "{kw}" also appears in your recent work',
        "detail": 'You are in a meeting and "{kw}" appears in your recent context. This topic may come up.',
    },
]


def is_meaningful(kw: str) -> bool:
    """Return True if keyword is worth showing as an insight."""
    if len(kw) < MIN_KW_LEN:
        return False
    if kw.lower() in NOISE_WORDS:
        return False
    # Filter pure numbers
    if kw.isdigit():
        return False
    # Filter paths and single letters
    if len(kw) < 4:
        return False
    return True


class ConflictDetector:
    def __init__(self, config, db):
        self.config    = config
        self.db        = db
        self._fired: dict[str, float] = {}
        self._cooldown = 600   # 10 min between same insight (was 5 min — increased)

    def analyse(self) -> list[Insight]:
        recent = self.db.get_recent_events(limit=60, hours=2)
        if len(recent) < 2:
            return []

        # Build app -> keywords map, filtering noise
        app_kws: dict[str, set] = {}
        for ev in recent:
            app = ev["app_name"]
            raw = (ev.get("keywords") or "")
            kws = {k.strip().lower() for k in raw.split(",")
                   if k.strip() and is_meaningful(k.strip())}
            if app not in app_kws:
                app_kws[app] = set()
            app_kws[app] |= kws

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

        new_kws = {k.lower() for k in event.keywords if is_meaningful(k)}
        if not new_kws:
            return []

        recent  = self.db.get_recent_events(limit=40, hours=1)
        results = []

        for ev in recent:
            if ev["app_name"] == event.app_name:
                continue
            db_kws = {k.strip().lower()
                      for k in (ev.get("keywords") or "").split(",")
                      if k.strip() and is_meaningful(k.strip())}
            shared = new_kws & db_kws
            if not shared:
                continue

            kw  = max(shared, key=len)
            key = f"quick_{event.app_name}_{ev['app_name']}_{kw}"
            if self._on_cd(key):
                continue

            itype = self._guess_type(event.app_name, ev["app_name"])
            title = f'"{kw}" — detected in {event.app_name} and {ev["app_name"]}'
            detail = (
                f'Your {event.app_name} window and a recent {ev["app_name"]} '
                f'activity both involve "{kw}". This may be relevant to '
                f'what you are working on right now.'
            )
            ins = Insight(itype, title, detail,
                          [event.app_name, ev["app_name"]],
                          min(1.0, len(shared) * 0.3))
            ins.id = self.db.add_insight(
                ins.insight_type, ins.title,
                ins.detail, ",".join(ins.source_apps))
            self._mark(key)
            results.append(ins)
            if len(results) >= 1:   # Max 1 quick insight per event
                break

        return results

    def _check_rule(self, rule, app_kws) -> Optional[Insight]:
        active   = set(app_kws.keys())
        matched_a = [a for a in active
                     if any(t.lower() in a.lower() for t in rule["apps_a"])]
        matched_b = [a for a in active
                     if any(t.lower() in a.lower() for t in rule["apps_b"])]

        if not matched_a or not matched_b:
            return None

        # Avoid matching app with itself
        if set(matched_a) == set(matched_b):
            return None

        all_matches = matched_a + matched_b
        all_kws: set = set()
        for a in all_matches:
            all_kws |= app_kws[a]

        shared = {kw for kw in all_kws
                  if is_meaningful(kw) and
                  sum(1 for a in all_matches if kw in app_kws[a]) >= 2}

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
            source_apps  = (matched_a + matched_b)[:3],
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
