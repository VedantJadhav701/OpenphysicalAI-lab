# Contributing to OpenPhysicalAI Lab

Thank you for your interest in contributing to **OpenPhysicalAI Lab**! We welcome contributions to robotics physics simulation, latency-coupled planning, verifier honesty evaluations, and budget profiling.

---

## 🧭 Code of Conduct
We are committed to providing a welcoming, inclusive, and harassment-free experience for everyone. Be respectful, constructive, and honest in all data reporting.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/VedantJadhav701/OpenphysicalAI-lab.git
   cd OpenphysicalAI-lab
   ```

2. **Python Environment Setup**:
   ```bash
   conda create -n opai python=3.11 -y
   conda activate opai
   pip install -e python
   ```

3. **Verify the Physics Engine Gate**:
   ```bash
   python python/gate1.py
   # Expected: gate1: 200/200 = 100.0%
   ```

4. **Run the Test Suite**:
   ```bash
   pytest python/tests
   ```

5. **Desktop App Setup**:
   ```bash
   npm install
   npm start
   ```

---

## 📊 Scientific Integrity & Benchmark Guidelines

1. **Always report $N$ and 95% Confidence Intervals**:
   - Single-run numbers are invalid. When presenting Task Success Rates (TSR), always provide the sample size ($N \ge 50$ for benchmark claims) and Wilson score interval.
2. **Real Hardware Data**:
   - Run `opai doctor` and include the system specs (GPU model, total VRAM, platform, driver info) alongside any budget card submission.
3. **Reproducibility**:
   - All benchmark results must include the exact CLI command used to reproduce them (e.g. `opai run --task pick_place --seed 42 ...`).
4. **Distinguish Ground Truth from Perception**:
   - `V0` is a simulator oracle. Never claim real-world autonomy based on `V0` scores; report `V1` (proprioception) and `V2` (vision).

---

## 🚀 Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-enhancement`.
2. Ensure `gate1.py` passes 200/200 and all unit tests pass:
   ```bash
   python python/gate1.py
   pytest python/tests
   ```
3. Commit with conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`).
4. Open a Pull Request with a clear description and any relevant Budget Cards.
