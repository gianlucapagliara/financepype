from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from financepype.assets.asset import Asset
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
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
    amount: Decimal = Field(ge=0)
    price: Decimal
    leverage: int
    position_action: PositionAction
    index_price: Decimal
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    fee: OperationFee


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
