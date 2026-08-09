from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class Company:
    name: str = ""
    address: str = ""
    representative: str = ""
