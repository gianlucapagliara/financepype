from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType


class PublicTrade(BaseModel):
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
        if v <= Decimal("0"):
            raise ValueError("Price must be greater than zero")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Amount must be greater than zero")
        return v
