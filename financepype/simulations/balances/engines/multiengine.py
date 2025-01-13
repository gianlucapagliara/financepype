"""Multi-engine router for balance simulations.

This module provides a router engine that delegates balance simulations to
specialized engines based on the instrument type. It acts as a single entry
point for all balance calculations while ensuring that each instrument type
is handled by the most appropriate engine.

The module supports multiple instrument types:
- Spot markets (regular spot trading)
- Perpetual futures (both regular and inverse)
- Options (both regular and inverse, calls and puts)

Example:
    >>> from financepype.markets import TradingPair, InstrumentType
    >>> from financepype.simulations.balances.engines import BalanceMultiEngine
    >>>
    >>> # Create an order for a spot market
    >>> pair = TradingPair("BTC-USD", instrument_type=InstrumentType.SPOT)
    >>> order = OrderDetails(trading_pair=pair, ...)
    >>>
    >>> # Simulate the order
    >>> result = BalanceMultiEngine.get_complete_simulation(
    ...     order_details=order,
    ... )
    >>>
    >>> # The simulation is handled by SpotBalanceEngine internally
    >>> print(result.opening_outflows)  # Shows the cost of the trade
"""

from financepype.markets.market import InstrumentType
from financepype.markets.trading_pair import TradingPair
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import AssetCashflow, OrderDetails
from financepype.simulations.balances.engines.option import (
    InverseOptionBalanceEngine,
    OptionBalanceEngine,
)
from financepype.simulations.balances.engines.perpetual import (
    InversePerpetualBalanceEngine,
    PerpetualBalanceEngine,
)
from financepype.simulations.balances.engines.spot import SpotBalanceEngine


class BalanceMultiEngine(BalanceEngine):
    """Router engine that delegates cashflow calculations to appropriate specialized engines.

    This engine maintains a mapping between instrument types and their corresponding
    balance engines, then delegates all cashflow calculations to the appropriate engine
    based on the trading pair's instrument type.

    Current Mappings:
    - SPOT → SpotBalanceEngine
    - PERPETUAL → PerpetualBalanceEngine
    - INVERSE_PERPETUAL → InversePerpetualBalanceEngine
    - OPTION → OptionBalanceEngine
    - INVERSE_OPTION → InverseOptionBalanceEngine

    This design allows:
    1. Single entry point for all balance calculations
    2. Easy addition of new instrument types
    3. Consistent cashflow patterns across all instrument types
    4. Specialized handling for each instrument type's unique requirements

    Example:
        >>> # Create a spot market order
        >>> order = OrderDetails(
        ...     trading_pair=TradingPair("BTC-USD", InstrumentType.SPOT),
        ...     amount=Decimal("1.0"),
        ...     price=Decimal("50000"),
        ...     ...
        ... )
        >>>
        >>> # Simulate the order
        >>> result = BalanceMultiEngine.get_complete_simulation(
        ...     order_details=order,
        ... )
    """

    INSTRUMENT_TYPE_TO_ENGINE_MAP = {
        InstrumentType.SPOT: SpotBalanceEngine,
        InstrumentType.PERPETUAL: PerpetualBalanceEngine,
        InstrumentType.INVERSE_PERPETUAL: InversePerpetualBalanceEngine,
        InstrumentType.CALL_OPTION: OptionBalanceEngine,
        InstrumentType.PUT_OPTION: OptionBalanceEngine,
        InstrumentType.INVERSE_CALL_OPTION: InverseOptionBalanceEngine,
        InstrumentType.INVERSE_PUT_OPTION: InverseOptionBalanceEngine,
    }

    @classmethod
    def get_engine(cls, trading_pair: TradingPair) -> type[BalanceEngine]:
        """Get the appropriate balance engine for a trading pair.

        This method determines which specialized engine should handle the
        simulation based on the trading pair's instrument type.

        Args:
            trading_pair: The trading pair to get the engine for

        Returns:
            The appropriate balance engine class for the trading pair's instrument type

        Raises:
            ValueError: If the instrument type is not supported

        Example:
            >>> pair = TradingPair("BTC-USD", InstrumentType.SPOT)
            >>> engine_class = BalanceMultiEngine.get_engine(pair)
            >>> print(engine_class)  # <class 'SpotBalanceEngine'>
        """
        if trading_pair.instrument_type not in cls.INSTRUMENT_TYPE_TO_ENGINE_MAP:
            raise ValueError(
                f"Unsupported instrument type: {trading_pair.instrument_type}"
            )
        return cls.INSTRUMENT_TYPE_TO_ENGINE_MAP[trading_pair.instrument_type]

    @classmethod
    def get_involved_assets(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get all assets involved in the operation.

        This method delegates to the appropriate specialized engine based on
        the trading pair's instrument type.

        Args:
            order_details: Complete specification of the order

        Returns:
            List of AssetCashflow objects with involvement types but no amounts

        Example:
            >>> flows = BalanceMultiEngine.get_involved_assets(order)
            >>> print([flow.asset for flow in flows])  # [Asset("BTC"), Asset("USD")]
        """
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_involved_assets(order_details)

    @classmethod
    def get_opening_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get all assets leaving the account at position opening.

        This method delegates to the appropriate specialized engine based on
        the trading pair's instrument type.

        Args:
            order_details: Complete specification of the order

        Returns:
            List of AssetCashflow objects representing outflows at opening

        Example:
            >>> flows = BalanceMultiEngine.get_opening_outflows(order, balances)
            >>> print(flows[0].amount)  # Cost of opening the position
        """
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_opening_outflows(order_details)

    @classmethod
    def get_opening_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get all assets entering the account at position opening.

        This method delegates to the appropriate specialized engine based on
        the trading pair's instrument type.

        Args:
            order_details: Complete specification of the order

        Returns:
            List of AssetCashflow objects representing inflows at opening

        Example:
            >>> flows = BalanceMultiEngine.get_opening_inflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.FEE for rebates
        """
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_opening_inflows(order_details)

    @classmethod
    def get_closing_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get all assets leaving the account at position closing.

        This method delegates to the appropriate specialized engine based on
        the trading pair's instrument type.

        Args:
            order_details: Complete specification of the order

        Returns:
            List of AssetCashflow objects representing outflows at closing

        Example:
            >>> flows = BalanceMultiEngine.get_closing_outflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.FEE
        """
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_closing_outflows(order_details)

    @classmethod
    def get_closing_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get all assets entering the account at position closing.

        This method delegates to the appropriate specialized engine based on
        the trading pair's instrument type.

        Args:
            order_details: Complete specification of the order

        Returns:
            List of AssetCashflow objects representing inflows at closing

        Example:
            >>> flows = BalanceMultiEngine.get_closing_inflows(order, balances)
            >>> print(flows[0].reason)  # CashflowReason.OPERATION
        """
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_closing_inflows(order_details)
