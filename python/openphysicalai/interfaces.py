"""Core interfaces (frozen in Phase 0). Implementations arrive in later phases."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Protocol

Track = Literal["planner", "learned", "hybrid", "scripted"]
Assist = Literal["A0", "A1", "A2", "A3"]
Verifier = Literal["V0", "V1", "V2"]


@dataclass
class EvaluationContract:
    observation_access: tuple = ("rgb", "proprio")
    control_hz: int = 20
    action_space: str = "skill_level"
    controller_assistance: Assist = "A3"
    verifier_level: Verifier = "V1"
    episodes: int = 100
    seeds: str = "shared"


@dataclass
class ActionResult:
    action: Any
    t_obs_ns: int = 0
    t_submit_ns: int = 0
    t_ready_ns: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


class Policy(Protocol):
    name: str
    track: Track

    def reset(self, task: str, seed: int, contract: EvaluationContract) -> None: ...

    def act(self, obs: Any, world_state: Optional[dict] = None, deadline_ms: Optional[float] = None) -> ActionResult: ...


class Backend(Protocol):
    def reset(self, seed: int) -> Any: ...

    def step(self, action: Any) -> Any: ...

    def evaluation_oracle_success(self) -> bool:
        """Ground-truth scoring. Never exposed to the agent."""
