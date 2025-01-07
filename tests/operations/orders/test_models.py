import pytest

from financepype.operations.orders.models import (
    OrderModifier,
    PositionAction,
    PositionMode,
    PriceType,
    TradeType,
)


def test_order_modifier() -> None:
    """Test OrderModifier enum."""
    assert OrderModifier.POST_ONLY in OrderModifier
    assert OrderModifier.REDUCE_ONLY in OrderModifier
    assert OrderModifier.IMMEDIATE_OR_CANCEL in OrderModifier
    assert OrderModifier.FILL_OR_KILL in OrderModifier
    assert OrderModifier.DAY in OrderModifier
    assert OrderModifier.AT_THE_OPEN in OrderModifier


def test_position_action() -> None:
    """Test PositionAction enum."""
    assert PositionAction.OPEN in PositionAction
    assert PositionAction.CLOSE in PositionAction
    assert PositionAction.FLIP in PositionAction
    assert PositionAction.NIL in PositionAction


def test_position_mode() -> None:
    """Test PositionMode enum."""
    assert PositionMode.HEDGE in PositionMode
    assert PositionMode.ONEWAY in PositionMode


def test_price_type() -> None:
    """Test PriceType enum."""
    assert PriceType.MidPrice in PriceType
    assert PriceType.BestBid in PriceType
    assert PriceType.BestAsk in PriceType
    assert PriceType.LastTrade in PriceType
    assert PriceType.LastOwnTrade in PriceType
    assert PriceType.InventoryCost in PriceType
    assert PriceType.Custom in PriceType


def test_trade_type() -> None:
    """Test TradeType enum."""
    assert TradeType.BUY in TradeType
    assert TradeType.SELL in TradeType
    assert TradeType.RANGE in TradeType

    # Test opposite trade type
    assert TradeType.BUY.opposite() == TradeType.SELL
    assert TradeType.SELL.opposite() == TradeType.BUY
    with pytest.raises(ValueError):
        TradeType.RANGE.opposite()
