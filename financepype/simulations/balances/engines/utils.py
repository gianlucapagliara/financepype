"""Contract-type-aware utility functions for balance engine calculations."""

from decimal import Decimal


def compute_position_vwap(
    is_inverse: bool,
    entries: list[tuple[Decimal, Decimal]],
) -> Decimal:
    """Compute VWAP (volume-weighted average price) for a position.

    Linear:  sum(price * amount) / sum(amount)
    Inverse: sum(amount) / sum(amount / price)

    Args:
        is_inverse: True if this is an inverse (base-margined) contract.
        entries: List of (price, amount) tuples representing fills.

    Returns:
        VWAP as a Decimal.

    Raises:
        ValueError: If entries is empty or denominator is zero.
    """
    if not entries:
        raise ValueError("entries must not be empty")

    if is_inverse:
        total_amount = sum((amount for _, amount in entries), Decimal("0"))
        total_base = sum((amount / price for price, amount in entries), Decimal("0"))
        if total_base == Decimal("0"):
            raise ValueError("Sum of amount/price is zero; cannot compute VWAP")
        return total_amount / total_base
    else:
        total_cost = sum((price * amount for price, amount in entries), Decimal("0"))
        total_amount = sum((amount for _, amount in entries), Decimal("0"))
        if total_amount == Decimal("0"):
            raise ValueError("Total amount is zero; cannot compute VWAP")
        return total_cost / total_amount


def compute_funding_fee(
    is_inverse: bool,
    amount: Decimal,
    mark_price: Decimal,
    rate: Decimal,
    is_long: bool,
) -> Decimal:
    """Compute the funding fee for a perpetual position.

    Linear:  fee = amount * mark_price * rate
        amount is in base units, so amount * mark_price gives the notional
        value in quote currency (e.g. USD). The rate is then applied to
        this notional value.
    Inverse: fee = (amount / mark_price) * rate
        amount is in USD notional, so amount / mark_price converts to base
        currency. The rate is applied to that base-currency value.

    Rate convention:
        rate is a plain decimal fraction (e.g. 0.0001 for 0.01%).
        It is NOT a percentage — do not multiply by 100 before passing.

    Sign convention: longs pay when rate > 0 (positive fee = cost).

    Args:
        is_inverse: True if this is an inverse (base-margined) contract.
        amount: Position size (base units for linear, USD notional for inverse).
        mark_price: Current mark price.
        rate: Funding rate (decimal fraction, e.g. 0.0001 for 0.01%.
              Positive means longs pay shorts).
        is_long: True if position is long.

    Returns:
        Funding fee as a Decimal. Positive means the position holder pays,
        negative means they receive.
    """
    if is_inverse:
        raw_fee = (amount / mark_price) * rate
    else:
        raw_fee = amount * mark_price * rate

    # Longs pay when rate > 0; shorts receive. Flip sign for shorts.
    if not is_long:
        raw_fee = -raw_fee
    return raw_fee


def compute_initial_margin(
    is_inverse: bool,
    amount: Decimal,
    price: Decimal,
    leverage: Decimal,
) -> Decimal:
    """Compute the initial margin requirement for opening a position.

    Linear:  margin = amount * price / leverage
    Inverse: margin = amount / (leverage * price)

    Args:
        is_inverse: True if this is an inverse (base-margined) contract.
        amount: Position size (base units for linear, USD notional for inverse).
        price: Entry price.
        leverage: Position leverage multiplier.

    Returns:
        Initial margin as a Decimal.
    """
    if is_inverse:
        return amount / (leverage * price)
    else:
        return amount * price / leverage
