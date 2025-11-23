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

    def validate_bar(
        self,
        bar_state: Dict[str, Any],
        required: Optional[Set[str]] = None,
        numeric_fields: Optional[Set[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate bar_state has required fields and valid values.

        Args:
            bar_state: The bar state dict to validate.
            required: Required field names (uses self.required_fields if None).
            numeric_fields: Fields that must be numeric and non-negative.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: List[str] = []
        required = required or self.required_fields

        # Check required fields exist and are not None
        for field in required:
            if field not in bar_state:
                errors.append(f"missing_field:{field}")
            elif bar_state[field] is None:
                errors.append(f"null_field:{field}")

        # Check numeric fields are valid numbers
        if numeric_fields:
            for field in numeric_fields:
                value = bar_state.get(field)
                if value is not None:
                    if not isinstance(value, (int, float)):
                        errors.append(f"non_numeric:{field}")
                    elif value < 0:
                        errors.append(f"negative:{field}")

        return len(errors) == 0, errors

    def get_numeric(
        self, bar_state: Dict[str, Any], field: str, default: float = 0.0
    ) -> float:
        """
        Safely get a numeric value from bar_state.

        Args:
            bar_state: The bar state dict.
            field: Field name to retrieve.
            default: Default value if field missing or invalid.

        Returns:
            Numeric value or default.
        """
        value = bar_state.get(field)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_bool(
        self, bar_state: Dict[str, Any], field: str, default: bool = False
    ) -> bool:
        """
        Safely get a boolean value from bar_state.

        Args:
            bar_state: The bar state dict.
            field: Field name to retrieve.
            default: Default value if field missing.

        Returns:
            Boolean value or default.
        """
        value = bar_state.get(field)
        if value is None:
            return default
        return bool(value)
