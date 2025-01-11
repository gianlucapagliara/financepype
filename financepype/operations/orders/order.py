import asyncio
import math
from decimal import Decimal
from typing import Any

from pydantic import Field
from typing_extensions import deprecated

from financepype.constants import s_decimal_0
from financepype.markets.trading_pair import TradingPair
from financepype.operations.operation import Operation
from financepype.operations.orders.models import (
    OrderModifier,
    OrderState,
    OrderType,
    OrderUpdate,
    PositionAction,
    TradeType,
    TradeUpdate,
)


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
    current_state: OrderState = Field(default=OrderState.PENDING_CREATE)

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
        return self.order_type == OrderType.LIMIT

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
        if order_update.client_order_id != self.client_operation_id or (
            self.operator_operation_id is not None
            and order_update.exchange_order_id != self.operator_operation_id
        ):
            return False

        prev_state = self.current_state

        if (
            self.operator_operation_id is None
            and order_update.exchange_order_id is not None
        ):
            self.update_operator_operation_id(order_update.exchange_order_id)

        # Check if the state transition is valid
        valid = self.is_valid_state_transition(order_update)
        if not valid:
            return False
        self.current_state = order_update.new_state

        updated = prev_state != self.current_state
        if updated:
            self.last_update_timestamp = order_update.update_timestamp

        return updated

    def is_valid_state_transition(self, order_update: OrderUpdate) -> bool:
        if self.is_pending_create:
            if order_update.new_state not in {OrderState.OPEN, OrderState.FAILED}:
                return False
        elif self.is_open:
            if order_update.new_state not in {
                OrderState.OPEN,
                OrderState.PENDING_CANCEL,
                OrderState.CANCELED,
                OrderState.FILLED,
            }:
                return False
        elif self.is_pending_cancel_confirmation:
            if order_update.new_state not in {
                OrderState.CANCELED,
                OrderState.OPEN,
                OrderState.FILLED,
            }:
                return False
        else:
            return False
        return True

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

    async def get_exchange_order_id(self, timeout: float = 10) -> str | None:
        if self.operator_operation_id is None:
            async with asyncio.timeout(timeout):
                await self.operator_operation_id_update_event.wait()
        return self.operator_operation_id

    def build_order_created_message(self) -> str:
        if self.trading_pair.market_info.instrument_type.is_spot:
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
