"""Tiered maintenance margin calculation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MMRTier:
    """Single maintenance margin tier.

    Attributes:
        limit: Position value upper bound for this tier.
        rate: Maintenance margin rate (decimal, e.g. 0.005 for 0.5%).
        deduction: Cumulative deduction applied at this tier.
    """

    limit: Decimal
    rate: Decimal
    deduction: Decimal


class TieredMMR:
    """Tiered maintenance margin calculator.

    Applies a stepped MMR structure where different position value ranges
    correspond to different maintenance margin rates with cumulative deductions.
    """

    def __init__(self, tiers: list[MMRTier]) -> None:
        """Initialize with a list of MMR tiers, sorted by limit ascending.

        Args:
            tiers: List of MMRTier instances defining the tiered structure.
        """
        self.tiers = sorted(tiers, key=lambda t: t.limit)

    def calculate_maintenance_margin(self, position_value: Decimal) -> Decimal:
        """Calculate maintenance margin for a given position value.

        Finds the applicable tier by comparing position_value to tier limits
        and applies: maintenance_margin = position_value * rate - deduction.

        Args:
            position_value: The current position value.

        Returns:
            Required maintenance margin as a Decimal.
        """
        tier = self.tiers[-1]
        for t in self.tiers:
            if position_value <= t.limit:
                tier = t
                break
        return position_value * tier.rate - tier.deduction
