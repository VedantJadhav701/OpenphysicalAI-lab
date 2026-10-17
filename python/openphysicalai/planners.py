"""Planners. Output: list of {"action":"pick","object":id} / {"action":"place","target":"container"}.
RulePlanner = scripted baseline that parses the instruction text. OllamaPlanner = real local LLM
through the Ollama HTTP API (http://127.0.0.1:11434)."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlanResult:
    plan: List[Dict]
    latency_ms: float
    raw: str = ""
    error: str = ""
    meta: Dict = field(default_factory=dict)


COLORS = ("red", "green", "yellow", "orange", "blue")


class RulePlanner:
    name = "rule-based"
    track = "scripted"

    def plan(self, instruction: str, ws: Dict) -> PlanResult:
        t0 = time.perf_counter()
        txt = instruction.lower()
        objs = [o for o in ws["objects"] if not o.get("in_container")]
        sel: List[Dict] = []
        if "smallest" in txt:
            if objs:
                sel = [min(objs, key=lambda o: o["half_size"])]
        elif "left of" in txt:
            m = re.search(r"left of the (\w+) cube", txt)
            ref = next((o for o in ws["objects"] if m and o["color"] == m.group(1)), None)
            if ref:
                sel = [o for o in objs if o["y"] > ref["y"] + 0.05 and o is not ref]
                sel = sel[:1]
        elif "all" in txt:
            m = re.search(r"all (\w+) cubes", txt)
            if m:
                sel = sorted([o for o in objs if o["color"] == m.group(1)], key=lambda o: o["x"])
        else:
            m = re.search(r"the (\w+) cube", txt)
            if m:
                sel = [o for o in objs if o["color"] == m.group(1)][:1]
        plan: List[Dict] = []
        for o in sel:
            plan += [{"action": "pick", "object": o["id"]}, {"action": "place", "target": "container"}]
        return PlanResult(plan, (time.perf_counter() - t0) * 1000)


SYSTEM = (
    "You control a robot arm. You are given a task instruction and the current world state as JSON. "
    "Return ONLY JSON of the form {\"plan\": [ ... ]}. Allowed steps: "
    "{\"action\":\"pick\",\"object\":\"<id from world state>\"} and {\"action\":\"place\",\"target\":\"container\"}. "
    "Every pick must be followed by a place. Never pick an object already in the container. "
    "Coordinates: x forward, y left (larger y = further left). half_size is half the cube edge in metres."
)

SCHEMA = {
    "type": "object",
    "properties": {"plan": {"type": "array", "items": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["pick", "place"]},
        "object": {"type": "string"}, "target": {"type": "string"}}, "required": ["action"]}}},
    "required": ["plan"],
}


def _http(url: str, payload: Optional[Dict] = None, timeout: float = 120.0) -> Dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ollama_models(host: str = "http://127.0.0.1:11434") -> Dict:
    try:
        d = _http(host + "/api/tags", timeout=3)
        return {"ok": True, "models": [{"name": m["name"], "size_gb": round(m.get("size", 0) / 2 ** 30, 2)} for m in d.get("models", [])]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "models": []}


class OllamaPlanner:
    track = "planner"

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", num_predict: int = 256, num_ctx: int = 2048):
        self.model, self.host, self.num_predict, self.num_ctx = model, host, num_predict, num_ctx
        self.name = f"ollama:{model}"

    def warmup(self):
        try:
            _http(self.host + "/api/chat", {"model": self.model, "messages": [{"role": "user", "content": "hi"}], "stream": False,
                                            "options": {"num_predict": 1, "num_ctx": self.num_ctx}, "keep_alive": "30m"}, timeout=300)
        except Exception:
            pass

    def plan(self, instruction: str, ws: Dict) -> PlanResult:
        slim = {"objects": [{k: o[k] for k in ("id", "color", "half_size", "x", "y", "in_container") if k in o} | ({"velocity_y": o["velocity_y"]} if "velocity_y" in o else {})
                            for o in ws["objects"]], "container": ws["container"]}
        body = {
            "model": self.model, "stream": False, "format": SCHEMA, "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 0, "num_predict": self.num_predict, "num_ctx": self.num_ctx},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Instruction: {instruction}\nWorld state: {json.dumps(slim)}"}],
        }
        t0 = time.perf_counter()
        try:
            d = _http(self.host + "/api/chat", body, timeout=300)
        except Exception as e:  # noqa: BLE001
            return PlanResult([], (time.perf_counter() - t0) * 1000, error=f"ollama_error: {e}")
        lat = (time.perf_counter() - t0) * 1000
        raw = d.get("message", {}).get("content", "")
        meta = {"eval_count": d.get("eval_count"), "prompt_eval_count": d.get("prompt_eval_count"),
                "tok_per_s": (d["eval_count"] / (d["eval_duration"] / 1e9)) if d.get("eval_count") and d.get("eval_duration") else None}
        try:
            plan = json.loads(raw).get("plan", [])
            if not isinstance(plan, list):
                raise ValueError("plan not a list")
        except Exception as e:  # noqa: BLE001
            return PlanResult([], lat, raw, f"invalid_json: {e}", meta)
        return PlanResult(plan, lat, raw, "", meta)


def validate_plan(plan: List[Dict], ws: Dict, holding: bool = False) -> Optional[str]:
    """Action validator. Returns an error string or None. Invalid plans are counted as planning failures."""
    if not plan:
        return "empty_plan"
    if len(plan) > 12:
        return "plan_too_long"
    ids = {o["id"]: o for o in ws["objects"]}
    expect = "place" if holding else "pick"
    for step in plan:
        if not isinstance(step, dict) or step.get("action") not in ("pick", "place"):
            return "unknown_action"
        if step["action"] != expect:
            return f"bad_order: expected {expect}"
        if step["action"] == "pick":
            o = ids.get(step.get("object"))
            if o is None:
                return f"unknown_object: {step.get('object')}"
            if o.get("in_container"):
                return "pick_in_container"
            expect = "place"
        else:
            if step.get("target") != "container":
                return "bad_target"
            expect = "pick"
    return None if expect == "pick" else "ends_holding"
