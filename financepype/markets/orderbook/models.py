from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from functools import total_ordering

from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


@dataclass
class OrderBookTradeEvent:
    trading_pair: TradingPair
    timestamp: float
    price: float
    amount: float
    type: TradeType


@dataclass
class OrderBookUpdateEvent:
    trading_pair: TradingPair
    timestamp: float


@dataclass
class OrderBookEntry:
    price: float
    amount: float
    update_id: int

    def __lt__(self, other: "OrderBookEntry") -> bool:
        return self.price < other.price

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderBookEntry):
            return NotImplemented
        return self.price == other.price


@dataclass
class OrderBookQueryResult:
    query_price: float
    query_volume: float
    result_price: float
    result_volume: float


@dataclass
class OrderBookRow:
    """
    Used to apply changes to OrderBook. OrderBook classes uses float internally for better performance over Decimal.
    """

    price: float
    amount: float
    update_id: int


@dataclass
class ClientOrderBookRow:
    """
    Used in market classes where OrderBook values are converted to Decimal.
    """

    price: Decimal
    amount: Decimal
    update_id: int


@dataclass
class ClientOrderBookQueryResult:
    query_price: Decimal
    query_volume: Decimal
    result_price: Decimal
    result_volume: Decimal


class OrderBookMessageType(Enum):
    SNAPSHOT = 1
    DIFF = 2
    TRADE = 3
    FUNDING = 4


class OrderBookEvent(Enum):
    """Events that can be emitted by the order book.

    Attributes:
        TradeEvent: Emitted when a trade occurs in the order book
        OrderBookUpdateEvent: Emitted when the order book state is updated
    """

    TradeEvent = "TradeEvent"
    OrderBookUpdateEvent = "OrderBookUpdateEvent"


@dataclass
@total_ordering
class BaseOrderBookMessage:
    """Base class for all order book messages."""

    type: OrderBookMessageType
    timestamp: float
    trading_pair: TradingPair

    def __lt__(self, other: "BaseOrderBookMessage") -> bool:
        if not isinstance(other, BaseOrderBookMessage):
            return NotImplemented
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        # Order book messages have priority over trade messages at same timestamp
        return isinstance(self, OrderBookUpdateMessage)


@dataclass
@total_ordering
class OrderBookUpdateMessage(BaseOrderBookMessage):
    """Message for order book updates (snapshots and diffs)."""

    update_id: int
    first_update_id: int = -1
    raw_asks: list[tuple[float, float]] = field(default_factory=list)
    raw_bids: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.type not in {OrderBookMessageType.SNAPSHOT, OrderBookMessageType.DIFF}:
            raise ValueError("Invalid message type for OrderBookUpdateMessage")
        if self.type == OrderBookMessageType.DIFF and self.first_update_id == -1:
            self.first_update_id = self.update_id

    @property
    def asks(self) -> list[OrderBookRow]:
        return [
            OrderBookRow(float(price), float(amount), self.update_id)
            for price, amount, *_ in self.raw_asks
        ]

    @property
    def bids(self) -> list[OrderBookRow]:
        return [
            OrderBookRow(float(price), float(amount), self.update_id)
            for price, amount, *_ in self.raw_bids
        ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderBookUpdateMessage):
            return NotImplemented
        return self.type == other.type and self.update_id == other.update_id

    def __hash__(self) -> int:
        return hash((self.type, self.update_id))

    def __lt__(self, other: "BaseOrderBookMessage") -> bool:
        if not isinstance(other, OrderBookUpdateMessage):
            return super().__lt__(other)
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.update_id < other.update_id


@dataclass
@total_ordering
class OrderBookTradeMessage(BaseOrderBookMessage):
    """Message for trade events."""

    trade_id: int
    price: float
    amount: float
    trade_type: TradeType

    def __post_init__(self) -> None:
        if self.type != OrderBookMessageType.TRADE:
            raise ValueError("Invalid message type for OrderBookTradeMessage")
        if self.trade_id == -1:
            raise ValueError("Trade ID is required for trade messages")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderBookTradeMessage):
            return NotImplemented
        return self.type == other.type and self.trade_id == other.trade_id

    def __hash__(self) -> int:
        return hash((self.type, self.trade_id))

    def __lt__(self, other: "BaseOrderBookMessage") -> bool:
        if not isinstance(other, OrderBookTradeMessage):
            return super().__lt__(other)
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.trade_id < other.trade_id
