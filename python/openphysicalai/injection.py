"""Seeded failure / perturbation injection. Ground truth of what was injected is logged for scoring
only and is never exposed to the agent."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

LEVELS = {
    "clean":    {"p": 0.00, "pos_noise": 0.000, "pix_noise": 0.0},
    "mild":     {"p": 0.10, "pos_noise": 0.010, "pix_noise": 8.0},
    "moderate": {"p": 0.25, "pos_noise": 0.020, "pix_noise": 16.0},
    "severe":   {"p": 0.40, "pos_noise": 0.035, "pix_noise": 28.0},
}

EXPECTED_DIAGNOSIS = {"grasp_slip": "object_dropped", "object_displaced": "grasp_miss", "wrong_placement": "wrong_placement"}


@dataclass
class Injector:
    level: str
    rng: np.random.Generator
    log: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        self.cfg = LEVELS[self.level]

    @property
    def pos_noise(self) -> float:
        return self.cfg["pos_noise"]

    @property
    def pix_noise(self) -> float:
        return self.cfg["pix_noise"]

    def _roll(self) -> bool:
        return self.cfg["p"] > 0 and self.rng.random() < self.cfg["p"]

    def displace(self, world, oid: str, step: int) -> bool:
        if self._roll():
            ang = self.rng.uniform(0, 2 * math.pi)
            d = self.rng.uniform(0.06, 0.09)
            x0, y0 = world.obj_pos(oid)[:2]
            nx, ny = x0 + d * math.cos(ang), y0 + d * math.sin(ang)
            nx, ny = min(max(nx, 0.10), 0.36), min(max(ny, -0.25), 0.25)
            world.teleport(oid, nx - x0, ny - y0)
            self.log.append({"type": "object_displaced", "step": step, "object": oid})
            return True
        return False

    def slip(self, step: int) -> bool:
        if self._roll():
            self.log.append({"type": "grasp_slip", "step": step})
            return True
        return False

    def placement_offset(self, step: int):
        if self._roll():
            ang = self.rng.uniform(0, 2 * math.pi)
            self.log.append({"type": "wrong_placement", "step": step})
            return 0.12 * math.cos(ang), 0.12 * math.sin(ang)
        return 0.0, 0.0
