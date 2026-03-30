"""Base interface for settlement engines.

Settlement engines compute cashflows for single recurring events (funding
payments, interest accrual, staking rewards). Unlike ``BalanceEngine`` which
models a position lifecycle (open/close with four phases), settlement engines
model instantaneous cashflow events applied to existing positions.

Both produce ``list[AssetCashflow]`` and feed into ``BalanceTracker``.
"""

from abc import ABC, abstractmethod
from typing import Any

from financepype.simulations.balances.engines.models import AssetCashflow


class SettlementEngine(ABC):
    """Base class for computing a single periodic settlement.

    Subclasses implement ``compute_settlement`` which takes a settlement
    details object and returns the cashflows for that one event.  All
    methods are classmethods (stateless), matching the ``BalanceEngine``
    pattern.
    """

    @classmethod
    @abstractmethod
    def compute_settlement(cls, details: Any) -> list[AssetCashflow]:
        """Compute cashflows for a single settlement event.

        Args:
            details: Settlement-specific details dataclass
                (e.g. ``FundingSettlementDetails``).

        Returns:
            List of ``AssetCashflow`` objects for this settlement.
        """
        raise NotImplementedError
