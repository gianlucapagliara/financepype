from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from financepype.assets.asset import Asset
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    OperationSimulationResult,
)


class BalanceEngine(ABC):
    """Base class for simulating cashflows of trading operations.

    This abstract class defines the interface for all balance engines. Each engine is responsible
    for simulating the cashflows of a specific type of trading operation (spot, perpetual, etc.).

    The simulation process is divided into four phases:
    1. Opening Outflows: Assets leaving the account at position opening (e.g., purchase cost, initial margin)
    2. Opening Inflows: Assets entering the account at position opening (typically empty)
    3. Closing Outflows: Assets leaving the account at position closing (e.g., fees deducted from returns)
    4. Closing Inflows: Assets entering the account at position closing (e.g., sale proceeds, PnL)

    Each phase can involve multiple assets and includes both operation costs/returns and fees.
    """

    @classmethod
    @abstractmethod
    def get_involved_assets(cls, operation_details: Any) -> list[AssetCashflow]:
        """Get all assets involved in the operation without amounts.

        This method is used to identify which assets will be involved in the operation
        before calculating the actual amounts. This is useful for pre-trade checks.

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)

        Returns:
            List of AssetCashflow objects with involvement types but no amounts
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_opening_outflows(
        cls,
        operation_details: Any,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        """Get all assets leaving the account at position opening.

        This includes:
        - Trade costs (e.g., purchase amount, initial margin)
        - Upfront fees (if fee impact type is ADDED_TO_COSTS)

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)
            current_balances: Current balances of all assets

        Returns:
            List of AssetCashflow objects representing outflows at opening
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_opening_inflows(
        cls,
        operation_details: Any,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        """Get all assets entering the account at position opening.

        This is typically empty for most operations as assets usually flow in at closing.

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)
            current_balances: Current balances of all assets

        Returns:
            List of AssetCashflow objects representing inflows at opening
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_closing_outflows(
        cls,
        operation_details: Any,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        """Get all assets leaving the account at position closing.

        This includes:
        - Fees deducted from returns (if fee impact type is DEDUCTED_FROM_RETURNS)
        - Any other closing costs

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)
            current_balances: Current balances of all assets

        Returns:
            List of AssetCashflow objects representing outflows at closing
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_closing_inflows(
        cls,
        operation_details: Any,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        """Get all assets entering the account at position closing.

        This includes:
        - Trade returns (e.g., sale proceeds, realized PnL)
        - Any other closing returns

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)
            current_balances: Current balances of all assets

        Returns:
            List of AssetCashflow objects representing inflows at closing
        """
        raise NotImplementedError

    @classmethod
    def get_complete_simulation(
        cls,
        operation_details: Any,
        current_balances: dict[Asset, Decimal],
    ) -> OperationSimulationResult:
        """Get a complete simulation of all cashflows for the operation.

        This method combines all four phases of the operation to provide a complete
        view of all cashflows that will occur.

        Args:
            operation_details: Details of the operation (e.g., OrderDetails)
            current_balances: Current balances of all assets

        Returns:
            OperationSimulationResult containing all cashflows
        """
        result = OperationSimulationResult(
            operation_details=operation_details,
            cashflows=[
                *cls.get_opening_outflows(operation_details, current_balances),
                *cls.get_opening_inflows(operation_details, current_balances),
                *cls.get_closing_outflows(operation_details, current_balances),
                *cls.get_closing_inflows(operation_details, current_balances),
            ],
        )
        return result
