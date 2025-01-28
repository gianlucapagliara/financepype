import asyncio
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from typing_extensions import deprecated

from financepype.operations.fees import OperationFee
from financepype.operations.orders.events import (
    OrderCancelFailureEvent,
    OrderCancelledEvent,
    OrderCompletedEvent,
    OrderCreatedEvent,
    OrderFailureEvent,
    OrderFilledEvent,
    OrderPublications,
)
from financepype.operations.orders.models import OrderState, OrderUpdate, TradeUpdate
from financepype.operations.orders.order import OrderOperation
from financepype.operations.tracker import OperationTracker


class OrderTracker(OperationTracker):
    TRADE_FILLS_WAIT_TIMEOUT = 5  # seconds
    TEST_MODE = False

    # === Properties ===

    @property
    @deprecated("Trackers: Use active_operations instead")
    def active_orders(self) -> dict[str, OrderOperation]:
        return self.active_operations  # type: ignore

    @property
    @deprecated("Trackers: Use cached_operations instead")
    def cached_orders(self) -> dict[str, OrderOperation]:
        return self.cached_operations  # type: ignore

    @property
    @deprecated("Trackers: Use lost_operations instead")
    def lost_orders(self) -> dict[str, OrderOperation]:
        return self.lost_operations  # type: ignore

    @property
    @deprecated("Trackers: Use all_updatable_operations instead")
    def all_updatable_orders(self) -> dict[str, OrderOperation]:
        return self.all_updatable_operations  # type: ignore

    @property
    @deprecated("Trackers: Use all_operations instead")
    def all_fillable_orders(self) -> dict[str, OrderOperation]:
        return self.all_operations  # type: ignore

    # === Tracking ===

    def restore_tracking_states(self, tracking_states: dict[str, Any]):
        """
        Restore in-flight orders from saved tracking states.
        :param tracking_states: a dictionary associating order ids with the serialized order (JSON format).
        """
        for serialized_order in tracking_states.values():
            order = serialized_order
            if not isinstance(serialized_order, OrderOperation):
                order = OrderOperation.model_validate(serialized_order)
            if order.is_open:
                self.start_tracking_operation(order)

    # === Updating ===

    def process_order_update(
        self,
        order_update: OrderUpdate,
        current_timestamp_function: Callable[[], float],
        force_update: bool = False,
    ) -> None:
        if not order_update.client_order_id and not order_update.exchange_order_id:
            self.logger().error(
                "OrderUpdate does not contain any client_order_id or exchange_order_id",
                exc_info=True,
            )
            return

        tracked_order: OrderOperation | None = cast(
            OrderOperation | None,
            self.fetch_updatable_operation(
                order_update.client_order_id,
                order_update.exchange_order_id,
            ),
        )

        if tracked_order:
            if (
                order_update.new_state == OrderState.FILLED
                and not tracked_order.is_done
                and not force_update
            ):
                asyncio.ensure_future(
                    self._wait_fills_to_process_order_update(
                        tracked_order,
                        order_update,
                        current_timestamp_function=current_timestamp_function,
                    )
                )
                return

            previous_state: OrderState = tracked_order.current_state

            updated: bool = tracked_order.process_operation_update(order_update)
            if updated:
                self._trigger_order_creation(
                    tracked_order,
                    previous_state,
                    order_update.new_state,
                    current_timestamp=(
                        order_update.update_timestamp
                        if not self.TEST_MODE
                        else current_timestamp_function()
                    ),
                )
                self._trigger_order_completion(
                    tracked_order,
                    order_update,
                    current_timestamp=(
                        order_update.update_timestamp
                        if not self.TEST_MODE
                        else current_timestamp_function()
                    ),
                )
        else:
            self.logger().debug(
                f"Order is not/no longer being tracked ({order_update})"
            )

        if (order_update.client_order_id in self._lost_operations) and (
            order_update.new_state in [OrderState.CANCELED, OrderState.FILLED]
        ):
            # If the order officially reaches a final state after being lost it should be removed from the lost list
            del self._lost_operations[order_update.client_order_id]

        return

    async def _wait_fills_to_process_order_update(
        self,
        tracked_order: OrderOperation,
        order_update: OrderUpdate,
        current_timestamp_function: Callable[[], float],
    ):
        try:
            await asyncio.wait_for(
                tracked_order.wait_until_completely_filled(),
                timeout=self.TRADE_FILLS_WAIT_TIMEOUT,
            )
        except TimeoutError:
            self.logger().warning(
                f"The order fill updates did not arrive on time for {tracked_order.client_order_id}. "
                f"The complete update will be processed with incomplete information."
            )
        finally:
            self.process_order_update(
                order_update, current_timestamp_function, force_update=True
            )

    def process_trade_update(
        self,
        trade_update: TradeUpdate,
        current_timestamp_function: Callable[[], float],
    ):
        tracked_order: OrderOperation | None = cast(
            OrderOperation | None,
            self.fetch_operation(
                trade_update.client_order_id, trade_update.exchange_order_id
            ),
        )

        if not tracked_order:
            return

        previous_executed_amount_base: Decimal = tracked_order.executed_amount_base

        updated: bool = tracked_order.process_operation_update(trade_update)
        if updated:
            self._trigger_order_fills(
                tracked_order=tracked_order,
                prev_executed_amount_base=previous_executed_amount_base,
                fill_amount=trade_update.fill_base_amount,
                fill_price=trade_update.fill_price,
                fill_fee=trade_update.fee,
                trade_id=trade_update.trade_id,
                current_timestamp=(
                    trade_update.fill_timestamp
                    if not self.TEST_MODE
                    else current_timestamp_function()
                ),
            )

    def process_order_not_found(
        self, client_order_id: str, current_timestamp_function: Callable[[], float]
    ) -> None:
        """
        Increments and checks if the order specified has exceeded the order_not_found_count_limit.
        A failed event is triggered if necessary.

        :param client_order_id: Client order id of an order.
        :type client_order_id: str
        """
        # Only concerned with active orders.
        tracked_order: OrderOperation | None = cast(
            OrderOperation | None,
            self.fetch_tracked_operation(client_operation_id=client_order_id),
        )

        if tracked_order is None:
            self.logger().debug(
                f"Order is not/no longer being tracked ({client_order_id})"
            )
            return

        self._operation_not_found_records[client_order_id] += 1
        if (
            self._operation_not_found_records[client_order_id]
            > self._lost_operation_count_limit
        ):
            # Only mark the order as failed if it has not been marked as done already asynchronously
            if not tracked_order.is_done:
                order_update: OrderUpdate = OrderUpdate(
                    client_order_id=client_order_id,
                    trading_pair=tracked_order.trading_pair,
                    update_timestamp=current_timestamp_function(),
                    new_state=OrderState.FAILED,
                )
                self.process_order_update(
                    order_update,
                    current_timestamp_function=current_timestamp_function,
                )
                del self._cached_operations[client_order_id]
                self._lost_operations[tracked_order.client_operation_id] = tracked_order

    # === Event Triggers ===

    def _trigger_created_event(self, order: OrderOperation, current_timestamp: float):
        self.trigger_event(
            OrderPublications.created_publication,
            OrderCreatedEvent(
                timestamp=current_timestamp,
                client_operation_id=order.client_operation_id,
                order_type=order.order_type,
                trade_type=order.trade_type,
                trading_pair=order.trading_pair,
                exchange_order_id=order.exchange_order_id,
            ),
        )

    def _trigger_cancelled_event(self, order: OrderOperation, current_timestamp: float):
        self.trigger_event(
            OrderPublications.cancelled_publication,
            OrderCancelledEvent(
                timestamp=current_timestamp,
                client_operation_id=order.client_operation_id,
                order_type=order.order_type,
                trade_type=order.trade_type,
                trading_pair=order.trading_pair,
                exchange_order_id=order.exchange_order_id,
            ),
        )

    def _trigger_filled_event(
        self,
        order: OrderOperation,
        fill_amount: Decimal,
        fill_price: Decimal,
        fill_fee: OperationFee,
        trade_id: str,
        current_timestamp: float,
    ):
        self.trigger_event(
            OrderPublications.filled_publication,
            OrderFilledEvent(
                timestamp=current_timestamp,
                client_operation_id=order.client_operation_id,
                order_type=order.order_type,
                trade_type=order.trade_type,
                trading_pair=order.trading_pair,
                exchange_order_id=order.exchange_order_id,
                amount=fill_amount,
                trade_fee=fill_fee,
                exchange_trade_id=trade_id,
            ),
        )

    def _trigger_completed_event(self, order: OrderOperation, current_timestamp: float):
        self.trigger_event(
            OrderPublications.completed_publication,
            OrderCompletedEvent(
                timestamp=current_timestamp,
                client_operation_id=order.client_operation_id,
                order_type=order.order_type,
                trade_type=order.trade_type,
                trading_pair=order.trading_pair,
                exchange_order_id=order.exchange_order_id,
                base_asset=order.base_asset,
                quote_asset=order.quote_asset,
                base_asset_amount=order.executed_amount_base,
                quote_asset_amount=order.executed_amount_quote,
            ),
        )

    def _trigger_failure_event(self, order: OrderOperation, current_timestamp: float):
        self.trigger_event(
            OrderPublications.failure_publication,
            OrderFailureEvent(
                timestamp=current_timestamp,
                client_operation_id=order.client_operation_id,
                order_type=order.order_type,
                trade_type=order.trade_type,
                trading_pair=order.trading_pair,
                exchange_order_id=order.exchange_order_id,
            ),
        )

    def _trigger_order_creation(
        self,
        tracked_order: OrderOperation,
        previous_state: OrderState,
        new_state: OrderState,
        current_timestamp: float,
    ):
        if (
            previous_state == OrderState.PENDING_CREATE
            and new_state != OrderState.FAILED
        ):
            self.logger().debug(tracked_order.build_order_created_message())
            self._trigger_created_event(
                tracked_order, current_timestamp=current_timestamp
            )

    def _trigger_order_fills(
        self,
        tracked_order: OrderOperation,
        prev_executed_amount_base: Decimal,
        fill_amount: Decimal,
        fill_price: Decimal,
        fill_fee: OperationFee,
        trade_id: str,
        current_timestamp: float,
    ):
        if prev_executed_amount_base < tracked_order.executed_amount_base:
            self.logger().debug(
                f"The {tracked_order.trade_type.name.upper()} order {tracked_order.client_operation_id} "
                f"amounting to {tracked_order.executed_amount_base}/{tracked_order.amount} "
                f"{tracked_order.base_asset} has been filled."
            )
            self._trigger_filled_event(
                order=tracked_order,
                fill_amount=fill_amount,
                fill_price=fill_price,
                fill_fee=fill_fee,
                trade_id=trade_id,
                current_timestamp=current_timestamp,
            )

    def _trigger_order_completion(
        self,
        tracked_order: OrderOperation,
        order_update: OrderUpdate,
        current_timestamp: float,
    ):
        if tracked_order.is_open:
            return

        if tracked_order.is_cancelled:
            self._trigger_cancelled_event(
                tracked_order, current_timestamp=current_timestamp
            )
            self.logger().debug(
                f"Successfully canceled order {tracked_order.client_operation_id}."
            )

        elif tracked_order.is_filled:
            self._trigger_completed_event(
                tracked_order, current_timestamp=current_timestamp
            )
            self.logger().debug(
                f"{tracked_order.trade_type.name.upper()} order {tracked_order.client_operation_id} completely filled."
            )

        elif tracked_order.is_failure:
            self._trigger_failure_event(
                tracked_order, current_timestamp=current_timestamp
            )
            self.logger().debug(
                f"Order {tracked_order.client_operation_id} has failed. Order Update: {order_update}"
            )

        self.stop_tracking_operation(tracked_order.client_operation_id)

    def _trigger_order_cancel_failure_event(
        self,
        tracked_order: OrderOperation,
        current_timestamp: float,
    ):
        self.trigger_event(
            OrderPublications.cancel_failure_publication,
            OrderCancelFailureEvent(
                timestamp=current_timestamp,
                client_operation_id=tracked_order.client_operation_id,
                order_type=tracked_order.order_type,
                trade_type=tracked_order.trade_type,
                trading_pair=tracked_order.trading_pair,
                exchange_order_id=tracked_order.exchange_order_id,
            ),
        )
