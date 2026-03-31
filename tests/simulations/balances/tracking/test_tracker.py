from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.constants import s_decimal_0
from financepype.simulations.balances.tracking.lock import BalanceLock
from financepype.simulations.balances.tracking.tracker import (
    BalanceChange,
    BalanceTracker,
    BalanceType,
    BalanceUpdateType,
)


@pytest.fixture
def balance_tracker() -> BalanceTracker:
    return BalanceTracker(track_history=True)


class TestBalanceTracker:
    def test_init(self, balance_tracker: BalanceTracker) -> None:
        assert balance_tracker.total_balances == {}
        assert balance_tracker.available_balances == {}
        assert balance_tracker.locks == {}
        assert len(balance_tracker.balance_history) == 0

    def test_add_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        amount = Decimal("1.5")
        balance_tracker.add_balance(btc_asset, amount, "deposit", BalanceType.TOTAL)
        balance_tracker.add_balance(btc_asset, amount, "deposit", BalanceType.AVAILABLE)

        assert balance_tracker.total_balances[btc_asset] == amount
        assert balance_tracker.available_balances[btc_asset] == amount
        assert len(balance_tracker.balance_history) == 2

    def test_remove_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        initial_amount = Decimal("2.0")
        remove_amount = Decimal("0.5")

        balance_tracker.add_balance(
            btc_asset, initial_amount, "deposit", BalanceType.TOTAL
        )
        balance_tracker.remove_balance(
            btc_asset, remove_amount, "withdrawal", BalanceType.TOTAL
        )

        assert (
            balance_tracker.total_balances[btc_asset] == initial_amount - remove_amount
        )

    def test_remove_balance_insufficient(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("1.0"), "deposit", BalanceType.TOTAL
        )

        with pytest.raises(ValueError, match="Insufficient balance"):
            balance_tracker.remove_balance(
                btc_asset, Decimal("2.0"), "withdrawal", BalanceType.TOTAL
            )

    def test_set_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        amount = Decimal("1.0")
        change = balance_tracker.set_balance(
            btc_asset, amount, "set", BalanceType.TOTAL
        )

        assert isinstance(change, BalanceChange)
        assert balance_tracker.total_balances[btc_asset] == amount
        assert change.update_type == BalanceUpdateType.SNAPSHOT

    def test_set_balances(
        self, balance_tracker: BalanceTracker, btc_asset: Asset, usdt_asset: Asset
    ) -> None:
        balances = [
            (btc_asset, Decimal("1.0")),
            (usdt_asset, Decimal("2.0")),
        ]

        changes = balance_tracker.set_balances(balances, "batch set", BalanceType.TOTAL)

        assert len(changes) == 2
        assert balance_tracker.total_balances[btc_asset] == Decimal("1.0")
        assert balance_tracker.total_balances[usdt_asset] == Decimal("2.0")

    def test_lock_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        # Add available balance first
        balance_tracker.add_balance(
            btc_asset, Decimal("2.0"), "deposit", BalanceType.AVAILABLE
        )

        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        result = balance_tracker.lock_balance(lock)

        assert isinstance(result, BalanceLock)
        assert result.remaining == Decimal("1.0")
        assert balance_tracker.get_locked_balance(btc_asset, "trade") == Decimal("1.0")

    def test_lock_balance_insufficient(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("0.5"), "deposit", BalanceType.AVAILABLE
        )

        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        with pytest.raises(ValueError, match="Insufficient balance to lock"):
            balance_tracker.lock_balance(lock)

    def test_release_locked_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("2.0"), "deposit", BalanceType.AVAILABLE
        )
        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        balance_tracker.lock_balance(lock)

        balance_tracker.release_locked_balance(btc_asset, "trade", Decimal("0.5"))
        assert balance_tracker.get_locked_balance(btc_asset, "trade") == Decimal("0.5")

    def test_get_unlocked_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("2.0"), "deposit", BalanceType.AVAILABLE
        )
        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        balance_tracker.lock_balance(lock)

        assert balance_tracker.get_unlocked_balance(btc_asset) == Decimal("1.0")

    def test_get_available_balance_for_purpose(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("3.0"), "deposit", BalanceType.AVAILABLE
        )
        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        balance_tracker.lock_balance(lock)

        # Should return unlocked balance (2.0) + locked balance for purpose (1.0)
        assert balance_tracker.get_available_balance(btc_asset, "trade") == Decimal(
            "3.0"
        )
        # Should return only unlocked balance for different purpose
        assert balance_tracker.get_available_balance(btc_asset, "other") == Decimal(
            "2.0"
        )

    def test_simulate_locks(
        self, balance_tracker: BalanceTracker, btc_asset: Asset, usdt_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("1.0"), "deposit", BalanceType.AVAILABLE
        )
        balance_tracker.add_balance(
            usdt_asset, Decimal("2.0"), "deposit", BalanceType.AVAILABLE
        )

        locks = [
            BalanceLock(asset=usdt_asset, amount=Decimal("1.0"), purpose="trade"),
        ]

        assert balance_tracker.simulate_locks(locks)
        # Verify no actual locks were created
        assert balance_tracker.get_locked_balance(btc_asset, "trade") == s_decimal_0

    def test_freeze_and_unfreeze_locked_balance(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        balance_tracker.add_balance(
            btc_asset, Decimal("2.0"), "deposit", BalanceType.AVAILABLE
        )
        lock = BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="trade")
        balance_tracker.lock_balance(lock)

        balance_tracker.freeze_locked_balance(btc_asset, "trade", Decimal("0.5"))
        assert balance_tracker.get_locked_balance(btc_asset, "trade") == Decimal("1.0")

        balance_tracker.unfreeze_locked_balance(btc_asset, "trade", Decimal("0.5"))
        assert balance_tracker.get_locked_balance(btc_asset, "trade") == Decimal("1.0")

    # === C1: lock_balance checks unlocked balance, not gross available ===

    def test_lock_balance_rejects_overcommit(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        """C1: Multiple locks must not exceed unlocked balance."""
        balance_tracker.add_balance(
            btc_asset, Decimal("10.0"), "deposit", BalanceType.AVAILABLE
        )
        lock1 = BalanceLock(asset=btc_asset, amount=Decimal("8.0"), purpose="margin_a")
        balance_tracker.lock_balance(lock1)

        # Only 2.0 unlocked remains; locking 5.0 must fail
        lock2 = BalanceLock(asset=btc_asset, amount=Decimal("5.0"), purpose="margin_b")
        with pytest.raises(ValueError, match="Insufficient balance to lock"):
            balance_tracker.lock_balance(lock2)

    def test_lock_balance_allows_within_unlocked(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        """C1: Locking within unlocked balance succeeds."""
        balance_tracker.add_balance(
            btc_asset, Decimal("10.0"), "deposit", BalanceType.AVAILABLE
        )
        lock1 = BalanceLock(asset=btc_asset, amount=Decimal("6.0"), purpose="margin_a")
        balance_tracker.lock_balance(lock1)

        # 4.0 unlocked remains; locking 4.0 must succeed
        lock2 = BalanceLock(asset=btc_asset, amount=Decimal("4.0"), purpose="margin_b")
        result = balance_tracker.lock_balance(lock2)
        assert result.amount == Decimal("4.0")
        assert balance_tracker.get_unlocked_balance(btc_asset) == s_decimal_0

    # === C4: simulate_locks is read-only ===

    def test_simulate_locks_does_not_mutate_state(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        """C4: simulate_locks must not create or modify any locks."""
        balance_tracker.add_balance(
            btc_asset, Decimal("5.0"), "deposit", BalanceType.AVAILABLE
        )
        # Pre-existing lock
        existing_lock = BalanceLock(
            asset=btc_asset, amount=Decimal("2.0"), purpose="existing"
        )
        balance_tracker.lock_balance(existing_lock)

        locks_to_test = [
            BalanceLock(asset=btc_asset, amount=Decimal("1.0"), purpose="existing"),
        ]
        result = balance_tracker.simulate_locks(locks_to_test)
        assert result is True

        # Pre-existing lock must be unchanged
        assert balance_tracker.get_locked_balance(btc_asset, "existing") == Decimal(
            "2.0"
        )
        assert balance_tracker.get_unlocked_balance(btc_asset) == Decimal("3.0")

    def test_simulate_locks_rejects_overcommit(
        self, balance_tracker: BalanceTracker, btc_asset: Asset
    ) -> None:
        """C4: simulate_locks rejects when total exceeds unlocked."""
        balance_tracker.add_balance(
            btc_asset, Decimal("5.0"), "deposit", BalanceType.AVAILABLE
        )
        lock = BalanceLock(asset=btc_asset, amount=Decimal("3.0"), purpose="existing")
        balance_tracker.lock_balance(lock)

        # Only 2.0 unlocked; simulating 3.0 must fail
        locks_to_test = [
            BalanceLock(asset=btc_asset, amount=Decimal("3.0"), purpose="new"),
        ]
        assert balance_tracker.simulate_locks(locks_to_test) is False

    # === C5: lock_multiple_balances rollback preserves pre-existing locks ===

    def test_lock_multiple_rollback_preserves_existing(
        self, balance_tracker: BalanceTracker, btc_asset: Asset, usdt_asset: Asset
    ) -> None:
        """C5: Rollback on failure must not destroy pre-existing locks."""
        balance_tracker.add_balance(
            btc_asset, Decimal("10.0"), "deposit", BalanceType.AVAILABLE
        )
        balance_tracker.add_balance(
            usdt_asset, Decimal("1.0"), "deposit", BalanceType.AVAILABLE
        )

        # Pre-existing lock on BTC
        existing = BalanceLock(asset=btc_asset, amount=Decimal("5.0"), purpose="margin")
        balance_tracker.lock_balance(existing)

        # Try to lock BTC (merge into existing) + USDT (will fail: need 10, have 1)
        locks = [
            BalanceLock(asset=btc_asset, amount=Decimal("3.0"), purpose="margin"),
            BalanceLock(asset=usdt_asset, amount=Decimal("10.0"), purpose="margin"),
        ]
        with pytest.raises(ValueError, match="Failed to lock all required balances"):
            balance_tracker.lock_multiple_balances(locks)

        # Pre-existing BTC lock must be intact at 5.0
        assert balance_tracker.get_locked_balance(btc_asset, "margin") == Decimal("5.0")
        assert balance_tracker.get_unlocked_balance(btc_asset) == Decimal("5.0")
