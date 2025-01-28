from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.assets.spot import SpotAsset
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import (
    OrderState,
    OrderType,
    OrderUpdate,
    TradeType,
    TradeUpdate,
)
from financepype.operations.orders.order import OrderOperation
from financepype.owners.owner import NamedOwnerIdentifier, OwnerIdentifier
from financepype.platforms.platform import Platform


@pytest.fixture
def test_platform() -> Platform:
    """Create a test platform."""
    return Platform(identifier="test_platform")


@pytest.fixture
def test_trading_pair() -> TradingPair:
    """Create a test trading pair."""
    return TradingPair(name="BTC-USDT")


@pytest.fixture
def test_quote_asset(test_platform: Platform) -> Asset:
    """Create a test quote asset."""
    return AssetFactory.get_asset(test_platform, "USDT")


@pytest.fixture
def test_owner_id(test_platform: Platform) -> OwnerIdentifier:
    """Create a test owner identifier."""
    return NamedOwnerIdentifier(name="test_owner", platform=test_platform)


@pytest.fixture
def test_order(
    test_platform: Platform,
    test_trading_pair: TradingPair,
    test_owner_id: OwnerIdentifier,
) -> OrderOperation:
    """Create a test order operation."""
    return OrderOperation(
        client_operation_id="test_order_1",
        trading_pair=test_trading_pair,
        order_type=OrderType.LIMIT,
        trade_type=TradeType.BUY,
        amount=Decimal("1.0"),
        price=Decimal("50000"),
        creation_timestamp=1640995200.0,
        owner_identifier=test_owner_id,
        current_state=OrderState.PENDING_CREATE,
    )


def test_order_operation_initialization(test_order: OrderOperation) -> None:
    """Test OrderOperation initialization."""
    assert test_order.client_operation_id == "test_order_1"
    assert test_order.operator_operation_id is None
    assert test_order.current_state == OrderState.PENDING_CREATE
    assert test_order.amount == Decimal("1.0")
    assert test_order.price == Decimal("50000")
    assert test_order.executed_amount_base == Decimal("0")
    assert test_order.executed_amount_quote == Decimal("0")
    assert test_order.order_fills == {}


def test_order_operation_properties(test_order: OrderOperation) -> None:
    """Test OrderOperation properties."""
    assert test_order.filled_amount == Decimal("0")
    assert test_order.remaining_amount == Decimal("1.0")
    assert test_order.is_limit is True
    assert test_order.is_market is False
    assert test_order.is_buy is True
    assert test_order.average_executed_price is None
    assert test_order.is_pending_create is True
    assert test_order.is_open is True
    assert test_order.is_done is False
    assert test_order.is_filled is False
    assert test_order.is_failure is False
    assert test_order.is_cancelled is False


def test_order_operation_update_with_order_update(test_order: OrderOperation) -> None:
    """Test OrderOperation update with OrderUpdate."""
    update = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995300.0,
        new_state=OrderState.OPEN,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )

    result = test_order.process_operation_update(update)
    assert result is True
    assert test_order.current_state == OrderState.OPEN
    assert test_order.operator_operation_id == "ex_order_1"
    assert test_order.last_update_timestamp == 1640995300.0


def test_order_operation_update_with_trade_update(
    test_order: OrderOperation, test_quote_asset: SpotAsset
) -> None:
    """Test OrderOperation update with TradeUpdate."""
    # First set the order to OPEN state
    open_update = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995300.0,
        new_state=OrderState.OPEN,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )
    test_order.process_operation_update(open_update)

    # Then process a trade update
    fee = OperationFee(
        amount=Decimal("1"),
        asset=test_quote_asset,
        fee_type=FeeType.PERCENTAGE,
        impact_type=FeeImpactType.ADDED_TO_COSTS,
    )

    trade_update = TradeUpdate(
        trade_id="trade_1",
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
        trading_pair=test_order.trading_pair,
        trade_type=TradeType.BUY,
        fill_timestamp=1640995400.0,
        fill_price=Decimal("50000"),
        fill_base_amount=Decimal("0.5"),
        fill_quote_amount=Decimal("25000"),
        fee=fee,
    )

    result = test_order.process_operation_update(trade_update)
    assert result is True
    assert test_order.executed_amount_base == Decimal("0.5")
    assert test_order.executed_amount_quote == Decimal("25000")
    assert test_order.current_state == OrderState.OPEN
    assert test_order.last_update_timestamp == 1640995400.0
    assert test_order.average_executed_price == Decimal("50000")


def test_order_operation_complete_fill(
    test_order: OrderOperation, test_quote_asset: SpotAsset
) -> None:
    """Test OrderOperation complete fill process."""
    # Set the order to OPEN state
    open_update = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995300.0,
        new_state=OrderState.OPEN,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )
    test_order.process_operation_update(open_update)

    # Process complete fill
    fee = OperationFee(
        amount=Decimal("1"),
        asset=test_quote_asset,
        fee_type=FeeType.PERCENTAGE,
        impact_type=FeeImpactType.ADDED_TO_COSTS,
    )

    trade_update = TradeUpdate(
        trade_id="trade_1",
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
        trading_pair=test_order.trading_pair,
        trade_type=TradeType.BUY,
        fill_timestamp=1640995400.0,
        fill_price=Decimal("50000"),
        fill_base_amount=Decimal("1.0"),
        fill_quote_amount=Decimal("50000"),
        fee=fee,
    )

    result = test_order.process_operation_update(trade_update)
    assert result is True
    assert test_order.executed_amount_base == Decimal("1.0")
    assert test_order.executed_amount_quote == Decimal("50000")
    assert test_order.current_state == OrderState.FILLED
    assert test_order.last_update_timestamp == 1640995400.0
    assert test_order.average_executed_price == Decimal("50000")
    assert test_order.is_filled is True
    assert test_order.is_done is True


def test_order_operation_cancellation(test_order: OrderOperation) -> None:
    """Test OrderOperation cancellation process."""
    # First set the order to OPEN state
    open_update = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995300.0,
        new_state=OrderState.OPEN,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )
    test_order.process_operation_update(open_update)

    # Request cancellation
    cancel_request = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995400.0,
        new_state=OrderState.PENDING_CANCEL,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )
    test_order.process_operation_update(cancel_request)

    assert test_order.current_state == OrderState.PENDING_CANCEL
    assert test_order.is_pending_cancel_confirmation is True
    assert test_order.is_open is True

    # Confirm cancellation
    cancel_confirm = OrderUpdate(
        trading_pair=test_order.trading_pair,
        update_timestamp=1640995500.0,
        new_state=OrderState.CANCELED,
        client_order_id="test_order_1",
        exchange_order_id="ex_order_1",
    )
    test_order.process_operation_update(cancel_confirm)

    assert test_order.current_state == OrderState.CANCELED
    assert test_order.is_cancelled is True
    assert test_order.is_done is True
    assert test_order.is_open is False
