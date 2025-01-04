from decimal import Decimal
from typing import Protocol
from unittest.mock import Mock, patch

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.markets.market import InstrumentType
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)
from financepype.simulations.balances.engines.multiengine import BalanceMultiEngine
from financepype.simulations.balances.engines.spot import SpotBalanceEngine


class MockEngine(Protocol):
    def get_opening_outflows(
        self, order: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]: ...

    def get_opening_inflows(
        self, order: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]: ...

    def get_closing_outflows(
        self, order: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]: ...

    def get_closing_inflows(
        self, order: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]: ...


@pytest.fixture
def mock_trading_pair() -> TradingPair:
    trading_pair = Mock(spec=TradingPair)
    trading_pair.instrument_type = InstrumentType.SPOT
    trading_pair.base = "BTC"
    trading_pair.quote = "USDT"
    return trading_pair


@pytest.fixture
def mock_platform() -> Platform:
    platform = Mock(spec=Platform)
    platform.identifier = "test_platform"
    return platform


@pytest.fixture
def mock_order_details(
    mock_trading_pair: TradingPair, mock_platform: Platform
) -> OrderDetails:
    mock_trading_rule = TradingRule(
        trading_pair=mock_trading_pair,
        min_order_size=Decimal("0.001"),
        min_price_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
    )
    mock_asset = Mock(spec=Asset)
    mock_fee = OperationFee(
        asset=mock_asset,
        amount=Decimal("0.1"),
        fee_type=FeeType.ABSOLUTE,
        impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
    )

    return OrderDetails(
        trading_pair=mock_trading_pair,
        trading_rule=mock_trading_rule,
        platform=mock_platform,
        trade_type=TradeType.BUY,
        order_type=OrderType.MARKET,
        amount=Decimal("1"),
        price=Decimal("100"),
        leverage=1,
        position_action=PositionAction.OPEN,
        index_price=Decimal("100"),
        fee=mock_fee,
    )


@pytest.fixture
def mock_current_balances() -> dict[Asset, Decimal]:
    asset = Mock(spec=Asset)
    return {asset: Decimal("1000")}


@pytest.fixture
def mock_engine(platform: Platform) -> Mock:
    engine = Mock(spec=SpotBalanceEngine)
    usdt = AssetFactory.get_asset(platform, "USDT")
    btc = AssetFactory.get_asset(platform, "BTC")

    engine.get_opening_outflows.return_value = [
        AssetCashflow(
            asset=usdt,
            amount=Decimal("100"),
            involvement_type=InvolvementType.OPENING,
            cashflow_type=CashflowType.OUTFLOW,
            reason=CashflowReason.OPERATION,
        )
    ]
    engine.get_opening_inflows.return_value = []
    engine.get_closing_outflows.return_value = [
        AssetCashflow(
            asset=usdt,
            amount=Decimal("0.1"),
            involvement_type=InvolvementType.CLOSING,
            cashflow_type=CashflowType.OUTFLOW,
            reason=CashflowReason.FEE,
        )
    ]
    engine.get_closing_inflows.return_value = [
        AssetCashflow(
            asset=btc,
            amount=Decimal("1"),
            involvement_type=InvolvementType.CLOSING,
            cashflow_type=CashflowType.INFLOW,
            reason=CashflowReason.OPERATION,
        )
    ]
    return engine


def test_get_engine_spot(mock_trading_pair: TradingPair) -> None:
    """Test getting the engine for a spot trading pair."""
    engine = BalanceMultiEngine.get_engine(mock_trading_pair)
    assert issubclass(engine, BalanceEngine)


def test_get_engine_unsupported() -> None:
    """Test that getting an engine for an unsupported instrument type raises ValueError."""
    trading_pair = Mock(spec=TradingPair)
    trading_pair.instrument_type = "UNSUPPORTED"
    with pytest.raises(ValueError, match="Unsupported instrument type: UNSUPPORTED"):
        BalanceMultiEngine.get_engine(trading_pair)


@patch.object(BalanceMultiEngine, "get_engine")
def test_get_opening_outflows(
    mock_get_engine: Mock,
    mock_order_details: OrderDetails,
    mock_current_balances: dict[Asset, Decimal],
    mock_engine: Mock,
) -> None:
    """Test getting opening outflows."""
    mock_get_engine.return_value = mock_engine
    outflows = BalanceMultiEngine.get_opening_outflows(
        mock_order_details, mock_current_balances
    )
    assert len(outflows) == 1
    assert outflows[0].amount == Decimal("100")
    mock_engine.get_opening_outflows.assert_called_once_with(
        mock_order_details, mock_current_balances
    )


@patch.object(BalanceMultiEngine, "get_engine")
def test_get_opening_inflows(
    mock_get_engine: Mock,
    mock_order_details: OrderDetails,
    mock_current_balances: dict[Asset, Decimal],
    mock_engine: Mock,
) -> None:
    """Test getting opening inflows."""
    mock_get_engine.return_value = mock_engine
    inflows = BalanceMultiEngine.get_opening_inflows(
        mock_order_details, mock_current_balances
    )
    assert len(inflows) == 0  # Spot trading has no opening inflows
    mock_engine.get_opening_inflows.assert_called_once_with(
        mock_order_details, mock_current_balances
    )


@patch.object(BalanceMultiEngine, "get_engine")
def test_get_closing_outflows(
    mock_get_engine: Mock,
    mock_order_details: OrderDetails,
    mock_current_balances: dict[Asset, Decimal],
    mock_engine: Mock,
) -> None:
    """Test getting closing outflows."""
    mock_get_engine.return_value = mock_engine
    outflows = BalanceMultiEngine.get_closing_outflows(
        mock_order_details, mock_current_balances
    )
    assert len(outflows) == 1
    assert outflows[0].amount == Decimal("0.1")  # Fee amount
    mock_engine.get_closing_outflows.assert_called_once_with(
        mock_order_details, mock_current_balances
    )


@patch.object(BalanceMultiEngine, "get_engine")
def test_get_closing_inflows(
    mock_get_engine: Mock,
    mock_order_details: OrderDetails,
    mock_current_balances: dict[Asset, Decimal],
    mock_engine: Mock,
) -> None:
    """Test getting closing inflows."""
    mock_get_engine.return_value = mock_engine
    inflows = BalanceMultiEngine.get_closing_inflows(
        mock_order_details, mock_current_balances
    )
    assert len(inflows) == 1
    assert inflows[0].amount == Decimal("1")  # Base asset amount
    mock_engine.get_closing_inflows.assert_called_once_with(
        mock_order_details, mock_current_balances
    )
