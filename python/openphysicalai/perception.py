"""Perception: Oracle (simulator truth + optional noise) and Vision (colour segmentation on the
software top-down image with Alpha-Beta temporal velocity tracking). Both return the same WorldState dict."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import render as R
from .sim import CONTAINER_HALF_IN, World


def _in_box(x, y, c):
    return abs(x - c[0]) < CONTAINER_HALF_IN and abs(y - c[1]) < CONTAINER_HALF_IN


@dataclass
class TrackedObjectState:
    pos: np.ndarray
    vel: np.ndarray
    sim_time: float
    samples: int = 1


class TemporalVelocityTracker:
    """Lightweight Alpha-Beta kinematic filter for VisionPerception.
    Estimates 3D object velocity (vx, vy, vz) purely from sequential
    top-down colour-segmentation centroids without touching MuJoCo qvel."""

    def __init__(
        self,
        alpha: float = 0.75,
        beta: float = 0.45,
        max_speed_mps: float = 0.50,
        min_dt: float = 1e-3,
        max_dt: float = 5.0,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.max_speed_mps = max_speed_mps
        self.min_dt = min_dt
        self.max_dt = max_dt
        self._tracks: Dict[str, TrackedObjectState] = {}

    def reset(self) -> None:
        self._tracks.clear()

    def update(
        self, obj_id: str, measured_pos: np.ndarray, sim_time: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        pos = np.asarray(measured_pos, dtype=np.float64)
        if obj_id not in self._tracks:
            self._tracks[obj_id] = TrackedObjectState(
                pos=pos.copy(),
                vel=np.zeros(3, dtype=np.float64),
                sim_time=sim_time,
                samples=1,
            )
            return pos.copy(), np.zeros(3, dtype=np.float64)

        prev = self._tracks[obj_id]
        dt = sim_time - prev.sim_time

        if dt < self.min_dt or dt > self.max_dt:
            self._tracks[obj_id] = TrackedObjectState(
                pos=pos.copy(),
                vel=prev.vel.copy() if abs(dt) < self.min_dt else np.zeros(3, dtype=np.float64),
                sim_time=sim_time,
                samples=prev.samples + 1,
            )
            return pos.copy(), self._tracks[obj_id].vel.copy()

        pred_pos = prev.pos + prev.vel * dt
        residual = pos - pred_pos

        new_pos = pred_pos + self.alpha * residual
        raw_vel = (pos - prev.pos) / dt
        new_vel = prev.vel + (self.beta / dt) * residual if prev.samples > 2 else raw_vel

        speed = float(np.linalg.norm(new_vel[:2]))
        if speed < 0.004:
            new_vel[:] = 0.0
        elif speed > self.max_speed_mps:
            new_vel = new_vel * (self.max_speed_mps / speed)

        new_vel[2] = 0.0

        self._tracks[obj_id] = TrackedObjectState(
            pos=new_pos,
            vel=new_vel,
            sim_time=sim_time,
            samples=prev.samples + 1,
        )
        return new_pos.copy(), new_vel.copy()

    @staticmethod
    def predict_intercept(
        pos: np.ndarray,
        vel: np.ndarray,
        planner_latency_s: float,
        arm_travel_time_s: float = 0.32,
        workspace_bounds: Tuple[Tuple[float, float], Tuple[float, float]] = (
            (0.10, 0.36),
            (-0.25, 0.25),
        ),
    ) -> np.ndarray:
        total_lead_s = max(0.0, float(planner_latency_s)) + max(0.0, float(arm_travel_time_s))
        intercept = np.asarray(pos, dtype=np.float64).copy()
        intercept[:2] += np.asarray(vel[:2], dtype=np.float64) * total_lead_s
        (x_min, x_max), (y_min, y_max) = workspace_bounds
        intercept[0] = float(np.clip(intercept[0], x_min, x_max))
        intercept[1] = float(np.clip(intercept[1], y_min, y_max))
        return intercept


class OraclePerception:
    name = "oracle"

    def __init__(self, rng: np.random.Generator, pos_noise: float = 0.0):
        self.rng, self.pos_noise = rng, pos_noise

    def perceive(self, w: World) -> Dict:
        c = w.spec.container_pos
        objs = []
        for o in w.spec.objects:
            p = w.obj_pos(o.oid)
            n = self.rng.normal(0, self.pos_noise, 2) if self.pos_noise > 0 else (0.0, 0.0)
            x, y = float(p[0] + n[0]), float(p[1] + n[1])
            d = {"id": o.oid, "color": o.color, "half_size": o.half, "x": round(x, 3), "y": round(y, 3),
                 "yaw": round(w.obj_yaw(o.oid), 3), "in_container": bool(w.in_container(o.oid))}
            if np.any(w.vel[o.oid]):
                d["velocity_y"] = float(w.vel[o.oid][1])
            objs.append(d)
        tip = w.tip()
        return {"t": round(w.time, 3), "source": "oracle", "container": {"x": c[0], "y": c[1]},
                "gripper": {"closure": round(w.finger_closure(), 4), "tip": [round(float(v), 3) for v in tip]}, "objects": objs}


def _components(mask: np.ndarray, min_px: int = 30):
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    out = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        q = deque([(r0, c0)])
        seen[r0, c0] = True
        pix = []
        while q:
            r, c = q.popleft()
            pix.append((r, c))
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and mask[rr, cc] and not seen[rr, cc]:
                    seen[rr, cc] = True
                    q.append((rr, cc))
        if len(pix) >= min_px:
            out.append(np.array(pix))
    return out


class VisionPerception:
    name = "vision"

    def __init__(self, rng: np.random.Generator, pixel_noise: float = 0.0, enable_velocity_tracker: bool = True):
        self.rng, self.pixel_noise = rng, pixel_noise
        self.enable_velocity_tracker = enable_velocity_tracker
        self.tracker = TemporalVelocityTracker(alpha=0.80, beta=0.55)

    def _detect_raw(self, w: World) -> List[Dict]:
        img = R.render(w, draw_arm=False, rng=self.rng, noise=self.pixel_noise)
        f = img.astype(np.int32)
        objs: List[Dict] = []
        k = 0
        for color in ("red", "green", "yellow", "orange"):
            ref = np.array(R.PALETTE[color])
            m = (np.abs(f - ref).sum(axis=2) < 60 + 3 * self.pixel_noise)
            for pix in _components(m):
                cy_, cx_ = pix.mean(axis=0)
                x, y = R.px_to_world(cy_ + 0.5, cx_ + 0.5)
                area_m2 = len(pix) * R.RES_X * R.RES_Y
                half = math.sqrt(area_m2) / 2
                d = pix - pix.mean(axis=0)
                wx, wy = -d[:, 0] * R.RES_X, -d[:, 1] * R.RES_Y
                zc = np.sum((wx + 1j * wy) ** 4)
                yaw = ((np.angle(zc) - math.pi) / 4) % (math.pi / 2)
                objs.append({
                    "id": f"obj_{k}",
                    "color": color,
                    "half_size": round(half, 3),
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "_raw_x": float(x),
                    "_raw_y": float(y),
                    "yaw": round(yaw, 3),
                    "in_container": bool(_in_box(x, y, w.spec.container_pos)),
                })
                k += 1
        return objs

    def perceive(self, w: World) -> Dict:
        raw_objs = self._detect_raw(w)
        # Cold-start optical burst: step 100 physics ticks (0.20s) so a 0.02 m/s cube
        # shifts by 4.0mm (~1.7 pixels), overcoming 2.34mm/px quantization on frame 1.
        if self.enable_velocity_tracker and not self.tracker._tracks:
            t0 = w.time
            for o in raw_objs:
                self.tracker.update(o["color"] + "_" + o["id"], np.array([o["_raw_x"], o["_raw_y"], 0.0]), t0)
            if any(np.any(v) for v in w.vel.values()):
                w.step(100)
                raw_objs = self._detect_raw(w)

        objs: List[Dict] = []
        for o in raw_objs:
            rx, ry = o.pop("_raw_x"), o.pop("_raw_y")
            d = dict(o)
            if self.enable_velocity_tracker:
                track_key = o["color"] + "_" + o["id"]
                filt_pos, est_vel = self.tracker.update(track_key, np.array([rx, ry, 0.0]), w.time)
                d["x"] = round(float(filt_pos[0]), 3)
                d["y"] = round(float(filt_pos[1]), 3)
                if abs(est_vel[1]) >= 0.006:
                    d["velocity_y"] = float(round(est_vel[1], 4))
            objs.append(d)

        c = w.spec.container_pos
        tip = w.tip()
        return {
            "t": round(w.time, 3),
            "source": "vision",
            "container": {"x": c[0], "y": c[1]},
            "gripper": {"closure": round(w.finger_closure(), 4), "tip": [round(float(v), 3) for v in tip]},
            "objects": objs,
        }
