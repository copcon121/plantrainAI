"""
SMCDataProcessor: orchestrates module execution over incoming bars.
This is a lightweight skeleton; plug in real module implementations as ready.
"""

from typing import Dict, Any, List

from .core.module_base import BaseModule


class SMCDataProcessor:
    def __init__(
        self,
        modules: List[BaseModule] | None = None,
        max_history: int = 2000,
        reset_on_symbol_change: bool = True,
    ) -> None:
        self.modules: List[BaseModule] = modules or []
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.reset_on_symbol_change = reset_on_symbol_change
        self._last_symbol: str | None = None

    def process_bar(self, bar_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run bar_state through the configured module pipeline.

        - Protects against module exceptions (captures under `processor_errors`).
        - Trims history to avoid unbounded growth (memory leak).
        - Optionally resets history when symbol changes.
        """
        state = dict(bar_state)
        errors: List[str] = []

        # Reset history when switching symbols/files to avoid state bleed
        symbol = state.get("symbol")
        if self.reset_on_symbol_change and symbol and symbol != self._last_symbol:
            self.history = []
        self._last_symbol = symbol

        for module in self.modules:
            try:
                state = module.process_bar(state, history=self.history)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{module.name}: {exc}")

        if errors:
            # Attach errors but still return state best-effort
            state["processor_errors"] = errors

        self.history.append(state)
        # Trim history to max_history to prevent unbounded memory use
        if self.max_history > 0 and len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        return state
