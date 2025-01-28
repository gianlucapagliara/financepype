from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from eventspype.pub.publication import EventPublication

from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import OperationFee
from financepype.operations.orders.models import OrderType, TradeType


class OrderEvents(Enum):
    OrderCreated = 101
    OrderCompleted = 102
    OrderFailure = 103
    OrderExpired = 104
    OrderFilled = 105
    OrderCancelled = 106
    OrderCancelFailure = 107


@dataclass
class OrderEvent:
    timestamp: float
    client_operation_id: str
    order_type: OrderType
    trade_type: TradeType
    trading_pair: TradingPair
    exchange_order_id: str | None


@dataclass
class OrderCreatedEvent(OrderEvent):
    pass


@dataclass
class OrderFailureEvent(OrderEvent):
    pass


@dataclass
class OrderCompletedEvent(OrderEvent):
    base_asset: str
    quote_asset: str
    base_asset_amount: Decimal
    quote_asset_amount: Decimal


@dataclass
class OrderCancelledEvent(OrderEvent):
    pass


@dataclass
class OrderCancelFailureEvent(OrderEvent):
    pass


@dataclass
class OrderExpiredEvent(OrderEvent):
    pass


@dataclass
class OrderFilledEvent(OrderEvent):
    amount: Decimal
    trade_fee: OperationFee
    exchange_trade_id: str


class OrderPublications:
    """
    Class containing event publications for orders.

    Attributes:
        created_publication (EventPublication): Publication for order created events
        failure_publication (EventPublication): Publication for order failure events
        completed_publication (EventPublication): Publication for order completed events
        cancelled_publication (EventPublication): Publication for order cancelled events
        expired_publication (EventPublication): Publication for order expired events
        cancel_failure_publication (EventPublication): Publication for order cancel failure events
        filled_publication (EventPublication): Publication for order filled events
    """

    created_publication = EventPublication(
        OrderEvents.OrderCreated,
        OrderCreatedEvent,
    )
    failure_publication = EventPublication(
        OrderEvents.OrderFailure,
        OrderFailureEvent,
    )
    completed_publication = EventPublication(
        OrderEvents.OrderCompleted,
        OrderCompletedEvent,
    )
    cancelled_publication = EventPublication(
        OrderEvents.OrderCancelled,
        OrderCancelledEvent,
    )
    expired_publication = EventPublication(
        OrderEvents.OrderExpired,
        OrderExpiredEvent,
    )
    cancel_failure_publication = EventPublication(
        OrderEvents.OrderCancelFailure,
        OrderCancelFailureEvent,
    )
    filled_publication = EventPublication(
        OrderEvents.OrderFilled,
        OrderFilledEvent,
    )
