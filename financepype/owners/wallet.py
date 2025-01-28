import asyncio
from abc import abstractmethod
from collections.abc import Coroutine, Iterable
from datetime import timedelta
from typing import Any, cast

from financepype.assets.blockchain import BlockchainAsset
from financepype.operations.transactions.events import TransactionPublications
from financepype.operations.transactions.models import (
    BlockchainTransactionState,
    BlockchainTransactionUpdate,
)
from financepype.operations.transactions.tracker import BlockchainTransactionTracker
from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.operators.blockchains.blockchain import Blockchain
from financepype.owners.owner import Owner, OwnerConfiguration
from financepype.platforms.blockchain import BlockchainPlatform


class BlockchainWalletConfiguration(OwnerConfiguration):
    """Configuration for blockchain wallet owners.

    This class extends OwnerConfiguration to include blockchain-specific
    configuration parameters. It defines settings for wallet behavior
    and transaction handling.

    Attributes:
        chain (BlockchainPlatform): The blockchain platform
        real_time_balance_update (bool): Whether to update balances in real-time
        tracked_assets (set[BlockchainAsset] | None): Assets to track
        default_tx_wait (timedelta): Default transaction wait timeout
    """

    chain: BlockchainPlatform
    real_time_balance_update: bool = True
    tracked_assets: set[BlockchainAsset]
    default_tx_wait: timedelta


class BlockchainWallet(Owner):
    """Base class for blockchain wallet owners.

    This class extends the Owner class to provide functionality specific to
    blockchain wallets. It handles transaction tracking, balance updates,
    and asset management for blockchain-based assets.

    The class provides an interface for interacting with blockchain networks,
    managing transactions, and tracking asset balances. It supports both
    real-time and manual balance updates.

    Attributes:
        DEFAULT_TRANSACTION_CLASS (type[BlockchainTransaction]): Default transaction type
        _poll_notifier (asyncio.Event): Event for polling notifications
        _transaction_tracker (BlockchainTransactionTracker): Tracks transactions
        _pending_transaction_update (set[str]): Set of pending transaction IDs
        _tracked_assets (set[BlockchainAsset]): Set of tracked assets

    Example:
        >>> config = BlockchainWalletConfiguration(...)
        >>> wallet = BlockchainWallet(config)
        >>> await wallet.update_all_balances()
        >>> await wallet.approve(operator, token)
    """

    broadcasted_publication = TransactionPublications.broadcasted_publication
    cancelled_publication = TransactionPublications.cancelled_publication
    confirmed_publication = TransactionPublications.confirmed_publication
    failed_publication = TransactionPublications.failed_publication
    finalized_publication = TransactionPublications.finalized_publication
    rejected_publication = TransactionPublications.rejected_publication

    DEFAULT_TRANSACTION_CLASS: type[BlockchainTransaction]

    def __init__(
        self,
        configuration: BlockchainWalletConfiguration,
    ) -> None:
        """Initialize a blockchain wallet.

        Args:
            configuration (BlockchainWalletConfiguration): Wallet configuration
        """
        super().__init__(configuration)

        self._poll_notifier = asyncio.Event()

        self._transaction_tracker = BlockchainTransactionTracker([self])
        self._pending_transaction_update: set[str] = set()

        self._tracked_assets = configuration.tracked_assets.copy()

        self.logger().info(f"Loaded hot wallet: {self}")

    # === Properties ===

    @property
    def blockchain(self) -> Blockchain:
        """Get the blockchain instance.

        Returns:
            Blockchain: The blockchain this wallet operates on

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @property
    def is_read_only(self) -> bool:
        """Check if wallet is read-only.

        Returns:
            bool: True if wallet is read-only
        """
        return False

    @property
    def transaction_tracker(self) -> BlockchainTransactionTracker:
        """Get the transaction tracker.

        Returns:
            BlockchainTransactionTracker: The transaction tracker instance
        """
        return self._transaction_tracker

    @property
    def configuration(self) -> BlockchainWalletConfiguration:
        """Get the wallet configuration.

        Returns:
            BlockchainWalletConfiguration: The wallet configuration
        """
        return cast(BlockchainWalletConfiguration, self._configuration)

    # === Tracked Assets ===

    def add_tracked_assets(self, assets: Iterable[BlockchainAsset]) -> None:
        """Add assets to track.

        Args:
            asset_identifiers (Iterable[BlockchainAsset]): Assets to track
        """
        old_assets = self._tracked_assets.copy()
        self._tracked_assets = self._tracked_assets.union(assets)

        for asset in self._tracked_assets - old_assets:
            asyncio.ensure_future(self.update_balance(asset))

    def remove_tracked_assets(self, assets: Iterable[BlockchainAsset]) -> None:
        """Remove tracked assets.

        Args:
            asset_identifiers (Iterable[BlockchainAsset]): Assets to remove
        """
        self._tracked_assets = self._tracked_assets.difference(assets)

    # === Balances ===

    async def update_all_balances(self) -> None:
        """Update balances for all tracked assets.

        This method triggers a balance update for all tracked assets
        and sets the balances_ready event when complete.
        """
        tasks: list[Coroutine[Any, Any, None]] = []
        for asset in self._tracked_assets:
            tasks.append(self.update_balance(asset))

        await asyncio.gather(*tasks)
        self._balances_ready.set()

    async def update_all_positions(self) -> None:
        raise NotImplementedError(
            "Positions are not supported on blockchain native wallets"
        )

    # === Transactions Management ===

    async def update_transaction(
        self,
        transaction: BlockchainTransaction,
        timeout: timedelta = timedelta(minutes=2),
        raise_timeout: bool = True,
        **kwargs: Any,
    ) -> BlockchainTransactionUpdate | None:
        """
        Waits for the transaction to be processed by the blockchain.

        Args:
            transaction (BlockchainTransaction): The transaction to wait for
            timeout (timedelta): Maximum time to wait for transaction completion
            raise_timeout (bool): Whether to raise an exception on timeout
            **kwargs: Additional waiting parameters

        Returns:
            BlockchainTransactionUpdate | None: The final transaction update or None if not pending
        """
        if not transaction.is_pending:
            return None

        transaction_update = await self.get_transaction_update(
            transaction, timeout, raise_timeout
        )
        updated = transaction.process_operation_update(transaction_update)
        if updated:
            transaction_update.new_state = transaction.current_state

        return transaction_update if updated else None

    async def update_transactions(self) -> None:
        """Update status of pending transactions.

        This method checks the status of all updatable transactions
        that are not currently pending an update.
        """
        tasks = []
        to_update = set(self.transaction_tracker.all_updatable_operations.keys())
        to_update = to_update - self._pending_transaction_update

        for tx_id in to_update:
            transaction = cast(
                BlockchainTransaction | None,
                self.transaction_tracker.fetch_tracked_operation(tx_id),
            )
            if transaction is None:
                continue
            self._pending_transaction_update.add(transaction.client_operation_id)
            tasks.append(
                self.update_transaction(
                    transaction, timeout=timedelta(seconds=0), raise_timeout=False
                )
            )

        await asyncio.gather(*tasks)

    def start_tracking_transaction(
        self, transaction: BlockchainTransaction, wait_timeout: timedelta
    ) -> None:
        """Start tracking a transaction.

        This method begins tracking a transaction and sets up an async
        task to wait for its completion and update balances accordingly.

        Args:
            transaction (BlockchainTransaction): Transaction to track
            wait_timeout (timedelta): How long to wait for completion
        """
        self.transaction_tracker.start_tracking_operation(transaction)
        self._pending_transaction_update.add(transaction.client_operation_id)

        async def _wait_tx_and_update_balances(
            wallet: "BlockchainWallet",
            transaction: BlockchainTransaction,
            wait_timeout: timedelta,
        ) -> None:
            update = await wallet.update_transaction(transaction, wait_timeout)
            if transaction.client_operation_id in wallet._pending_transaction_update:
                wallet._pending_transaction_update.remove(
                    transaction.client_operation_id
                )
            if update is not None:
                wallet.transaction_tracker.process_transaction_update(
                    update, lambda: wallet.current_timestamp
                )
                await wallet.update_all_balances()

        asyncio.ensure_future(
            _wait_tx_and_update_balances(self, transaction, wait_timeout)
        )

    def prepare_tracking_transaction(
        self,
        client_operation_id: str,
        transaction_class: type[BlockchainTransaction] | None = None,
        wait_timeout: timedelta | None = None,
        additional_kwargs: dict[str, Any] | None = None,
    ) -> BlockchainTransaction:
        """Prepare a transaction for tracking.

        This method creates or retrieves a transaction and prepares it
        for tracking. If the transaction already exists, it is returned.
        Otherwise, a new transaction is created and tracking is started.

        Args:
            client_operation_id (str): Unique transaction identifier
            transaction_class (type[BlockchainTransaction] | None): Optional custom transaction class
            wait_timeout (timedelta | None): Optional custom wait timeout
            additional_kwargs (dict[str, Any] | None): Additional transaction parameters

        Returns:
            BlockchainTransaction: The prepared transaction
        """
        tracked_transaction = cast(
            BlockchainTransaction | None,
            self.transaction_tracker.fetch_tracked_operation(client_operation_id),
        )
        if tracked_transaction is not None:
            return tracked_transaction

        transaction = self.DEFAULT_TRANSACTION_CLASS(
            client_operation_id=client_operation_id,
            creation_timestamp=self.current_timestamp,
            operator_operation_id=None,
            owner_identifier=self.identifier,
            current_state=BlockchainTransactionState.PENDING_BROADCAST,
            signed_transaction=None,
        )
        if transaction_class is not None:
            additional_kwargs = additional_kwargs or {}
            transaction = transaction_class.from_transaction(
                transaction, **additional_kwargs
            )

        self.start_tracking_transaction(
            transaction,
            wait_timeout=(
                wait_timeout
                if wait_timeout is not None
                else self.configuration.default_tx_wait
            ),
        )

        return transaction

    @abstractmethod
    async def get_transaction_update(
        self,
        transaction: BlockchainTransaction,
        timeout: timedelta,
        raise_timeout: bool,
        **kwargs: Any,
    ) -> BlockchainTransactionUpdate:
        """Get an update for a transaction.

        Args:
            transaction (BlockchainTransaction): The transaction to get update for
            timeout (timedelta): Maximum time to wait for update
            raise_timeout (bool): Whether to raise an exception on timeout
            **kwargs: Additional parameters for the update

        Returns:
            BlockchainTransactionUpdate: The transaction update

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
