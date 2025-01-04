from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.constants import s_decimal_0, s_decimal_inf


class Position(BaseModel):
    asset: DerivativeContract
    amount: Decimal = Field(gt=s_decimal_0)
    leverage: Decimal = Field(gt=s_decimal_0)
    entry_price: Decimal = Field(gt=s_decimal_0)
    margin: Decimal = Field(ge=s_decimal_0)
    unrealized_pnl: Decimal
    liquidation_price: Decimal = Field(ge=s_decimal_0)

    @field_validator("liquidation_price", mode="before")
    def validate_liquidation_price(cls, v: Decimal) -> Decimal:
        return v if v > s_decimal_0 else s_decimal_0

    @property
    def unrealized_percentage_pnl(self) -> Decimal:
        return self.unrealized_pnl / self.margin * Decimal("100")

    @property
    def value(self) -> Decimal:
        return self.entry_price * self.amount

    @property
    def position_side(self) -> DerivativeSide:
        return self.asset.side

    @property
    def is_long(self) -> bool:
        return self.position_side == DerivativeSide.LONG

    @property
    def is_short(self) -> bool:
        return self.position_side == DerivativeSide.SHORT

    def distance_from_liquidation(self, price: Decimal) -> Decimal:
        distance = price - self.liquidation_price
        if self.is_short:
            distance = -distance
        return distance

    def percentage_from_liquidation(self, price: Decimal) -> Decimal:
        if self.liquidation_price == s_decimal_0:
            return s_decimal_inf
        return self.distance_from_liquidation(price) / self.liquidation_price

    def margin_distance_from_liquidation(self, price: Decimal) -> Decimal:
        margin = self.margin
        remaining_margin = margin + self.unrealized_pnl
        return remaining_margin

    def margin_percentage_from_liquidation(self, price: Decimal) -> Decimal:
        distance = self.margin_distance_from_liquidation(price)
        return distance / self.margin

    def is_at_liquidation_risk(
        self, price: Decimal, max_percentage: Decimal = Decimal("95")
    ) -> bool:
        percentage = self.margin_percentage_from_liquidation(price) * Decimal("100")
        risk = percentage <= max_percentage
        return risk
