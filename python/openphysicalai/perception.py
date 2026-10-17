"""Perception: Oracle (simulator truth + optional noise) and Vision (colour segmentation on the
software top-down image). Both return the same WorldState dict."""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Optional

import numpy as np

from . import render as R
from .sim import CONTAINER_HALF_IN, World


def _in_box(x, y, c):
    return abs(x - c[0]) < CONTAINER_HALF_IN and abs(y - c[1]) < CONTAINER_HALF_IN


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
        q = deque([(r0, c0)]); seen[r0, c0] = True; pix = []
        while q:
            r, c = q.popleft(); pix.append((r, c))
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and mask[rr, cc] and not seen[rr, cc]:
                    seen[rr, cc] = True; q.append((rr, cc))
        if len(pix) >= min_px:
            out.append(np.array(pix))
    return out


class VisionPerception:
    name = "vision"

    def __init__(self, rng: np.random.Generator, pixel_noise: float = 0.0):
        self.rng, self.pixel_noise = rng, pixel_noise

    def perceive(self, w: World) -> Dict:
        img = R.render(w, draw_arm=False, rng=self.rng, noise=self.pixel_noise)   # arm not drawn: avoids self-occlusion of the perception frame
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
                # yaw (mod 90 deg) from the 4th angular moment of the blob: corners give phase 4*yaw + pi
                d = pix - pix.mean(axis=0)
                zc = complex(0, 0)
                wx, wy = -d[:, 0] * R.RES_X, -d[:, 1] * R.RES_Y
                zc = np.sum((wx + 1j * wy) ** 4)
                yaw = ((np.angle(zc) - math.pi) / 4) % (math.pi / 2)
                objs.append({"id": f"obj_{k}", "color": color, "half_size": round(half, 3), "x": round(x, 3), "y": round(y, 3),
                             "yaw": round(yaw, 3), "in_container": bool(_in_box(x, y, w.spec.container_pos))})
                k += 1
        c = w.spec.container_pos
        tip = w.tip()
        return {"t": round(w.time, 3), "source": "vision", "container": {"x": c[0], "y": c[1]},
                "gripper": {"closure": round(w.finger_closure(), 4), "tip": [round(float(v), 3) for v in tip]}, "objects": objs}
