"""
BarState dataclass: holds per-bar raw and enriched fields.
Extend fields as specs harden; keep as lightweight dict wrapper for now.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class BarState:
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BarState":
        return cls(data=dict(payload))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)

    def update(self, extra: Dict[str, Any]) -> None:
        self.data.update(extra)
