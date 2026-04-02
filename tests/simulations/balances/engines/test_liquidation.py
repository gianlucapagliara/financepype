"""Tests for LiquidationPriceCalculator."""

from decimal import Decimal

from financepype.simulations.balances.engines.liquidation import (
    LiquidationPriceCalculator,
)


class TestCalculateSimple:
    """Tests for LiquidationPriceCalculator.calculate_simple."""

    def test_linear_long(self) -> None:
        # entry * (1 - 1/leverage) = 50000 * (1 - 0.1) = 45000
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
        )
        assert result == Decimal("45000")

    def test_linear_short(self) -> None:
        # entry * (1 + 1/leverage) = 50000 * 1.1 = 55000
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=False,
            is_long=False,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
        )
        assert result == Decimal("55000")

    def test_inverse_long(self) -> None:
        # entry / (1 + 1/leverage) = 50000 / 1.1 ≈ 45454.545...
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=True,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("50000"),
            leverage=Decimal("10"),
        )
        expected = Decimal("50000") / (Decimal("1") + Decimal("1") / Decimal("10"))
        assert result == expected

    def test_inverse_short(self) -> None:
        # entry / (1 - 1/leverage) = 50000 / 0.9 ≈ 55555.555...
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=True,
            is_long=False,
            entry_price=Decimal("50000"),
            amount=Decimal("50000"),
            leverage=Decimal("10"),
        )
        expected = Decimal("50000") / (Decimal("1") - Decimal("1") / Decimal("10"))
        assert result == expected

    def test_leverage_1_linear_long(self) -> None:
        # 1x leverage: liq = entry * (1 - 1) = 0
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("1"),
        )
        assert result == Decimal("0")

    def test_leverage_1_linear_short(self) -> None:
        # 1x leverage: liq = entry * (1 + 1) = 100000
        result = LiquidationPriceCalculator.calculate_simple(
            is_inverse=False,
            is_long=False,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("1"),
        )
        assert result == Decimal("100000")


class TestCalculateWithMargin:
    """Tests for LiquidationPriceCalculator.calculate_with_margin."""

    def test_linear_long_basic(self) -> None:
        # liq = entry - (available_balance - MM) / amount
        # = 50000 - (10000 - 500) / 1 = 50000 - 9500 = 40500
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
            available_balance=Decimal("10000"),
            maintenance_margin=Decimal("500"),
        )
        assert result == Decimal("40500")

    def test_linear_short_basic(self) -> None:
        # liq = entry + (available_balance - MM) / amount
        # = 50000 + (10000 - 500) / 1 = 59500
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=False,
            is_long=False,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
            available_balance=Decimal("10000"),
            maintenance_margin=Decimal("500"),
        )
        assert result == Decimal("59500")

    def test_linear_long_clamps_to_zero(self) -> None:
        # Large available_balance pushes liq below 0 => clamped to 0
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
            available_balance=Decimal("100000"),
            maintenance_margin=Decimal("500"),
        )
        assert result == Decimal("0")

    def test_inverse_long_basic(self) -> None:
        # position_value = amount / entry = 50000 / 50000 = 1
        # liq = amount / (position_value + (IM - MM) + available_balance)
        # = 50000 / (1 + (0 - 0.1) + 0.9) = 50000 / 1.8 ≈ 27777.77...
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=True,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("50000"),
            leverage=Decimal("10"),
            available_balance=Decimal("0.9"),
            maintenance_margin=Decimal("0.1"),
            initial_margin=Decimal("0"),
        )
        position_value = Decimal("50000") / Decimal("50000")
        expected = Decimal("50000") / (
            position_value + (Decimal("0") - Decimal("0.1")) + Decimal("0.9")
        )
        assert result == expected

    def test_inverse_short_basic(self) -> None:
        # position_value = 50000 / 50000 = 1
        # liq = 50000 / (1 - (0 - 0.1 + 0.9)) = 50000 / (1 - 0.8) = 50000 / 0.2 = 250000
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=True,
            is_long=False,
            entry_price=Decimal("50000"),
            amount=Decimal("50000"),
            leverage=Decimal("10"),
            available_balance=Decimal("0.9"),
            maintenance_margin=Decimal("0.1"),
            initial_margin=Decimal("0"),
        )
        position_value = Decimal("50000") / Decimal("50000")
        expected = Decimal("50000") / (
            position_value - (Decimal("0") - Decimal("0.1") + Decimal("0.9"))
        )
        assert result == expected

    def test_inverse_returns_negative_one_on_non_positive_denominator(self) -> None:
        # Force denominator <= 0 for long inverse
        result = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=True,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("50000"),
            leverage=Decimal("10"),
            available_balance=Decimal("-100"),
            maintenance_margin=Decimal("0"),
            initial_margin=Decimal("0"),
        )
        assert result == Decimal("-1")

    def test_with_initial_margin(self) -> None:
        # Verify initial_margin parameter is used
        # linear long: same as basic but IM doesn't affect linear formula directly
        r1 = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
            available_balance=Decimal("10000"),
            maintenance_margin=Decimal("500"),
            initial_margin=Decimal("1000"),
        )
        r2 = LiquidationPriceCalculator.calculate_with_margin(
            is_inverse=False,
            is_long=True,
            entry_price=Decimal("50000"),
            amount=Decimal("1"),
            leverage=Decimal("10"),
            available_balance=Decimal("10000"),
            maintenance_margin=Decimal("500"),
        )
        # For linear, initial_margin is not used, so results should match
        assert r1 == r2
