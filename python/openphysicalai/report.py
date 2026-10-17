"""Budget Card (markdown) for a finished run."""
from __future__ import annotations

from typing import Dict


def _p(x):
    return "n/a" if x is None else f"{x*100:.1f}%"


def budget_card(r: Dict) -> str:
    m, c, p, b = r["metrics"], r["config"], r["profile"], r["budget"]
    lines = [
        f"# Budget Card {r['id']}", "",
        f"- Created: {r['created']}   Version: {r['version']}",
        f"- Task: {c['task']}   Policy: {r['policy_name']} (track {r['track']}, assistance {r['assist']})",
        f"- Agent: {c['agent']}   Perception: {c['perception']}   Verifier: {c['verifier']}   Perturbation: {c['perturb']}   Mode: {c['mode']}",
        f"- Episodes: {m['episodes']}   Seed start: {c['seed']}   Extra latency: {c['extra_latency_ms']} ms",
        f"- GPU: {p.get('gpu_name') or 'none detected'} ({p.get('gpu_total_gb')} GB)   Measurement confidence: {p['confidence']}",
        "", f"## Budget: {'PASS' if b['pass'] else 'FAIL'} (profile {b['profile']})", "",
        "| Check | Value | Cap | OK | Note |", "|---|---|---|---|---|",
    ]
    for k in b["checks"]:
        lines.append(f"| {k['name']} | {k['value'] if k['value'] is not None else '-'} | {k['cap']} | {'yes' if k['ok'] else 'NO'} | {k['note']} |")
    lines += ["", f"VRAM process source: {p['vram_process_source']}. Device baseline before run: {p.get('vram_device_baseline_gb')} GB.",
              "", "## Capability and reliability", "",
              f"- Task success: {_p(m['tsr'])} (95% CI {_p(m['tsr_ci'][0])} to {_p(m['tsr_ci'][1])}), {m['successes']}/{m['episodes']}",
              f"- Plan latency p50/p95/p99: {m['latency_ms']['p50']:.0f} / {m['latency_ms']['p95']:.0f} / {m['latency_ms']['p99']:.0f} ms",
              f"- Deadline-miss rate: {_p(m['deadline_miss_rate'])}   Mean staleness: {m['staleness_s_mean']:.2f} s",
              f"- Failures injected: {m['failures_injected']}   Detection: {_p(m['detection_rate'])}   Recovery: {_p(m['recovery_rate'])}   Diagnosis accuracy: {_p(m['diagnosis_accuracy'])}",
              f"- Verifier false-alarm rate: {_p(m['false_alarm_rate'])}   Missed-failure rate: {_p(m['missed_failure_rate'])}",
              f"- Failure breakdown: {m['failure_breakdown']}",
              f"- Energy per episode: {('%.1f J' % m['energy_j_per_episode']) if m['energy_j_per_episode'] is not None else 'n/a (no GPU power reading)'}",
              f"- Peak GPU temperature: {p.get('temp_peak_c')}   Throttled: {p.get('throttled_any')}"]
    if c["verifier"] == "V0":
        lines.append("\nV0 is oracle-assisted (simulator ground truth). Do not use as a headline recovery claim.")
    if c["perturb"] != "clean":
        lines.append("\nPerception noise: oracle mode adds position noise; vision mode adds pixel noise. Levels are not equivalent across perception modes.")
    return "\n".join(lines) + "\n"
