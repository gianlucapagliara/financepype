from collections.abc import Callable
from decimal import Decimal
from enum import Enum

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0


class LockType(Enum):
    HARD = 1
    ESTIMATED = 2


class BalanceLock:
    def __init__(
        self,
        asset: Asset,
        amount: Decimal,
        purpose: str = "",
        lock_type: LockType = LockType.HARD,
    ):
        self._asset = asset
        self._amount = amount
        self._lock_type = lock_type
        self._purpose = purpose

        self._used = s_decimal_0
        self._freezed = s_decimal_0

    def __repr__(self) -> str:
        return f"<LockedBalance: {self.amount} of {self.asset.identifier.value}>"

    def __str__(self) -> str:
        return self.__repr__()

    # === Properties ===

    @property
    def asset(self) -> Asset:
        return self._asset

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def lock_type(self) -> LockType:
        return self._lock_type

    @property
    def purpose(self) -> str:
        return self._purpose

    @property
    def used(self) -> Decimal:
        return self._used

    @property
    def freezed(self) -> Decimal:
        return self._freezed

    @property
    def remaining(self) -> Decimal:
        return self.amount - self.used - self.freezed

    def add(self, lock: "BalanceLock") -> None:
        if self.lock_type != lock.lock_type:
            raise ValueError("Lock type mismatch")
        self._amount += lock.amount

    def release(self, amount: Decimal) -> None:
        if self.amount >= amount:
            self._amount -= amount
        else:
            raise ValueError("Insufficient locked balance to release")

    def use(self, amount: Decimal) -> None:
        if self.remaining < amount:
            raise ValueError("Insufficient remaining balance to use")
        self._used += amount

    def freeze(self, amount: Decimal) -> None:
        if self.remaining < amount:
            raise ValueError("Insufficient remaining balance to freeze")
        self._freezed += amount

    def unfreeze(self, amount: Decimal) -> None:
        if self.freezed < amount:
            raise ValueError("Insufficient freezed balance to unfreeze")
        self._freezed -= amount


class DynamicLock(BalanceLock):
    def __init__(
        self,
        asset: Asset,
        other_asset: Asset,
        other_asset_quantity: Decimal,
        lock_type: LockType,
        update_function: Callable[[Decimal], Decimal],
        purpose: str = "",
    ):
        super().__init__(asset, s_decimal_0, purpose=purpose, lock_type=lock_type)

        self.other_asset = other_asset
        self.other_asset_quantity = other_asset_quantity
        self.update_function = update_function

    def __repr__(self) -> str:
        return f"<DynamicLock: {self.other_asset_quantity} of {self.other_asset.identifier.value} in {self.asset.identifier.value}>"

    def add(self, lock: BalanceLock) -> None:
        if not isinstance(lock, DynamicLock):
            raise ValueError("Lock type mismatch")

        if self.other_asset != lock.other_asset:
            raise ValueError("Other asset mismatch")
        if self.update_function != lock.update_function:
            raise ValueError("Update function mismatch")
        self.other_asset_quantity += lock.other_asset_quantity

    def update(self) -> None:
        self._amount = self.update_function(self.other_asset_quantity)
