from dataclasses import dataclass
from enum import Enum

from eventspype.pub.publication import EventPublication


class BlockchainTransactionEvent(Enum):
    """
    Enumeration of possible blockchain transaction events.

    Each event represents a specific state or transition in the transaction lifecycle:
    - TransactionRejected (901): Transaction was rejected by the network
    - TransactionBroadcasted (902): Transaction was successfully broadcast to the network
    - TransactionConfirmed (903): Transaction was confirmed in a block
    - TransactionFinalized (904): Transaction is considered final (enough confirmations)
    - TransactionFailed (905): Transaction execution failed
    - TransactionCancelled (906): Transaction was cancelled by the user
    """

    TransactionRejected = 901
    TransactionBroadcasted = 902
    TransactionConfirmed = 903
    TransactionFinalized = 904
    TransactionFailed = 905
    TransactionCancelled = 906


@dataclass
class TransactionEvent:
    """
    Base class for all transaction events.

    Attributes:
        timestamp (float): Unix timestamp when the event occurred
        client_operation_id (str): Unique identifier for the transaction operation
    """

    timestamp: float
    client_operation_id: str


@dataclass
class TransactionBroadcastedEvent(TransactionEvent):
    """Event emitted when a transaction is successfully broadcast to the blockchain network."""

    pass


@dataclass
class TransactionConfirmedEvent(TransactionEvent):
    """Event emitted when a transaction is confirmed in a block on the blockchain."""

    pass


@dataclass
class TransactionFinalizedEvent(TransactionEvent):
    """Event emitted when a transaction has received enough confirmations to be considered final."""

    pass


@dataclass
class TransactionFailedEvent(TransactionEvent):
    """Event emitted when a transaction execution fails on the blockchain."""

    pass


@dataclass
class TransactionRejectedEvent(TransactionEvent):
    """Event emitted when a transaction is rejected by the blockchain network."""

    pass


@dataclass
class TransactionCancelledEvent(TransactionEvent):
    """Event emitted when a transaction is cancelled by the user before execution."""

    pass


class TransactionPublications:
    """
    Class containing event publications for blockchain transactions.

    Attributes:
        broadcasted_publication (EventPublication): Publication for transaction broadcasted events
        confirmed_publication (EventPublication): Publication for transaction confirmed events
        finalized_publication (EventPublication): Publication for transaction finalized events
        failed_publication (EventPublication): Publication for transaction failed events
        rejected_publication (EventPublication): Publication for transaction rejected events
        cancelled_publication (EventPublication): Publication for transaction cancelled events
    """

    broadcasted_publication = EventPublication(
        BlockchainTransactionEvent.TransactionBroadcasted,
        TransactionBroadcastedEvent,
    )
    confirmed_publication = EventPublication(
        BlockchainTransactionEvent.TransactionConfirmed,
        TransactionConfirmedEvent,
    )
    finalized_publication = EventPublication(
        BlockchainTransactionEvent.TransactionFinalized,
        TransactionFinalizedEvent,
    )
    failed_publication = EventPublication(
        BlockchainTransactionEvent.TransactionFailed,
        TransactionFailedEvent,
    )
    rejected_publication = EventPublication(
        BlockchainTransactionEvent.TransactionRejected,
        TransactionRejectedEvent,
    )
    cancelled_publication = EventPublication(
        BlockchainTransactionEvent.TransactionCancelled,
        TransactionCancelledEvent,
    )
