from decimal import Decimal

from financepype.assets.asset import Asset
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

        Args:
            trading_pair: The trading pair to get the engine for

        Returns:
            The appropriate balance engine class for the trading pair's instrument type

        Raises:
            ValueError: If the instrument type is not supported
        """
        if trading_pair.instrument_type not in cls.INSTRUMENT_TYPE_TO_ENGINE_MAP:
            raise ValueError(
                f"Unsupported instrument type: {trading_pair.instrument_type}"
            )
        return cls.INSTRUMENT_TYPE_TO_ENGINE_MAP[trading_pair.instrument_type]

    @classmethod
    def get_involved_assets(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_involved_assets(order_details)

    @classmethod
    def get_opening_outflows(
        cls,
        order_details: OrderDetails,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_opening_outflows(order_details, current_balances)

    @classmethod
    def get_opening_inflows(
        cls,
        order_details: OrderDetails,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_opening_inflows(order_details, current_balances)

    @classmethod
    def get_closing_outflows(
        cls,
        order_details: OrderDetails,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_closing_outflows(order_details, current_balances)

    @classmethod
    def get_closing_inflows(
        cls,
        order_details: OrderDetails,
        current_balances: dict[Asset, Decimal],
    ) -> list[AssetCashflow]:
        engine = cls.get_engine(order_details.trading_pair)
        return engine.get_closing_inflows(order_details, current_balances)
