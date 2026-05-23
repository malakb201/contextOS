"""
core/context_engine.py
The orchestrator. Connects the AppWatcher to the ConflictDetector
and runs the periodic full-analysis loop.

Responsibilities:
  - Receive AppEvents from AppWatcher in real-time
  - Run quick conflict checks on each new event
  - Every N seconds, run a full analysis of all recent events
  - Monitor CPU and trigger pause/resume on AppWatcher
  - Notify the UI layer when new insights are ready
"""

import time
import logging
import threading
import os
from typing import Callable

from core.conflict_detector import ConflictDetector, Insight

logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"


class ContextEngine:
    """
    Sits between the watcher (input) and the UI (output).

    Usage:
        engine = ContextEngine(config, db)
        engine.add_insight_listener(my_ui_callback)
        engine.start(watcher, detector)
        ...
        engine.stop()
    """

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
        """Register a callback called whenever a new insight is created."""
        self._insight_listeners.append(fn)

    def start(self, watcher, detector: ConflictDetector):
        """Start the engine. Wires up the watcher listener and analysis loop."""
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
        """Gracefully stop everything."""
        self._running = False
        if self._watcher:
            self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ContextEngine stopped.")

    def get_stats(self) -> dict:
        """Return today's stats for the dashboard Home tab."""
        counts = self.db.get_insight_count_today()
        return {
            "insights_today":   sum(counts.values()),
            "conflicts_caught": counts.get("conflict", 0),
            "tasks_auto_done":  counts.get("auto_update", 0),
            "focus_minutes":    self.stats["focus_minutes"],
        }

    # ── Real-time event handler ────────────────────────────────────────────────

    def _on_app_event(self, event):
        """Called by AppWatcher every time the active window changes."""
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
        """Every N seconds, run a full analysis of all recent events."""
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
        """Send a new insight to all registered UI listeners."""
        logger.info(f"Dispatching insight: {insight}")
        for fn in self._insight_listeners:
            try:
                fn(insight)
            except Exception as e:
                logger.error(f"Insight listener error: {e}")

    # ── CPU monitoring ─────────────────────────────────────────────────────────

    def _get_cpu_percent(self) -> float:
        """Return current overall CPU usage as a percentage (0–100)."""
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
