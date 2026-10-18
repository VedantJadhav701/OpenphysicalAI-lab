"""Benchmark V0, V1, V2 verifiers with N=100 episodes per cell."""
import json
import sys
from openphysicalai.runner import RunConfig, run

def main():
    results = {}
    for verifier in ["V0", "V1", "V2"]:
        print(f"Running Verifier {verifier} (N=100)...", flush=True)
        cfg = RunConfig(
            task="pick_place",
            agent="recovery",
            policy="rule",
            verifier=verifier,
            perturb="moderate",
            mode="realtime",
            episodes=100,
            seed=42,
            frames=False
        )
        res = run(cfg)
        m = res["metrics"]
        results[verifier] = res
        print(f"=== Verifier {verifier} (N=100) ===")
        print(f"TSR: {m['tsr']:.1%} (95% CI: {m['tsr_ci'][0]:.1%} - {m['tsr_ci'][1]:.1%})")
        print(f"Failures Injected: {m['failures_injected']}")
        print(f"Detection Rate: {m['detection_rate']}")
        print(f"Recovery Rate: {m['recovery_rate']}")
        print(f"False Alarm Rate: {m['false_alarm_rate']}")
        print(f"Missed Failure Rate: {m['missed_failure_rate']}")
        print(f"Failure Breakdown: {m['failure_breakdown']}\n", flush=True)

        with open(f"verifier_{verifier}_N100.json", "w") as f:
            json.dump(res, f, indent=2)

    with open("verifier_benchmark_summary_N100.json", "w") as f:
        json.dump({v: r["metrics"] for v, r in results.items()}, f, indent=2)

if __name__ == "__main__":
    main()
