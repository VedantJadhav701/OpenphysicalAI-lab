"""Run velocity lead latency sweep: extra_latency in [0, 500, 1000, 2000] ms with velocity_lead ON vs OFF.
Seeds 0..49 (N=50 per cell). Saves raw and summary to benchmarks/velocity_lead_sweep.json.
"""
import json
import os
import sys
from openphysicalai.runner import RunConfig, run
from openphysicalai.stats import wilson_interval, mcnemar_test, paired_bootstrap_difference

def main():
    latencies = [0, 500, 1000, 2000]
    n_episodes = 50
    results = {}

    print(f"Starting Velocity Lead Latency Sweep (N={n_episodes} per condition)...")

    for lat in latencies:
        print(f"\n==========================================")
        print(f"Latency: {lat} ms")
        print(f"==========================================")

        # 1. Lead ON
        cfg_on = RunConfig(
            task="dynamic",
            policy="rule",
            agent="recovery",
            perception="oracle",
            verifier="V1",
            perturb="clean",
            mode="realtime",
            budget="standard",
            episodes=n_episodes,
            seed=0,
            extra_latency_ms=float(lat),
            velocity_lead=True,
            frames=False,
        )
        res_on = run(cfg_on)
        m_on = res_on["metrics"]
        tsr_on = m_on["tsr"]
        succ_on = m_on["successes"]
        ci_on = wilson_interval(succ_on, n_episodes)
        print(f"  Lead ON:  {tsr_on*100:.1f}% ({succ_on}/{n_episodes}), 95% Wilson CI: [{ci_on[0]*100:.1f}%, {ci_on[1]*100:.1f}%]")

        # 2. Lead OFF
        cfg_off = RunConfig(
            task="dynamic",
            policy="rule",
            agent="recovery",
            perception="oracle",
            verifier="V1",
            perturb="clean",
            mode="realtime",
            budget="standard",
            episodes=n_episodes,
            seed=0,
            extra_latency_ms=float(lat),
            velocity_lead=False,
            frames=False,
        )
        res_off = run(cfg_off)
        m_off = res_off["metrics"]
        tsr_off = m_off["tsr"]
        succ_off = m_off["successes"]
        ci_off = wilson_interval(succ_off, n_episodes)
        print(f"  Lead OFF: {tsr_off*100:.1f}% ({succ_off}/{n_episodes}), 95% Wilson CI: [{ci_off[0]*100:.1f}%, {ci_off[1]*100:.1f}%]")

        # Paired statistics
        y_on = [e["success"] for e in res_on["episodes_detail"]]
        y_off = [e["success"] for e in res_off["episodes_detail"]]
        mc = mcnemar_test(y_off, y_on)  # baseline=OFF, treatment=ON
        bs = paired_bootstrap_difference(y_off, y_on)

        print(f"  Paired Delta: {bs['diff']*100:+.1f}% (95% CI: [{bs['ci_lower']*100:+.1f}%, {bs['ci_upper']*100:+.1f}%])")
        print(f"  McNemar p-value: {mc['p_value']} (stat={mc['statistic']:.2f})")

        results[f"{lat}ms"] = {
            "extra_latency_ms": lat,
            "on": {
                "success_rate": tsr_on,
                "successes": succ_on,
                "n": n_episodes,
                "wilson_ci_95": ci_on,
                "energy_j_per_ep": res_on.get("energy_j_per_ep"),
                "episodes_detail": res_on["episodes_detail"],
            },
            "off": {
                "success_rate": tsr_off,
                "successes": succ_off,
                "n": n_episodes,
                "wilson_ci_95": ci_off,
                "energy_j_per_ep": res_off.get("energy_j_per_ep"),
                "episodes_detail": res_off["episodes_detail"],
            },
            "paired_stats": {
                "diff": bs["diff"],
                "bootstrap_ci_95": [bs["ci_lower"], bs["ci_upper"]],
                "mcnemar_stat": mc["statistic"],
                "mcnemar_p_value": mc["p_value"],
                "significant_05": mc["significant_05"],
            }
        }

    out_file = os.path.join("benchmarks", "velocity_lead_sweep.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved complete sweep results to {out_file}")

if __name__ == "__main__":
    main()
