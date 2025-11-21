"""
Fix #02: FVG Quality (primary signal) - stub.
Implement per docs/MODULE_FIX02_FVG_QUALITY.md.
"""
from typing import Any, Dict, List

from processor.core.module_base import BaseModule


class FVGQualityModule(BaseModule):
    name = "fix02_fvg_quality"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def process_bar(self, bar_state: Dict[str, Any], history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return bar_state
        # TODO: implement FVG detection/quality scoring
        return bar_state
