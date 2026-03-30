from decimal import Decimal

from financepype.constants import s_decimal_0
from financepype.operations.fees import FeeType
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    FundingSettlementDetails,
    InvolvementType,
)
from financepype.simulations.balances.engines.settlement import SettlementEngine


class FundingSettlementEngine(SettlementEngine):
    """Settlement engine for a single funding payment.

    Primary interface for backtesting. Takes a ``FundingSettlementDetails``
    (position state + rate for this period) and returns the cashflows.
    """

    @classmethod
    def _calculate_payment(cls, details: FundingSettlementDetails) -> Decimal:
        return abs(details.position_size * details.rate / Decimal("100"))

    @classmethod
    def _is_receiving(cls, details: FundingSettlementDetails) -> bool:
        is_short = details.position_side == "SHORT"
        positive_rate = details.rate > s_decimal_0
        return (is_short and positive_rate) or (not is_short and not positive_rate)

    @classmethod
    def _calculate_fee(cls, details: FundingSettlementDetails) -> Decimal:
        if details.fee.fee_type == FeeType.ABSOLUTE:
            return details.fee.amount
        if details.fee.fee_type == FeeType.PERCENTAGE:
            payment = cls._calculate_payment(details)
            return payment * (details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {details.fee.fee_type}")

    @classmethod
    def compute_settlement(
        cls, details: FundingSettlementDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        payment = cls._calculate_payment(details)

        if payment == s_decimal_0:
            return result

        receiving = cls._is_receiving(details)
        result.append(
            AssetCashflow(
                asset=details.settlement_asset,
                involvement_type=InvolvementType.SETTLEMENT,
                cashflow_type=CashflowType.INFLOW
                if receiving
                else CashflowType.OUTFLOW,
                reason=CashflowReason.FUNDING,
                amount=payment,
                timestamp=details.timestamp,
            )
        )

        if details.fee.amount > s_decimal_0:
            fee_amount = cls._calculate_fee(details)
            if fee_amount > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=details.settlement_asset,
                        involvement_type=InvolvementType.SETTLEMENT,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=fee_amount,
                        timestamp=details.timestamp,
                    )
                )

        return result
