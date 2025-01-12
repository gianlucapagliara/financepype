import time
from typing import Any

import pytest

from financepype.operations.transactions.models import (
    BlockchainTransactionReceipt,
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.operators.blockchains.identifier import BlockchainIdentifier
from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.platform import Platform


class MockBlockchainIdentifier(BlockchainIdentifier):
    """Mock implementation of BlockchainIdentifier for testing."""

    @classmethod
    def is_valid(cls, value: Any) -> bool:
        return isinstance(value, str)

    @classmethod
    def id_from_string(cls, value: str) -> str:
        return value

    @classmethod
    def id_to_string(cls, value: str) -> str:
        return value


class ConcreteBlockchainTransaction(BlockchainTransaction):
    """Concrete implementation of BlockchainTransaction for testing."""

    @property
    def can_be_modified(self) -> bool:
        return True

    @property
    def can_be_cancelled(self) -> bool:
        return True

    @property
    def can_be_speeded_up(self) -> bool:
        return True

    async def process_receipt(self, receipt: BlockchainTransactionReceipt) -> bool:
        self.receipt = receipt
        return True

    @classmethod
    def from_transaction(
        cls, transaction: BlockchainTransaction, **kwargs
    ) -> BlockchainTransaction:
        """Create a new transaction from an existing one."""
        new_kwargs = {
            "client_operation_id": transaction.client_operation_id,
            "owner_identifier": transaction.owner_identifier,
            "creation_timestamp": transaction.creation_timestamp,
            "current_state": transaction.current_state,
            **kwargs,
        }
        return cls(**new_kwargs)


@pytest.fixture
def platform():
    return Platform(identifier="test_platform", name="test_platform")


@pytest.fixture
def owner_identifier(platform):
    return OwnerIdentifier(name="test_owner", platform=platform)


@pytest.fixture
def blockchain_id():
    return MockBlockchainIdentifier(raw="ethereum", string="ethereum")


@pytest.fixture
def transaction(blockchain_id, owner_identifier):
    current_time = time.time()
    return ConcreteBlockchainTransaction(
        client_operation_id="test_operation_id",
        owner_identifier=owner_identifier,
        creation_timestamp=current_time,
        current_state=BlockchainTransactionState.PENDING_BROADCAST,
    )


@pytest.mark.asyncio
async def test_transaction_initialization(transaction, blockchain_id):
    """Test that BlockchainTransaction initializes with correct default values."""
    assert transaction.current_state == BlockchainTransactionState.PENDING_BROADCAST
    assert transaction.operator_operation_id is None
    assert transaction.signed_transaction is None
    assert transaction.receipt is None
    assert transaction.fee is None
    assert transaction.explorer_link is None
    assert transaction.client_operation_id == "test_operation_id"


def test_transaction_id_property(transaction):
    """Test that transaction_id property returns operator_operation_id."""
    tx_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
    transaction.operator_operation_id = tx_id
    assert transaction.transaction_id == tx_id


def test_client_transaction_id_property(transaction):
    """Test that client_transaction_id property returns client_operation_id."""
    assert transaction.client_transaction_id == transaction.client_operation_id


def test_state_properties(transaction):
    """Test all state-related properties."""
    # Test is_pending
    assert transaction.is_pending is True
    assert transaction.is_pending_broadcast is True
    assert transaction.is_broadcasted is False

    # Test broadcasted state
    transaction.current_state = BlockchainTransactionState.BROADCASTED
    assert transaction.is_pending is True
    assert transaction.is_pending_broadcast is False
    assert transaction.is_broadcasted is True

    # Test completed states
    transaction.current_state = BlockchainTransactionState.CONFIRMED
    assert transaction.is_completed is True
    assert transaction.is_finalized is False

    transaction.current_state = BlockchainTransactionState.FINALIZED
    assert transaction.is_completed is True
    assert transaction.is_finalized is True

    # Test failure states
    transaction.current_state = BlockchainTransactionState.FAILED
    assert transaction.is_failure is True
    assert transaction.is_completed is False

    transaction.current_state = BlockchainTransactionState.REJECTED
    assert transaction.is_failure is True
    assert transaction.is_completed is False

    # Test cancelled state
    transaction.current_state = BlockchainTransactionState.CANCELLED
    assert transaction.is_cancelled is True
    assert transaction.is_failure is False

    # Test closed states
    for state in [
        BlockchainTransactionState.CONFIRMED,
        BlockchainTransactionState.FINALIZED,
        BlockchainTransactionState.FAILED,
        BlockchainTransactionState.REJECTED,
        BlockchainTransactionState.CANCELLED,
    ]:
        transaction.current_state = state
        assert transaction.is_closed is True


def test_process_operation_update(transaction):
    """Test processing transaction updates."""
    tx_id = MockBlockchainIdentifier(raw="0x123", string="0x123")

    # Test initial update with transaction ID
    update = BlockchainTransactionUpdate(
        update_timestamp=1000.0,
        client_transaction_id=transaction.client_transaction_id,
        transaction_id=tx_id,
        new_state=BlockchainTransactionState.BROADCASTED,
    )

    success = transaction.process_operation_update(update)
    assert success is True
    assert transaction.transaction_id == tx_id
    assert transaction.current_state == BlockchainTransactionState.BROADCASTED
    assert transaction.last_update_timestamp == 1000.0

    # Test update with same transaction ID but different state
    update = BlockchainTransactionUpdate(
        update_timestamp=2000.0,
        client_transaction_id=transaction.client_transaction_id,
        transaction_id=tx_id,
        new_state=BlockchainTransactionState.CONFIRMED,
    )

    success = transaction.process_operation_update(update)
    assert success is True
    assert transaction.current_state == BlockchainTransactionState.CONFIRMED
    assert transaction.last_update_timestamp == 2000.0

    # Test update with different transaction ID (should fail)
    different_tx_id = MockBlockchainIdentifier(raw="0x456", string="0x456")
    update = BlockchainTransactionUpdate(
        update_timestamp=3000.0,
        client_transaction_id=transaction.client_transaction_id,
        transaction_id=different_tx_id,
        new_state=BlockchainTransactionState.FINALIZED,
    )

    success = transaction.process_operation_update(update)
    assert success is False
    assert transaction.current_state == BlockchainTransactionState.CONFIRMED
    assert transaction.last_update_timestamp == 2000.0


def test_update_signed_transaction(transaction):
    """Test updating signed transaction data."""
    signed_tx = {"raw_tx": "0x123..."}
    transaction.update_signed_transaction(signed_tx)
    assert transaction.signed_transaction == signed_tx

    # Test that updating an already signed transaction raises an error
    with pytest.raises(ValueError, match="Signed transaction already set"):
        transaction.update_signed_transaction({"raw_tx": "0x456..."})


@pytest.mark.asyncio
async def test_process_receipt(transaction):
    """Test processing transaction receipt."""
    tx_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
    receipt = BlockchainTransactionReceipt(
        transaction_id=tx_id,
        data={"gas_used": 21000},
    )

    success = await transaction.process_receipt(receipt)
    assert success is True
    assert transaction.receipt == receipt


def test_from_transaction(transaction):
    """Test creating a new transaction from an existing one."""
    new_client_id = "new_operation_id"
    new_transaction = ConcreteBlockchainTransaction.from_transaction(
        transaction, client_operation_id=new_client_id
    )

    assert new_transaction.client_operation_id == new_client_id
    assert new_transaction.current_state == transaction.current_state
