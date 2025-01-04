import asyncio
import math
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import deprecated

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0
from financepype.markets.market import MarketInfo
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import OperationFee
from financepype.operations.operation import Operation
from financepype.operations.orders.models import (
    OrderModifier,
    OrderType,
    PositionAction,
    TradeType,
)

GET_EX_ORDER_ID_TIMEOUT = 10  # seconds


class OrderState(Enum):
    PENDING_CREATE = 0  # Initial state -> waiting for exchange to create order (order not yet in order book)
    OPEN = 1  # Ready to be filled
    PENDING_CANCEL = 2  # User requested cancellation of order -> waiting for confirmation from exchange
    CANCELED = 3  # Order was cancelled by user
    PARTIALLY_FILLED = 4  # Order partially filled -> still open
    FILLED = 5  # Order completely filled -> completed
    FAILED = 6  # Order failed to be created by the exchange


class OrderUpdate(BaseModel):
    """A class representing an update to an order's state.

    This class contains information about changes to an order's state,
    including new state, timestamps, and identifiers.
    """

    trading_pair: str
    update_timestamp: float  # seconds
    new_state: OrderState
    client_order_id: str | None = None
    exchange_order_id: str | None = None
    misc_updates: dict[str, Any] | None = None


class TradeUpdate(BaseModel):
    """A class representing a trade update for an order.

    This class contains information about a trade that has occurred,
    including fill details, prices, amounts, and fees.
    """

    trade_id: str
    client_order_id: str
    exchange_order_id: str
    trading_pair: TradingPair
    trade_type: TradeType
    fill_timestamp: float  # seconds
    fill_price: Decimal
    fill_base_amount: Decimal
    fill_quote_amount: Decimal
    fee: OperationFee
    group_order_id: str = ""

    @property
    def group_client_order_id(self) -> str | None:
        return (
            f"{self.group_order_id}{self.client_order_id}"
            if self.client_order_id is not None and self.group_order_id is not None
            else None
        )

    @property
    def fee_asset(self) -> Asset:  # Type depends on the asset implementation
        return self.fee.asset

    @property
    def instrument_info(self) -> MarketInfo:
        return self.trading_pair.instrument_info


class OrderOperation(Operation):
    """A class representing a trading order operation.

    This class extends the base Operation class to handle trading order-specific
    functionality, including order state management, trade updates, and fills tracking.
    """

    trading_pair: TradingPair
    order_type: OrderType
    trade_type: TradeType
    amount: Decimal
    price: Decimal | None = None
    modifiers: set[OrderModifier] = Field(default_factory=set)
    group_order_id: str = ""
    leverage: int = 1
    index_price: Decimal | None = None
    position: PositionAction = PositionAction.NIL
    executed_amount_base: Decimal = Field(default=s_decimal_0)
    executed_amount_quote: Decimal = Field(default=s_decimal_0)
    order_fills: dict[str, TradeUpdate] = Field(default_factory=dict)

    completely_filled_event: asyncio.Event = Field(
        default_factory=asyncio.Event,
        exclude=True,
    )

    def model_post_init(self, __context: Any) -> None:
        """Initialize non-Pydantic attributes after model initialization."""
        super().model_post_init(__context)

        if self.trade_type == TradeType.RANGE:
            raise ValueError("TradeType.RANGE is not supported")

        if self.index_price is None:
            self.index_price = self.price

        if self.current_state is None:
            self.current_state = OrderState.PENDING_CREATE

    # === Properties ===

    @property
    def attributes(self) -> tuple[str, ...]:
        return (self.client_operation_id,)

    @property
    @deprecated("Operations: Use client_operation_id instead")
    def client_order_id(self) -> str:
        return self.client_operation_id

    @property
    def exchange_order_id(self) -> str | None:
        return self.operator_operation_id

    @property
    def exchange_order_id_update_event(self) -> asyncio.Event:
        return self.operator_operation_id_update_event

    @property
    def group_client_order_id(self) -> str:
        return f"{self.group_order_id}{self.client_operation_id}"

    @property
    def filled_amount(self) -> Decimal:
        return self.executed_amount_base

    @property
    def remaining_amount(self) -> Decimal:
        return self.amount - self.executed_amount_base

    @property
    def base_asset(self) -> Any:  # Type depends on the asset implementation
        return self.trading_pair.base

    @property
    def quote_asset(self) -> Any:  # Type depends on the asset implementation
        return self.trading_pair.quote

    @property
    def is_limit(self) -> bool:
        return self.order_type.is_limit_type()

    @property
    def is_market(self) -> bool:
        return self.order_type == OrderType.MARKET

    @property
    def is_buy(self) -> bool:
        return self.trade_type == TradeType.BUY

    @property
    def average_executed_price(self) -> Decimal | None:
        executed_value: Decimal = s_decimal_0
        total_base_amount: Decimal = s_decimal_0
        for order_fill in self.order_fills.values():
            executed_value += order_fill.fill_price * order_fill.fill_base_amount
            total_base_amount += order_fill.fill_base_amount
        if executed_value == s_decimal_0 or total_base_amount == s_decimal_0:
            return None
        return executed_value / total_base_amount

    @property
    def instrument_info(self) -> MarketInfo:
        return self.trading_pair.instrument_info

    # === Status Properties ===

    @property
    def is_pending_create(self) -> bool:
        return self.current_state == OrderState.PENDING_CREATE

    @property
    def is_pending_cancel_confirmation(self) -> bool:
        return self.current_state == OrderState.PENDING_CANCEL

    @property
    def is_open(self) -> bool:
        return self.current_state in {
            OrderState.PENDING_CREATE,
            OrderState.OPEN,
            OrderState.PARTIALLY_FILLED,
            OrderState.PENDING_CANCEL,
        }

    @property
    def is_done(self) -> bool:
        return (
            self.current_state
            in {OrderState.CANCELED, OrderState.FILLED, OrderState.FAILED}
            or math.isclose(self.executed_amount_base, self.amount)
            or self.executed_amount_base >= self.amount
        )

    @property
    def is_filled(self) -> bool:
        return self.current_state == OrderState.FILLED or (
            self.amount != s_decimal_0
            and (
                math.isclose(self.executed_amount_base, self.amount)
                or self.executed_amount_base >= self.amount
            )
        )

    @property
    def is_failure(self) -> bool:
        return self.current_state == OrderState.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self.current_state == OrderState.CANCELED

    # === Updating ===

    def process_operation_update(self, update: OrderUpdate | TradeUpdate) -> bool:
        """Process an update to the order's state or trade information."""
        if isinstance(update, OrderUpdate):
            return self._update_with_order_update(update)
        elif isinstance(update, TradeUpdate):
            return self._update_with_trade_update(update)
        return False

    def _update_with_order_update(self, order_update: OrderUpdate) -> bool:
        """Update the in flight order with an order update (from REST API or WS API)."""
        if (
            order_update.client_order_id != self.client_operation_id
            and order_update.exchange_order_id != self.operator_operation_id
        ):
            return False

        prev_state = self.current_state

        if (
            self.operator_operation_id is None
            and order_update.exchange_order_id is not None
        ):
            self.update_operator_operation_id(order_update.exchange_order_id)

        if self.is_open:
            self.current_state = order_update.new_state

        updated = prev_state != self.current_state
        if updated:
            self.last_update_timestamp = order_update.update_timestamp

        return updated

    def _update_with_trade_update(self, trade_update: TradeUpdate) -> bool:
        """Update the in flight order with a trade update (from REST API or WS API)."""
        trade_id: str = trade_update.trade_id

        if trade_id in self.order_fills or (
            self.client_operation_id != trade_update.client_order_id
            and self.operator_operation_id != trade_update.exchange_order_id
        ):
            return False

        self.order_fills[trade_id] = trade_update

        self.executed_amount_base += trade_update.fill_base_amount
        self.executed_amount_quote += trade_update.fill_quote_amount

        self.last_update_timestamp = trade_update.fill_timestamp

        # Update state based on fill amount
        if (
            math.isclose(self.executed_amount_base, self.amount)
            or self.executed_amount_base >= self.amount
        ):
            self.current_state = OrderState.FILLED
        elif self.executed_amount_base > 0:
            self.current_state = OrderState.PARTIALLY_FILLED

        self.check_filled_condition()

        return True

    @deprecated("Operations: Use update_operator_operation_id instead")
    def update_exchange_order_id(self, exchange_order_id: str) -> None:
        self.update_operator_operation_id(exchange_order_id)

    @deprecated("Operations: Use process_operation_update instead")
    def update_with_order_update(self, order_update: OrderUpdate) -> bool:
        return self.process_operation_update(order_update)

    @deprecated("Operations: Use process_operation_update instead")
    def update_with_trade_update(self, trade_update: TradeUpdate) -> bool:
        return self.process_operation_update(trade_update)

    def check_filled_condition(self) -> None:
        if (abs(self.amount) - self.executed_amount_base).quantize(
            Decimal("1e-8")
        ) <= 0:
            self.completely_filled_event.set()

    async def wait_until_completely_filled(self) -> None:
        await self.completely_filled_event.wait()

    # === Other ===

    async def get_exchange_order_id(self) -> str | None:
        if self.operator_operation_id is None:
            async with asyncio.timeout(GET_EX_ORDER_ID_TIMEOUT):
                await self.operator_operation_id_update_event.wait()
        return self.operator_operation_id

    def build_order_created_message(self) -> str:
        if self.instrument_info.instrument_type.is_spot:
            message = (
                f"Created {self.order_type.name.upper()} {self.trade_type.name.upper()} order "
                f"{self.client_operation_id} for {self.amount} {self.trading_pair}."
            )
        else:
            message = (
                f"Created {self.order_type.name.upper()} {self.trade_type.name.upper()} order "
                f"{self.client_operation_id} for {self.amount} to {self.position.name.upper()} a {self.trading_pair} position."
            )
        return message
