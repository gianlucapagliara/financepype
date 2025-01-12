from collections.abc import Callable
from unittest.mock import Mock, patch

import pytest
from eventspype.pub.multipublisher import MultiPublisher

from financepype.assets.blockchain import BlockchainIdentifier
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
from financepype.operations.transactions.tracker import BlockchainTransactionTracker
from financepype.operations.transactions.transaction import BlockchainTransaction

pytestmark = pytest.mark.asyncio


class MockBlockchainIdentifier(BlockchainIdentifier):
    """Mock implementation of BlockchainIdentifier for testing."""

    @classmethod
    def id_from_string(cls, string: str) -> bytes:
        """Convert string to bytes."""
        return string.encode()

    @classmethod
    def id_to_string(cls, raw: bytes) -> str:
        """Convert bytes to string."""
        return raw.decode()

    @classmethod
    def is_valid(cls, raw: bytes) -> bool:
        """Always return True for testing."""
        return True


@pytest.fixture
def mock_transaction():
    transaction = Mock(spec=BlockchainTransaction)
    transaction.client_operation_id = "test_client_id"
    transaction.client_transaction_id = "test_client_id"
    transaction.transaction_id = MockBlockchainIdentifier(
        string="test_tx_id", raw=b"test_tx_id"
    )
    transaction.current_state = BlockchainTransactionState.PENDING_BROADCAST

    # Mock property getters
    type(transaction).is_closed = property(
        lambda self: self.current_state
        in [
            BlockchainTransactionState.CONFIRMED,
            BlockchainTransactionState.FINALIZED,
            BlockchainTransactionState.FAILED,
            BlockchainTransactionState.REJECTED,
            BlockchainTransactionState.CANCELLED,
        ]
    )
    type(transaction).is_completed = property(
        lambda self: self.current_state == BlockchainTransactionState.CONFIRMED
    )
    type(transaction).is_finalized = property(
        lambda self: self.current_state == BlockchainTransactionState.FINALIZED
    )
    type(transaction).is_cancelled = property(
        lambda self: self.current_state == BlockchainTransactionState.CANCELLED
    )
    type(transaction).is_failure = property(
        lambda self: self.current_state
        in [
            BlockchainTransactionState.FAILED,
            BlockchainTransactionState.REJECTED,
        ]
    )

    # Add specific state checkers
    type(transaction).is_rejected = property(
        lambda self: self.current_state == BlockchainTransactionState.REJECTED
    )
    type(transaction).is_failed = property(
        lambda self: self.current_state == BlockchainTransactionState.FAILED
    )

    return transaction


@pytest.fixture
def event_publishers():
    class MockPublisher(MultiPublisher):
        broadcasted_publication = TransactionPublications.broadcasted_publication
        confirmed_publication = TransactionPublications.confirmed_publication
        finalized_publication = TransactionPublications.finalized_publication
        failed_publication = TransactionPublications.failed_publication
        rejected_publication = TransactionPublications.rejected_publication
        cancelled_publication = TransactionPublications.cancelled_publication

    return [MockPublisher()]


@pytest.fixture
def tracker(event_publishers):
    return BlockchainTransactionTracker(event_publishers=event_publishers)


@pytest.fixture
def current_timestamp():
    return 1000.0


@pytest.fixture
def timestamp_function(current_timestamp):
    return lambda: current_timestamp


async def test_process_transaction_update_untracked_transaction(
    tracker: BlockchainTransactionTracker, timestamp_function: Callable[[], float]
) -> None:
    """Test processing an update for an untracked transaction."""
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id="unknown_id",
        transaction_id=MockBlockchainIdentifier(string="unknown_tx", raw=b"unknown_tx"),
        new_state=BlockchainTransactionState.BROADCASTED,
    )

    tracker.process_transaction_update(update, timestamp_function)
    # Should log debug message and not raise any errors


async def test_process_transaction_update_broadcast_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that broadcast event is triggered when transaction is broadcasted."""
    tracker.start_tracking_operation(mock_transaction)
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.BROADCASTED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionBroadcastedEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_confirmed_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that confirmed event is triggered when transaction is confirmed."""
    tracker.start_tracking_operation(mock_transaction)
    mock_transaction.current_state = BlockchainTransactionState.CONFIRMED
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.CONFIRMED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionConfirmedEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_finalized_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that finalized event is triggered when transaction is finalized."""
    tracker.start_tracking_operation(mock_transaction)
    mock_transaction.current_state = BlockchainTransactionState.FINALIZED
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.FINALIZED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionFinalizedEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_failed_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that failed event is triggered when transaction fails."""
    tracker.start_tracking_operation(mock_transaction)
    mock_transaction.current_state = BlockchainTransactionState.FAILED
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.FAILED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionFailedEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_rejected_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that rejected event is triggered when transaction is rejected."""
    tracker.start_tracking_operation(mock_transaction)
    mock_transaction.current_state = BlockchainTransactionState.REJECTED
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.REJECTED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionRejectedEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_cancelled_event(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that cancelled event is triggered when transaction is cancelled."""
    tracker.start_tracking_operation(mock_transaction)
    mock_transaction.current_state = BlockchainTransactionState.CANCELLED
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.CANCELLED,
    )

    with patch.object(tracker, "trigger_event") as mock_trigger:
        tracker.process_transaction_update(update, timestamp_function)

        mock_trigger.assert_called_once()
        event = mock_trigger.call_args[0][1]
        assert isinstance(event, TransactionCancelledEvent)
        assert event.client_operation_id == mock_transaction.client_transaction_id


async def test_process_transaction_update_lost_operation_cleanup(
    tracker: BlockchainTransactionTracker,
    mock_transaction: BlockchainTransaction,
    timestamp_function: Callable[[], float],
) -> None:
    """Test that lost operations are cleaned up when they reach a final state."""
    tracker._lost_operations[mock_transaction.client_transaction_id] = mock_transaction
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=mock_transaction.client_transaction_id,
        transaction_id=mock_transaction.transaction_id,
        new_state=BlockchainTransactionState.FINALIZED,
    )

    tracker.process_transaction_update(update, timestamp_function)
    assert mock_transaction.client_transaction_id not in tracker._lost_operations
