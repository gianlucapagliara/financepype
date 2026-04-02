"""Tests for contract-type-aware utility functions."""

from decimal import Decimal

import pytest

from financepype.simulations.balances.engines.utils import (
    compute_funding_fee,
    compute_initial_margin,
    compute_position_vwap,
)


class TestComputePositionVwap:
    def test_linear_single_entry(self) -> None:
        entries = [(Decimal("50000"), Decimal("1"))]
        result = compute_position_vwap(is_inverse=False, entries=entries)
        assert result == Decimal("50000")

    def test_linear_equal_amounts(self) -> None:
        # (50000*1 + 60000*1) / 2 = 55000
        entries = [
            (Decimal("50000"), Decimal("1")),
            (Decimal("60000"), Decimal("1")),
        ]
        result = compute_position_vwap(is_inverse=False, entries=entries)
        assert result == Decimal("55000")

    def test_linear_unequal_amounts(self) -> None:
        # (50000*2 + 60000*1) / 3 = 160000/3
        entries = [
            (Decimal("50000"), Decimal("2")),
            (Decimal("60000"), Decimal("1")),
        ]
        result = compute_position_vwap(is_inverse=False, entries=entries)
        expected = Decimal("160000") / Decimal("3")
        assert result == expected

    def test_inverse_single_entry(self) -> None:
        # VWAP = total_amount / sum(amount/price) = 50000 / (50000/50000) = 50000
        entries = [(Decimal("50000"), Decimal("50000"))]
        result = compute_position_vwap(is_inverse=True, entries=entries)
        assert result == Decimal("50000")

    def test_inverse_two_entries(self) -> None:
        # entries: (50000, 50000) and (100000, 100000)
        # total_amount = 150000
        # sum(amount/price) = 50000/50000 + 100000/100000 = 1 + 1 = 2
        # VWAP = 150000 / 2 = 75000
        entries = [
            (Decimal("50000"), Decimal("50000")),
            (Decimal("100000"), Decimal("100000")),
        ]
        result = compute_position_vwap(is_inverse=True, entries=entries)
        assert result == Decimal("75000")

    def test_empty_entries_raises(self) -> None:
        with pytest.raises(ValueError, match="entries must not be empty"):
            compute_position_vwap(is_inverse=False, entries=[])

    def test_linear_zero_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="Total amount is zero"):
            compute_position_vwap(
                is_inverse=False,
                entries=[(Decimal("50000"), Decimal("0"))],
            )


class TestComputeFundingFee:
    def test_linear_long_positive_rate(self) -> None:
        # Long pays: 1 * 50000 * 0.001 = 50
        result = compute_funding_fee(
            is_inverse=False,
            amount=Decimal("1"),
            mark_price=Decimal("50000"),
            rate=Decimal("0.001"),
            is_long=True,
        )
        assert result == Decimal("50")

    def test_linear_short_positive_rate(self) -> None:
        # Short receives: -(1 * 50000 * 0.001) = -50
        result = compute_funding_fee(
            is_inverse=False,
            amount=Decimal("1"),
            mark_price=Decimal("50000"),
            rate=Decimal("0.001"),
            is_long=False,
        )
        assert result == Decimal("-50")

    def test_linear_long_negative_rate(self) -> None:
        # Negative rate: long receives: 1 * 50000 * (-0.001) = -50
        result = compute_funding_fee(
            is_inverse=False,
            amount=Decimal("1"),
            mark_price=Decimal("50000"),
            rate=Decimal("-0.001"),
            is_long=True,
        )
        assert result == Decimal("-50")

    def test_inverse_long_positive_rate(self) -> None:
        # (50000 / 50000) * 0.001 = 0.001
        result = compute_funding_fee(
            is_inverse=True,
            amount=Decimal("50000"),
            mark_price=Decimal("50000"),
            rate=Decimal("0.001"),
            is_long=True,
        )
        assert result == Decimal("0.001")

    def test_inverse_short_positive_rate(self) -> None:
        # Short receives: -(50000 / 50000) * 0.001 = -0.001
        result = compute_funding_fee(
            is_inverse=True,
            amount=Decimal("50000"),
            mark_price=Decimal("50000"),
            rate=Decimal("0.001"),
            is_long=False,
        )
        assert result == Decimal("-0.001")

    def test_inverse_rate_scaling(self) -> None:
        # (100000 / 50000) * 0.001 = 0.002 for long
        result = compute_funding_fee(
            is_inverse=True,
            amount=Decimal("100000"),
            mark_price=Decimal("50000"),
            rate=Decimal("0.001"),
            is_long=True,
        )
        assert result == Decimal("0.002")

    def test_zero_rate(self) -> None:
        result = compute_funding_fee(
            is_inverse=False,
            amount=Decimal("1"),
            mark_price=Decimal("50000"),
            rate=Decimal("0"),
            is_long=True,
        )
        assert result == Decimal("0")


class TestComputeInitialMargin:
    def test_linear_basic(self) -> None:
        # 1 * 50000 / 10 = 5000
        result = compute_initial_margin(
            is_inverse=False,
            amount=Decimal("1"),
            price=Decimal("50000"),
            leverage=Decimal("10"),
        )
        assert result == Decimal("5000")

    def test_linear_leverage_1(self) -> None:
        # 1 * 50000 / 1 = 50000
        result = compute_initial_margin(
            is_inverse=False,
            amount=Decimal("1"),
            price=Decimal("50000"),
            leverage=Decimal("1"),
        )
        assert result == Decimal("50000")

    def test_inverse_basic(self) -> None:
        # 50000 / (10 * 50000) = 0.1
        result = compute_initial_margin(
            is_inverse=True,
            amount=Decimal("50000"),
            price=Decimal("50000"),
            leverage=Decimal("10"),
        )
        assert result == Decimal("0.1")

    def test_inverse_leverage_1(self) -> None:
        # 50000 / (1 * 50000) = 1.0
        result = compute_initial_margin(
            is_inverse=True,
            amount=Decimal("50000"),
            price=Decimal("50000"),
            leverage=Decimal("1"),
        )
        assert result == Decimal("1")

    def test_inverse_higher_leverage(self) -> None:
        # 100000 / (100 * 50000) = 0.02
        result = compute_initial_margin(
            is_inverse=True,
            amount=Decimal("100000"),
            price=Decimal("50000"),
            leverage=Decimal("100"),
        )
        assert result == Decimal("0.02")
