"""
SMCDataProcessor: orchestrates module execution over incoming bars.
This is a lightweight skeleton; plug in real module implementations as ready.
"""

from typing import Dict, Any, List

from .core.module_base import BaseModule


class SMCDataProcessor:
    def __init__(self, modules: List[BaseModule] | None = None) -> None:
        self.modules: List[BaseModule] = modules or []
        self.history: List[Dict[str, Any]] = []

    def process_bar(self, bar_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run bar_state through the configured module pipeline.
        """
        state = dict(bar_state)
        for module in self.modules:
            state = module.process_bar(state, history=self.history)
        self.history.append(state)
        return state
