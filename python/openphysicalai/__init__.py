"""OpenPhysicalAI Lab core (early scaffold).

Interfaces and budget logic only. MuJoCo backend, scheduler and real policies
arrive in Phase 1+ (see docs/OpenPhysicalAI_Lab_Plan_v3.md).
"""
__version__ = "0.2.0"

from .budget import Budget, BudgetCheck, evaluate_budget  # noqa: F401
from .stats import wilson_interval  # noqa: F401
