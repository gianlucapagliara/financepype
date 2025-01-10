from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.constants import s_decimal_0, s_decimal_inf


class Position(BaseModel):
    """Represents a derivative trading position.

    This class models an open position in a derivative market, including its size,
    leverage, entry price, margin, and current profit/loss status.

    Attributes:
        asset (DerivativeContract): The derivative contract being traded
        amount (Decimal): Position size in base currency units
        leverage (Decimal): Position leverage multiplier
        entry_price (Decimal): Average entry price of the position
        entry_index_price (Decimal): Average entry index price of the position
        margin (Decimal): Amount of margin allocated to the position
        unrealized_pnl (Decimal): Current unrealized profit/loss
        liquidation_price (Decimal): Price at which position will be liquidated
    """

    asset: DerivativeContract
    amount: Decimal = Field(gt=s_decimal_0)
    leverage: Decimal = Field(gt=s_decimal_0)
    entry_price: Decimal = Field(gt=s_decimal_0)
    entry_index_price: Decimal = Field(gt=s_decimal_0)
    margin: Decimal = Field(ge=s_decimal_0)
    unrealized_pnl: Decimal
    liquidation_price: Decimal = Field(ge=s_decimal_0)

    @field_validator("liquidation_price", mode="before")
    def validate_liquidation_price(cls, v: Decimal) -> Decimal:
        """Validate and normalize the liquidation price.

        Args:
            v (Decimal): The liquidation price to validate

        Returns:
            Decimal: Validated liquidation price, minimum 0
        """
        return v if v > s_decimal_0 else s_decimal_0

    @property
    def unrealized_percentage_pnl(self) -> Decimal:
        """Calculate unrealized PnL as a percentage of margin.

        Returns:
            Decimal: Percentage PnL relative to margin
        """
        return self.unrealized_pnl / self.margin * Decimal("100")

    @property
    def value(self) -> Decimal:
        """Calculate the total value of the position.

        Returns:
            Decimal: Position value in quote currency
        """
        return self.entry_price * self.amount

    @property
    def position_side(self) -> DerivativeSide:
        """Get the side of the position (long/short).

        Returns:
            DerivativeSide: The position side
        """
        return self.asset.side

    @property
    def is_long(self) -> bool:
        """Check if position is long.

        Returns:
            bool: True if long position
        """
        return self.position_side == DerivativeSide.LONG

    @property
    def is_short(self) -> bool:
        """Check if position is short.

        Returns:
            bool: True if short position
        """
        return self.position_side == DerivativeSide.SHORT

    def distance_from_liquidation(self, price: Decimal) -> Decimal:
        """Calculate absolute distance from liquidation price.

        Args:
            price (Decimal): Current market price

        Returns:
            Decimal: Distance from liquidation in quote currency
        """
        distance = price - self.liquidation_price
        if self.is_short:
            distance = -distance
        return distance

    def percentage_from_liquidation(self, price: Decimal) -> Decimal:
        """Calculate percentage distance from liquidation price.

        Args:
            price (Decimal): Current market price

        Returns:
            Decimal: Percentage distance from liquidation
        """
        if self.liquidation_price == s_decimal_0:
            return s_decimal_inf
        return self.distance_from_liquidation(price) / self.liquidation_price

    def margin_distance_from_liquidation(self, price: Decimal) -> Decimal:
        """Calculate remaining margin before liquidation.

        Args:
            price (Decimal): Current market price

        Returns:
            Decimal: Remaining margin in quote currency
        """
        margin = self.margin
        remaining_margin = margin + self.unrealized_pnl
        return remaining_margin

    def margin_percentage_from_liquidation(self, price: Decimal) -> Decimal:
        """Calculate percentage of margin remaining before liquidation.

        Args:
            price (Decimal): Current market price

        Returns:
            Decimal: Percentage of initial margin remaining
        """
        distance = self.margin_distance_from_liquidation(price)
        return distance / self.margin

    def is_at_liquidation_risk(
        self, price: Decimal, max_percentage: Decimal = Decimal("95")
    ) -> bool:
        """Check if position is at risk of liquidation.

        Args:
            price (Decimal): Current market price
            max_percentage (Decimal): Maximum safe percentage threshold

        Returns:
            bool: True if position is at risk of liquidation
        """
        percentage = self.margin_percentage_from_liquidation(price) * Decimal("100")
        risk = percentage <= max_percentage
        return risk
