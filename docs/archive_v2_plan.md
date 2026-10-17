# OpenPhysicalAI Lab — Plan v2

## Budget-Aware, Latency-Coupled, Recovery-Measured Evaluation for Physical AI

**Status:** Research + open-source build plan (v2, supersedes v1)
**Reference hardware:** RTX 3050 Laptop GPU (4 GB VRAM), i5, 16 GB RAM — profile `OPAI-4G`
**Mode:** Local-first, no cloud dependency, no robot hardware needed
**First simulator:** MuJoCo (CPU physics, offscreen render)
**Later backends:** LIBERO/robosuite adapter, ManiSkill3 adapter, Isaac Lab, ROS2, real robots

---

# 0. What Changed From v1

## 0.1 Keep (v1 was right)

- Local-first, MuJoCo first, one arm, one scene, five tasks.
- Do not claim "first" anything. Position as evaluation layer, integrate ecosystems.
- Oracle vs Vision perception split (separates reasoning failure from perception failure).
- Open-loop vs Closed-loop vs Closed-loop+Recovery as three baseline agents.
- Resource budget as a hard PASS/FAIL contract.
- Pareto frontier, Deployment Readiness Score, reproducibility standard.

## 0.2 Add (v1 gaps)

1. **Latency-coupled simulation ("real-time mode").** v1 measured latency but sim paused while model thought. Real robots do not get that. In real-time mode the world keeps moving during inference. This is the biggest differentiator. See section 4.
2. **Policy-type-agnostic interface.** v1 was LLM-planner-centric (text plan -> scripted controller). Credible Physical AI lab must also evaluate VLA / learned policies (SmolVLA, Octo, ACT, Diffusion Policy). Add `Policy` interface with three agent classes. See section 5.
3. **Comparable-results adapter early.** Add a LIBERO subset adapter (V1.5) so numbers can be checked against published results. Without it, nobody trusts a new benchmark.
4. **LeRobot integration.** De-facto open-source standard for datasets, SmolVLA, policies. Interop = contributors and reach.
5. **Energy and thermal metrics.** Laptop GPU throttles. Report joules/episode (NVML power), clocks, temperature. Unmeasured throttling silently corrupts latency results.
6. **Latency distribution, not mean.** p50/p95/p99, deadline-miss rate, control-rate satisfaction.
7. **Minimum-budget search.** Automate "smallest VRAM/RAM/latency budget that reaches X% success". Headline feature, not a side experiment.
8. **Statistics baked in.** Wilson / bootstrap confidence intervals, paired seeds, effect sizes. Reported by default.
9. **Budget Card.** One-page auto-generated artifact per run (like a model card) with budget, hardware fingerprint, results, config hash.
10. **Honest timeline.** 30-day plan in v1 is optimistic. v2 uses 8 weeks with go/no-go gates. See section 10.

## 0.3 Replace / Cut

- Replace "Phys-SLM training" as early goal -> keep as V4. Benchmark first. (v1 said same; v2 enforces with gate.)
- Cut dashboard from V1 core. CLI + HTML report first. Dashboard after Gate 4.
- Cut 3B model + vision model running together on 4 GB. Does not fit. Run sequentially or use oracle perception for 3B+ runs. See section 6.
- Cut 71-section sprawl. This doc is the single source; v1 stays as archive.
- Replace 5 near-identical tabletop tasks with 5 tasks covering distinct skills (section 7).

---

# 1. Project Definition

> **OpenPhysicalAI Lab is a local-first open-source laboratory that measures how much reliable physical capability a Physical AI system delivers under an explicit budget of VRAM, RAM, latency, energy, and failure cost — in a simulator where the world keeps moving while the model thinks.**

Users can:

1. Pick task, scene, robot, perception mode.
2. Plug in any model: LLM planner, VLM, VLA, learned policy, rule-based.
3. Set a budget (`OPAI-4G` or custom YAML).
4. Run closed-loop episodes, clean and perturbed.
5. Inject failures, measure detection and recovery.
6. Get PASS/FAIL against budget, Pareto plots, and a Budget Card.
7. Reproduce any run from a config hash.

Core question:

> **Given fixed compute and memory, which Physical AI architecture gives the most reliable capability?**

---

# 2. Differentiators (the five pillars)

| # | Pillar | One-line meaning |
|---|--------|------------------|
| 1 | Budget as first-class contract | Every run has PASS/FAIL against VRAM/RAM/latency/energy |
| 2 | Latency-coupled sim | World advances during inference; slow model = worse physics outcome |
| 3 | Recovery as measured quantity | Detection, diagnosis, recovery success, recovery cost |
| 4 | Architecture-agnostic | Planner+skills, VLA, hybrid all run through same harness |
| 5 | Runs on 4 GB | Anyone with a cheap laptop GPU can reproduce results |

If a feature does not serve one of these five, defer it.

---

# 3. Comparison: Existing Systems vs OpenPhysicalAI Lab

**Read this honestly.** Existing projects are strong at what they target. OpenPhysicalAI Lab does not replace them; it is the budget/latency/recovery evaluation layer that can wrap them. Entries below are best-knowledge summaries; **verify each cell against the current repo/paper before publishing** (several of these projects update fast, and I could not fully re-verify as of Oct 2026).

## 3.1 What each existing system is mainly for

| System | Main focus | Sim backend | Typical model type |
|--------|-----------|-------------|--------------------|
| LIBERO | Lifelong / language-conditioned manipulation tasks | robosuite (MuJoCo) | Imitation policies, VLAs |
| Meta-World | Multi-task / meta-RL manipulation | MuJoCo | RL policies |
| ManiSkill3 | Fast GPU-parallel manipulation sim + tasks | SAPIEN (GPU) | RL, IL, VLAs |
| RoboCasa | Large-scale household kitchen tasks | robosuite (MuJoCo) | IL, VLAs |
| BEHAVIOR-1K | Long-horizon household activities | OmniGibson / Isaac | Embodied agents |
| VLABench | Language-conditioned VLA evaluation | MuJoCo-based | VLAs / VLMs |
| EmbodiedBench | MLLM-driven embodied agents | Multiple | MLLM agents |
| SIMPLER | Sim evaluation correlated with real-robot results | SAPIEN / ManiSkill | VLAs (RT, Octo) |
| LIBERO-Plus and similar robustness suites | Perturbation robustness of VLAs | LIBERO-based | VLAs |
| Recovery-focused benchmarks (e.g. LIBERO-Recover) | Failure recovery | LIBERO-based | VLAs |
| LeRobot | Datasets, policies, training, real-robot tooling | Multiple | ACT, Diffusion, SmolVLA, etc. |
| Isaac Lab | Large-scale GPU robot learning | Isaac Sim | RL, IL |
| Efficient/edge-VLA papers | Smaller, faster VLAs | Various | VLAs |

## 3.2 Capability matrix (OpenPhysicalAI Lab vs typical existing)

"Typical existing" = most systems above; individual exceptions exist.

| Capability | Typical existing | OpenPhysicalAI Lab |
|------------|------------------|--------------------|
| Task success measurement | Yes (primary) | Yes |
| Resource budget as PASS/FAIL contract | No (VRAM/latency reported ad hoc, if at all) | **Yes, core** |
| Peak VRAM / RAM per full pipeline | Rare | **Yes, standard** |
| Latency distribution (p95/p99) + deadline misses | Rare | **Yes** |
| Sim advances during inference (latency-coupled) | Rare (usually paused) | **Yes (real-time mode)** |
| Energy per episode | Rare | **Yes (NVML)** |
| Failure injection | Partial (robustness suites) | Yes, taxonomy-based |
| Recovery success + recovery cost | Partial (few dedicated suites) | **Yes, core** |
| Minimum-budget-for-target-success search | No | **Yes, headline** |
| Quantization vs capability sweep | Mostly separate papers | **Yes, built-in** |
| LLM planner, VLM, VLA, policy in one harness | Mostly one family each | **Yes** |
| Runs fully on 4 GB GPU laptop | Often needs 8-24 GB+ or cluster | **Yes by design** |
| Auto-generated reproducible report | Rare | **Yes (Budget Card)** |
| Scale of tasks / scenes / robots | **Large (their strength)** | Small at V1 (our weakness) |
| Real-robot validation | Some (SIMPLER, LeRobot) | Not until V5 |
| Physics fidelity / photorealism | Higher in Isaac/SAPIEN | MuJoCo-level |
| Community / citations / maturity | **Established** | New |

## 3.3 Where we are weaker (say this openly)

- Fewer tasks and scenes than LIBERO / RoboCasa / BEHAVIOR.
- No real-robot validation until late.
- MuJoCo CPU rendering is simpler than Isaac/SAPIEN.
- Zero community at start.

Mitigation: LIBERO adapter (comparable numbers), LeRobot interop (reach), small but carefully designed task set, strong reproducibility.

## 3.4 Positioning statement (safe to use)

> OpenPhysicalAI Lab provides a local-first experimental framework for jointly evaluating Physical AI capability, resource consumption, real-time latency effects, and recovery behavior under explicit deployment budgets.

## 3.5 Claims to never make

- "First Physical AI benchmark / VLA eval / recovery benchmark / edge VLA / resource-efficient VLA."
- "Better than LIBERO / ManiSkill." Different goal.
- Any claim about real-robot performance from sim results alone.

---

# 4. Latency-Coupled Simulation (key new feature)

## 4.1 Problem

Standard eval: observe -> model thinks (sim frozen) -> act. A 2 s model and a 50 ms model look equal on physics. On a real robot the 2 s model acts on stale state.

## 4.2 Modes

```text
Mode S (Synchronous)    sim paused during inference        # comparable with literature
Mode R (Real-time)      sim advances during inference      # OpenPhysicalAI default for budget runs
Mode R+C (Chunked)      model emits action chunk; executes while next chunk computes
```

## 4.3 Implementation sketch

- Sim runs at fixed `control_hz` (e.g. 20 Hz) on a clock.
- Inference runs in separate thread/process; result applied when ready.
- If inference misses deadline: robot repeats last action / holds (configurable) and `deadline_miss` increments.
- Latency measured wall-clock including preprocessing + postprocessing.
- Disturbance objects (rolling, moving target) make staleness matter. Include at least one dynamic task.

## 4.4 New metrics from this

- Deadline-miss rate
- Staleness at action time (ms between observation and applied action)
- Success delta Mode S vs Mode R (the "latency tax")

The latency tax per model is a strong, publishable, easy-to-understand result.

---

# 5. Architecture

```text
                         Task / Instruction
                                |
                         +------+------+
                         | Task Manager|
                         +------+------+
                                |
              +-----------------+------------------+
              |                                    |
        Perception                              Policy (any type)
   (Oracle | Vision | VLM)            +-------------+-------------+
              |                       |             |             |
         World State            Planner+Skills      VLA /      Hybrid
              |                 (LLM -> actions)  Policy     (VLM plan +
              +--------------->  structured       (obs->      policy exec)
                                  action          action
                                     |            chunk)
                                     v              |
                               Action Validator     |
                                     |              |
                                     v              v
                                    Controller / Action Adapter
                                              |
                                              v
                                    Environment (Backend)
                                              |
                                          Observation
                                              |
                                           Verifier
                                      +-------+-------+
                                   SUCCESS         FAILURE
                                      |               |
                                    DONE     Diagnose -> Recover -> Replan
                                              |
                         Profiler (VRAM/RAM/latency/energy/thermal) runs alongside
                                              |
                                  Logger -> DB -> Budget Card / Report
```

## 5.1 Policy interface (new)

```python
class Policy:
    name: str
    kind: Literal["planner", "vla", "hybrid", "scripted"]

    def reset(self, task, seed): ...
    def act(self, obs, world_state=None, deadline_ms=None) -> ActionResult: ...
    # ActionResult: structured_action OR action_chunk, plus inference metadata
```

Planner policies output structured actions (`{"action":"pick","object":"red_cube"}`) -> validator -> skill controller.
VLA/learned policies output continuous action chunks -> action adapter (joint/EE deltas) -> sim.

Both go through the same profiler, verifier, failure injector, and metrics. That is what makes comparison fair.

## 5.2 Structured actions + validator (keep from v1)

Planner never emits raw motor commands. Validator checks: object exists, reachable, gripper state legal, within workspace. Invalid action = counted `planning` failure, not silently fixed.

## 5.3 World state (keep from v1)

Common JSON schema (robot, objects, containers, relations). Two sources: Oracle (sim ground truth) and Vision (camera -> model -> state). Add `confidence` per object for Vision mode.

---

# 6. Hardware Feasibility on RTX 3050 4 GB / i5 / 16 GB

Numbers are approximate; **measure on your machine in Phase 0**.

## 6.1 What runs well

| Workload | Where | Notes |
|----------|-------|-------|
| MuJoCo physics | CPU | Fast, light |
| Offscreen camera render | GPU (EGL) or CPU | Roughly 0.2-0.4 GB VRAM on GPU; CPU fallback slower |
| 0.6B-1.7B LLM, Q4 | GPU via llama.cpp | ~0.4-1.2 GB weights + KV cache |
| ~4B LLM, Q4 | GPU, tight | ~2.5 GB + KV; leaves little room |
| Small VLM (256M-500M) | GPU | ~0.5-1.2 GB |
| SmolVLA-class (~450M) | GPU fp16 | ~1 GB; good VLA baseline |
| Octo-small/base | GPU | Tiny; cheap baseline |
| ACT / Diffusion Policy (small) | GPU/CPU | Needs demos for training; train short on 3050 feasible for simple tasks |
| SQLite, FastAPI, HTML reports | CPU | Trivial |

## 6.2 What does NOT fit (do not plan around it)

- OpenVLA 7B, pi0-class 3B+ VLAs at useful precision.
- 3B+ LLM **plus** vision model **plus** sim render at once inside 4 GB.
- Large RL or large VLA training.
- Full Isaac Sim.

Handle these with: oracle perception for big planners, sequential model loading, or "does not fit budget" recorded as a valid result (FAIL is data).

## 6.3 Laptop-specific risks

- **Thermal throttling** changes latency run to run. Log GPU clocks/temp; warm up before timing; run fixed power plan; repeat runs.
- **Display uses VRAM** if the 3050 drives the screen. Hybrid graphics (iGPU on display) frees ~0.3-0.5 GB. Record which setup was used in the Budget Card.
- **Windows vs Linux/WSL2** VRAM overhead differs. Pick one for official results and say so.
- **16 GB RAM** is enough, but sim + model + Python + browser add up; log peak RSS.

## 6.4 Verdict on your milestone

First milestone (pick & place, small local model, 4 GB budget, inject failure, detect, recover, report) is **feasible** on this hardware with:

- Oracle perception first, Vision second.
- Planner policy 0.6B-1.7B Q4 (not 3B).
- Scripted skill controller (no learned low-level policy yet).
- Report as CLI + HTML.

Hardest part is not the GPU. It is reliable grasping in sim and a failure verifier that does not give false alarms. Budget your time there.

---

# 7. Benchmark Suite: OPAI-Core (5 tasks, distinct skills)

Revised so tasks cover different capabilities, not just pick-and-place variants.

| # | Task | Instruction example | Tests |
|---|------|--------------------|-------|
| 1 | Pick & Place | "Put the red cube in the blue container." | Grounding, grasp, place (integration test) |
| 2 | Attribute + Spatial Selection | "Move the object left of the triangle into the container." / "Pick the smallest object." | Spatial language, comparison |
| 3 | Multi-object Sequencing | "Put all red objects in the blue container." | State tracking, repeated manipulation |
| 4 | Articulated / Contact Task | "Open the drawer and put the cube inside." | Non-trivial contact, ordering |
| 5 | Dynamic Task (new) | "Pick the cube from the slow conveyor." | Latency sensitivity; makes real-time mode matter |

Failure Recovery is **not a task**; it is a **perturbation layer** applied to tasks 1-5 (see section 8). This gives more data than v1's single recovery task.

## 7.1 Episode protocol

- 100 episodes/task/config (minimum 50), 10 seed groups.
- Randomize object positions, initial robot state, distractors.
- Same seeds across compared models (paired design).
- Never report single-run success.

## 7.2 V1.5 external adapters (comparability)

- LIBERO subset (e.g. spatial/object suites): run through `Policy` interface; compare to published numbers where hardware allows.
- ManiSkill3 / robosuite tasks via backend adapter (CPU or GPU as fits).

---

# 8. Failure Injection and Recovery

## 8.1 Failure taxonomy

```text
grasp_fail            gripper closes, object not held
object_dropped        lost mid-transport
wrong_object          grounded to wrong target
wrong_placement       placed outside target
object_displaced      moved by external force
obstacle              new object in path
perception_noise      blur, occlusion, color shift, jitter (Vision mode)
action_timeout        deadline miss in real-time mode
collision             unexpected contact
controller_fail       IK / planner failure
```

## 8.2 Perturbation levels

`clean` / `mild` / `moderate` / `severe`, seeded and reproducible.

## 8.3 Recovery pipeline

```text
Verify -> Detect -> Diagnose (type) -> Select recovery -> Replan -> Execute -> Re-verify
```

Max retries configurable. Count every extra action, ms, and token.

## 8.4 Recovery metrics

- Detection rate, **false alarm rate** (important: v1 omitted it)
- Diagnosis accuracy (vs injected ground-truth failure)
- Recovery success rate
- Recovery cost (extra actions, latency, tokens, joules)
- Unrecoverable-failure handling (does agent give up safely?)

---

# 9. Metrics

## 9.1 Capability

- Task Success Rate (TSR) with 95% CI
- Planning Success Rate
- Action Success Rate
- Action Efficiency (actual vs minimum actions)

## 9.2 Reliability / Recovery

- Failure rate by type
- Recovery Success Rate, Detection Rate, False Alarm Rate, Diagnosis Accuracy
- Recovery Cost

## 9.3 Resource (per full pipeline, not model-only)

- Peak VRAM (weights + KV + vision + render + runtime)
- Peak RAM (process RSS)
- End-to-end latency: p50 / p95 / p99
- Time to first action
- Token throughput
- **Energy per episode (J)** via NVML
- GPU clocks / temp (throttle flag)

## 9.4 Real-time

- Deadline-miss rate
- Staleness at action (ms)
- **Latency tax** = TSR(Mode S) - TSR(Mode R)

## 9.5 Aggregate (always alongside raw metrics, never alone)

```text
Capability Efficiency = TSR / normalized resource cost
Deployment Readiness Score = weighted(TSR, RSR, budget compliance, p95 latency, energy)
Min-Budget@X = smallest budget achieving TSR >= X% (e.g. 80%)
```

## 9.6 Statistics

- Wilson / bootstrap CIs on all rates.
- Paired comparison across shared seeds (McNemar or paired bootstrap).
- Report effect size, not only p-value.
- Pre-register primary comparisons before running full sweeps.

---

# 10. Resource Budget Contract

```yaml
profile: OPAI-4G
resource_budget:
  max_vram_gb: 4.0
  max_ram_gb: 8.0
  max_latency_ms_p95: 500
  min_sim_fps: 20
  max_energy_j_per_episode: null   # optional
mode: realtime                      # sync | realtime | chunked
```

Output:

```text
PASS
or
FAIL
  VRAM: 4.37 GB > 4.00 GB   (peak during: vision+planner load)
  Latency p95: 612 ms > 500 ms
```

Named profiles: `OPAI-2G`, `OPAI-4G` (reference), `OPAI-8G`, `OPAI-16G`. Enforce VRAM via real measurement (and optionally `torch.cuda.set_per_process_memory_fraction` / model-load limits), not just reporting.

---

# 11. Experiments

## 11.1 Core matrix (keep it small)

Do not run a full cross-product. Run these in order, each gated on the last.

| ID | Experiment | Compare | Output |
|----|-----------|---------|--------|
| E1 | Loop structure | Open-loop vs Closed-loop vs Closed-loop+Recovery, clean vs perturbed, 100 eps | First research signal |
| E2 | Model scale | 0.6B / 1.7B / ~4B Q4 planners, same seeds | Pareto frontier |
| E3 | Quantization | FP16 / Q8 / Q4 (+Q5/Q6 if time) | Capability lost vs resource saved |
| E4 | Latency tax | Mode S vs Mode R, per model | Latency tax chart |
| E5 | Architecture | Planner+skills vs SmolVLA vs Octo vs hybrid | Cross-family comparison |
| E6 | Budget sweep | 1 / 2 / 4 / 8 GB | Min-Budget@80% |
| E7 | Failure recovery by type | Per failure type | Detection / recovery table |

E1 is the go/no-go for the whole research story. If closed-loop+recovery does not beat open-loop under perturbation, debug the verifier before spending on E2-E7.

## 11.2 Expected compute

Sim is cheap. Bottleneck is LLM inference (~1-4 s/plan for small Q4 on 3050). 100 episodes x ~3 plans x 3 s is minutes to ~1 hour per config. Full matrix is days, not weeks; schedule overnight batch runs, with thermal cool-down between configs.

---

# 12. Repository Layout

```text
openphysicalai/
  core/            interfaces: Policy, Perception, Backend, Verifier, Budget
  backends/        mujoco/  (later) libero/  maniskill/  isaaclab/
  robots/          arm model + controller
  tasks/           opai_core/ task defs + success checks
  perception/      oracle.py  vision.py
  policies/        planners/  vla/  scripted/
  recovery/        verifier, diagnosis, strategies
  injection/       failure + perturbation generators
  profiler/        vram, ram, latency, energy, thermal
  bench/           runner, seeds, stats, pareto, min_budget
  store/           sqlite schema, run records, config hash
  report/          budget_card, html report, plots
  cli/             opai run | sweep | report | profile | compare
  configs/         budgets/  tasks/  models/
  tests/           unit + smoke + determinism
  docs/
  examples/
```

CLI:

```text
opai profile                         # measure your machine, create hardware fingerprint
opai run  --task pick_place --policy qwen3-1.7b-q4 --budget OPAI-4G --mode realtime
opai sweep --config sweeps/e1_loop.yaml
opai report --run <id>               # Budget Card + HTML
opai compare <runA> <runB>           # paired stats
```

---

# 13. Roadmap With Gates (8 weeks, part-time realistic)

v1 had 30 days. With internship, studies, and startup work, 8 weeks is safer. Each gate must pass before moving on.

## Phase 0 — Spec + hardware profile (3-4 days)

- Freeze interfaces (section 5.1), budget YAML, task defs.
- Run `opai profile` equivalent: record VRAM headroom, tokens/s for 0.6B/1.7B Q4, render cost, thermals.
- **Gate 0:** measured numbers confirm 1.7B Q4 + render fits well under 4 GB.

## Phase 1 — MuJoCo prototype (1 week)

- Arm, table, cube, container, camera, deterministic IK controller.
- **Gate 1:** scripted pick-and-place succeeds >= 95% over 200 randomized episodes. If not, stop and fix; everything depends on this.

## Phase 2 — Environment + World State + Oracle (1 week)

- Env API (reset / observe / execute / success), config system, tests.
- Structured actions + validator + skill controller.
- **Gate 2:** rule-based planner solves tasks 1-3 with Oracle perception.

## Phase 3 — Small model planner + closed loop (1 week)

- llama.cpp runtime, `Policy` planner, JSON-constrained output (grammar-constrained decoding).
- Verifier, failure injector (grasp_fail, displaced), recovery loop.
- **Gate 3 = First Milestone:** user picks task + model + 4 GB budget -> run -> failure injected -> detected -> recovered -> report. (Your milestone.)

## Phase 4 — Profiler + stats + reports (1 week)

- VRAM/RAM/latency/energy/thermal profiler, SQLite store, Budget Card, CIs.
- Run **E1**.
- **Gate 4:** E1 shows measurable signal with CIs. Decide: continue / fix verifier.

## Phase 5 — Vision + real-time mode (1 week)

- Vision perception (small VLM or detector), Mode S/R/chunked, dynamic task.
- Run **E4**, **E3**, **E2**.

## Phase 6 — VLA baselines + adapters (1-2 weeks)

- SmolVLA / Octo through `Policy`, action adapter, LeRobot interop, LIBERO subset adapter.
- Run **E5**, **E6**, **E7**.

## Phase 7 — Release (1 week)

- Docs, quickstart (< 15 min to first run), CI, Docker/conda, pinned versions, v0.1 tag, preprint.
- Dashboard only now, and only if time allows.

## Later

```text
V2  more backends (ManiSkill3, Isaac Lab)
V3  more VLA/SLM models, community leaderboard (JSON result submission)
V4  Phys-SLM (0.3B-1.7B, synthetic sim demos -> SFT/LoRA), benchmarked on OPAI-Core
V5  real robot adapters (ROS2, SO-100-class low-cost arm via LeRobot)
V6  edge hardware: Jetson, Raspberry Pi, phone, Qualcomm/AMD edge
```

---

# 14. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Sim grasping unreliable | High | Gate 1; use weld/suction-style grasp assist as documented fallback; report which grasp model used |
| Verifier false alarms ruin recovery results | High | Track false alarm rate; verifier uses sim ground truth first, vision-based verifier later |
| LLM emits invalid JSON | Medium | Grammar-constrained decoding; invalid output counted as failure |
| 4 GB too tight with vision + planner | Medium | Sequential loading, oracle mode, report FAIL as data |
| Thermal throttling noise | Medium | Warm-up, cool-down, repeat runs, log clocks |
| Scope creep (dashboard, Phys-SLM) | High | Gates; no dashboard before Gate 4, no training before Gate 5 |
| Nobody trusts new benchmark | Medium | LIBERO adapter, open configs, seeds, CIs |
| Result is "closed-loop helps" (obvious) | Medium | Value is in quantified budget/latency tax/min-budget, not in the obvious direction |
| Time (internship + startup + studies) | High | 8-week plan, weekly gate review, cut Phase 6 breadth first |

---

# 15. Reproducibility Standard

Every run stores:

```text
git commit, package versions, config hash
seeds, task/scene version
model name, quantization, runtime + version
hardware fingerprint (GPU, driver, CUDA, OS, RAM, power plan, display GPU)
budget profile, mode (sync / realtime / chunked)
all raw per-episode records
```

`opai reproduce <run_id>` re-runs from the record. Determinism test in CI (same seed -> same trajectory on CPU physics).

---

# 16. Open-Source Strategy

- License: Apache-2.0 (or MIT). Choose early.
- Quickstart under 15 minutes on a 4 GB laptop.
- Plugin points: add model, add task, add backend, add failure type. Each documented with a 50-line example.
- Good-first-issue labels, `CONTRIBUTING.md`, code of conduct.
- Results repo: community submits `results.json` + Budget Card; static leaderboard page generated from them (no server needed).
- Tests: unit, smoke (1 episode), determinism. CI on CPU-only runners for non-GPU parts; GPU tests run locally and are tagged.
- Semantic versioning; benchmark versioned separately (`OPAI-Core v1.0`) so results stay comparable.

---

# 17. Paper Direction

Working title options:

1. *OpenPhysicalAI Lab: Budget-Aware, Latency-Coupled Evaluation of Closed-Loop Physical AI* (safest)
2. *How Much Physical Intelligence Fits in 4 GB?* (memorable, use only if E2/E6 support it)
3. *The Latency Tax: Real-Time Effects on Small Physical AI Agents* (if E4 is the strongest finding)

Story:

```text
Benchmarks report success, deployment cares about budget and timing
 -> we build OpenPhysicalAI Lab
 -> measure capability + resources + real-time effects + recovery
 -> E1 loop structure, E2 scale, E3 quantization, E4 latency tax, E5 architectures, E6 min-budget
 -> identify deployment-efficient configurations on a 4 GB laptop
```

Venue options once results exist: workshop at CoRL / ICRA / NeurIPS (datasets & benchmarks, embodied/efficient ML tracks), or arXiv + open repo first.

---

# 18. Success Criteria

**Engineering:** `pip install` works, milestone runs end to end, profiler accurate, CI green, quickstart < 15 min.
**Research:** E1 signal with CIs, latency tax measured, Pareto frontier meaningful, results reproducible by a third party.
**Open source:** documented, modular, one external contributor adds a model or task.
**Practical:** a user with a 4 GB GPU and 16 GB RAM runs useful Physical AI experiments without robot hardware.

---

# 19. Immediate Next Actions

1. Phase 0 measurements on your 3050: tokens/s for 0.6B and 1.7B Q4, render VRAM, thermals under 10-minute load. Write numbers into `docs/hardware_OPAI-4G.md`.
2. Freeze `Policy`, `Perception`, `Backend`, `Budget` interfaces.
3. Build Phase 1 only. Do not touch dashboard, Vision mode, VLAs, or training until Gate 1 passes.
4. Create repo skeleton with CI and determinism test on day one.
5. Verify every cell of the comparison matrix (section 3) against current repos/papers before any public claim.

---

# 20. Final Definition

> **OpenPhysicalAI Lab: a local-first open-source laboratory for evaluating reliable Physical AI under explicit compute, memory, latency, and energy budgets — where the world keeps moving while the model thinks.**

```text
Physical AI Evaluation = Capability + Efficiency + Reliability + Recovery + Real-time behavior
Constraint             = Compute + Memory + Latency + Energy + Failure budget
Reference hardware     = RTX 3050 Laptop, 4 GB VRAM, 16 GB RAM (OPAI-4G)
First simulator        = MuJoCo
First models           = 0.3B-4B Q4 planners, plus SmolVLA / Octo baselines
First benchmark        = OPAI-Core: 5 tasks + failure/perturbation layer + budget contract
```
