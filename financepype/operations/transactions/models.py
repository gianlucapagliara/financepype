from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from financepype.assets.blockchain import BlockchainAsset
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operators.blockchains.identifier import BlockchainIdentifier


class BlockchainTransactionState(Enum):
    """
    Enumeration of possible blockchain transaction states.

    States represent the current status of a transaction in its lifecycle:
    - PENDING_BROADCAST: Transaction created but not yet sent to the network
    - BROADCASTED: Transaction sent to the network, awaiting confirmation
    - CONFIRMED: Transaction included in a block and confirmed
    - FINALIZED: Transaction has enough confirmations to be considered immutable
    - FAILED: Transaction execution failed on the blockchain
    - REJECTED: Transaction rejected during simulation or by network
    - CANCELLED: Transaction cancelled by the user before execution
    """

    PENDING_BROADCAST = "pending"  # Not processed by a provider
    BROADCASTED = "broadcasted"  # Sent to a provider, but not confirmed yet
    CONFIRMED = "completed"  # Confirmed on the blockchain
    FINALIZED = "finalized"  # Confirmed and unchangeable on the blockchain
    FAILED = "failed"  # Processed by a provider, but failed
    REJECTED = "rejected"  # Rejected in the simulation or by a provider
    CANCELLED = "cancelled"  # Cancelled by the user


class BlockchainTransactionFee(OperationFee):
    """
    Represents the fee structure for a blockchain transaction.

    Attributes:
        asset (BlockchainAsset | None): The asset in which the fee is paid
        fee_type (FeeType): Type of fee (always ABSOLUTE)
        impact_type (FeeImpactType): How the fee impacts the transaction cost (always ADDED_TO_COSTS)
    """

    asset: BlockchainAsset | None = None
    fee_type: FeeType = Field(default=FeeType.ABSOLUTE, init=False)
    impact_type: FeeImpactType = Field(default=FeeImpactType.ADDED_TO_COSTS, init=False)


class BlockchainTransactionReceipt(BaseModel):
    """
    Immutable receipt of a processed blockchain transaction.

    Attributes:
        transaction_id (BlockchainIdentifier): Unique identifier of the transaction
        data (Any): Additional transaction-specific data from the blockchain
    """

    model_config = ConfigDict(frozen=True)

    transaction_id: BlockchainIdentifier


class BlockchainTransactionUpdate(BaseModel):
    """
    Represents an update to a blockchain transaction's status.

    Attributes:
        update_timestamp (float): Unix timestamp of when the update occurred
        client_transaction_id (str): Client-side identifier for the transaction
        transaction_id (BlockchainIdentifier): Blockchain-specific transaction identifier
        new_state (BlockchainTransactionState): Updated state of the transaction
        receipt (BlockchainTransactionReceipt | None): Transaction receipt if available
        explorer_link (str | None): URL to view transaction in blockchain explorer
        other_data (dict[str, Any]): Additional transaction-specific data
    """

    update_timestamp: float
    client_transaction_id: str | None = None
    transaction_id: BlockchainIdentifier | None = None
    new_state: BlockchainTransactionState
    receipt: BlockchainTransactionReceipt | None = None
    explorer_link: str | None = None
    other_data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def validate_identifiers(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate that at least one identifier is present."""
        if not data.get("client_transaction_id") and not data.get("transaction_id"):
            raise ValueError(
                "At least one of client_transaction_id or transaction_id must be present"
            )
        return data
