"""Break periods use minute offsets from the work date."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class BreakRecord:
    start_minute: int
    end_minute: int

    @property
    def minutes(self) -> int:
        return self.end_minute - self.start_minute
