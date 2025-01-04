from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from financepype.markets.trade import PublicTrade
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


@pytest.fixture
def trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USD")


@pytest.fixture
def valid_trade_data(trading_pair: TradingPair) -> dict[str, Any]:
    return {
        "trade_id": "123456",
        "trading_pair": trading_pair,
        "price": Decimal("50000.00"),
        "amount": Decimal("1.5"),
        "side": TradeType.BUY,
        "time": datetime(2024, 1, 1, 12, 0, 0),
        "is_liquidation": False,
    }


def test_public_trade_initialization(valid_trade_data: dict[str, Any]) -> None:
    """Test successful initialization of PublicTrade with valid data."""
    trade = PublicTrade(**valid_trade_data)
    assert trade.trade_id == valid_trade_data["trade_id"]
    assert trade.trading_pair == valid_trade_data["trading_pair"]
    assert trade.price == valid_trade_data["price"]
    assert trade.amount == valid_trade_data["amount"]
    assert trade.side == valid_trade_data["side"]
    assert trade.time == valid_trade_data["time"]
    assert trade.is_liquidation == valid_trade_data["is_liquidation"]


def test_public_trade_immutability(valid_trade_data: dict[str, Any]) -> None:
    """Test that PublicTrade instances are immutable."""
    trade = PublicTrade(**valid_trade_data)
    with pytest.raises(ValidationError):
        trade.price = Decimal("55000.00")


def test_public_trade_validation(trading_pair: TradingPair) -> None:
    """Test validation of required fields."""
    # Test with empty values
    with pytest.raises(ValueError):
        PublicTrade(
            trade_id="",
            trading_pair=trading_pair,
            price=Decimal("0"),
            amount=Decimal("0"),
            side=TradeType.BUY,
            time=datetime.now(),
            is_liquidation=False,
        )


def test_public_trade_with_negative_price(valid_trade_data: dict[str, Any]) -> None:
    """Test that negative prices are rejected."""
    valid_trade_data["price"] = Decimal("-50000.00")
    with pytest.raises(ValueError):
        PublicTrade(**valid_trade_data)


def test_public_trade_with_negative_amount(valid_trade_data: dict[str, Any]) -> None:
    """Test that negative amounts are rejected."""
    valid_trade_data["amount"] = Decimal("-1.5")
    with pytest.raises(ValueError):
        PublicTrade(**valid_trade_data)


def test_public_trade_with_zero_price(valid_trade_data: dict[str, Any]) -> None:
    """Test that zero prices are rejected."""
    valid_trade_data["price"] = Decimal("0")
    with pytest.raises(ValueError):
        PublicTrade(**valid_trade_data)


def test_public_trade_with_zero_amount(valid_trade_data: dict[str, Any]) -> None:
    """Test that zero amounts are rejected."""
    valid_trade_data["amount"] = Decimal("0")
    with pytest.raises(ValueError):
        PublicTrade(**valid_trade_data)


def test_public_trade_equality(valid_trade_data: dict[str, Any]) -> None:
    """Test equality comparison of PublicTrade instances."""
    trade1 = PublicTrade(**valid_trade_data)
    trade2 = PublicTrade(**valid_trade_data)
    assert trade1 == trade2

    # Different trade_id should make trades unequal
    modified_data = valid_trade_data.copy()
    modified_data["trade_id"] = "789012"
    trade3 = PublicTrade(**modified_data)
    assert trade1 != trade3
