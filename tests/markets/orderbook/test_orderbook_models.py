from decimal import Decimal

import pytest

from financepype.markets.orderbook.models import (
    BaseOrderBookMessage,
    ClientOrderBookQueryResult,
    ClientOrderBookRow,
    OrderBookEntry,
    OrderBookEvent,
    OrderBookMessageType,
    OrderBookQueryResult,
    OrderBookRow,
    OrderBookTradeEvent,
    OrderBookTradeMessage,
    OrderBookUpdateEvent,
    OrderBookUpdateMessage,
)
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


@pytest.fixture
def trading_pair() -> TradingPair:
    """Create a trading pair fixture for tests."""
    return TradingPair(name="BTC-USDT")


def test_order_book_trade_event(trading_pair: TradingPair) -> None:
    """Test OrderBookTradeEvent creation and attributes."""
    event = OrderBookTradeEvent(
        trading_pair=trading_pair,
        timestamp=1234567890.0,
        price=50000.0,
        amount=1.5,
        type=TradeType.BUY,
    )

    assert event.trading_pair == trading_pair
    assert event.timestamp == 1234567890.0
    assert event.price == 50000.0
    assert event.amount == 1.5
    assert event.type == TradeType.BUY


def test_order_book_update_event(trading_pair: TradingPair) -> None:
    """Test OrderBookUpdateEvent creation and attributes."""
    event = OrderBookUpdateEvent(
        trading_pair=trading_pair,
        timestamp=1234567890.0,
    )

    assert event.trading_pair == trading_pair
    assert event.timestamp == 1234567890.0


def test_order_book_entry_comparison() -> None:
    """Test OrderBookEntry comparison operations."""
    entry1 = OrderBookEntry(price=100.0, amount=1.0, update_id=1)
    entry2 = OrderBookEntry(price=200.0, amount=2.0, update_id=2)
    entry3 = OrderBookEntry(price=100.0, amount=3.0, update_id=3)

    # Test less than
    assert entry1 < entry2
    assert not entry2 < entry1

    # Test equality
    assert entry1 == entry3  # Same price means equal
    assert entry1 != entry2

    # Test comparison with non-OrderBookEntry
    assert entry1 != "not an entry"


def test_order_book_query_result() -> None:
    """Test OrderBookQueryResult creation and attributes."""
    result = OrderBookQueryResult(
        query_price=100.0,
        query_volume=1.0,
        result_price=98.5,
        result_volume=0.95,
    )

    assert result.query_price == 100.0
    assert result.query_volume == 1.0
    assert result.result_price == 98.5
    assert result.result_volume == 0.95


def test_order_book_row() -> None:
    """Test OrderBookRow creation and attributes."""
    row = OrderBookRow(price=100.0, amount=1.0, update_id=1)

    assert row.price == 100.0
    assert row.amount == 1.0
    assert row.update_id == 1


def test_client_order_book_row() -> None:
    """Test ClientOrderBookRow creation and attributes."""
    row = ClientOrderBookRow(
        price=Decimal("100.0"),
        amount=Decimal("1.0"),
        update_id=1,
    )

    assert row.price == Decimal("100.0")
    assert row.amount == Decimal("1.0")
    assert row.update_id == 1


def test_client_order_book_query_result() -> None:
    """Test ClientOrderBookQueryResult creation and attributes."""
    result = ClientOrderBookQueryResult(
        query_price=Decimal("100.0"),
        query_volume=Decimal("1.0"),
        result_price=Decimal("98.5"),
        result_volume=Decimal("0.95"),
    )

    assert result.query_price == Decimal("100.0")
    assert result.query_volume == Decimal("1.0")
    assert result.result_price == Decimal("98.5")
    assert result.result_volume == Decimal("0.95")


def test_order_book_message_type() -> None:
    """Test OrderBookMessageType enum values."""
    assert OrderBookMessageType.SNAPSHOT.value == 1
    assert OrderBookMessageType.DIFF.value == 2
    assert OrderBookMessageType.TRADE.value == 3
    assert OrderBookMessageType.FUNDING.value == 4


def test_order_book_event() -> None:
    """Test OrderBookEvent enum values."""
    assert OrderBookEvent.TradeEvent.value == "TradeEvent"
    assert OrderBookEvent.OrderBookUpdateEvent.value == "OrderBookUpdateEvent"


def test_base_order_book_message_comparison(trading_pair: TradingPair) -> None:
    """Test BaseOrderBookMessage comparison operations."""
    msg1 = BaseOrderBookMessage(
        type=OrderBookMessageType.SNAPSHOT,
        timestamp=1000.0,
        trading_pair=trading_pair,
    )
    msg2 = BaseOrderBookMessage(
        type=OrderBookMessageType.SNAPSHOT,
        timestamp=2000.0,
        trading_pair=trading_pair,
    )

    assert msg1 < msg2
    assert not msg2 < msg1
    assert msg1 != msg2


def test_order_book_update_message(trading_pair: TradingPair) -> None:
    """Test OrderBookUpdateMessage creation and validation."""
    # Test snapshot message
    snapshot = OrderBookUpdateMessage(
        type=OrderBookMessageType.SNAPSHOT,
        timestamp=1000.0,
        trading_pair=trading_pair,
        update_id=1,
        raw_asks=[(100.0, 1.0), (101.0, 2.0)],
        raw_bids=[(99.0, 1.0), (98.0, 2.0)],
    )

    assert snapshot.type == OrderBookMessageType.SNAPSHOT
    assert len(snapshot.asks) == 2
    assert len(snapshot.bids) == 2
    assert snapshot.asks[0].price == 100.0
    assert snapshot.bids[0].price == 99.0

    # Test diff message
    diff = OrderBookUpdateMessage(
        type=OrderBookMessageType.DIFF,
        timestamp=1001.0,
        trading_pair=trading_pair,
        update_id=2,
        raw_asks=[(102.0, 1.0)],
        raw_bids=[(97.0, 1.0)],
    )

    assert diff.type == OrderBookMessageType.DIFF
    assert diff.first_update_id == 2
    assert len(diff.asks) == 1
    assert len(diff.bids) == 1

    # Test invalid message type
    with pytest.raises(ValueError):
        OrderBookUpdateMessage(
            type=OrderBookMessageType.TRADE,
            timestamp=1002.0,
            trading_pair=trading_pair,
            update_id=3,
        )


def test_order_book_trade_message(trading_pair: TradingPair) -> None:
    """Test OrderBookTradeMessage creation and validation."""
    # Test valid trade message
    trade = OrderBookTradeMessage(
        type=OrderBookMessageType.TRADE,
        timestamp=1000.0,
        trading_pair=trading_pair,
        trade_id=1,
        price=100.0,
        amount=1.0,
        trade_type=TradeType.BUY,
    )

    assert trade.type == OrderBookMessageType.TRADE
    assert trade.trade_id == 1
    assert trade.price == 100.0
    assert trade.amount == 1.0
    assert trade.trade_type == TradeType.BUY

    # Test invalid message type
    with pytest.raises(ValueError):
        OrderBookTradeMessage(
            type=OrderBookMessageType.SNAPSHOT,
            timestamp=1001.0,
            trading_pair=trading_pair,
            trade_id=2,
            price=101.0,
            amount=2.0,
            trade_type=TradeType.SELL,
        )

    # Test invalid trade ID
    with pytest.raises(ValueError):
        OrderBookTradeMessage(
            type=OrderBookMessageType.TRADE,
            timestamp=1002.0,
            trading_pair=trading_pair,
            trade_id=-1,
            price=102.0,
            amount=3.0,
            trade_type=TradeType.BUY,
        )


def test_message_ordering(trading_pair: TradingPair) -> None:
    """Test ordering between different types of order book messages."""
    # Create messages with same timestamp but different types
    update = OrderBookUpdateMessage(
        type=OrderBookMessageType.SNAPSHOT,
        timestamp=1000.0,
        trading_pair=trading_pair,
        update_id=1,
    )
    trade = OrderBookTradeMessage(
        type=OrderBookMessageType.TRADE,
        timestamp=1000.0,
        trading_pair=trading_pair,
        trade_id=1,
        price=100.0,
        amount=1.0,
        trade_type=TradeType.BUY,
    )

    # Update messages should have priority over trade messages at same timestamp
    assert update < trade
    assert not trade < update

    # Create messages with different timestamps
    later_update = OrderBookUpdateMessage(
        type=OrderBookMessageType.SNAPSHOT,
        timestamp=1001.0,
        trading_pair=trading_pair,
        update_id=2,
    )
    later_trade = OrderBookTradeMessage(
        type=OrderBookMessageType.TRADE,
        timestamp=1001.0,
        trading_pair=trading_pair,
        trade_id=2,
        price=101.0,
        amount=2.0,
        trade_type=TradeType.SELL,
    )

    # Earlier messages should come before later messages
    assert update < later_update
    assert update < later_trade
    assert trade < later_update
    assert trade < later_trade
