"""
Base interface for per-bar processing modules.
Each module receives BarState (dict-like) and returns an updated dict.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseModule(ABC):
    name: str = "base_module"

    @abstractmethod
    def process_bar(self, bar_state: Dict[str, Any], history: list | None = None) -> Dict[str, Any]:
        """
        Process a single bar.

        Args:
            bar_state: Current bar fields (mutable dict).
            history: Optional recent bar_state list for context-sensitive logic.

        Returns:
            Updated bar_state dict.
        """
        raise NotImplementedError
