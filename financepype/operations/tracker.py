import logging
from collections import defaultdict
from typing import Any

from cachetools import TTLCache
from eventspype.pub.multipublisher import MultiPublisher
from eventspype.pub.publication import EventPublication

from financepype.operations.operation import Operation


class OperationTracker:
    """Tracks and manages the lifecycle of trading operations.

    This class provides utilities for tracking in-flight operations, caching completed
    operations, and handling operation errors. It maintains different states for
    operations and provides methods to update and query their status.

    The tracker maintains three sets of operations:
    1. Active operations: Currently in-flight and being tracked
    2. Cached operations: Recently completed operations kept for a short time
    3. Lost operations: Operations that failed or couldn't be found

    Attributes:
        MAX_CACHE_SIZE (int): Maximum number of cached operations
        CACHED_OPERATION_TTL (float): Time to live for cached operations in seconds

    Example:
        >>> tracker = OperationTracker(event_publishers=[publisher])
        >>> tracker.start_tracking_operation(operation)
        >>> tracker.update_operator_operation_id("client_id_1", "exchange_id_1")
    """

    MAX_CACHE_SIZE = 1000
    CACHED_OPERATION_TTL = 30.0  # seconds

    _logger: logging.Logger | None = None

    @classmethod
    def logger(cls) -> logging.Logger:
        """Get the logger instance for the tracker.

        Returns:
            logging.Logger: The logger instance
        """
        if cls._logger is None:
            cls._logger = logging.getLogger("exchange")
        return cls._logger

    def __init__(
        self,
        event_publishers: list[MultiPublisher],
        lost_operation_count_limit: int = 3,
    ) -> None:
        """Initialize the operation tracker.

        Args:
            event_publishers (list[MultiPublisher]): Publishers for operation events
            lost_operation_count_limit (int): Max attempts before marking as lost
        """
        super().__init__()

        self._event_publishers = event_publishers
        self._lost_operation_count_limit = lost_operation_count_limit
        self._in_flight_operations: dict[str, Operation] = {}
        self._cached_operations: TTLCache[str, Operation] = TTLCache(
            maxsize=self.MAX_CACHE_SIZE, ttl=self.CACHED_OPERATION_TTL
        )
        self._lost_operations: dict[str, Operation] = {}
        self._operation_not_found_records: dict[str, int] = defaultdict(lambda: 0)

    # === Properties ===

    @property
    def active_operations(self) -> dict[str, Operation]:
        """Get currently active operations.

        Returns:
            dict[str, Operation]: Map of client IDs to active operations
        """
        return self._in_flight_operations

    @property
    def cached_operations(self) -> dict[str, Operation]:
        """Get recently completed operations from cache.

        Returns:
            dict[str, Operation]: Map of client IDs to cached operations
        """
        return dict(self._cached_operations.items())

    @property
    def lost_operations(self) -> dict[str, Operation]:
        """Get operations marked as lost or failed.

        Returns:
            dict[str, Operation]: Map of client IDs to lost operations
        """
        return dict(self._lost_operations.items())

    @property
    def all_updatable_operations(self) -> dict[str, Operation]:
        """Get all operations that can still receive updates.

        Returns:
            dict[str, Operation]: Map of client IDs to updatable operations
        """
        return {**self.active_operations, **self.lost_operations}

    @property
    def all_operations(self) -> dict[str, Operation]:
        """Get all tracked operations across all states.

        Returns:
            dict[str, Operation]: Map of client IDs to all operations
        """
        return {
            **self.active_operations,
            **self.cached_operations,
            **self.lost_operations,
        }

    # === Tracking ===

    def start_tracking_operation(self, operation: Operation) -> None:
        """Start tracking a new operation.

        Args:
            operation (Operation): The operation to track
        """
        self._in_flight_operations[operation.client_operation_id] = operation

    def stop_tracking_operation(self, client_operation_id: str) -> None:
        """Stop tracking an operation and move it to cache.

        Args:
            client_operation_id (str): ID of the operation to stop tracking
        """
        if client_operation_id in self._in_flight_operations:
            self._cached_operations[client_operation_id] = self._in_flight_operations[
                client_operation_id
            ]
            del self._in_flight_operations[client_operation_id]

    def restore_tracking_states(self, tracking_states: dict[str, Any]) -> None:
        """Restore tracker state from saved state.

        Args:
            tracking_states (dict[str, Any]): Saved tracker state

        Raises:
            NotImplementedError: Not implemented yet
        """
        raise NotImplementedError

    # === Retrieving ===

    def fetch_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: Any | None = None,
        operations: dict[str, Operation] | None = None,
    ) -> Operation | None:
        """Fetch an operation by its client or operator ID.

        Args:
            client_operation_id (str | None): Client-assigned operation ID
            operator_operation_id (Any | None): Operator-assigned operation ID
            operations (dict[str, Operation] | None): Operations to search in

        Returns:
            Operation | None: The found operation or None

        Raises:
            ValueError: If neither ID is provided
        """
        if client_operation_id is None and operator_operation_id is None:
            raise ValueError(
                "At least one of client_operation_id or operator_operation_id must be provided"
            )

        if operations is None:
            operations = self.all_operations

        if client_operation_id is not None:
            found_order = operations.get(client_operation_id, None)
        else:
            found_order = next(
                (
                    operation
                    for operation in operations.values()
                    if operation.operator_operation_id == operator_operation_id
                ),
                None,
            )

        return found_order

    def fetch_tracked_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: Any | None = None,
    ) -> Operation | None:
        """Fetch an operation from active operations.

        Args:
            client_operation_id (str | None): Client-assigned operation ID
            operator_operation_id (Any | None): Operator-assigned operation ID

        Returns:
            Operation | None: The found operation or None
        """
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self._in_flight_operations,
        )

    def fetch_cached_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: Any | None = None,
    ) -> Operation | None:
        """Fetch an operation from cached operations.

        Args:
            client_operation_id (str | None): Client-assigned operation ID
            operator_operation_id (Any | None): Operator-assigned operation ID

        Returns:
            Operation | None: The found operation or None
        """
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self.cached_operations,
        )

    def fetch_updatable_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: Any | None = None,
    ) -> Operation | None:
        """Fetch an operation that can still receive updates.

        Args:
            client_operation_id (str | None): Client-assigned operation ID
            operator_operation_id (str | None): Operator-assigned operation ID

        Returns:
            Operation | None: The found operation or None
        """
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self.all_updatable_operations,
        )

    # === Updating ===

    def update_operator_operation_id(
        self, client_operation_id: str, operator_operation_id: Any
    ) -> Operation | None:
        """Update the operator-assigned ID for an operation.

        Args:
            client_operation_id (str): Client-assigned operation ID
            operator_operation_id (Any): New operator-assigned operation ID

        Returns:
            Operation | None: The updated operation or None if not found
        """
        operation = self.fetch_tracked_operation(client_operation_id)
        if operation:
            operation.update_operator_operation_id(operator_operation_id)
        return operation

    # === Events ===

    def trigger_event(self, event_publication: EventPublication, event: Any) -> None:
        """Trigger an event on all event publishers.

        Args:
            event_publication (EventPublication): The event publication details
            event (Any): The event data to publish
        """
        for event_publisher in self._event_publishers:
            event_publisher.trigger_event(event_publication, event)
