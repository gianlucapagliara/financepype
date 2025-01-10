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
    InvolvementType,
    OrderDetails,
)
from financepype.simulations.balances.engines.option import (
    InverseOptionBalanceEngine,
    OptionBalanceEngine,
)


@pytest.fixture
def platform() -> Platform:
    return Platform(identifier="test")


@pytest.fixture
def trading_pair() -> TradingPair:
    return TradingPair(
        name="BTC-USDT-CALL_OPTION-1D-20240630-50000",
    )


@pytest.fixture
def inverse_trading_pair() -> TradingPair:
    return TradingPair(
        name="BTC-USD-INVERSE_CALL_OPTION-1D-20240630-50000",
    )


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
        buy_order_collateral_token="USDT",
        sell_order_collateral_token="USDT",
        other_rules={"option_margin_ratio": "0.1"},
    )


@pytest.fixture
def inverse_trading_rule(inverse_trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=inverse_trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("1000000"),
        buy_order_collateral_token="BTC",
        sell_order_collateral_token="BTC",
        other_rules={"option_margin_ratio": "0.1"},
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
        amount=Decimal("1"),  # 1 BTC contract size
        price=Decimal("1000"),  # Premium of 1000 USDT
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        entry_index_price=Decimal("50000"),
        fee=OperationFee(
            asset=quote_asset,
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
    quote_asset: Asset,
) -> OrderDetails:
    return OrderDetails(
        platform=platform,
        trading_pair=trading_pair,
        trading_rule=trading_rule,
        amount=Decimal("1"),  # 1 BTC contract size
        price=Decimal("1000"),  # Premium of 1000 USDT
        leverage=1,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        entry_index_price=Decimal("50000"),
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def inverse_buy_order_details(
    platform: Platform,
    inverse_trading_pair: TradingPair,
    inverse_trading_rule: TradingRule,
    base_asset: Asset,
) -> OrderDetails:
    return OrderDetails(
        platform=platform,
        trading_pair=inverse_trading_pair,
        trading_rule=inverse_trading_rule,
        amount=Decimal("50000"),  # $50,000 contract value
        price=Decimal("0.02"),  # Premium of 0.02 BTC
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        entry_index_price=Decimal("50000"),
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


def test_regular_option_fee_absolute(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test absolute fee calculation for regular options."""
    buy_order_details.fee.asset = quote_asset
    buy_order_details.fee.fee_type = FeeType.ABSOLUTE
    buy_order_details.fee.amount = Decimal("10")
    fee_impact = OptionBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    assert fee_impact[quote_asset] == Decimal("10")


def test_regular_option_fee_percentage_quote_currency(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test percentage fee in quote currency for regular options."""
    fee_impact = OptionBalanceEngine._get_fee_impact(buy_order_details)
    assert len(fee_impact) == 1
    # 0.1% of 1000 USDT premium = 1 USDT
    assert fee_impact[quote_asset] == Decimal("1")


def test_regular_option_fee_percentage_base_currency(
    buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test percentage fee in base currency for regular options."""
    buy_order_details.fee.asset = base_asset
    with pytest.raises(NotImplementedError):
        OptionBalanceEngine._get_fee_impact(buy_order_details)


def test_inverse_option_fee_absolute(
    inverse_buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test absolute fee calculation for inverse options."""
    inverse_buy_order_details.fee.asset = base_asset
    inverse_buy_order_details.fee.fee_type = FeeType.ABSOLUTE
    inverse_buy_order_details.fee.amount = Decimal("0.001")
    fee_impact = InverseOptionBalanceEngine._get_fee_impact(inverse_buy_order_details)
    assert len(fee_impact) == 1
    assert base_asset in fee_impact
    assert fee_impact[base_asset] == Decimal("0.001")


def test_inverse_option_fee_percentage_base_currency(
    inverse_buy_order_details: OrderDetails, base_asset: Asset
) -> None:
    """Test percentage fee in base currency for inverse options."""
    fee_impact = InverseOptionBalanceEngine._get_fee_impact(inverse_buy_order_details)
    assert len(fee_impact) == 1
    # 0.1% of 0.02 BTC premium = 0.00002 BTC
    assert fee_impact[base_asset] == Decimal("0.00002")


def test_inverse_option_fee_percentage_quote_currency(
    inverse_buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test percentage fee in quote currency for inverse options."""
    inverse_buy_order_details.fee.asset = quote_asset
    with pytest.raises(NotImplementedError):
        InverseOptionBalanceEngine._get_fee_impact(inverse_buy_order_details)


def test_regular_option_fee_added_to_costs(
    buy_order_details: OrderDetails,
) -> None:
    """Test fee added to costs for regular options."""
    outflows = OptionBalanceEngine.get_opening_outflows(buy_order_details, {})
    assert len(outflows) == 2  # Premium and fee
    assert outflows[0].reason == CashflowReason.OPERATION  # Premium
    assert outflows[1].reason == CashflowReason.FEE  # Fee
    assert outflows[1].amount == Decimal("1")  # 0.1% of 1000 USDT


def test_regular_option_fee_deducted_from_returns(
    buy_order_details: OrderDetails,
) -> None:
    """Test fee deducted from returns for regular options."""
    buy_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    outflows = OptionBalanceEngine.get_closing_outflows(buy_order_details, {})
    assert len(outflows) == 1  # Fee only
    assert outflows[0].reason == CashflowReason.FEE
    assert outflows[0].amount == Decimal("1")  # 0.1% of 1000 USDT


def test_inverse_option_fee_added_to_costs(
    inverse_buy_order_details: OrderDetails,
) -> None:
    """Test fee added to costs for inverse options."""
    outflows = InverseOptionBalanceEngine.get_opening_outflows(
        inverse_buy_order_details, {}
    )
    assert len(outflows) == 2  # Premium and fee
    assert outflows[0].reason == CashflowReason.OPERATION  # Premium
    assert outflows[1].reason == CashflowReason.FEE  # Fee
    assert outflows[1].amount == Decimal("0.00002")  # 0.1% of 0.02 BTC


def test_inverse_option_fee_deducted_from_returns(
    inverse_buy_order_details: OrderDetails,
) -> None:
    """Test fee deducted from returns for inverse options."""
    inverse_buy_order_details.fee.impact_type = FeeImpactType.DEDUCTED_FROM_RETURNS
    outflows = InverseOptionBalanceEngine.get_closing_outflows(
        inverse_buy_order_details, {}
    )
    assert len(outflows) == 1  # Fee only
    assert outflows[0].reason == CashflowReason.FEE
    assert outflows[0].amount == Decimal("0.00002")  # 0.1% of 0.02 BTC


def test_get_involved_assets_open_buy(
    buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for opening long option position."""
    assets = OptionBalanceEngine.get_involved_assets(buy_order_details)

    # Should have 3 cashflows:
    # 1. Premium payment (USDT outflow)
    # 2. Position asset outflow
    # 3. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 3

    # Check premium payment
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.OPENING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION

    # Check position asset flow
    position_asset = AssetFactory.get_asset(
        buy_order_details.platform,
        buy_order_details.trading_pair.name,
        side=buy_order_details.trade_type.to_position_side(),
    )
    assert assets[1].asset == position_asset
    assert assets[1].involvement_type == InvolvementType.OPENING
    assert assets[1].cashflow_type == CashflowType.OUTFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[2].asset == quote_asset
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.FEE


def test_get_involved_assets_open_sell(
    sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for opening short option position."""
    assets = OptionBalanceEngine.get_involved_assets(sell_order_details)

    # Should have 4 cashflows:
    # 1. Margin lock (USDT outflow)
    # 2. Premium receipt (USDT inflow)
    # 3. Position asset outflow
    # 4. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 4

    # Check margin lock
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.OPENING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION

    # Check premium receipt
    assert assets[1].asset == quote_asset  # USDT
    assert assets[1].involvement_type == InvolvementType.OPENING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    # Check position asset flow
    position_asset = AssetFactory.get_asset(
        sell_order_details.platform,
        sell_order_details.trading_pair.name,
        side=sell_order_details.trade_type.to_position_side(),
    )
    assert assets[2].asset == position_asset
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[3].asset == quote_asset
    assert assets[3].involvement_type == InvolvementType.OPENING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.FEE


@pytest.fixture
def close_buy_order_details(buy_order_details: OrderDetails) -> OrderDetails:
    """Fixture for closing a short position by buying."""
    buy_order_details.position_action = PositionAction.CLOSE
    return buy_order_details


def test_get_involved_assets_close_buy(
    close_buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for closing short option position by buying."""
    assets = OptionBalanceEngine.get_involved_assets(close_buy_order_details)

    # Should have 4 cashflows:
    # 1. Settlement payment (USDT outflow)
    # 2. Margin return (USDT inflow)
    # 3. Position asset inflow
    # 4. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 4

    # Check settlement payment
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.CLOSING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION

    # Check margin return
    assert assets[1].asset == quote_asset  # USDT
    assert assets[1].involvement_type == InvolvementType.CLOSING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    # Check position asset flow
    position_asset = AssetFactory.get_asset(
        close_buy_order_details.platform,
        close_buy_order_details.trading_pair.name,
        side=close_buy_order_details.trade_type.opposite().to_position_side(),
    )
    assert assets[2].asset == position_asset
    assert assets[2].involvement_type == InvolvementType.CLOSING
    assert assets[2].cashflow_type == CashflowType.INFLOW
    assert assets[2].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[3].asset == quote_asset
    assert assets[3].involvement_type == InvolvementType.OPENING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.FEE


@pytest.fixture
def close_sell_order_details(sell_order_details: OrderDetails) -> OrderDetails:
    """Fixture for closing a long position by selling."""
    sell_order_details.position_action = PositionAction.CLOSE
    return sell_order_details


def test_get_involved_assets_close_sell(
    close_sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for closing long option position by selling."""
    assets = OptionBalanceEngine.get_involved_assets(close_sell_order_details)

    # Should have 3 cashflows:
    # 1. Settlement receipt (USDT inflow)
    # 2. Position asset inflow
    # 3. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 3

    # Check settlement receipt
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.CLOSING
    assert assets[0].cashflow_type == CashflowType.INFLOW
    assert assets[0].reason == CashflowReason.PNL

    # Check position asset flow
    position_asset = AssetFactory.get_asset(
        close_sell_order_details.platform,
        close_sell_order_details.trading_pair.name,
        side=close_sell_order_details.trade_type.opposite().to_position_side(),
    )
    assert assets[1].asset == position_asset
    assert assets[1].involvement_type == InvolvementType.CLOSING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[2].asset == quote_asset
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.FEE


@pytest.fixture
def flip_buy_order_details(buy_order_details: OrderDetails) -> OrderDetails:
    """Fixture for flipping from short to long by buying."""
    buy_order_details.position_action = PositionAction.FLIP
    return buy_order_details


def test_get_involved_assets_flip_buy(
    flip_buy_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for flipping from short to long position."""
    assets = OptionBalanceEngine.get_involved_assets(flip_buy_order_details)

    # Should have 6 cashflows:
    # 1. Settlement payment (USDT outflow)
    # 2. Margin return (USDT inflow)
    # 3. Premium payment (USDT outflow)
    # 4. Opening position asset outflow
    # 5. Closing position asset inflow
    # 6. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 6

    # Check settlement payment
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.CLOSING
    assert assets[0].cashflow_type == CashflowType.OUTFLOW
    assert assets[0].reason == CashflowReason.OPERATION

    # Check margin return
    assert assets[1].asset == quote_asset  # USDT
    assert assets[1].involvement_type == InvolvementType.CLOSING
    assert assets[1].cashflow_type == CashflowType.INFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    # Check premium payment
    assert assets[2].asset == quote_asset  # USDT
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.OUTFLOW
    assert assets[2].reason == CashflowReason.OPERATION

    # Check opening position asset flow
    opening_position_asset = AssetFactory.get_asset(
        flip_buy_order_details.platform,
        flip_buy_order_details.trading_pair.name,
        side=flip_buy_order_details.trade_type.to_position_side(),
    )
    assert assets[3].asset == opening_position_asset
    assert assets[3].involvement_type == InvolvementType.OPENING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.OPERATION

    # Check closing position asset flow
    closing_position_asset = AssetFactory.get_asset(
        flip_buy_order_details.platform,
        flip_buy_order_details.trading_pair.name,
        side=flip_buy_order_details.trade_type.opposite().to_position_side(),
    )
    assert assets[4].asset == closing_position_asset
    assert assets[4].involvement_type == InvolvementType.CLOSING
    assert assets[4].cashflow_type == CashflowType.INFLOW
    assert assets[4].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[5].asset == quote_asset
    assert assets[5].involvement_type == InvolvementType.OPENING
    assert assets[5].cashflow_type == CashflowType.OUTFLOW
    assert assets[5].reason == CashflowReason.FEE


@pytest.fixture
def flip_sell_order_details(sell_order_details: OrderDetails) -> OrderDetails:
    """Fixture for flipping from long to short by selling."""
    sell_order_details.position_action = PositionAction.FLIP
    return sell_order_details


def test_get_involved_assets_flip_sell(
    flip_sell_order_details: OrderDetails, quote_asset: Asset
) -> None:
    """Test getting involved assets for flipping from long to short position."""
    assets = OptionBalanceEngine.get_involved_assets(flip_sell_order_details)

    # Should have 6 cashflows:
    # 1. Settlement receipt (USDT inflow)
    # 2. Margin lock (USDT outflow)
    # 3. Premium receipt (USDT inflow)
    # 4. Opening position asset outflow
    # 5. Closing position asset inflow
    # 6. Fee (if ADDED_TO_COSTS)
    assert len(assets) == 6

    # Check settlement receipt
    assert assets[0].asset == quote_asset  # USDT
    assert assets[0].involvement_type == InvolvementType.CLOSING
    assert assets[0].cashflow_type == CashflowType.INFLOW
    assert assets[0].reason == CashflowReason.PNL

    # Check margin lock and premium receipt
    assert assets[1].asset == quote_asset  # USDT
    assert assets[1].involvement_type == InvolvementType.OPENING
    assert assets[1].cashflow_type == CashflowType.OUTFLOW
    assert assets[1].reason == CashflowReason.OPERATION

    assert assets[2].asset == quote_asset  # USDT
    assert assets[2].involvement_type == InvolvementType.OPENING
    assert assets[2].cashflow_type == CashflowType.INFLOW
    assert assets[2].reason == CashflowReason.OPERATION

    # Check opening position asset flow
    opening_position_asset = AssetFactory.get_asset(
        flip_sell_order_details.platform,
        flip_sell_order_details.trading_pair.name,
        side=flip_sell_order_details.trade_type.to_position_side(),
    )
    assert assets[3].asset == opening_position_asset
    assert assets[3].involvement_type == InvolvementType.OPENING
    assert assets[3].cashflow_type == CashflowType.OUTFLOW
    assert assets[3].reason == CashflowReason.OPERATION

    # Check closing position asset flow
    closing_position_asset = AssetFactory.get_asset(
        flip_sell_order_details.platform,
        flip_sell_order_details.trading_pair.name,
        side=flip_sell_order_details.trade_type.opposite().to_position_side(),
    )
    assert assets[4].asset == closing_position_asset
    assert assets[4].involvement_type == InvolvementType.CLOSING
    assert assets[4].cashflow_type == CashflowType.INFLOW
    assert assets[4].reason == CashflowReason.OPERATION

    # Check fee
    assert assets[5].asset == quote_asset
    assert assets[5].involvement_type == InvolvementType.OPENING
    assert assets[5].cashflow_type == CashflowType.OUTFLOW
    assert assets[5].reason == CashflowReason.FEE
