"""Reproduce the Phase-1 gate: scripted pick-and-place over 200 random scenes in real MuJoCo."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from openphysicalai import skills
from openphysicalai.sim import ObjSpec, SceneSpec, World

ok, n = 0, 200
for seed in range(n):
    r = random.Random(seed)
    x, y, yaw = r.uniform(0.12, 0.34), r.uniform(-0.22, 0.22), r.uniform(0, math.pi / 2)
    cx, cy = (0.30, 0.17) if y < 0 else (0.30, -0.17)
    if abs(y - cy) < 0.12 and abs(x - cx) < 0.12:
        cx = 0.15
    w = World(SceneSpec([ObjSpec("cube_0", "red", 0.02, (x, y), yaw)], (cx, cy)))
    p = w.obj_pos("cube_0")
    skills.pick(w, p[0], p[1], 0.02, yaw)
    skills.place(w, cx, cy)
    ok += w.in_container("cube_0")
print(f"gate1: {ok}/{n} = {ok/n:.1%}")
