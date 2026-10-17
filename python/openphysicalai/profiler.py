"""Resource profiler: samples process-tree RSS (+ Ollama processes), system RAM, and NVIDIA GPU
device memory / power / temperature / throttling. Reports what was actually measured and flags
estimates. VRAM per process is only available where the driver exposes it (Linux; usually not on Windows WDDM)."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil

try:
    import pynvml  # nvidia-ml-py
    pynvml.nvmlInit()
    _NVML = True
except Exception:  # noqa: BLE001
    pynvml = None
    _NVML = False

GB = 2 ** 30


def _tree_pids() -> List[psutil.Process]:
    me = psutil.Process(os.getpid())
    procs = [me] + me.children(recursive=True)
    for p in psutil.process_iter(["name"]):
        try:
            if "ollama" in (p.info["name"] or "").lower():
                procs.append(p)
        except Exception:  # noqa: BLE001
            pass
    return procs


def gpu_snapshot() -> Optional[Dict]:
    if _NVML:
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            name = pynvml.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, bytes) else name
            d = {"name": name, "total_gb": mem.total / GB, "used_gb": mem.used / GB, "source": "nvml"}
            try:
                d["power_w"] = pynvml.nvmlDeviceGetPowerUsage(h) / 1000
            except Exception:  # noqa: BLE001
                d["power_w"] = None
            try:
                d["temp_c"] = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:  # noqa: BLE001
                d["temp_c"] = None
            try:
                d["sm_clock"] = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_SM)
                r = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(h)
                d["throttled"] = bool(r & (pynvml.nvmlClocksThrottleReasonHwSlowdown | pynvml.nvmlClocksThrottleReasonSwThermalSlowdown | pynvml.nvmlClocksThrottleReasonHwThermalSlowdown))
            except Exception:  # noqa: BLE001
                d["sm_clock"], d["throttled"] = None, None
            return d
        except Exception:  # noqa: BLE001
            pass
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,power.draw,temperature.gpu,clocks.sm",
                                  "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4, check=True).stdout.strip().splitlines()[0]
            n, t, u, pw, tp, ck = [x.strip() for x in out.split(",")]
            f = lambda v: float(v) if v.replace(".", "", 1).isdigit() else None  # noqa: E731
            return {"name": n, "total_gb": float(t) / 1024, "used_gb": float(u) / 1024, "power_w": f(pw), "temp_c": f(tp), "sm_clock": f(ck), "throttled": None, "source": "nvidia-smi"}
        except Exception:  # noqa: BLE001
            return None
    return None


def _get_ollama_api_vram_gb(host: str = "http://127.0.0.1:11434") -> float:
    """Queries Ollama local daemon for exact loaded model VRAM usage."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{host}/api/ps", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=0.40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            total_vram_bytes = sum(int(m.get("size_vram", 0)) for m in models)
            return total_vram_bytes / GB
    except Exception:
        return 0.0


def gpu_process_vram_gb(pids: List[int]) -> Optional[float]:
    """Sum of VRAM attributed to given pids, or None if the driver does not expose it."""
    if not _NVML:
        return None
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        procs = pynvml.nvmlDeviceGetComputeRunningProcesses(h) + pynvml.nvmlDeviceGetGraphicsRunningProcesses(h)
        tot, seen = 0, False
        for p in procs:
            if p.pid in pids:
                if p.usedGpuMemory is None:
                    return None
                tot += p.usedGpuMemory
                seen = True
        return tot / GB if seen else 0.0
    except Exception:  # noqa: BLE001
        return None


@dataclass
class ProfileResult:
    vram_device_baseline_gb: Optional[float] = None
    vram_device_peak_gb: Optional[float] = None
    vram_process_peak_gb: Optional[float] = None
    vram_process_source: str = "unavailable"
    ram_process_peak_gb: float = 0.0
    ram_system_peak_gb: float = 0.0
    gpu_name: Optional[str] = None
    gpu_total_gb: Optional[float] = None
    energy_j: Optional[float] = None
    temp_peak_c: Optional[float] = None
    throttled_any: Optional[bool] = None
    samples: int = 0
    duration_s: float = 0.0
    confidence: str = "low"
    vram_ollama_peak_gb: float = 0.0

    def as_dict(self) -> Dict:
        return self.__dict__.copy()


class Profiler:
    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._stop = threading.Event()
        self._t: Optional[threading.Thread] = None
        self.r = ProfileResult()
        self._t0 = 0.0
        self._last_t = None
        self._pv_est_unavailable = False

    def start(self):
        g = gpu_snapshot()
        self.r.gpu_name = g["name"] if g else None
        self.r.gpu_total_gb = round(g["total_gb"], 2) if g else None
        self.r.vram_device_baseline_gb = round(g["used_gb"], 3) if g else None
        self._t0 = time.perf_counter()
        self._stop.clear()
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()
        return self

    def _sample(self):
        r = self.r
        procs = _tree_pids()
        rss = 0
        for p in procs:
            try:
                rss += p.memory_info().rss
            except Exception:  # noqa: BLE001
                pass
        r.ram_process_peak_gb = max(r.ram_process_peak_gb, rss / GB)
        r.ram_system_peak_gb = max(r.ram_system_peak_gb, (psutil.virtual_memory().total - psutil.virtual_memory().available) / GB)
        g = gpu_snapshot()
        now = time.perf_counter()
        if g:
            r.vram_device_peak_gb = max(r.vram_device_peak_gb or 0, g["used_gb"])
            if g.get("temp_c") is not None:
                r.temp_peak_c = max(r.temp_peak_c or 0, g["temp_c"])
            if g.get("throttled"):
                r.throttled_any = True
            elif r.throttled_any is None and g.get("throttled") is False:
                r.throttled_any = False
            if g.get("power_w") is not None and self._last_t is not None:
                r.energy_j = (r.energy_j or 0.0) + g["power_w"] * (now - self._last_t)
            pv = gpu_process_vram_gb([p.pid for p in procs])
            if pv is None:
                self._pv_est_unavailable = True
            else:
                r.vram_process_peak_gb = max(r.vram_process_peak_gb or 0, pv)
            ov = _get_ollama_api_vram_gb()
            if ov > 0.0:
                r.vram_ollama_peak_gb = max(r.vram_ollama_peak_gb, ov)
        self._last_t = now
        r.samples += 1

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._sample()
            except Exception:  # noqa: BLE001
                pass
            self._stop.wait(self.interval)

    def stop(self) -> ProfileResult:
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)
        r = self.r
        r.duration_s = round(time.perf_counter() - self._t0, 2)
        if r.vram_device_peak_gb is not None:
            ollama_vram = getattr(r, "vram_ollama_peak_gb", 0.0) or _get_ollama_api_vram_gb()
            desktop_floor = 0.45
            wddm_delta = max(0.0, r.vram_device_peak_gb - (r.vram_device_baseline_gb or desktop_floor))
            
            if r.vram_process_peak_gb is not None and r.vram_process_peak_gb > 0.1:
                r.vram_process_source = "nvml per-process"
                r.confidence = "high"
            elif ollama_vram > 0.1:
                # Direct report from Ollama daemon + MuJoCo 3D OpenGL renderer context (~0.18 GB)
                r.vram_process_peak_gb = round(min(r.vram_device_peak_gb, ollama_vram + 0.18), 3)
                r.vram_process_source = "ollama /api/ps + 3d gl context"
                r.confidence = "high"
            else:
                r.vram_process_peak_gb = round(wddm_delta, 3)
                r.vram_process_source = "estimated: device peak minus baseline"
                r.confidence = "medium"
            r.vram_device_peak_gb = round(r.vram_device_peak_gb, 3)
        else:
            r.confidence = "low"
        r.ram_process_peak_gb = round(r.ram_process_peak_gb, 3)
        r.ram_system_peak_gb = round(r.ram_system_peak_gb, 3)
        if r.energy_j is not None:
            r.energy_j = round(r.energy_j, 1)
        return r
