from decimal import Decimal

from financepype.constants import s_decimal_0
from financepype.operations.fees import FeeType
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    FundingOrderDetails,
    InvolvementType,
)


class FundingBalanceEngine(BalanceEngine):
    """Engine for simulating cashflows of funding rate payments.

    Funding payments are instantaneous events exchanged between longs and shorts
    on perpetual positions. The payment direction depends on position side and
    funding rate sign:

    - Long + positive rate  -> pays (outflow)
    - Long + negative rate  -> receives (inflow)
    - Short + positive rate -> receives (inflow)
    - Short + negative rate -> pays (outflow)

    All cashflows use the OPENING involvement type since funding is instantaneous.
    The CLOSING phase is always empty.
    """

    @classmethod
    def _calculate_funding_payment(cls, order_details: FundingOrderDetails) -> Decimal:
        """Calculate the absolute funding payment amount."""
        return abs(
            order_details.position_size * order_details.funding_rate / Decimal("100")
        )

    @classmethod
    def _is_receiving(cls, order_details: FundingOrderDetails) -> bool:
        """Determine if the position receives funding.

        Short + positive rate -> receives
        Long + negative rate  -> receives
        """
        is_short = order_details.position_side == "SHORT"
        positive_rate = order_details.funding_rate > s_decimal_0
        return (is_short and positive_rate) or (not is_short and not positive_rate)

    @classmethod
    def _calculate_fee_amount(cls, order_details: FundingOrderDetails) -> Decimal:
        """Calculate the fee amount for the funding payment."""
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            return order_details.fee.amount
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            payment = cls._calculate_funding_payment(order_details)
            return payment * (order_details.fee.amount / Decimal("100"))
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls, order_details: FundingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = [
            AssetCashflow(
                asset=order_details.settlement_asset,
                involvement_type=InvolvementType.OPENING,
                cashflow_type=CashflowType.INFLOW,
                reason=CashflowReason.FUNDING,
            ),
            AssetCashflow(
                asset=order_details.settlement_asset,
                involvement_type=InvolvementType.OPENING,
                cashflow_type=CashflowType.OUTFLOW,
                reason=CashflowReason.FUNDING,
            ),
        ]
        if order_details.fee.amount > s_decimal_0:
            result.append(
                AssetCashflow(
                    asset=order_details.settlement_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                )
            )
        return result

    @classmethod
    def get_opening_outflows(
        cls, order_details: FundingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        payment = cls._calculate_funding_payment(order_details)

        if payment == s_decimal_0:
            return result

        if not cls._is_receiving(order_details):
            result.append(
                AssetCashflow(
                    asset=order_details.settlement_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FUNDING,
                    amount=payment,
                )
            )

        if order_details.fee.amount > s_decimal_0:
            fee_amount = cls._calculate_fee_amount(order_details)
            if fee_amount > s_decimal_0:
                result.append(
                    AssetCashflow(
                        asset=order_details.settlement_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.FEE,
                        amount=fee_amount,
                    )
                )

        return result

    @classmethod
    def get_opening_inflows(
        cls, order_details: FundingOrderDetails
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        payment = cls._calculate_funding_payment(order_details)

        if payment == s_decimal_0:
            return result

        if cls._is_receiving(order_details):
            result.append(
                AssetCashflow(
                    asset=order_details.settlement_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.FUNDING,
                    amount=payment,
                )
            )

        return result

    @classmethod
    def get_closing_outflows(
        cls, order_details: FundingOrderDetails
    ) -> list[AssetCashflow]:
        return []

    @classmethod
    def get_closing_inflows(
        cls, order_details: FundingOrderDetails
    ) -> list[AssetCashflow]:
        return []
