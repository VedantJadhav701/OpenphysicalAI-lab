# OpenPhysicalAI Lab — Plan v3

## Budget-Aware, Latency-Coupled, Recovery-Measured Evaluation for Physical AI

**Status:** Research + open-source build plan (v3, supersedes v2)
**Reference hardware:** RTX 3050 Laptop (4 GB VRAM), i5, 16 GB RAM
**Mode:** Local-first, no cloud dependency, no robot hardware needed
**First simulator:** MuJoCo
**Goal:** the most trustworthy, easiest-to-run open Physical AI evaluation lab — useful to researchers, students, hobbyists, and edge-deployment engineers

---

# 0. Changes From v2

v2 review found five P0 gaps. All fixed here.

| P0 | Gap | Fix (section) |
|----|-----|---------------|
| 1 | Budget measurement undefined (display GPU, allocator, other apps, 4 GB != 4 GB usable, 8 GB RAM cap vs 16 GB machine) | Split Hardware Profile vs Budget Profile; process-attributed vs device-wide memory; measurement uncertainty (section 4) |
| 2 | 500 ms p95 vs real 1-4 s planner latency | Per-stage latency budgets; defaults set from Phase 0 measurement, frozen and pre-registered; strict profiles optional (section 5) |
| 3 | Real-time scheduler unspecified | Single-owner scheduler spec, timestamps, stale-action policy, bounded queues, deterministic virtual-clock mode (section 6) |
| 4 | Cross-policy comparisons unfair | Evaluation Contract + Tracks + assistance levels; no cross-track ranking (section 7) |
| 5 | Verifier leaks ground truth | Three roles: Evaluation Oracle / Agent Verifier / Diagnosis; oracle-assisted vs honest results reported separately (section 8) |

Also new in v3: adoption and robustness plan for all users (sections 14-15), governance (section 16), honest-failure rule.

## Keep from v2

Local-first, MuJoCo first, one arm, five tasks, no "first" claims, Oracle vs Vision perception, Open-loop vs Closed-loop vs Recovery agents, Pareto, reproducibility, LIBERO adapter, LeRobot interop, energy + thermal metrics, CIs and paired stats, Budget Card, gated roadmap.

---

# 1. Definition

> **OpenPhysicalAI Lab is a local-first open-source laboratory that measures how much reliable physical capability a Physical AI system delivers under explicit, honestly measured budgets of VRAM, RAM, latency, energy, and failure cost, in a simulator where the world keeps moving while the model thinks.**

Core question:

> **Given a fixed, measured hardware budget, which Physical AI architecture gives the most reliable capability, and how honestly can we tell?**

---

# 2. Five Pillars (feature filter)

1. Budget is a measured contract, not a label.
2. Latency-coupled simulation (world moves during inference).
3. Recovery is measured, with honest verifier levels.
4. Architecture-agnostic harness with fair, track-separated comparison.
5. Runs on a 4 GB laptop; scales up to big GPUs.

If a feature serves none, defer it.

---

# 3. Comparison With Existing Systems

Existing projects are strong at what they target. OpenPhysicalAI Lab is the budget / latency / recovery evaluation layer that can wrap them. **Verify every cell against current repos and papers before public use.**

| System | Main focus | Backend |
|--------|-----------|---------|
| LIBERO | Language-conditioned manipulation, lifelong learning | robosuite / MuJoCo |
| Meta-World | Multi-task / meta-RL | MuJoCo |
| ManiSkill3 | Fast GPU-parallel manipulation | SAPIEN |
| RoboCasa | Large-scale household tasks | robosuite |
| BEHAVIOR-1K | Long-horizon household | OmniGibson / Isaac |
| VLABench | VLA / VLM language-conditioned eval | MuJoCo-based |
| EmbodiedBench | MLLM embodied agents | multiple |
| SIMPLER | Sim eval correlated with real robots | SAPIEN |
| LIBERO-Plus / robustness suites | Perturbation robustness | LIBERO-based |
| Recovery suites (e.g. LIBERO-Recover) | Failure recovery | LIBERO-based |
| LeRobot | Datasets, policies, real robots | multiple |
| Isaac Lab | Large-scale robot learning | Isaac Sim |

| Capability | Typical existing | OpenPhysicalAI Lab |
|------------|------------------|--------------------|
| Task success | Yes (primary) | Yes |
| Resource budget as measured PASS/FAIL contract | Rare / ad hoc | **Yes, core** |
| Process-attributed + device-wide memory, with uncertainty | Rare | **Yes** |
| Per-stage latency, p50/p95/p99, deadline misses | Rare | **Yes** |
| Sim advances during inference | Rare | **Yes** (single-owner scheduler) |
| Energy per episode, throttle flags | Rare | **Yes** |
| Recovery success + cost + false-alarm rate | Partial | **Yes** |
| Oracle-assisted vs honest recovery reported separately | Rare | **Yes** |
| Track-separated fair comparison across policy types | Rare | **Yes** |
| Minimum-budget-for-target-success search | No | **Yes** |
| Quantization vs capability sweep | Separate papers | **Built in** |
| Runs on 4 GB laptop GPU | Often 8-24 GB+ | **By design** |
| Scale of tasks / scenes / robots | **Large (their strength)** | Small at V1 |
| Real-robot validation | Some | Later (V5) |
| Physics / render fidelity | Higher in Isaac / SAPIEN | MuJoCo-level |
| Community, citations | **Established** | New |

Weaknesses (say openly): fewer tasks, no real-robot validation early, simpler rendering, zero community at start. Mitigations: LIBERO adapter, LeRobot interop, strict reproducibility, small but carefully designed suite.

Never claim: first benchmark / first VLA eval / first recovery benchmark / first edge VLA / better than LIBERO or ManiSkill / real-robot performance from sim.

---

# 4. Budget Measurement Specification (fixes P0-1)

## 4.1 Separate three things that v2 mixed

```text
HardwareProfile   what the machine physically has        (capacity, measured)
BudgetProfile     what the experiment is allowed to use  (cap, configured)
Observation       what was actually used                 (measured, with uncertainty)
```

`OPAI-4G` is a **HardwareProfile class** (device with ~4 GB VRAM). Budgets are separate YAML. A 4 GB GPU does NOT mean 4 GB is available to the experiment.

## 4.2 Memory metrics (record all that the platform supports)

| Metric | Meaning | Source |
|--------|---------|--------|
| `vram_device_total` | Physical VRAM | NVML |
| `vram_device_used_baseline` | Used before experiment starts (display, browser, other apps) | NVML at start |
| `vram_device_used_peak` | Device-wide used, peak during run | NVML sampling |
| `vram_process_peak` | VRAM attributed to our process tree | NVML per-process where supported; else framework counters |
| `vram_framework_allocated` / `reserved` | Allocator allocated vs reserved (torch) | `torch.cuda.max_memory_allocated/reserved` |
| `vram_runtime_reported` | llama.cpp / ONNX / TensorRT self-reported buffers | runtime logs |
| `ram_process_peak` | Peak RSS of process tree (incl. sim workers, model server) | psutil |
| `ram_system_used_peak` | System-wide RAM used | psutil |

Platform caveat: per-process VRAM is not reliably exposed on Windows (WDDM); fall back to framework/runtime counters and flag `process_vram_source: estimated`. Linux native is the **reference platform**; Windows and WSL2 supported with documented caveats.

## 4.3 Budget definition and pass rule

```yaml
hardware_profile: OPAI-4G         # capacity class, auto-detected + verified
budget:
  vram_process_peak_gb: 3.2       # cap on our process (leaves headroom for OS/display)
  vram_device_peak_gb: 3.8        # cap on device-wide used incl. baseline
  ram_process_peak_gb: 8.0        # cap on our process tree (machine has 16 GB)
  ram_system_peak_gb: 14.0
```

Pass = process cap AND device cap both satisfied. Report which cap failed.

## 4.4 Uncertainty and limits

- Sampling interval recorded (default 20 Hz). Short spikes can be missed; also record framework peak counters.
- Allocator reserved can exceed allocated; report both, enforce on the larger.
- `opai profile` measures baseline overhead (idle device usage) and stores it in the Hardware Card.
- Display setup recorded (display on dGPU or iGPU). Official results state it.
- Every Budget Card carries a `measurement_confidence` field (`high` / `medium` / `low`) with reason.

---

# 5. Latency Budgets (fixes P0-2)

## 5.1 Per-stage budgets, not one number

```yaml
latency_budget:
  perception_ms_p95: <set from Phase 0>
  planning_ms_p95:   <set from Phase 0>
  action_exec_ms:    <skill / controller duration, not a limit>
  control_loop_hz:   <e.g. 10 or 20>
  end_to_end_ms_p95: <sum policy, planner-mode vs reactive-mode defined separately>
```

Planner agents and reactive policies have different timing structure:

- **Planner mode:** model replans occasionally; low-level skill runs between plans. Budget on plan latency + time-to-first-action.
- **Reactive mode:** model runs every control step or chunk. Budget on per-step / per-chunk latency vs control period.

## 5.2 Profile tiers

```text
Relaxed   realistic for small LLM planners on reference laptop (set from measured Phase 0)
Standard  default profile for official results (set from Phase 0, frozen)
Strict    aspirational (e.g. 500 ms end-to-end); optional; expect FAIL for many planners
```

## 5.3 Honesty rule

- Phase 0 measures latency; profile defaults chosen **before** experiments and frozen with a version tag.
- Profiles are **pre-registered**: hash of profile stored in every run.
- Thresholds are never changed after seeing results to obtain a pass. A new profile version may be added, old results stay under old version.
- Budget FAIL is a valid, reported result.

---

# 6. Real-Time Simulation Scheduler (fixes P0-3)

## 6.1 Principles

1. **One owner mutates simulator state.** Only the scheduler thread/process steps MuJoCo. Inference workers never touch sim objects; they receive immutable observation snapshots and return action messages.
2. Fixed simulation timestep (`dt_sim`, e.g. 2 ms) and fixed control period (`dt_ctrl`, e.g. 50 ms = 20 Hz).
3. Monotonic clock only (`time.monotonic_ns`), never wall-clock date.

## 6.2 Event timeline

```text
t_obs      observation snapshot captured (sim time + monotonic stamp)
t_submit   snapshot handed to inference worker
t_ready    action result returned by worker
t_apply    action applied by scheduler at next control-tick boundary >= t_ready
```

Every action record stores `t_obs, t_submit, t_ready, t_apply, staleness = t_apply - t_obs, sim_steps_elapsed`.

## 6.3 Two timing modes

| Mode | Latency source | Use |
|------|---------------|-----|
| `wallclock` | Real measured inference time; sim paced against monotonic clock | Hardware-realistic results, noisy |
| `virtual` | Latency taken from a recorded **latency trace** (or distribution) and charged in simulated time; inference still executes but sim is not paced by wall time | Deterministic, reproducible, CI-friendly, hardware-independent re-analysis |

Official numbers: run `wallclock` on reference hardware, store latency trace; `virtual` replays that trace so third parties can reproduce physics outcomes exactly without matching hardware.

## 6.4 Stale-action policy (configurable, documented, recorded)

```text
hold          keep previous actuation / hold position
repeat_last   repeat last action
safe_stop     stop motion
drop_if_stale discard action if staleness > max_staleness_ms, keep policy output as "dropped"
```

Default: `hold` with `max_staleness_ms` set per profile. Dropped/late actions counted as `deadline_miss`.

## 6.5 Queues and cancellation

- Inference request queue length **1** (latest-wins). New observation replaces pending request.
- In-flight inference older than `cancel_after_ms` is cancelled or its result discarded; counted as `late_discarded`.
- Backpressure never blocks the scheduler.
- Chunked mode: policy emits action chunk of length K; scheduler consumes chunk while next request is in flight; chunk overlap/blending rule documented.

## 6.6 Determinism rules

- Seeded RNG for scenes, perturbations, and perception noise; separate streams.
- `virtual` mode: no dependence on thread timing; same seed + same latency trace = identical trajectory (CI test).
- `wallclock` mode: reproducibility reported statistically (repeat runs, variance across repeats), never claimed bitwise.
- Latency tax = TSR(sync) - TSR(realtime); paired by seed.

---

# 7. Fair Cross-Policy Evaluation (fixes P0-4)

## 7.1 Evaluation Contract (stored in every run)

```yaml
evaluation_contract:
  observation_access: [rgb, proprio]      # or [state_oracle] etc.
  camera: {views: 1, resolution: 224x224, hz: 10}
  control_hz: 20
  action_space: skill_level | ee_delta | joint_delta
  action_duration: fixed | skill_defined
  controller_assistance: A0 | A1 | A2 | A3
  verifier_level: V0 | V1 | V2        # see section 8
  success_check: evaluation_oracle    # scoring only
  max_steps: N
  episodes: 100
  seeds: shared
```

## 7.2 Controller assistance levels

```text
A0  raw continuous control, no assistance
A1  continuous control + safety clamps (joint limits, collision stop)
A2  parameterized primitives (move_to, grasp, release) with IK
A3  high-level skills (pick, place) with scripted grasp planner
```

Grasp assist (e.g. weld / suction shortcut) is its own flag, always reported.

## 7.3 Tracks (never merged in one ranking)

| Track | Policy type | Typical assistance | Example models |
|-------|-------------|--------------------|----------------|
| P — Planner | LLM / VLM emits structured actions | A2-A3 | Qwen-class SLMs |
| L — Learned | VLA / policy emits continuous actions | A0-A1 | SmolVLA, Octo, ACT, Diffusion Policy |
| H — Hybrid | Planner + learned low-level | A1-A2 | VLM plan + policy exec |

Rules:

- Leaderboards are per track and per assistance level.
- Cross-track comparison only on a **common-denominator task subset** with matched observation access and clearly flagged assistance difference; shown as separate figure, not ranking.
- Matched tasks and seeds across all compared policies.
- Compute cost reported per track-appropriate unit (per plan for P, per chunk / per step for L).
- Statement in docs: shared API enables integration, it does not by itself make comparisons fair.

---

# 8. Verifier, Oracle, and Diagnosis Separation (fixes P0-5)

## 8.1 Three distinct roles

```text
Evaluation Oracle   uses simulator ground truth; scores the episode; NEVER visible to agent
Agent Verifier      uses only information the agent could have (by verifier level)
Recovery Diagnosis  agent's estimate of what went wrong; compared against injected ground truth
```

## 8.2 Verifier information levels

| Level | Agent sees | Meaning |
|-------|-----------|---------|
| V0 | Privileged simulator state (oracle-assisted) | Upper bound; diagnostic only |
| V1 | Proprioception + gripper width/force + contact signals | Realistic for many real robots |
| V2 | Camera only (+ proprio optional) via perception model | Closest to deployable |

## 8.3 Reporting rules

- Every recovery result is tagged with verifier level and perception mode (Oracle / Vision).
- Headline recovery claims use **V1 or V2**. V0 results are labeled "oracle-assisted upper bound".
- Report oracle-assisted and honest recovery side by side to show the gap (itself a finding).
- Metrics: detection rate, **false alarm rate**, **missed failure rate**, diagnosis accuracy (vs injected truth), recovery success, recovery cost.
- Failure injection ground truth is logged for scoring only; never exposed to agent.

---

# 9. Architecture

```text
Task Manager -> Perception (Oracle | Vision | VLM) -> World State (+confidence)
                                                          |
                         Policy (Planner | Learned | Hybrid) per Track
                                                          |
                          Action Validator -> Controller / Action Adapter (assistance level)
                                                          |
                                     Scheduler (single sim owner) -> Backend
                                                          |
                         Agent Verifier (V0/V1/V2) -> Diagnose -> Recover -> Replan
                                                          |
   Evaluation Oracle (scores)   Profiler (VRAM/RAM/latency/energy/thermal)   Logger -> DB -> Budget Card
```

```python
class Policy:
    name: str
    track: Literal["planner", "learned", "hybrid", "scripted"]
    def reset(self, task, seed, contract): ...
    def act(self, obs, world_state=None, deadline_ms=None) -> ActionResult: ...
```

Planner never emits raw motor commands; validator rejects illegal actions (counted as planning failure). Backends implement `Backend` interface (MuJoCo first; LIBERO / ManiSkill / Isaac Lab adapters later).

---

# 10. Benchmark Suite OPAI-Core v1

| # | Task | Tests |
|---|------|-------|
| 1 | Pick & Place ("red cube into blue container") | Integration baseline |
| 2 | Attribute + Spatial Selection ("smallest object", "left of triangle") | Language grounding |
| 3 | Multi-object Sequencing ("all red objects") | State tracking |
| 4 | Articulated / Contact ("open drawer, put cube inside") | Contact, ordering |
| 5 | Dynamic ("pick cube from slow conveyor") | Latency sensitivity |

Failure/perturbation is a **layer** over tasks 1-5, not a task. Failure taxonomy: grasp_fail, object_dropped, wrong_object, wrong_placement, object_displaced, obstacle, perception_noise, action_timeout, collision, controller_fail. Levels: clean / mild / moderate / severe.

Protocol: 100 episodes per task/config (min 50), 10 seed groups, paired seeds, randomized scene + robot start + distractors. Benchmark is versioned (`OPAI-Core v1.0`) separately from code.

External adapters (V1.5): LIBERO subset for comparability; ManiSkill3 / robosuite later.

---

# 11. Metrics

**Capability:** TSR with 95% CI (Wilson / bootstrap), planning success, action success, action efficiency.
**Reliability:** failure rate by type, detection, false alarm, missed failure, diagnosis accuracy, recovery success, recovery cost (extra actions, ms, tokens, J), safe give-up rate.
**Resource:** all memory metrics in section 4, per-stage latency p50/p95/p99, time to first action, token throughput, energy per episode (NVML), GPU clock + temp + throttle flag.
**Real-time:** deadline-miss rate, staleness at apply, late-discard count, **latency tax**.
**Aggregate (never alone):** Capability Efficiency, Deployment Readiness Score, Min-Budget@X.
**Statistics:** paired tests across shared seeds (McNemar / paired bootstrap), effect sizes, pre-registered primary comparisons.

---

# 12. Experiments (gated)

| ID | Experiment | Output |
|----|-----------|--------|
| E1 | Open-loop vs Closed-loop vs Closed-loop+Recovery, clean vs perturbed, at V1 and V2 verifier levels | First research signal + oracle gap |
| E2 | Model scale (0.6B / 1.7B / ~4B Q4) | Pareto frontier |
| E3 | Quantization (FP16 / Q8 / Q4) | Capability lost vs resource saved |
| E4 | Latency tax (sync vs realtime) per model | Latency tax chart |
| E5 | Track comparison (P vs L vs H) on matched subset | Cross-architecture figure (not ranking) |
| E6 | Budget sweep (1 / 2 / 4 / 8 GB) | Min-Budget@80% |
| E7 | Recovery by failure type and verifier level | Detection / recovery table |

E1 is the go/no-go. If recovery gives no gain at V1/V2, fix verifier before E2-E7.

---

# 13. Hardware Feasibility (RTX 3050 4 GB / i5 / 16 GB)

Fits: MuJoCo (CPU), 0.6B-1.7B Q4 planners, ~4B Q4 (tight, planner only), small VLM (256M-500M), SmolVLA-class and Octo-small, ACT / small Diffusion Policy, SQLite, HTML reports.
Does not fit: 7B VLAs, 3B+ LLM + vision + render concurrently, large RL / VLA training, full Isaac Sim.
Risks: thermal throttling (log clocks, warm-up, cool-down), display VRAM use (record display GPU), Windows vs Linux VRAM differences (Linux reference).
All numbers approximate until Phase 0 measures them.

Your first milestone is feasible: oracle perception, 0.6B-1.7B Q4 planner, scripted skills (A3), V1 verifier, CLI + HTML report. Hard parts: reliable sim grasp and a verifier with low false alarms.

---

# 14. Robust For All Users

## 14.1 Install tiers

```text
Tier 0  Browser demo (HF Space / Colab): zero install, CPU, replay a recorded run + try a rule-based agent
Tier 1  pip install openphysicalai   CPU only, MuJoCo, rule-based + tiny model; works on any laptop
Tier 2  pip install "openphysicalai[gpu]"   llama.cpp / torch CUDA; 4 GB class GPUs
Tier 3  Docker image (CUDA)   pinned, reproducible, for clusters and bigger GPUs
```

## 14.2 Platform and hardware matrix

- Linux (reference), Windows, macOS (CPU / Apple Silicon via Metal for llama.cpp), WSL2 documented.
- NVIDIA CUDA first; AMD ROCm and Apple Metal as community-supported tiers via llama.cpp / ONNX Runtime.
- Auto-detect hardware, create HardwareProfile on `opai profile`; refuse to run official mode if profile is inconsistent.
- Headless rendering (EGL / OSMesa) fallback; no display required.

## 14.3 Robustness practices

- Pinned dependency lock files; supported-version table (Python, MuJoCo, CUDA, llama.cpp).
- `opai doctor` diagnoses install problems (drivers, EGL, memory, thermal) with fix hints.
- Crash-safe runs: resumable sweeps, per-episode checkpoint to SQLite, partial results preserved.
- Clear failure categories: infrastructure failure vs agent failure (never mixed in TSR).
- CI: lint, type check, unit, smoke (1 episode), `virtual`-mode determinism test, docs build; matrix over OS and Python versions on CPU runners; GPU tests tagged and run locally.
- Stable plugin API with semantic versioning and deprecation policy.
- Security: no arbitrary code from model output executed; planner output parsed as JSON only, validated against schema.

---

# 15. Growth and Adoption Plan (earning stars honestly)

Stars follow usefulness, clarity, and visibility. No guarantee; these levers matter most.

## 15.1 First 60 seconds

- README top: one-sentence pitch, 10-second GIF of robot recovering from a failed grasp, one-command quickstart, results chart ("how much physical AI fits in 4 GB").
- `pip install openphysicalai && opai demo` works with no GPU and no downloads over 100 MB.
- Badges: CI, PyPI, license, docs, Colab, HF Space.

## 15.2 Assets that make people share it

- **Leaderboard site** (static, GitHub Pages): per-track tables, Pareto plots, Min-Budget@80% chart. Community submits `results.json` + Budget Card via PR; CI validates schema and contract.
- **The "Latency Tax" figure** and **"oracle vs honest recovery gap" figure**: clean, quotable, own-brand findings.
- **Hardware Wall**: "runs on X laptop" entries from contributors (RTX 3050, 4060, M-series, Jetson). Strong community hook.
- Technical blog posts and a short demo video; arXiv preprint; post to r/robotics, r/LocalLLaMA, Hugging Face, X/LinkedIn, Hacker News (Show HN), Papers with Code.
- LeRobot and Hugging Face ecosystem visibility (model cards linking to OPAI results).
- Outreach to maintainers of LIBERO, ManiSkill, LeRobot: position as complementary eval layer.

## 15.3 Contributor flywheel

- 50-line plugin examples: add a model, add a task, add a failure type, add a backend.
- `good first issue` list prepared before launch (at least 20).
- Fast review SLA, `CONTRIBUTING.md`, code of conduct, issue and PR templates, public roadmap board.
- Credit: contributors listed on results and leaderboard.

## 15.4 Credibility

- Every claim backed by a reproducible config; all raw episodes released.
- Limitations section in README (weaknesses from section 3 stated plainly).
- No "first" claims; cite and integrate prior work generously.

---

# 16. Governance and Sustainability

- License: Apache-2.0 (patent grant, widely accepted). Decide before first commit.
- Benchmark versioning and result compatibility policy (`OPAI-Core v1.x` comparable).
- Citation file (`CITATION.cff`), DOI via Zenodo on each release.
- Roadmap issues public; RFC process for interface changes.
- Maintainer plan: set realistic cadence given other commitments; recruit 1-2 co-maintainers early.

---

# 17. Repository Layout

```text
openphysicalai/
  core/        interfaces: Policy, Perception, Backend, Verifier, Budget, Contract
  scheduler/   single-owner sim scheduler, clocks, queues, stale policy, latency traces
  backends/    mujoco/  (later) libero/ maniskill/ isaaclab/
  robots/      arm + controllers (A0-A3)
  tasks/       opai_core/ definitions + evaluation oracle
  perception/  oracle.py vision.py
  policies/    planners/ learned/ hybrid/ scripted/
  recovery/    agent verifiers V0-V2, diagnosis, strategies
  injection/   failure + perturbation generators (ground-truth log)
  profiler/    vram (device+process), ram, latency per stage, energy, thermal, uncertainty
  bench/       runner, seeds, stats, pareto, min_budget, leaderboard export
  store/       sqlite, run records, config + profile hash
  report/      budget_card, hardware_card, html report, plots
  cli/         opai profile | doctor | demo | run | sweep | report | compare | reproduce
  configs/     hardware/ budgets/ latency/ contracts/ tasks/ models/
  docs/  examples/  tests/  site/ (leaderboard)
```

---

# 18. Roadmap (8 weeks part-time, gated)

| Phase | Time | Deliverable | Gate |
|-------|------|-------------|------|
| 0 | 3-4 d | Interfaces frozen; `opai profile` measures VRAM baseline, tokens/s (0.6B / 1.7B Q4), render cost, thermals, per-stage latency; **latency profiles chosen and frozen** | Measured numbers fit budget plan |
| 1 | 1 wk | MuJoCo arm, scene, camera, deterministic controller | Scripted pick-place >= 95% over 200 episodes |
| 2 | 1 wk | Env API, world state, oracle perception, validator, skills (A3), evaluation oracle | Rule-based planner solves tasks 1-3 |
| 3 | 1 wk | Scheduler (sync + virtual + wallclock), llama.cpp planner with grammar-constrained JSON, V1 verifier, failure injection, recovery, report | **First Milestone** end to end |
| 4 | 1 wk | Profiler with uncertainty, SQLite, Budget Card, CIs; run E1 (V0 vs V1) | E1 shows signal with CIs |
| 5 | 1 wk | Vision perception, V2 verifier, dynamic task; E2, E3, E4 | Latency tax measurable |
| 6 | 1-2 wk | Learned-track baselines (SmolVLA / Octo), LeRobot interop, LIBERO subset adapter; E5, E6, E7 | Tracks reported separately |
| 7 | 1 wk | Docs, tiers 0-3 install, CI matrix, demo site, leaderboard, preprint, v0.1 tag, launch | Quickstart < 15 min on fresh machine |

Later: V2 more backends, V3 more models + community leaderboard, V4 Phys-SLM (synthetic sim demos -> SFT/LoRA, benchmarked on OPAI-Core), V5 real-robot adapters (ROS2, low-cost arms via LeRobot), V6 edge devices (Jetson, Raspberry Pi, phone).

---

# 19. Risks

| Risk | Mitigation |
|------|-----------|
| Sim grasp unreliable | Gate 1; documented grasp-assist flag |
| Verifier false alarms | Track false alarm + missed failure; V1/V2 levels |
| Strict latency profile fails all planners | Tiers; report FAIL honestly; never retune post hoc |
| Per-process VRAM unavailable on Windows | Fallback counters, `estimated` flag, Linux reference |
| Wall-clock noise | `virtual` mode for reproducibility, repeats for wallclock |
| Unfair cross-track claims | Tracks, assistance levels, no merged ranking |
| Scope creep | Gates; no dashboard before Gate 4; no training before Gate 5 |
| Low adoption | Section 15 plan; demo, leaderboard, integrations |
| Maintainer time | 8-week plan, co-maintainers, cut Phase 6 breadth first |

---

# 20. Success Criteria

**Engineering:** milestone runs end to end; profiler honest about uncertainty; CI green on OS matrix; install < 15 min.
**Research:** E1 signal with CIs at honest verifier levels; latency tax measured; Pareto meaningful; third party reproduces results.
**Community:** external contributors add models/tasks; leaderboard has submissions beyond the authors; integrations with LeRobot / LIBERO ecosystem.
**Practical:** a 4 GB GPU laptop user runs useful Physical AI experiments with no robot.

---

# 21. Immediate Next Actions

1. Run Phase 0 on your 3050: baseline VRAM with display on, tokens/s for 0.6B and 1.7B Q4, render VRAM, 10-minute thermal run, per-stage latencies.
2. Freeze interfaces: `Policy`, `Perception`, `Backend`, `Budget`, `EvaluationContract`, `Scheduler`.
3. Choose and freeze latency profiles from Phase 0 numbers; commit the hash.
4. Repo skeleton on day one: CI, determinism test in `virtual` mode, license, CONTRIBUTING.
5. Build Phase 1 only until Gate 1 passes.
6. Verify the comparison table (section 3) against current repos before any public claim.

---

# 22. Final Definition

> **OpenPhysicalAI Lab: a local-first open-source laboratory for honestly evaluating reliable Physical AI under measured compute, memory, latency, and energy budgets, where the world keeps moving while the model thinks.**

```text
Evaluation   = Capability + Efficiency + Reliability + Recovery (honest verifier level) + Real-time behavior
Constraint   = Measured VRAM + RAM + per-stage Latency + Energy + Failure budget
Fairness     = Evaluation contract + tracks + assistance levels + paired seeds
Reference    = RTX 3050 Laptop 4 GB, 16 GB RAM, Linux reference platform
First sim    = MuJoCo
```
