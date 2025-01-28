from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from financepype.assets.blockchain import BlockchainAsset, BlockchainAssetData
from financepype.operations.fees import FeeImpactType, FeeType
from financepype.operations.transactions.models import (
    BlockchainTransactionFee,
    BlockchainTransactionReceipt,
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operators.blockchains.identifier import BlockchainIdentifier
from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType


class MockBlockchainIdentifier(BlockchainIdentifier):
    """Test implementation of BlockchainIdentifier."""

    @classmethod
    def is_valid(cls, value: Any) -> bool:
        return isinstance(value, str)

    @classmethod
    def id_from_string(cls, value: str) -> str:
        return value

    @classmethod
    def id_to_string(cls, value: str) -> str:
        return value


def test_blockchain_transaction_state_values() -> None:
    """Test that BlockchainTransactionState enum has correct values."""
    assert BlockchainTransactionState.PENDING_BROADCAST.value == "pending"
    assert BlockchainTransactionState.BROADCASTED.value == "broadcasted"
    assert BlockchainTransactionState.CONFIRMED.value == "completed"
    assert BlockchainTransactionState.FINALIZED.value == "finalized"
    assert BlockchainTransactionState.FAILED.value == "failed"
    assert BlockchainTransactionState.REJECTED.value == "rejected"
    assert BlockchainTransactionState.CANCELLED.value == "cancelled"


def test_blockchain_transaction_fee_defaults() -> None:
    """Test that BlockchainTransactionFee has correct default values."""
    fee = BlockchainTransactionFee(amount=Decimal("0"))
    assert fee.asset is None
    assert fee.fee_type == FeeType.ABSOLUTE
    assert fee.impact_type == FeeImpactType.ADDED_TO_COSTS


def test_blockchain_transaction_fee_with_asset() -> None:
    """Test BlockchainTransactionFee with a specific asset."""
    platform = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
    identifier = MockBlockchainIdentifier(raw="0x123", string="0x123")
    data = BlockchainAssetData(name="Test Token", symbol="TEST", decimals=18)
    asset = BlockchainAsset(platform=platform, identifier=identifier, data=data)

    fee = BlockchainTransactionFee(amount=Decimal("0.1"), asset=asset)
    assert fee.asset == asset
    assert fee.fee_type == FeeType.ABSOLUTE
    assert fee.impact_type == FeeImpactType.ADDED_TO_COSTS


def test_blockchain_transaction_receipt() -> None:
    """Test BlockchainTransactionReceipt creation and immutability."""
    transaction_id = MockBlockchainIdentifier(raw="0x123", string="0x123")

    receipt = BlockchainTransactionReceipt(transaction_id=transaction_id)

    assert receipt.transaction_id == transaction_id

    # Test immutability
    with pytest.raises(ValidationError):
        receipt.transaction_id = MockBlockchainIdentifier(raw="0x456", string="0x456")


def test_blockchain_transaction_update_minimal() -> None:
    """Test BlockchainTransactionUpdate with minimal required fields."""
    transaction_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
    update = BlockchainTransactionUpdate(
        update_timestamp=1234567890.0,
        client_transaction_id="client_tx_1",
        transaction_id=transaction_id,
        new_state=BlockchainTransactionState.PENDING_BROADCAST,
    )

    assert update.update_timestamp == 1234567890.0
    assert update.client_transaction_id == "client_tx_1"
    assert update.transaction_id is not None
    assert update.transaction_id == transaction_id
    assert update.transaction_id.string == "0x123"
    assert update.new_state == BlockchainTransactionState.PENDING_BROADCAST
    assert update.receipt is None
    assert update.explorer_link is None
    assert update.other_data == {}


def test_blockchain_transaction_update_full() -> None:
    """Test BlockchainTransactionUpdate with all fields."""
    transaction_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
    receipt = BlockchainTransactionReceipt(
        transaction_id=transaction_id, data={"gas_used": 21000}
    )

    update = BlockchainTransactionUpdate(
        update_timestamp=1234567890.0,
        client_transaction_id="client_tx_1",
        transaction_id=transaction_id,
        new_state=BlockchainTransactionState.CONFIRMED,
        receipt=receipt,
        explorer_link="https://etherscan.io/tx/0x123",
        other_data={"gas_price": "20000000000"},
    )

    assert update.update_timestamp == 1234567890.0
    assert update.client_transaction_id == "client_tx_1"
    assert update.transaction_id == transaction_id
    assert update.new_state == BlockchainTransactionState.CONFIRMED
    assert update.receipt == receipt
    assert update.explorer_link == "https://etherscan.io/tx/0x123"
    assert update.other_data == {"gas_price": "20000000000"}


def test_blockchain_transaction_update_validation() -> None:
    """Test validation of BlockchainTransactionUpdate fields."""
    transaction_id = MockBlockchainIdentifier(raw="0x123", string="0x123")

    # Test missing required fields
    with pytest.raises(ValidationError):
        BlockchainTransactionUpdate(
            update_timestamp=1234567890.0,
            client_transaction_id=None,
            transaction_id=None,  # type: ignore
            new_state=BlockchainTransactionState.PENDING_BROADCAST,
        )

    # Test invalid timestamp type
    with pytest.raises(ValidationError):
        BlockchainTransactionUpdate(
            update_timestamp=None,  # type: ignore
            client_transaction_id="client_tx_1",
            transaction_id=transaction_id,
            new_state=BlockchainTransactionState.PENDING_BROADCAST,
        )

    # Test invalid state
    with pytest.raises(ValidationError):
        BlockchainTransactionUpdate(
            update_timestamp=1234567890.0,
            client_transaction_id="client_tx_1",
            transaction_id=transaction_id,
            new_state=None,  # type: ignore
        )
