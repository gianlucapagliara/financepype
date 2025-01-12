from eventspype.pub.publication import EventPublication

from financepype.operations.transactions.events import (
    BlockchainTransactionEvent,
    TransactionBroadcastedEvent,
    TransactionCancelledEvent,
    TransactionConfirmedEvent,
    TransactionEvent,
    TransactionFailedEvent,
    TransactionFinalizedEvent,
    TransactionPublications,
    TransactionRejectedEvent,
)


def test_blockchain_transaction_event_values():
    """Test that BlockchainTransactionEvent enum has correct values."""
    assert BlockchainTransactionEvent.TransactionRejected.value == 901
    assert BlockchainTransactionEvent.TransactionBroadcasted.value == 902
    assert BlockchainTransactionEvent.TransactionConfirmed.value == 903
    assert BlockchainTransactionEvent.TransactionFinalized.value == 904
    assert BlockchainTransactionEvent.TransactionFailed.value == 905
    assert BlockchainTransactionEvent.TransactionCancelled.value == 906


def test_transaction_event_base():
    """Test the base TransactionEvent class."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_broadcasted_event():
    """Test TransactionBroadcastedEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionBroadcastedEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_confirmed_event():
    """Test TransactionConfirmedEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionConfirmedEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_finalized_event():
    """Test TransactionFinalizedEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionFinalizedEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_failed_event():
    """Test TransactionFailedEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionFailedEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_rejected_event():
    """Test TransactionRejectedEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionRejectedEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_cancelled_event():
    """Test TransactionCancelledEvent creation."""
    timestamp = 1234567890.0
    client_operation_id = "test_operation_id"
    event = TransactionCancelledEvent(
        timestamp=timestamp, client_operation_id=client_operation_id
    )

    assert isinstance(event, TransactionEvent)
    assert event.timestamp == timestamp
    assert event.client_operation_id == client_operation_id


def test_transaction_publications():
    """Test TransactionPublications class and its event publications."""
    # Test that all publications are instances of EventPublication
    assert isinstance(TransactionPublications.broadcasted_publication, EventPublication)
    assert isinstance(TransactionPublications.confirmed_publication, EventPublication)
    assert isinstance(TransactionPublications.finalized_publication, EventPublication)
    assert isinstance(TransactionPublications.failed_publication, EventPublication)
    assert isinstance(TransactionPublications.rejected_publication, EventPublication)
    assert isinstance(TransactionPublications.cancelled_publication, EventPublication)

    # Test that publications are correctly mapped to event classes
    assert (
        TransactionPublications.broadcasted_publication.event_class
        == TransactionBroadcastedEvent
    )
    assert (
        TransactionPublications.confirmed_publication.event_class
        == TransactionConfirmedEvent
    )
    assert (
        TransactionPublications.finalized_publication.event_class
        == TransactionFinalizedEvent
    )
    assert (
        TransactionPublications.failed_publication.event_class == TransactionFailedEvent
    )
    assert (
        TransactionPublications.rejected_publication.event_class
        == TransactionRejectedEvent
    )
    assert (
        TransactionPublications.cancelled_publication.event_class
        == TransactionCancelledEvent
    )
