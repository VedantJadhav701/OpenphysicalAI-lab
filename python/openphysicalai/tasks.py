"""OPAI-Core v0.1 task generators. Each task returns a scene, an instruction and a goal
used ONLY by the evaluation oracle (never shown to the agent)."""
from __future__ import annotations

import math
import random
import zlib
from dataclasses import dataclass
from typing import Dict, List

from .sim import CONTAINER_HALF_IN, WORKSPACE, ObjSpec, SceneSpec

TASKS: Dict[str, str] = {
    "pick_place": "Pick & Place",
    "smallest": "Select smallest",
    "spatial": "Spatial (left of)",
    "multi": "Multi-object (all red)",
    "dynamic": "Dynamic (moving cube)",
}
CONVEYOR_SPEED = 0.02   # m/s along +y
CLEAR = 0.15            # min distance cube<->container centre (finger/wall clearance)


@dataclass
class TaskInstance:
    task: str
    instruction: str
    spec: SceneSpec
    targets: List[str]        # object ids that must end inside the container
    forbidden: List[str]      # object ids that must NOT end inside the container
    time_limit: float = 150.0


def _sample(rng: random.Random, n: int, avoid, min_sep=0.10, xr=(0.12, 0.34), yr=(-0.22, 0.22)):
    pts = []
    tries = 0
    while len(pts) < n and tries < 2000:
        tries += 1
        p = (rng.uniform(*xr), rng.uniform(*yr))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= min_sep for q in pts + avoid):
            pts.append(p)
    if len(pts) < n:
        raise RuntimeError("scene sampling failed")
    return pts


def _container(rng: random.Random):
    return (rng.choice([0.28, 0.32]), rng.choice([-1, 1]) * rng.uniform(0.17, 0.21))


def generate(task: str, seed: int) -> TaskInstance:
    rng = random.Random(seed * 7919 + zlib.crc32(task.encode()) % 1000)   # stable across processes (str hash() is randomized)
    c = _container(rng)
    avoid = [c]
    # keep objects >= 0.15 from container centre
    def pts(n, **kw):
        out, tries = [], 0
        while len(out) < n and tries < 200:
            tries += 1
            try:
                cand = _sample(rng, n, avoid + [(c[0], c[1])] * 1, **kw)
            except RuntimeError:
                continue
            if all(math.hypot(p[0] - c[0], p[1] - c[1]) > CLEAR for p in cand):
                return cand
        raise RuntimeError("scene sampling failed")

    yaw = lambda: rng.uniform(0, math.pi / 2)
    if task == "pick_place":
        p = pts(3)
        cols = ["red", rng.choice(["green", "yellow"]), rng.choice(["orange", "green", "yellow"])]
        if cols[1] == cols[2]:
            cols[2] = "orange" if cols[1] != "orange" else "green"
        objs = [ObjSpec(f"cube_{i}", cols[i], 0.02, p[i], yaw()) for i in range(3)]
        return TaskInstance(task, "Put the red cube in the blue container.", SceneSpec(objs, c), ["cube_0"], ["cube_1", "cube_2"])
    if task == "smallest":
        p = pts(3)
        cols = rng.sample(["red", "green", "yellow", "orange"], 3)
        halves = [0.015, 0.02, 0.025]
        rng.shuffle(halves)
        objs = [ObjSpec(f"cube_{i}", cols[i], halves[i], p[i], yaw()) for i in range(3)]
        t = min(range(3), key=lambda i: halves[i])
        return TaskInstance(task, "Put the smallest cube in the blue container.", SceneSpec(objs, c), [f"cube_{t}"], [f"cube_{i}" for i in range(3) if i != t])
    if task == "spatial":
        for _ in range(2000):
            if _ % 200 == 199:
                c = _container(rng)
            rx = rng.uniform(0.15, 0.32)
            ry = rng.uniform(-0.06, 0.06)
            tgt = (rx + rng.uniform(-0.03, 0.03), ry + rng.uniform(0.12, 0.15))
            dis = (rx + rng.uniform(-0.03, 0.03), ry - rng.uniform(0.12, 0.15))
            ok = all(math.hypot(q[0] - c[0], q[1] - c[1]) > CLEAR for q in [(rx, ry), tgt, dis])
            if ok and abs(tgt[1]) < 0.24 and abs(dis[1]) < 0.24:
                break
        else:
            raise RuntimeError("spatial sampling failed")
        objs = [ObjSpec("cube_0", "red", 0.02, tgt, yaw()), ObjSpec("cube_1", "yellow", 0.02, (rx, ry), yaw()), ObjSpec("cube_2", "green", 0.02, dis, yaw())]
        rng.shuffle(objs)
        return TaskInstance(task, "Put the cube to the left of the yellow cube in the blue container. Left means larger y.",
                            SceneSpec(objs, c), [o.oid for o in objs if o.color == "red"], [o.oid for o in objs if o.color == "green"])
    if task == "multi":
        n_red = rng.choice([2, 3])
        n_other = 2
        p = pts(n_red + n_other, min_sep=0.09)
        objs = [ObjSpec(f"cube_{i}", "red", 0.02, p[i], yaw()) for i in range(n_red)]
        objs += [ObjSpec(f"cube_{n_red+j}", rng.choice(["green", "yellow"]), 0.02, p[n_red + j], yaw()) for j in range(n_other)]
        return TaskInstance(task, "Put all red cubes in the blue container.", SceneSpec(objs, c),
                            [f"cube_{i}" for i in range(n_red)], [f"cube_{n_red+j}" for j in range(n_other)], 220.0)
    if task == "dynamic":
        y0 = rng.uniform(-0.22, -0.12)
        x0 = rng.uniform(0.16, 0.30)
        cc = (0.30, 0.19) if rng.random() < 0.5 else (0.16, 0.19)
        d = (x0 + rng.choice([-1, 1]) * 0.12, rng.uniform(-0.2, 0.0))
        if abs(d[0] - 0.22) > 0.15:
            d = (0.22, d[1])
        objs = [ObjSpec("cube_0", "red", 0.02, (x0, y0), yaw(), (0.0, CONVEYOR_SPEED)), ObjSpec("cube_1", "green", 0.02, (d[0], max(-0.2, min(0.02, d[1]))), yaw())]
        if math.hypot(objs[1].pos[0] - x0, objs[1].pos[1] - y0) < 0.10:
            objs[1].pos = (x0, y0 + 0.18)
        return TaskInstance(task, "Put the red cube, which is moving, in the blue container.", SceneSpec(objs, cc), ["cube_0"], ["cube_1"])
    raise ValueError(f"unknown task {task}")


def oracle_success(world, inst: TaskInstance) -> bool:
    return all(world.in_container(t) for t in inst.targets) and not any(world.in_container(f) for f in inst.forbidden)
