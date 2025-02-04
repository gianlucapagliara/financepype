from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, TradeType
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.simulations.balances.engines.models import (
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)
from financepype.simulations.balances.engines.spot import SpotBalanceEngine


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
def buy_order_details(
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
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def sell_order_details(
    platform: Platform,
    trading_pair: TradingPair,
    trading_rule: TradingRule,
    base_asset: Asset,
) -> OrderDetails:
    return OrderDetails(
        platform=platform,
        trading_pair=trading_pair,
        trading_rule=trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),
        leverage=1,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


def test_get_outflow_asset_buy(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting outflow asset for buy order."""
    assert SpotBalanceEngine._get_outflow_asset(buy_order_details) == quote_asset


def test_get_outflow_asset_sell(
    sell_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test getting outflow asset for sell order."""
    assert SpotBalanceEngine._get_outflow_asset(sell_order_details) == base_asset


def test_get_inflow_asset_buy(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test getting inflow asset for buy order."""
    assert SpotBalanceEngine._get_inflow_asset(buy_order_details) == base_asset


def test_get_inflow_asset_sell(
    sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting inflow asset for sell order."""
    assert SpotBalanceEngine._get_inflow_asset(sell_order_details) == quote_asset


def test_get_fee_impact_absolute(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee impact calculation with absolute fee."""
    buy_order_details.fee.asset = base_asset
    buy_order_details.fee.fee_type = FeeType.ABSOLUTE
    buy_order_details.fee.amount = Decimal("10")
    fee_impact = SpotBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[buy_order_details.fee.asset] == Decimal("10")


def test_get_fee_impact_percentage_same_asset(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee impact calculation with percentage fee in same asset."""
    fee_impact = SpotBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    # 0.1% of 50000 = 50
    assert quote_asset in fee_impact
    assert fee_impact[quote_asset] == Decimal("50")


def test_get_fee_impact_percentage_different_asset(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee impact calculation with percentage fee in different asset."""
    buy_order_details.fee.asset = base_asset
    with pytest.raises(NotImplementedError):
        SpotBalanceEngine._get_fee_impact(buy_order_details)


def test_get_fee_impact_invalid_type(buy_order_details: OrderDetails) -> None:
    """Test fee impact calculation with invalid fee type."""
    buy_order_details.fee.fee_type = "INVALID"  # type: ignore
    with pytest.raises(ValueError, match="Unsupported fee type"):
        SpotBalanceEngine._get_fee_impact(buy_order_details)


def test_get_involved_assets_buy(
    buy_order_details: OrderDetails, base_asset: Asset, quote_asset: Asset
) -> None:
    """Test getting involved assets for buy order."""
    assets = SpotBalanceEngine.get_involved_assets(buy_order_details)
    assert len(assets) == 4  # Cost outflow, Return inflow, Fee outflow
    assert assets[0].asset == quote_asset
    assert assets[0].involvement_type == InvolvementType.OPENING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION
    assert assets[1].asset == base_asset
    assert assets[1].involvement_type == InvolvementType.CLOSING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION
    assert assets[2].asset == quote_asset
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.FEE
    assert assets[3].asset == base_asset
    assert assets[3].involvement_type == InvolvementType.CLOSING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.FEE


def test_get_involved_assets_sell(
    sell_order_details: OrderDetails, base_asset: Asset, quote_asset: Asset
) -> None:
    """Test getting involved assets for sell order."""
    assets = SpotBalanceEngine.get_involved_assets(sell_order_details)
    assert len(assets) == 4  # Cost outflow, Return inflow, Fee outflow
    assert assets[0].asset == base_asset
    assert assets[0].involvement_type == InvolvementType.OPENING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION
    assert assets[1].asset == quote_asset
    assert assets[1].involvement_type == InvolvementType.CLOSING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION
    assert assets[2].asset == base_asset
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.FEE
    assert assets[3].asset == quote_asset
    assert assets[3].involvement_type == InvolvementType.CLOSING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.FEE


def test_get_opening_outflows_buy(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting opening outflows for buy order."""
    outflows = SpotBalanceEngine.get_opening_outflows(buy_order_details)
    assert len(outflows) == 2  # Cost and fee
    assert outflows[0].asset == quote_asset
    assert outflows[0].amount == Decimal("50000")  # amount * price
    assert outflows[1].asset == quote_asset
    assert outflows[1].amount == Decimal("50")  # 0.1% fee


def test_get_opening_outflows_sell(
    sell_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test getting opening outflows for sell order."""
    outflows = SpotBalanceEngine.get_opening_outflows(sell_order_details)
    assert len(outflows) == 2  # Cost and fee
    assert outflows[0].asset == base_asset
    assert outflows[0].amount == Decimal("1")  # amount
    assert outflows[1].asset == base_asset
    assert outflows[1].amount == Decimal("0.001")  # 0.1% fee


def test_get_opening_inflows(buy_order_details: OrderDetails) -> None:
    """Test getting opening inflows."""
    inflows = SpotBalanceEngine.get_opening_inflows(buy_order_details)
    assert len(inflows) == 0  # No opening inflows in spot trading


def test_get_closing_outflows_with_fee_deduction(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test getting closing outflows with fee deducted from returns."""
    buy_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    outflows = SpotBalanceEngine.get_closing_outflows(buy_order_details)
    assert len(outflows) == 1  # Fee only
    assert outflows[0].asset == base_asset
    assert outflows[0].amount == Decimal("0.001")  # 0.1% fee


def test_get_closing_inflows_buy(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test getting closing inflows for buy order."""
    inflows = SpotBalanceEngine.get_closing_inflows(buy_order_details)
    assert len(inflows) == 1  # Return only
    assert inflows[0].asset == base_asset
    assert inflows[0].amount == Decimal("1")  # amount


def test_get_closing_inflows_sell(
    sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting closing inflows for sell order."""
    inflows = SpotBalanceEngine.get_closing_inflows(sell_order_details)
    assert len(inflows) == 1  # Return only
    assert inflows[0].asset == quote_asset
    assert inflows[0].amount == Decimal("50000")  # amount * price


def test_get_fee_impact_buy_quote_currency_added_to_costs(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee calculation for BUY order with quote currency fee ADDED_TO_COSTS."""
    buy_order_details.fee.asset = quote_asset
    buy_order_details.fee.impact_type = FeeImpactType.ADDED_TO_COSTS
    fee_impact = SpotBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[quote_asset] == Decimal("50")  # 0.1% of notional (50000)


def test_get_fee_impact_buy_quote_currency_deducted_from_returns(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee calculation for BUY order with quote currency fee DEDUCTED_FROM_RETURNS."""
    buy_order_details.fee.asset = quote_asset
    buy_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    with pytest.raises(NotImplementedError):
        SpotBalanceEngine._get_fee_impact(buy_order_details)


def test_get_fee_impact_buy_base_currency_added_to_costs(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee calculation for BUY order with base currency fee ADDED_TO_COSTS."""
    buy_order_details.fee.asset = base_asset
    buy_order_details.fee.impact_type = FeeImpactType.ADDED_TO_COSTS
    with pytest.raises(NotImplementedError):
        SpotBalanceEngine._get_fee_impact(buy_order_details)


def test_get_fee_impact_buy_base_currency_deducted_from_returns(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee calculation for BUY order with base currency fee DEDUCTED_FROM_RETURNS."""
    buy_order_details.fee.asset = base_asset
    buy_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    fee_impact = SpotBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[base_asset] == Decimal("0.001")  # 0.1% of amount (1)


def test_get_fee_impact_sell_quote_currency_added_to_costs(
    sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee calculation for SELL order with quote currency fee ADDED_TO_COSTS."""
    sell_order_details.fee.asset = quote_asset
    sell_order_details.fee.impact_type = FeeImpactType.ADDED_TO_COSTS
    with pytest.raises(NotImplementedError):
        SpotBalanceEngine._get_fee_impact(sell_order_details)


def test_get_fee_impact_sell_quote_currency_deducted_from_returns(
    sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test fee calculation for SELL order with quote currency fee DEDUCTED_FROM_RETURNS."""
    sell_order_details.fee.asset = quote_asset
    sell_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    fee_impact = SpotBalanceEngine._get_fee_impact(sell_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[quote_asset] == Decimal("50")  # 0.1% of notional (50000)


def test_get_fee_impact_sell_base_currency_added_to_costs(
    sell_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee calculation for SELL order with base currency fee ADDED_TO_COSTS."""
    sell_order_details.fee.asset = base_asset
    sell_order_details.fee.impact_type = FeeImpactType.ADDED_TO_COSTS
    fee_impact = SpotBalanceEngine._get_fee_impact(sell_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[base_asset] == Decimal("0.001")  # 0.1% of amount (1)


def test_get_fee_impact_sell_base_currency_deducted_from_returns(
    sell_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test fee calculation for SELL order with base currency fee DEDUCTED_FROM_RETURNS."""
    sell_order_details.fee.asset = base_asset
    sell_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    with pytest.raises(NotImplementedError):
        SpotBalanceEngine._get_fee_impact(sell_order_details)
