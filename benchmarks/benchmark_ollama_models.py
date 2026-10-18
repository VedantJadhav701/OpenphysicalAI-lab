"""Benchmark 3 local Ollama models with success, latency, and VRAM on RTX 3050 Laptop."""
import json
import time
from openphysicalai.runner import RunConfig, run

MODELS = ["llama3.2:1b", "gemma2:2b", "qwen2.5:3b"]
EPISODES = 20  # N=20 each for rigorous comparison across models

def main():
    benchmarks = {}
    for m in MODELS:
        print(f"\n==========================================", flush=True)
        print(f"Benchmarking model: {m} (N={EPISODES})", flush=True)
        print(f"==========================================", flush=True)
        cfg = RunConfig(
            task="pick_place",
            agent="closed_loop",
            policy=f"ollama:{m}",
            verifier="V1",
            perturb="clean",
            mode="realtime",
            episodes=EPISODES,
            seed=10,
            frames=False
        )
        try:
            t0 = time.time()
            res = run(cfg)
            elapsed = time.time() - t0
            metrics = res["metrics"]
            profile = res["profile"]
            benchmarks[m] = {
                "model": m,
                "episodes": EPISODES,
                "successes": metrics["successes"],
                "tsr": metrics["tsr"],
                "tsr_ci": metrics["tsr_ci"],
                "latency_p50_ms": metrics["latency_ms"]["p50"],
                "latency_p95_ms": metrics["latency_ms"]["p95"],
                "tok_per_s_mean": metrics["tokens_per_s_mean"],
                "vram_device_peak_gb": profile.get("vram_device_peak_gb"),
                "vram_ollama_peak_gb": profile.get("vram_ollama_peak_gb"),
                "ram_process_peak_gb": profile.get("ram_process_peak_gb"),
                "elapsed_s": round(elapsed, 1),
            }
            print(f"[{m}] TSR: {metrics['tsr']:.1%} (CI: {metrics['tsr_ci'][0]:.1%} - {metrics['tsr_ci'][1]:.1%}) | "
                  f"Latency p50: {metrics['latency_ms']['p50']:.0f} ms | p95: {metrics['latency_ms']['p95']:.0f} ms | "
                  f"Tok/s: {metrics['tokens_per_s_mean']} | Peak VRAM: {profile.get('vram_device_peak_gb')} GB", flush=True)
        except Exception as e:
            print(f"[{m}] Error running benchmark: {e}", flush=True)
            benchmarks[m] = {"model": m, "error": str(e)}

    with open("ollama_3models_benchmark.json", "w") as f:
        json.dump(benchmarks, f, indent=2)
    print("\nSaved all model benchmark results to ollama_3models_benchmark.json", flush=True)

if __name__ == "__main__":
    main()
