"""Budget contract: separate caps for process-attributed and device-wide usage."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Budget:
    vram_process_peak_gb: float = 3.2
    vram_device_peak_gb: float = 3.8
    ram_process_peak_gb: float = 8.0
    ram_system_peak_gb: float = 14.0
    planning_ms_p95: float = 2500.0
    profile: str = "standard"


@dataclass
class BudgetCheck:
    name: str
    value: Optional[float]
    cap: float
    ok: bool
    note: str = ""


@dataclass
class BudgetResult:
    passed: bool
    checks: List[BudgetCheck] = field(default_factory=list)


def evaluate_budget(budget: Budget, observed: Dict[str, Optional[float]], not_applicable: tuple = ()) -> BudgetResult:
    """Compare observed peaks to caps. A missing observation is a failure of measurement, not a pass.
    `not_applicable` lists keys that do not apply on this machine (e.g. VRAM caps on a CPU-only machine)."""
    spec = [
        ("vram_process_peak_gb", budget.vram_process_peak_gb),
        ("vram_device_peak_gb", budget.vram_device_peak_gb),
        ("ram_process_peak_gb", budget.ram_process_peak_gb),
        ("ram_system_peak_gb", budget.ram_system_peak_gb),
        ("planning_ms_p95", budget.planning_ms_p95),
    ]
    checks: List[BudgetCheck] = []
    for name, cap in spec:
        v = observed.get(name)
        if name in not_applicable:
            checks.append(BudgetCheck(name, None, cap, True, "not applicable"))
        elif v is None:
            checks.append(BudgetCheck(name, None, cap, False, "not measured"))
        else:
            checks.append(BudgetCheck(name, float(v), cap, float(v) <= cap))
    return BudgetResult(all(c.ok for c in checks), checks)


PROFILES = {
    "relaxed":  Budget(3.2, 3.8, 8.0, 14.0, 4000.0, "relaxed"),
    "standard": Budget(3.2, 3.8, 8.0, 14.0, 2500.0, "standard"),
    "strict":   Budget(3.2, 3.8, 8.0, 14.0, 500.0, "strict"),
}
