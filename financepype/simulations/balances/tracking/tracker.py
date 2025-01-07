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
    TOTAL = "total"
    AVAILABLE = "available"


class BalanceUpdateType(Enum):
    SNAPSHOT = "snapshot"
    DIFFERENTIAL = "differential"
    SIMULATED = "simulated"


class BalanceChange(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    asset: Asset
    amount: Decimal
    reason: str
    balance_type: BalanceType
    update_type: BalanceUpdateType


class BalanceTracker:
    def __init__(self, track_history: bool = False) -> None:
        self._total_balances: dict[Asset, Decimal] = {}
        self._available_balances: dict[Asset, Decimal] = {}
        self._positions: dict[DerivativeContract, Position] = {}
        self._locks: dict[Asset, dict[str, BalanceLock]] = {}

        self._track_history = track_history
        self._balance_history: list[BalanceChange] = []

    # === Properties ===

    @property
    def balance_history(self) -> list[BalanceChange]:
        return self._balance_history.copy()

    @property
    def total_balances(self) -> dict[Asset, Decimal]:
        return self._total_balances.copy()

    @property
    def available_balances(self) -> dict[Asset, Decimal]:
        return self._available_balances.copy()

    @property
    def positions(self) -> dict[DerivativeContract, Position]:
        return self._positions.copy()

    @property
    def locks(self) -> dict[Asset, dict[str, BalanceLock]]:
        return self._locks.copy()

    # === Balance History ===

    def clear_balance_history(self) -> None:
        self._balance_history.clear()

    def record_balance_change(self, change: BalanceChange) -> None:
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
        return BalanceChange(
            asset=asset,
            amount=amount,
            reason=reason,
            balance_type=balance_type,
            update_type=update_type,
        )

    # === Balance Management ===

    def add_balance(
        self, asset: Asset, amount: Decimal, reason: str, balance_type: BalanceType
    ) -> None:
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

    # === Positions Management ===

    def increase_position(
        self, position: Position, reason: str, balance_type: BalanceType
    ) -> None: ...

    def decrease_position(
        self, position: Position, reason: str, balance_type: BalanceType
    ) -> None: ...

    def set_position(
        self, position: Position, reason: str, balance_type: BalanceType
    ) -> None:
        self.set_balance(position.asset, position.amount, reason, balance_type)
        self._positions[position.asset] = position

    def get_position(self, asset: DerivativeContract) -> Position | None:
        return self._positions.get(asset)

    def remove_position(self, asset: DerivativeContract) -> Position | None:
        position = self._positions.pop(asset, None)
        if position:
            self.remove_balance(
                asset, position.value, "Remove Position", BalanceType.TOTAL
            )
            self.remove_balance(
                asset, position.value, "Remove Position", BalanceType.AVAILABLE
            )
        return position

    # === Locking Management ===

    def _check_lock(
        self, asset: Asset, purpose: str, raise_error: bool = True
    ) -> str | None:
        error = None

        if asset not in self._locks:
            error = "Asset not found in locked balances"
        elif purpose not in self._locks[asset]:
            error = f"No locked balance found for purpose '{purpose}'"

        if error and raise_error:
            raise ValueError(error)

        return error

    def lock_balance(self, lock: BalanceLock) -> BalanceLock:
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
