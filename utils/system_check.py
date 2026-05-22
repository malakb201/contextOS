"""
utils/system_check.py  -  Reads hardware specs and recommends a mode.
"""
import os, platform, logging
logger = logging.getLogger(__name__)

class SystemCheck:
    def get_specs(self):
        return {
            "ram_gb":     self._ram(),
            "cpu_cores":  self._cores(),
            "os_version": platform.platform(),
            "is_windows": os.name == "nt",
        }

    def recommend_mode(self):
        ram = self._ram()
        mode = "lite" if ram < 3.0 else "full"
        logger.info(f"RAM={ram:.1f}GB -> {mode} mode")
        return mode

    def _ram(self):
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            pass
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        return int(line.split()[1]) / (1024**2)
        except Exception:
            pass
        return 4.0

    def _cores(self):
        return os.cpu_count() or 2
