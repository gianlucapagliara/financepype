from decimal import Decimal
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel

from financepype.assets.contract import DerivativeSide
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import OperationFee


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"  # Deprecated

    def __new__(cls, value: object) -> Self:
        if value == "LIMIT_MAKER":
            print(
                "WARNING: LIMIT_MAKER is deprecated. Use LIMIT instead with POST_ONLY modifier."
            )
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def is_limit_type(self) -> bool:
        return self.name in [
            "LIMIT",
            "LIMIT_MAKER",
        ]  # Done by name to avoid __new__ warning

    def is_market_type(self) -> bool:
        return self == OrderType.MARKET


class OrderModifier(Enum):
    POST_ONLY = "POST_ONLY"
    REDUCE_ONLY = "REDUCE_ONLY"
    IMMEDIATE_OR_CANCEL = "IMMEDIATE_OR_CANCEL"
    FILL_OR_KILL = "FILL_OR_KILL"
    DAY = "DAY"
    AT_THE_OPEN = "AT_THE_OPEN"


class PositionAction(Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    FLIP = "FLIP"
    NIL = "NIL"


class PositionMode(Enum):
    HEDGE = "HEDGE"
    ONEWAY = "ONEWAY"


class PriceType(Enum):
    MidPrice = "MidPrice"
    BestBid = "BestBid"
    BestAsk = "BestAsk"
    LastTrade = "LastTrade"
    LastOwnTrade = "LastOwnTrade"
    InventoryCost = "InventoryCost"
    Custom = "Custom"


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    RANGE = "RANGE"

    def opposite(self) -> "TradeType":
        if self == TradeType.BUY:
            return TradeType.SELL
        elif self == TradeType.SELL:
            return TradeType.BUY
        else:
            raise ValueError("TradeType.RANGE does not have an opposite.")

    def to_position_side(self) -> DerivativeSide:
        if self == TradeType.BUY:
            return DerivativeSide.LONG
        elif self == TradeType.SELL:
            return DerivativeSide.SHORT
        else:
            return DerivativeSide.BOTH


class OrderState(Enum):
    PENDING_CREATE = "pending_create"  # Initial state -> waiting for exchange to create order (order not yet in order book)
    OPEN = "open"  # Ready to be filled
    PARTIALLY_FILLED = "partially_filled"  # Partially filled
    PENDING_CANCEL = "pending_cancel"  # User requested cancellation of order -> waiting for confirmation from exchange
    CANCELED = "canceled"  # Order was cancelled by user
    FILLED = "filled"  # Order completely filled -> completed
    FAILED = "failed"  # Order failed to be created by the exchange


class OrderUpdate(BaseModel):
    """A class representing an update to an order's state.

    This class contains information about changes to an order's state,
    including new state, timestamps, and identifiers.
    """

    trading_pair: TradingPair
    update_timestamp: float  # seconds
    new_state: OrderState
    client_order_id: str | None = None
    exchange_order_id: str | None = None
    misc_updates: dict[str, Any] | None = None


class TradeUpdate(BaseModel):
    """A class representing a trade update for an order.

    This class contains information about a trade that has occurred,
    including fill details, prices, amounts, and fees.
    """

    trade_id: str
    client_order_id: str | None = None
    exchange_order_id: str
    trading_pair: TradingPair
    trade_type: TradeType
    fill_timestamp: float  # seconds
    fill_price: Decimal
    fill_base_amount: Decimal
    fill_quote_amount: Decimal
    fee: OperationFee
    group_order_id: str = ""

    @property
    def group_client_order_id(self) -> str | None:
        return (
            f"{self.group_order_id}{self.client_order_id}"
            if self.client_order_id is not None and self.group_order_id is not None
            else None
        )
