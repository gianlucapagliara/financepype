from decimal import Decimal

import pytest

from financepype.assets.spot import SpotAsset
from financepype.simulations.balances.tracking.lock import (
    BalanceLock,
    DynamicLock,
    LockType,
)


def test_lock_type_values() -> None:
    assert LockType.HARD.value == 1
    assert LockType.ESTIMATED.value == 2


def test_balance_lock_init(btc_asset: SpotAsset) -> None:
    lock = BalanceLock(
        asset=btc_asset,
        amount=Decimal("1.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )

    assert lock.asset == btc_asset
    assert lock.amount == Decimal("1.5")
    assert lock.purpose == "test"
    assert lock.lock_type == LockType.HARD
    assert lock.used == Decimal("0")
    assert lock.freezed == Decimal("0")
    assert lock.remaining == Decimal("1.5")
    assert str(lock) == "<LockedBalance: 1.5 of BTC>"


def test_balance_lock_add(btc_asset: SpotAsset) -> None:
    lock1 = BalanceLock(
        asset=btc_asset,
        amount=Decimal("1.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )
    lock2 = BalanceLock(
        asset=btc_asset,
        amount=Decimal("0.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )

    lock1.add(lock2)
    assert lock1.amount == Decimal("2.0")

    # Test adding lock with different type
    lock3 = BalanceLock(
        asset=btc_asset,
        amount=Decimal("0.5"),
        purpose="test",
        lock_type=LockType.ESTIMATED,
    )
    with pytest.raises(ValueError, match="Lock type mismatch"):
        lock1.add(lock3)


def test_balance_lock_release(btc_asset: SpotAsset) -> None:
    lock = BalanceLock(
        asset=btc_asset,
        amount=Decimal("1.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )

    lock.release(Decimal("0.5"))
    assert lock.amount == Decimal("1.0")

    # Test releasing more than available
    with pytest.raises(ValueError, match="Insufficient locked balance to release"):
        lock.release(Decimal("1.5"))


def test_balance_lock_use(btc_asset: SpotAsset) -> None:
    lock = BalanceLock(
        asset=btc_asset,
        amount=Decimal("1.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )

    lock.use(Decimal("0.5"))
    assert lock.used == Decimal("0.5")
    assert lock.remaining == Decimal("1.0")

    # Test using more than remaining
    with pytest.raises(ValueError, match="Insufficient remaining balance to use"):
        lock.use(Decimal("1.1"))


def test_balance_lock_freeze_unfreeze(btc_asset: SpotAsset) -> None:
    lock = BalanceLock(
        asset=btc_asset,
        amount=Decimal("1.5"),
        purpose="test",
        lock_type=LockType.HARD,
    )

    lock.freeze(Decimal("0.5"))
    assert lock.freezed == Decimal("0.5")
    assert lock.remaining == Decimal("1.0")

    # Test freezing more than remaining
    with pytest.raises(ValueError, match="Insufficient remaining balance to freeze"):
        lock.freeze(Decimal("1.1"))

    lock.unfreeze(Decimal("0.3"))
    assert lock.freezed == Decimal("0.2")
    assert lock.remaining == Decimal("1.3")

    # Test unfreezing more than frozen
    with pytest.raises(ValueError, match="Insufficient freezed balance to unfreeze"):
        lock.unfreeze(Decimal("0.3"))


def test_dynamic_lock(btc_asset: SpotAsset, usdt_asset: SpotAsset) -> None:
    def update_func(quantity: Decimal) -> Decimal:
        return quantity * Decimal("50000")  # Mock BTC/USDT price

    lock = DynamicLock(
        asset=usdt_asset,
        other_asset=btc_asset,
        other_asset_quantity=Decimal("1.5"),
        lock_type=LockType.ESTIMATED,
        update_function=update_func,
        purpose="test",
    )

    assert lock.other_asset == btc_asset
    assert lock.other_asset_quantity == Decimal("1.5")
    assert str(lock) == "<DynamicLock: 1.5 of BTC in USDT>"

    # Test update
    lock.update()
    assert lock.amount == Decimal("75000")  # 1.5 BTC * 50000 USDT/BTC

    # Test add
    other_lock = DynamicLock(
        asset=usdt_asset,
        other_asset=btc_asset,
        other_asset_quantity=Decimal("0.5"),
        lock_type=LockType.ESTIMATED,
        update_function=update_func,
        purpose="test",
    )

    lock.add(other_lock)
    assert lock.other_asset_quantity == Decimal("2.0")

    # Test adding incompatible lock
    with pytest.raises(ValueError, match="Lock type mismatch"):
        lock.add(
            BalanceLock(
                asset=usdt_asset,
                amount=Decimal("1000"),
                purpose="test",
                lock_type=LockType.ESTIMATED,
            )
        )
