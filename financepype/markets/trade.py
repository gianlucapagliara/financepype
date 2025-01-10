from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


class PublicTrade(BaseModel):
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

    trade_id: str = Field(..., min_length=1)
    trading_pair: TradingPair
    price: Decimal
    amount: Decimal
    side: TradeType
    time: datetime
    is_liquidation: bool

    model_config = ConfigDict(frozen=True)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate that the trade price is positive.

        Args:
            v (Decimal): The price to validate

        Returns:
            Decimal: The validated price

        Raises:
            ValueError: If price is not greater than zero
        """
        if v <= Decimal("0"):
            raise ValueError("Price must be greater than zero")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate that the trade amount is positive.

        Args:
            v (Decimal): The amount to validate

        Returns:
            Decimal: The validated amount

        Raises:
            ValueError: If amount is not greater than zero
        """
        if v <= Decimal("0"):
            raise ValueError("Amount must be greater than zero")
        return v
