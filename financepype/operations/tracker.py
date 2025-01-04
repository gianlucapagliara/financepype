import logging
from collections import defaultdict
from typing import Any

from cachetools import TTLCache
from eventspype.pub.multipublisher import MultiPublisher
from eventspype.pub.publication import EventPublication

from financepype.operations.operation import Operation


class OperationTracker:
    MAX_CACHE_SIZE = 1000
    CACHED_OPERATION_TTL = 30.0  # seconds

    _logger: logging.Logger | None = None

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger("exchange")
        return cls._logger

    def __init__(
        self,
        event_publishers: list[MultiPublisher],
        lost_operation_count_limit: int = 3,
    ) -> None:
        """
        Provides utilities for connectors to update in-flight operations and also handle operation errors.
        Also it maintains cached operations to allow for additional updates to occur after the original one is determined to
        no longer be active.
        An error constitutes, but is not limited to, the following:
        (1) Operation not found on operator.
        (2) Cannot retrieve operator_operation_id of an operation.
        (3) Error thrown by operation when fetching operator status.
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
        """
        Returns operations that are actively tracked
        """
        return self._in_flight_operations

    @property
    def cached_operations(self) -> dict[str, Operation]:
        """
        Returns operations that are no longer actively tracked.
        """
        return dict(self._cached_operations.items())

    @property
    def lost_operations(self) -> dict[str, Operation]:
        """
        Returns a dictionary of all orders marked as failed after not being found more times than the configured limit
        """
        return dict(self._lost_operations.items())

    @property
    def all_updatable_operations(self) -> dict[str, Operation]:
        """
        Returns all operations that could receive status updates
        """
        return {**self.active_operations, **self.lost_operations}

    @property
    def all_operations(self) -> dict[str, Operation]:
        """
        Returns all operations that are currently tracked
        """
        return {
            **self.active_operations,
            **self.cached_operations,
            **self.lost_operations,
        }

    # === Tracking ===

    def start_tracking_operation(self, operation: Operation) -> None:
        self._in_flight_operations[operation.client_operation_id] = operation

    def stop_tracking_operation(self, client_operation_id: str) -> None:
        if client_operation_id in self._in_flight_operations:
            self._cached_operations[client_operation_id] = self._in_flight_operations[
                client_operation_id
            ]
            del self._in_flight_operations[client_operation_id]

    def restore_tracking_states(self, tracking_states: dict[str, Any]) -> None:
        raise NotImplementedError

    # === Retrieving ===

    def fetch_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: str | None = None,
        operations: dict[str, Operation] | None = None,
    ) -> Operation | None:
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
        operator_operation_id: str | None = None,
    ) -> Operation | None:
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self._in_flight_operations,
        )

    def fetch_cached_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: str | None = None,
    ) -> Operation | None:
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self.cached_operations,
        )

    def fetch_updatable_operation(
        self,
        client_operation_id: str | None = None,
        operator_operation_id: str | None = None,
    ) -> Operation | None:
        return self.fetch_operation(
            client_operation_id,
            operator_operation_id,
            operations=self.all_updatable_operations,
        )

    # === Updating ===

    def update_operator_operation_id(
        self, client_operation_id: str, operator_operation_id: str
    ) -> Operation | None:
        operation = self.fetch_tracked_operation(client_operation_id)
        if operation:
            operation.update_operator_operation_id(operator_operation_id)
        return operation

    # === Events ===

    def trigger_event(self, event_publication: EventPublication, event: Any) -> None:
        for event_publisher in self._event_publishers:
            event_publisher.trigger_event(event_publication, event)
