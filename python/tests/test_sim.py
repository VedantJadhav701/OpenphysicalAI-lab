import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openphysicalai import skills, tasks  # noqa: E402
from openphysicalai.runner import RunConfig, run  # noqa: E402
from openphysicalai.sim import ObjSpec, SceneSpec, World  # noqa: E402


def test_scene_generation_is_deterministic():
    assert tasks.generate("spatial", 39).spec.objects[0].pos == tasks.generate("spatial", 39).spec.objects[0].pos


def test_scripted_pick_place_gate():
    """Phase-1 gate (reduced): real MuJoCo pick-and-place >= 95% over 40 random scenes."""
    ok, n = 0, 40
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
    assert ok / n >= 0.95


def test_end_to_end_run_clean():
    res = run(RunConfig(task="pick_place", agent="recovery", perception="vision", perturb="clean", episodes=10, frames=False))
    assert res["metrics"]["tsr"] >= 0.8 and res["metrics"]["episodes"] == 10
