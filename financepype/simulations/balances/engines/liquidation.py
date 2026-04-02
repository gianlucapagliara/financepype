"""Liquidation price calculation for perpetual futures positions."""

from decimal import Decimal


class LiquidationPriceCalculator:
    """Static methods for computing liquidation prices.

    Supports both linear (quote-margined) and inverse (base-margined) contracts
    in isolated margin mode.
    """

    @staticmethod
    def calculate_simple(
        is_inverse: bool,
        is_long: bool,
        entry_price: Decimal,
        amount: Decimal,
        leverage: Decimal,
    ) -> Decimal:
        """Basic liquidation price for isolated margin without tiered MMR.

        Formulas:
            Linear long:   entry * (1 - 1/leverage)
            Linear short:  entry * (1 + 1/leverage)
            Inverse long:  entry / (1 + 1/leverage)
            Inverse short: entry / (1 - 1/leverage)

        Args:
            is_inverse: True if this is an inverse (base-margined) contract.
            is_long: True if position is long.
            entry_price: Average entry price of the position.
            amount: Position size (base units for linear, USD notional for inverse).
            leverage: Position leverage multiplier.

        Returns:
            Liquidation price as a Decimal.
        """
        inv_leverage = Decimal("1") / leverage
        if is_inverse:
            if is_long:
                return entry_price / (Decimal("1") + inv_leverage)
            else:
                return entry_price / (Decimal("1") - inv_leverage)
        else:
            if is_long:
                return entry_price * (Decimal("1") - inv_leverage)
            else:
                return entry_price * (Decimal("1") + inv_leverage)

    @staticmethod
    def calculate_with_margin(
        is_inverse: bool,
        is_long: bool,
        entry_price: Decimal,
        amount: Decimal,
        leverage: Decimal,
        available_balance: Decimal,
        maintenance_margin: Decimal,
        initial_margin: Decimal = Decimal("0"),
    ) -> Decimal:
        """Complex liquidation price accounting for available balance and MMR.

        For inverse contracts (position_value = amount / entry_price):
            long:  liq = amount / (position_value + (IM - MM) + available_balance)
            short: liq = amount / (position_value - (IM - MM + available_balance))

        For linear contracts:
            long:  liq = entry - (available_balance - MM) / amount
            short: liq = entry + (available_balance - MM) / amount

        Returns -1 if liquidation cannot be computed (e.g. non-positive denominator).

        Args:
            is_inverse: True if this is an inverse (base-margined) contract.
            is_long: True if position is long.
            entry_price: Average entry price of the position.
            amount: Position size.
            leverage: Position leverage multiplier.
            available_balance: Available balance in position currency.
            maintenance_margin: Required maintenance margin.
            initial_margin: Initial margin (default 0).

        Returns:
            Liquidation price as a Decimal, or Decimal("-1") if not computable.
        """
        if is_inverse:
            position_value = amount / entry_price
            margin_diff = initial_margin - maintenance_margin
            if is_long:
                denominator = position_value + margin_diff + available_balance
            else:
                denominator = position_value - (margin_diff + available_balance)
            if denominator <= Decimal("0"):
                return Decimal("-1")
            return amount / denominator
        else:
            if is_long:
                liq = entry_price - (available_balance - maintenance_margin) / amount
            else:
                liq = entry_price + (available_balance - maintenance_margin) / amount
            return max(liq, Decimal("0"))
