# OpenPhysicalAI Lab

## Resource-Aware Evaluation Framework for Reliable Closed-Loop Physical AI

**Project status:** Research + open-source development plan  
**Target hardware:** RTX 3050 Laptop GPU, 4 GB VRAM, 16 GB RAM  
**Primary development mode:** Local-first  
**Initial simulator:** MuJoCo  
**Future backends:** Isaac Lab, other simulators, ROS2, real robots

---

# 1. Project Definition

## 1.1 Project name

**OpenPhysicalAI Lab**

## 1.2 Core definition

> OpenPhysicalAI Lab is a local-first open-source laboratory for measuring how much physical intelligence a Physical AI agent provides per unit of compute, memory, latency, and failure budget.

The system lets users:

1. Select physical tasks.
2. Select simulation environments.
3. Select AI models.
4. Set hardware/resource budgets.
5. Run closed-loop Physical AI agents.
6. Measure task capability.
7. Measure resource consumption.
8. Inject disturbances and failures.
9. Measure recovery behavior.
10. Compare models and system architectures.
11. Produce reproducible deployment reports.

---

# 2. Problem Statement

Physical AI research has many separate pieces:

- robot simulators
- manipulation benchmarks
- VLA models
- multimodal LLMs
- robot policies
- robustness benchmarks
- recovery benchmarks
- hardware deployment studies
- model efficiency research

But these pieces often answer different questions.

A high benchmark score does not tell us:

- How much VRAM did model need?
- How much RAM did complete system need?
- How much latency did action generation add?
- Can model run within 4 GB VRAM?
- What happens when perception fails?
- What happens when robot misses grasp?
- Can agent detect failure?
- Can agent recover?
- How many extra actions does recovery require?
- What capability is lost after quantization?
- What is best model under fixed deployment budget?

OpenPhysicalAI Lab focuses on this combined question:

> **Given fixed compute and system constraints, which Physical AI architecture gives best capability and reliability?**

---

# 3. Research Gap

Existing systems already cover major parts of Physical AI.

Examples include:

- LIBERO
- Meta-World
- ManiSkill
- BEHAVIOR-1K
- RoboCasa
- VLABench
- EmbodiedBench
- PAI-Bench
- LIBERO-Plus
- RoboTwin-Plus
- SIMPLER
- Open X-Embodiment
- OpenVLA
- vla-eval
- LIBERO-Recover
- SafeVLA-Bench
- efficient VLA / edge deployment research

Therefore OpenPhysicalAI Lab must not claim:

- first Physical AI benchmark
- first VLA evaluation framework
- first robot recovery benchmark
- first robustness benchmark
- first small VLA
- first edge VLA

Those areas already have substantial prior work.

## 3.1 Proposed gap

OpenPhysicalAI Lab studies the **joint trade-off between**:

1. Physical task capability
2. Compute consumption
3. Memory consumption
4. Inference latency
5. Task efficiency
6. Failure frequency
7. Recovery capability
8. Deployment budget

Core research question:

> **How do model scale, quantization, system architecture, and closed-loop recovery affect Physical AI capability under constrained deployment budgets?**

---

# 4. Core Research Hypothesis

A larger model is not automatically a better deployable Physical AI system.

A useful Physical AI system should maximize:

```text
Physical Capability
-------------------------------
Compute + Memory + Latency + Failure Cost
```

This creates a practical optimization problem.

A 7B model achieving 90% task success may be less useful than a 0.6B model achieving 84% success while:

- using half memory
- using less VRAM
- running faster
- recovering from failures
- fitting inside target hardware

OpenPhysicalAI Lab should make this trade-off measurable.

---

# 5. Main Research Questions

## RQ1 — Model scaling

How does model size affect:

- task success
- planning quality
- perception-grounded reasoning
- latency
- VRAM
- RAM
- recovery capability?

## RQ2 — Quantization

How much physical task capability is lost through:

- FP16
- INT8
- Q8
- Q6
- Q5
- Q4

compared with resource savings?

## RQ3 — Closed-loop control

Does:

```text
Plan → Execute
```

perform worse than:

```text
Plan → Execute → Observe → Verify → Recover → Replan
```

?

## RQ4 — Failure recovery

Which failures can an agent detect and recover from?

Examples:

- failed grasp
- wrong object
- wrong placement
- object displacement
- perception error
- action timeout
- collision
- unexpected obstacle

## RQ5 — Resource budget

How does capability change under:

```text
1 GB
2 GB
4 GB
8 GB
```

VRAM/RAM budgets?

## RQ6 — Deployment efficiency

What is best model/system for a fixed budget?

Example:

```text
VRAM <= 4 GB
RAM <= 8 GB
Latency <= 500 ms
```

## RQ7 — Pareto efficiency

Which models lie on capability-efficiency Pareto frontier?

---

# 6. Project Scope

## 6.1 V1 scope

V1 must contain:

- local installation
- MuJoCo
- one robot
- RGB camera
- basic manipulation scene
- five benchmark tasks
- local small model inference
- structured action representation
- action validator
- closed-loop execution
- failure verification
- recovery
- resource profiling
- experiment logging
- benchmark runner
- reproducible results

## 6.2 V1 does not contain

Do not build:

- custom physics simulator
- humanoid robot
- full ROS2 stack
- large VLA training
- distributed training
- cloud dependency
- multi-agent architecture
- large-scale RL
- physical robot dependency
- giant multimodal model

---

# 7. Product Identity

OpenPhysicalAI Lab should have four major layers.

```text
                 OpenPhysicalAI Lab
                        |
        +---------------+---------------+
        |               |               |
     Runtime        Benchmark        Research
        |               |               |
        +---------------+---------------+
                        |
                    Dashboard
```

## 7.1 Runtime

Runs Physical AI agents.

## 7.2 Benchmark

Measures agents.

## 7.3 Research

Runs controlled experiments.

## 7.4 Dashboard

Shows simulation, agent state, metrics, failures, and results.

---

# 8. System Architecture

```text
                         USER
                          |
                    Task instruction
                          |
                          v
                  +---------------+
                  | Task Manager  |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |  Perception   |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |  World State  |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |   Reasoner    |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  | Action Planner|
                  +-------+-------+
                          |
                          v
                  +---------------+
                  | Action Validator|
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |   Controller  |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |  Environment  |
                  +-------+-------+
                          |
                          v
                     Observation
                          |
                          v
                  +---------------+
                  |   Verifier    |
                  +-------+-------+
                          |
                +---------+---------+
                |                   |
              SUCCESS             FAILURE
                |                   |
                v                   v
              DONE              Recovery
                                    |
                                    v
                                Replanning
                                    |
                                    +------> Controller
```

---

# 9. Physical AI Agent Model

Agent should not directly produce arbitrary motor commands.

Use hierarchy:

```text
Natural language
      |
      v
Task reasoning
      |
      v
Structured action
      |
      v
Action validation
      |
      v
Robot controller
      |
      v
Motor/physics action
```

Example:

```json
{
  "action": "pick",
  "object": "red_cube"
}
```

Then controller converts this into:

```text
MOVE_TO(red_cube)
GRASP(red_cube)
LIFT()
```

This separation gives:

- safety
- reproducibility
- easier debugging
- easier evaluation
- model interchangeability

---

# 10. World State

Create common structured world representation.

Example:

```json
{
  "robot": {
    "position": [0.10, 0.20, 0.10],
    "gripper": "open"
  },
  "objects": [
    {
      "id": "cube_01",
      "type": "cube",
      "color": "red",
      "position": [0.30, 0.20, 0.04]
    }
  ],
  "containers": [
    {
      "id": "box_01",
      "type": "container",
      "color": "blue",
      "position": [0.70, 0.40, 0.02]
    }
  ]
}
```

World state should support two sources.

## Oracle mode

Simulator ground truth.

## Vision mode

Camera → vision model → structured world state.

This allows controlled research:

```text
Reasoning failure
vs.
Perception failure
```

---

# 11. Simulation Strategy

## Initial simulator

Use **MuJoCo**.

Reasons:

- lightweight
- local
- Python-friendly
- suitable for laptop
- good physics
- good manipulation support
- easier than heavy simulator stack for V1

## Future simulator

Add Isaac Lab as optional backend.

Do not replace MuJoCo.

Architecture:

```text
OpenPhysicalAI
      |
      +---- MuJoCoBackend
      |
      +---- IsaacLabBackend
      |
      +---- FutureRobotBackend
```

---

# 12. Initial Robot

Use one simple robot arm.

Target:

- 6-DOF arm
- parallel gripper
- RGB camera
- table
- simple objects

Avoid humanoids.

Avoid mobile manipulators initially.

Avoid complex environments.

---

# 13. Initial Environment

Create one simple manipulation environment:

```text
Table
 |
 +-- Robot arm
 |
 +-- Red cube
 |
 +-- Blue container
 |
 +-- Camera
```

First task:

> Put red cube inside blue container.

This task becomes system integration test.

---

# 14. Benchmark Tasks

V1 benchmark contains five task families.

## Task 1 — Pick and Place

Instruction:

```text
Put the red cube inside the blue container.
```

Tests:

- object grounding
- grasping
- placement
- basic planning

---

## Task 2 — Object Selection

Instruction:

```text
Pick up the smallest object.
```

Tests:

- visual comparison
- object selection
- spatial reasoning

---

## Task 3 — Spatial Reasoning

Instruction:

```text
Move the object left of the triangle into the container.
```

Tests:

- relative position
- language grounding
- spatial reasoning

---

## Task 4 — Multi-object Manipulation

Instruction:

```text
Put all red objects into the blue container.
```

Tests:

- task decomposition
- repeated manipulation
- state tracking

---

## Task 5 — Failure Recovery

Inject controlled failure:

- failed grasp
- object displacement
- wrong placement
- obstacle
- perception perturbation

Tests:

- failure detection
- diagnosis
- recovery
- replanning

---

# 15. Benchmark Execution Protocol

Every task should run multiple episodes.

Example:

```text
Task:
Pick and Place

Episodes:
100

Random seeds:
10 seed groups

Object positions:
randomized

Robot initial state:
randomized

Camera:
fixed initially
```

Later add domain randomization.

Do not report single-run success as research result.

Minimum target:

```text
50 episodes/task
```

Better:

```text
100 episodes/task
```

---

# 16. Metrics

## 16.1 Task Success Rate

```text
TSR = successful episodes / total episodes
```

Primary capability metric.

---

## 16.2 Planning Success Rate

Measures whether generated plan is valid and task-complete.

---

## 16.3 Action Success Rate

Measures individual action success.

```text
ASR = successful actions / total actions
```

---

## 16.4 Recovery Success Rate

```text
RSR =
successfully recovered failures
/
recoverable failures
```

---

## 16.5 Failure Rate

Break down failures:

```text
grasp
perception
planning
collision
placement
timeout
controller
```

---

## 16.6 End-to-End Latency

Measure:

```text
observation latency
+
perception latency
+
reasoning latency
+
planning latency
+
control latency
```

---

## 16.7 Time to First Action

Measure model/system responsiveness.

---

## 16.8 Peak VRAM

Measure:

- model weights
- KV cache
- inference runtime
- vision model
- simulator GPU usage

---

## 16.9 Peak RAM

Measure complete process.

---

## 16.10 Token Throughput

For language models:

```text
tokens/sec
```

---

## 16.11 Action Efficiency

Compare:

```text
actual actions
vs.
minimum actions
```

---

## 16.12 Recovery Cost

Measure:

```text
additional actions
additional latency
additional compute
```

---

## 16.13 Resource Efficiency

Proposed metric:

```text
Capability Efficiency =
Task Success Rate
/
Normalized Resource Cost
```

Do not use this as sole ranking metric.

Always report raw metrics too.

---

# 17. Resource Budget

This is core feature.

Users define:

```yaml
resource_budget:
  max_vram_gb: 4
  max_ram_gb: 8
  max_latency_ms: 500
  min_simulation_fps: 20
```

System returns:

```text
PASS
```

or:

```text
FAIL

VRAM:
4.37 GB > 4.00 GB
```

---

# 18. Reference Hardware Profile

Create named profile:

```text
OPAI-4G
```

Definition:

```text
GPU:
RTX 3050 Laptop GPU

VRAM:
4 GB

System RAM:
16 GB
```

Initial research should explicitly report results on this profile.

Later profiles:

```text
OPAI-2G
OPAI-4G
OPAI-8G
OPAI-16G
```

---

# 19. Model Strategy

Do not train large models locally.

Initial models should be small.

Target range:

```text
0.3B
0.5B
0.6B
1.1B
1.7B
3B
```

Use quantization where supported.

Initial comparison:

```text
0.6B Q4
1.7B Q4
3B Q4
```

Only test 3B if memory allows.

---

# 20. Model Interface

Every model should implement common interface.

Conceptual API:

```python
class ReasoningModel:

    def generate_plan(
        self,
        instruction,
        world_state
    ):
        ...
```

Model registry:

```python
ModelRegistry.register(...)
```

User should be able to swap model without changing environment.

---

# 21. Perception Interface

```python
class PerceptionModel:

    def perceive(self, observation):
        ...
```

Output:

```python
WorldState
```

Support:

```text
OraclePerception
VisionPerception
FutureVLMPerception
```

---

# 22. Environment Interface

```python
class PhysicalEnvironment:

    def reset(self):
        ...

    def observe(self):
        ...

    def execute(self, action):
        ...

    def get_state(self):
        ...

    def check_success(self):
        ...
```

This becomes core API.

---

# 23. Robot Interface

```python
class RobotBackend:

    def move_to(self, target):
        ...

    def grasp(self):
        ...

    def release(self):
        ...

    def observe(self):
        ...
```

Backends:

```text
MuJoCoRobot
IsaacRobot
FutureROSRobot
```

---

# 24. Failure Injection

Build failure injection into benchmark.

Example:

```yaml
failure_injection:
  enabled: true

  types:
    - failed_grasp
    - object_displacement
    - wrong_placement
    - obstacle
    - camera_noise
```

Each failure should have known ground truth.

Example:

```text
Expected:
cube inside container

Observed:
cube 10 cm outside container

Failure:
placement_failure
```

---

# 25. Recovery Architecture

```text
Action
  |
  v
Observation
  |
  v
Verifier
  |
  +---- Success ---> Continue
  |
  +---- Failure
          |
          v
      Diagnose
          |
          v
       Recover
          |
          v
       Re-plan
          |
          v
         Act
```

Recovery policies:

### V1

Rule-based recovery.

### V2

LLM/SLM-based recovery.

### V3

Learned recovery policy.

This gives clean research comparisons.

---

# 26. Core Experiment Matrix

## Experiment A — Model scaling

Compare:

```text
0.3B
0.6B
1.1B
1.7B
3B
```

Metrics:

- success
- latency
- VRAM
- RAM
- recovery
- action efficiency

---

## Experiment B — Quantization

Compare:

```text
FP16
INT8
Q8
Q6
Q5
Q4
```

Question:

> How much physical capability survives quantization?

---

## Experiment C — Open-loop vs closed-loop

Compare:

```text
A:
Plan → Execute

B:
Plan → Execute → Observe

C:
Plan → Execute → Observe → Verify → Recover → Replan
```

Hypothesis:

```text
Closed-loop systems should maintain higher success under perturbations.
```

---

## Experiment D — Resource budget

Test:

```text
1 GB
2 GB
4 GB
8 GB
```

Measure capability degradation.

---

## Experiment E — Perception source

Compare:

```text
Oracle state
vs.
Vision perception
```

This isolates perception impact.

---

## Experiment F — Failure recovery

Compare:

```text
No recovery
Rule-based recovery
LLM-based recovery
Learned recovery
```

---

## Experiment G — Disturbance severity

Create:

```text
Low
Medium
High
```

disturbance levels.

Measure:

- task success
- recovery
- recovery time
- extra actions

---

# 27. Pareto Frontier

This should become major analysis.

Plot:

```text
Task Success
      |
100%  |                       *
      |                  *
 90%  |             *
      |        *
 80%  |    *
      |
      +-----------------------------
          VRAM / Latency / RAM
```

Identify Pareto-optimal systems.

A model is Pareto dominated if another model provides:

- equal/higher success
- equal/lower memory
- equal/lower latency

with at least one strict improvement.

---

# 28. Deployment Readiness Score

Do not make this single score primary.

Can create optional composite score.

Example:

```text
Deployment Readiness =
Capability
×
Reliability
×
Budget Compliance
```

Better approach:

Report:

```text
Capability
Efficiency
Reliability
Budget compliance
```

separately.

Avoid hiding important trade-offs inside one number.

---

# 29. Dashboard

Use:

```text
Frontend:
React + TypeScript

Backend:
FastAPI

Database:
SQLite
```

Dashboard pages:

```text
Dashboard
Environments
Tasks
Models
Agents
Experiments
Benchmarks
Results
Resource Profiles
Settings
```

---

# 30. Main Experiment UI

Core screen:

```text
+-------------------------------------------------------+
| OpenPhysicalAI Lab                                    |
+----------------------+--------------------------------+
| Simulation           | Agent State                    |
|                      |                                |
|      Robot           | Perception          PASS       |
|    Cube  Box         | World State         PASS       |
|                      | Planning            PASS       |
|                      | Action              3/5        |
|                      | Verification        RUNNING    |
+----------------------+--------------------------------+
| Metrics                                             |
| Success: 82% | Latency: 341 ms | VRAM: 2.1 GB      |
| RAM: 4.3 GB   | Actions: 5      | Recovery: 67%     |
+-------------------------------------------------------+
```

---

# 31. Experiment Database

SQLite schema should eventually contain:

```text
experiments
models
tasks
episodes
actions
failures
recoveries
resource_measurements
benchmark_runs
```

Every experiment must be reproducible.

Store:

- model ID
- model revision
- quantization
- task
- environment version
- simulator version
- random seed
- hardware profile
- resource budget
- results

---

# 32. Experiment Reproducibility

Every result must record:

```text
Git commit
Model revision
Model quantization
Environment version
Task version
Random seed
Python version
PyTorch version
GPU
VRAM
RAM
Operating system
Configuration
```

This is necessary for paper-quality results.

---

# 33. CLI

Target CLI:

```bash
openphys --help
```

Examples:

```bash
openphys env list
```

```bash
openphys model list
```

```bash
openphys task list
```

```bash
openphys run --task pick_place --model phys-0.6b
```

```bash
openphys benchmark --suite core-v1
```

```bash
openphys experiment --config configs/experiment.yaml
```

```bash
openphys report --experiment exp_001
```

```bash
openphys lab
```

---

# 34. Python API

Target:

```python
from openphys import Agent, Environment

env = Environment.load("mujoco/pick_place")

agent = Agent(
    model="phys-0.6b",
    quantization="Q4"
)

result = agent.run(
    task="put red cube in blue container",
    environment=env
)

print(result.success)
print(result.metrics)
```

Exact API can change during development.

Keep interface stable after V0.3.

---

# 35. Project Repository

```text
OpenPhysicalAI/
│
├── openphys/
│   ├── agents/
│   ├── perception/
│   ├── reasoning/
│   ├── actions/
│   ├── environments/
│   ├── recovery/
│   ├── benchmark/
│   ├── models/
│   └── telemetry/
│
├── environments/
│   └── mujoco/
│
├── tasks/
│   ├── pick_place/
│   ├── object_selection/
│   ├── spatial_reasoning/
│   ├── multi_object/
│   └── recovery/
│
├── benchmark/
│
├── dashboard/
│
├── experiments/
│
├── configs/
│
├── scripts/
│
├── examples/
│
├── tests/
│
├── docs/
│
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
```

---

# 36. Development Roadmap

## Phase 0 — Specification

**Duration: 1–2 days**

Deliverables:

- project specification
- architecture diagram
- API design
- benchmark definition
- metric definition
- research questions

---

## Phase 1 — MuJoCo Prototype

**Duration: 3–5 days**

Build:

- robot
- camera
- table
- cube
- container
- deterministic controller

Success criterion:

> Robot completes pick-and-place reliably.

---

## Phase 2 — Environment API

**Duration: 2–4 days**

Build:

- `PhysicalEnvironment`
- observation schema
- action schema
- task interface
- reset/step
- success checking

Success criterion:

> Environment can run independently through Python API.

---

## Phase 3 — World State

**Duration: 2–4 days**

Build:

- object representation
- robot state
- spatial relations
- oracle perception

Success criterion:

> Any task state can be represented as structured data.

---

## Phase 4 — Perception

**Duration: 4–7 days**

Build:

- camera pipeline
- object detector
- world-state conversion

Success criterion:

> Camera observation produces usable scene representation.

---

## Phase 5 — Local Reasoning

**Duration: 4–7 days**

Build:

- model runtime
- model registry
- structured planning
- action generation
- validation

Success criterion:

> Local small model generates valid plans.

---

## Phase 6 — Closed Loop

**Duration: 4–7 days**

Build:

- observation after action
- verifier
- failure detector
- retry
- recovery

Success criterion:

> Agent can detect at least one controlled failure and recover.

---

## Phase 7 — Benchmark

**Duration: 5–7 days**

Build:

- five task families
- episode runner
- metrics
- random seeds
- result storage

Success criterion:

> 100-episode benchmark can run automatically.

---

## Phase 8 — Resource Profiler

**Duration: 4–7 days**

Measure:

- VRAM
- RAM
- latency
- tokens/sec
- simulator FPS
- model load time

Success criterion:

> Every benchmark run produces resource report.

---

## Phase 9 — Dashboard

**Duration: 1–2 weeks**

Build:

- experiment browser
- live simulation
- metrics
- model comparison
- experiment comparison
- resource budget editor

Success criterion:

> User can perform complete experiment without editing source code.

---

## Phase 10 — Research Experiments

**Duration: 2–4 weeks**

Run:

- model scaling
- quantization
- open-loop/closed-loop
- resource budgets
- perception comparison
- recovery comparison
- disturbances

Success criterion:

> Statistically meaningful benchmark results.

---

## Phase 11 — Open-source Release

**Duration: 1 week**

Deliver:

- README
- installation guide
- examples
- API docs
- benchmark documentation
- experiment configs
- baseline results
- license
- contribution guide

---

# 37. RTX 3050 Development Plan

Hardware:

```text
RTX 3050 Laptop GPU
4 GB VRAM
16 GB RAM
```

## Good workloads

```text
MuJoCo
CPU simulation
small SLM inference
small VLM inference
quantized models
vision inference
benchmarking
FastAPI
React
SQLite
```

## Avoid initially

```text
large VLM
7B+ FP16 inference
large VLA training
large RL training
large-scale diffusion
full Isaac Sim workflows
```

## Training

If training Phys-SLM:

Use:

- small base model
- LoRA/QLoRA
- small sequence length
- gradient accumulation
- CPU offload where necessary
- small batch size

Large training can happen later on rented/cloud GPU.

---

# 38. First Model Baselines

Start with inference-only baselines.

Example categories:

```text
Baseline 1:
Rule-based planner

Baseline 2:
Small SLM

Baseline 3:
Larger SLM

Baseline 4:
VLM/VLA where hardware permits
```

This lets research separate:

```text
model capability
vs.
system architecture
```

---

# 39. Baseline Agent Types

## Agent A — Open-loop

```text
Instruction
→ Plan
→ Execute
→ Done
```

## Agent B — Closed-loop

```text
Instruction
→ Plan
→ Execute
→ Observe
→ Verify
```

## Agent C — Closed-loop + recovery

```text
Instruction
→ Plan
→ Execute
→ Observe
→ Verify
→ Diagnose
→ Recover
→ Replan
```

These three agents should become primary research baselines.

---

# 40. Failure Taxonomy

Define standard categories.

```text
F01 — Perception failure
F02 — Object grounding failure
F03 — Planning failure
F04 — Invalid action
F05 — Grasp failure
F06 — Placement failure
F07 — Collision
F08 — State estimation failure
F09 — Timeout
F10 — Recovery failure
F11 — Controller failure
F12 — Resource failure
```

Resource failure example:

```text
VRAM > budget
```

This matters because deployment failure can happen before physical action.

---

# 41. Perturbation Taxonomy

Later benchmark:

```text
P01 — Object position
P02 — Object orientation
P03 — Lighting
P04 — Camera noise
P05 — Camera pose
P06 — Instruction variation
P07 — Distractor objects
P08 — Robot initial state
P09 — Object displacement
P10 — Obstacle insertion
```

Each benchmark episode should record perturbation level.

---

# 42. Research Dataset

Do not create giant dataset initially.

Generate structured trajectories:

```text
instruction
observation
world_state
plan
action
result
failure
recovery
final_state
```

Example:

```json
{
  "instruction": "Put red cube in blue box",
  "world_state": {...},
  "plan": [...],
  "action": "GRASP",
  "result": "failure",
  "failure_type": "grasp_failure",
  "recovery": [
    "reposition",
    "retry_grasp"
  ],
  "final_success": true
}
```

Later this can become:

**OpenPhysicalAI Trajectory Dataset**

---

# 43. Future Custom Model

After benchmark infrastructure works, train:

## Phys-SLM

Target:

```text
0.3B–1.7B
```

Tasks:

- physical task decomposition
- structured action planning
- failure diagnosis
- recovery planning

Training pipeline:

```text
Simulator
   |
   v
Task generation
   |
   v
Teacher model
   |
   v
Synthetic demonstrations
   |
   v
SFT / LoRA
   |
   v
Phys-SLM
   |
   v
Benchmark
```

Do not start here.

Benchmark first.

---

# 44. Paper Plan

Potential title:

> **OpenPhysicalAI Lab: A Resource-Aware Evaluation Framework for Reliable Closed-Loop Physical AI**

Alternative:

> **Measuring Physical Intelligence Under Compute Constraints: A Resource-Aware Benchmark for Closed-Loop Agents**

Alternative:

> **How Much Physical Intelligence Fits in 4 GB? Resource-Aware Evaluation of Closed-Loop Physical AI Agents**

Last title is more memorable but should be used only if experiments support it.

---

# 45. Paper Structure

## Abstract

Problem:

Physical AI evaluation often focuses on task success while deployment depends on compute, memory, latency, and reliability.

Method:

OpenPhysicalAI Lab evaluates agents across:

- capability
- efficiency
- failure
- recovery
- resource budget

Results:

Model scale, quantization, closed-loop feedback, and recovery produce measurable trade-offs.

---

## 1. Introduction

Discuss:

- Physical AI growth
- VLA/embodied AI
- simulation benchmarks
- edge deployment
- evaluation fragmentation
- deployment constraints

---

## 2. Related Work

Sections:

### Robot simulation

- MuJoCo
- Isaac Lab
- ManiSkill

### Manipulation benchmarks

- LIBERO
- Meta-World
- BEHAVIOR
- RoboCasa
- VLABench

### Embodied/VLA evaluation

- EmbodiedBench
- vla-eval
- PAI-Bench

### Robustness

- LIBERO-Plus
- RoboTwin-Plus

### Recovery

- LIBERO-Recover
- agentic recovery work

### Efficient VLA

- Lite VLA
- XPU evaluation
- efficient VLA surveys

---

## 3. System

Explain:

```text
Perception
World State
Reasoning
Planning
Action
Verification
Recovery
```

---

## 4. Benchmark

Explain:

- tasks
- environments
- perturbations
- failure taxonomy
- resource profiles
- metrics

---

## 5. Experiments

### E1

Model scaling.

### E2

Quantization.

### E3

Open-loop vs closed-loop.

### E4

Resource budgets.

### E5

Perception quality.

### E6

Recovery.

### E7

Pareto analysis.

---

## 6. Results

Report:

- task success
- recovery success
- latency
- VRAM
- RAM
- action efficiency
- failure distribution
- Pareto frontier

---

## 7. Limitations

Explicitly state:

- simulation-to-real gap
- limited hardware
- limited task diversity
- small model set
- simulator-specific effects

---

## 8. Conclusion

State practical finding:

> Physical AI model quality cannot be evaluated only by task success. Deployment requires capability-resource-reliability analysis.

---

# 46. Figures Needed

## Figure 1 — OpenPhysicalAI architecture

```text
Instruction
→ Perception
→ World State
→ Reasoning
→ Planning
→ Action
→ Observation
→ Verification
→ Recovery
```

## Figure 2 — System workflow

User → Task → Agent → Simulator → Benchmark → Report.

## Figure 3 — Resource-aware evaluation loop

Show:

```text
VRAM
RAM
Latency
FPS
Energy
```

around agent.

## Figure 4 — Model scaling

Success vs model size.

## Figure 5 — Memory/latency trade-off

Success vs VRAM.

## Figure 6 — Quantization

Performance degradation vs compression.

## Figure 7 — Open-loop vs closed-loop

Task success under clean and perturbed environments.

## Figure 8 — Recovery

Recovery success by failure type.

## Figure 9 — Pareto frontier

Capability vs resource cost.

## Figure 10 — Failure distribution

Pie/bar chart:

- perception
- planning
- grasp
- placement
- collision
- timeout
- recovery

---

# 47. Expected Research Result

Do not assume exact results before experiments.

Potential outcome:

```text
Small models:
low resource cost
lower capability

Medium models:
best trade-off

Large models:
higher capability
higher latency/memory

Quantization:
lower resource cost
possible capability degradation

Closed-loop:
better robustness

Recovery:
higher success under disturbances
additional latency/actions
```

These are hypotheses, not claims.

---

# 48. What Would Count as Strong Result?

Strong result does not mean:

> Our model has highest success.

Better result:

> A 0.6B quantized agent achieves near-large-model task performance while using substantially less memory and latency, especially when paired with closed-loop verification and recovery.

Or:

> Closed-loop recovery improves robustness enough to compensate for using smaller models under a fixed 4 GB deployment budget.

Or:

> Model scaling gives diminishing returns beyond a certain resource budget for selected manipulation tasks.

Any of these could produce useful research if statistically supported.

---

# 49. Statistical Evaluation

Do not report:

```text
Model A = 82%
Model B = 79%
```

without uncertainty.

Use:

- multiple seeds
- multiple episodes
- confidence intervals
- bootstrap where suitable
- paired comparisons where possible

For 100 episodes:

```text
Success = 82 / 100
```

report confidence interval.

For paired episode comparisons, use appropriate paired statistical test.

---

# 50. Reproducibility Standard

Every paper result must map to:

```text
configs/
experiments/
results/
```

Example:

```text
experiments/
├── model_scaling.yaml
├── quantization.yaml
├── closed_loop.yaml
├── recovery.yaml
└── resource_budget.yaml
```

Anyone should be able to run:

```bash
openphys experiment --config experiments/model_scaling.yaml
```

and reproduce result.

---

# 51. Open-source Strategy

Repository should contain:

```text
Core framework
Simulation environments
Benchmark tasks
Experiment configs
Evaluation scripts
Baseline implementations
Documentation
Result schemas
```

Models can be hosted separately if licensing/storage requires it.

Dataset can be released through Hugging Face.

Paper code should be tagged by release version.

---

# 52. Documentation

Required docs:

```text
docs/
├── getting-started.md
├── architecture.md
├── agent-api.md
├── environment-api.md
├── model-api.md
├── benchmark.md
├── metrics.md
├── resource-profiling.md
├── recovery.md
├── experiments.md
├── contributing.md
└── hardware.md
```

---

# 53. Testing

Unit tests:

```text
world state
action schema
action validator
task definitions
metrics
resource parser
failure classifier
```

Integration tests:

```text
environment
→ agent
→ action
→ observation
→ verifier
```

Benchmark smoke test:

```text
10 episodes
```

Full benchmark:

```text
50–100 episodes/task
```

---

# 54. CI

GitHub Actions should eventually run:

```text
lint
unit tests
API tests
environment smoke test
benchmark smoke test
documentation build
```

Do not run full GPU benchmark in every CI job.

---

# 55. Versioning

Use semantic versioning.

```text
v0.1.0
```

for first usable prototype.

```text
v0.2.0
```

for closed-loop benchmark.

```text
v0.5.0
```

for research-ready framework.

```text
v1.0.0
```

when APIs and benchmark protocol are stable.

---

# 56. Long-Term Roadmap

## V1

Local simulation laboratory.

## V2

Multiple simulators.

## V3

More VLA/SLM models.

## V4

Custom Phys-SLM.

## V5

Real robot adapters.

## V6

Edge hardware benchmark.

Potential devices:

- Android phone
- Raspberry Pi
- Jetson
- Qualcomm edge device
- AMD/NVIDIA edge hardware

---

# 57. Long-Term Research Direction

OpenPhysicalAI could eventually become:

```text
Physical AI
    |
    +-- Capability
    |
    +-- Efficiency
    |
    +-- Reliability
    |
    +-- Recovery
    |
    +-- Safety
    |
    +-- Deployment
```

Potential future benchmark:

## OPAI-Bench

A benchmark suite specifically for:

> **Resource-aware, reliable, closed-loop Physical AI.**

But do not launch OPAI-Bench before validating OpenPhysicalAI Lab infrastructure.

---

# 58. Important Design Principle

Do not replace existing ecosystems.

Integrate them.

```text
LIBERO
Meta-World
ManiSkill
RoboCasa
BEHAVIOR
VLABench
```

should eventually become possible environments/tasks.

OpenPhysicalAI Lab becomes evaluation layer.

This avoids rebuilding years of existing work.

---

# 59. Competitive Position

Existing systems mainly specialize in:

```text
Simulation
Benchmarking
VLA models
Robustness
Recovery
Hardware evaluation
```

OpenPhysicalAI Lab should combine these around one practical deployment question:

> **What Physical AI system gives best reliable capability under a fixed resource budget?**

That is project identity.

---

# 60. What Not to Claim

Never claim:

```text
"First Physical AI benchmark"
```

Never claim:

```text
"First VLA evaluation platform"
```

Never claim:

```text
"First recovery benchmark"
```

Never claim:

```text
"First resource-efficient VLA"
```

Use precise claim:

> OpenPhysicalAI Lab provides a local-first experimental framework for jointly evaluating Physical AI capability, resource consumption, and recovery behavior under explicit deployment budgets.

---

# 61. First 30-Day Plan

## Week 1

### Day 1

- Create repository.
- Create Python package.
- Define APIs.
- Install MuJoCo.
- Run first robot.

### Day 2

- Add camera.
- Add objects.
- Create scene.

### Day 3

- Implement deterministic controller.
- Pick cube.
- Place cube.

### Day 4

- Environment API.
- Reset.
- Observe.
- Execute.
- Success.

### Day 5

- Task API.
- Config system.
- Basic tests.

---

## Week 2

### Day 6–7

- World state.
- Oracle perception.

### Day 8–9

- Camera pipeline.
- Vision perception.

### Day 10

- Local model runtime.

### Day 11–12

- Structured planning.

### Day 13

- Action validator.

### Day 14

- Agent integration.

---

## Week 3

### Day 15–16

- Closed-loop observation.

### Day 17

- Success verifier.

### Day 18

- Failure injection.

### Day 19

- Failure classification.

### Day 20

- Recovery.

### Day 21

- Replanning.

---

## Week 4

### Day 22–24

Create five benchmark tasks.

### Day 25

Benchmark runner.

### Day 26

Resource profiler.

### Day 27

Experiment database.

### Day 28

Model comparison.

### Day 29

Initial dashboard.

### Day 30

Run first complete experiment.

---

# 62. First Milestone

Do not call project MVP complete until this works:

```text
User starts OpenPhysicalAI Lab
        |
        v
Selects:
Task = Pick & Place
Model = Small local SLM
Budget = 4 GB VRAM
        |
        v
Simulation starts
        |
        v
Agent observes environment
        |
        v
Agent creates plan
        |
        v
Robot executes
        |
        v
Failure injected
        |
        v
Agent detects failure
        |
        v
Agent recovers
        |
        v
Task succeeds
        |
        v
Report generated
```

Report:

```text
Task Success
Recovery Success
Latency
VRAM
RAM
Actions
Retries
Failure Type
Budget Compliance
```

This is first real OpenPhysicalAI Lab milestone.

---

# 63. First Research Experiment

Use one task first.

Compare:

```text
Agent A:
Open-loop

Agent B:
Closed-loop

Agent C:
Closed-loop + recovery
```

Run:

```text
100 episodes
```

under:

```text
clean environment
+
perturbed environment
```

Measure:

```text
success
failure
recovery
latency
actions
```

If closed-loop recovery produces meaningful improvement, you have first research signal.

---

# 64. Second Research Experiment

Model scaling:

```text
0.6B
1.7B
3B
```

Same:

- tasks
- seeds
- environment
- budget
- evaluation

Measure:

```text
success
latency
VRAM
RAM
recovery
```

Plot Pareto frontier.

---

# 65. Third Research Experiment

Quantization:

```text
FP16
Q8
Q4
```

Compare:

```text
resource savings
vs.
physical capability
```

This fits your existing edge-AI experience.

---

# 66. Fourth Research Experiment

Resource budget:

```text
1 GB
2 GB
4 GB
8 GB
```

Find:

> Minimum resource budget required for target capability.

Example research question:

```text
What minimum VRAM budget is required
to achieve ≥80% task success?
```

That is much more practical than generic benchmark ranking.

---

# 67. Fifth Research Experiment

Failure recovery.

Create:

```text
failed grasp
wrong placement
object displacement
obstacle
perception noise
```

Measure:

```text
failure detection rate
diagnosis accuracy
recovery success
recovery latency
additional actions
```

---

# 68. Final Research Story

Final paper story should look like:

```text
Physical AI models are getting better.
        |
        v
But deployment has constraints.
        |
        v
Benchmark score alone is insufficient.
        |
        v
We build OpenPhysicalAI Lab.
        |
        v
Evaluate capability + resources + reliability.
        |
        v
Run model scaling experiments.
        |
        v
Run quantization experiments.
        |
        v
Run closed-loop/recovery experiments.
        |
        v
Find capability-resource-reliability trade-offs.
        |
        v
Identify deployment-efficient Physical AI systems.
```

---

# 69. Project Success Criteria

OpenPhysicalAI Lab succeeds if:

### Engineering

- local install works
- simulator works
- agent works
- benchmark works
- profiler works
- dashboard works

### Research

- controlled experiments work
- results reproducible
- resource/capability trade-offs measurable
- recovery measurable
- Pareto analysis meaningful

### Open-source

- documented
- easy installation
- modular
- reproducible
- contributors can add models/tasks/environments

### Practical

A user with:

```text
4 GB GPU
16 GB RAM
```

can run useful Physical AI experiments without buying robot hardware.

---

# 70. Final Project Definition

## OpenPhysicalAI Lab

> **A local-first open-source laboratory for evaluating reliable Physical AI under real deployment constraints.**

Core equation:

```text
Physical AI Evaluation
=
Capability
+
Efficiency
+
Reliability
+
Recovery
```

Core constraint:

```text
Compute
+
Memory
+
Latency
+
Failure Budget
```

Core workflow:

```text
Task
 ↓
Perception
 ↓
World State
 ↓
Reasoning
 ↓
Planning
 ↓
Action
 ↓
Observation
 ↓
Verification
 ↓
Recovery
 ↓
Benchmark
 ↓
Deployment Report
```

Core research question:

> **How much reliable physical capability can we obtain under a fixed compute and memory budget?**

Core hardware target:

```text
RTX 3050
4 GB VRAM
16 GB RAM
```

Core first simulator:

```text
MuJoCo
```

Core first model range:

```text
0.3B–3B
```

Core first benchmark:

```text
5 manipulation tasks
+
controlled failures
+
resource constraints
```

Core first paper direction:

> **Resource-Aware Evaluation of Reliable Closed-Loop Physical AI Agents**

---

# 71. Immediate Next Action

Start with **Phase 0 + Phase 1 only**.

Do not build dashboard yet.

Do not train model yet.

Do not add Isaac Lab yet.

First prove:

```text
RTX 3050
    |
    v
MuJoCo
    |
    v
Robot arm
    |
    v
Camera
    |
    v
Pick-and-place
    |
    v
Reliable simulation
```

Once this works, build OpenPhysicalAI abstraction around it.

That keeps project technically grounded and prevents spending weeks building UI around unproven robotics infrastructure.
