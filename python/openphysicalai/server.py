"""JSON-lines sidecar for the Electron app. stdin: {"id":n,"cmd":...,...}  stdout: replies + events."""
from __future__ import annotations

import argparse
import json
import platform
import sys
import threading
import traceback

from . import __version__
from .planners import ollama_models
from .profiler import gpu_snapshot
from .report import budget_card
from .runner import RunConfig, run
from .store import Store
from .tasks import TASKS
from .budget import PROFILES

_out = threading.Lock()


def send(obj):
    with _out:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()


def hardware():
    import psutil
    g = gpu_snapshot()
    cls = "CPU-only"
    if g:
        t = g["total_gb"]
        cls = "OPAI-2G" if t <= 3 else "OPAI-4G" if t <= 6 else "OPAI-8G" if t <= 10 else "OPAI-12G" if t <= 14 else "OPAI-16G" if t <= 20 else "OPAI-24G" if t <= 32 else "OPAI-PRO"
    vm = psutil.virtual_memory()
    return {"os": platform.platform(), "python": sys.version.split()[0], "cpu": platform.processor() or platform.machine(),
            "cores": psutil.cpu_count(logical=True), "ram_total_gb": round(vm.total / 2 ** 30, 1), "ram_free_gb": round(vm.available / 2 ** 30, 1),
            "gpu": g, "hardware_class": cls}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    args = ap.parse_args()
    store = Store(args.data)
    cancel = threading.Event()
    running = {"t": None}

    def do_run(rid, cfgd):
        try:
            cfg = RunConfig.from_dict(cfgd)
            cancel.clear()
            res = run(cfg, emit=lambda ev: send({**ev, "rid": rid}), cancel=cancel)
            if res:
                store.save(res)
                send({"event": "done", "rid": rid, "run_id": res["id"]})
        except Exception as e:  # noqa: BLE001
            send({"event": "error", "rid": rid, "message": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]})
        finally:
            running["t"] = None

    send({"event": "ready", "version": __version__})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
            cmd, mid = m.get("cmd"), m.get("id")
            if cmd == "hello":
                res = {"version": __version__, "tasks": TASKS, "budgets": {k: v.__dict__ for k, v in PROFILES.items()}}
            elif cmd == "hardware":
                res = hardware()
            elif cmd == "ollama":
                res = ollama_models(m.get("host", "http://127.0.0.1:11434"))
            elif cmd == "run":
                if running["t"] and running["t"].is_alive():
                    send({"id": mid, "ok": False, "error": "a run is already in progress"})
                    continue
                t = threading.Thread(target=do_run, args=(mid, m.get("config", {})), daemon=True)
                running["t"] = t
                t.start()
                res = {"started": True}
            elif cmd == "cancel":
                cancel.set()
                res = {"cancelling": True}
            elif cmd == "list_runs":
                res = store.list()
            elif cmd == "get_run":
                r = store.get(m["run_id"])
                if r:
                    r = {k: v for k, v in r.items() if k != "episodes_detail"} | {"n_episodes_detail": len(r.get("episodes_detail", []))}
                res = r
            elif cmd == "card":
                r = store.get(m["run_id"])
                res = budget_card(r) if r else None
            elif cmd == "clear_runs":
                store.clear()
                res = True
            elif cmd == "poke":
                from .runner import poke as do_poke
                res = {"poked": do_poke(m.get("action", ""))}
            else:
                send({"id": mid, "ok": False, "error": f"unknown cmd {cmd}"})
                continue
            send({"id": mid, "ok": True, "result": res})
        except Exception as e:  # noqa: BLE001
            send({"id": m.get("id") if isinstance(m, dict) else None, "ok": False, "error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    main()
