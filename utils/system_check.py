"""
utils/system_check.py
Reads the hardware specs of the current machine and recommends
whether to run ContextOS in lite, full, or cloud mode.
Works on Windows, Linux, and Mac.
"""

import os
import platform
import logging

logger = logging.getLogger(__name__)


class SystemCheck:

    def get_specs(self) -> dict:
        """Return a dict of key hardware specs."""
        return {
            "ram_gb":    self._get_ram_gb(),
            "cpu_cores": self._get_cpu_cores(),
            "os_version": platform.platform(),
            "is_windows": os.name == "nt",
        }

    def recommend_mode(self) -> str:
        """
        Choose the right mode based on available RAM:
          < 3 GB  → lite   (keyword rules only, no AI)
          3–6 GB  → full   (local small AI model)
          > 6 GB  → full   (full local AI + faster analysis)
        """
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
