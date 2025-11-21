"""
EventState dataclass: represents derived trading events (e.g., FVG retests).
Constructed from BarState snapshots after module pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class EventState:
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "EventState":
        return cls(data=dict(payload))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)

    def update(self, extra: Dict[str, Any]) -> None:
        self.data.update(extra)
