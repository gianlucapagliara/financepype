from abc import abstractmethod
from typing import Any, Self

from pydantic import Field

from financepype.operations.operation import Operation
from financepype.operations.transactions.models import (
    BlockchainTransactionFee,
    BlockchainTransactionReceipt,
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operators.blockchains.identifier import BlockchainIdentifier


class BlockchainTransaction(Operation):
    """
    Represents a blockchain transaction with its lifecycle management.

    This class handles the complete lifecycle of a blockchain transaction, including:
    - Transaction creation and signing
    - Broadcasting to the network
    - Status tracking and updates
    - Receipt processing
    - Transaction modifications (speed up, cancel)

    Attributes:
        current_state (BlockchainTransactionState): Initial state of the transaction
        operator_operation_id (BlockchainIdentifier | None): Unique identifier for the transaction
        signed_transaction (Any | None): The signed transaction data
        receipt (BlockchainTransactionReceipt | None): Transaction receipt after processing
        fee (BlockchainTransactionFee | None): Transaction fee details
        explorer_link (str | None): Link to view transaction in blockchain explorer
    """

    current_state: BlockchainTransactionState = Field(
        default=BlockchainTransactionState.PENDING_BROADCAST
    )
    operator_operation_id: BlockchainIdentifier | None = None
    signed_transaction: Any | None = None
    receipt: BlockchainTransactionReceipt | None = None
    fee: BlockchainTransactionFee | None = None
    explorer_link: str | None = None

    @classmethod
    def from_transaction(cls, transaction: Self, **kwargs: Any) -> Self:
        return transaction

    # === Properties ===

    @property
    def client_transaction_id(self) -> str:
        """Legacy identifier for the transaction. Use client_operation_id instead."""
        return self.client_operation_id

    @property
    def transaction_id(self) -> BlockchainIdentifier | None:
        """The unique identifier of the transaction on the blockchain."""
        return self.operator_operation_id

    @property
    def paid_fee(self) -> BlockchainTransactionFee | None:
        """The actual fee paid for this transaction."""
        raise NotImplementedError

    @property
    @abstractmethod
    def can_be_modified(self) -> bool:
        """Whether the transaction can be modified (e.g., gas price adjustment)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def can_be_cancelled(self) -> bool:
        """Whether the transaction can be cancelled."""
        raise NotImplementedError

    @property
    @abstractmethod
    def can_be_speeded_up(self) -> bool:
        """Whether the transaction can be accelerated (e.g., by increasing gas price)."""
        raise NotImplementedError

    # === Status Properties ===

    @property
    def is_pending(self) -> bool:
        """Whether the transaction is in a pending state (not yet confirmed)."""
        return self.current_state in [
            BlockchainTransactionState.PENDING_BROADCAST,
            BlockchainTransactionState.BROADCASTED,
        ]

    @property
    def is_pending_broadcast(self) -> bool:
        return self.current_state == BlockchainTransactionState.PENDING_BROADCAST

    @property
    def is_broadcasted(self) -> bool:
        return self.current_state == BlockchainTransactionState.BROADCASTED

    @property
    def is_failure(self) -> bool:
        return self.current_state in [
            BlockchainTransactionState.FAILED,
            BlockchainTransactionState.REJECTED,
        ]

    @property
    def is_completed(self) -> bool:
        return self.current_state in [
            BlockchainTransactionState.CONFIRMED,
            BlockchainTransactionState.FINALIZED,
        ]

    @property
    def is_finalized(self) -> bool:
        return self.current_state == BlockchainTransactionState.FINALIZED

    @property
    def is_cancelled(self) -> bool:
        return self.current_state == BlockchainTransactionState.CANCELLED

    @property
    def is_closed(self) -> bool:
        return self.current_state in [
            BlockchainTransactionState.CONFIRMED,
            BlockchainTransactionState.FINALIZED,
            BlockchainTransactionState.FAILED,
            BlockchainTransactionState.REJECTED,
            BlockchainTransactionState.CANCELLED,
        ]

    # === Updating ===

    def process_operation_update(
        self, transaction_update: BlockchainTransactionUpdate
    ) -> bool:
        """
        Updates the transaction with new information from the blockchain.

        Args:
            transaction_update: New transaction information from the blockchain

        Returns:
            bool: True if the update was applied successfully, False otherwise
        """
        # Handle initial transaction ID update
        if (
            self.transaction_id is None
            and transaction_update.transaction_id is not None
        ):
            self.update_operator_operation_id(transaction_update.transaction_id)

        if transaction_update.transaction_id != self.transaction_id:
            return False

        if transaction_update.update_timestamp < self.last_update_timestamp:
            return False

        prev_status = self.current_state

        if transaction_update.new_state != self.current_state:
            self.current_state = transaction_update.new_state

        if transaction_update.explorer_link is not None:
            self.explorer_link = transaction_update.explorer_link

        if transaction_update.receipt is not None:
            self.process_receipt(transaction_update.receipt)

        if prev_status != self.current_state:
            self.last_update_timestamp = transaction_update.update_timestamp

        return True

    def update_signed_transaction(self, signed_transaction: Any) -> None:
        """
        Updates the transaction with its signed data.

        Args:
            signed_transaction: The signed transaction data

        Raises:
            ValueError: If the transaction is already signed
        """
        if self.signed_transaction is not None:
            raise ValueError("Signed transaction already set")
        self.signed_transaction = signed_transaction

    @abstractmethod
    def process_receipt(self, receipt: BlockchainTransactionReceipt) -> bool:
        """
        Processes the transaction receipt from the blockchain.

        Args:
            receipt: The transaction receipt to process

        Returns:
            bool: True if receipt was processed successfully
        """
        raise NotImplementedError
