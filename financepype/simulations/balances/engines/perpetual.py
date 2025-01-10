from abc import abstractmethod
from decimal import Decimal

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
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


class BasePerpetualBalanceEngine(BalanceEngine):
    """Base class for perpetual futures balance engines.

    Provides common functionality for both regular and inverse perpetual futures:
    - Asset flow patterns (OPEN/CLOSE/FLIP)
    - Fee handling
    - Position management

    Fee Calculation Scenarios:
    1. Regular Perpetuals (e.g., BTC-USDT perpetuals):
       A. Absolute Fees:
          - Fixed amount in the fee asset (usually quote currency)
          - Example: 10 USDT fee for any trade size
          - BUY/SELL with ADDED_TO_COSTS: Fee deducted immediately
          - BUY/SELL with DEDUCTED_FROM_RETURNS: Fee deducted at position close

       B. Percentage Fees in Quote Currency (USDT):
          - Based on notional value (amount * price)
          - BUY with ADDED_TO_COSTS:
            * Opening 1 BTC position at $50,000 with 0.1% fee
            * Fee = $50,000 * 0.1% = $50 USDT
          - BUY with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from PnL at close
          - SELL with ADDED_TO_COSTS:
            * Selling 1 BTC position at $50,000 with 0.1% fee
            * Fee = $50,000 * 0.1% = $50 USDT
          - SELL with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from PnL at close

    2. Inverse Perpetuals (e.g., BTC/USD perpetuals):
       A. Absolute Fees:
          - Fixed amount in the fee asset (usually base currency)
          - Example: 0.001 BTC fee for any trade size
          - BUY/SELL with ADDED_TO_COSTS: Fee deducted immediately
          - BUY/SELL with DEDUCTED_FROM_RETURNS: Fee deducted at position close

       B. Percentage Fees in Base Currency (BTC):
          - Based on position size in contracts
          - BUY with ADDED_TO_COSTS:
            * Opening $50,000 worth position with 0.1% fee
            * Position size = $50,000 / $50,000 = 1 BTC
            * Fee = 1 BTC * 0.1% = 0.001 BTC
          - BUY with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from PnL at close
          - SELL with ADDED_TO_COSTS:
            * Selling $50,000 worth position with 0.1% fee
            * Position size = $50,000 / $50,000 = 1 BTC
            * Fee = 1 BTC * 0.1% = 0.001 BTC
          - SELL with DEDUCTED_FROM_RETURNS:
            * Same calculation, deducted from PnL at close

    Subclasses must implement:
    - _get_outflow_asset: Define which asset is used for margin/collateral
    - _calculate_pnl: Define PnL calculation logic
    - _calculate_margin: Define margin calculation logic
    - _calculate_index_price: Define index price calculation logic
    """

    @classmethod
    def _get_margin(cls, order_details: OrderDetails) -> Decimal:
        """Get the margin for the perpetual."""
        return (
            order_details.margin
            if order_details.margin is not None
            else cls._calculate_margin(order_details)
        )

    @classmethod
    @abstractmethod
    def _get_outflow_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the collateral asset for margin.

        Regular perpetuals: Quote currency (e.g., USDT in BTC/USDT)
        Inverse perpetuals: Base currency (e.g., BTC in BTC/USD)
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the required margin amount.

        Regular perpetuals: (amount * price) / leverage in quote currency
        Inverse perpetuals: (contract_value) / (leverage * price) in base currency
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the PnL for a position.

        Regular perpetuals: (exit_price - entry_price) * position_size in quote currency
        Inverse perpetuals: (1/entry_price - 1/exit_price) * contract_value in base currency
        """
        raise NotImplementedError

    @classmethod
    def _get_expected_fee_asset(cls, order_details: OrderDetails) -> Asset:
        """Get the expected fee asset based on the trade type and fee impact type."""
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
            return cls._get_outflow_asset(order_details)
        elif order_details.fee.impact_type == FeeImpactType.ADDED_TO_COSTS:
            return cls._get_outflow_asset(order_details)
        else:
            raise ValueError(
                f"Unsupported fee impact type: {order_details.fee.impact_type}"
            )

    @classmethod
    def _calculate_fee_amount(cls, order_details: OrderDetails) -> Decimal:
        """Calculate the fee amount based on fee type and trade details.

        The fee calculation depends on the perpetual type (regular vs inverse) and fee asset:

        1. Regular Perpetuals:
           - Quote currency fees (USDT): Based on notional value
           - Example: 0.1% fee on $50,000 position = $50 USDT fee

        2. Inverse Perpetuals:
           - Base currency fees (BTC): Based on position size
           - Example: 0.1% fee on 1 BTC position = 0.001 BTC fee

        Args:
            order_details: Details of the perpetual futures order

        Returns:
            The calculated fee amount

        Raises:
            ValueError: If fee type is not supported
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
            notional_value = order_details.amount * order_details.price
            fee_amount = notional_value * (order_details.fee.amount / Decimal("100"))
            return fee_amount

        # Handle unsupported fee types
        raise ValueError(f"Unsupported fee type: {order_details.fee.fee_type}")

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
            # For flip, we'll need both closing the existing position and opening a new one
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
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.PNL,
                )
            )
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
                    asset=potential_closing_position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
        elif order_details.position_action == PositionAction.CLOSE:
            result.append(
                AssetCashflow(
                    asset=potential_closing_position_asset,
                    involvement_type=InvolvementType.OPENING,
                    cashflow_type=CashflowType.OUTFLOW,
                    reason=CashflowReason.OPERATION,
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
        elif order_details.position_action == PositionAction.OPEN:
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
                    asset=potential_closing_position_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.OPERATION,
                )
            )
        else:
            raise ValueError(
                f"Unsupported position action: {order_details.position_action}"
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
    def get_opening_outflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)

        # Initial margin
        margin_amount = cls._get_margin(order_details)
        result.append(
            AssetCashflow(
                asset=collateral_asset,
                involvement_type=InvolvementType.OPENING,
                cashflow_type=CashflowType.OUTFLOW,
                reason=CashflowReason.OPERATION,
                amount=margin_amount,
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
                    amount=cls._calculate_fee_amount(order_details),
                )
            )

        return result

    @classmethod
    def get_opening_inflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        return []

    @classmethod
    def get_closing_outflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []

        # Fee deducted from returns
        if order_details.fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS:
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

        return result

    @classmethod
    def get_closing_inflows(
        cls, order_details: OrderDetails, current_balances: dict[Asset, Decimal]
    ) -> list[AssetCashflow]:
        result: list[AssetCashflow] = []
        collateral_asset = cls._get_outflow_asset(order_details)

        # Calculate PnL
        if order_details.position_action in [PositionAction.CLOSE, PositionAction.FLIP]:
            pnl = cls._calculate_pnl(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.PNL,
                    amount=abs(
                        pnl
                    ),  # Amount should be positive, direction handled by cashflow_type
                )
            )
        elif order_details.position_action == PositionAction.OPEN:
            # For OPEN positions, we return the initial margin plus any PnL
            margin_amount = cls._get_margin(order_details)
            pnl = cls._calculate_pnl(order_details)
            result.append(
                AssetCashflow(
                    asset=collateral_asset,
                    involvement_type=InvolvementType.CLOSING,
                    cashflow_type=CashflowType.INFLOW,
                    reason=CashflowReason.PNL,
                    amount=margin_amount + abs(pnl),
                )
            )

        return result


class PerpetualBalanceEngine(BasePerpetualBalanceEngine):
    """Engine for simulating cashflows of regular perpetual futures trading operations.

    Regular perpetuals have:
    - PnL in quote currency
    - Margin in quote currency
    - Position size in base currency

    OPEN LONG:
    1. Opening Outflows:
        - USDT (quote): initial margin ((amount * price) / leverage)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - USDT (quote): margin return + PnL
        - PnL = (exit_price - entry_price) * position_size

    OPEN SHORT:
    1. Opening Outflows:
        - USDT (quote): initial margin ((amount * price) / leverage)
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - USDT (quote): margin return + PnL
        - PnL = (entry_price - exit_price) * position_size

    FLIP:
    - Combines CLOSE of existing position with OPEN of new position
    - All cashflows from both operations apply
    - PnL is realized from the closed position

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
    def _calculate_margin(cls, order_details: OrderDetails) -> Decimal:
        """Calculate margin in quote currency.

        margin = (amount * price) / leverage
        """
        return (order_details.amount * order_details.price) / Decimal(
            order_details.leverage
        )

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in quote currency.

        For regular perpetuals:
        - LONG: PnL = (exit_price - entry_price) * position_size
        - SHORT: PnL = (entry_price - exit_price) * position_size
        """
        if order_details.entry_price is None or order_details.exit_price is None:
            return Decimal("0")

        entry_price = order_details.entry_price
        exit_price = order_details.exit_price
        position_size = order_details.amount

        if order_details.trade_type == TradeType.BUY:
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

    OPEN LONG:
    1. Opening Outflows:
        - BTC (base): initial margin (contract_value / (leverage * entry_price))
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - BTC (base): margin return + PnL
        - PnL = (1/entry_price - 1/exit_price) * contract_value

    OPEN SHORT:
    1. Opening Outflows:
        - BTC (base): initial margin (contract_value / (leverage * entry_price))
        - Fee asset: fee amount (if ADDED_TO_COSTS)
    2. Opening Inflows: None
    3. Closing Outflows:
        - Fee asset: fee amount (if DEDUCTED_FROM_RETURNS)
    4. Closing Inflows:
        - BTC (base): margin return + PnL
        - PnL = (1/exit_price - 1/entry_price) * contract_value

    FLIP:
    - Combines CLOSE of existing position with OPEN of new position
    - All cashflows from both operations apply
    - PnL is realized from the closed position

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
        contract_value = order_details.amount  # In USD
        entry_price = order_details.entry_index_price
        return contract_value / (Decimal(order_details.leverage) * entry_price)

    @classmethod
    def _calculate_pnl(cls, order_details: OrderDetails) -> Decimal:
        """Calculate PnL in base currency.

        For inverse perpetuals:
        - LONG: PnL = (1/entry_price - 1/exit_price) * contract_value
        - SHORT: PnL = (1/exit_price - 1/entry_price) * contract_value
        """
        if order_details.entry_price is None or order_details.exit_price is None:
            return Decimal("0")

        entry_price = order_details.entry_price
        exit_price = order_details.exit_price
        contract_value = order_details.amount  # In USD

        if order_details.trade_type == TradeType.BUY:
            pnl = (
                Decimal("1") / entry_price - Decimal("1") / exit_price
            ) * contract_value
        else:
            pnl = (
                Decimal("1") / exit_price - Decimal("1") / entry_price
            ) * contract_value

        return pnl
