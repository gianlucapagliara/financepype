from decimal import Decimal

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.orders.models import PositionAction
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    RewardSettlementDetails,
    StakingOrderDetails,
)
from financepype.simulations.balances.engines.settlement import SettlementEngine

SECONDS_PER_YEAR = Decimal("31536000")  # 365 * 24 * 60 * 60


class StakingBalanceEngine(BalanceEngine):
    """Engine for simulating cashflows of staking operations.

    Supports both traditional locked staking and liquid staking (BETH, stETH,
    BBSOL). For liquid staking, ``receipt_asset`` on the order details
    specifies the derivative token received on stake.

    Fee handling:
    - ADDED_TO_COSTS: entry fee on principal (e.g. liquid staking minting fee)
    - DEDUCTED_FROM_RETURNS: exit fee on accrued rewards (e.g. protocol commission)

    OPEN (start staking):
    - Opening outflow: staked_asset leaves available balance (COLLATERAL)
    - Opening outflow: fee on principal if ADDED_TO_COSTS
    - Closing inflow: receipt_asset or staked_asset locked (COLLATERAL)

    CLOSE (unstake + collect rewards):
    - Opening outflow: receipt_asset or staked_asset returned (COLLATERAL)
    - Closing inflow: original staked_asset returned (COLLATERAL)
    - Closing inflow: reward_asset accrued (REWARD)
    - Closing outflow: fee on rewards if DEDUCTED_FROM_RETURNS
    """

    @classmethod
    def _get_position_asset(cls, order_details: StakingOrderDetails) -> Asset:
        """Get the asset representing the staked position.

        For liquid staking this is the receipt token (BETH, stETH, BBSOL).
        For traditional staking this is the staked asset itself.
        """
        return order_details.receipt_asset or order_details.staked_asset

    @classmethod
    def _calculate_reward(cls, order_details: StakingOrderDetails) -> Decimal:
        """Calculate accrued staking reward.

        Simple interest (default):
            reward = amount * reward_rate * (staking_duration / seconds_per_year)

        Compound interest (compound=True):
            A = amount * (1 + rate * interval / year) ^ (duration / interval)
            reward = A - amount

        reward_rate is APY as a decimal percentage (e.g. 5 means 5%).
        """
        rate = order_details.reward_rate / Decimal("100")
        duration = Decimal(order_details.staking_duration)

        if order_details.compound and order_details.compound_interval > 0:
            interval = Decimal(order_details.compound_interval)
            n_periods = int(duration / interval)
            if n_periods <= 0:
                # Duration shorter than one compound interval — simple interest
                return order_details.amount * rate * (duration / SECONDS_PER_YEAR)
            rate_per_period = rate * interval / SECONDS_PER_YEAR
            final = order_details.amount * (1 + rate_per_period) ** n_periods
            return final - order_details.amount

        return order_details.amount * rate * (duration / SECONDS_PER_YEAR)

    @classmethod
    def _calculate_fee_amount(cls, order_details: StakingOrderDetails) -> Decimal:
        """Calculate fee amount.

        - ADDED_TO_COSTS: percentage fee on principal (staked amount).
        - DEDUCTED_FROM_RETURNS: percentage fee on accrued rewards.
        """
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            return order_details.fee.amount
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
                base = order_details.amount
            else:
                base = cls._calculate_reward(order_details)
            return base * (order_details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls, order_details: StakingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        position_asset = cls._get_position_asset(order_details)

        if order_details.position_action == PositionAction.OPEN:
            result.append(
                AssetCashflow(
                    asset=order_details.staked_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )
        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )
            result.append(
                AssetCashflow(
                    asset=order_details.staked_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )
            result.append(
                AssetCashflow(
                    asset=order_details.reward_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.REWARD,
                )
            )

        if order_details.fee.amount > s_decimal_0:
            if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
                result.append(
                    AssetCashflow(
                        asset=order_details.staked_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                    )
                )
            elif (
                order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS
                and order_details.position_action == PositionAction.CLOSE
            ):
                result.append(
                    AssetCashflow(
                        asset=order_details.reward_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                    )
                )

        return result

    @classmethod
    def get_opening_outflows(
        cls, order_details: StakingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.OPEN:
            result.append(
                AssetCashflow(
                    asset=order_details.staked_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.amount,
                )
            )
            if (
                order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS
                and order_details.fee.amount > s_decimal_0
            ):
                result.append(
                    AssetCashflow(
                        asset=order_details.staked_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=cls._calculate_fee_amount(order_details),
                    )
                )

        elif order_details.position_action == PositionAction.CLOSE:
            position_asset = cls._get_position_asset(order_details)
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.amount,
                )
            )

        return result

    @classmethod
    def get_opening_inflows(
        cls, order_details: StakingOrderDetails
    ) -> list[AssetCashflow]:
        return []

    @classmethod
    def get_closing_outflows(
        cls, order_details: StakingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if (
            order_details.position_action == PositionAction.CLOSE
            and order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS
            and order_details.fee.amount > s_decimal_0
        ):
            fee_amount = cls._calculate_fee_amount(order_details)
            if fee_amount > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=order_details.reward_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=fee_amount,
                    )
                )

        return result

    @classmethod
    def get_closing_inflows(
        cls, order_details: StakingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.OPEN:
            position_asset = cls._get_position_asset(order_details)
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.amount,
                )
            )

        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=order_details.staked_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.amount,
                )
            )
            reward = cls._calculate_reward(order_details)
            if reward > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=order_details.reward_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.REWARD,
                        amount=reward,
                    )
                )

        return result


class RewardSettlementEngine(SettlementEngine):
    """Settlement engine for a single staking reward distribution.

    Primary interface for backtesting. Computes reward for one epoch
    given the current staked principal and rate.
    """

    @classmethod
    def _calculate_reward(cls, details: RewardSettlementDetails) -> Decimal:
        rate = details.rate / Decimal("100")
        return (
            details.principal
            * rate
            * (Decimal(details.duration_seconds) / SECONDS_PER_YEAR)
        )

    @classmethod
    def _calculate_fee(cls, details: RewardSettlementDetails) -> Decimal:
        if details.fee.fee_type == FeeType.ABSOLUTE:
            return details.fee.amount
        if details.fee.fee_type == FeeType.PERCENTAGE:
            if details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
                base = cls._calculate_reward(details)
            else:
                base = details.principal
            return base * (details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {details.fee.fee_type}")

    @classmethod
    def compute_settlement(
        cls, details: RewardSettlementDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        reward = cls._calculate_reward(details)

        if reward > s_decimal_0:
            result.append(
                AssetCashflow(
                    asset=details.reward_asset,
                    involvement_type=InvolvementType.SETTLEMENT,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.REWARD,
                    amount=reward,
                    timestamp=details.timestamp,
                )
            )

        if details.fee.amount > s_decimal_0:
            fee_amount = cls._calculate_fee(details)
            if fee_amount > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=details.reward_asset,
                        involvement_type=InvolvementType.SETTLEMENT,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=fee_amount,
                        timestamp=details.timestamp,
                    )
                )

        return result
