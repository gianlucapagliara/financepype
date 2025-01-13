from decimal import Decimal

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.orders.models import TradeType
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)


class SpotBalanceEngine(BalanceEngine):
    """Engine for simulating cashflows of spot trading operations.

    Handles spot trading with the following patterns:

    BUY Order (e.g., BUY BTC/USDT):
    1. Opening Outflows:
        - USDT (quote): amount * price (cost)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - BTC (base): amount (return)

    SELL Order (e.g., SELL BTC/USDT):
    1. Opening Outflows:
        - BTC (base): amount (cost)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - USDT (quote): amount * price (return)

    Fee Handling:
    - Supports both absolute and percentage fees
    - Percentage fees must be in the same asset as the trade
    - Fees can be either added to costs or deducted from returns
    """

    @classmethod
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the asset that will flow out during the trade.

        For BUY orders: quote currency (e.g., USDT in BTC/USDT)
        For SELL orders: base currency (e.g., BTC in BTC/USDT)
        """
        if order_details.trade_type == TradeType.BUY:
            symbol = order_details.trading_pair.quote
        elif order_details.trade_type == TradeType.SELL:
            symbol = order_details.trading_pair.base
        else:
            raise ValueError(f"Unsupported trade type: {order_details.trade_type}")
        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _get_inflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the asset that will flow in during the trade.

        For BUY orders: base currency (e.g., BTC in BTC/USDT)
        For SELL orders: quote currency (e.g., USDT in BTC/USDT)
        """
        if order_details.trade_type == TradeType.BUY:
            symbol = order_details.trading_pair.base
        elif order_details.trade_type == TradeType.SELL:
            symbol = order_details.trading_pair.quote
        else:
            raise ValueError(f"Unsupported trade type: {order_details.trade_type}")
        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _get_expected_fee_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the expected fee asset based on the trade type and fee impact type."""
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
            return cls._get_inflow_asset(order_details)
        elif order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            return cls._get_outflow_asset(order_details)
        else:
            raise ValueError(
                f"Unsupported fee impact type: {order_details.fee.impact_type}"
            )

    @classmethod
    def _get_fee_impact(cls, order_details: OrderDetails) -> dict[Asset, Decimal]:
        """Calculate the fee amount based on fee type, fee asset, and trade details.

        Fee Calculation Scenarios:
        1. Absolute Fees:
        - Fixed amount in the fee asset
        - Example: 10 USDT fee for any trade size

        2. Percentage Fees (e.g., USDT in BTC-USDT):
        - BUY with ADDED_TO_COSTS:
            * Trading 1 BTC at $50,000 with 0.1% fee
            * Fee = $50,000 * 0.1% = $50 USDT
        - BUY with DEDUCTED_FROM_RETURNS:
            * Trading 1 BTC at $50,000 with 0.1% fee
            * Fee = 1 BTC * 0.1% = 0.001 BTC
        - SELL with ADDED_TO_COSTS:
            * Trading 1 BTC at $50,000 with 0.1% fee
            * Fee = 1 BTC * 0.1% = 0.001 BTC
        - SELL with DEDUCTED_FROM_RETURNS:
            * Trading 1 BTC at $50,000 with 0.1% fee
            * Fee = $50,000 * 0.1% = $50 USDT

        3. Percentage Fees in Other Assets:
        - Not supported yet
        - Would require price data for conversion

        Args:
            order_details: Details of the spot trading order

        Returns:
            Dict mapping fee asset to fee amount

        Raises:
            NotImplementedError: If fee is in an asset not involved in the trade
            ValueError: If fee type is not supported
        """
        # Handle absolute fees (fixed amount)
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            if order_details.fee.asset is None:
                raise ValueError("Fee asset is required for absolute fees")
            return {order_details.fee.asset: order_details.fee.amount}

        # Handle percentage fees
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            # Get expected fee asset based on impact type
            expected_asset = cls._get_expected_fee_asset(order_details)

            # If fee asset is specified, verify it matches expected
            if (
                order_details.fee.asset is not None
                and order_details.fee.asset != expected_asset
            ):
                raise NotImplementedError(
                    "Percentage fee on not involved asset not supported yet. "
                    f"Fee asset: {str(order_details.fee.asset)}, expected asset: {str(expected_asset)}"
                )

            # Calculate fee amount based on whether it's quote or base currency
            quote_asset = AssetFactory.get_asset(
                order_details.platform, order_details.trading_pair.quote
            )
            is_quote_currency_fee = expected_asset == quote_asset

            # Calculate fee amount
            if is_quote_currency_fee:
                # Quote currency fees are based on notional value
                notional_value = order_details.amount * order_details.price
                fee_amount = notional_value * (
                    order_details.fee.amount / Decimal("100")
                )
            else:
                # Base currency fees are based on trade amount
                fee_amount = order_details.amount * (
                    order_details.fee.amount / Decimal("100")
                )

            return {expected_asset: fee_amount}

        # Handle unsupported fee types
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls,
        order_details: OrderDetails,
    ) -> list[AssetCashflow]:
        """Get all assets involved in a spot trading operation.

        This method identifies all assets that will be affected by the trade,
        including the traded assets and fee assets. It considers both the
        opening and closing phases of the trade.

        Args:
            order_details: Details of the spot trading order

        Returns:
            list[AssetCashflow]: List of asset cashflows involved in the trade
        """
        result: list[AssetCashflow] = []

        # Cost
        outflow_asset = cls._get_outflow_asset(order_details)
        result.append(
            AssetCashflow(
                asset=outflow_asset,
                involvement_type=InvolvementType.OPENING,
                cashflow_type=CashflowType.OUTFLOW,
                reason=CashflowReason.OPERATION,
            )
        )

        # Return
        inflow_asset = cls._get_inflow_asset(order_details)
        result.append(
            AssetCashflow(
                asset=inflow_asset,
                involvement_type=InvolvementType.CLOSING,
                cashflow_type=CashflowType.INFLOW,
                reason=CashflowReason.OPERATION,
            )
        )

        # Fee
        if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            fee_asset = cls._get_expected_fee_asset(order_details)
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
    def get_opening_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Calculate the initial outflows for a spot trade.

        For BUY orders:
        - Outflow of quote currency (cost = amount * price)
        - Fee outflow if ADDED_TO_COSTS

        For SELL orders:
        - Outflow of base currency (cost = amount)
        - Fee outflow if ADDED_TO_COSTS

        Args:
            order_details: Details of the spot trading order

        Returns:
            list[AssetCashflow]: List of opening outflows
        """
        result: list[AssetCashflow] = []

        # Cost
        asset = cls._get_outflow_asset(order_details)
        if order_details.trade_type == TradeType.BUY:
            amount = order_details.amount * order_details.price
        elif order_details.trade_type == TradeType.SELL:
            amount = order_details.amount
        else:
            raise ValueError(f"Unsupported trade type: {order_details.trade_type}")
        result.append(
            AssetCashflow(
                asset=asset,
                involvement_type=InvolvementType.OPENING,
                cashflow_type=CashflowType.OUTFLOW,
                amount=amount,
                reason=CashflowReason.OPERATION,
            )
        )

        # Fee
        if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            fee_impact = cls._get_fee_impact(order_details)
            for asset, amount in fee_impact.items():
                result.append(
                    AssetCashflow(
                        asset=asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        amount=amount,
                        reason=CashflowReason.FEE,
                    )
                )

        return result

    @classmethod
    def get_opening_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Calculate the initial inflows for a spot trade.

        For spot trading, there are no opening inflows.
        All inflows occur during the closing phase.

        Args:
            order_details: Details of the spot trading order

        Returns:
            list[AssetCashflow]: Empty list as there are no opening inflows
        """
        return []

    @classmethod
    def get_closing_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Calculate the final outflows for a spot trade.

        The only closing outflows are fees when they are configured
        to be deducted from returns.

        Args:
            order_details: Details of the spot trading order

        Returns:
            list[AssetCashflow]: List of closing outflows (fees)
        """
        result: list[AssetCashflow] = []

        # Fee
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
            fee_impact = cls._get_fee_impact(order_details)
            for asset, amount in fee_impact.items():
                result.append(
                    AssetCashflow(
                        asset=asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        amount=amount,
                        reason=CashflowReason.FEE,
                    )
                )

        return result

    @classmethod
    def get_closing_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Calculate the final inflows for a spot trade.

        For BUY orders:
        - Inflow of base currency (return = amount)

        For SELL orders:
        - Inflow of quote currency (return = amount * price)

        Args:
            order_details: Details of the spot trading order

        Returns:
            list[AssetCashflow]: List of closing inflows
        """
        result: list[AssetCashflow] = []

        # Return
        asset = cls._get_inflow_asset(order_details)
        if order_details.trade_type == TradeType.BUY:
            amount = order_details.amount
        elif order_details.trade_type == TradeType.SELL:
            amount = order_details.amount * order_details.price
        else:
            raise ValueError(f"Unsupported trade type: {order_details.trade_type}")
        result.append(
            AssetCashflow(
                asset=asset,
                involvement_type=InvolvementType.CLOSING,
                cashflow_type=CashflowType.INFLOW,
                amount=amount,
                reason=CashflowReason.OPERATION,
            )
        )

        return result
