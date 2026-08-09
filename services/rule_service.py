from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "rules"

def load_rule(year: int, name: str) -> dict:
    path = ROOT / str(year) / f"{name}_rules.json"
    with path.open(encoding="utf-8") as file:
        return json.load(file)
