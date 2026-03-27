from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


@dataclass(frozen=True, slots=True)
class PublicTrade:
    """Represents a public trade executed on an exchange.

    This class models individual trades that occur on an exchange and are visible
    to all market participants. It includes essential trade information such as
    price, amount, and timing.

    Attributes:
        trade_id (str): Unique identifier for the trade
        trading_pair (TradingPair): The trading pair involved
        price (Decimal): Execution price of the trade
        amount (Decimal): Amount traded in base currency
        side (TradeType): Whether the trade was a buy or sell
        time (datetime): When the trade occurred
        is_liquidation (bool): Whether this was a liquidation trade
    """

    trade_id: str
    trading_pair: TradingPair
    price: Decimal
    amount: Decimal
    side: TradeType
    time: datetime
    is_liquidation: bool

    def __post_init__(self) -> None:
        if self.price <= Decimal("0"):
            raise ValueError("Price must be greater than zero")
        if self.amount <= Decimal("0"):
            raise ValueError("Amount must be greater than zero")
