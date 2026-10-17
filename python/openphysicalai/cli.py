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


def _nvidia():
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip().splitlines()[0]
        name, total, used = [x.strip() for x in out.split(",")]
        return {"name": name, "vram_total_gb": round(float(total) / 1024, 2), "vram_used_gb": round(float(used) / 1024, 2)}
    except Exception:
        return None


def cmd_profile(_args) -> int:
    info = {"version": __version__, "os": platform.platform(), "python": sys.version.split()[0], "gpu": _nvidia()}
    print(json.dumps(info, indent=2))
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
    cfg = RunConfig.from_dict({k: v for k, v in vars(args).items() if k not in ("cmd", "fn") and v is not None})
    cfg.frames = False

    def emit(e):
        if e.get("event") == "progress" and e["done"] % 10 == 0:
            print(f"  episode {e['done']}/{e['total']}  successes {e['successes']}", file=sys.stderr)

    print(budget_card(run(cfg, emit=emit)))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="opai")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profile").set_defaults(fn=cmd_profile)
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
    r.set_defaults(fn=cmd_run)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
