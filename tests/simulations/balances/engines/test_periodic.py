"""Tests for PeriodicSimulator, borrow_duration, compound staking, and settlement engines."""

from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import PositionAction
from financepype.platforms.platform import Platform
from financepype.simulations.balances.engines.borrowing import (
    BorrowBalanceEngine,
    InterestSettlementEngine,
)
from financepype.simulations.balances.engines.funding import FundingSettlementEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    BorrowOrderDetails,
    CashflowReason,
    CashflowType,
    FundingOrderDetails,
    FundingSettlementDetails,
    InterestSettlementDetails,
    InvolvementType,
    RewardSettlementDetails,
    StakingOrderDetails,
)
from financepype.simulations.balances.engines.periodic import PeriodicSimulator
from financepype.simulations.balances.engines.staking import (
    RewardSettlementEngine,
    StakingBalanceEngine,
)

ZERO_FEE = OperationFee(
    asset=None,
    amount=Decimal("0"),
    fee_type=FeeType.PERCENTAGE,
    impact_type=FeeImpactType.ADDED_TO_COSTS,
)


@pytest.fixture
def platform() -> Platform:
    return Platform(identifier="test")


@pytest.fixture
def btc_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "BTC")


@pytest.fixture
def usdt_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "USDT")


@pytest.fixture
def eth_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "ETH")


# ---------------------------------------------------------------------------
# AssetCashflow: period_index / timestamp defaults
# ---------------------------------------------------------------------------


class TestAssetCashflowTimeMetadata:
    def test_defaults_are_none(self, btc_asset: Asset) -> None:
        cf = AssetCashflow(
            asset=btc_asset,
            involvement_type=InvolvementType.OPENING,
            cashflow_type=CashflowType.OUTFLOW,
            reason=CashflowReason.OPERATION,
            amount=Decimal("1"),
        )
        assert cf.period_index is None
        assert cf.timestamp is None

    def test_explicit_values(self, btc_asset: Asset) -> None:
        cf = AssetCashflow(
            asset=btc_asset,
            involvement_type=InvolvementType.OPENING,
            cashflow_type=CashflowType.OUTFLOW,
            reason=CashflowReason.OPERATION,
            amount=Decimal("1"),
            period_index=3,
            timestamp=1700000000,
        )
        assert cf.period_index == 3
        assert cf.timestamp == 1700000000


# ---------------------------------------------------------------------------
# BorrowBalanceEngine: borrow_duration
# ---------------------------------------------------------------------------


class TestBorrowDuration:
    def test_zero_duration_uses_total_rate(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """borrow_duration=0 -> interest = amount * rate/100 (legacy behavior)."""
        details = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("5"),
            borrow_duration=0,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        interest = BorrowBalanceEngine._calculate_interest(details)
        assert interest == Decimal("1000") * Decimal("5") / Decimal("100")

    def test_duration_computes_time_proportional(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """borrow_duration > 0 -> time-proportional annual interest."""
        one_day = 86400
        details = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("10"),  # 10% annual
            borrow_duration=one_day,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        interest = BorrowBalanceEngine._calculate_interest(details)
        expected = (
            Decimal("1000")
            * Decimal("10")
            / Decimal("100")
            * Decimal(one_day)
            / Decimal("31536000")
        )
        assert interest == expected

    def test_full_year_duration_equals_annual_rate(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """One full year of borrow_duration should equal amount * rate/100."""
        details = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("5"),
            borrow_duration=31536000,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        interest = BorrowBalanceEngine._calculate_interest(details)
        assert interest == Decimal("50")


# ---------------------------------------------------------------------------
# StakingBalanceEngine: compound interest
# ---------------------------------------------------------------------------


class TestStakingCompound:
    def test_simple_interest_default(
        self, eth_asset: Asset, platform: Platform
    ) -> None:
        """compound=False -> simple linear interest."""
        details = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),  # 10% APY
            staking_duration=31536000,  # 1 year
            compound=False,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        reward = StakingBalanceEngine._calculate_reward(details)
        assert reward == Decimal("10")  # 100 * 10%

    def test_compound_interest(self, eth_asset: Asset, platform: Platform) -> None:
        """compound=True with daily compounding over 1 year."""
        details = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),  # 10% APY
            staking_duration=31536000,  # 1 year
            compound=True,
            compound_interval=86400,  # daily
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        reward = StakingBalanceEngine._calculate_reward(details)
        # Compound should yield more than simple
        assert reward > Decimal("10")
        # 365 daily compounds at 10% APY: (1 + 0.1/365)^365 - 1 ~ 10.5156%
        assert reward < Decimal("11")

    def test_compound_short_duration_fallback(
        self, eth_asset: Asset, platform: Platform
    ) -> None:
        """Duration shorter than compound_interval falls back to simple."""
        details = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),
            staking_duration=3600,  # 1 hour
            compound=True,
            compound_interval=86400,  # 1 day (longer than duration)
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        reward = StakingBalanceEngine._calculate_reward(details)
        expected = (
            Decimal("100")
            * Decimal("10")
            / Decimal("100")
            * Decimal("3600")
            / Decimal("31536000")
        )
        assert reward == expected


# ---------------------------------------------------------------------------
# FundingSettlementEngine
# ---------------------------------------------------------------------------


class TestFundingSettlementEngine:
    def test_long_positive_rate_pays(self, usdt_asset: Asset) -> None:
        details = FundingSettlementDetails(
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            position_side="LONG",
            rate=Decimal("0.01"),
            timestamp=1700000000,
            fee=ZERO_FEE,
        )
        cashflows = FundingSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 1
        assert cashflows[0].cashflow_type == CashflowType.OUTFLOW
        assert cashflows[0].reason == CashflowReason.FUNDING
        assert cashflows[0].involvement_type == InvolvementType.SETTLEMENT
        assert cashflows[0].timestamp == 1700000000
        assert cashflows[0].amount == Decimal("10") * Decimal("0.01") / Decimal("100")

    def test_short_positive_rate_receives(self, usdt_asset: Asset) -> None:
        details = FundingSettlementDetails(
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            position_side="SHORT",
            rate=Decimal("0.01"),
            timestamp=1700000000,
            fee=ZERO_FEE,
        )
        cashflows = FundingSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 1
        assert cashflows[0].cashflow_type == CashflowType.INFLOW

    def test_long_negative_rate_receives(self, usdt_asset: Asset) -> None:
        details = FundingSettlementDetails(
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            position_side="LONG",
            rate=Decimal("-0.02"),
            timestamp=1700000000,
            fee=ZERO_FEE,
        )
        cashflows = FundingSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 1
        assert cashflows[0].cashflow_type == CashflowType.INFLOW

    def test_zero_rate_no_cashflows(self, usdt_asset: Asset) -> None:
        details = FundingSettlementDetails(
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            position_side="LONG",
            rate=Decimal("0"),
            timestamp=1700000000,
            fee=ZERO_FEE,
        )
        cashflows = FundingSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 0

    def test_with_fee(self, usdt_asset: Asset) -> None:
        fee = OperationFee(
            asset=None,
            amount=Decimal("1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )
        details = FundingSettlementDetails(
            settlement_asset=usdt_asset,
            position_size=Decimal("1000"),
            position_side="LONG",
            rate=Decimal("0.01"),
            timestamp=1700000000,
            fee=fee,
        )
        cashflows = FundingSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 2
        fee_cf = [cf for cf in cashflows if cf.reason == CashflowReason.FEE][0]
        assert fee_cf.cashflow_type == CashflowType.OUTFLOW


# ---------------------------------------------------------------------------
# InterestSettlementEngine
# ---------------------------------------------------------------------------


class TestInterestSettlementEngine:
    def test_single_period_interest(self, btc_asset: Asset) -> None:
        one_day = 86400
        details = InterestSettlementDetails(
            borrowed_asset=btc_asset,
            principal=Decimal("1000"),
            rate=Decimal("10"),  # 10% annual
            duration_seconds=one_day,
            timestamp=one_day,
            fee=ZERO_FEE,
        )
        cashflows = InterestSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 1
        cf = cashflows[0]
        assert cf.cashflow_type == CashflowType.OUTFLOW
        assert cf.reason == CashflowReason.INTEREST
        assert cf.involvement_type == InvolvementType.SETTLEMENT
        assert cf.timestamp == one_day
        expected = (
            Decimal("1000")
            * Decimal("10")
            / Decimal("100")
            * Decimal(one_day)
            / Decimal("31536000")
        )
        assert cf.amount == expected

    def test_full_year_interest(self, btc_asset: Asset) -> None:
        details = InterestSettlementDetails(
            borrowed_asset=btc_asset,
            principal=Decimal("1000"),
            rate=Decimal("5"),
            duration_seconds=31536000,
            timestamp=31536000,
            fee=ZERO_FEE,
        )
        cashflows = InterestSettlementEngine.compute_settlement(details)
        assert cashflows[0].amount == Decimal("50")

    def test_with_fee(self, btc_asset: Asset) -> None:
        fee = OperationFee(
            asset=None,
            amount=Decimal("0.5"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )
        details = InterestSettlementDetails(
            borrowed_asset=btc_asset,
            principal=Decimal("1000"),
            rate=Decimal("10"),
            duration_seconds=86400,
            timestamp=86400,
            fee=fee,
        )
        cashflows = InterestSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 2
        fee_cf = [cf for cf in cashflows if cf.reason == CashflowReason.FEE][0]
        assert fee_cf.amount == Decimal("1000") * Decimal("0.5") / Decimal("100")


# ---------------------------------------------------------------------------
# RewardSettlementEngine
# ---------------------------------------------------------------------------


class TestRewardSettlementEngine:
    def test_single_epoch_reward(self, eth_asset: Asset) -> None:
        one_day = 86400
        details = RewardSettlementDetails(
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            principal=Decimal("100"),
            rate=Decimal("10"),  # 10% annual
            duration_seconds=one_day,
            timestamp=one_day,
            fee=ZERO_FEE,
        )
        cashflows = RewardSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 1
        cf = cashflows[0]
        assert cf.cashflow_type == CashflowType.INFLOW
        assert cf.reason == CashflowReason.REWARD
        assert cf.involvement_type == InvolvementType.SETTLEMENT
        expected = (
            Decimal("100")
            * Decimal("10")
            / Decimal("100")
            * Decimal(one_day)
            / Decimal("31536000")
        )
        assert cf.amount == expected

    def test_full_year_reward(self, eth_asset: Asset) -> None:
        details = RewardSettlementDetails(
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            principal=Decimal("100"),
            rate=Decimal("10"),
            duration_seconds=31536000,
            timestamp=31536000,
            fee=ZERO_FEE,
        )
        cashflows = RewardSettlementEngine.compute_settlement(details)
        assert cashflows[0].amount == Decimal("10")

    def test_with_deducted_fee(self, eth_asset: Asset) -> None:
        fee = OperationFee(
            asset=None,
            amount=Decimal("10"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
        )
        details = RewardSettlementDetails(
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            principal=Decimal("100"),
            rate=Decimal("10"),
            duration_seconds=31536000,
            timestamp=31536000,
            fee=fee,
        )
        cashflows = RewardSettlementEngine.compute_settlement(details)
        assert len(cashflows) == 2
        reward_cf = [cf for cf in cashflows if cf.reason == CashflowReason.REWARD][0]
        fee_cf = [cf for cf in cashflows if cf.reason == CashflowReason.FEE][0]
        assert reward_cf.cashflow_type == CashflowType.INFLOW
        assert fee_cf.cashflow_type == CashflowType.OUTFLOW
        # Fee is 10% of reward (10) = 1
        assert fee_cf.amount == Decimal("1")


# ---------------------------------------------------------------------------
# PeriodicSimulator.simulate_funding (settlement-based)
# ---------------------------------------------------------------------------


class TestPeriodicFunding:
    def test_multi_rate_schedule(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("-0.02"),
            1700057600: Decimal("0.005"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)

        assert len(result.period_results) == 3
        for idx, pr in enumerate(result.period_results):
            for cf in pr.cashflows:
                assert cf.period_index == idx
                assert cf.involvement_type == InvolvementType.SETTLEMENT

        # First period: LONG + positive rate -> outflow
        first = result.period_results[0]
        assert any(
            cf.cashflow_type == CashflowType.OUTFLOW
            and cf.reason == CashflowReason.FUNDING
            for cf in first.cashflows
        )

        # Second period: LONG + negative rate -> inflow (receives)
        second = result.period_results[1]
        assert any(
            cf.cashflow_type == CashflowType.INFLOW
            and cf.reason == CashflowReason.FUNDING
            for cf in second.cashflows
        )

    def test_timestamps_tagged(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("0.02"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)
        timestamps = sorted(schedule.keys())
        for idx, pr in enumerate(result.period_results):
            for cf in pr.cashflows:
                assert cf.timestamp == timestamps[idx]

    def test_empty_schedule(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        result = PeriodicSimulator.simulate_funding(base, {})
        assert len(result.period_results) == 0


# ---------------------------------------------------------------------------
# PeriodicSimulator.simulate_interest (settlement-based)
# ---------------------------------------------------------------------------


class TestPeriodicInterest:
    def test_none_schedule_single_period(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """None rate_schedule uses lifecycle engine for one period."""
        base = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("5"),
            borrow_duration=0,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        result = PeriodicSimulator.simulate_interest(base, rate_schedule=None)
        assert len(result.period_results) == 1

    def test_multi_period_compounding(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """Interest compounds across periods when compound=True."""
        base = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("10"),
            borrow_duration=0,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        one_day = 86400
        schedule = [(one_day, Decimal("10"))] * 3
        result = PeriodicSimulator.simulate_interest(base, schedule, compound=True)

        assert len(result.period_results) == 3
        # Settlement details have .principal instead of .amount
        p0 = result.period_results[0].operation_details.principal
        p1 = result.period_results[1].operation_details.principal
        p2 = result.period_results[2].operation_details.principal
        assert p0 == Decimal("1000")
        assert p1 > Decimal("1000")
        assert p2 > p1

    def test_multi_period_no_compounding(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        """Without compounding, principal stays the same across periods."""
        base = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("10"),
            borrow_duration=0,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        one_day = 86400
        schedule = [(one_day, Decimal("10"))] * 3
        result = PeriodicSimulator.simulate_interest(base, schedule, compound=False)

        assert len(result.period_results) == 3
        for pr in result.period_results:
            assert pr.operation_details.principal == Decimal("1000")

    def test_period_index_and_timestamp(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = BorrowOrderDetails(
            platform=platform,
            borrowed_asset=btc_asset,
            collateral_asset=usdt_asset,
            amount=Decimal("1000"),
            collateral_amount=Decimal("1500"),
            interest_rate=Decimal("10"),
            borrow_duration=0,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        schedule = [(3600, Decimal("10")), (7200, Decimal("12"))]
        result = PeriodicSimulator.simulate_interest(base, schedule, compound=False)

        for cf in result.period_results[0].cashflows:
            assert cf.period_index == 0
            assert cf.timestamp == 3600
        for cf in result.period_results[1].cashflows:
            assert cf.period_index == 1
            assert cf.timestamp == 3600 + 7200


# ---------------------------------------------------------------------------
# PeriodicSimulator.simulate_staking_rewards (settlement-based)
# ---------------------------------------------------------------------------


class TestPeriodicStaking:
    def test_none_schedule_single_period(
        self, eth_asset: Asset, platform: Platform
    ) -> None:
        base = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),
            staking_duration=31536000,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        result = PeriodicSimulator.simulate_staking_rewards(base, rate_schedule=None)
        assert len(result.period_results) == 1

    def test_multi_epoch_compound(self, eth_asset: Asset, platform: Platform) -> None:
        """With compound=True on base_details, principal grows across epochs."""
        base = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),
            staking_duration=86400,
            compound=True,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        one_day = 86400
        schedule = [(one_day, Decimal("10"))] * 3
        result = PeriodicSimulator.simulate_staking_rewards(base, schedule)

        assert len(result.period_results) == 3
        p0 = result.period_results[0].operation_details.principal
        p1 = result.period_results[1].operation_details.principal
        p2 = result.period_results[2].operation_details.principal
        assert p0 == Decimal("100")
        assert p1 > Decimal("100")
        assert p2 > p1

    def test_multi_epoch_no_compound(
        self, eth_asset: Asset, platform: Platform
    ) -> None:
        """With compound=False, principal stays constant across epochs."""
        base = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),
            staking_duration=86400,
            compound=False,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        one_day = 86400
        schedule = [(one_day, Decimal("10"))] * 3
        result = PeriodicSimulator.simulate_staking_rewards(base, schedule)

        for pr in result.period_results:
            assert pr.operation_details.principal == Decimal("100")

    def test_variable_rate_schedule(self, eth_asset: Asset, platform: Platform) -> None:
        """Different rates per epoch are respected."""
        base = StakingOrderDetails(
            platform=platform,
            staked_asset=eth_asset,
            reward_asset=eth_asset,
            amount=Decimal("100"),
            reward_rate=Decimal("10"),
            staking_duration=86400,
            compound=False,
            position_action=PositionAction.CLOSE,
            fee=ZERO_FEE,
        )
        one_day = 86400
        schedule = [
            (one_day, Decimal("5")),
            (one_day, Decimal("15")),
        ]
        result = PeriodicSimulator.simulate_staking_rewards(base, schedule)

        assert result.period_results[0].operation_details.rate == Decimal("5")
        assert result.period_results[1].operation_details.rate == Decimal("15")


# ---------------------------------------------------------------------------
# PeriodicSimulationResult: aggregation and query methods
# ---------------------------------------------------------------------------


class TestPeriodicSimulationResult:
    def test_total_cashflows(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("0.02"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)
        total = result.total_cashflows
        expected_count = sum(len(pr.cashflows) for pr in result.period_results)
        assert len(total) == expected_count

    def test_total_by_asset(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("0.01"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)
        by_asset = result.total_by_asset
        assert usdt_asset in by_asset

    def test_cashflows_at(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("0.02"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)

        at_first = result.cashflows_at(1700000000)
        assert len(at_first) == 1
        assert at_first[0].timestamp == 1700000000

        at_second = result.cashflows_at(1700028800)
        assert len(at_second) == 1
        assert at_second[0].timestamp == 1700028800

        at_missing = result.cashflows_at(9999999999)
        assert len(at_missing) == 0

    def test_cashflows_in_range(
        self, btc_asset: Asset, usdt_asset: Asset, platform: Platform
    ) -> None:
        base = FundingOrderDetails(
            platform=platform,
            position_asset=btc_asset,
            settlement_asset=usdt_asset,
            position_size=Decimal("10"),
            funding_rate=Decimal("0.01"),
            payment_period=28800,
            position_side="LONG",
            fee=ZERO_FEE,
        )
        schedule: dict[int, Decimal] = {
            1700000000: Decimal("0.01"),
            1700028800: Decimal("0.02"),
            1700057600: Decimal("0.03"),
        }
        result = PeriodicSimulator.simulate_funding(base, schedule)

        # Range includes first two, excludes third (end is exclusive)
        in_range = result.cashflows_in_range(1700000000, 1700057600)
        assert all(cf.timestamp in (1700000000, 1700028800) for cf in in_range)

        # All three
        all_range = result.cashflows_in_range(1700000000, 1700057601)
        assert len(all_range) == 3
