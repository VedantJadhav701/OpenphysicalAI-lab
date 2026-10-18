import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, "python")
from openphysicalai.runner import RunConfig, run
from openphysicalai.report import budget_card
from openphysicalai.stats import mcnemar_test, paired_bootstrap_difference

MODELS = ["llama3.2:1b", "gemma2:2b", "qwen2.5:3b"]
EPISODES = 50
TASK = "pick_place"
PERTURB = "moderate"
VERIFIER = "V1"
MODE = "sync"


def unload_all():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            for m in data.get("models", []):
                name = m.get("name")
                if name:
                    u_req = urllib.request.Request(
                        "http://127.0.0.1:11434/api/generate",
                        data=json.dumps({"model": name, "keep_alive": 0}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    urllib.request.urlopen(u_req, timeout=3)
    except Exception as e:
        print(f"Warning unloading models: {e}")


def main():
    results = {}
    print(f"=== Starting 3-Model Benchmark: N={EPISODES}, Task={TASK}, Perturb={PERTURB} ===\n")
    
    for m in MODELS:
        print(f"\n>>> Benchmarking model: {m} (N={EPISODES}) ...")
        unload_all()
        time.sleep(1.0)
        
        cfg = RunConfig(
            task=TASK,
            policy=f"ollama:{m}",
            agent="recovery",
            perception="oracle",
            verifier=VERIFIER,
            perturb=PERTURB,
            mode=MODE,
            episodes=EPISODES,
            seed=0,
            frames=False,
        )
        
        def emit(e):
            if e.get("event") == "progress" and e["done"] % 10 == 0:
                print(f"  [{m}] episode {e['done']}/{e['total']}  successes: {e['successes']}", file=sys.stderr)
        
        t0 = time.perf_counter()
        res = run(cfg, emit=emit)
        dur = time.perf_counter() - t0
        
        out_name = f"model_{m.replace(':', '_')}_N{EPISODES}.json"
        with open(out_name, "w") as f:
            json.dump(res, f, indent=2)
            
        results[m] = res
        card = budget_card(res)
        print(f"\n--- Budget Card for {m} ---")
        print(card)
        print(f"Saved to {out_name} (Duration: {dur:.1f}s)")

    print("\n=======================================================")
    print("=== PAIRED STATISTICAL COMPARISON ACROSS MODELS ===")
    print("=======================================================")
    
    pairs = [
        ("llama3.2:1b", "gemma2:2b"),
        ("gemma2:2b", "qwen2.5:3b"),
        ("llama3.2:1b", "qwen2.5:3b"),
    ]
    
    for ma, mb in pairs:
        ya = [e["success"] for e in results[ma]["episodes_detail"]]
        yb = [e["success"] for e in results[mb]["episodes_detail"]]
        mc = mcnemar_test(ya, yb)
        bs = paired_bootstrap_difference(ya, yb)
        tsr_a = results[ma]["metrics"]["tsr"] * 100
        tsr_b = results[mb]["metrics"]["tsr"] * 100
        print(f"\n--- {ma} vs {mb} (N={EPISODES}) ---")
        print(f"  TSR {ma}: {tsr_a:.1f}% vs {mb}: {tsr_b:.1f}%")
        print(f"  Mean diff: {bs['diff']*100:+.1f}% (95% CI: {bs['ci_lower']*100:+.1f}% to {bs['ci_upper']*100:+.1f}%)")
        print(f"  McNemar p-value: {mc['p_value']} (stat={mc['statistic']}, sig={mc['significant_05']})")


if __name__ == "__main__":
    main()
