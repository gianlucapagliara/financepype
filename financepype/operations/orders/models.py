from enum import Enum

from financepype.assets.contract import DerivativeSide


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


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
