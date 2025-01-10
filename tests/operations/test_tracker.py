import time
from typing import Any
from unittest.mock import Mock

import pytest
from eventspype.pub.multipublisher import MultiPublisher
from eventspype.pub.publication import EventPublication

from financepype.operations.operation import Operation
from financepype.operations.tracker import OperationTracker
from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.platform import Platform


class MockEvent:
    """A mock event class for testing."""

    pass


class MockOperation(Operation):
    """A simple operation implementation for testing."""

    def __init__(self, client_operation_id: str):
        current_time = time.time()
        super().__init__(
            client_operation_id=client_operation_id,
            owner_identifier=OwnerIdentifier(
                name="test_owner", platform=Platform(identifier="test")
            ),
            creation_timestamp=current_time,
            current_state=None,
        )

    def process_operation_update(self, update: Any) -> bool:
        """Process an update to the operation's state."""
        self.current_state = update
        return True


@pytest.fixture
def mock_publisher() -> MultiPublisher:
    publisher = Mock(spec=MultiPublisher)
    return publisher


@pytest.fixture
def tracker(mock_publisher: MultiPublisher) -> OperationTracker:
    return OperationTracker(event_publishers=[mock_publisher])


def test_tracker_initialization(tracker: OperationTracker) -> None:
    """Test that a tracker is properly initialized."""
    assert len(tracker.active_operations) == 0
    assert len(tracker.cached_operations) == 0
    assert len(tracker.lost_operations) == 0
    assert len(tracker.all_updatable_operations) == 0
    assert len(tracker.all_operations) == 0


def test_start_tracking_operation(tracker: OperationTracker) -> None:
    """Test starting to track an operation."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)

    assert len(tracker.active_operations) == 1
    assert tracker.active_operations["test_op"] == operation
    assert len(tracker.cached_operations) == 0
    assert len(tracker.lost_operations) == 0


def test_stop_tracking_operation(tracker: OperationTracker) -> None:
    """Test stopping tracking an operation."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)
    tracker.stop_tracking_operation("test_op")

    assert len(tracker.active_operations) == 0
    assert len(tracker.cached_operations) == 1
    assert tracker.cached_operations["test_op"] == operation
    assert len(tracker.lost_operations) == 0


def test_fetch_operation_by_client_id(tracker: OperationTracker) -> None:
    """Test fetching an operation by client ID."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)

    found = tracker.fetch_operation(client_operation_id="test_op")
    assert found == operation

    not_found = tracker.fetch_operation(client_operation_id="nonexistent")
    assert not_found is None


def test_fetch_operation_by_operator_id(tracker: OperationTracker) -> None:
    """Test fetching an operation by operator ID."""
    operation = MockOperation(client_operation_id="test_op")
    operation.update_operator_operation_id("op_123")
    tracker.start_tracking_operation(operation)

    found = tracker.fetch_operation(operator_operation_id="op_123")
    assert found == operation

    not_found = tracker.fetch_operation(operator_operation_id="nonexistent")
    assert not_found is None


def test_fetch_operation_requires_id(tracker: OperationTracker) -> None:
    """Test that fetching an operation requires at least one ID."""
    with pytest.raises(
        ValueError,
        match="At least one of client_operation_id or operator_operation_id must be provided",
    ):
        tracker.fetch_operation()


def test_fetch_tracked_operation(tracker: OperationTracker) -> None:
    """Test fetching a tracked operation."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)

    found = tracker.fetch_tracked_operation(client_operation_id="test_op")
    assert found == operation

    # After stopping tracking, it should not be found
    tracker.stop_tracking_operation("test_op")
    not_found = tracker.fetch_tracked_operation(client_operation_id="test_op")
    assert not_found is None


def test_fetch_cached_operation(tracker: OperationTracker) -> None:
    """Test fetching a cached operation."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)
    tracker.stop_tracking_operation("test_op")

    found = tracker.fetch_cached_operation(client_operation_id="test_op")
    assert found == operation


def test_fetch_updatable_operation(tracker: OperationTracker) -> None:
    """Test fetching an updatable operation."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)

    found = tracker.fetch_updatable_operation(client_operation_id="test_op")
    assert found == operation

    # After stopping tracking, it should not be found in updatable operations
    tracker.stop_tracking_operation("test_op")
    not_found = tracker.fetch_updatable_operation(client_operation_id="test_op")
    assert not_found is None


def test_update_operator_operation_id(tracker: OperationTracker) -> None:
    """Test updating an operation's operator ID."""
    operation = MockOperation(client_operation_id="test_op")
    tracker.start_tracking_operation(operation)

    updated = tracker.update_operator_operation_id("test_op", "op_123")
    assert updated == operation
    assert operation.operator_operation_id == "op_123"

    # Trying to update a non-existent operation should return None
    not_updated = tracker.update_operator_operation_id("nonexistent", "op_456")
    assert not_updated is None


def test_trigger_event(
    tracker: OperationTracker, mock_publisher: MultiPublisher
) -> None:
    """Test triggering an event."""
    event_publication = EventPublication("test_event", event_class=MockEvent)
    event = {"data": "test"}

    tracker.trigger_event(event_publication, event)

    mock_publisher.trigger_event.assert_called_once_with(event_publication, event)
