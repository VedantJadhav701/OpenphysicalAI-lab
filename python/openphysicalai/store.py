"""SQLite run store (stdlib only)."""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List, Optional


class Store:
    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "opai.sqlite")
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, summary TEXT, full TEXT)")
        self.db.commit()

    def save(self, run: Dict):
        m, c = run["metrics"], run["config"]
        summary = {"id": run["id"], "created": run["created"], "task": c["task"], "policy": run["policy_name"], "track": run["track"],
                   "agent": c["agent"], "perception": c["perception"], "verifier": c["verifier"], "perturb": c["perturb"], "mode": c["mode"],
                   "episodes": m["episodes"], "tsr": m["tsr"], "tsr_ci": m["tsr_ci"], "budget_pass": run["budget"]["pass"],
                   "budget": c["budget"], "p95": m["latency_ms"]["p95"], "label": c.get("label", "")}
        self.db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)", (run["id"], run["created"], json.dumps(summary), json.dumps(run)))
        self.db.commit()

    def list(self, limit: int = 300) -> List[Dict]:
        return [json.loads(r[0]) for r in self.db.execute("SELECT summary FROM runs ORDER BY created DESC LIMIT ?", (limit,))]

    def get(self, rid: str) -> Optional[Dict]:
        r = self.db.execute("SELECT full FROM runs WHERE id=?", (rid,)).fetchone()
        return json.loads(r[0]) if r else None

    def clear(self):
        self.db.execute("DELETE FROM runs")
        self.db.commit()
