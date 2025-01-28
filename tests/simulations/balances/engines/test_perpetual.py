from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.markets.position import Position
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
    return TradingPair(name="BTC-USDT-PERPETUAL")


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
        index_price=Decimal("50000"),
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
    assert TestPerpetualBalanceEngine._calculate_margin(order_details) == Decimal(
        "5000"
    )


def test_inverse_calculate_margin(order_details: OrderDetails) -> None:
    """Test margin calculation for inverse perpetual."""
    # amount / (leverage * price) = 1 / (10 * 50000) = 0.000002
    assert TestInversePerpetualBalanceEngine._calculate_margin(
        order_details
    ) == Decimal("0.000002")


def test_perpetual_calculate_pnl_long_profit(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test PnL calculation for regular perpetual long position with profit."""
    # Create a new order details with entry price
    entry_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),  # Entry price
        leverage=10,
        trade_type=order_details.trade_type,
        order_type=order_details.order_type,
        position_action=order_details.position_action,
        index_price=Decimal("50000"),
        fee=order_details.fee,
    )
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.LONG,
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("45000"),
    )
    # Create a new order details for closing at a higher price
    close_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("55000"),  # Exit price
        leverage=10,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("55000"),
        current_position=position,
        fee=order_details.fee,
    )
    # (exit_price - entry_price) * amount = (55000 - 50000) * 1 = 5000
    assert TestPerpetualBalanceEngine._calculate_pnl(close_details) == Decimal("5000")


def test_perpetual_calculate_pnl_short_profit(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test PnL calculation for regular perpetual short position with profit."""
    # Create a new order details with entry price
    entry_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),  # Entry price
        leverage=10,
        trade_type=TradeType.SELL,
        order_type=order_details.order_type,
        position_action=order_details.position_action,
        index_price=Decimal("50000"),
        fee=order_details.fee,
    )
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for closing at a lower price
    close_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("45000"),  # Exit price
        leverage=10,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("45000"),
        current_position=position,
        fee=order_details.fee,
    )
    # (entry_price - exit_price) * amount = (50000 - 45000) * 1 = 5000
    assert TestPerpetualBalanceEngine._calculate_pnl(close_details) == Decimal("5000")


def test_inverse_calculate_pnl_long_profit(
    order_details: OrderDetails, base_asset: Asset, platform: Platform
) -> None:
    """Test PnL calculation for inverse perpetual long position with profit."""
    # Create a new order details with entry price
    entry_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),  # Entry price
        leverage=10,
        trade_type=order_details.trade_type,
        order_type=order_details.order_type,
        position_action=order_details.position_action,
        index_price=Decimal("50000"),
        fee=order_details.fee,
    )
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.LONG,
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("0.000002"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("45000"),
    )
    # Create a new order details for closing at a higher price
    close_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("55000"),  # Exit price
        leverage=10,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("55000"),
        current_position=position,
        fee=order_details.fee,
    )
    # contract_value * (1/entry_price - 1/exit_price) = 1 * (1/50000 - 1/55000)
    expected = Decimal("1") * (
        Decimal("1") / Decimal("50000") - Decimal("1") / Decimal("55000")
    )
    assert TestInversePerpetualBalanceEngine._calculate_pnl(close_details) == expected


def test_inverse_calculate_pnl_short_profit(
    order_details: OrderDetails, base_asset: Asset, platform: Platform
) -> None:
    """Test PnL calculation for inverse perpetual short position with profit."""
    # Create a new order details with entry price
    entry_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("50000"),  # Entry price
        leverage=10,
        trade_type=TradeType.SELL,
        order_type=order_details.order_type,
        position_action=order_details.position_action,
        index_price=Decimal("50000"),
        fee=order_details.fee,
    )
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("0.000002"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for closing at a lower price
    close_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("45000"),  # Exit price
        leverage=10,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("45000"),
        current_position=position,
        fee=order_details.fee,
    )
    # contract_value * (1/exit_price - 1/entry_price) = 1 * (1/45000 - 1/50000)
    expected = Decimal("1") * (
        Decimal("1") / Decimal("45000") - Decimal("1") / Decimal("50000")
    )
    assert TestInversePerpetualBalanceEngine._calculate_pnl(close_details) == expected


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
    assert len(assets) == 3  # Margin outflow, Opening fee outflow, Position inflow
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.MARGIN
        for a in assets
    ), "Missing margin outflow"
    assert any(
        a.cashflow_type == CashflowType.INFLOW and a.reason == CashflowReason.OPERATION
        for a in assets
    ), "Missing position inflow"
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.FEE
        and a.involvement_type == InvolvementType.OPENING
        for a in assets
    ), "Missing opening fee"


def test_get_involved_assets_close(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test involved assets for closing position."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details with close position action
    close_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to close SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.CLOSE,
        index_price=order_details.index_price,
        current_position=position,
        fee=order_details.fee,
    )
    assets = TestPerpetualBalanceEngine.get_involved_assets(close_order_details)
    assert len(assets) == 4  # Position outflow, Margin return, PnL flow, Closing fee
    assert any(
        a.asset == contract
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.OPERATION
        for a in assets
    ), "Missing position outflow"
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.INFLOW
        and a.reason == CashflowReason.MARGIN
        for a in assets
    ), "Missing margin return"
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.INFLOW
        and a.reason == CashflowReason.PNL
        for a in assets
    ), "Missing PnL flow"
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.FEE
        and a.involvement_type == InvolvementType.CLOSING
        for a in assets
    ), "Missing closing fee"


def test_get_involved_assets_flip(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test involved assets for flipping position."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("0.5"),  # Smaller than the order amount (1.0)
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("2500"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for flipping
    flip_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,  # 1.0 > 0.5 (position amount)
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to flip from SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.FLIP,
        index_price=order_details.index_price,
        current_position=position,
        fee=order_details.fee,
    )
    assets = TestPerpetualBalanceEngine.get_involved_assets(flip_order_details)
    # Should have 7 asset flows:
    # 1. Existing position outflow (opening)
    # 2. New margin outflow (opening)
    # 3. New position inflow (closing)
    # 4. PnL flow (closing)
    # 5. Opening fee outflow
    # 6. Closing fee outflow
    # 7. Old margin inflow (closing)
    assert len(assets) == 7

    # Verify opening flows
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.MARGIN
        and a.involvement_type == InvolvementType.OPENING
        for a in assets
    ), "Missing margin outflow"

    assert any(
        a.asset == contract
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.OPERATION
        and a.involvement_type == InvolvementType.OPENING
        for a in assets
    ), "Missing position outflow"

    # Verify closing flows
    assert any(
        isinstance(a.asset, DerivativeContract)
        and a.cashflow_type == CashflowType.INFLOW
        and a.reason == CashflowReason.OPERATION
        and a.involvement_type == InvolvementType.CLOSING
        for a in assets
    ), "Missing position inflow"

    assert any(
        a.asset == quote_asset
        and a.reason == CashflowReason.PNL
        and a.involvement_type == InvolvementType.CLOSING
        for a in assets
    ), "Missing PnL flow"

    # Verify fee flows
    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.FEE
        and a.involvement_type == InvolvementType.OPENING
        for a in assets
    ), "Missing opening fee"

    assert any(
        a.asset == quote_asset
        and a.cashflow_type == CashflowType.OUTFLOW
        and a.reason == CashflowReason.FEE
        and a.involvement_type == InvolvementType.CLOSING
        for a in assets
    ), "Missing closing fee"


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


def test_get_closing_outflows_with_fee_deduction(
    order_details: OrderDetails, platform: Platform
) -> None:
    """Test closing outflows with fee deducted from returns."""
    # Create a position to close
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details with CLOSE position action and fee deducted from returns
    close_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,
        order_type=order_details.order_type,
        position_action=PositionAction.CLOSE,
        index_price=order_details.index_price,
        current_position=position,
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
        ),
    )
    outflows = TestPerpetualBalanceEngine.get_closing_outflows(close_order_details)
    assert len(outflows) == 1  # Fee only
    assert outflows[0].reason == CashflowReason.FEE
    assert outflows[0].involvement_type == InvolvementType.CLOSING


def test_get_closing_inflows_with_profit(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test closing inflows with profit."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for closing with profit
    close_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("45000"),  # Lower than entry price for profit on SHORT
        leverage=10,
        trade_type=TradeType.BUY,  # BUY to close SHORT
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("45000"),
        current_position=position,
        fee=order_details.fee,
    )
    inflows = TestPerpetualBalanceEngine.get_closing_inflows(close_order_details)
    assert len(inflows) == 2  # Margin return and PnL
    assert inflows[0].asset == quote_asset
    assert inflows[0].amount == Decimal("5000")  # Margin amount
    assert inflows[1].asset == quote_asset
    assert inflows[1].amount == Decimal("5000")  # PnL amount


def test_get_closing_inflows_open_position(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test closing inflows for opening position."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("1"),
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for closing
    close_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=Decimal("1"),
        price=Decimal("45000"),
        leverage=10,
        trade_type=TradeType.BUY,  # BUY to close SHORT
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("45000"),
        current_position=position,
        fee=order_details.fee,
    )
    inflows = TestPerpetualBalanceEngine.get_closing_inflows(close_order_details)
    assert len(inflows) == 2  # Margin return and PnL
    assert inflows[0].asset == quote_asset
    assert inflows[0].amount == Decimal("5000")  # Margin amount
    assert inflows[1].asset == quote_asset
    assert inflows[1].amount == Decimal("5000")  # PnL amount


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
    # Create a new order details with OPEN position action
    open_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,
        order_type=order_details.order_type,
        position_action=PositionAction.OPEN,
        index_price=order_details.index_price,
        fee=order_details.fee,
    )
    assert TestPerpetualBalanceEngine._calculate_pnl(open_order_details) == Decimal("0")


def test_inverse_calculate_pnl_missing_prices(order_details: OrderDetails) -> None:
    """Test inverse PnL calculation with missing prices."""
    # Create a new order details with OPEN position action
    open_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,
        order_type=order_details.order_type,
        position_action=PositionAction.OPEN,
        index_price=order_details.index_price,
        fee=order_details.fee,
    )
    assert TestInversePerpetualBalanceEngine._calculate_pnl(
        open_order_details
    ) == Decimal("0")


def test_get_opening_outflows_flip(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test opening outflows for flip operation."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("0.5"),  # Smaller than the order amount (1.0)
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("2500"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for flipping
    flip_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,  # 1.0 > 0.5 (position amount)
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to flip from SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.FLIP,
        index_price=order_details.index_price,
        current_position=position,
        fee=order_details.fee,
    )
    outflows = TestPerpetualBalanceEngine.get_opening_outflows(flip_order_details)
    assert len(outflows) == 3  # Margin outflow, Position outflow, Fee outflow

    # Verify margin outflow
    margin_outflow = next(
        (
            flow
            for flow in outflows
            if flow.asset == quote_asset
            and flow.reason == CashflowReason.MARGIN
            and flow.involvement_type == InvolvementType.OPENING
        ),
        None,
    )
    assert margin_outflow is not None
    assert margin_outflow.amount == Decimal("2500")  # Current position margin

    # Verify position outflow
    position_outflow = next(
        (
            flow
            for flow in outflows
            if isinstance(flow.asset, DerivativeContract)
            and flow.reason == CashflowReason.OPERATION
            and flow.involvement_type == InvolvementType.OPENING
        ),
        None,
    )
    assert position_outflow is not None
    assert position_outflow.amount == Decimal("0.5")  # Current position amount

    # Verify fee outflow
    fee_outflow = next(
        (
            flow
            for flow in outflows
            if flow.asset == quote_asset
            and flow.reason == CashflowReason.FEE
            and flow.involvement_type == InvolvementType.OPENING
        ),
        None,
    )
    assert fee_outflow is not None
    assert fee_outflow.amount == Decimal("25")  # 0.1% of notional value (50000 * 0.5)


def test_get_closing_outflows_flip(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test closing outflows for flip operation."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("0.5"),  # Smaller than the order amount (1.0)
        leverage=Decimal("10"),
        entry_price=Decimal("45000"),  # Lower entry price
        entry_index_price=Decimal("45000"),
        margin=Decimal("2500"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for flipping with a higher price to ensure negative PnL for SHORT
    flip_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,  # 1.0 > 0.5 (position amount)
        price=Decimal("50000"),  # Higher price for negative PnL on SHORT
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to flip from SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.FLIP,
        index_price=Decimal("50000"),
        current_position=position,
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
        ),
    )
    outflows = TestPerpetualBalanceEngine.get_closing_outflows(flip_order_details)
    assert len(outflows) == 2  # Fee and negative PnL

    # Verify fee outflow
    fee_outflow = next(
        (
            flow
            for flow in outflows
            if flow.asset == quote_asset
            and flow.reason == CashflowReason.FEE
            and flow.involvement_type == InvolvementType.CLOSING
        ),
        None,
    )
    assert fee_outflow is not None
    assert fee_outflow.amount == Decimal("25")  # 0.1% of notional value (25000)

    # Verify PnL outflow
    pnl_outflow = next(
        (
            flow
            for flow in outflows
            if flow.asset == quote_asset
            and flow.reason == CashflowReason.PNL
            and flow.involvement_type == InvolvementType.CLOSING
        ),
        None,
    )
    assert pnl_outflow is not None
    assert pnl_outflow.amount == Decimal("2500")  # (50000 - 45000) * 0.5 = 2500 loss


def test_get_closing_inflows_flip(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test closing inflows for flip operation."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("0.5"),  # Smaller than the order amount (1.0)
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("2500"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for flipping with a higher price to ensure positive PnL
    flip_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,  # 1.0 > 0.5 (position amount)
        price=Decimal("55000"),  # Higher price for positive PnL on SHORT
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to flip from SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.FLIP,
        index_price=Decimal("55000"),
        current_position=position,
        fee=order_details.fee,
    )
    inflows = TestPerpetualBalanceEngine.get_closing_inflows(flip_order_details)
    assert len(inflows) == 2  # Margin return and position inflow

    # Verify position inflow
    position_inflow = next(
        (
            flow
            for flow in inflows
            if isinstance(flow.asset, DerivativeContract)
            and flow.reason == CashflowReason.OPERATION
            and flow.involvement_type == InvolvementType.CLOSING
        ),
        None,
    )
    assert position_inflow is not None
    assert position_inflow.amount == Decimal("0.5")  # Current position amount


def test_get_opening_inflows_flip(
    order_details: OrderDetails, quote_asset: Asset, platform: Platform
) -> None:
    """Test opening inflows for flip operation."""
    # Create a position with the opposite side of the trade type
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=order_details.trading_pair.name),
        side=DerivativeSide.SHORT,  # Opposite of BUY which is LONG
    )
    position = Position(
        asset=contract,
        amount=Decimal("0.5"),  # Smaller than the order amount (1.0)
        leverage=Decimal("10"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("2500"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("55000"),
    )
    # Create a new order details for flipping
    flip_order_details = OrderDetails(
        platform=order_details.platform,
        trading_pair=order_details.trading_pair,
        trading_rule=order_details.trading_rule,
        amount=order_details.amount,  # 1.0 > 0.5 (position amount)
        price=order_details.price,
        leverage=order_details.leverage,
        trade_type=order_details.trade_type,  # BUY to flip from SHORT
        order_type=order_details.order_type,
        position_action=PositionAction.FLIP,
        index_price=order_details.index_price,
        current_position=position,
        fee=order_details.fee,
    )
    inflows = TestPerpetualBalanceEngine.get_opening_inflows(flip_order_details)
    # No inflows for flip operation in opening phase
    assert len(inflows) == 0
