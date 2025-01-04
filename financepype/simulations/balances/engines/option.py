from abc import abstractmethod
from decimal import Decimal

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.markets.market import InstrumentType
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.orders.models import PositionAction, TradeType
from financepype.simulations.balances.engines.engine import BalanceEngine
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)


class BaseOptionBalanceEngine(BalanceEngine):
    """Base class for option balance engines.

    Provides common functionality for both regular and inverse options:
    - Asset flow patterns (OPEN/CLOSE)
    - Fee handling
    - Premium collection/payment
    - Settlement calculation
    - Margin management

    Fee Calculation Scenarios:
    1. Regular Options (e.g., BTC-USDT options):
       A. Absolute Fees:
          - Fixed amount in the fee asset (usually quote currency)
          - Example: 10 USDT fee for any trade size
          - BUY/SELL with ADDED_TO_COSTS: Fee deducted immediately
          - BUY/SELL with DEDUCTED_FROM_RETURNS: Fee deducted at settlement

       B. Percentage Fees in Quote Currency (USDT):
          - Based on premium value for option trades
          - BUY with ADDED_TO_COSTS:
            * Buying 1 BTC call at $1000 premium with 0.1% fee
            * Fee = $1000 * 0.1% = $1 USDT
          - BUY with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from settlement
          - SELL with ADDED_TO_COSTS:
            * Selling 1 BTC call at $1000 premium with 0.1% fee
            * Fee = $1000 * 0.1% = $1 USDT
          - SELL with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from margin return

    2. Inverse Options (e.g., BTC/USD options):
       A. Absolute Fees:
          - Fixed amount in the fee asset (usually base currency)
          - Example: 0.001 BTC fee for any trade size
          - BUY/SELL with ADDED_TO_COSTS: Fee deducted immediately
          - BUY/SELL with DEDUCTED_FROM_RETURNS: Fee deducted at settlement

       B. Percentage Fees in Base Currency (BTC):
          - Based on premium value in BTC
          - BUY with ADDED_TO_COSTS:
            * Buying $50,000 notional at 0.02 BTC premium with 0.1% fee
            * Fee = 0.02 BTC * 0.1% = 0.00002 BTC
          - BUY with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from settlement
          - SELL with ADDED_TO_COSTS:
            * Selling $50,000 notional at 0.02 BTC premium with 0.1% fee
            * Fee = 0.02 BTC * 0.1% = 0.00002 BTC
          - SELL with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from margin return

    Subclasses must implement:
    - _get_outflow_asset: Define which asset is used for margin/collateral
    - _calculate_premium: Define premium calculation logic
    - _calculate_margin: Define margin calculation logic
    - _calculate_settlement: Define settlement calculation logic
    """

    @classmethod
    @abstractmethod
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the collateral/premium asset.

        Regular options: Quote currency (e.g., USDT in BTC/USDT)
        Inverse options: Base currency (e.g., BTC in BTC/USD)
        """
        raise NotImplementedError

    @classmethod
    def _get_fee_impact(cls, order_details: OrderDetails) -> dict[Asset, Decimal]:
        """Calculate the fee amount based on fee type and trade details.

        The fee calculation depends on the option type (regular vs inverse) and fee asset:

        1. Regular Options:
           - Quote currency fees (USDT): Based on premium value
           - Example: 0.1% fee on $1000 premium = $1 USDT fee

        2. Inverse Options:
           - Base currency fees (BTC): Based on premium value in BTC
           - Example: 0.1% fee on 0.02 BTC premium = 0.00002 BTC fee

        Args:
            order_details: Details of the option trading order

        Returns:
            Dict mapping fee asset to fee amount

        Raises:
            NotImplementedError: If fee is in an asset not involved in the trade
            ValueError: If fee type is not supported
        """
        fee_asset = order_details.fee.asset
        collateral_asset = cls._get_outflow_asset(order_details)

        # Validate fee asset is involved in the trade
        if fee_asset != collateral_asset:
            raise NotImplementedError(
                f"Fee in {fee_asset} not supported. Expected {collateral_asset}"
            )

        # Handle absolute fees (fixed amount)
        if order_details.fee.fee_type == FeeType.ABSOLUTE:
            return {fee_asset: order_details.fee.amount}

        # Handle percentage fees
        if order_details.fee.fee_type == FeeType.PERCENTAGE:
            # Calculate fee based on premium
            premium = cls._calculate_premium(order_details)
            fee_amount = premium * (order_details.fee.amount / Decimal("100"))
            return {fee_asset: fee_amount}

        # Handle unsupported fee types
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

    @classmethod
    @abstractmethod
    def _calculate_premium(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the option premium.

        Regular options: premium = option_price * contract_size in quote currency
        Inverse options: premium = (option_price * contract_value) / entry_price in base currency
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the margin requirement for short options.

        Regular options: Based on strike price and contract size in quote currency
        Inverse options: Based on strike price and contract value in base currency
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the settlement amount for exercised/assigned options.

        Regular options:
        - Calls: max(0, spot_price - strike_price) * contract_size
        - Puts: max(0, strike_price - spot_price) * contract_size

        Inverse options:
        - Calls: max(0, 1/strike_price - 1/spot_price) * contract_value
        - Puts: max(0, 1/spot_price - 1/strike_price) * contract_value
        """
        raise NotImplementedError

    @classmethod
    def get_involved_assets(cls, order_details: OrderDetails) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)
        potential_opening_position_asset = AssetFactory.get_asset(
            order_details.platform,
            order_details.trading_pair.name,
            side=order_details.trade_type.to_position_side(),
        )
        potential_closing_position_asset = AssetFactory.get_asset(
            order_details.platform,
            order_details.trading_pair.name,
            side=order_details.trade_type.opposite().to_position_side(),
        )

        if order_details.position_action == PositionAction.FLIP:
            # Closing the existing position
            if order_details.trade_type == TradeType.BUY:
                # Closing short position: potential settlement payment
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Return margin
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Opening long position: pay premium
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Position asset flows
                result.append(
                    AssetCashflow(
                        asset=potential_opening_position_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                result.append(
                    AssetCashflow(
                        asset=potential_closing_position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
            else:  # SELL
                # Closing long position: receive settlement if exercised
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.PNL,
                    )
                )
                # Opening short position: receive premium, lock margin
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
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Position asset flows
                result.append(
                    AssetCashflow(
                        asset=potential_opening_position_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                result.append(
                    AssetCashflow(
                        asset=potential_closing_position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
        elif order_details.position_action == PositionAction.OPEN:
            if order_details.trade_type == TradeType.BUY:
                # Long option: pay premium
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Position asset flow
                result.append(
                    AssetCashflow(
                        asset=potential_opening_position_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
            else:
                # Short option: receive premium, lock margin
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
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Position asset flow
                result.append(
                    AssetCashflow(
                        asset=potential_opening_position_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
        elif order_details.position_action == PositionAction.CLOSE:
            if order_details.trade_type == TradeType.BUY:
                # Closing short: pay settlement if assigned
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Return margin
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
                # Position asset flow
                result.append(
                    AssetCashflow(
                        asset=potential_closing_position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )
            else:
                # Closing long: receive settlement if exercised
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.PNL,
                    )
                )
                # Position asset flow
                result.append(
                    AssetCashflow(
                        asset=potential_closing_position_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                    )
                )

        # Fee
        if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            fee_impact = cls._get_fee_impact(order_details)
            result.append(
                AssetCashflow(
                    asset=order_details.fee.asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=fee_impact[order_details.fee.asset],
                )
            )

        return result

    @classmethod
    def get_opening_outflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
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
            else:
                # Short option: margin requirement
                margin = cls._calculate_margin(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.OPENING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=margin,
                    )
                )

        # Fee
        if order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            fee_impact = cls._get_fee_impact(order_details)
            result.append(
                AssetCashflow(
                    asset=order_details.fee.asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=fee_impact[order_details.fee.asset],
                )
            )

        return result

    @classmethod
    def get_opening_inflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)

        if (
            order_details.position_action == PositionAction.OPEN
            and order_details.trade_type == TradeType.SELL
        ):
            # Short option: receive premium
            premium = cls._calculate_premium(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                    amount=premium,
                )
            )

        return result

    @classmethod
    def get_closing_outflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)

        if (
            order_details.position_action == PositionAction.CLOSE
            and order_details.trade_type == TradeType.BUY
        ):
            # Closing short position: potential settlement payment
            settlement = cls._calculate_settlement(order_details)
            if settlement > 0:
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.OUTFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=settlement,
                    )
                )

        # Fee
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
            fee_impact = cls._get_fee_impact(order_details)
            result.append(
                AssetCashflow(
                    asset=order_details.fee.asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.FEE,
                    amount=fee_impact[order_details.fee.asset],
                )
            )

        return result

    @classmethod
    def get_closing_inflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)

        if order_details.position_action == PositionAction.CLOSE:
            if order_details.trade_type == TradeType.BUY:
                # Closing short: return of remaining margin
                margin = cls._calculate_margin(order_details)
                result.append(
                    AssetCashflow(
                        asset=collateral_asset,
                        involvement_type=InvolvementType.CLOSING,
                        cashflow_type=CashflowType.INFLOW,
                        reason=CashflowReason.OPERATION,
                        amount=margin,
                    )
                )
            else:
                # Closing long: potential settlement receipt
                settlement = cls._calculate_settlement(order_details)
                if settlement > 0:
                    result.append(
                        AssetCashflow(
                            asset=collateral_asset,
                            involvement_type=InvolvementType.CLOSING,
                            cashflow_type=CashflowType.INFLOW,
                            reason=CashflowReason.PNL,
                            amount=settlement,
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
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
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
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in quote currency.

        For regular options, margin is typically:
        - For calls: max(premium, (strike_price - current_price) * contract_size * margin_ratio)
        - For puts: max(premium, (current_price - strike_price) * contract_size * margin_ratio)

        The margin ratio is determined by the trading rules and should account for:
        - Option type (call/put)
        - Time to expiry
        - Strike distance from current price
        """
        instrument_info = order_details.trading_pair.instrument_info

        # Get option type
        is_call = instrument_info.instrument_type == InstrumentType.CALL_OPTION

        # Get strike price
        strike_price = instrument_info.strike_price
        if strike_price is None:
            raise ValueError("Strike price not specified in instrument info")

        # Calculate premium
        premium = order_details.amount * order_details.price

        # Get current price and contract size
        current_price = order_details.index_price
        contract_size = order_details.amount

        # Get margin ratio from trading rules (default to 10% if not specified)
        margin_ratio = Decimal("0.1")
        if "option_margin_ratio" in order_details.trading_rule.other_rules:
            margin_ratio = Decimal(
                str(order_details.trading_rule.other_rules["option_margin_ratio"])
            )

        # Calculate required margin based on option type
        if is_call:
            margin = max(
                premium,  # minimum margin is the premium paid
                (
                    (strike_price - current_price) * contract_size * margin_ratio
                    if strike_price > current_price
                    else Decimal("0")
                ),
            )
        else:  # put option
            margin = max(
                premium,  # minimum margin is the premium paid
                (
                    (current_price - strike_price) * contract_size * margin_ratio
                    if current_price > strike_price
                    else Decimal("0")
                ),
            )

        return margin

    @classmethod
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate settlement in quote currency.

        For regular options:
        - Calls: max(0, spot_price - strike_price) * contract_size
        - Puts: max(0, strike_price - spot_price) * contract_size
        """
        instrument_info = order_details.trading_pair.instrument_info

        # Get option type
        is_call = instrument_info.instrument_type == InstrumentType.CALL_OPTION

        # Get strike price
        strike_price = instrument_info.strike_price
        if strike_price is None:
            raise ValueError("Strike price not specified in instrument info")

        spot_price = order_details.price
        contract_size = order_details.amount

        if is_call:
            settlement = max(Decimal("0"), spot_price - strike_price) * contract_size
        else:  # put option
            settlement = max(Decimal("0"), strike_price - spot_price) * contract_size

        return settlement


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
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
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
        entry_price = order_details.index_price
        return premium_usd / entry_price

    @classmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in base currency.

        For inverse options, margin is typically:
        - For calls: max(premium, contract_value * margin_ratio / current_price)
        - For puts: max(premium, contract_value * margin_ratio / current_price)

        The margin ratio is determined by the trading rules and should account for:
        - Option type (call/put)
        - Time to expiry
        - Strike distance from current price
        """
        instrument_info = order_details.trading_pair.instrument_info

        # Get option type
        is_call = instrument_info.instrument_type == InstrumentType.INVERSE_CALL_OPTION

        # Get strike price
        strike_price = instrument_info.strike_price
        if strike_price is None:
            raise ValueError("Strike price not specified in instrument info")

        # Calculate premium in base currency
        premium = cls._calculate_premium(order_details)

        # Get current price and contract value
        current_price = order_details.index_price
        contract_value = order_details.amount  # In USD

        # Get margin ratio from trading rules (default to 10% if not specified)
        margin_ratio = Decimal("0.1")
        if "option_margin_ratio" in order_details.trading_rule.other_rules:
            margin_ratio = Decimal(
                str(order_details.trading_rule.other_rules["option_margin_ratio"])
            )

        # Calculate required margin in base currency
        if is_call:
            margin = max(
                premium,  # minimum margin is the premium paid
                (
                    (contract_value * margin_ratio) / current_price
                    if strike_price > current_price
                    else Decimal("0")
                ),
            )
        else:  # put option
            margin = max(
                premium,  # minimum margin is the premium paid
                (
                    (contract_value * margin_ratio) / current_price
                    if current_price > strike_price
                    else Decimal("0")
                ),
            )

        return margin

    @classmethod
    def _calculate_settlement(cls, order_details: OrderDetails) -> Decimal:
        """Calculate settlement in base currency.

        For inverse options:
        - Calls: max(0, (1/strike_price - 1/spot_price)) * contract_value
        - Puts: max(0, (1/spot_price - 1/strike_price)) * contract_value
        """
        instrument_info = order_details.trading_pair.instrument_info

        # Get option type
        is_call = instrument_info.instrument_type == InstrumentType.INVERSE_CALL_OPTION

        # Get strike price
        strike_price = instrument_info.strike_price
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
