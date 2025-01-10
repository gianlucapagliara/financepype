"""Models for balance simulation engines.

This module defines the core data structures used by balance simulation engines
to track and simulate cashflows in trading operations. It provides models for
representing order details, cashflows, and simulation results.

The module uses Pydantic models for data validation and type safety, with
support for decimal arithmetic to ensure precise financial calculations.

Key Components:
1. Enums for categorizing cashflows:
   - CashflowReason: Purpose of the cashflow (operation, fee, PnL)
   - InvolvementType: When the cashflow occurs (opening, closing)
   - CashflowType: Direction of the cashflow (inflow, outflow)

2. Models:
   - AssetCashflow: Individual asset movement with amount and metadata
   - OrderDetails: Complete specification of a trading order
   - OperationSimulationResult: Results of simulating an operation

Example:
    >>> # Create an order
    >>> order = OrderDetails(
    ...     trading_pair=TradingPair("BTC-USD"),
    ...     amount=Decimal("1.0"),
    ...     price=Decimal("50000"),
    ...     ...
    ... )
    >>>
    >>> # Create a cashflow
    >>> flow = AssetCashflow(
    ...     asset=Asset("BTC"),
    ...     involvement_type=InvolvementType.OPENING,
    ...     cashflow_type=CashflowType.OUTFLOW,
    ...     reason=CashflowReason.OPERATION,
    ...     amount=Decimal("1.0")
    ... )
"""

import time
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0, s_decimal_NaN
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import OperationFee
from financepype.operations.orders.models import (
    OrderModifier,
    OrderType,
    PositionAction,
    TradeType,
)
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule


class CashflowReason(Enum):
    """Reason for a cashflow in a trading operation.

    This enum categorizes the purpose of each cashflow:
    - OPERATION: Direct result of the trading operation (e.g., buying/selling)
    - FEE: Trading fees, commissions, etc.
    - PNL: Profit or loss from the operation
    """

    OPERATION = "operation"
    FEE = "fee"
    PNL = "pnl"


class InvolvementType(Enum):
    """When a cashflow occurs in a trading operation.

    This enum specifies the timing of each cashflow:
    - OPENING: When opening a position (e.g., initial margin, purchase cost)
    - CLOSING: When closing a position (e.g., sale proceeds, PnL)
    """

    OPENING = "opening"
    CLOSING = "closing"


class CashflowType(Enum):
    """Direction of a cashflow in a trading operation.

    This enum specifies whether assets are entering or leaving the account:
    - OUTFLOW: Assets leaving the account (negative impact on balance)
    - INFLOW: Assets entering the account (positive impact on balance)
    """

    OUTFLOW = "outflow"
    INFLOW = "inflow"


class AssetCashflow(BaseModel):
    """Model for a single asset movement in a trading operation.

    This class represents one asset flow (in or out) during a trading operation,
    including metadata about when it occurs and why.

    Attributes:
        asset (Asset): The asset being moved
        involvement_type (InvolvementType): When the flow occurs (opening/closing)
        cashflow_type (CashflowType): Direction of flow (inflow/outflow)
        reason (CashflowReason): Purpose of the flow (operation/fee/PnL)
        amount (Decimal): Amount of the asset being moved (always positive)

    Example:
        >>> flow = AssetCashflow(
        ...     asset=Asset("BTC"),
        ...     involvement_type=InvolvementType.OPENING,
        ...     cashflow_type=CashflowType.OUTFLOW,
        ...     reason=CashflowReason.OPERATION,
        ...     amount=Decimal("1.0")
        ... )
        >>> print(flow.cashflow_amount)  # -1.0 (negative for outflow)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    asset: Asset = Field(description="The asset being moved")
    involvement_type: InvolvementType = Field(description="When the flow occurs")
    cashflow_type: CashflowType = Field(description="Direction of the flow")
    reason: CashflowReason = Field(description="Purpose of the flow")
    amount: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Amount of the asset (always positive)",
    )

    @property
    def is_outflow(self) -> bool:
        """Whether this is an outflow (asset leaving the account)."""
        return self.cashflow_type == CashflowType.OUTFLOW

    @property
    def is_inflow(self) -> bool:
        """Whether this is an inflow (asset entering the account)."""
        return self.cashflow_type == CashflowType.INFLOW

    @property
    def cashflow_amount(self) -> Decimal:
        """The signed amount of the cashflow (negative for outflows)."""
        if self.is_outflow:
            return -self.amount
        return self.amount


class OrderDetails(BaseModel):
    """Complete specification of a trading order for simulation.

    This class contains all the information needed to simulate a trading order,
    including the trading pair, order parameters, and associated rules.

    Attributes:
        trading_pair (TradingPair): The pair being traded
        trading_rule (TradingRule): Rules governing the trade
        platform (Platform): Trading platform
        trade_type (TradeType): Type of trade (e.g., buy, sell)
        order_type (OrderType): Type of order (e.g., market, limit)
        order_modifiers (set[OrderModifier]): Additional order specifications
        amount (Decimal): Order size
        price (Decimal): Order price
        leverage (int): Leverage multiplier
        position_action (PositionAction): Opening/closing action
        index_price (Decimal): Current index price
        entry_price (Decimal | None): Position entry price
        exit_price (Decimal | None): Position exit price
        fee (OperationFee): Fee structure for the order

    Example:
        >>> order = OrderDetails(
        ...     trading_pair=TradingPair("BTC-USD"),
        ...     trading_rule=rule,
        ...     platform=platform,
        ...     trade_type=TradeType.BUY,
        ...     order_type=OrderType.MARKET,
        ...     amount=Decimal("1.0"),
        ...     price=Decimal("50000"),
        ...     leverage=1,
        ...     position_action=PositionAction.OPEN,
        ...     index_price=Decimal("50000"),
        ...     fee=fee
        ... )
    """

    trading_pair: TradingPair = Field(description="The pair being traded")
    trading_rule: TradingRule = Field(description="Rules governing the trade")
    platform: Platform = Field(description="Trading platform")
    trade_type: TradeType = Field(description="Type of trade (buy/sell)")
    order_type: OrderType = Field(description="Type of order (market/limit/etc)")
    order_modifiers: set[OrderModifier] = Field(
        default_factory=set,
        description="Additional order specifications",
    )
    amount: Decimal = Field(ge=0, description="Order size")
    price: Decimal = Field(description="Order price")
    leverage: int = Field(description="Leverage multiplier")
    position_action: PositionAction = Field(
        description="Opening/closing action",
    )
    margin: Decimal | None = Field(
        default=None,
        description="Margin amount. If not provided, it will be calculated.",
    )
    entry_index_price: Decimal = Field(description="Current index price")
    entry_price: Decimal | None = Field(
        default=None,
        description="Position entry price",
    )
    exit_price: Decimal | None = Field(
        default=None,
        description="Position exit price",
    )
    fee: OperationFee = Field(description="Fee structure for the order")

    def check_potential_failure(self, current_timestamp: float | None = None) -> None:
        """Check if the order would fail based on trading rules.

        This method validates the order against trading rules to ensure it would
        be accepted by the exchange. It checks:
        - Order type support
        - Order modifier support
        - Trading rule expiration
        - Minimum/maximum order size
        - Minimum/maximum notional size

        Args:
            current_timestamp (float | None): Current time for expiry check

        Raises:
            ValueError: If any validation fails, with a descriptive message
        """
        if self.order_type not in self.trading_rule.supported_order_types:
            raise ValueError(
                f"{self.order_type} is not in the list of supported order types"
            )
        if self.order_modifiers.issubset(self.trading_rule.supported_order_modifiers):
            raise ValueError(
                f"{self.order_modifiers} is not in the list of supported order modifiers"
            )

        current_timestamp = current_timestamp or time.time()
        if self.trading_rule.is_expired(current_timestamp):
            raise ValueError(
                f"Order on {self.trading_pair} cannot be created since the trading rule is expired."
            )
        if self.amount < self.trading_rule.min_order_size:
            raise ValueError(
                f"{self.trade_type.name.title()} order amount {self.amount} is lower than the minimum order"
                f" size {self.trading_rule.min_order_size}. The order will not be created."
            )
        if self.amount > self.trading_rule.max_order_size:
            raise ValueError(
                f"{self.trade_type.name.title()} order amount {self.amount} is higher than the maximum order"
                f" size {self.trading_rule.max_order_size}. The order will not be created."
            )
        if (
            self.price is not None
            and self.price is not s_decimal_NaN
            and self.price > s_decimal_0
            and self.amount * self.price < self.trading_rule.min_notional_size
        ):
            raise ValueError(
                f"{self.trade_type.name.title()} order notional {self.amount * self.price} is lower than the "
                f"minimum notional size {self.trading_rule.min_notional_size}. "
                "The order will not be created."
            )
        if (
            self.price is not None
            and self.price is not s_decimal_NaN
            and self.price > s_decimal_0
            and self.amount * self.price > self.trading_rule.max_notional_size
        ):
            raise ValueError(
                f"{self.trade_type.name.title()} order notional {self.amount * self.price} is higher than the "
                f"maximum notional size {self.trading_rule.max_notional_size}. "
                "The order will not be created."
            )


class OperationSimulationResult(BaseModel):
    """Results of simulating a trading operation.

    This class contains the complete results of simulating a trading operation,
    including all cashflows that would occur during the operation.

    Attributes:
        operation_details (Any): Details of the simulated operation
        cashflows (list[AssetCashflow]): All cashflows in the operation

    Example:
        >>> result = OperationSimulationResult(
        ...     operation_details=order,
        ...     cashflows=[
        ...         AssetCashflow(...),  # Opening outflow
        ...         AssetCashflow(...),  # Closing inflow
        ...     ]
        ... )
        >>> print(result.opening_outflows)  # {Asset("BTC"): Decimal("-1.0")}
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    operation_details: Any = Field(description="Details of the simulated operation")
    cashflows: list[AssetCashflow] = Field(
        description="All cashflows in the operation",
    )

    @property
    def opening_cashflow(self) -> dict[Asset, Decimal]:
        """Net cashflow at position opening for each asset."""
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
        }

    @property
    def opening_outflows(self) -> dict[Asset, Decimal]:
        """Assets leaving the account at position opening."""
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
            and cashflow.is_outflow
        }

    @property
    def opening_inflows(self) -> dict[Asset, Decimal]:
        """Assets entering the account at position opening."""
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
            and cashflow.is_inflow
        }

    @property
    def closing_cashflow(self) -> dict[Asset, Decimal]:
        """Net cashflow at position closing for each asset."""
        return {
            cashflow.asset: cashflow.amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
        }

    @property
    def closing_outflows(self) -> dict[Asset, Decimal]:
        """Assets leaving the account at position closing."""
        return {
            cashflow.asset: cashflow.amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
            and cashflow.is_outflow
        }

    @property
    def closing_inflows(self) -> dict[Asset, Decimal]:
        """Assets entering the account at position closing."""
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
            and cashflow.is_inflow
        }
