"""
core/conflict_detector.py  -  Finds conflicts and answers across apps.
No AI needed — pure keyword matching. Fast and works offline.
"""
import logging, time
from dataclasses import dataclass, field
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

CONFLICT_RULES = [
    {
        "name":          "code_vs_email",
        "trigger_apps":  {"VS Code","Gmail","Outlook"},
        "insight_type":  "conflict",
        "title_template":  "Possible conflict: \"{kw}\" in email and your code",
        "detail_template": "You have an email mentioning \"{kw}\" and you are editing a related file. Check if the email has instructions about this code.",
    },
    {
        "name":          "slack_answer",
        "trigger_apps":  {"Slack","Teams","VS Code","Chrome"},
        "insight_type":  "answer",
        "title_template":  "Slack may have the answer for \"{kw}\"",
        "detail_template": "A recent Slack message mentions \"{kw}\" which matches what you are working on. The fix may already be there.",
    },
    {
        "name":          "notion_task_match",
        "trigger_apps":  {"Notion","Obsidian","VS Code","Figma"},
        "insight_type":  "auto_update",
        "title_template":  "Task \"{kw}\" may be ready to mark in-progress",
        "detail_template": "You have been working on \"{kw}\" for a while. Your Notion board may have a matching task to update.",
    },
    {
        "name":          "figma_code_mismatch",
        "trigger_apps":  {"Figma","VS Code"},
        "insight_type":  "conflict",
        "title_template":  "Design and code both mention \"{kw}\"",
        "detail_template": "Your Figma design and current code file both reference \"{kw}\". Make sure they are in sync.",
    },
    {
        "name":          "browser_research",
        "trigger_apps":  {"Chrome","Firefox","Edge","VS Code"},
        "insight_type":  "answer",
        "title_template":  "Your browser research relates to \"{kw}\"",
        "detail_template": "You searched for \"{kw}\" in your browser and are currently working on something related.",
    },
]

class ConflictDetector:
    def __init__(self, config, db):
        self.config  = config
        self.db      = db
        self._fired: dict = {}
        self._cooldown    = 300

    def analyse(self):
        recent = self.db.get_recent_events(limit=50, hours=2)
        if len(recent) < 2:
            return []
        app_kws: dict = {}
        for e in recent:
            app = e["app_name"]
            kws = e.get("keywords","") or ""
            if app not in app_kws:
                app_kws[app] = set()
            app_kws[app].update(k.strip().lower() for k in kws.split(",") if k.strip())
        results = []
        for rule in CONFLICT_RULES:
            ins = self._apply(rule, app_kws)
            if ins:
                ins.id = self.db.add_insight(ins.insight_type, ins.title,
                                              ins.detail, ",".join(ins.source_apps))
                results.append(ins)
        return results

    def analyse_single_event(self, event):
        if not event or not event.keywords:
            return []
        recent   = self.db.get_recent_events(limit=30, hours=1)
        insights = []
        for ev in recent:
            if ev["app_name"] == event.app_name:
                continue
            db_kws  = set((ev.get("keywords") or "").split(","))
            new_kws = set(event.keywords)
            shared  = {k for k in db_kws & new_kws if len(k) >= 4}
            if not shared:
                continue
            kw  = max(shared, key=len)
            key = f"quick_{event.app_name}_{ev['app_name']}_{kw}"
            if self._on_cd(key):
                continue
            itype  = "answer" if any(c in ev["app_name"].lower()
                                     for c in ["slack","teams","gmail","outlook"]) else "conflict"
            title  = f'"{kw}" seen in both {event.app_name} and {ev["app_name"]}'
            detail = (f'Your {event.app_name} window and a recent {ev["app_name"]} '
                      f'event both mention "{kw}". This might be relevant.')
            ins = Insight(itype, title, detail, [event.app_name, ev["app_name"]],
                          min(1.0, len(shared)*0.3))
            ins.id = self.db.add_insight(ins.insight_type, ins.title,
                                          ins.detail, ",".join(ins.source_apps))
            self._mark(key)
            insights.append(ins)
            if len(insights) >= 2:
                break
        return insights

    def _apply(self, rule, app_kws):
        trigger  = rule["trigger_apps"]
        active   = list(app_kws.keys())
        matched  = [a for a in active if any(t.lower() in a.lower() for t in trigger)]
        if len(matched) < 2:
            return None
        kw_per   = {a: app_kws[a] for a in matched}
        all_kws  = set()
        for kws in kw_per.values():
            all_kws |= kws
        shared = set()
        for kw in all_kws:
            if len(kw) < 4:
                continue
            if sum(1 for kws in kw_per.values() if kw in kws) >= 2:
                shared.add(kw)
        if not shared:
            return None
        kw  = max(shared, key=len)
        key = f"{rule['name']}_{kw}"
        if self._on_cd(key):
            return None
        self._mark(key)
        return Insight(
            rule["insight_type"],
            rule["title_template"].format(kw=kw),
            rule["detail_template"].format(kw=kw),
            matched[:3],
            min(1.0, len(shared)*0.25+0.25),
        )

    def _on_cd(self, key):
        return (time.time() - self._fired.get(key, 0)) < self._cooldown

    def _mark(self, key):
        self._fired[key] = time.time()
