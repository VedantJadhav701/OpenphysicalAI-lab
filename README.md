# OpenPhysicalAI Lab (v0.2, real engine)

Desktop app (Electron, iOS-style UI, Windows + macOS) around a real simulation and evaluation engine.
It measures how much reliable physical capability a Physical AI system delivers under an explicit, measured budget of VRAM, RAM, latency and energy, in a simulator where the world keeps moving while the planner thinks.

## What is real

| Part | Status |
|---|---|
| Physics | Real MuJoCo: 5-DOF arm, parallel gripper with friction, table, cubes, open-top container, kinematic conveyor. Analytic IK, Cartesian skills. |
| Phase-1 gate | Scripted pick-and-place: **200/200** over random scenes (`python python/gate1.py`). |
| Tasks | 5: pick & place, smallest, spatial ("left of"), multi-object, dynamic (moving cube). Seeded, deterministic across processes. |
| Perception | Oracle (sim truth + noise) and Vision (colour segmentation on a top-down frame). Vision position error about 1 mm on clean scenes. |
| Planners | Rule-based baseline (parses the instruction) and **Ollama** local LLMs with JSON-schema output + action validator. |
| Agents | Open-loop, closed-loop, closed-loop + recovery (detect, diagnose, re-observe, replan). |
| Verifier levels | V0 oracle (upper bound), V1 proprioception, V2 proprioception + camera. Evaluation oracle scores episodes and is never shown to the agent. |
| Failure injection | Grasp slip, displaced object, wrong placement, perception noise; seeded; ground truth logged for scoring only. |
| Real-time mode | Single owner steps the sim. The world is advanced by the planner's measured latency (hold policy) before the plan is applied, so slow planners act on stale observations. |
| Profiler | Process-tree RSS (+ Ollama processes), system RAM, GPU device VRAM / power / temperature / throttling via NVML or nvidia-smi. |
| Budget contract | Process vs device caps; a missing measurement fails; caps that cannot apply (no GPU) are marked not applicable. |
| Storage | SQLite in the app data folder; Budget Card export (.md); CSV export of experiments. |

## Verified Platforms & Environments

- **Linux (CPU)**: Real Electron launched under Xvfb; engine driven end-to-end.
- **Windows 11 (NVIDIA RTX 3050 Laptop GPU, 4 GB)**:
  - MuJoCo 3.16.0 verified on Python 3.11 (`thermo_agent` conda environment) & Python 3.13.
  - Phase-1 gate (`python gate1.py`) passed **200/200 random scenes (100.0%)** deterministically.
  - Test suite (`pytest tests/`) passed 100%.
  - Hardware profiler verified with NVML via `nvidia-ml-py`: correctly identifies RTX 3050 (OPAI-4G class), tracks GPU power, temperature, and WDDM memory estimation.
- **Real Ollama LLM Planning & Real-Time Benchmark**:
  - Model: `qwen3:4b-instruct-2507-q4_K_M` (2.5 GB, Q4 quantized) on RTX 3050 Laptop GPU.
  - Valid structured JSON schema output with 0 validation errors.
  - Warm inference latency: **~1056 ms** (~29.4 tokens/sec).
  - Loop-structure benchmark under moderate perturbations in real-time mode:

| Agent | Verifier | Mode | Perturbation | TSR (95% CI) | Detect | Recover | False Alarm | Missed | Planning p95 |
|---|---|---|---|---|---|---|---|---|---|
| **Open-loop** | V2 | realtime | Moderate | **70.0%** (39.7% to 89.2%) | n/a | n/a | n/a | n/a | 1460 ms |
| **Closed-loop** | V2 | realtime | Moderate | **70.0%** (39.7% to 89.2%) | 100.0% | 0.0% | 0.0% | 0.0% | 1290 ms |
| **Recovery** | V2 | realtime | Moderate | **100.0%** (72.2% to 100.0%) | **100.0%** | **100.0%** | **0.0%** | **0.0%** | **1227 ms** |

*(Demonstrates +30.0% reliability gain from active diagnosis & replanning under real-time physics).*

  - **Verifier Honesty Benchmark** (Moderate Perturbation, Real-Time Mode):

| Agent | Verifier | Mode | Perturbation | TSR (95% CI) | Detect | Recover | False Alarm | Missed | Planning p95 |
|---|---|---|---|---|---|---|---|---|---|
| **Recovery** | **V0 (oracle)** | realtime | Moderate | **100.0%** (72.2% to 100.0%) | 100.0% | 100.0% | 0.0% | 0.0% | 1320 ms |
| **Recovery** | **V1 (proprio)** | realtime | Moderate | **100.0%** (72.2% to 100.0%) | 100.0% | 100.0% | 0.0% | 0.0% | 1393 ms |
| **Recovery** | **V2 (camera)** | realtime | Moderate | **100.0%** (72.2% to 100.0%) | 100.0% | 100.0% | 0.0% | 0.0% | 1336 ms |

  - **The Latency Tax Benchmark** (Dynamic Moving Cube, Vision Perception):

| Agent | Verifier | Mode | Synthetic Latency | TSR (95% CI) | Detect | Recover | Planning p95 |
|---|---|---|---|---|---|---|---|
| **Closed-loop** | V1 | sync | 0 ms | **38.0%** (25.9% to 51.8%) | n/a | n/a | 0 ms |
| **Closed-loop** | V1 | realtime | 0 ms | **38.0%** (25.9% to 51.8%) | n/a | n/a | 0 ms |
| **Closed-loop** | V1 | realtime | 1000 ms (1.0 s) | **0.0%** (0.0% to 7.1%) | n/a | n/a | 1000 ms |
| **Closed-loop** | V1 | realtime | 2000 ms (2.0 s) | **0.0%** (0.0% to 7.1%) | n/a | n/a | 2000 ms |
| **Closed-loop** | V1 | realtime | 4000 ms (4.0 s) | **0.0%** (0.0% to 7.1%) | n/a | n/a | 4000 ms |

*(Empirical proof of the latency tax: at $\ge 1.0\text{ s}$ planner latency without velocity compensation, success collapses from 38% straight to 0% because the arm acts on stale observations while the world moves).*

## Pending Verification

- **macOS**: Not run yet. Expect small first-launch adjustments.
- **Installers**: `npm run dist` unsigned builds (SmartScreen / Gatekeeper).
- **Not built yet**: Learned VLA policies, drawer task, ROS2.

## Known limits (honest)

- Perception frames come from a software top-down camera drawn from simulator state, not MuJoCo's OpenGL renderer. It works with no GL driver but is cleaner than a real camera.
- Vision perception has no velocity estimate, so it cannot lead a moving cube. That is what produces the latency tax in the dynamic task (oracle mode gets velocity and compensates).
- Perturbation levels are not equivalent across perception modes: oracle mode adds position noise, vision mode adds pixel noise. Do not compare them across modes.
- Learned policies (VLA), drawer task, ROS2 and real robots are not implemented yet.
- V1 cannot see where an object landed, so it misses wrong placements. That is intentional and shows up as the V0/V1/V2 gap.

## Run

### Desktop App (Electron)

```bash
# Optional: activate existing conda environment
conda activate thermo_agent

# Install dependencies and start
npm install
npm start
```

If an active Conda environment (such as `thermo_agent`) or `OPAI_PYTHON` is detected, the app automatically hooks into it. Otherwise, on first launch it creates a private Python environment (`mujoco`, `numpy`, `psutil`) in its app data folder.

For local LLM planning:
```bash
ollama run qwen3:4b-instruct-2507-q4_K_M
```

Headless (no Electron):

```bash
cd python
pip install -r requirements.txt
python -m openphysicalai.cli run --task pick_place --perception vision --perturb moderate --verifier V2 --episodes 50
python gate1.py
```

## Build installers

```bash
npm run dist:win     # on Windows
npm run dist:mac     # on macOS
```

or push a `v*` tag and use `.github/workflows/build.yml`.

## Layout

```text
main.js preload.js           Electron main (env setup, sidecar manager), secure bridge
src/                         iOS-style UI
python/openphysicalai/       sim, tasks, skills, perception, render, planners, injection,
                             runner, profiler, budget, store, report, server (JSON lines), cli
python/tests, gate1.py       tests and the Phase-1 gate
docs/                        plan v3 (+ archived v1, v2)
```

License: Apache-2.0 (replace the LICENSE stub with the full text before release).
