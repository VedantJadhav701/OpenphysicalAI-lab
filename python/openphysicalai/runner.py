"""Episode runner + run orchestration. Single owner of simulator state (this thread). Model inference
is synchronous; in `realtime` mode the world is advanced by the measured inference time (hold policy)
before the plan is applied, so slow models act on stale observations."""
from __future__ import annotations

import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import numpy as np

from . import render as R
from . import skills, tasks
from .budget import PROFILES, evaluate_budget
from .injection import EXPECTED_DIAGNOSIS, Injector
from .perception import OraclePerception, VisionPerception
from .planners import OllamaPlanner, RulePlanner, validate_plan
from .profiler import Profiler, gpu_snapshot
from .sim import World
from .stats import wilson_interval

SLOTS = [(-0.04, -0.04), (0.04, -0.04), (0.0, 0.04), (0.04, 0.04), (-0.04, 0.04)]
LIFT_Z = 0.08
HELD_RANGE = (0.020, 0.042)
PICK_LEAD_S = 1.05   # Calibrated to match 0.65s horizontal move + 0.40s descent to near_gripper capture zone
VERSION = "0.2.2"


class Cancelled(Exception):
    pass


@dataclass
class RunConfig:
    task: str = "pick_place"
    policy: str = "rule"              # "rule" or "ollama:<model>"
    agent: str = "recovery"           # open_loop | closed_loop | recovery
    perception: str = "oracle"        # oracle | vision
    verifier: str = "V1"              # V0 | V1 | V2
    perturb: str = "clean"
    mode: str = "sync"                # sync | realtime
    episodes: int = 50
    seed: int = 0
    budget: str = "standard"
    extra_latency_ms: float = 0.0     # explicit synthetic latency added to each plan (for latency-tax sweeps)
    velocity_lead: bool = True        # predictive velocity lead compensation
    max_attempts: int = 3
    ollama_host: str = "http://127.0.0.1:11434"
    frames: bool = True
    camera_mode: str = "3d"
    label: str = ""
    resume_from: Optional[str] = None

    @staticmethod
    def from_dict(d: Dict) -> "RunConfig":
        base = RunConfig()
        for k, v in d.items():
            if hasattr(base, k):
                cur = getattr(base, k)
                if isinstance(cur, bool):
                    setattr(base, k, bool(v) if not isinstance(v, str) else v.lower() in ("true", "1"))
                elif isinstance(cur, str):
                    setattr(base, k, str(v))
                else:
                    setattr(base, k, type(cur)(v))
        base.episodes = max(1, min(int(base.episodes), 2000))
        return base


_active_run = {"w": None, "inj": None, "pokes": []}


def poke(action: str) -> bool:
    """Queues an interactive user perturbation to be executed safely on the MuJoCo owner thread."""
    if not _active_run.get("w"):
        return False
    if action in ("slip", "nudge", "step"):
        _active_run["pokes"].append(action)
        return True
    return False


def _drain_pokes(w: World, inj: Optional[Injector] = None):
    while _active_run["pokes"]:
        action = _active_run["pokes"].pop(0)
        if action == "slip":
            w.set_gripper(0.0)
            if inj is not None:
                inj.log.append({"type": "grasp_slip", "step": w.sim_steps, "manual": True})
        elif action == "nudge":
            for o in w.spec.objects:
                if not w.in_container(o.oid):
                    w.teleport(o.oid, 0.0, 0.045)
                    if inj is not None:
                        inj.log.append({"type": "object_displaced", "step": w.sim_steps, "object": o.oid, "manual": True})
                    break
        elif action == "step":
            w.step(20)


def make_planner(cfg: RunConfig):
    if cfg.policy == "rule":
        return RulePlanner()
    if cfg.policy.startswith("ollama:"):
        return OllamaPlanner(cfg.policy.split(":", 1)[1], cfg.ollama_host)
    raise ValueError(f"unknown policy {cfg.policy}")


class FrameEmitter:
    def __init__(self, world_ref: Dict, emit: Optional[Callable], cancel, enabled: bool, camera_mode: str = "3d", min_dt: float = 0.10):
        self.w, self.emit, self.cancel, self.enabled = world_ref, emit, cancel, enabled
        self.camera_mode, self.min_dt = camera_mode, min_dt
        self.last = 0.0
        self.tick_count = 0
        self._last_gpu = 0.0
        self.extra: Dict = {}

    def __call__(self):
        if self.cancel is not None and self.cancel.is_set():
            raise Cancelled()
        w = self.w["w"]
        _drain_pokes(w, _active_run.get("inj"))
        if not (self.enabled and self.emit):
            return
        now = time.perf_counter()
        if now - self.last < self.min_dt:
            return
        self.last = now
        self.tick_count += 1
        qpos_list = [round(float(w.data.qpos[jid]), 2) for jid in w.jid] if hasattr(w, "jid") else [0.0, -0.45, 0.82, -0.37, 0.0]
        extra = {}
        if now - self._last_gpu >= 1.0:
            self._last_gpu = now
            try:
                extra["gpu"] = gpu_snapshot()
            except Exception:  # noqa: BLE001
                pass
        payload = {
            "event": "frame",
            "png": R.png_b64(R.render_3d(w)),
            "qpos": qpos_list,
            "gripper": round(w.finger_closure(), 3),
            "sim_time": round(w.time, 1),
            **extra,
            **self.extra,
        }
        # Only encode 2D orthographic PNG when viewing ortho or every 3rd frame to save CPU
        if self.camera_mode == "ortho" or self.tick_count % 3 == 1:
            payload["ortho_png"] = R.png_b64(R.render_2d(w, draw_arm=True))
        self.emit(payload)


def _sim_id(w: World, ws_obj: Dict) -> Optional[str]:
    """Ground-truth id of the simulator object the agent's estimate refers to (for scoring/injection only)."""
    best, bd = None, 1e9
    for o in w.spec.objects:
        if o.color != ws_obj["color"]:
            continue
        p = w.obj_pos(o.oid)
        d = math.hypot(p[0] - ws_obj["x"], p[1] - ws_obj["y"])
        if d < bd:
            best, bd = o.oid, d
    return best


def _vision_count_in_container(w: World, rng, pix_noise) -> int:
    ws = VisionPerception(rng, pix_noise).perceive(w)
    return sum(1 for o in ws["objects"] if o["in_container"])


def run_episode(cfg: RunConfig, seed: int, planner, budget_ms: float, frame_hook_factory, cancel) -> Dict:
    inst = tasks.generate(cfg.task, seed)
    w = World(inst.spec)
    holder = {"w": w}
    _active_run["w"] = w
    hook = frame_hook_factory(holder)
    rng = np.random.default_rng(seed + 1)
    inj = Injector(cfg.perturb, np.random.default_rng(seed + 2))
    _active_run["inj"] = inj
    perc = OraclePerception(rng, inj.pos_noise) if cfg.perception == "oracle" else VisionPerception(rng, inj.pix_noise)
    closed = cfg.agent in ("closed_loop", "recovery")
    ep = {"seed": seed, "task": cfg.task, "plans": 0, "plan_latencies_ms": [], "plan_errors": [], "actions": 0, "replans": 0,
          "verif_fail": 0, "false_alarms": 0, "missed": 0, "verifs": 0, "deadline_miss": 0, "staleness_s": [],
          "events": [], "failure": None, "tok_per_s": []}
    attempts = 0
    placed_ok = 0
    outcome = "ok"
    gid = 0
    try:
        while w.time < inst.time_limit:
            ws = perc.perceive(w)
            t_obs = w.time
            idmap = {o["id"]: _sim_id(w, o) for o in ws["objects"]}
            pr = planner.plan(inst.instruction, ws)
            lat = pr.latency_ms + cfg.extra_latency_ms
            ep["plans"] += 1
            ep["plan_latencies_ms"].append(lat)
            if lat > budget_ms:
                ep["deadline_miss"] += 1
            if pr.meta.get("tok_per_s"):
                ep["tok_per_s"].append(pr.meta["tok_per_s"])
            if cfg.mode == "realtime" and lat > 0:
                w.hold(lat / 1000.0, hook)          # world keeps moving while the model thinks
            verr = pr.error or validate_plan(pr.plan, ws)
            if verr:
                ep["plan_errors"].append(str(verr))
                outcome = "planning"
                attempts += 1
                if cfg.agent == "recovery" and attempts <= cfg.max_attempts:
                    ep["replans"] += 1
                    continue
                break
            ep["staleness_s"].append(round(w.time - t_obs, 3))
            holding_id = None
            failed_step = False
            i = 0
            while i < len(pr.plan):
                step = pr.plan[i]
                ep["actions"] += 1
                gid += 1
                if step["action"] == "pick":
                    o = next(o for o in ws["objects"] if o["id"] == step["object"])
                    sid = idmap.get(o["id"])
                    ev_before = len(inj.log)
                    if sid:
                        inj.displace(w, sid, gid)
                    slip = inj.slip(gid)
                    x, y = o["x"], o["y"]
                    if getattr(cfg, "velocity_lead", True) and o.get("velocity_y"):
                        y += o["velocity_y"] * ((w.time - t_obs) + PICK_LEAD_S)
                    y = min(max(y, -0.25), 0.25)
                    res = skills.pick(w, x, y, o["half_size"], o.get("yaw", 0.0), hook,
                                      drop_hook=(lambda: (w.set_gripper(0.0), w.settle(0.4))) if slip else None)
                    holding_id = sid
                    if not res.ok:
                        outcome = "controller"
                    if closed:
                        cl = w.finger_closure()
                        truth_ok = bool(sid) and w.obj_pos(sid)[2] > LIFT_Z
                        if cfg.verifier == "V0":
                            flag_ok = truth_ok
                        else:
                            flag_ok = HELD_RANGE[0] <= cl <= HELD_RANGE[1]
                        ep["verifs"] += 1
                        if not flag_ok and truth_ok:
                            ep["false_alarms"] += 1
                        if flag_ok and not truth_ok:
                            ep["missed"] += 1
                        for e in inj.log[ev_before:]:
                            e["detected"] = not flag_ok
                            e["diagnosis"] = ("object_dropped" if cl < HELD_RANGE[0] else "grasp_miss" if cl > HELD_RANGE[1] else "wrong_object") if not flag_ok else None
                        if not flag_ok:
                            ep["verif_fail"] += 1
                            failed_step = True
                            skills.go_home(w, hook)
                            break
                else:  # place
                    ev_before = len(inj.log)
                    cx, cy = ws["container"]["x"], ws["container"]["y"]
                    ox, oy = SLOTS[placed_ok % len(SLOTS)]
                    mx, my = inj.placement_offset(gid)
                    res = skills.place(w, cx + ox + mx, cy + oy + my, hook)
                    if not res.ok:
                        outcome = "controller"
                    if closed:
                        truth_ok = bool(holding_id) and w.in_container(holding_id)
                        if cfg.verifier == "V0":
                            flag_ok = truth_ok
                        elif cfg.verifier == "V1":
                            flag_ok = w.finger_closure() < 0.005          # proprio only: cannot see where it landed
                        else:
                            cnt = _vision_count_in_container(w, np.random.default_rng(seed + 100 + gid), inj.pix_noise)
                            flag_ok = cnt >= placed_ok + 1
                        ep["verifs"] += 1
                        if not flag_ok and truth_ok:
                            ep["false_alarms"] += 1
                        if flag_ok and not truth_ok:
                            ep["missed"] += 1
                        for e in inj.log[ev_before:]:
                            e["detected"] = not flag_ok
                            e["diagnosis"] = "wrong_placement" if not flag_ok else None
                        if not flag_ok:
                            ep["verif_fail"] += 1
                            failed_step = True
                            skills.go_home(w, hook)
                            break
                    if holding_id and w.in_container(holding_id):
                        placed_ok += 1
                    holding_id = None
                i += 1
            skills.go_home(w, hook)
            if failed_step:
                attempts += 1
                if cfg.agent == "recovery" and attempts <= cfg.max_attempts:
                    ep["replans"] += 1
                    continue
                outcome = "detected_abort" if cfg.agent == "closed_loop" else "recovery_exhausted"
                break
            break
    except Cancelled:
        raise
    finally:
        w.close()
    ok = tasks.oracle_success(w, inst)
    if w.time >= inst.time_limit and not ok:
        outcome = "timeout"
    ep["success"] = bool(ok)
    ep["sim_time_s"] = round(w.time, 1)
    ep["events"] = inj.log
    if not ok:
        ep["failure"] = outcome if outcome != "ok" else ("placement_or_grasp" if inj.log else "task_wrong")
    for e in ep["events"]:
        e["recovered"] = bool(ok and e.get("detected"))
        e["diag_correct"] = (e.get("diagnosis") == EXPECTED_DIAGNOSIS.get(e["type"])) if e.get("detected") else None
    return ep


def _pct(a, q):
    return float(np.percentile(a, q)) if len(a) else 0.0


def summarize(cfg: RunConfig, eps: List[Dict], prof: Dict, gpu_present: bool) -> Dict:
    n = len(eps)
    k = sum(e["success"] for e in eps)
    lats = [l for e in eps for l in e["plan_latencies_ms"]]
    events = [ev for e in eps for ev in e["events"]]
    det = [ev for ev in events if ev.get("detected") is not None]
    verifs = sum(e["verifs"] for e in eps)
    fails = {}
    for e in eps:
        if e["failure"]:
            fails[e["failure"]] = fails.get(e["failure"], 0) + 1
    toks = [t for e in eps for t in e["tok_per_s"]]
    m = {
        "episodes": n, "successes": k, "tsr": k / n, "tsr_ci": list(wilson_interval(k, n)),
        "latency_ms": {"p50": _pct(lats, 50), "p95": _pct(lats, 95), "p99": _pct(lats, 99), "mean": float(np.mean(lats)) if lats else 0.0},
        "deadline_miss_rate": sum(e["deadline_miss"] for e in eps) / max(1, len(lats)),
        "staleness_s_mean": float(np.mean([s for e in eps for s in e["staleness_s"]])) if any(e["staleness_s"] for e in eps) else 0.0,
        "plans_per_episode": float(np.mean([e["plans"] for e in eps])),
        "actions_per_episode": float(np.mean([e["actions"] for e in eps])),
        "sim_time_s_mean": float(np.mean([e["sim_time_s"] for e in eps])),
        "failures_injected": len(events),
        "detection_rate": (sum(1 for ev in det if ev["detected"]) / len(det)) if det else None,
        "recovery_rate": (sum(1 for ev in det if ev["detected"] and ev["recovered"]) / max(1, sum(1 for ev in det if ev["detected"]))) if any(ev.get("detected") for ev in det) else None,
        "diagnosis_accuracy": (lambda c: (sum(c) / len(c)) if c else None)([ev["diag_correct"] for ev in det if ev.get("diag_correct") is not None]),
        "false_alarm_rate": (sum(e["false_alarms"] for e in eps) / verifs) if verifs else None,
        "missed_failure_rate": (sum(e["missed"] for e in eps) / verifs) if verifs else None,
        "failure_breakdown": fails,
        "tokens_per_s_mean": float(np.mean(toks)) if toks else None,
        "energy_j_per_episode": (prof["energy_j"] / n) if prof.get("energy_j") is not None else None,
    }
    b = PROFILES[cfg.budget]
    obs = {"vram_process_peak_gb": prof.get("vram_process_peak_gb"), "vram_device_peak_gb": prof.get("vram_device_peak_gb"),
           "ram_process_peak_gb": prof.get("ram_process_peak_gb"), "ram_system_peak_gb": prof.get("ram_system_peak_gb"),
           "planning_ms_p95": m["latency_ms"]["p95"]}
    na = () if gpu_present else ("vram_process_peak_gb", "vram_device_peak_gb")
    res = evaluate_budget(b, obs, na)
    budget = {"profile": cfg.budget, "pass": res.passed,
              "checks": [{"name": c.name, "value": c.value, "cap": c.cap, "ok": c.ok, "note": c.note} for c in res.checks]}
    return {"metrics": m, "budget": budget}


def run(cfg: RunConfig, emit: Optional[Callable[[Dict], None]] = None, cancel=None) -> Dict:
    planner = make_planner(cfg)
    gpu = gpu_snapshot()
    if hasattr(planner, "warmup"):
        if emit:
            emit({"event": "log", "line": f"warming up {planner.name} ..."})
        planner.warmup()
    budget_ms = PROFILES[cfg.budget].planning_ms_p95
    fe_holder = {}
    def factory(world_ref):
        fe = FrameEmitter(world_ref, emit, cancel, cfg.frames, camera_mode=cfg.camera_mode)
        fe_holder["fe"] = fe
        return fe
    prof = Profiler().start()
    eps: List[Dict] = []
    completed_seeds = set()
    if cfg.resume_from and os.path.isfile(cfg.resume_from):
        try:
            with open(cfg.resume_from, "r") as f:
                prev_data = json.load(f)
            prev_eps = prev_data.get("episodes_detail", [])
            for ep in prev_eps:
                eps.append(ep)
                if "seed" in ep:
                    completed_seeds.add(ep["seed"])
            if emit:
                emit({"event": "log", "line": f"Resuming: loaded {len(prev_eps)} episodes from {cfg.resume_from}"})
        except Exception as e:  # noqa: BLE001
            if emit:
                emit({"event": "log", "line": f"Warning: could not load resume file {cfg.resume_from}: {e}"})

    t0 = time.perf_counter()
    try:
        for i in range(cfg.episodes):
            target_seed = cfg.seed + i
            if target_seed in completed_seeds:
                continue
            ep = run_episode(cfg, target_seed, planner, budget_ms, factory, cancel)
            eps.append(ep)
            if emit:
                k = sum(e["success"] for e in eps)
                emit({"event": "progress", "done": len(eps), "total": cfg.episodes, "successes": k, "last_ok": ep["success"]})
    except Cancelled:
        prof.stop()
        if emit:
            emit({"event": "cancelled"})
        return {}
    finally:
        _active_run["w"] = None
        _active_run["inj"] = None
        _active_run["pokes"] = []
    eps.sort(key=lambda e: e.get("seed", 0))
    pr = prof.stop().as_dict()
    summ = summarize(cfg, eps, pr, gpu is not None)
    return {"id": "run_" + uuid.uuid4().hex[:10], "created": datetime.now(timezone.utc).isoformat(), "version": VERSION,
            "config": asdict(cfg), "policy_name": planner.name, "track": planner.track, "assist": "A3",
            "profile": pr, "wall_s": round(time.perf_counter() - t0, 1), **summ, "episodes_detail": eps}
