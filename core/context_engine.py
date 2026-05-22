"""
core/context_engine.py  -  Orchestrates watcher + detector + CPU guard.
"""
import time, logging, threading, os
from typing import Callable
from core.conflict_detector import ConflictDetector, Insight

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"

class ContextEngine:
    def __init__(self, config, db):
        self.config   = config
        self.db       = db
        self._running = False
        self._paused  = False
        self._thread  = None
        self._listeners: list[Callable] = []
        self.stats    = {"insights_today":0,"conflicts_caught":0,
                         "tasks_auto_done":0,"focus_minutes":0}
        self._watcher  = None
        self._detector = None

    def add_insight_listener(self, fn):
        self._listeners.append(fn)

    def start(self, watcher, detector):
        self._watcher  = watcher
        self._detector = detector
        watcher.add_listener(self._on_event)
        watcher.start()
        self._running = True
        self._thread  = threading.Thread(target=self._loop, name="ContextEngine", daemon=True)
        self._thread.start()
        logger.info("ContextEngine started.")

    def stop(self):
        self._running = False
        if self._watcher:
            self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)

    def get_stats(self):
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    self.stats["focus_minutes"],
        }

    def _on_event(self, event):
        if self._paused:
            return
        try:
            for ins in self._detector.analyse_single_event(event):
                self._dispatch(ins)
        except Exception as e:
            logger.error(f"Quick analysis error: {e}")

    def _loop(self):
        interval = int(self.config.get("analysis_interval", 30))
        while self._running:
            time.sleep(interval)
            if not self._running:
                break
            if self._paused:
                continue
            if self.config.get("smart_pause", True):
                cpu = self._cpu()
                thr = int(self.config.get("smart_pause_threshold", 80))
                if cpu > thr:
                    logger.info(f"CPU {cpu:.0f}% — pausing.")
                    self._paused = True
                    if self._watcher:
                        self._watcher.pause()
                    continue
                elif self._paused and cpu < thr - 10:
                    logger.info(f"CPU {cpu:.0f}% — resuming.")
                    self._paused = False
                    if self._watcher:
                        self._watcher.resume()
            try:
                for ins in self._detector.analyse():
                    self._dispatch(ins)
                self.stats["focus_minutes"] += interval // 60
            except Exception as e:
                logger.error(f"Analysis error: {e}")

    def _dispatch(self, insight):
        for fn in self._listeners:
            try:
                fn(insight)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def _cpu(self):
        if IS_WINDOWS:
            try:
                import psutil
                return psutil.cpu_percent(interval=1)
            except Exception:
                return 0.0
        try:
            with open("/proc/stat") as f:
                parts = list(map(int, f.readline().split()[1:]))
            idle  = parts[3]
            total = sum(parts)
            return max(0.0, 100.0 - idle/total*100.0)
        except Exception:
            return 0.0
