"""Periodic simulator for recurring cashflows.

Uses ``SettlementEngine`` subclasses to compute one payment at a time. Each
method accepts a rate schedule, iterates it, and collects results into a
``PeriodicSimulationResult``.

For interest and staking rewards, a ``rate_schedule=None`` fallback delegates
to the lifecycle ``BalanceEngine`` (``BorrowBalanceEngine`` /
``StakingBalanceEngine``) for single-period simulation of the full
open-to-close lifecycle.
"""

from dataclasses import replace
from decimal import Decimal

from financepype.simulations.balances.engines.borrowing import (
    BorrowBalanceEngine,
    InterestSettlementEngine,
)
from financepype.simulations.balances.engines.funding import (
    FundingSettlementEngine,
)
from financepype.simulations.balances.engines.models import (
    BorrowOrderDetails,
    FundingOrderDetails,
    FundingSettlementDetails,
    InterestSettlementDetails,
    OperationSimulationResult,
    PeriodicSimulationResult,
    RewardSettlementDetails,
    StakingOrderDetails,
)
from financepype.simulations.balances.engines.staking import (
    RewardSettlementEngine,
    StakingBalanceEngine,
)


class PeriodicSimulator:
    """Stateless simulator that iterates settlement engines over rate schedules.

    All methods use ``SettlementEngine`` subclasses (per-payment model).
    ``simulate_interest`` and ``simulate_staking_rewards`` fall back to their
    respective lifecycle engines when ``rate_schedule=None`` for single-period
    open-to-close simulation.
    """

    # ------------------------------------------------------------------
    # Settlement-based interface (primary, for backtesting)
    # ------------------------------------------------------------------

    @classmethod
    def simulate_funding(
        cls,
        base_details: FundingOrderDetails,
        rate_schedule: dict[int, Decimal],
    ) -> PeriodicSimulationResult:
        """Simulate funding payments using the settlement engine.

        Args:
            base_details: Base funding order details (position size, side, etc.)
            rate_schedule: Map of payment timestamps to funding rates,
                matching the output of ``FundingInfo.get_next_payment_rates()``.

        Returns:
            PeriodicSimulationResult with one result per payment.
        """
        period_results: list[OperationSimulationResult] = []

        for idx, (timestamp, rate) in enumerate(sorted(rate_schedule.items())):
            settlement = FundingSettlementDetails(
                settlement_asset=base_details.settlement_asset,
                position_size=base_details.position_size,
                position_side=base_details.position_side,
                rate=rate,
                timestamp=timestamp,
                fee=base_details.fee,
            )
            cashflows = FundingSettlementEngine.compute_settlement(settlement)

            tagged = [replace(cf, period_index=idx) for cf in cashflows]

            period_results.append(
                OperationSimulationResult(
                    operation_details=settlement,
                    cashflows=tagged,
                )
            )

        return PeriodicSimulationResult(
            operation_details=base_details,
            period_results=period_results,
        )

    @classmethod
    def simulate_interest(
        cls,
        base_details: BorrowOrderDetails,
        rate_schedule: list[tuple[int, Decimal]] | None = None,
        compound: bool = True,
    ) -> PeriodicSimulationResult:
        """Simulate interest accrual using the settlement engine.

        Args:
            base_details: Base borrow order details.
            rate_schedule: List of (duration_secs, annual_rate) per period.
                When None, uses the single rate/duration from base_details
                for one period via the lifecycle engine (backward-compatible).
            compound: Whether to compound interest (add accrued interest to
                principal for the next period).

        Returns:
            PeriodicSimulationResult with one result per period.
        """
        if rate_schedule is None:
            result = BorrowBalanceEngine.get_complete_simulation(base_details)
            return PeriodicSimulationResult(
                operation_details=base_details,
                period_results=[result],
            )

        period_results: list[OperationSimulationResult] = []
        current_principal = base_details.amount
        cumulative_seconds = 0

        for idx, (duration_secs, rate) in enumerate(rate_schedule):
            timestamp = cumulative_seconds + duration_secs

            settlement = InterestSettlementDetails(
                borrowed_asset=base_details.borrowed_asset,
                principal=current_principal,
                rate=rate,
                duration_seconds=duration_secs,
                timestamp=timestamp,
                fee=base_details.fee,
            )
            cashflows = InterestSettlementEngine.compute_settlement(settlement)

            tagged = [replace(cf, period_index=idx) for cf in cashflows]

            period_results.append(
                OperationSimulationResult(
                    operation_details=settlement,
                    cashflows=tagged,
                )
            )

            if compound:
                interest = InterestSettlementEngine._calculate_interest(settlement)
                current_principal = current_principal + interest

            cumulative_seconds = timestamp

        return PeriodicSimulationResult(
            operation_details=base_details,
            period_results=period_results,
        )

    @classmethod
    def simulate_staking_rewards(
        cls,
        base_details: StakingOrderDetails,
        rate_schedule: list[tuple[int, Decimal]] | None = None,
    ) -> PeriodicSimulationResult:
        """Simulate reward accrual using the settlement engine.

        Respects the ``compound`` setting from order details. When compounding
        is enabled, the principal grows by the reward of each epoch before
        simulating the next.

        Args:
            base_details: Base staking order details.
            rate_schedule: List of (duration_secs, annual_rate) per epoch.
                When None, uses the single rate/duration from base_details
                for one period via the lifecycle engine (backward-compatible).

        Returns:
            PeriodicSimulationResult with one result per epoch.
        """
        if rate_schedule is None:
            result = StakingBalanceEngine.get_complete_simulation(base_details)
            return PeriodicSimulationResult(
                operation_details=base_details,
                period_results=[result],
            )

        period_results: list[OperationSimulationResult] = []
        current_principal = base_details.amount
        cumulative_seconds = 0

        for idx, (duration_secs, rate) in enumerate(rate_schedule):
            timestamp = cumulative_seconds + duration_secs

            settlement = RewardSettlementDetails(
                staked_asset=base_details.staked_asset,
                reward_asset=base_details.reward_asset,
                principal=current_principal,
                rate=rate,
                duration_seconds=duration_secs,
                timestamp=timestamp,
                fee=base_details.fee,
            )
            cashflows = RewardSettlementEngine.compute_settlement(settlement)

            tagged = [replace(cf, period_index=idx) for cf in cashflows]

            period_results.append(
                OperationSimulationResult(
                    operation_details=settlement,
                    cashflows=tagged,
                )
            )

            if base_details.compound:
                reward = RewardSettlementEngine._calculate_reward(settlement)
                current_principal = current_principal + reward

            cumulative_seconds = timestamp

        return PeriodicSimulationResult(
            operation_details=base_details,
            period_results=period_results,
        )
