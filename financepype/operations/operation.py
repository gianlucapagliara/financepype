import asyncio
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from financepype.owners.owner import OwnerIdentifier


class Operation(BaseModel):
    """Abstract base class for trading operations.

    This class provides the foundation for tracking and managing trading operations
    across different platforms. It maintains the operation's state, identifiers,
    and timestamps throughout its lifecycle.

    Attributes:
        client_operation_id (str): Unique identifier assigned by the client
        operator_operation_id (str | None): Identifier assigned by the operator/exchange
        owner_identifier (OwnerIdentifier | None): Identity of the operation owner
        creation_timestamp (float): Unix timestamp when operation was created
        last_update_timestamp (float): Unix timestamp of the last state update
        current_state (Any): Current state of the operation
        other_data (dict): Additional operation-specific data

    Example:
        >>> op = MyOperation(
        ...     client_operation_id="trade_123",
        ...     creation_timestamp=1640995200.0,
        ...     owner_identifier=OwnerIdentifier("user1")
        ... )
        >>> await op.wait_for_operator_operation_id()
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client_operation_id: str
    operator_operation_id: Any | None = None
    owner_identifier: OwnerIdentifier
    creation_timestamp: float
    last_update_timestamp: float = 0.0
    current_state: Any
    other_data: dict[str, Any] = Field(default_factory=dict)

    operator_operation_id_update_event: asyncio.Event = Field(
        default_factory=asyncio.Event,
        exclude=True,
    )

    def model_post_init(self, __context: Any) -> None:
        """Initialize non-Pydantic attributes after model initialization."""
        super().model_post_init(__context)
        if self.operator_operation_id:
            self.operator_operation_id_update_event.set()

    def __str__(self) -> str:
        """Get a string representation of the operation.

        Returns:
            str: Human-readable representation of the operation
        """
        return (
            f"{self.__class__.__name__}(client_operation_id={self.client_operation_id}, operator_operation_id={self.operator_operation_id}, "
            f"owner_identifier={self.owner_identifier}, last_update_timestamp={self.last_update_timestamp}, current_state={self.current_state})"
        )

    # === Updating ===

    def update_operator_operation_id(self, operator_operation_id: Any) -> None:
        """Update the operator-assigned operation ID.

        This method can only be called once to set the operator ID.
        Subsequent attempts to change it will raise an error.

        Args:
            operator_operation_id: The new operator operation identifier

        Raises:
            ValueError: If attempting to change an existing operator ID
        """
        if (
            self.operator_operation_id is not None
            and self.operator_operation_id != operator_operation_id
        ):
            raise ValueError(
                f"Cannot update operator operation id from {self.operator_operation_id} to {operator_operation_id}"
            )
        self.operator_operation_id = operator_operation_id
        self.operator_operation_id_update_event.set()

    @abstractmethod
    def process_operation_update(self, update: Any) -> bool:
        """Process an update to the operation's state.

        This method must be implemented by subclasses to handle
        operation-specific state updates.

        Args:
            update: The update data to process

        Returns:
            bool: True if the update was processed successfully, False otherwise

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
