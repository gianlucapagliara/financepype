from decimal import Decimal

from financepype.constants import s_decimal_0
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.orders.models import PositionAction
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    BorrowOrderDetails,
    CashflowReason,
    CashflowType,
    InterestSettlementDetails,
    InvolvementType,
)
from financepype.simulations.balances.engines.settlement import SettlementEngine

SECONDS_PER_YEAR = Decimal("31536000")  # 365 * 24 * 60 * 60


class BorrowBalanceEngine(BalanceEngine):
    """Engine for simulating cashflows of borrow/repay operations.

    OPEN (borrow):
    - Opening outflow: collateral_asset locked (COLLATERAL)
    - Opening outflow: fee if ADDED_TO_COSTS
    - Closing inflow: borrowed_asset received (OPERATION)

    CLOSE (repay):
    - Opening outflow: borrowed_asset returned (OPERATION)
    - Opening outflow: interest payment (INTEREST)
    - Opening outflow: fee if ADDED_TO_COSTS
    - Closing inflow: collateral_asset released (COLLATERAL)

    Note: interest_rate on BorrowOrderDetails is an annual percentage.
    Since BorrowOrderDetails does not carry a duration field, callers
    should encode the effective rate for the period, or subclass and
    override ``_calculate_interest`` to supply duration externally.
    The default implementation treats interest_rate as the total rate
    for the loan period: ``interest = amount * interest_rate / 100``.
    """

    @classmethod
    def _calculate_interest(cls, order_details: BorrowOrderDetails) -> Decimal:
        """Calculate accrued interest for the borrow period.

        When ``borrow_duration`` is set (> 0), computes time-proportional
        interest: ``amount * (rate / 100) * (duration / SECONDS_PER_YEAR)``.
        Otherwise falls back to: ``amount * interest_rate / 100``
        (treating interest_rate as the total rate for the period).
        """
        rate = order_details.interest_rate / Decimal("100")
        if order_details.borrow_duration > 0:
            return (
                order_details.amount
                * rate
                * (Decimal(order_details.borrow_duration) / SECONDS_PER_YEAR)
            )
        return order_details.amount * rate

    @classmethod
    def _calculate_fee_amount(cls, order_details: BorrowOrderDetails) -> Decimal:
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            return order_details.fee.amount
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            return order_details.amount * (order_details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls, order_details: BorrowOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.OPEN:
            result.append(
                AssetCashflow(
                    asset=order_details.collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )
            result.append(
                AssetCashflow(
                    asset=order_details.borrowed_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=order_details.borrowed_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
            result.append(
                AssetCashflow(
                    asset=order_details.borrowed_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.INTEREST,
                )
            )
            result.append(
                AssetCashflow(
                    asset=order_details.collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                )
            )

        if order_details.fee.amount > s_decimal_0:
            fee_asset = (
                order_details.collateral_asset
                if order_details.position_action == PositionAction.OPEN
                else order_details.borrowed_asset
            )
            result.append(
                AssetCashflow(
                    asset=fee_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                )
            )

        return result

    @classmethod
    def get_opening_outflows(
        cls, order_details: BorrowOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.OPEN:
            result.append(
                AssetCashflow(
                    asset=order_details.collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.collateral_amount,
                )
            )
            if (
                order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS
                and order_details.fee.amount > s_decimal_0
            ):
                result.append(
                    AssetCashflow(
                        asset=order_details.collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=cls._calculate_fee_amount(order_details),
                    )
                )

        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=order_details.borrowed_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
                    amount=order_details.amount,
                )
            )
            interest = cls._calculate_interest(order_details)
            if interest > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=order_details.borrowed_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.INTEREST,
                        amount=interest,
                    )
                )
            if (
                order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS
                and order_details.fee.amount > s_decimal_0
            ):
                result.append(
                    AssetCashflow(
                        asset=order_details.borrowed_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=cls._calculate_fee_amount(order_details),
                    )
                )

        return result

    @classmethod
    def get_opening_inflows(
        cls, order_details: BorrowOrderDetails
    ) -> list[AssetCashflow]:
        return []

    @classmethod
    def get_closing_outflows(
        cls, order_details: BorrowOrderDetails
    ) -> list[AssetCashflow]:
        return []

    @classmethod
    def get_closing_inflows(
        cls, order_details: BorrowOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.OPEN:
            result.append(
                AssetCashflow(
                    asset=order_details.borrowed_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                    amount=order_details.amount,
                )
            )

        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=order_details.collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.COLLATERAL,
                    amount=order_details.collateral_amount,
                )
            )

        return result


class InterestSettlementEngine(SettlementEngine):
    """Settlement engine for a single interest accrual event.

    Primary interface for backtesting. Computes interest for one period
    given the current principal and rate.
    """

    @classmethod
    def _calculate_interest(cls, details: InterestSettlementDetails) -> Decimal:
        rate = details.rate / Decimal("100")
        return (
            details.principal
            * rate
            * (Decimal(details.duration_seconds) / SECONDS_PER_YEAR)
        )

    @classmethod
    def _calculate_fee(cls, details: InterestSettlementDetails) -> Decimal:
        if details.fee.fee_type == FeeType.ABSOLUTE:
            return details.fee.amount
        if details.fee.fee_type == FeeType.PERCENTAGE:
            return details.principal * (details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {details.fee.fee_type}")

    @classmethod
    def compute_settlement(
        cls, details: InterestSettlementDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        interest = cls._calculate_interest(details)

        if interest > s_decimal_0:
            result.append(
                AssetCashflow(
                    asset=details.borrowed_asset,
                    involvement_type=InvolvementType.SETTLEMENT,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.INTEREST,
                    amount=interest,
                    timestamp=details.timestamp,
                )
            )

        if details.fee.amount > s_decimal_0:
            fee_amount = cls._calculate_fee(details)
            if fee_amount > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=details.borrowed_asset,
                        involvement_type=InvolvementType.SETTLEMENT,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=fee_amount,
                        timestamp=details.timestamp,
                    )
                )

        return result
