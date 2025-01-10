"""Balance locking mechanism for trading simulations.

This module provides mechanisms for locking portions of asset balances during
trading simulations. It supports both static and dynamic locks, with different
lock types for different use cases.

Key Features:
1. Static Balance Locks:
   - Lock a fixed amount of an asset
   - Track used and frozen portions
   - Support for hard and estimated locks

2. Dynamic Balance Locks:
   - Lock amounts that change based on other assets
   - Automatic updates based on custom functions
   - Useful for margin requirements, etc.

Example:
    >>> from decimal import Decimal
    >>> from financepype.assets import Asset
    >>> from financepype.simulations.balances.tracking import BalanceLock, LockType
    >>>
    >>> # Create a hard lock on BTC
    >>> lock = BalanceLock(
    ...     asset=Asset("BTC"),
    ...     amount=Decimal("1.0"),
    ...     purpose="margin",
    ...     lock_type=LockType.HARD
    ... )
    >>>
    >>> # Use some of the locked balance
    >>> lock.use(Decimal("0.5"))
    >>> print(lock.remaining)  # 0.5
"""

from collections.abc import Callable
from decimal import Decimal
from enum import Enum

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0


class LockType(Enum):
    """Type of balance lock.

    This enum defines the different types of balance locks:
    - HARD: Strict lock that must be respected (e.g., margin requirements)
    - ESTIMATED: Flexible lock for planning purposes (e.g., expected fees)
    """

    HARD = 1
    ESTIMATED = 2


class BalanceLock:
    """Lock for tracking reserved portions of an asset balance.

    This class manages a lock on a specific amount of an asset. The lock can
    track how much of the locked amount has been used or frozen, and ensures
    that the total used/frozen amount never exceeds the lock amount.

    Attributes:
        asset (Asset): The asset being locked
        amount (Decimal): Total amount of the lock
        purpose (str): Description of why the balance is locked
        lock_type (LockType): Whether this is a hard or estimated lock
        used (Decimal): Amount of the lock that has been used
        freezed (Decimal): Amount of the lock that is frozen
        remaining (Decimal): Amount still available (amount - used - freezed)

    Example:
        >>> # Create a lock for trading margin
        >>> lock = BalanceLock(
        ...     asset=Asset("BTC"),
        ...     amount=Decimal("1.0"),
        ...     purpose="margin",
        ...     lock_type=LockType.HARD
        ... )
        >>>
        >>> # Use some of the locked balance
        >>> lock.use(Decimal("0.5"))
        >>> print(lock.remaining)  # 0.5
        >>>
        >>> # Freeze some for pending operations
        >>> lock.freeze(Decimal("0.3"))
        >>> print(lock.remaining)  # 0.2
    """

    def __init__(
        self,
        asset: Asset,
        amount: Decimal,
        purpose: str = "",
        lock_type: LockType = LockType.HARD,
    ):
        """Initialize a new balance lock.

        Args:
            asset: The asset to lock
            amount: Amount to lock
            purpose: Description of why the balance is locked
            lock_type: Whether this is a hard or estimated lock
        """
        self._asset = asset
        self._amount = amount
        self._lock_type = lock_type
        self._purpose = purpose

        self._used = s_decimal_0
        self._freezed = s_decimal_0

    def __repr__(self) -> str:
        """Get string representation of the lock."""
        return f"<LockedBalance: {self.amount} of {self.asset.identifier.value}>"

    def __str__(self) -> str:
        """Get string representation of the lock."""
        return self.__repr__()

    @property
    def asset(self) -> Asset:
        """The asset being locked."""
        return self._asset

    @property
    def amount(self) -> Decimal:
        """Total amount of the lock."""
        return self._amount

    @property
    def lock_type(self) -> LockType:
        """Whether this is a hard or estimated lock."""
        return self._lock_type

    @property
    def purpose(self) -> str:
        """Description of why the balance is locked."""
        return self._purpose

    @property
    def used(self) -> Decimal:
        """Amount of the lock that has been used."""
        return self._used

    @property
    def freezed(self) -> Decimal:
        """Amount of the lock that is frozen."""
        return self._freezed

    @property
    def remaining(self) -> Decimal:
        """Amount still available (amount - used - freezed)."""
        return self.amount - self.used - self.freezed

    def add(self, lock: "BalanceLock") -> None:
        """Add another lock's amount to this lock.

        Args:
            lock: Another lock of the same type to add

        Raises:
            ValueError: If the lock types don't match
        """
        if self.lock_type != lock.lock_type:
            raise ValueError("Lock type mismatch")
        self._amount += lock.amount

    def release(self, amount: Decimal) -> None:
        """Release some of the locked amount.

        Args:
            amount: Amount to release

        Raises:
            ValueError: If trying to release more than is locked
        """
        if self.amount >= amount:
            self._amount -= amount
        else:
            raise ValueError("Insufficient locked balance to release")

    def use(self, amount: Decimal) -> None:
        """Mark some of the remaining balance as used.

        Args:
            amount: Amount to mark as used

        Raises:
            ValueError: If trying to use more than is remaining
        """
        if self.remaining < amount:
            raise ValueError("Insufficient remaining balance to use")
        self._used += amount

    def freeze(self, amount: Decimal) -> None:
        """Freeze some of the remaining balance.

        Args:
            amount: Amount to freeze

        Raises:
            ValueError: If trying to freeze more than is remaining
        """
        if self.remaining < amount:
            raise ValueError("Insufficient remaining balance to freeze")
        self._freezed += amount

    def unfreeze(self, amount: Decimal) -> None:
        """Unfreeze some of the frozen balance.

        Args:
            amount: Amount to unfreeze

        Raises:
            ValueError: If trying to unfreeze more than is frozen
        """
        if self.freezed < amount:
            raise ValueError("Insufficient freezed balance to unfreeze")
        self._freezed -= amount


class DynamicLock(BalanceLock):
    """Lock with a dynamically updated amount based on another asset.

    This class extends BalanceLock to support locks whose amount changes based
    on the quantity of another asset. This is useful for cases like margin
    requirements that depend on position size.

    Attributes:
        other_asset (Asset): The asset that determines the lock amount
        other_asset_quantity (Decimal): Quantity of the other asset
        update_function (Callable): Function to calculate lock amount

    Example:
        >>> # Create a dynamic margin lock based on position size
        >>> def margin_requirement(size: Decimal) -> Decimal:
        ...     return size * Decimal("0.1")  # 10% margin
        >>>
        >>> lock = DynamicLock(
        ...     asset=Asset("USD"),
        ...     other_asset=Asset("BTC"),
        ...     other_asset_quantity=Decimal("10.0"),
        ...     lock_type=LockType.HARD,
        ...     update_function=margin_requirement,
        ...     purpose="margin"
        ... )
        >>>
        >>> # Update the lock amount based on position size
        >>> lock.update()
        >>> print(lock.amount)  # 1.0 (10% of 10 BTC)
    """

    def __init__(
        self,
        asset: Asset,
        other_asset: Asset,
        other_asset_quantity: Decimal,
        lock_type: LockType,
        update_function: Callable[[Decimal], Decimal],
        purpose: str = "",
    ):
        """Initialize a new dynamic balance lock.

        Args:
            asset: The asset to lock
            other_asset: The asset that determines the lock amount
            other_asset_quantity: Initial quantity of the other asset
            lock_type: Whether this is a hard or estimated lock
            update_function: Function to calculate lock amount from quantity
            purpose: Description of why the balance is locked
        """
        super().__init__(asset, s_decimal_0, purpose=purpose, lock_type=lock_type)

        self.other_asset = other_asset
        self.other_asset_quantity = other_asset_quantity
        self.update_function = update_function

    def __repr__(self) -> str:
        """Get string representation of the dynamic lock."""
        return f"<DynamicLock: {self.other_asset_quantity} of {self.other_asset.identifier.value} in {self.asset.identifier.value}>"

    def add(self, lock: BalanceLock) -> None:
        """Add another dynamic lock's quantity to this lock.

        Args:
            lock: Another dynamic lock to add

        Raises:
            ValueError: If the locks are incompatible
        """
        if not isinstance(lock, DynamicLock):
            raise ValueError("Lock type mismatch")

        if self.other_asset != lock.other_asset:
            raise ValueError("Other asset mismatch")
        if self.update_function != lock.update_function:
            raise ValueError("Update function mismatch")
        self.other_asset_quantity += lock.other_asset_quantity

    def update(self) -> None:
        """Update the lock amount based on the current quantity."""
        self._amount = self.update_function(self.other_asset_quantity)
