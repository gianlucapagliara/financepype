"""Tests for TieredMMR maintenance margin calculator."""

import dataclasses
from decimal import Decimal

import pytest

from financepype.simulations.balances.engines.margin import MMRTier, TieredMMR


@pytest.fixture
def simple_tiers() -> list[MMRTier]:
    """Three-tier MMR structure for testing."""
    return [
        MMRTier(limit=Decimal("50000"), rate=Decimal("0.005"), deduction=Decimal("0")),
        MMRTier(
            limit=Decimal("250000"), rate=Decimal("0.01"), deduction=Decimal("250")
        ),
        MMRTier(
            limit=Decimal("1000000"),
            rate=Decimal("0.02"),
            deduction=Decimal("2750"),
        ),
    ]


@pytest.fixture
def tiered_mmr(simple_tiers: list[MMRTier]) -> TieredMMR:
    return TieredMMR(simple_tiers)


class TestMMRTier:
    def test_frozen_dataclass(self) -> None:
        tier = MMRTier(
            limit=Decimal("50000"),
            rate=Decimal("0.005"),
            deduction=Decimal("0"),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            tier.limit = Decimal("100000")  # type: ignore[misc]

    def test_fields(self) -> None:
        tier = MMRTier(
            limit=Decimal("100"),
            rate=Decimal("0.01"),
            deduction=Decimal("5"),
        )
        assert tier.limit == Decimal("100")
        assert tier.rate == Decimal("0.01")
        assert tier.deduction == Decimal("5")


class TestTieredMMR:
    def test_tiers_sorted_by_limit(self, simple_tiers: list[MMRTier]) -> None:
        shuffled = list(reversed(simple_tiers))
        mmr = TieredMMR(shuffled)
        limits = [t.limit for t in mmr.tiers]
        assert limits == sorted(limits)

    def test_first_tier_at_boundary(self, tiered_mmr: TieredMMR) -> None:
        # Exactly at tier 1 boundary: 50000 * 0.005 - 0 = 250
        result = tiered_mmr.calculate_maintenance_margin(Decimal("50000"))
        assert result == Decimal("250")

    def test_first_tier_below_boundary(self, tiered_mmr: TieredMMR) -> None:
        # 10000 * 0.005 - 0 = 50
        result = tiered_mmr.calculate_maintenance_margin(Decimal("10000"))
        assert result == Decimal("50")

    def test_second_tier(self, tiered_mmr: TieredMMR) -> None:
        # 100000 * 0.01 - 250 = 750
        result = tiered_mmr.calculate_maintenance_margin(Decimal("100000"))
        assert result == Decimal("750")

    def test_second_tier_at_boundary(self, tiered_mmr: TieredMMR) -> None:
        # 250000 * 0.01 - 250 = 2250
        result = tiered_mmr.calculate_maintenance_margin(Decimal("250000"))
        assert result == Decimal("2250")

    def test_third_tier(self, tiered_mmr: TieredMMR) -> None:
        # 500000 * 0.02 - 2750 = 7250
        result = tiered_mmr.calculate_maintenance_margin(Decimal("500000"))
        assert result == Decimal("7250")

    def test_beyond_last_tier_uses_last(self, tiered_mmr: TieredMMR) -> None:
        # Falls into last tier: 2000000 * 0.02 - 2750 = 37250
        result = tiered_mmr.calculate_maintenance_margin(Decimal("2000000"))
        assert result == Decimal("37250")

    def test_single_tier(self) -> None:
        mmr = TieredMMR(
            [
                MMRTier(
                    limit=Decimal("999999999"),
                    rate=Decimal("0.01"),
                    deduction=Decimal("0"),
                )
            ]
        )
        result = mmr.calculate_maintenance_margin(Decimal("1000"))
        assert result == Decimal("10")

    def test_zero_position_value(self, tiered_mmr: TieredMMR) -> None:
        result = tiered_mmr.calculate_maintenance_margin(Decimal("0"))
        assert result == Decimal("0")
