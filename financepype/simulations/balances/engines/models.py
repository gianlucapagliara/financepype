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

import functools
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0, s_decimal_NaN
from financepype.markets.position import Position
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
    - MARGIN: Margin used for the operation
    - FEE: Trading fees, commissions, etc.
    - PNL: Profit or loss from the operation
    - FUNDING: Funding rate payment (for perpetual positions)
    - COLLATERAL: Collateral deposit/return (for borrow/staking operations)
    - INTEREST: Interest payment (for borrow operations)
    """

    OPERATION = "operation"
    MARGIN = "margin"
    FEE = "fee"
    PNL = "pnl"
    FUNDING = "funding"
    COLLATERAL = "collateral"
    INTEREST = "interest"
    REWARD = "reward"


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


@dataclass(slots=True)
class AssetCashflow:
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

    asset: Asset
    involvement_type: InvolvementType
    cashflow_type: CashflowType
    reason: CashflowReason
    amount: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.amount.is_nan():
            object.__setattr__(self, "amount", s_decimal_NaN)
        elif self.amount < s_decimal_0:
            raise ValueError("Amount must be positive or Inf/NaN")

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
        if self.amount.is_nan():
            return s_decimal_NaN

        if self.is_outflow:
            return -self.amount
        return self.amount


class MinimalOrderDetails(BaseModel):
    """Minimal order details for simulation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trading_pair: TradingPair = Field(description="The pair being traded")
    trading_rule: TradingRule = Field(description="Rules governing the trade")
    platform: Platform = Field(description="Trading platform")
    trade_type: TradeType = Field(description="Type of trade (buy/sell)")
    order_type: OrderType = Field(description="Type of order (market/limit/etc)")
    position_action: PositionAction = Field(
        description="Opening/closing action",
    )

    def split_order_details(self) -> list[Self]:
        """Split the order details into multiple orders if needed.

        This method is used to split the order details into multiple orders if
        the position action is FLIP.
        """
        if self.position_action != PositionAction.FLIP:
            return [self]

        fields = dict(self)
        close_fields = {**fields, "position_action": PositionAction.CLOSE}
        open_fields = {**fields, "position_action": PositionAction.OPEN}
        return [
            type(self).model_construct(**close_fields),
            type(self).model_construct(**open_fields),
        ]


class OrderDetails(MinimalOrderDetails):
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

    model_config = ConfigDict(frozen=True)

    trading_pair: TradingPair = Field(description="The pair being traded")
    trading_rule: TradingRule = Field(description="Rules governing the trade")
    platform: Platform = Field(description="Trading platform")
    trade_type: TradeType = Field(description="Type of trade (buy/sell)")
    order_type: OrderType = Field(description="Type of order (market/limit/etc)")
    order_modifiers: set[OrderModifier] = Field(
        default_factory=set,
        description="Additional order specifications",
    )
    amount: Decimal = Field(description="Order size", allow_inf_nan=True)
    price: Decimal = Field(description="Order price")
    index_price: Decimal | None = Field(
        default=None,
        description="Current index price",
    )
    leverage: int = Field(default=1, description="Leverage multiplier")
    position_action: PositionAction = Field(
        description="Opening/closing action",
        default=PositionAction.NIL,
    )
    current_position: Position | None = Field(
        default=None,
        description="Current position",
    )
    other_positions: list[Position] = Field(
        default_factory=list,
        description="Other positions useful for cross margin calculations",
    )
    fee: OperationFee = Field(description="Fee structure for the order")

    @field_validator("amount", mode="before")
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate the amount of the asset."""
        if value.is_nan():
            return s_decimal_NaN
        if value < s_decimal_0:
            raise ValueError("Amount must be positive or Inf/NaN")
        return value

    def model_post_init(self, __context: Any) -> None:
        """Validate order details after initialization."""
        super().model_post_init(__context)

        # Validate derivative trading constraints
        if self.trading_pair.market_info.is_derivative:
            self.check_derivative_trading_constraints()
        elif self.trading_pair.market_info.is_spot:
            self.check_spot_trading_constraints()

    def check_spot_trading_constraints(self) -> None:
        """Check spot trading constraints."""
        if self.leverage != 1:
            raise ValueError("Leverage must be 1 for spot trading")
        if self.position_action != PositionAction.NIL:
            raise ValueError("Position action must be NIL for spot trading")
        if any(
            field is not None
            for field in [
                self.index_price,
                self.current_position,
            ]
        ):
            raise ValueError("Index price and position must be None for spot trading")

    def check_derivative_trading_constraints(self) -> None:
        """Check derivative trading constraints."""
        if self.position_action == PositionAction.NIL:
            raise ValueError("Position action must be provided for derivative trading")
        self.check_position_action_consistency()

    def check_position_action_consistency(self) -> None:
        """Check position action consistency."""
        if self.position_action == PositionAction.OPEN:
            self._check_open_consistency()
        elif self.position_action == PositionAction.CLOSE:
            self._check_close_consistency()
        elif self.position_action == PositionAction.FLIP:
            self._check_flip_consistency()

    def _check_open_consistency(self) -> None:
        if (
            self.current_position is not None
            and self.current_position.position_side
            != self.trade_type.to_position_side()
        ):
            raise ValueError(
                "Current position side must match trade type for opening a new position"
            )

    def _check_close_consistency(self) -> None:
        if self.current_position is None:
            raise ValueError("Current position must be provided for closing")
        if self.current_position.position_side == self.trade_type.to_position_side():
            raise ValueError(
                "Current position side must not match trade type for closing"
            )
        if self.amount > self.current_position.amount:
            raise ValueError(
                "Order amount must be less than or equal to current position amount for closing, otherwise it would be a flip"
            )

    def _check_flip_consistency(self) -> None:
        if self.current_position is None:
            raise ValueError("Current position must be provided for flipping")
        if self.current_position.position_side == self.trade_type.to_position_side():
            raise ValueError(
                "Current position side must not match trade type for flipping"
            )
        if self.amount <= self.current_position.amount:
            raise ValueError(
                "Order amount must be greater than current position amount for flipping"
            )

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
        if not self.order_modifiers.issubset(
            self.trading_rule.supported_order_modifiers
        ):
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

    def split_order_details(self) -> list[Self]:
        if self.position_action != PositionAction.FLIP:
            return [self]

        fields = dict(self)
        close_order = type(self).model_construct(
            **{
                **fields,
                "amount": cast(Position, self.current_position).amount,
                "position_action": PositionAction.CLOSE,
            }
        )
        open_order = type(self).model_construct(
            **{
                **fields,
                "amount": self.amount - cast(Position, self.current_position).amount,
                "position_action": PositionAction.OPEN,
                "current_position": None,
            }
        )
        return [close_order, open_order]


class StakingOrderDetails(BaseModel):
    """Details for a staking operation simulation.

    Attributes:
        platform: Trading platform
        staked_asset: The asset being staked
        reward_asset: The asset in which rewards are paid
        amount: Amount being staked
        reward_rate: Annual reward rate (percentage, APY)
        lock_period: Lock period in seconds (0 for no lock)
        position_action: Opening or closing the staking position
        current_position: Current position (required for closing)
        fee: Fee structure for the operation
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    platform: Platform = Field(description="Trading platform")
    staked_asset: Asset = Field(description="The asset being staked")
    reward_asset: Asset = Field(description="The asset in which rewards are paid")
    amount: Decimal = Field(description="Amount being staked")
    reward_rate: Decimal = Field(description="Annual reward rate (percentage, APY)")
    lock_period: int = Field(
        default=0, description="Lock period in seconds (0 for no lock)"
    )
    position_action: PositionAction = Field(
        description="Opening or closing the position"
    )
    current_position: Position | None = Field(
        default=None,
        description="Current position (required for closing)",
    )
    fee: OperationFee = Field(description="Fee structure for the operation")


class BorrowOrderDetails(BaseModel):
    """Details for a borrowing/lending operation simulation.

    Attributes:
        platform: Trading platform
        borrowed_asset: The asset being borrowed
        collateral_asset: The asset used as collateral
        amount: Amount being borrowed
        collateral_amount: Amount of collateral deposited
        interest_rate: Annual interest rate (percentage)
        position_action: Opening or closing the borrow position
        current_position: Current position (required for closing)
        fee: Fee structure for the operation
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    platform: Platform = Field(description="Trading platform")
    borrowed_asset: Asset = Field(description="The asset being borrowed")
    collateral_asset: Asset = Field(description="The asset used as collateral")
    amount: Decimal = Field(description="Amount being borrowed")
    collateral_amount: Decimal = Field(description="Amount of collateral deposited")
    interest_rate: Decimal = Field(description="Annual interest rate (percentage)")
    position_action: PositionAction = Field(
        description="Opening or closing the position"
    )
    current_position: Position | None = Field(
        default=None,
        description="Current position (required for closing)",
    )
    fee: OperationFee = Field(description="Fee structure for the operation")


class FundingOrderDetails(BaseModel):
    """Details for a funding rate payment simulation.

    Attributes:
        platform: Trading platform
        position_asset: The perpetual asset (e.g., BTC-PERP)
        settlement_asset: The asset used for settlement (e.g., USDT)
        position_size: Size of the position
        funding_rate: Current funding rate (percentage)
        payment_period: Funding payment period in seconds
        position_side: Side of the position (LONG/SHORT)
        fee: Fee structure for the operation
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    platform: Platform = Field(description="Trading platform")
    position_asset: Asset = Field(description="The perpetual asset")
    settlement_asset: Asset = Field(description="The asset used for settlement")
    position_size: Decimal = Field(description="Size of the position")
    funding_rate: Decimal = Field(description="Current funding rate (percentage)")
    payment_period: int = Field(description="Funding payment period in seconds")
    position_side: str = Field(description="Side of the position (LONG/SHORT)")
    fee: OperationFee = Field(description="Fee structure for the operation")


@dataclass
class OperationSimulationResult:
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

    operation_details: Any
    cashflows: list[AssetCashflow]

    @functools.cached_property
    def opening_cashflow(self) -> dict[Asset, Decimal]:
        """Net cashflow at position opening for each asset."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if cashflow.involvement_type != InvolvementType.OPENING:
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows

    @functools.cached_property
    def opening_outflows(self) -> dict[Asset, Decimal]:
        """Assets leaving the account at position opening."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if (
                cashflow.involvement_type != InvolvementType.OPENING
                or not cashflow.is_outflow
            ):
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows

    @functools.cached_property
    def opening_inflows(self) -> dict[Asset, Decimal]:
        """Assets entering the account at position opening."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if (
                cashflow.involvement_type != InvolvementType.OPENING
                or not cashflow.is_inflow
            ):
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows

    @functools.cached_property
    def closing_cashflow(self) -> dict[Asset, Decimal]:
        """Net cashflow at position closing for each asset."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if cashflow.involvement_type != InvolvementType.CLOSING:
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows

    @functools.cached_property
    def closing_outflows(self) -> dict[Asset, Decimal]:
        """Assets leaving the account at position closing."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if (
                cashflow.involvement_type != InvolvementType.CLOSING
                or not cashflow.is_outflow
            ):
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows

    @functools.cached_property
    def closing_inflows(self) -> dict[Asset, Decimal]:
        """Assets entering the account at position closing."""
        cashflows: dict[Asset, Decimal] = {}
        for cashflow in self.cashflows:
            if (
                cashflow.involvement_type != InvolvementType.CLOSING
                or not cashflow.is_inflow
            ):
                continue
            cashflows[cashflow.asset] = (
                cashflows.get(cashflow.asset, s_decimal_0) + cashflow.cashflow_amount
            )
        return cashflows
