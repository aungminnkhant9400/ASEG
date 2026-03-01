from typing import Dict, Optional

try:
    from pynvml import (
        NVML_TEMPERATURE_GPU,
        nvmlDeviceGetCount,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetMemoryInfo,
        nvmlDeviceGetName,
        nvmlDeviceGetTemperature,
        nvmlDeviceGetUUID,
        nvmlDeviceGetUtilizationRates,
        nvmlInit,
    )

    NVML_IMPORTED = True
except Exception:
    NVML_IMPORTED = False


class GPUMonitor:
    def __init__(self, gpu_index: int = 0) -> None:
        self.gpu_index = gpu_index
        self._enabled = False
        self._handle = None

        if not NVML_IMPORTED:
            return

        try:
            nvmlInit()
            count = nvmlDeviceGetCount()
            if count < 1:
                return
            index = min(self.gpu_index, count - 1)
            self._handle = nvmlDeviceGetHandleByIndex(index)
            self._enabled = True
        except Exception:
            self._enabled = False
            self._handle = None

    def get_stats(self) -> Dict[str, Optional[float]]:
        stats: Dict[str, Optional[float]] = {
            "name": None,
            "uuid": None,
            "utilization_pct": None,
            "mem_used_mb": None,
            "mem_total_mb": None,
            "temperature_c": None,
        }

        if not self._enabled or self._handle is None:
            return stats

        try:
            name = nvmlDeviceGetName(self._handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="ignore")

            uuid = nvmlDeviceGetUUID(self._handle)
            if isinstance(uuid, bytes):
                uuid = uuid.decode("utf-8", errors="ignore")

            utilization = nvmlDeviceGetUtilizationRates(self._handle)
            memory = nvmlDeviceGetMemoryInfo(self._handle)
            temperature = nvmlDeviceGetTemperature(self._handle, NVML_TEMPERATURE_GPU)

            stats.update(
                {
                    "name": str(name),
                    "uuid": str(uuid),
                    "utilization_pct": float(utilization.gpu),
                    "mem_used_mb": round(memory.used / (1024 * 1024), 2),
                    "mem_total_mb": round(memory.total / (1024 * 1024), 2),
                    "temperature_c": float(temperature),
                }
            )
        except Exception:
            return stats

        return stats
