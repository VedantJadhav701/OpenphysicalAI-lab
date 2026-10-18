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
    gpu_info = None
    if g:
        t = g["total_gb"]
        u = g.get("used_gb", 0.0)
        cls = "OPAI-2G" if t <= 3 else "OPAI-4G" if t <= 6 else "OPAI-8G" if t <= 12 else "OPAI-16G"
        gpu_info = {
            **g,
            "free_gb": round(t - u, 2),
            "baseline_used_pct": round((u / t) * 100, 1) if t > 0 else 0.0,
        }
    doc = {
        "version": __version__,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "processor": platform.processor(),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_available_gb": round(mem.available / (1024**3), 2),
        "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
        "hardware_class": cls,
        "gpu": gpu_info,
    }
    print(json.dumps(doc, indent=2))
    return 0


def cmd_compare(args) -> int:
    from .stats import mcnemar_test, paired_bootstrap_difference
    with open(args.baseline, "r") as f:
        da = json.load(f)
    with open(args.treatment, "r") as f:
        db = json.load(f)

    map_a = {e["seed"]: e["success"] for e in da.get("episodes_detail", []) if "seed" in e}
    map_b = {e["seed"]: e["success"] for e in db.get("episodes_detail", []) if "seed" in e}
    common_seeds = sorted(set(map_a.keys()) & set(map_b.keys()))

    if not common_seeds:
        print(f"Error: No matching episode seeds found between {args.baseline} and {args.treatment}", file=sys.stderr)
        return 1

    ya = [map_a[s] for s in common_seeds]
    yb = [map_b[s] for s in common_seeds]

    mc = mcnemar_test(ya, yb)
    bs = paired_bootstrap_difference(ya, yb)

    tsr_a = sum(ya) / len(ya)
    tsr_b = sum(yb) / len(yb)

    print(f"\n# Paired Comparison Report")
    print(f"- Baseline: {args.baseline} ({da.get('config', {}).get('policy', 'unknown')}, verifier {da.get('config', {}).get('verifier', '?')})")
    print(f"- Treatment: {args.treatment} ({db.get('config', {}).get('policy', 'unknown')}, verifier {db.get('config', {}).get('verifier', '?')})")
    print(f"- Common paired episodes: N={len(common_seeds)}")
    print(f"- Baseline TSR: {tsr_a*100:.1f}% ({sum(ya)}/{len(ya)})")
    print(f"- Treatment TSR: {tsr_b*100:.1f}% ({sum(yb)}/{len(yb)})")
    print(f"- Mean difference: {bs['diff']*100:+.1f}% (95% bootstrap CI: {bs['ci_lower']*100:+.1f}% to {bs['ci_upper']*100:+.1f}%)")
    print(f"- McNemar test: statistic={mc['statistic']}, p-value={mc['p_value']} ({'statistically significant (p < 0.05)' if mc['significant_05'] else 'not statistically significant'})\n")
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
    cfg_dict = {k: v for k, v in vars(args).items() if k not in ("cmd", "fn", "export_json", "resume") and v is not None}
    cfg = RunConfig.from_dict(cfg_dict)
    cfg.frames = False
    if getattr(args, "resume", None):
        cfg.resume_from = args.resume

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
    elif getattr(args, "resume", None):
        with open(args.resume, "w") as f:
            json.dump(res, f, indent=2)
        print(f"Updated resumed run data in {args.resume}")

    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="opai")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profile").set_defaults(fn=cmd_profile)
    sub.add_parser("doctor", help="inspect host hardware, NVML, and budget class").set_defaults(fn=cmd_doctor)
    cb = sub.add_parser("check-budget")
    cb.add_argument("observed", help='JSON, e.g. \'{"vram_process_peak_gb": 2.1}\'')
    cb.set_defaults(fn=cmd_check_budget)
    
    cmp = sub.add_parser("compare", help="paired McNemar test and bootstrap difference between two run JSONs")
    cmp.add_argument("baseline", help="path to baseline run JSON")
    cmp.add_argument("treatment", help="path to treatment run JSON")
    cmp.set_defaults(fn=cmd_compare)

    r = sub.add_parser("run", help="headless benchmark run, prints a Budget Card")
    for name, default in (("task", "pick_place"), ("policy", "rule"), ("agent", "recovery"), ("perception", "oracle"), ("verifier", "V1"),
                          ("perturb", "clean"), ("mode", "sync"), ("budget", "standard")):
        r.add_argument("--" + name, default=default)
    r.add_argument("--episodes", type=int, default=50)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--extra-latency-ms", dest="extra_latency_ms", type=float, default=0.0)
    r.add_argument("--velocity-lead", dest="velocity_lead", action=argparse.BooleanOptionalAction, default=True)
    r.add_argument("--export-json", dest="export_json", type=str, default=None, help="path to export raw run.json")
    r.add_argument("--resume", dest="resume", type=str, default=None, help="resume from an existing run.json export")
    r.set_defaults(fn=cmd_run)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
