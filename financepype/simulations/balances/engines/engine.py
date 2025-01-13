"""Base interface for balance simulation engines.

This module defines the abstract base class for all balance simulation engines.
Each engine is responsible for simulating the cashflows that occur during
trading operations in a specific market type (spot, perpetual, options, etc.).

The simulation process is divided into four phases:
1. Opening Outflows: Assets leaving the account at position opening
   - Purchase cost
   - Initial margin
   - Opening fees

2. Opening Inflows: Assets entering the account at position opening
   - Typically empty for most operations
   - May include rebates or rewards in some cases

3. Closing Outflows: Assets leaving the account at position closing
   - Closing fees
   - Liquidation fees
   - Settlement costs

4. Closing Inflows: Assets entering the account at position closing
   - Sale proceeds
   - Realized PnL
   - Rebates or rewards

Example:
    >>> class SpotEngine(BalanceEngine):
    ...     @classmethod
    ...     def get_involved_assets(cls, operation_details):
    ...         return [
    ...             AssetCashflow(
    ...                 asset=operation_details.trading_pair.base_asset,
    ...                 involvement_type=InvolvementType.OPENING,
    ...                 cashflow_type=CashflowType.OUTFLOW,
    ...                 reason=CashflowReason.OPERATION
    ...             )
    ...         ]
    ...
    ...     @classmethod
    ...     def get_opening_outflows(cls, operation_details):
    ...         return [
    ...             AssetCashflow(
    ...                 asset=operation_details.trading_pair.base_asset,
    ...                 involvement_type=InvolvementType.OPENING,
    ...                 cashflow_type=CashflowType.OUTFLOW,
    ...                 reason=CashflowReason.OPERATION,
    ...                 amount=operation_details.amount
    ...             )
    ...         ]
"""

from abc import ABC, abstractmethod
from typing import Any

from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    OperationSimulationResult,
)


class BalanceEngine(ABC):
    """Base class for simulating cashflows of trading operations.

    This abstract class defines the interface for all balance engines. Each engine
    is responsible for simulating the cashflows of a specific type of trading
    operation (spot, perpetual, options, etc.).

    The simulation process is divided into four phases:
    1. Opening Outflows: Assets leaving the account at position opening
    2. Opening Inflows: Assets entering the account at position opening
    3. Closing Outflows: Assets leaving the account at position closing
    4. Closing Inflows: Assets entering the account at position closing

    Each phase can involve multiple assets and includes both operation costs/returns
    and fees. The engine must handle all aspects of the operation, including:
    - Asset identification
    - Amount calculation
    - Fee calculation
    - PnL calculation
    - Balance validation

    Example:
        >>> engine = MyBalanceEngine()
        >>> result = engine.get_complete_simulation(
        ...     operation_details=order,
        ... )
        >>> print(result.opening_outflows)  # Assets used to open position
    """

    @classmethod
    @abstractmethod
    def get_involved_assets(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets involved in the operation without amounts.

        This method is used to identify which assets will be involved in the operation
        before calculating the actual amounts. This is useful for pre-trade checks
        and balance validation.

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects with involvement types but no amounts

        Example:
            >>> flows = engine.get_involved_assets(order)
            >>> print([flow.asset for flow in flows])  # [Asset("BTC"), Asset("USD")]
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_opening_outflows(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets leaving the account at position opening.

        This method calculates all assets that will leave the account when opening
        the position, including:
        - Trade costs (e.g., purchase amount, initial margin)
        - Upfront fees (if fee impact type is ADDED_TO_COSTS)
        - Any other opening costs

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects representing outflows at opening

        Example:
            >>> flows = engine.get_opening_outflows(order, balances)
            >>> print(flows[0].amount)  # Amount of BTC to purchase
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_opening_inflows(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets entering the account at position opening.

        This method calculates all assets that will enter the account when opening
        the position. This is typically empty for most operations as assets usually
        flow in at closing, but may include:
        - Opening rebates
        - Rewards or incentives
        - Special case returns

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects representing inflows at opening

        Example:
            >>> flows = engine.get_opening_inflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.FEE for rebates
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_closing_outflows(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets leaving the account at position closing.

        This method calculates all assets that will leave the account when closing
        the position, including:
        - Fees deducted from returns
        - Liquidation fees
        - Settlement costs
        - Any other closing costs

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects representing outflows at closing

        Example:
            >>> flows = engine.get_closing_outflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.FEE
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_closing_inflows(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets entering the account at position closing.

        This method calculates all assets that will enter the account when closing
        the position, including:
        - Trade returns (e.g., sale proceeds)
        - Realized PnL
        - Rebates or rewards
        - Any other closing returns

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects representing inflows at closing

        Example:
            >>> flows = engine.get_closing_inflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.OPERATION
        """
        raise NotImplementedError

    @classmethod
    def get_complete_simulation(
        cls, operation_details: Any
    ) -> OperationSimulationResult:
        """Get a complete simulation of all cashflows for the operation.

        This method combines all four phases of the operation to provide a complete
        view of all cashflows that will occur. It's useful for:
        - Pre-trade analysis
        - Risk assessment
        - Balance validation
        - Fee calculation
        - PnL projection

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            OperationSimulationResult containing all cashflows

        Example:
            >>> result = engine.get_complete_simulation(order, balances)
            >>> print(result.opening_outflows)  # Opening costs
            >>> print(result.closing_inflows)   # Expected returns
        """
        result = OperationSimulationResult(
            operation_details=operation_details,
            cashflows=[
                *cls.get_opening_outflows(operation_details),
                *cls.get_opening_inflows(operation_details),
                *cls.get_closing_outflows(operation_details),
                *cls.get_closing_inflows(operation_details),
            ],
        )
        return result
