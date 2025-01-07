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
    OPERATION = "operation"
    FEE = "fee"
    PNL = "pnl"


class InvolvementType(Enum):
    OPENING = "opening"
    CLOSING = "closing"


class CashflowType(Enum):
    OUTFLOW = "outflow"
    INFLOW = "inflow"


class AssetCashflow(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    asset: Asset
    involvement_type: InvolvementType
    cashflow_type: CashflowType
    reason: CashflowReason
    amount: Decimal = Field(default=Decimal(0), ge=0)

    @property
    def is_outflow(self) -> bool:
        return self.cashflow_type == CashflowType.OUTFLOW

    @property
    def is_inflow(self) -> bool:
        return self.cashflow_type == CashflowType.INFLOW

    @property
    def cashflow_amount(self) -> Decimal:
        if self.is_outflow:
            return -self.amount
        return self.amount


class OrderDetails(BaseModel):
    trading_pair: TradingPair
    trading_rule: TradingRule
    platform: Platform
    trade_type: TradeType
    order_type: OrderType
    order_modifiers: set[OrderModifier] = Field(default_factory=set)
    amount: Decimal = Field(ge=0)
    price: Decimal
    leverage: int
    position_action: PositionAction
    index_price: Decimal
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    fee: OperationFee

    def check_potential_failure(self, current_timestamp: float | None = None) -> None:
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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    operation_details: Any
    cashflows: list[AssetCashflow]

    @property
    def opening_cashflow(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
        }

    @property
    def opening_outflows(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
        }

    @property
    def opening_inflows(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.OPENING
        }

    @property
    def closing_cashflow(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
        }

    @property
    def closing_outflows(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
        }

    @property
    def closing_inflows(self) -> dict[Asset, Decimal]:
        return {
            cashflow.asset: cashflow.cashflow_amount
            for cashflow in self.cashflows
            if cashflow.involvement_type == InvolvementType.CLOSING
        }
