import asyncio
import time
from datetime import timedelta
from typing import Any, ClassVar, cast

import pytest
from pydantic import ValidationError

from financepype.assets.blockchain import BlockchainAsset, BlockchainAssetData
from financepype.operations.transactions.models import (
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.operators.blockchains.blockchain import Blockchain
from financepype.operators.blockchains.identifier import BlockchainIdentifier
from financepype.operators.blockchains.models import BlockchainConfiguration
from financepype.owners.owner import OwnerIdentifier
from financepype.owners.wallet import (
    BlockchainWallet,
    BlockchainWalletConfiguration,
    BlockchainWalletIdentifier,
)
from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType
from financepype.platforms.platform import Platform


class MockBlockchainType(BlockchainType):
    """Mock blockchain type."""

    EVM = "EVM"
    SOLANA = "Solana"


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


class MockBlockchain(Blockchain):
    """Test implementation of Blockchain."""

    def __init__(self, platform: BlockchainPlatform) -> None:
        config = BlockchainConfiguration(platform=platform)
        super().__init__(configuration=config)


class MockBlockchainTransaction(BlockchainTransaction):
    """Test implementation of BlockchainTransaction."""

    def __init__(
        self,
        client_operation_id: str,
        creation_timestamp: float,
        operator_operation_id: BlockchainIdentifier | None = None,
        owner_identifier: OwnerIdentifier | None = None,
        current_state: BlockchainTransactionState = BlockchainTransactionState.PENDING_BROADCAST,
        signed_transaction: Any | None = None,
    ) -> None:
        if owner_identifier is None:
            owner_identifier = OwnerIdentifier(
                name="test_owner", platform=Platform(identifier="test_platform")
            )
        super().__init__(
            client_operation_id=client_operation_id,
            creation_timestamp=creation_timestamp,
            operator_operation_id=operator_operation_id,
            owner_identifier=owner_identifier,
            current_state=current_state,
            signed_transaction=signed_transaction,
        )

    @property
    def blockchain(self) -> Blockchain:
        return MockBlockchain(
            platform=BlockchainPlatform(
                identifier="ethereum", type=MockBlockchainType.EVM
            )
        )

    @property
    def can_be_cancelled(self) -> bool:
        return False

    @property
    def can_be_modified(self) -> bool:
        return False

    @property
    def can_be_speeded_up(self) -> bool:
        return False

    async def process_receipt(self, receipt: Any) -> bool:
        return True

    @property
    def transaction_id(self) -> BlockchainIdentifier | None:
        return self.operator_operation_id

    def update_operator_operation_id(
        self, operator_operation_id: BlockchainIdentifier
    ) -> None:
        self.operator_operation_id = operator_operation_id


class MockBlockchainWallet(BlockchainWallet):
    """Test implementation of BlockchainWallet."""

    DEFAULT_TRANSACTION_CLASS: ClassVar[type[BlockchainTransaction]] = (
        MockBlockchainTransaction
    )

    def __init__(self, configuration: BlockchainWalletConfiguration) -> None:
        super().__init__(configuration=configuration)
        self._chain = MockBlockchain(platform=configuration.identifier.platform)
        self._transaction_updates: dict[str, BlockchainTransactionUpdate] = {}

    @property
    def blockchain(self) -> Blockchain:
        return self._chain

    @property
    def current_timestamp(self) -> float:
        return time.time()

    async def get_transaction_update(
        self,
        transaction: BlockchainTransaction,
        timeout: timedelta,
        raise_timeout: bool,
        **kwargs: Any,
    ) -> BlockchainTransactionUpdate:
        if transaction.client_operation_id in self._transaction_updates:
            update = self._transaction_updates[transaction.client_operation_id]
            if transaction.transaction_id is None:
                transaction.update_operator_operation_id(update.transaction_id)
            return update

        tx_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
        if transaction.transaction_id is None:
            transaction.update_operator_operation_id(tx_id)
        return BlockchainTransactionUpdate(
            update_timestamp=self.current_timestamp,
            client_transaction_id=transaction.client_operation_id,
            transaction_id=tx_id,
            new_state=transaction.current_state,
        )

    def set_transaction_update(
        self, transaction_id: str, update: BlockchainTransactionUpdate
    ) -> None:
        """Set a transaction update for testing."""
        self._transaction_updates[transaction_id] = update

    async def update_transactions(self) -> None:
        """Update status of pending transactions."""
        tasks = []
        for tx_id in self.transaction_tracker.all_updatable_operations.keys():
            transaction = cast(
                BlockchainTransaction | None,
                self.transaction_tracker.fetch_tracked_operation(tx_id),
            )
            if transaction is None:
                continue
            tasks.append(
                self.update_transaction(
                    transaction, timeout=timedelta(seconds=0), raise_timeout=False
                )
            )

        await asyncio.gather(*tasks)


@pytest.fixture
def blockchain_platform() -> BlockchainPlatform:
    """Create a blockchain platform fixture."""
    return BlockchainPlatform(identifier="ethereum", type=MockBlockchainType.EVM)


@pytest.fixture
def wallet_address() -> BlockchainIdentifier:
    return MockBlockchainIdentifier(raw="0x123", string="0x123")


@pytest.fixture
def wallet_identifier(
    blockchain_platform: BlockchainPlatform, wallet_address: BlockchainIdentifier
) -> BlockchainWalletIdentifier:
    return BlockchainWalletIdentifier(
        name="test_owner", platform=blockchain_platform, address=wallet_address
    )


@pytest.fixture
def test_asset(blockchain_platform: BlockchainPlatform) -> BlockchainAsset:
    """Create a test asset fixture."""
    test_id = MockBlockchainIdentifier(raw="0x123", string="0x123")
    data = BlockchainAssetData(name="Test Token", symbol="TEST", decimals=18)
    return BlockchainAsset(platform=blockchain_platform, identifier=test_id, data=data)


@pytest.fixture
def wallet_config(
    blockchain_platform: BlockchainPlatform,
    test_asset: BlockchainAsset,
    wallet_identifier: BlockchainWalletIdentifier,
) -> BlockchainWalletConfiguration:
    """Create a wallet configuration fixture."""

    return BlockchainWalletConfiguration(
        tracked_assets={test_asset},
        identifier=wallet_identifier,
    )


@pytest.fixture
def wallet(wallet_config: BlockchainWalletConfiguration) -> MockBlockchainWallet:
    """Create a test wallet fixture."""
    return MockBlockchainWallet(configuration=wallet_config)


def test_wallet_configuration_validation(
    wallet_config: BlockchainWalletConfiguration,
    test_asset: BlockchainAsset,
) -> None:
    """Test wallet configuration validation."""
    # Valid configuration
    config = wallet_config
    assert test_asset in config.tracked_assets
    assert config.default_tx_wait == timedelta(minutes=2)
    assert config.real_time_balance_update is True

    # Missing required fields
    with pytest.raises(ValidationError):
        BlockchainWalletConfiguration()  # type: ignore

    # Invalid chain type
    with pytest.raises(ValidationError):
        BlockchainWalletConfiguration(
            chain="invalid",  # type: ignore
            tracked_assets={test_asset},
            default_tx_wait=timedelta(minutes=2),
        )

    # Invalid tracked_assets type
    with pytest.raises(ValidationError):
        BlockchainWalletConfiguration(
            tracked_assets="invalid",  # type: ignore
        )


def test_wallet_initialization(wallet: MockBlockchainWallet) -> None:
    """Test wallet initialization."""
    assert not wallet.is_read_only
    assert isinstance(wallet.blockchain, MockBlockchain)
    assert wallet.transaction_tracker is not None
    assert len(wallet._pending_transaction_update) == 0
    assert len(wallet._tracked_assets) == 1


def test_wallet_tracked_assets(
    wallet: MockBlockchainWallet, test_asset: BlockchainAsset
) -> None:
    """Test tracked assets management."""
    # Initial state
    assert test_asset in wallet._tracked_assets

    # Remove asset
    wallet.remove_tracked_assets({test_asset})
    assert test_asset not in wallet._tracked_assets

    # Add asset back
    wallet.add_tracked_assets({test_asset})
    assert test_asset in wallet._tracked_assets

    # Add duplicate asset (should not duplicate)
    wallet.add_tracked_assets({test_asset})
    assert len(wallet._tracked_assets) == 1


@pytest.mark.asyncio
async def test_wallet_transaction_tracking(wallet: MockBlockchainWallet) -> None:
    """Test transaction tracking functionality."""
    # Prepare transaction
    tx = wallet.prepare_tracking_transaction("test_tx_1")
    assert tx.client_operation_id == "test_tx_1"
    assert tx.current_state == BlockchainTransactionState.PENDING_BROADCAST

    # Start tracking
    wallet.start_tracking_transaction(tx, timedelta(seconds=1))
    assert tx.client_operation_id in wallet._pending_transaction_update
    assert (
        wallet.transaction_tracker.fetch_tracked_operation(tx.client_operation_id) == tx
    )

    # Update transaction
    update = BlockchainTransactionUpdate(
        update_timestamp=wallet.current_timestamp,
        client_transaction_id=tx.client_operation_id,
        transaction_id=MockBlockchainIdentifier(raw="0x123", string="0x123"),
        new_state=BlockchainTransactionState.CONFIRMED,
    )
    wallet.set_transaction_update(tx.client_operation_id, update)

    result = await wallet.update_transaction(tx)
    assert result is not None
    assert result.new_state == BlockchainTransactionState.CONFIRMED
    assert tx.current_state == BlockchainTransactionState.CONFIRMED


@pytest.mark.asyncio
async def test_wallet_transaction_updates(wallet: MockBlockchainWallet) -> None:
    """Test multiple transaction updates."""
    # Create and track multiple transactions
    tx1 = wallet.prepare_tracking_transaction("test_tx_1")
    tx2 = wallet.prepare_tracking_transaction("test_tx_2")

    wallet.start_tracking_transaction(tx1, timedelta(seconds=1))
    wallet.start_tracking_transaction(tx2, timedelta(seconds=1))

    # Set different updates
    update1 = BlockchainTransactionUpdate(
        update_timestamp=wallet.current_timestamp,
        client_transaction_id=tx1.client_operation_id,
        transaction_id=MockBlockchainIdentifier(raw="0x123", string="0x123"),
        new_state=BlockchainTransactionState.CONFIRMED,
    )
    update2 = BlockchainTransactionUpdate(
        update_timestamp=wallet.current_timestamp,
        client_transaction_id=tx2.client_operation_id,
        transaction_id=MockBlockchainIdentifier(raw="0x456", string="0x456"),
        new_state=BlockchainTransactionState.FAILED,
    )

    wallet.set_transaction_update(tx1.client_operation_id, update1)
    wallet.set_transaction_update(tx2.client_operation_id, update2)

    # Update all transactions
    await wallet.update_transactions()

    assert tx1.current_state == BlockchainTransactionState.CONFIRMED
    assert tx2.current_state == BlockchainTransactionState.FAILED
