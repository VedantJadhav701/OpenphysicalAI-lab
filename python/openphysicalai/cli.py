"""opai CLI (scaffold): `opai profile`, `opai check-budget`."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys

from . import __version__
from .budget import Budget, evaluate_budget
from .profiler import gpu_snapshot


def cmd_profile(_args) -> int:
    info = {
        "version": __version__,
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "gpu": gpu_snapshot(),
    }
    print(json.dumps(info, indent=2))
    return 0


def cmd_doctor(_args) -> int:
    import psutil
    g = gpu_snapshot()
    mem = psutil.virtual_memory()
    cls = "CPU-only"
    if g:
        t = g["total_gb"]
        cls = "OPAI-2G" if t <= 3 else "OPAI-4G" if t <= 6 else "OPAI-8G" if t <= 12 else "OPAI-16G"
    doc = {
        "version": __version__,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "processor": platform.processor(),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_available_gb": round(mem.available / (1024**3), 2),
        "hardware_class": cls,
        "gpu": g,
    }
    print(json.dumps(doc, indent=2))
    return 0


def cmd_check_budget(args) -> int:
    observed = json.loads(args.observed)
    res = evaluate_budget(Budget(), observed)
    print("PASS" if res.passed else "FAIL")
    for c in res.checks:
        print(f"  {'ok ' if c.ok else 'BAD'} {c.name}: {c.value} / {c.cap} {c.note}")
    return 0 if res.passed else 1


def cmd_run(args) -> int:
    from .report import budget_card
    from .runner import RunConfig, run
    cfg_dict = {k: v for k, v in vars(args).items() if k not in ("cmd", "fn", "export_json") and v is not None}
    cfg = RunConfig.from_dict(cfg_dict)
    cfg.frames = False

    reproduce_cmd = (
        f"opai run --task {cfg.task} --policy {cfg.policy} --agent {cfg.agent} "
        f"--perception {cfg.perception} --verifier {cfg.verifier} --perturb {cfg.perturb} "
        f"--mode {cfg.mode} --budget {cfg.budget} --episodes {cfg.episodes} --seed {cfg.seed}"
    )

    def emit(e):
        if e.get("event") == "progress" and e["done"] % 10 == 0:
            print(f"  episode {e['done']}/{e['total']}  successes {e['successes']}", file=sys.stderr)

    res = run(cfg, emit=emit)
    res["reproduce_command"] = reproduce_cmd
    card_text = budget_card(res)
    print(card_text)
    print(f"\nReproduce command:\n  {reproduce_cmd}\n")

    if getattr(args, "export_json", None):
        out_path = args.export_json
        with open(out_path, "w") as f:
            json.dump(res, f, indent=2)
        print(f"Exported raw run data to {out_path}")

    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="opai")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profile").set_defaults(fn=cmd_profile)
    sub.add_parser("doctor", help="inspect host hardware, NVML, and budget class").set_defaults(fn=cmd_doctor)
    cb = sub.add_parser("check-budget")
    cb.add_argument("observed", help='JSON, e.g. \'{"vram_process_peak_gb": 2.1}\'')
    cb.set_defaults(fn=cmd_check_budget)
    r = sub.add_parser("run", help="headless benchmark run, prints a Budget Card")
    for name, default in (("task", "pick_place"), ("policy", "rule"), ("agent", "recovery"), ("perception", "oracle"), ("verifier", "V1"),
                          ("perturb", "clean"), ("mode", "sync"), ("budget", "standard")):
        r.add_argument("--" + name, default=default)
    r.add_argument("--episodes", type=int, default=50)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--extra-latency-ms", dest="extra_latency_ms", type=float, default=0.0)
    r.add_argument("--velocity-lead", dest="velocity_lead", action=argparse.BooleanOptionalAction, default=True)
    r.add_argument("--export-json", dest="export_json", type=str, default=None, help="path to export raw run.json")
    r.set_defaults(fn=cmd_run)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
