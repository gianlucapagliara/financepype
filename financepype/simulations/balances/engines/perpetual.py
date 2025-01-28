from abc import abstractmethod
from decimal import Decimal
from typing import cast

from financepype.assets.asset import Asset
from financepype.assets.contract import DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.markets.position import Position
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.orders.models import PositionAction, TradeType
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    MinimalOrderDetails,
    OrderDetails,
)


class BasePerpetualBalanceEngine(BalanceEngine):
    """Base class for perpetual futures balance engines.

    Provides common functionality for both regular and inverse perpetual futures:
    - Asset flow patterns (OPEN/CLOSE/FLIP)
    - Fee handling
    - Position management

    OPEN LONG/SHORT:
    1. Opening Outflows:
        - Margin in collateral asset
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - None
    3. Closing Outflows:
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Position asset

    CLOSE LONG/SHORT:
    1. Opening Outflows:
        - Position asset
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - None
    3. Closing Outflows:
        - Negative PnL (if any)
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Margin return
        - Positive PnL (if any)

    FLIP:
    - Combines CLOSE of existing position with OPEN of new position
    - All cashflows from both operations apply
    - PnL is realized from the closed position
    - Margin is returned from old position and new margin is required for new position
    1. Opening Outflows:
        - Existing position asset (for closing)
        - New margin in collateral asset (for opening)
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - Old margin return from existing position
    3. Closing Outflows:
        - Negative PnL (if any) from existing position
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - New position asset
        - Positive PnL (if any) from existing position

    Subclasses must implement:
    - _get_outflow_asset: Define which asset is used for margin/collateral
    - _calculate_margin: Define margin calculation logic
    - _calculate_pnl: Define PnL calculation logic
    - _calculate_index_price: Define index price calculation logic
    - _calculate_liquidation_price: Define liquidation price calculation logic
    """

    @classmethod
    @abstractmethod
    def _get_outflow_asset(cls, order_details: MinimalOrderDetails) -> Asset:
        """Get the collateral asset for margin."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the required margin amount."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the PnL for a position."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_index_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the index price for a position."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_liquidation_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the liquidation price for a position."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _notional_value(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the fee amount based on percentage fee."""
        raise NotImplementedError

    @classmethod
    def _get_expected_fee_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the expected fee asset based on the trade type and fee impact type."""
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
            return cls._get_outflow_asset(order_details)
        elif order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            return cls._get_outflow_asset(order_details)

        raise ValueError(
            f"Unsupported fee impact type: {order_details.fee.impact_type}"
        )

    @classmethod
    def _calculate_fee_amount(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the fee amount based on fee type and trade details.

        The fee calculation depends on the fee type and impact type:

        1. Absolute Fees:
            - Fixed amount in the specified fee asset
            - Fee asset must match the expected asset based on impact type

        2. Percentage Fees:
            - Calculated as percentage of notional value (amount * price)
            - Fee is in the same asset as margin/collateral

        Args:
            order_details: Details of the perpetual futures order

        Returns:
            The calculated fee amount

        Raises:
            ValueError: If fee type is not supported or fee asset is missing for absolute fees
            NotImplementedError: If fee is in an asset not involved in the trade
        """
        expected_asset = cls._get_expected_fee_asset(order_details)

        # If fee asset is specified, verify it matches expected
        if (
            order_details.fee.asset is not None
            and order_details.fee.asset != expected_asset
        ):
            raise NotImplementedError(
                "Fee on not involved asset not supported yet. "
                f"Fee asset: {str(order_details.fee.asset)}, expected asset: {str(expected_asset)}"
            )

        # Handle absolute fees (fixed amount)
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            if order_details.fee.asset is None:
                raise ValueError("Fee asset is required for absolute fees")
            return order_details.fee.amount

        # Handle percentage fees
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            # Calculate based on notional value
            notional_value = cls._notional_value(order_details)
            fee_amount = notional_value * (order_details.fee.amount / Decimal("100"))
            return fee_amount

        # Handle unsupported fee types
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls, order_details: MinimalOrderDetails
    ) -> list[AssetCashflow]:
        """Get the involved assets for a perpetual futures order.

        OPEN:
        - Margin outflow (opening)
        - Position inflow (closing)
        - Fee outflow for opening (if ADDED_TO_COSTS)
        - Fee outflow for closing (if DEDUCTED_FROM_RETURNS)

        CLOSE:
        - Position outflow (opening)
        - Margin return inflow (closing)
        - PnL inflow/outflow (closing)
        - Fee outflow for opening (if ADDED_TO_COSTS)
        - Fee outflow for closing (if DEDUCTED_FROM_RETURNS)

        FLIP:
        - Existing position outflow (opening)
        - New margin outflow (opening)
        - Old margin inflow (opening)
        - New position inflow (closing)
        - PnL inflow (closing)
        - PnL outflow (closing)
        - Fee outflow for opening (if ADDED_TO_COSTS)
        -Fee outflow for closing (if DEDUCTED_FROM_RETURNS)

        Args:
            order_details (MinimalOrderDetails): Details of the perpetual futures order

        Returns:
            list[AssetCashflow]: List of involved assets
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_involved_assets(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)

        if order_details.position_action in [PositionAction.OPEN]:
            position_asset = AssetFactory.get_asset(
                order_details.platform,
                order_details.trading_pair.name,
                side=order_details.trade_type.to_position_side(),
            )
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.MARGIN,
                )
            )
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                )
            )
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
        elif order_details.position_action in [PositionAction.CLOSE]:
            position_asset = AssetFactory.get_asset(
                order_details.platform,
                order_details.trading_pair.name,
                side=order_details.trade_type.opposite().to_position_side(),
            )
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                )
            )
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.MARGIN,
                )
            )
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.PNL,
                )
            )

        return result

    @classmethod
    def get_opening_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_opening_outflows(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)

        if order_details.position_action == PositionAction.OPEN:
            margin_amount = cls._calculate_margin(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.MARGIN,
                    amount=margin_amount,
                )
            )
            fee_asset = cls._get_expected_fee_asset(order_details)
            result.append(
                AssetCashflow(
                    asset=fee_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=cls._calculate_fee_amount(order_details),
                )
            )

        if order_details.position_action == PositionAction.CLOSE:
            closing_position_asset = AssetFactory.get_asset(
                order_details.platform,
                order_details.trading_pair.name,
                side=order_details.trade_type.opposite().to_position_side(),
            )
            position_amount = order_details.amount
            result.append(
                AssetCashflow(
                    asset=closing_position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
                    amount=position_amount,
                )
            )

        return result

    @classmethod
    def get_opening_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_opening_inflows(order_details))
            return result

        return result

    @classmethod
    def get_closing_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_closing_outflows(order_details))
            return result

        # Calculate PnL
        if order_details.position_action in [PositionAction.CLOSE]:
            fee_asset = cls._get_expected_fee_asset(order_details)
            result.append(
                AssetCashflow(
                    asset=fee_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=cls._calculate_fee_amount(order_details),
                )
            )

        # Calculate PnL
        if order_details.position_action in [PositionAction.CLOSE, PositionAction.FLIP]:
            pnl = cls._calculate_pnl(order_details)
            if pnl < 0:
                collateral_asset = cls._get_outflow_asset(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.PNL,
                        amount=abs(pnl),
                    )
                )

        return result

    @classmethod
    def get_closing_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_closing_inflows(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)
        if order_details.position_action in [PositionAction.OPEN]:
            opening_position_asset = AssetFactory.get_asset(
                order_details.platform,
                order_details.trading_pair.name,
                side=order_details.trade_type.to_position_side(),
            )
            position_amount = order_details.amount
            result.append(
                AssetCashflow(
                    asset=opening_position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                    amount=position_amount,
                )
            )

        if order_details.position_action == PositionAction.CLOSE:
            current_position = cast(Position, order_details.current_position)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.MARGIN,
                    amount=current_position.margin,
                )
            )

            pnl = cls._calculate_pnl(order_details)
            if pnl > 0:
                collateral_asset = cls._get_outflow_asset(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.PNL,
                        amount=abs(pnl),
                    )
                )

        return result


class PerpetualBalanceEngine(BasePerpetualBalanceEngine):
    """Engine for simulating cashflows of regular perpetual futures trading operations.

    Regular perpetuals have:
    - PnL in quote currency
    - Margin in quote currency
    - Position size in base currency

    Fee Handling:
    - Supports both absolute and percentage fees
    - Fees are typically in the quote currency
    - Fees can be either added to costs or deducted from returns
    """

    @classmethod
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the collateral asset for margin.

        For regular perpetuals, this is determined by the trading rule:
        - BUY: buy_order_collateral_token
        - SELL: sell_order_collateral_token

        Typically this is the quote currency (e.g., USDT in BTC/USDT)
        """
        symbol = None
        if order_details.trade_type == TradeType.BUY:
            symbol = order_details.trading_rule.buy_order_collateral_token
        elif order_details.trade_type == TradeType.SELL:
            symbol = order_details.trading_rule.sell_order_collateral_token

        if symbol is None:
            raise ValueError("Collateral token not specified in trading rule")

        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in quote currency.

        margin = (amount * price) / leverage
        """
        return (order_details.amount * order_details.price) / Decimal(
            order_details.leverage
        )

    @classmethod
    def _notional_value(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the notional value of the order."""
        return order_details.amount * order_details.price

    @classmethod
    def _calculate_index_price(cls, order_details: OrderDetails) -> Decimal:
        raise NotImplementedError(
            "Index price can't be calculated for regular perpetuals"
        )

    @classmethod
    def _calculate_liquidation_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the liquidation price for a position."""
        raise NotImplementedError

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in quote currency.

        For regular perpetuals:
        - LONG: PnL = (exit_price - entry_price) * position_size
        - SHORT: PnL = (entry_price - exit_price) * position_size
        """
        if order_details.position_action == PositionAction.OPEN:
            return Decimal("0")

        current_position = cast(Position, order_details.current_position)
        entry_price = current_position.entry_price
        exit_price = order_details.price
        position_size = (
            order_details.amount
            if order_details.position_action == PositionAction.CLOSE
            else current_position.amount
        )

        if current_position.position_side == DerivativeSide.LONG:
            pnl = (exit_price - entry_price) * position_size
        else:
            pnl = (entry_price - exit_price) * position_size

        return pnl


class InversePerpetualBalanceEngine(BasePerpetualBalanceEngine):
    """Engine for simulating cashflows of inverse perpetual futures trading operations.

    Inverse perpetuals have:
    - PnL in base currency
    - Margin in base currency
    - Position size in contract value (USD)

    Key Differences from Regular Perpetuals:
    - PnL and margin in base currency (e.g., BTC)
    - Position size in contract value (USD)
    - PnL calculated using inverse price formula
    - Margin requirements in base currency
    """

    @classmethod
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the collateral asset for margin.

        For inverse perpetuals, this is always the base currency
        (e.g., BTC in BTC/USD)
        """
        symbol = order_details.trading_pair.base
        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in base currency.

        margin = contract_value / (leverage * entry_price)
        """
        contract_value = order_details.amount
        entry_price = order_details.price
        return contract_value / (Decimal(order_details.leverage) * entry_price)

    @classmethod
    def _notional_value(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the notional value of the order."""
        return order_details.amount / order_details.price

    @classmethod
    def _calculate_index_price(cls, order_details: OrderDetails) -> Decimal:
        raise NotImplementedError(
            "Index price can't be calculated for inverse perpetuals"
        )

    @classmethod
    def _calculate_liquidation_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the liquidation price for a position."""
        raise NotImplementedError

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in base currency.

        For inverse perpetuals:
        - LONG: PnL = (1/entry_price - 1/exit_price) * contract_value
        - SHORT: PnL = (1/exit_price - 1/entry_price) * contract_value
        """
        if order_details.position_action == PositionAction.OPEN:
            return Decimal("0")

        current_position = cast(Position, order_details.current_position)
        entry_price = current_position.entry_price
        exit_price = order_details.price
        contract_value = (
            order_details.amount
            if order_details.position_action == PositionAction.CLOSE
            else current_position.amount
        )

        if current_position.position_side == DerivativeSide.LONG:
            pnl = (
                Decimal("1") / entry_price - Decimal("1") / exit_price
            ) * contract_value
        else:
            pnl = (
                Decimal("1") / exit_price - Decimal("1") / entry_price
            ) * contract_value

        return pnl
