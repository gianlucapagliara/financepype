from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.simulations.balances.engines.models import (
    CashflowReason,
    CashflowType,
    OrderDetails,
)
from financepype.simulations.balances.engines.perpetual import (
    InversePerpetualBalanceEngine,
    PerpetualBalanceEngine,
)


class TestPerpetualBalanceEngine(PerpetualBalanceEngine):
    """Test implementation of PerpetualBalanceEngine."""


class TestInversePerpetualBalanceEngine(InversePerpetualBalanceEngine):
    """Test implementation of InversePerpetualBalanceEngine."""


@pytest.fixture
def platform() -> Platform:
    return Platform(identifier="test")


@pytest.fixture
def trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USDT")


@pytest.fixture
def trading_rule(trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("1000000"),
    )


@pytest.fixture
def base_asset(platform: Platform, trading_pair: TradingPair) -> Asset:
    return AssetFactory.get_asset(platform, trading_pair.base)


@pytest.fixture
def quote_asset(platform: Platform, trading_pair: TradingPair) -> Asset:
    return AssetFactory.get_asset(platform, trading_pair.quote)


@pytest.fixture
def order_details(
    platform: Platform,
    trading_pair: TradingPair,
    trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    return OrderDetails(
        platform=platform,
        trading_pair=trading_pair,
        trading_rule=trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),
        leverage=10,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        entry_index_price=Decimal("50000"),
        entry_price=Decimal("50000"),
        exit_price=None,
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


def test_perpetual_get_outflow_asset(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test that regular perpetual uses quote currency as collateral."""
    assert TestPerpetualBalanceEngine._get_outflow_asset(order_details) == quote_asset


def test_inverse_get_outflow_asset(
    order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test that inverse perpetual uses base currency as collateral."""
    assert (
        TestInversePerpetualBalanceEngine._get_outflow_asset(order_details)
        == base_asset
    )


def test_perpetual_calculate_margin(order_details: OrderDetails) -> None:
    """Test margin calculation for regular perpetual."""
    # (amount * price) / leverage = (1 * 50000) / 10 = 5000
    assert TestPerpetualBalanceEngine._get_margin(order_details) == Decimal("5000")


def test_inverse_calculate_margin(order_details: OrderDetails) -> None:
    """Test margin calculation for inverse perpetual."""
    # amount / (leverage * price) = 1 / (10 * 50000) = 0.000002
    assert TestInversePerpetualBalanceEngine._get_margin(order_details) == Decimal(
        "0.000002"
    )


def test_perpetual_calculate_pnl_long_profit(order_details: OrderDetails) -> None:
    """Test PnL calculation for regular perpetual long position with profit."""
    order_details.exit_price = Decimal("55000")
    # (exit_price - entry_price) * amount = (55000 - 50000) * 1 = 5000
    assert TestPerpetualBalanceEngine._calculate_pnl(order_details) == Decimal("5000")


def test_perpetual_calculate_pnl_short_profit(order_details: OrderDetails) -> None:
    """Test PnL calculation for regular perpetual short position with profit."""
    order_details.trade_type = TradeType.SELL
    order_details.exit_price = Decimal("45000")
    # (entry_price - exit_price) * amount = (50000 - 45000) * 1 = 5000
    assert TestPerpetualBalanceEngine._calculate_pnl(order_details) == Decimal("5000")


def test_inverse_calculate_pnl_long_profit(order_details: OrderDetails) -> None:
    """Test PnL calculation for inverse perpetual long position with profit."""
    order_details.exit_price = Decimal("55000")
    # contract_value * (1/entry_price - 1/exit_price) = 1 * (1/50000 - 1/55000)
    expected = Decimal("1") * (
        Decimal("1") / Decimal("50000") - Decimal("1") / Decimal("55000")
    )
    assert TestInversePerpetualBalanceEngine._calculate_pnl(order_details) == expected


def test_inverse_calculate_pnl_short_profit(order_details: OrderDetails) -> None:
    """Test PnL calculation for inverse perpetual short position with profit."""
    order_details.trade_type = TradeType.SELL
    order_details.exit_price = Decimal("45000")
    # contract_value * (1/exit_price - 1/entry_price) = 1 * (1/45000 - 1/50000)
    expected = Decimal("1") * (
        Decimal("1") / Decimal("45000") - Decimal("1") / Decimal("50000")
    )
    assert TestInversePerpetualBalanceEngine._calculate_pnl(order_details) == expected


def test_calculate_fee_amount_percentage(order_details: OrderDetails) -> None:
    """Test fee calculation with percentage fee."""
    # amount * price * fee_percentage / 100 = 1 * 50000 * 0.1 / 100 = 50
    assert TestPerpetualBalanceEngine._calculate_fee_amount(order_details) == Decimal(
        "50"
    )


def test_calculate_fee_amount_absolute(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee calculation with absolute fee."""
    order_details.fee.asset = quote_asset
    order_details.fee.fee_type = FeeType.ABSOLUTE
    order_details.fee.amount = Decimal("10")
    assert TestPerpetualBalanceEngine._calculate_fee_amount(order_details) == Decimal(
        "10"
    )


def test_calculate_fee_amount_invalid(order_details: OrderDetails) -> None:
    """Test fee calculation with invalid fee type."""
    order_details.fee.fee_type = "INVALID"  # type: ignore
    with pytest.raises(ValueError, match="Unsupported fee type"):
        TestPerpetualBalanceEngine._calculate_fee_amount(order_details)


def test_get_involved_assets_open(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test involved assets for opening position."""
    assets = TestPerpetualBalanceEngine.get_involved_assets(order_details)
    assert len(assets) == 3  # Collateral outflow, Position inflow, Fee outflow
    assert assets[0].asset == quote_asset
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION


def test_get_involved_assets_close(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test involved assets for closing position."""
    order_details.position_action = PositionAction.CLOSE
    assets = TestPerpetualBalanceEngine.get_involved_assets(order_details)
    assert len(assets) == 3  # Position outflow, PnL inflow, Fee outflow
    assert assets[1].asset == quote_asset
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.PNL


def test_get_involved_assets_flip(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test involved assets for flipping position."""
    order_details.position_action = PositionAction.FLIP
    assets = TestPerpetualBalanceEngine.get_involved_assets(order_details)
    assert len(assets) == 5  # New position, Old position close, PnL, New margin, Fee
    assert assets[1].asset == quote_asset
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.PNL


def test_get_involved_assets_invalid_action(order_details: OrderDetails) -> None:
    """Test involved assets with invalid position action."""
    order_details.position_action = "INVALID"  # type: ignore
    with pytest.raises(ValueError, match="Unsupported position action"):
        TestPerpetualBalanceEngine.get_involved_assets(order_details)


def test_get_opening_outflows(order_details: OrderDetails, quote_asset: Asset) -> None:
    """Test opening outflows calculation."""
    outflows = TestPerpetualBalanceEngine.get_opening_outflows(order_details)
    assert len(outflows) == 2  # Margin and fee
    assert outflows[0].asset == quote_asset
    assert outflows[0].amount == Decimal("5000")  # Margin amount
    assert outflows[1].amount == Decimal("50")  # Fee amount


def test_get_opening_inflows(order_details: OrderDetails) -> None:
    """Test opening inflows calculation."""
    inflows = TestPerpetualBalanceEngine.get_opening_inflows(order_details)
    assert len(inflows) == 0  # No inflows on opening


def test_get_closing_outflows_with_fee_deduction(order_details: OrderDetails) -> None:
    """Test closing outflows with fee deducted from returns."""
    order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    outflows = TestPerpetualBalanceEngine.get_closing_outflows(order_details)
    assert len(outflows) == 1  # Fee only
    assert outflows[0].amount == Decimal("50")


def test_get_closing_inflows_with_profit(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test closing inflows with profit."""
    order_details.position_action = PositionAction.CLOSE
    order_details.exit_price = Decimal("55000")
    inflows = TestPerpetualBalanceEngine.get_closing_inflows(order_details)
    assert len(inflows) == 1  # PnL only
    assert inflows[0].asset == quote_asset
    assert inflows[0].amount == Decimal("5000")  # Profit amount


def test_perpetual_get_outflow_asset_invalid_trade_type(
    order_details: OrderDetails,
) -> None:
    """Test getting outflow asset with invalid trade type."""
    order_details.trade_type = "INVALID"  # type: ignore
    with pytest.raises(ValueError, match="Unsupported trade type"):
        TestPerpetualBalanceEngine._get_outflow_asset(order_details)


def test_perpetual_get_outflow_asset_missing_collateral(
    order_details: OrderDetails,
) -> None:
    """Test getting outflow asset with missing collateral token."""
    order_details.trading_rule.buy_order_collateral_token = None
    order_details.trading_rule.sell_order_collateral_token = None
    with pytest.raises(
        ValueError, match="Collateral token not specified in trading rule"
    ):
        TestPerpetualBalanceEngine._get_outflow_asset(order_details)


def test_perpetual_calculate_pnl_missing_prices(order_details: OrderDetails) -> None:
    """Test PnL calculation with missing prices."""
    order_details.entry_price = None
    order_details.exit_price = None
    assert TestPerpetualBalanceEngine._calculate_pnl(order_details) == Decimal("0")


def test_inverse_calculate_pnl_missing_prices(order_details: OrderDetails) -> None:
    """Test inverse PnL calculation with missing prices."""
    order_details.entry_price = None
    order_details.exit_price = None
    assert TestInversePerpetualBalanceEngine._calculate_pnl(order_details) == Decimal(
        "0"
    )


def test_get_closing_inflows_open_position(
    order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test closing inflows for opening position."""
    order_details.position_action = PositionAction.OPEN
    order_details.exit_price = Decimal("55000")
    inflows = TestPerpetualBalanceEngine.get_closing_inflows(order_details)
    assert len(inflows) == 1  # Margin + PnL
    assert inflows[0].asset == quote_asset
    # Margin (5000) + PnL (5000) = 10000
    assert inflows[0].amount == Decimal("10000")
