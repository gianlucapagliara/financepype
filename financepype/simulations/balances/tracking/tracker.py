"""Balance tracking system for trading simulations.

This module provides a comprehensive system for tracking asset balances during
trading simulations. It supports tracking of total and available balances,
positions, and locked balances, with optional history tracking.

Key Features:
1. Balance Types:
   - Total Balance: All assets owned
   - Available Balance: Assets free for trading
   - Locked Balance: Assets reserved for specific purposes

2. Position Tracking:
   - Track derivative positions
   - Support for position increases/decreases
   - Position value tracking

3. Balance Locking:
   - Lock balances for specific purposes
   - Track used and frozen portions
   - Support for multiple locks per asset

4. History Tracking:
   - Optional balance change history
   - Track reasons for changes
   - Support for snapshots and differentials

Example:
    >>> from decimal import Decimal
    >>> from financepype.assets import Asset
    >>> from financepype.simulations.balances.tracking import BalanceTracker
    >>>
    >>> # Initialize tracker with history
    >>> tracker = BalanceTracker(track_history=True)
    >>>
    >>> # Add some balance
    >>> tracker.add_balance(
    ...     asset=Asset("BTC"),
    ...     amount=Decimal("1.0"),
    ...     reason="deposit",
    ...     balance_type=BalanceType.TOTAL
    ... )
    >>>
    >>> # Lock some for trading
    >>> lock = BalanceLock(
    ...     asset=Asset("BTC"),
    ...     amount=Decimal("0.5"),
    ...     purpose="margin"
    ... )
    >>> tracker.lock_balance(lock)
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from financepype.assets.asset import Asset
from financepype.assets.contract import DerivativeContract
from financepype.constants import s_decimal_0
from financepype.markets.position import Position
from financepype.simulations.balances.tracking.lock import BalanceLock


class BalanceType(Enum):
    """Type of balance being tracked.

    This enum defines the different types of balances:
    - TOTAL: All assets owned by the account
    - AVAILABLE: Assets that are free for trading
    """

    TOTAL = "total"
    AVAILABLE = "available"


class BalanceUpdateType(Enum):
    """Type of balance update operation.

    This enum defines how a balance is being updated:
    - SNAPSHOT: Complete balance update
    - DIFFERENTIAL: Incremental change
    - SIMULATED: Hypothetical change for testing
    """

    SNAPSHOT = "snapshot"
    DIFFERENTIAL = "differential"
    SIMULATED = "simulated"


class BalanceChange(BaseModel):
    """Record of a change in asset balance.

    This class represents a single change in an asset's balance, including
    metadata about when and why the change occurred.

    Attributes:
        timestamp (datetime): When the change occurred
        asset (Asset): The asset whose balance changed
        amount (Decimal): Amount of the change
        reason (str): Description of why the change occurred
        balance_type (BalanceType): Type of balance affected
        update_type (BalanceUpdateType): How the balance was updated

    Example:
        >>> change = BalanceChange(
        ...     asset=Asset("BTC"),
        ...     amount=Decimal("1.0"),
        ...     reason="deposit",
        ...     balance_type=BalanceType.TOTAL,
        ...     update_type=BalanceUpdateType.DIFFERENTIAL
        ... )
    """

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the change occurred",
    )
    asset: Asset = Field(description="The asset whose balance changed")
    amount: Decimal = Field(description="Amount of the change")
    reason: str = Field(description="Description of why the change occurred")
    balance_type: BalanceType = Field(description="Type of balance affected")
    update_type: BalanceUpdateType = Field(description="How the balance was updated")


class BalanceTracker:
    """System for tracking asset balances during trading simulations.

    This class provides comprehensive balance tracking functionality, including:
    - Total and available balances
    - Position tracking
    - Balance locking
    - Optional history tracking

    The tracker maintains separate dictionaries for different types of balances
    and provides methods for safely modifying these balances while maintaining
    consistency between them.

    Attributes:
        balance_history (list[BalanceChange]): Record of all balance changes
        total_balances (dict[Asset, Decimal]): All assets owned
        available_balances (dict[Asset, Decimal]): Assets free for trading
        positions (dict[DerivativeContract, Position]): Open positions
        locks (dict[Asset, dict[str, BalanceLock]]): Locked balances

    Example:
        >>> tracker = BalanceTracker(track_history=True)
        >>> tracker.add_balance(
        ...     asset=Asset("BTC"),
        ...     amount=Decimal("1.0"),
        ...     reason="deposit",
        ...     balance_type=BalanceType.TOTAL
        ... )
        >>> print(tracker.get_balance(Asset("BTC"), BalanceType.TOTAL))  # 1.0
    """

    def __init__(self, track_history: bool = False) -> None:
        """Initialize a new balance tracker.

        Args:
            track_history: Whether to record balance change history
        """
        self._total_balances: dict[Asset, Decimal] = {}
        self._available_balances: dict[Asset, Decimal] = {}
        self._positions: dict[DerivativeContract, Position] = {}
        self._locks: dict[Asset, dict[str, BalanceLock]] = {}

        self._track_history = track_history
        self._balance_history: list[BalanceChange] = []

    @property
    def balance_history(self) -> list[BalanceChange]:
        """Record of all balance changes (if history tracking is enabled)."""
        return self._balance_history.copy()

    @property
    def total_balances(self) -> dict[Asset, Decimal]:
        """All assets owned by the account."""
        return self._total_balances.copy()

    @property
    def available_balances(self) -> dict[Asset, Decimal]:
        """Assets that are free for trading."""
        return self._available_balances.copy()

    @property
    def positions(self) -> dict[DerivativeContract, Position]:
        """Currently open positions."""
        return self._positions.copy()

    @property
    def locks(self) -> dict[Asset, dict[str, BalanceLock]]:
        """Currently locked balances by asset and purpose."""
        return self._locks.copy()

    def clear_balance_history(self) -> None:
        """Clear the balance change history."""
        self._balance_history.clear()

    def record_balance_change(self, change: BalanceChange) -> None:
        """Record a balance change in the history.

        This method only records the change if history tracking is enabled.

        Args:
            change: The balance change to record
        """
        if not self._track_history:
            return
        self._balance_history.append(change)

    def _get_balance_change(
        self,
        asset: Asset,
        amount: Decimal,
        reason: str,
        balance_type: BalanceType,
        update_type: BalanceUpdateType,
    ) -> BalanceChange:
        """Create a new balance change record.

        Args:
            asset: The asset whose balance changed
            amount: Amount of the change
            reason: Description of why the change occurred
            balance_type: Type of balance affected
            update_type: How the balance was updated

        Returns:
            A new BalanceChange instance
        """
        return BalanceChange(
            asset=asset,
            amount=amount,
            reason=reason,
            balance_type=balance_type,
            update_type=update_type,
        )

    def add_balance(
        self, asset: Asset, amount: Decimal, reason: str, balance_type: BalanceType
    ) -> None:
        """Add to an asset's balance.

        This method increases the balance of an asset, creating a new balance
        entry if the asset doesn't exist yet.

        Args:
            asset: The asset to add balance to
            amount: Amount to add
            reason: Description of why the balance is being added
            balance_type: Whether to add to total or available balance

        Example:
            >>> tracker.add_balance(
            ...     asset=Asset("BTC"),
            ...     amount=Decimal("1.0"),
            ...     reason="deposit",
            ...     balance_type=BalanceType.TOTAL
            ... )
        """
        balance_dict = (
            self._total_balances
            if balance_type == BalanceType.TOTAL
            else self._available_balances
        )

        self.record_balance_change(
            self._get_balance_change(
                asset, amount, reason, balance_type, BalanceUpdateType.DIFFERENTIAL
            )
        )
        if asset in balance_dict:
            balance_dict[asset] += amount
        else:
            balance_dict[asset] = amount

    def remove_balance(
        self, asset: Asset, amount: Decimal, reason: str, balance_type: BalanceType
    ) -> None:
        """Remove from an asset's balance.

        This method decreases the balance of an asset, removing the balance
        entry entirely if it reaches zero.

        Args:
            asset: The asset to remove balance from
            amount: Amount to remove
            reason: Description of why the balance is being removed
            balance_type: Whether to remove from total or available balance

        Raises:
            ValueError: If the asset doesn't exist or has insufficient balance

        Example:
            >>> tracker.remove_balance(
            ...     asset=Asset("BTC"),
            ...     amount=Decimal("0.5"),
            ...     reason="withdrawal",
            ...     balance_type=BalanceType.TOTAL
            ... )
        """
        balance_dict = (
            self._total_balances
            if balance_type == BalanceType.TOTAL
            else self._available_balances
        )
        if asset not in balance_dict:
            raise ValueError("Asset not found in balances")

        if balance_dict[asset] < amount:
            raise ValueError("Insufficient balance")
        balance_change = self._get_balance_change(
            asset,
            -amount,
            reason,
            balance_type,
            BalanceUpdateType.DIFFERENTIAL,
        )
        self.record_balance_change(balance_change)

        balance_dict[asset] -= amount
        if balance_dict[asset] <= s_decimal_0:
            del balance_dict[asset]

    def set_balance(
        self, asset: Asset, amount: Decimal, reason: str, balance_type: BalanceType
    ) -> BalanceChange:
        """Set an asset's balance to a specific amount.

        This method sets the balance of an asset to an exact amount, recording
        the change as a snapshot update.

        Args:
            asset: The asset to set balance for
            amount: New balance amount
            reason: Description of why the balance is being set
            balance_type: Whether to set total or available balance

        Returns:
            Record of the balance change

        Raises:
            ValueError: If the amount is negative

        Example:
            >>> tracker.set_balance(
            ...     asset=Asset("BTC"),
            ...     amount=Decimal("1.0"),
            ...     reason="balance correction",
            ...     balance_type=BalanceType.TOTAL
            ... )
        """
        if amount < s_decimal_0:
            raise ValueError("Amount must be greater than 0")

        balance_dict = (
            self._total_balances
            if balance_type == BalanceType.TOTAL
            else self._available_balances
        )
        change_amount = amount - balance_dict.get(asset, s_decimal_0)
        balance_dict[asset] = amount
        balance_change = self._get_balance_change(
            asset,
            change_amount,
            reason,
            balance_type,
            BalanceUpdateType.SNAPSHOT,
        )
        self.record_balance_change(balance_change)

        return balance_change

    def set_balances(
        self,
        new_balances: list[tuple[Asset, Decimal]],
        reason: str,
        balance_type: BalanceType,
        complete_update: bool = False,
    ) -> list[BalanceChange]:
        """Set balances for multiple assets.

        This method sets the balances of multiple assets at once, optionally
        clearing any assets not included in the update.

        Args:
            new_balances: List of (asset, amount) pairs to set
            reason: Description of why the balances are being set
            balance_type: Whether to set total or available balances
            complete_update: Whether to clear unlisted assets

        Returns:
            List of balance change records

        Example:
            >>> tracker.set_balances(
            ...     new_balances=[
            ...         (Asset("BTC"), Decimal("1.0")),
            ...         (Asset("ETH"), Decimal("10.0"))
            ...     ],
            ...     reason="exchange sync",
            ...     balance_type=BalanceType.TOTAL,
            ...     complete_update=True
            ... )
        """
        balance_changes: list[BalanceChange] = []
        updated_assets: list[Asset] = []
        for asset, amount in new_balances:
            balance_changes.append(
                self.set_balance(asset, amount, reason, balance_type)
            )
            updated_assets.append(asset)

        if complete_update:
            balance_dict = (
                self._total_balances
                if balance_type == BalanceType.TOTAL
                else self._available_balances
            )
            not_updated_assets = set(balance_dict.keys()) - set(updated_assets)
            for asset in not_updated_assets:
                balance_changes.append(
                    self.set_balance(asset, s_decimal_0, reason, balance_type)
                )

        return balance_changes

    def set_position(
        self, position: Position, reason: str, balance_type: BalanceType
    ) -> None:
        """Set a position's size and update balances accordingly.

        Args:
            position: The position to set
            reason: Description of why the position is being set
            balance_type: Whether to update total or available balance
        """
        self.set_balance(position.asset, position.amount, reason, balance_type)
        self._positions[position.asset] = position

    def get_position(self, asset: DerivativeContract) -> Position | None:
        """Get the current position for an asset.

        Args:
            asset: The asset to get position for

        Returns:
            The current position or None if no position exists
        """
        return self._positions.get(asset)

    def remove_position(self, asset: DerivativeContract) -> Position | None:
        """Remove a position and its associated balances.

        Args:
            asset: The asset to remove position for

        Returns:
            The removed position or None if no position existed
        """
        position = self._positions.pop(asset, None)
        if position:
            self.remove_balance(
                asset, position.value, "Remove Position", BalanceType.TOTAL
            )
            self.remove_balance(
                asset, position.value, "Remove Position", BalanceType.AVAILABLE
            )
        return position

    def _check_lock(
        self, asset: Asset, purpose: str, raise_error: bool = True
    ) -> str | None:
        """Check if a lock exists for an asset and purpose.

        Args:
            asset: The asset to check
            purpose: The purpose to check
            raise_error: Whether to raise an error if the lock doesn't exist

        Returns:
            Error message if the lock doesn't exist, None otherwise

        Raises:
            ValueError: If the lock doesn't exist and raise_error is True
        """
        error = None

        if asset not in self._locks:
            error = "Asset not found in locked balances"
        elif purpose not in self._locks[asset]:
            error = f"No locked balance found for purpose '{purpose}'"

        if error and raise_error:
            raise ValueError(error)

        return error

    def lock_balance(self, lock: BalanceLock) -> BalanceLock:
        """Lock a portion of an asset's balance.

        This method reserves a portion of an asset's balance for a specific
        purpose, preventing it from being used for other purposes.

        Args:
            lock: The balance lock to apply

        Returns:
            The applied balance lock

        Raises:
            ValueError: If there is insufficient balance to lock

        Example:
            >>> lock = BalanceLock(
            ...     asset=Asset("BTC"),
            ...     amount=Decimal("0.5"),
            ...     purpose="margin"
            ... )
            >>> tracker.lock_balance(lock)
        """
        if not (
            lock.asset in self._available_balances
            and self._available_balances[lock.asset] >= lock.amount
        ):
            raise ValueError("Insufficient balance to lock")

        if lock.asset not in self._locks:
            self._locks[lock.asset] = {}

        if lock.purpose not in self._locks[lock.asset]:
            self._locks[lock.asset][lock.purpose] = lock
        elif not isinstance(lock, type(self._locks[lock.asset][lock.purpose])):
            raise ValueError(
                "Lock type mismatch. You should release the existing lock first or use a different purpose."
            )
        else:
            existing_lock = self._locks[lock.asset][lock.purpose]
            existing_lock.add(lock)
            lock = existing_lock

        return lock

    def release_locked_balance(
        self, asset: Asset, purpose: str, amount: Decimal
    ) -> None:
        self._check_lock(asset, purpose)

        lock = self._locks[asset][purpose]
        lock.release(amount)

    def release_all_locked_balances(self, asset: Asset) -> None:
        if asset in self._locks:
            for purpose in self._locks[asset]:
                self.release_locked_balance(
                    asset, purpose, self._locks[asset][purpose].remaining
                )

    def lock_multiple_balances(self, locks: list[BalanceLock]) -> list[BalanceLock]:
        completed_locks: list[BalanceLock] = []
        try:
            for lock in locks:
                completed_locks.append(self.lock_balance(lock))
        except ValueError as e:
            # If any lock fails, release all previous locks
            for lock in completed_locks:
                self.release_locked_balance(lock.asset, lock.purpose, lock.amount)
            raise ValueError("Failed to lock all required balances") from e

        return completed_locks

    def simulate_locks(self, locks: list[BalanceLock]) -> bool:
        try:
            self.lock_multiple_balances(locks)
            for lock in locks:
                self.release_locked_balance(lock.asset, lock.purpose, lock.amount)
            return True
        except ValueError:
            return False

    def use_locked_balance(self, asset: Asset, purpose: str, amount: Decimal) -> None:
        self._check_lock(asset, purpose)
        self._locks[asset][purpose].use(amount)

    def freeze_locked_balance(
        self, asset: Asset, purpose: str, amount: Decimal
    ) -> None:
        self._check_lock(asset, purpose)
        self._locks[asset][purpose].freeze(amount)

    def freeze_multiple_locked_balances(
        self, asset_purpose_amounts: list[tuple[Asset, str, Decimal]]
    ) -> None:
        freezed = []
        try:
            for asset, purpose, amount in asset_purpose_amounts:
                self.freeze_locked_balance(asset, purpose, amount)
                freezed.append((asset, purpose, amount))
        except:
            for asset, purpose, amount in freezed:
                self.unfreeze_locked_balance(
                    asset=asset,
                    purpose=purpose,
                    amount=amount,
                )
            raise

    def unfreeze_locked_balance(
        self, asset: Asset, purpose: str, amount: Decimal
    ) -> None:
        self._check_lock(asset, purpose)
        self._locks[asset][purpose].unfreeze(amount)

    # === Balance Queries ===

    def get_balance(self, asset: Asset, balance_type: BalanceType) -> Decimal:
        if balance_type == BalanceType.AVAILABLE:
            return self._available_balances.get(asset, s_decimal_0)
        elif balance_type == BalanceType.TOTAL:
            return self._total_balances.get(asset, s_decimal_0)
        else:
            raise ValueError(f"Invalid balance type: {balance_type}")

    def get_unlocked_balance(self, asset: Asset) -> Decimal:
        return self.get_balance(asset, BalanceType.AVAILABLE) - sum(
            locked_balance.remaining
            for locked_balance in self._locks.get(asset, {}).values()
        )

    def get_locked_balance(self, asset: Asset, purpose: str) -> Decimal:
        if asset in self._locks and purpose in self._locks[asset]:
            return self._locks[asset][purpose].amount
        else:
            return s_decimal_0

    def get_available_locked_balance(self, asset: Asset, purpose: str) -> Decimal:
        if asset in self._locks and purpose in self._locks[asset]:
            return self._locks[asset][purpose].remaining
        else:
            return s_decimal_0

    def get_available_balance(self, asset: Asset, purpose: str) -> Decimal:
        return self.get_unlocked_balance(asset) + self.get_available_locked_balance(
            asset, purpose
        )
