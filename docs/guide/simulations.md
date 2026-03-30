# Simulations

The `simulations` module provides a cashflow simulation framework for trading operations. Before executing a trade, you can calculate exactly which assets will flow in and out of an account — covering purchase costs, fees, PnL, funding payments, borrow interest, and staking rewards.

## Balance Tracking

### BalanceTracker

`BalanceTracker` is the central store for asset balances. It separates balances into *total* (everything owned) and *available* (free to trade), and adds support for locked balances and derivative positions.

```python
from decimal import Decimal
from financepype.simulations.balances.tracking.tracker import BalanceTracker, BalanceType

tracker = BalanceTracker(track_history=True)  # track_history=False by default
```

#### Adding and Removing Balances

```python
from financepype.assets.factory import AssetFactory
from financepype.platforms.platform import Platform

platform = Platform(identifier="sim")
btc = AssetFactory.get_asset(platform, "BTC")

tracker.add_balance(btc, Decimal("1.0"), reason="deposit", balance_type=BalanceType.TOTAL)
tracker.add_balance(btc, Decimal("1.0"), reason="deposit", balance_type=BalanceType.AVAILABLE)

tracker.remove_balance(btc, Decimal("0.1"), reason="withdrawal", balance_type=BalanceType.TOTAL)
```

#### Setting Balances

`set_balance` overwrites an asset's balance and returns a `BalanceChange` record:

```python
change = tracker.set_balance(btc, Decimal("2.0"), "exchange sync", BalanceType.TOTAL)
```

`set_balances` updates multiple assets at once. With `complete_update=True`, assets not in the list are zeroed out:

```python
usdt = AssetFactory.get_asset(platform, "USDT")
tracker.set_balances(
    new_balances=[(btc, Decimal("1.5")), (usdt, Decimal("50000"))],
    reason="snapshot",
    balance_type=BalanceType.TOTAL,
    complete_update=True,
)
```

#### Querying Balances

```python
tracker.get_balance(btc, BalanceType.TOTAL)      # Decimal
tracker.get_balance(btc, BalanceType.AVAILABLE)  # Decimal
tracker.get_unlocked_balance(btc)                 # available minus all locks
tracker.get_locked_balance(btc, "order_001")      # amount locked for purpose
tracker.get_available_locked_balance(btc, "order_001")  # remaining in lock
tracker.get_available_balance(btc, "order_001")   # unlocked + available-in-lock
```

### BalanceLock

`BalanceLock` reserves a portion of available balance for a specific purpose (e.g., an open order). Multiple locks can coexist per asset.

```python
from financepype.simulations.balances.tracking.lock import BalanceLock

lock = BalanceLock(asset=usdt, amount=Decimal("500"), purpose="order_001")
tracker.lock_balance(lock)

# Use some of the lock (e.g., partial fill)
tracker.use_locked_balance(usdt, "order_001", Decimal("250"))

# Freeze (commit) part of the lock
tracker.freeze_locked_balance(usdt, "order_001", Decimal("250"))

# Release (free) the rest
tracker.release_locked_balance(usdt, "order_001", Decimal("250"))
```

#### Atomic Multi-Lock

```python
locks = [
    BalanceLock(asset=btc, amount=Decimal("0.1"), purpose="order_002"),
    BalanceLock(asset=usdt, amount=Decimal("5000"), purpose="order_002"),
]
# All locks succeed atomically, or none are applied
tracker.lock_multiple_balances(locks)

# Simulate without actually locking
can_lock = tracker.simulate_locks(locks)
```

### BalanceType and BalanceUpdateType

```python
from financepype.simulations.balances.tracking.tracker import BalanceType, BalanceUpdateType

# BalanceType
BalanceType.TOTAL      # all owned assets
BalanceType.AVAILABLE  # assets free for trading

# BalanceUpdateType (recorded in history)
BalanceUpdateType.SNAPSHOT      # complete overwrite
BalanceUpdateType.DIFFERENTIAL  # incremental change
BalanceUpdateType.SIMULATED     # hypothetical change
```

### Balance History

If `track_history=True`, every balance change is recorded:

```python
history = tracker.balance_history  # list[BalanceChange]
for change in history:
    print(change.timestamp, change.asset, change.amount, change.reason)

tracker.clear_balance_history()
```

## Balance Engines

Balance engines simulate the cashflows of trading operations without actually executing them. They answer the question: *what will happen to my balances if I do this trade?*

### BalanceEngine (Abstract)

```python
from financepype.simulations.balances.engines.engine import BalanceEngine
```

Each engine implements four class methods that return lists of `AssetCashflow`:

| Method | Description |
|--------|-------------|
| `get_involved_assets(details)` | Assets involved (no amounts) |
| `get_opening_outflows(details)` | Assets leaving at open |
| `get_opening_inflows(details)` | Assets arriving at open |
| `get_closing_outflows(details)` | Assets leaving at close |
| `get_closing_inflows(details)` | Assets arriving at close |

`get_complete_simulation(details)` combines all four into an `OperationSimulationResult`.

### AssetCashflow and Models

```python
from financepype.simulations.balances.engines.models import (
    AssetCashflow, CashflowType, InvolvementType, CashflowReason,
    OperationSimulationResult,
)
```

| Enum | Values |
|------|--------|
| `CashflowType` | `INFLOW`, `OUTFLOW` |
| `InvolvementType` | `OPENING`, `CLOSING`, `SETTLEMENT` |
| `CashflowReason` | `OPERATION`, `FEE`, `PNL`, `FUNDING`, `INTEREST`, `REWARD`, `MARGIN`, `COLLATERAL` |

### Lifecycle Engines (BalanceEngine)

Model position lifecycles with 4 phases (opening outflows/inflows, closing outflows/inflows).

| Engine | Market | Description |
|--------|--------|-------------|
| `SpotBalanceEngine` | Spot | Buy/sell asset, deduct fees |
| `PerpetualBalanceEngine` | Perpetual | Margin, PnL, funding exposure |
| `OptionBalanceEngine` | Options | Premium, settlement |
| `BorrowBalanceEngine` | Lending | Open/close borrow lifecycle (collateral, repayment) |
| `StakingBalanceEngine` | Staking | Open/close staking lifecycle (stake, unstake, rewards) |
| `MultiEngine` | Any | Combine multiple engines |
| `Dashboard` | Any | Aggregate simulation results |

### Settlement Engines (SettlementEngine)

Model instantaneous recurring events (one payment at a time, with timestamps).

| Engine | Use Case | Description |
|--------|----------|-------------|
| `FundingSettlementEngine` | Perpetual | Single funding payment |
| `InterestSettlementEngine` | Lending | Single interest accrual period |
| `RewardSettlementEngine` | Staking | Single reward distribution epoch |
| `PeriodicSimulator` | Any | Iterates settlement engines over rate schedules |

### Example: Spot Engine

```python
from financepype.simulations.balances.engines.spot import SpotBalanceEngine

result = SpotBalanceEngine.get_complete_simulation(order)
print(result.opening_outflows)  # e.g., USDT leaving (buy cost)
print(result.closing_inflows)   # e.g., BTC arriving (purchase)
```

### Example: Funding Settlement

```python
from financepype.simulations.balances.engines.periodic import PeriodicSimulator

# Simulate multiple funding payments over a rate schedule
result = PeriodicSimulator.simulate_funding(funding_order_details, rate_schedule)
print(result.total_by_asset)  # Net funding impact across all periods
```

## BalanceSimulationEngine

`BalanceSimulationEngine` combines a `BalanceTracker` with one or more balance engines to simulate and apply trade results.

```python
from financepype.simulations.simulation import BalanceSimulationEngine

engine = BalanceSimulationEngine(tracker)
result = engine.simulate_order(order_details)

# Apply results to tracker
engine.apply_simulation_result(result)
```

## MultiEngine

`MultiEngine` delegates to different engines based on the operation type:

```python
from financepype.simulations.balances.engines.multiengine import MultiEngine

multi = MultiEngine(engines={
    MarketType.SPOT: SpotBalanceEngine,
    MarketType.PERPETUAL: PerpetualBalanceEngine,
    MarketType.CALL_OPTION: OptionBalanceEngine,
})

result = multi.get_complete_simulation(order_details)
```

## Dashboard

`Dashboard` aggregates simulation results across multiple operations for portfolio-level analysis:

```python
from financepype.simulations.balances.engines.dashboard import Dashboard

dashboard = Dashboard()
dashboard.add_result(result1)
dashboard.add_result(result2)

summary = dashboard.get_summary()
print(summary.net_inflows)
print(summary.total_fees)
```

## Practical Example

Simulate the full lifecycle of a spot buy order:

```python
import asyncio
from decimal import Decimal
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.markets.trading_pair import TradingPair
from financepype.simulations.balances.tracking.tracker import BalanceTracker, BalanceType
from financepype.simulations.balances.tracking.lock import BalanceLock

platform = Platform(identifier="sim")
btc = AssetFactory.get_asset(platform, "BTC")
usdt = AssetFactory.get_asset(platform, "USDT")

tracker = BalanceTracker()

# Initial state
tracker.set_balance(usdt, Decimal("10000"), "initial", BalanceType.TOTAL)
tracker.set_balance(usdt, Decimal("10000"), "initial", BalanceType.AVAILABLE)

# When order is placed: lock USDT
lock = BalanceLock(asset=usdt, amount=Decimal("500"), purpose="order_001")
tracker.lock_balance(lock)

# When order is filled: release lock, update balances
tracker.release_locked_balance(usdt, "order_001", Decimal("500"))
tracker.remove_balance(usdt, Decimal("500"), "buy fill", BalanceType.TOTAL)
tracker.remove_balance(usdt, Decimal("500"), "buy fill", BalanceType.AVAILABLE)
tracker.add_balance(btc, Decimal("0.01"), "buy fill", BalanceType.TOTAL)
tracker.add_balance(btc, Decimal("0.01"), "buy fill", BalanceType.AVAILABLE)

print(tracker.get_balance(usdt, BalanceType.TOTAL))   # Decimal('9500')
print(tracker.get_balance(btc, BalanceType.TOTAL))    # Decimal('0.01')
```
