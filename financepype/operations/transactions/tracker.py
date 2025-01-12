from collections.abc import Callable
from typing import cast

from financepype.operations.tracker import OperationTracker
from financepype.operations.transactions.events import (
    TransactionBroadcastedEvent,
    TransactionCancelledEvent,
    TransactionConfirmedEvent,
    TransactionFailedEvent,
    TransactionFinalizedEvent,
    TransactionPublications,
    TransactionRejectedEvent,
)
from financepype.operations.transactions.models import (
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operations.transactions.transaction import BlockchainTransaction


class BlockchainTransactionTracker(OperationTracker):
    """
    Tracks and manages the lifecycle of blockchain transactions.

    This tracker monitors transaction states, processes updates, and publishes events
    for various transaction lifecycle stages. It handles transaction creation,
    confirmation, finalization, failure, and cancellation events.

    Publications:
        broadcasted_publication: Published when a transaction is broadcast to the network
        confirmed_publication: Published when a transaction is confirmed in a block
        finalized_publication: Published when a transaction reaches finality
        failed_publication: Published when a transaction fails
        rejected_publication: Published when a transaction is rejected
        cancelled_publication: Published when a transaction is cancelled
    """

    def process_transaction_update(
        self,
        operation_update: BlockchainTransactionUpdate,
        current_timestamp_function: Callable[[], float],
    ) -> None:
        """
        Processes an update to a tracked transaction's state.

        This method handles updates to transaction state, triggers appropriate events,
        and manages the tracking lifecycle of the transaction.

        Args:
            operation_update: The update containing new transaction state and information
            current_timestamp_function: Function to get the current timestamp

        Raises:
            ValueError: If the update lacks transaction identification information
        """
        tracked_operation = cast(
            BlockchainTransaction | None,
            self.fetch_updatable_operation(
                operation_update.client_transaction_id,
                operation_update.transaction_id,
            ),
        )

        if tracked_operation is not None:
            previous_state = tracked_operation.current_state

            updated = tracked_operation.process_operation_update(operation_update)
            if updated:
                self._trigger_transaction_creation(
                    tracked_operation,
                    previous_state,
                    operation_update.new_state,
                    current_timestamp=current_timestamp_function(),
                )
                self._trigger_transaction_completion(
                    tracked_operation,
                    operation_update,
                    current_timestamp=current_timestamp_function(),
                )
        else:
            self.logger().debug(
                f"Transaction is not/no longer being tracked ({operation_update})"
            )

        if (operation_update.client_transaction_id in self._lost_operations) and (
            operation_update.new_state
            in [
                BlockchainTransactionState.CONFIRMED,
                BlockchainTransactionState.FINALIZED,
                BlockchainTransactionState.FAILED,
                BlockchainTransactionState.REJECTED,
                BlockchainTransactionState.CANCELLED,
            ]
        ):
            # If the operation officially reaches a final state after being lost it should be removed from the lost list
            del self._lost_operations[operation_update.client_transaction_id]

    # === Event Triggers ===

    def _trigger_broadcasted_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction is broadcast to the network."""
        self.trigger_event(
            TransactionPublications.broadcasted_publication,
            TransactionBroadcastedEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_confirmed_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction is confirmed in a block."""
        self.trigger_event(
            TransactionPublications.confirmed_publication,
            TransactionConfirmedEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_finalized_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction reaches finality."""
        self.trigger_event(
            TransactionPublications.finalized_publication,
            TransactionFinalizedEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_failed_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction fails."""
        self.trigger_event(
            TransactionPublications.failed_publication,
            TransactionFailedEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_rejected_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction is rejected."""
        self.trigger_event(
            TransactionPublications.rejected_publication,
            TransactionRejectedEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_cancelled_event(
        self, operation: BlockchainTransaction, current_timestamp: float
    ) -> None:
        """Triggers an event when a transaction is cancelled."""
        self.trigger_event(
            TransactionPublications.cancelled_publication,
            TransactionCancelledEvent(
                timestamp=current_timestamp,
                client_operation_id=operation.client_transaction_id,
                # ...,
            ),
        )

    def _trigger_transaction_creation(
        self,
        tracked_transaction: BlockchainTransaction,
        previous_state: BlockchainTransactionState,
        new_state: BlockchainTransactionState,
        current_timestamp: float,
    ) -> None:
        """
        Handles the creation phase of a transaction.

        Triggers appropriate events when a transaction transitions from pending
        to an active state.

        Args:
            tracked_transaction: The transaction being tracked
            previous_state: The previous state of the transaction
            new_state: The new state of the transaction
            current_timestamp: Current time in Unix timestamp format
        """
        if previous_state == BlockchainTransactionState.PENDING_BROADCAST and (
            new_state
            not in [
                BlockchainTransactionState.PENDING_BROADCAST,
                BlockchainTransactionState.FAILED,
                BlockchainTransactionState.REJECTED,
                BlockchainTransactionState.CANCELLED,
            ]
        ):
            self._trigger_broadcasted_event(tracked_transaction, current_timestamp)

    def _trigger_transaction_completion(
        self,
        tracked_transaction: BlockchainTransaction,
        transaction_update: BlockchainTransactionUpdate,
        current_timestamp: float,
    ) -> None:
        """
        Handles the completion phase of a transaction.

        Triggers appropriate events based on the final state of the transaction
        (completed, finalized, failed, or cancelled).

        Args:
            tracked_transaction: The transaction being tracked
            transaction_update: The update that triggered completion
            current_timestamp: Current time in Unix timestamp format
        """
        if not tracked_transaction.is_closed:
            return

        if tracked_transaction.is_cancelled:
            self._trigger_cancelled_event(
                tracked_transaction, current_timestamp=current_timestamp
            )

        elif tracked_transaction.is_completed:
            self._trigger_confirmed_event(
                tracked_transaction, current_timestamp=current_timestamp
            )

        elif tracked_transaction.is_finalized:
            self._trigger_finalized_event(
                tracked_transaction, current_timestamp=current_timestamp
            )

        elif tracked_transaction.current_state == BlockchainTransactionState.REJECTED:
            self._trigger_rejected_event(
                tracked_transaction, current_timestamp=current_timestamp
            )

        elif tracked_transaction.current_state == BlockchainTransactionState.FAILED:
            self._trigger_failed_event(
                tracked_transaction, current_timestamp=current_timestamp
            )

        self.stop_tracking_operation(tracked_transaction.client_transaction_id)
