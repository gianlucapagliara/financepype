from abc import abstractmethod
from decimal import Decimal

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.constants import s_decimal_0, s_decimal_NaN
from financepype.markets.market import InstrumentType
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


def _safe_decimal(value: Decimal | None) -> Decimal:
    """Convert an optional decimal to a decimal, raising ValueError if None."""
    if value is None:
        raise ValueError("Expected decimal value but got None")
    return value


class BaseOptionBalanceEngine(BalanceEngine):
    """Base class for option balance engines.

    Provides common functionality for both regular and inverse options:
    - Asset flow patterns (OPEN/CLOSE)
    - Fee handling
    - Premium collection/payment
    - Settlement calculation
    - Margin management

    OPEN LONG CALL/PUT:
    1. Opening Outflows:
        - Premium payment in collateral asset
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - None
    3. Closing Outflows:
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Option contract

    CLOSE LONG CALL/PUT:
    1. Opening Outflows:
        - Position asset
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - None
    3. Closing Outflows:
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Premium received in collateral asset

    OPEN SHORT CALL/PUT:
    1. Opening Outflows:
        - Margin in collateral asset
        - Fee (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - Premium received in collateral asset
        - Contract
    3. Closing Outflows:
        - Fee (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Position asset

    CLOSE SHORT CALL/PUT:
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

    Subclasses must implement:
    - _get_outflow_asset: Define which asset is used for margin/collateral
    - _calculate_premium: Define premium calculation logic
    - _calculate_margin: Define margin calculation logic
    - _calculate_index_price: Define index price calculation logic (from margin)
    - _calculate_pnl: Define PnL calculation logic
    - _calculate_settlement: Define settlement calculation logic
    """

    @classmethod
    @abstractmethod
    def _get_outflow_asset(cls, order_details: MinimalOrderDetails) -> Asset:
        """Get the collateral asset for margin/premium."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_premium(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the option premium."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the margin requirement for short options."""
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
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the settlement amount for exercised/assigned options."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_liquidation_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the liquidation price for a position."""
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

        The fee calculation depends on the option type (regular vs inverse) and fee asset:

        1. Regular Options:
            - Quote currency fees (USDT): Based on premium value
            - Example: 0.1% fee on $1000 premium = $1 USDT fee

        2. Inverse Options:
            - Base currency fees (BTC): Based on premium value in BTC
            - Example: 0.1% fee on 0.02 BTC premium = 0.00002 BTC fee
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
            # Calculate based on premium value
            premium = cls._calculate_premium(order_details)
            fee_amount = premium * (order_details.fee.amount / Decimal("100"))
            return fee_amount

        # Handle unsupported fee types
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    def get_involved_assets(
        cls, order_details: MinimalOrderDetails
    ) -> list[AssetCashflow]:
        """Get the involved assets for an option order.

        BUY CALL/PUT (Opening Long Position):
        1. Opening Outflows:
            - Premium payment in collateral asset
            - Fee (if ADDED_TO_COSTS)
        2. Opening Inflows:
            - None
        3. Closing Outflows:
            - Fee (if DEDUCTED_FROM_RETURNS)
        4. Closing Inflows:
            - Option contract (LONG_CALL or LONG_PUT)

        SELL CALL/PUT (Opening Short Position):
        1. Opening Outflows:
            - Margin in collateral asset
            - Fee (if ADDED_TO_COSTS)
        2. Opening Inflows:
            - Premium received
        3. Closing Outflows:
            - Option contract (SHORT_CALL or SHORT_PUT)
            - Fee (if DEDUCTED_FROM_RETURNS)
        4. Closing Inflows:
            - Margin return
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_involved_assets(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)

        # Get position assets
        position_asset = AssetFactory.get_asset(
            order_details.platform,
            order_details.trading_pair.name,
            side=order_details.trade_type.to_position_side(),
        )

        # Add position asset flows based on action
        if order_details.position_action == PositionAction.OPEN:
            if order_details.trade_type == TradeType.BUY:
                # Long option: premium payment and receive contract
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
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
            else:  # SELL
                # Short option: margin requirement and receive premium
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
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
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
        elif order_details.position_action == PositionAction.CLOSE:
            # Deliver position asset
            result.append(
                AssetCashflow(
                    asset=position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
            if order_details.trade_type == TradeType.SELL:
                # Closing long: receive premium
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
            else:  # BUY
                # Closing short: return margin and possible PnL
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

        # Fees
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
                asset=collateral_asset,
                involvement_type=InvolvementType.CLOSING,
                cashflow_type=CashflowType.OUTFLOW,
                reason=CashflowReason.FEE,
            )
        )

        return result

    @classmethod
    def get_opening_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get opening outflows for an option order.

        OPEN LONG CALL/PUT:
        - Premium payment in collateral asset
        - Fee (if ADDED_TO_COSTS)

        OPEN SHORT CALL/PUT:
        - Margin in collateral asset
        - Fee (if ADDED_TO_COSTS)

        CLOSE LONG/SHORT CALL/PUT:
        - Position asset
        - Fee (if ADDED_TO_COSTS)
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_opening_outflows(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)

        if order_details.position_action == PositionAction.OPEN:
            if order_details.trade_type == TradeType.BUY:
                # Long option: premium payment
                premium = cls._calculate_premium(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=premium,
                    )
                )
            elif order_details.trade_type == TradeType.SELL:
                # Short option: margin requirement
                margin = cls._calculate_margin(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.MARGIN,
                        amount=margin,
                    )
                )

            fee_amount = cls._calculate_fee_amount(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=fee_amount,
                )
            )
        elif order_details.position_action == PositionAction.CLOSE:
            # Deliver position asset
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
                    amount=order_details.amount,
                )
            )

        return result

    @classmethod
    def get_opening_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get opening inflows for an option order.

        OPEN/CLOSE LONG/SHORT CALL/PUT:
        - None
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_opening_inflows(order_details))
            return result

        return result

    @classmethod
    def get_closing_outflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get closing outflows for an option order.

        OPEN LONG/SHORT CALL/PUT:
        - Fee (if DEDUCTED_FROM_RETURNS)

        CLOSE LONG CALL/PUT:
        - Fee (if DEDUCTED_FROM_RETURNS)

        CLOSE SHORT CALL/PUT:
        - Negative PnL (if any)
        - Fee (if DEDUCTED_FROM_RETURNS)
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_closing_outflows(order_details))
            return result

        if order_details.position_action == PositionAction.CLOSE:
            collateral_asset = cls._get_outflow_asset(order_details)
            fee_amount = cls._calculate_fee_amount(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=fee_amount,
                )
            )

            # Calculate PnL for closing short positions
            if order_details.trade_type == TradeType.BUY:
                pnl = cls._calculate_pnl(order_details)
                if not pnl.is_nan() and (
                    pnl < s_decimal_0
                ):  # Negative PnL for short position
                    result.append(
                        AssetCashflow(
                            asset=collateral_asset,
                            involvement_type=InvolvementType.CLOSING,
                            cashflow_type=CashflowType.OUTFLOW,
                            reason=CashflowReason.PNL,
                            amount=-pnl,
                        )
                    )

        return result

    @classmethod
    def get_closing_inflows(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        """Get closing inflows for an option order.

        OPEN LONG CALL/PUT:
        - Option contract

        OPEN SHORT CALL/PUT:
        - Position asset
        - Premium received in collateral asset

        CLOSE LONG CALL/PUT:
        - Premium received in collateral asset

        CLOSE SHORT CALL/PUT:
        - Margin return
        - Positive PnL (if any)
        """
        result: list[AssetCashflow] = []

        if order_details.position_action == PositionAction.FLIP:
            order_details_list = order_details.split_order_details()
            for order_details in order_details_list:
                result.extend(cls.get_closing_inflows(order_details))
            return result

        collateral_asset = cls._get_outflow_asset(order_details)
        if order_details.position_action == PositionAction.OPEN:
            if order_details.trade_type == TradeType.BUY:
                # Long option: receive contract
                position_asset = AssetFactory.get_asset(
                    order_details.platform,
                    order_details.trading_pair.name,
                    side=order_details.trade_type.to_position_side(),
                )
                result.append(
                    AssetCashflow(
                        asset=position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=order_details.amount,
                    )
                )
            else:  # SELL
                # Short option: receive position asset
                position_asset = AssetFactory.get_asset(
                    order_details.platform,
                    order_details.trading_pair.name,
                    side=order_details.trade_type.to_position_side(),
                )
                result.append(
                    AssetCashflow(
                        asset=position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=order_details.amount,
                    )
                )
                premium = cls._calculate_premium(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=premium,
                    )
                )
        elif order_details.position_action == PositionAction.CLOSE:
            if order_details.trade_type == TradeType.SELL:
                # Closing long: receive premium
                premium = cls._calculate_premium(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=premium,
                    )
                )
            elif order_details.trade_type == TradeType.BUY:
                # Closing short: return margin and possible positive PnL
                margin = cls._calculate_margin(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.MARGIN,
                        amount=margin,
                    )
                )
                # Add positive PnL if any
                pnl = cls._calculate_pnl(order_details)
                if pnl.is_nan() or (
                    pnl > s_decimal_0
                ):  # Positive PnL for short position
                    result.append(
                        AssetCashflow(
                            asset=collateral_asset,
                            involvement_type=InvolvementType.CLOSING,
                            cashflow_type=CashflowType.INFLOW,
                            reason=CashflowReason.PNL,
                            amount=pnl,
                        )
                    )

        return result


class OptionBalanceEngine(BaseOptionBalanceEngine):
    """Engine for simulating cashflows of regular option trading operations.

    Regular options have:
    - Premium in quote currency
    - Settlement in quote currency
    - Margin in quote currency
    - Contract size in base currency

    BUY CALL/PUT (Opening Long Position):
    1. Opening Outflows:
        - USDT (quote): premium (option price * contract size)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - If exercised:
            - max(0, (spot_price - strike_price) * contract_size) for calls
            - max(0, (strike_price - spot_price) * contract_size) for puts
        - If expired: 0

    SELL CALL/PUT (Opening Short Position):
    1. Opening Outflows:
        - Margin requirement in quote currency
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - USDT (quote): premium (option price * contract size)
    3. Closing Outflows:
        - If assigned:
            - max(0, (spot_price - strike_price) * contract_size) for calls
            - max(0, (strike_price - spot_price) * contract_size) for puts
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Return of remaining margin

    Fee Handling:
    - Supports both absolute and percentage fees
    - Fees are typically in the quote currency
    - Fees can be either added to costs or deducted from returns
    """

    @classmethod
    def _get_outflow_asset(cls, order_details: MinimalOrderDetails) -> Asset:
        """Get the collateral/premium asset.

        For regular options, this is determined by the trading rule:
        - BUY: quote currency for premium payment
        - SELL: quote currency for margin requirement
        """
        if order_details.trade_type == TradeType.BUY:
            symbol = order_details.trading_rule.buy_order_collateral_token
        elif order_details.trade_type == TradeType.SELL:
            symbol = order_details.trading_rule.sell_order_collateral_token
        else:
            raise ValueError(f"Unsupported trade type: {order_details.trade_type}")
        if symbol is None:
            raise ValueError("Collateral token not specified in trading rule")
        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _calculate_premium(cls, order_details: OrderDetails) -> Decimal:
        """Calculate premium in quote currency.

        premium = option_price * contract_size
        """
        return order_details.amount * order_details.price

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in quote currency.

        For regular options:
        - LONG: not applicable
        - SHORT: PnL = ...
        """
        return s_decimal_NaN

    @classmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in quote currency."""
        return s_decimal_NaN

    @classmethod
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate settlement in quote currency.

        For regular options:
        - Calls: max(0, spot_price - strike_price) * contract_size
        - Puts: max(0, strike_price - spot_price) * contract_size
        """
        # Get option type
        is_call = (
            order_details.trading_pair.market_info.instrument_type
            == InstrumentType.CALL_OPTION
        )

        # Get strike price
        strike_price = order_details.trading_pair.market_info.strike_price
        if strike_price is None:
            raise ValueError("Strike price not specified in instrument info")

        spot_price = order_details.price
        contract_size = order_details.amount

        if is_call:
            settlement = max(Decimal("0"), spot_price - strike_price) * contract_size
        else:  # put option
            settlement = max(Decimal("0"), strike_price - spot_price) * contract_size

        return settlement

    @classmethod
    def _calculate_index_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the index price."""
        raise NotImplementedError


class InverseOptionBalanceEngine(BaseOptionBalanceEngine):
    """Engine for simulating cashflows of inverse option trading operations.

    Inverse options have:
    - Premium in base currency
    - Settlement in base currency
    - Margin in base currency
    - Contract value in USD

    BUY CALL/PUT (Opening Long Position):
    1. Opening Outflows:
        - BTC (base): premium (option price * contract_value / entry_price)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - If exercised:
            - max(0, (1/strike_price - 1/spot_price)) * contract_value for calls
            - max(0, (1/spot_price - 1/strike_price)) * contract_value for puts
        - If expired: 0

    SELL CALL/PUT (Opening Short Position):
    1. Opening Outflows:
        - Margin requirement in base currency
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows:
        - BTC (base): premium (option price * contract_value / entry_price)
    3. Closing Outflows:
        - If assigned:
            - max(0, (1/strike_price - 1/spot_price)) * contract_value for calls
            - max(0, (1/spot_price - 1/strike_price)) * contract_value for puts
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - Return of remaining margin

    Key Differences from Regular Options:
    - Premium and settlement in base currency (e.g., BTC)
    - Contract value in USD
    - Settlement calculated using inverse price formula
    - Margin requirements in base currency
    """

    @classmethod
    def _get_outflow_asset(cls, order_details: MinimalOrderDetails) -> Asset:
        """Get the collateral/premium asset.

        For inverse options, this is always the base currency
        (e.g., BTC in BTC/USD)
        """
        symbol = order_details.trading_pair.base
        asset = AssetFactory.get_asset(order_details.platform, symbol)
        return asset

    @classmethod
    def _calculate_premium(cls, order_details: OrderDetails) -> Decimal:
        """Calculate premium in base currency.

        premium_btc = (premium_usd * contract_value) / entry_price
        """
        premium_usd = order_details.amount * order_details.price
        entry_price = _safe_decimal(order_details.index_price)
        return premium_usd / entry_price

    @classmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in base currency."""
        return s_decimal_NaN

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in base currency.

        For inverse options:
        - LONG: not applicable
        - SHORT: PnL = ...
        """
        return s_decimal_NaN

    @classmethod
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate settlement in base currency.

        For inverse options:
        - Calls: max(0, (1/strike_price - 1/spot_price)) * contract_value
        - Puts: max(0, (1/spot_price - 1/strike_price)) * contract_value
        """
        # Get option type
        is_call = (
            order_details.trading_pair.market_info.instrument_type
            == InstrumentType.INVERSE_CALL_OPTION
        )

        # Get strike price
        strike_price = order_details.trading_pair.market_info.strike_price
        if strike_price is None:
            raise ValueError("Strike price not specified in instrument info")

        spot_price = order_details.price
        contract_value = order_details.amount  # In USD

        if is_call:
            settlement = max(
                Decimal("0"),
                (Decimal("1") / strike_price - Decimal("1") / spot_price)
                * contract_value,
            )
        else:  # put option
            settlement = max(
                Decimal("0"),
                (Decimal("1") / spot_price - Decimal("1") / strike_price)
                * contract_value,
            )

        return settlement

    @classmethod
    def _calculate_index_price(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the index price."""
        raise NotImplementedError
