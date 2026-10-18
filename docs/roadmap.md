# OpenPhysicalAI Lab: Coding-Agent Prompt, Feature Roadmap and Hardware Robustness Spec

Contents

1. Master prompt for the coding agent (copy the block in Part 1 into your agent)
2. Feature backlog with priorities and acceptance criteria
3. Hardware robustness spec (4 GB VRAM laptops and above)
4. How to make it the best (positioning, growth, release checklist)
5. Marketing assets and launch-video script
6. Known debt and unverified items

---

## Part 1. Master prompt for the coding agent

Copy everything inside the fence.

````text
ROLE
You are the lead engineer on OpenPhysicalAI Lab, an open-source, local-first Physical AI evaluation lab.
Mission: measure how much reliable physical capability a Physical AI system delivers under an explicit,
MEASURED budget of VRAM, RAM, latency and energy, in a simulator where the world keeps moving while the
planner thinks. Primary dev machine: laptop, RTX 3050 4 GB VRAM, i5, 16 GB RAM. Everything must run there.
Must also degrade gracefully on CPU-only machines and scale up on bigger GPUs.

CURRENT STATE (v0.2.0, real, not a demo)
Repo layout:
  main.js, preload.js        Electron main: env setup (venv in userData), Python sidecar (JSON-lines stdio), IPC
  src/                       iOS-style vanilla-JS UI (Home, New Run, Results, Experiments, Models, Settings)
  python/openphysicalai/
    sim.py          MuJoCo 3.x MJCF generator + World (5-DOF arm, analytic IK, parallel gripper, kinematic conveyor)
    skills.py       pick / place / go_home Cartesian skills
    tasks.py        5 seeded tasks: pick_place, smallest, spatial, multi, dynamic (zlib.crc32 seeding)
    render.py       numpy top-down software camera (no GL needed)
    perception.py   OraclePerception, VisionPerception (colour segmentation, yaw by 4th angular moment)
    planners.py     RulePlanner, OllamaPlanner (/api/chat, JSON-schema format, temp 0, seed 0), validate_plan
    injection.py    seeded failure injection: grasp_slip, object_displaced, wrong_placement, perception noise
    runner.py       RunConfig, run_episode, summarize, run; modes sync / realtime; agents open_loop / closed_loop / recovery
    profiler.py     psutil tree RSS (+Ollama), NVML / nvidia-smi device VRAM, power, temp, throttle
    budget.py       Budget contract, process vs device caps, missing measurement = FAIL, not_applicable on CPU-only
    stats.py        Wilson intervals
    store.py        SQLite;  report.py Budget Card (.md);  server.py JSON-lines commands;  cli.py `opai`
  python/tests, python/gate1.py   tests and the Phase-1 gate (scripted pick-place must be 200/200)
Measured so far (CPU, rule planner, small N, build environment): see README. Do not quote them as final.

HARD CONSTRAINTS
1. Local-first. No network calls at runtime except localhost Ollama. No telemetry.
2. Peak VRAM for the lab's own processes must stay <= 3.2 GB on 4 GB cards (device <= 3.8 GB).
3. Must start and run (slower) with no GPU. VRAM checks become `not_applicable`, never silently passed.
4. Deterministic: same seed + config => same scenes and same physics outcome across processes and OSes
   (never use Python hash(); use zlib.crc32 or numpy Generator with explicit seeds).
5. The evaluation oracle scores episodes. The agent never sees oracle data except through an explicitly
   labelled oracle perception mode.
6. Windows 10/11, macOS 12+ (Intel and Apple Silicon), Linux. No platform-only code paths without a fallback.

HONESTY RULES (non-negotiable)
- Never fabricate results, benchmarks, GPU readings, or "tested on X". If you did not run it, say so.
- Every claim in README/docs is tagged one of: VERIFIED (you ran it, command + output recorded), UNVERIFIED, PLANNED.
- Missing measurement = FAIL or `unknown`, never a pass or a guess.
- Oracle-mode and vision-mode perturbation levels are NOT equivalent; never compare across modes.
- If a number looks too good, find out why before reporting it.
- Report N and Wilson 95% CI with every success rate. No rate without N.

CODING STANDARDS
- Python >= 3.9, type hints, dataclasses, no global mutable state, small pure functions where possible.
- Every module has tests. `pytest -q` must pass before any commit. CI runs on Linux, Windows, macOS.
- JS: no frameworks in the renderer unless justified; contextIsolation + sandbox stay on; no remote content.
- Public JSON schemas (run results, Budget Card, plugin manifests) are versioned (`schema_version`).
- Every user-visible error has a cause and a fix hint. No silent excepts.
- Commit small, conventional commits. Never commit generated results or large binaries.

WORKING RULES
1. Before coding a task: restate its acceptance criteria, list files you will touch, list the tests you will add.
2. Do one backlog item at a time, in priority order (P0 first). Do not start the next until gates pass.
3. After each item run: `cd python && pytest -q`, `python gate1.py` (must stay 200/200), and a headless
   `opai run` smoke test. Paste real output in the PR description.
4. When a change alters any measured result, re-run the affected experiments and update docs with new numbers + N.
5. If blocked or a requirement is ambiguous, ask ONE precise question; do not guess silently on anything
   that changes scientific meaning (scoring, budgets, perturbations, seeds).
6. Keep a CHANGELOG.md and update the README status table (VERIFIED / UNVERIFIED / PLANNED) every time.
7. Finish each item with: what changed, how verified, what is still unverified, next step.

FIRST ACTIONS
a) Read README.md and docs/OpenPhysicalAI_Lab_Plan_v3.md. b) Run the tests and the gate. c) Run `opai profile`
on this machine and save the output as docs/hardware/<machine>.json. d) Start backlog item P0-1.
````

---

## Part 2. Feature backlog

Priority key: P0 = needed before public launch, P1 = within 4 weeks after launch, P2 = growth, P3 = later.

### P0 (launch blockers)

| ID | Feature | Acceptance criteria |
|---|---|---|
| P0-1 | `opai doctor` / Phase 0 hardware profile | One command prints OS, CPU, RAM, GPU(s), VRAM, driver, Ollama status, thermals, and a recommended tier (Part 3). Writes JSON. Works with no GPU. Tested on Windows, macOS, Linux CI (GPU fields mocked). |
| P0-2 | Real GPU path verification | Run on the RTX 3050: NVML device VRAM, power, temp, throttle recorded in a real run. Windows per-process VRAM fallback labelled "estimated". Result stored in docs/hardware/. |
| P0-3 | Real Ollama verification | Test with at least 3 models (1B, 1.7B-4B, 7B quantized). Record JSON validity rate, p50/p95 latency, VRAM peak per model. Document failures. |
| P0-4 | Crash-safe, resumable runs | Episodes written to SQLite as they finish. Kill the process mid-run, restart, `--resume` continues with identical results to an uninterrupted run. |
| P0-5 | Windows + macOS installers verified | `npm run dist` on both OSes via CI; manual launch on real machines; Python discovery and venv creation work; first-run screen shows clear fix hints. |
| P0-6 | Full Apache-2.0 LICENSE, NOTICE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY | Files present, license headers consistent. |
| P0-7 | Reproducibility bundle | Every run exports `run.json` with config, seeds, versions (mujoco, numpy, app, git sha), hardware, and results. `opai reproduce run.json` re-runs and compares. |
| P0-8 | Paired statistics | Comparisons between two configs on the same seeds use McNemar (binary) plus paired bootstrap CI. UI shows "difference and CI", not only two rates. |

### P1 (first month)

| ID | Feature | Acceptance criteria |
|---|---|---|
| P1-1 | Parallel episode workers | `--workers N` with process pool; results identical to serial for same seeds; auto cap by cores and RAM; never exceeds budget RAM cap. |
| P1-2 | Virtual-latency mode with trace replay | Planner latency taken from a recorded trace instead of wall clock so results are reproducible across machines. Trace format documented. |
| P1-3 | Velocity estimation in vision perception | Two-frame tracker gives velocity; dynamic task latency tax shrinks for vision agent; report both with and without. |
| P1-4 | Min-Budget@X search | Given a success target (for example 80%), binary-search the smallest model size / quant / latency cap that reaches it. Output: a table and a Pareto plot. |
| P1-5 | Model-scale and quantization sweep | Auto-run an Ollama model list and quantizations; Pareto chart of success vs VRAM vs latency. |
| P1-6 | Hardware Wall export | Submit-ready JSON of results + hardware profile; schema validated; stable ordering; no personal data. |
| P1-7 | MuJoCo native renderer option | Optional EGL/GLFW/Metal path producing real camera images; falls back to the software renderer; both modes labelled in results. |
| P1-8 | Onboarding wizard + model recommender | First run detects hardware, suggests tier, offers `ollama pull` for a fitting model, runs a 20-episode sanity run in under 3 minutes on 4 GB tier. |
| P1-9 | Plugin SDK v1 | Planner, perception, task and verifier plugins via a manifest + entry point; examples and tests; sandboxed import errors do not crash the app. |

### P2 (growth)

| ID | Feature | Acceptance criteria |
|---|---|---|
| P2-1 | Drawer / articulated-object task | Open drawer, place object inside; seeded; scripted gate >= 95%. |
| P2-2 | Learned-policy track | Adapter for LeRobot policies (ACT, SmolVLA). Same budget contract, same injector. Document VRAM use per policy. |
| P2-3 | LIBERO / ManiSkill adapter | Read-only adapter that runs a subset of tasks under the same budget/latency harness. |
| P2-4 | Web leaderboard + Hardware Wall page | Static site generated from submitted JSON (GitHub Pages). Filter by tier, task, budget profile. |
| P2-5 | Docker image and headless server mode | `docker run opai ...` for CI and clusters; CPU image and CUDA image. |
| P2-6 | Energy accounting | Joules per successful episode from NVML power samples; CPU via RAPL where available; "not measured" otherwise. |
| P2-7 | Auto-update + signed builds | Apple notarization, Windows code signing, electron-updater with opt-in only. |
| P2-8 | Bundled Python | python-build-standalone shipped in installer so no system Python is needed. |

### P3 (later)

ROS2 bridge, real-robot adapter (SO-100 / low-cost arms), multi-arm tasks, language-conditioned task generator, Isaac Lab adapter for 12 GB+ GPUs, community task marketplace.

### Suggested order of the first 8 weeks

| Weeks | Focus | Gate |
|---|---|---|
| 1 | P0-1, P0-2, P0-3 | Real 3050 numbers recorded. |
| 2 | P0-4, P0-7, P0-8 | Resume and reproduce proven by test. |
| 3 | P0-5, P0-6, P1-8 | Installers launch on real Windows and macOS. |
| 4 | P1-1, P1-3 | Parallel runs identical to serial. |
| 5 | P1-4, P1-5 | Pareto outputs on 3 models. |
| 6 | P1-6, P2-4 skeleton, docs | Hardware Wall schema frozen. |
| 7 | Launch prep: video, README, demo GIFs, honest limits | Checklist in Part 4 complete. |
| 8 | Public launch | Tagged v0.3. |

---

## Part 3. Hardware robustness spec (4 GB VRAM laptops and above)

### 3.1 Tiers

Auto-detected by `opai doctor`. A tier sets defaults only; the user can override everything.

| Tier | Typical hardware | Default planner | Default budget profile | Defaults |
|---|---|---|---|---|
| T0 CPU-only | No discrete GPU, 8 GB+ RAM | Rule planner; optional 0.5B-1.7B Q4 on CPU | relaxed | VRAM checks `not_applicable`; workers = cores/2; vision at low resolution. |
| T1 4 GB | RTX 3050 / 1650 / MX-class 4 GB | Q4 models up to about 1.7B-3B | standard | Process cap 3.2 GB, device cap 3.8 GB; 1 worker for LLM, up to 3 for rule planner. |
| T2 6-8 GB | 3060 laptop, 4060, 3070 | Q4 up to 7B-8B (tight) | standard | Process cap 5.0 / 7.0 GB device (provisional). |
| T3 12-16 GB | 4070 Ti / 4080 / 5070 Ti | 7B-14B Q4, small VLMs | standard / strict | Process cap 10 / 14 GB (provisional). |
| T4 24 GB+ | 3090 / 4090 / 5090, workstation | 30B Q4, larger VLMs, learned policies | strict | Caps by user; multiple workers. |
| Apple Silicon | M1-M4, unified memory | Ollama Metal, same tiering by unified RAM | by RAM | Never report VRAM; report unified memory use; GPU power not available. |
| AMD / Intel GPU | ROCm / Vulkan via Ollama | Same tiering by device memory | by memory | Device memory by vendor tool; per-process unavailable; labelled estimated. |

All cap numbers above are provisional until measured on real hardware. Do not publish them as facts.

### 3.2 Requirements

1. **Detection**: NVML first, then `nvidia-smi`, then rocm-smi / system_profiler / wmic fallbacks. If nothing works: T0 and say why.
2. **Budget enforcement**: the lab checks its own VRAM before loading a model. If `model_size_estimate + kv_cache_estimate + baseline > cap`, refuse with a clear message and suggest a smaller model or quantization. Never load and hope.
3. **OOM safety**: catch Ollama out-of-memory and HTTP errors; record the episode as `planner_error` with cause; continue the run; show a summary of how many episodes were lost. Never crash the app.
4. **Sequential loading**: never hold perception model and planner model in VRAM at once on T1/T2 unless the estimate fits. Unload (`keep_alive: 0`) between phases when needed.
5. **Thermal and power awareness**: log temperature, clocks, throttle reasons. If throttling is detected, mark affected episodes (`thermal_throttled=true`) and warn that latency numbers are degraded. Optional pause-and-cool mode.
6. **Thread caps**: set `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, MuJoCo threads, worker count from cores and RAM so the UI stays responsive. Default leaves at least 2 logical cores free.
7. **RAM guard**: workers autoscale down if system RAM use passes 85% of the RAM cap; hard stop and clear message at the cap.
8. **Disk**: warn if free space under 5 GB; cap result storage growth; frames are never stored unless the user opts in.
9. **Battery / laptop**: detect battery power and warn that benchmarks on battery are not comparable; record `on_battery` in the hardware profile.
10. **No-GPU rendering**: software renderer is always available; native GL is optional and never required.
11. **Scaling up**: nothing in the code may assume 4 GB. Caps and defaults come from the tier and the user config; larger tiers unlock larger model lists and more workers.
12. **Comparability rule**: results are only comparable inside the same tier + budget profile + hardware class. The Hardware Wall groups by these.

### 3.3 Test matrix

| Machine class | Required before launch |
|---|---|
| Windows 11, RTX 3050 4 GB (author) | Full run + GPU profiling + 3 Ollama models |
| Windows 10/11, CPU-only | Full run with rule planner |
| macOS Apple Silicon | Launch, run, Ollama Metal |
| macOS Intel | Launch, run (rule planner) |
| Ubuntu 22.04 | CI + headless |
| Any 8 GB+ NVIDIA | Community-reported through the Hardware Wall |

Mark every cell VERIFIED only after a real run. Unfilled cells stay UNVERIFIED in the README.

---

## Part 4. How to make it the best

### 4.1 What makes this project different (keep this sharp)

1. **Budget-first**: every score comes with measured VRAM, RAM, latency, energy. "Success per GB" and "success per second" are first-class.
2. **Latency-coupled world**: the world moves while the planner thinks. Latency tax is measured, not assumed.
3. **Honest verifier levels**: V0/V1/V2 expose how much a verifier flatters results.
4. **Laptop-class by design**: the benchmark is meaningful on the hardware most people have.
5. **Reproducible**: seeds, versions, hardware, one-command reproduce.
6. **Open and extensible**: plugin SDK, open schemas, community Hardware Wall.

### 4.2 Positioning

One sentence: "Evaluate Physical AI under real budgets."
Not another benchmark of success rate on a datacentre GPU. A lab that answers: what does it deliver on a 4 GB laptop, and how fast does it fall apart when thinking is slow?

### 4.3 Growth plan

- Launch assets: 30 s video, 3 GIFs (slip then recovery, latency tax chart, Budget Card), clean README with honest limits.
- First targets: r/robotics, r/LocalLLaMA, Hacker News (Show HN), LeRobot and MuJoCo communities, Hugging Face blog/space, X and LinkedIn robotics circles.
- Credibility: publish the first small study ("What a 4 GB laptop can do: latency tax in Physical AI") with N, CIs and raw data. Honest limits section stays.
- Good-first-issues: label 15+ issues (new tasks, new planners, docs, Windows fixes).
- Hardware Wall: invite people to submit their results; show top entries by tier.
- Cadence: a release every 2 weeks for the first 3 months; changelog with real numbers.
- Governance: Apache-2.0, DCO or CLA decision, code of conduct, maintainers file, roadmap issue.

### 4.4 Release checklist

- [ ] Full LICENSE, NOTICE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- [ ] CI green on Linux, Windows, macOS
- [ ] Installers launch on real Windows and macOS; first-run flow tested by someone who is not the author
- [ ] Real GPU run recorded on RTX 3050; docs/hardware filled
- [ ] 3 real Ollama models tested; results documented
- [ ] README: status table VERIFIED / UNVERIFIED / PLANNED, honest limits, quickstart in under 5 minutes
- [ ] Reproduce command proven
- [ ] First study written with raw data attached
- [ ] Demo GIFs and the launch video use only real, re-verified numbers
- [ ] Repository URL, name check (trademarks), domain decided; added to the video end card
- [ ] Issue templates and 15 good-first-issues
- [ ] Release notes and Show HN text drafted

---

## Part 5. Marketing assets

Delivered files (folder `marketing/`):

| File | Use |
|---|---|
| `logo-icon.svg`, `logo-icon-1024.png`, `logo-icon-256.png` | App icon, avatar, favicon source |
| `logo-horizontal-dark.svg/.png`, `logo-horizontal-light.svg/.png` | README header, website, slides |
| `logo-mono.svg` | One-colour uses |
| `OpenPhysicalAI_Lab_Launch_30s.mp4` | 1920x1080, 30 fps, 30 s, with music |

Logo idea: a gauge ring (the budget) around a two-link robot arm with a gripper, on an iOS-style blue-to-indigo gradient.

### 30 s video script (matches the rendered cut)

| Time | On screen | Voice-over / caption (optional) |
|---|---|---|
| 0-6 s | "Physical AI has a benchmark problem." then three questions | "Does it fit on your hardware? Is it fast enough? Does it recover when things go wrong?" |
| 6-9 s | Logo reveal, tagline | "OpenPhysicalAI Lab. Evaluate Physical AI under real budgets." |
| 9-16 s | Simulation: grasp slips, agent recovers; live gauges | "Real physics. Real failures. Real recovery." |
| 16-20 s | Latency-tax bar chart | "Watch success collapse as thinking gets slower." |
| 20-24 s | Recovery comparison chart | "See what verification and recovery really buy." |
| 24-27 s | Feature cards | "Runs on a 4 GB laptop. 100% local. Five tasks. Ollama. Open source." |
| 27-30 s | End card | "Measure what Physical AI really delivers." |

Before public use, check all of these:
- Chart numbers (40/40/0/0 and 25/25/55/67/68) come from the build environment (CPU, rule planner, small N). Re-run on your machine with larger N and update the video.
- "Windows and macOS" and "runs on 4 GB" must be VERIFIED first.
- The end card has no URL; add the real repository link once it exists.

---

## Part 6. Known debt and unverified items

UNVERIFIED: Windows and macOS runs, installers, real Ollama models, real GPU profiling (NVML, power, throttle), code signing, bundled Python.

Known limits:
- `ram_process_peak` currently reads small (about 0.07 GB) because only the Python process is measured in some paths; verify the tree and Ollama accounting on a real run.
- Vision perception comes from a software top-down camera and is cleaner than a real camera; no velocity estimate yet.
- Oracle and vision perturbation levels are not equivalent.
- No learned (VLA) policies, no drawer task, no ROS2, no real robot.
- Budget profile numbers are provisional.
- LICENSE file is a stub until replaced with the full Apache-2.0 text.
- Measured results so far use small episode counts and the rule planner; confidence intervals are wide.
